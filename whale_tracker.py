import requests
import time
from typing import Dict, List, Optional
import yaml
import logging
from datetime import datetime
import pandas as pd
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class WhaleTracker:
    def __init__(self, config_path: str = 'config.yaml', whale_csv_path: str = 'csv_reports/whale_summary.csv'):
        self.config = self._load_config(config_path)
        self.whale_addresses = self._load_whale_addresses(whale_csv_path)
        self.last_checked_block = {
            'ethereum': None,
            'bsc': None
        }
        self.api_keys = {
            'ethereum': self._get_etherscan_api_key(),
            'bsc': self._get_bscscan_api_key()
        }

    def _load_config(self, config_path: str) -> dict:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)

    def _load_whale_addresses(self, whale_csv_path: str) -> Dict[str, List[Dict]]:
        """Load whale addresses from CSV file and organize them by chain."""
        if not os.path.exists(whale_csv_path):
            logger.error(f"Whale addresses CSV file not found: {whale_csv_path}")
            return {'ethereum': [], 'bsc': []}

        try:
            df = pd.read_csv(whale_csv_path)
            whale_addresses = {'ethereum': [], 'bsc': []}

            # Convert column names to lowercase for case-insensitive matching
            df.columns = [col.lower() for col in df.columns]
            
            # Filter for addresses with significant volume (> whale_alert_threshold)
            df = df[df['total volume (usd)'] > self.config['whale_alert_threshold']]
            
            for _, row in df.iterrows():
                # Get chain from 'active chains' column
                chains = [chain.strip().lower() for chain in row['active chains'].split(',')]
                
                for chain in chains:
                    if chain in whale_addresses:
                        whale_addresses[chain].append({
                            'address': row['address'],
                            'label': f"Whale {row['address'][:8]} ({row['tokens traded']})"
                        })

            # Log the number of whales found for each chain
            for chain, whales in whale_addresses.items():
                logger.info(f"Loaded {len(whales)} whale addresses for {chain}")
                
            return whale_addresses
        except Exception as e:
            logger.error(f"Error loading whale addresses from CSV: {e}")
            return {'ethereum': [], 'bsc': []}

    def _get_etherscan_api_key(self) -> str:
        api_key = os.getenv('ETHERSCAN_API_KEY')
        if not api_key:
            raise ValueError("ETHERSCAN_API_KEY not found in environment variables")
        return api_key

    def _get_bscscan_api_key(self) -> str:
        api_key = os.getenv('BSCSCAN_API_KEY')
        if not api_key:
            raise ValueError("BSCSCAN_API_KEY not found in environment variables")
        return api_key

    def _get_current_block(self, chain: str) -> Optional[int]:
        base_url = {
            'ethereum': 'https://api.etherscan.io/api',
            'bsc': 'https://api.bscscan.com/api'
        }
        
        url = f"{base_url[chain]}?module=proxy&action=eth_blockNumber&apikey={self.api_keys[chain]}"
        try:
            response = requests.get(url, timeout=self.config['api_timeout'])
            data = response.json()
            
            # Log the full response for debugging
            logger.debug(f"API Response ({chain}): {data}")
            
            if data.get('status') == '1' or (isinstance(data.get('result'), str) and len(data['result']) > 2):
                try:
                    return int(data['result'], 16)
                except ValueError as e:
                    logger.error(f"Error parsing block number for {chain}: {e}")
                    return None
            else:
                error_msg = data.get('result', data.get('message', 'Unknown error'))
                logger.error(f"API error for {chain}: {error_msg}")
                if 'Invalid API Key' in str(error_msg):
                    logger.error(f"Please check your {chain.upper()}_API_KEY in the .env file")
                return None
        except Exception as e:
            logger.error(f"Network error for {chain}: {e}")
            return None

    def _fetch_transactions(self, chain: str, address: str, start_block: int) -> List[dict]:
        base_url = {
            'ethereum': 'https://api.etherscan.io/api',
            'bsc': 'https://api.bscscan.com/api'
        }
        
        url = f"{base_url[chain]}?module=account&action=txlist&address={address}&startblock={start_block}&sort=asc&apikey={self.api_keys[chain]}"
        
        try:
            response = requests.get(url, timeout=self.config['api_timeout'])
            data = response.json()
            
            # Log the full response for debugging
            logger.debug(f"API Response ({chain}): {data}")
            
            if data.get('status') == '1' and isinstance(data.get('result'), list):
                return data['result']
            else:
                error_msg = data.get('result', data.get('message', 'Unknown error'))
                logger.error(f"API error for {chain}: {error_msg}")
                if 'Invalid API Key' in str(error_msg):
                    logger.error(f"Please check your {chain.upper()}_API_KEY in the .env file")
                elif 'No transactions found' in str(error_msg):
                    logger.info(f"No transactions found for address {address} on {chain}")
                return []
        except Exception as e:
            logger.error(f"Request error for {chain}: {e}")
            return []

    def _process_transaction(self, tx: dict, chain: str, whale_info: dict) -> None:
        # Get token contract addresses for the current chain
        token_addresses = {
            token_name.lower(): token_data[chain].lower()
            for token_name, token_data in self.config['tokens'].items()
        }
        
        # Check if this transaction involves any of our tracked tokens
        contract_address = tx.get('to', '').lower()
        if contract_address not in token_addresses.values():
            return
        
        # Get the token name
        token_name = next(
            (name for name, addr in token_addresses.items() if addr == contract_address),
            'Unknown'
        ).upper()
        
        # For ERC20 transfers, the value is in the input data
        # This is a simplified check - in production you'd want to decode the input data properly
        if tx['value'] == '0' and len(tx.get('input', '')) >= 138:  # Standard ERC20 transfer length
            # Extract value from input data (this is a simplified version)
            try:
                value_hex = tx['input'][-64:]
                value = int(value_hex, 16)
                # Most stablecoins use 6 decimals
                decimals = 6 if token_name in ['USDT', 'USDC'] else 18
                value = value / (10 ** decimals)
            except Exception as e:
                logger.error(f"Error processing transaction value: {e}")
                return
        else:
            # Not an ERC20 transfer
            return

        timestamp = datetime.fromtimestamp(int(tx['timeStamp']))
        
        # For stablecoins, the value is approximately equal to USD
        if value > self.config['whale_alert_threshold']:
            logger.info(
                f"🐋 Whale Alert! {chain.upper()}\n"
                f"Whale: {whale_info['label']}\n"
                f"Token: {token_name}\n"
                f"Transaction: {tx['hash']}\n"
                f"From: {tx['from']}\n"
                f"To: {tx['to']}\n"
                f"Value: ${value:,.2f}\n"
                f"Time: {timestamp}"
            )

    def check_whale_transactions(self) -> None:
        # First verify API keys
        for chain in ['ethereum', 'bsc']:
            if not self.api_keys[chain] or self.api_keys[chain] == 'your_etherscan_api_key_here' or self.api_keys[chain] == 'your_bscscan_api_key_here':
                logger.error(f"Invalid {chain.upper()}_API_KEY in .env file. Please update with your actual API key.")
                continue
                
        for chain in ['ethereum', 'bsc']:
            current_block = self._get_current_block(chain)
            if current_block is None:
                continue

            if self.last_checked_block[chain] is None:
                self.last_checked_block[chain] = current_block - 1000  # Start from last 1000 blocks

            whale_addresses = self.whale_addresses.get(chain, [])
            if not whale_addresses:
                logger.warning(f"No whale addresses configured for chain: {chain}")
                continue
            
            logger.info(f"Checking {len(whale_addresses)} whale addresses on {chain}")
            
            for whale in whale_addresses:
                # Respect rate limits
                time.sleep(self.config['rate_limits'][chain])
                
                transactions = self._fetch_transactions(
                    chain,
                    whale['address'],
                    self.last_checked_block[chain]
                )
                
                if transactions:
                    logger.info(f"Found {len(transactions)} transactions for whale {whale['label']} on {chain}")
                
                for tx in transactions:
                    self._process_transaction(tx, chain, whale)

            self.last_checked_block[chain] = current_block

    def reload_whale_addresses(self, whale_csv_path: str = 'csv_reports/whale_summary.csv') -> None:
        """Reload whale addresses from CSV file without restarting the tracker."""
        logger.info("Reloading whale addresses from CSV...")
        self.whale_addresses = self._load_whale_addresses(whale_csv_path)
        logger.info(f"Loaded {sum(len(addrs) for addrs in self.whale_addresses.values())} whale addresses")

def main():
    tracker = WhaleTracker(whale_csv_path='/Users/jeremy/stablecoin-tracker/csv_reports/whale_summary.csv')
    logger.info("Starting whale transaction tracker...")
    
    while True:
        try:
            tracker.check_whale_transactions()
            # Reload whale addresses before each check to catch any updates
            tracker.reload_whale_addresses('/Users/jeremy/stablecoin-tracker/csv_reports/whale_summary.csv')
            time.sleep(60 * 15)  # Wait for 15 minutes before next check
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            time.sleep(60)  # Wait 1 minute before retrying on error

if __name__ == "__main__":
    main() 