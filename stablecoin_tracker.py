import os
import time
import schedule
import requests
from datetime import datetime
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import StringIO
import sys
import pathlib
import json
import pandas as pd
import yaml
import logging
from typing import Dict, List, Optional

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_config():
    """Load configuration from config.yaml"""
    config_path = pathlib.Path("config.yaml")
    if not config_path.exists():
        raise FileNotFoundError("config.yaml not found. Please create the configuration file.")
    
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

# Load configuration
CONFIG = load_config()

# API Keys
ETHERSCAN_API_KEY = os.getenv('ETHERSCAN_API_KEY')
BSCSCAN_API_KEY = os.getenv('BSCSCAN_API_KEY')

# Constants from config
LARGE_TX_THRESHOLD = CONFIG['large_tx_threshold']
API_TIMEOUT = CONFIG['api_timeout']
TOKENS = CONFIG['tokens']

def get_supply_from_defillama(token_info):
    """Get token supply from DefiLlama API"""
    url = "https://stablecoins.llama.fi/stablecoins?includePrices=true"
    try:
        response = requests.get(url)
        data = response.json()
        
        for stablecoin in data['peggedAssets']:
            # Match by name or symbol
            if (stablecoin['name'] == token_info['defillama_id'] or 
                stablecoin['symbol'] == token_info['defillama_id']):
                return float(stablecoin['circulating']['peggedUSD'])
        return 0
    except Exception as e:
        print(f"Error fetching supply: {str(e)}")
        if 'response' in locals():
            print(f"Response status code: {response.status_code}")
            print(f"Response content: {response.text[:500]}...")  # Print first 500 chars of response
        return 0

def get_transactions_page(chain, token_address, page):
    """Get a single page of transactions"""
    api_key = ETHERSCAN_API_KEY if chain == 'ethereum' else BSCSCAN_API_KEY
    base_url = 'https://api.etherscan.io/api' if chain == 'ethereum' else 'https://api.bscscan.com/api'
    
    # Get timestamp from update_interval minutes ago
    minutes_ago = int(time.time()) - (CONFIG['update_interval'] * 60)
    
    url = (
        f"{base_url}?module=account&action=tokentx"
        f"&contractaddress={token_address}"
        f"&starttime={minutes_ago}"
        f"&page={page}"
        f"&offset=20"  # Transactions per page
        f"&sort=desc"
        f"&apikey={api_key}"
    )
    
    # Add delay between requests based on config
    time.sleep(CONFIG['rate_limits'][chain])
    
    try:
        response = requests.get(url, timeout=API_TIMEOUT)
        data = response.json()
        
        if data.get('message') == 'OK' and data.get('status') == '1':
            result = data['result']
            print(f"Successfully fetched {len(result)} transactions for {chain} page {page}")
            return result
        else:
            print(f"API Error for {chain} page {page}: {data.get('message', 'Unknown error')}")
            return []
    except Exception as e:
        print(f"Error fetching {chain} page {page}: {str(e)}")
        return []

def get_large_transactions(chain, token_address):
    """Get large transactions from Etherscan/BscScan"""
    print(f"\nFetching transactions for {chain}...")
    all_transactions = []
    
    # Process pages sequentially for better stability
    for page in range(1, 3):  # Fetch first 2 pages
        transactions = get_transactions_page(chain, token_address, page)
        if transactions:
            all_transactions.extend(transactions)
            time.sleep(1)  # Add small delay between pages
    
    print(f"Found {len(all_transactions)} total transactions for {chain}")
    
    try:
        # Filter for transactions > threshold
        large_txs = [
            tx for tx in all_transactions 
            if float(tx['value']) / (10 ** int(tx['tokenDecimal'])) > LARGE_TX_THRESHOLD
        ]
        
        # Sort by value in descending order
        large_txs.sort(
            key=lambda x: float(x['value']) / (10 ** int(x['tokenDecimal'])), 
            reverse=True
        )
        return large_txs[:10]  # Return top 10 largest transactions
    except Exception as e:
        print(f"Error processing transactions for {chain}: {str(e)}")
        return []

def get_whale_data_path():
    """Generate the whale data file path"""
    data_dir = pathlib.Path("data")
    data_dir.mkdir(exist_ok=True)
    return data_dir / "whale_addresses.json"

def load_whale_data():
    """Load existing whale data from file"""
    whale_file = get_whale_data_path()
    if whale_file.exists():
        try:
            with open(whale_file, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}

def save_whale_data(whale_data):
    """Save whale data to file"""
    whale_file = get_whale_data_path()
    with open(whale_file, 'w') as f:
        json.dump(whale_data, f, indent=4)

def update_whale_data(tx, chain, token_name):
    """Update whale data with new transaction"""
    whale_data = load_whale_data()
    
    # Get transaction details
    value = float(tx['value']) / (10 ** int(tx['tokenDecimal']))
    timestamp = datetime.fromtimestamp(int(tx['timeStamp'])).strftime('%Y-%m-%d %H:%M:%S')
    
    # Update sender data
    if tx['from'] not in whale_data:
        whale_data[tx['from']] = {
            'total_transactions': 0,
            'chains': set(),
            'tokens': set(),
            'last_active': '',
            'transactions': []
        }
    
    # Update receiver data
    if tx['to'] not in whale_data:
        whale_data[tx['to']] = {
            'total_transactions': 0,
            'chains': set(),
            'tokens': set(),
            'last_active': '',
            'transactions': []
        }
    
    # Update sender stats
    sender = whale_data[tx['from']]
    sender['total_transactions'] += 1
    sender['chains'] = list(set(sender['chains']).union([chain]))
    sender['tokens'] = list(set(sender['tokens']).union([token_name]))
    sender['last_active'] = timestamp
    sender['transactions'].append({
        'type': 'send',
        'token': token_name,
        'chain': chain,
        'amount': value,
        'timestamp': timestamp,
        'tx_hash': tx['hash']
    })
    
    # Update receiver stats
    receiver = whale_data[tx['to']]
    receiver['total_transactions'] += 1
    receiver['chains'] = list(set(receiver['chains']).union([chain]))
    receiver['tokens'] = list(set(receiver['tokens']).union([token_name]))
    receiver['last_active'] = timestamp
    receiver['transactions'].append({
        'type': 'receive',
        'token': token_name,
        'chain': chain,
        'amount': value,
        'timestamp': timestamp,
        'tx_hash': tx['hash']
    })
    
    # Keep only last N transactions per address based on config
    max_txs = CONFIG['max_transactions_per_address']
    sender['transactions'] = sender['transactions'][-max_txs:]
    receiver['transactions'] = receiver['transactions'][-max_txs:]
    
    save_whale_data(whale_data)
    return whale_data

def format_large_transaction(tx, chain, token_name):
    """Format transaction data for display"""
    value = float(tx['value']) / (10 ** int(tx['tokenDecimal']))
    timestamp = datetime.fromtimestamp(int(tx['timeStamp']))
    
    # Update whale data
    update_whale_data(tx, chain, token_name)
    
    # Create a formatted string with clear sections
    formatted_tx = (
        f"{'=' * 100}\n"
        f"Time: {timestamp.strftime('%Y-%m-%d %H:%M:%S')} | Chain: {chain.upper()}\n"
        f"Amount: {value:,.2f}\n"
        f"From: {tx['from']}\n"
        f"To: {tx['to']}\n"
        f"Tx Hash: {tx['hash']}\n"
        f"Block: {tx['blockNumber']}\n"
        f"{'=' * 100}"
    )
    return formatted_tx

def generate_report_path():
    """Generate the report directory and filename"""
    reports_dir = pathlib.Path("reports")
    reports_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return reports_dir / f"stablecoin_report_{timestamp}.txt"

def generate_whale_report():
    """Generate a summary report of whale activity"""
    whale_data = load_whale_data()
    
    if not whale_data:
        return "No whale activity recorded yet."
    
    report = []
    report.append(f"\n{'=' * 100}")
    report.append("WHALE ACTIVITY SUMMARY")
    report.append(f"{'=' * 100}\n")
    
    # Sort whales by total transactions
    sorted_whales = sorted(
        whale_data.items(),
        key=lambda x: x[1]['total_transactions'],
        reverse=True
    )
    
    for address, data in sorted_whales:
        report.append(f"Address: {address}")
        report.append(f"Total Transactions: {data['total_transactions']}")
        report.append(f"Active on Chains: {', '.join(data['chains'])}")
        report.append(f"Tokens Traded: {', '.join(data['tokens'])}")
        report.append(f"Last Active: {data['last_active']}")
        report.append(f"Recent Transaction: {data['transactions'][-1]}")
        report.append("-" * 100)
    
    return "\n".join(report)

def get_csv_directory():
    """Generate the CSV directory path"""
    csv_dir = pathlib.Path("csv_reports")
    csv_dir.mkdir(exist_ok=True)
    return csv_dir

def export_whale_summary_to_csv():
    """Export whale summary data to a single persistent CSV file using pandas"""
    whale_data = load_whale_data()
    if not whale_data:
        return None
    
    csv_dir = get_csv_directory()
    summary_file = csv_dir / "whale_summary.csv"
    
    # Prepare data for DataFrame
    summary_data = []
    for address, data in whale_data.items():
        transactions = data['transactions']
        total_volume = sum(tx['amount'] for tx in transactions)
        avg_tx_size = total_volume / len(transactions) if transactions else 0
        
        summary_data.append({
            'Address': address,
            'Total Transactions': data['total_transactions'],
            'Active Chains': ', '.join(data['chains']),
            'Tokens Traded': ', '.join(data['tokens']),
            'Last Active': data['last_active'],
            'Total Volume (USD)': total_volume,
            'Average Transaction Size (USD)': avg_tx_size
        })
    
    # Create DataFrame and sort by Total Volume
    df = pd.DataFrame(summary_data)
    df.sort_values('Total Volume (USD)', ascending=False, inplace=True)
    df.to_csv(summary_file, index=False, float_format='%.2f')
    
    return summary_file

class StablecoinTracker:
    def __init__(self, config_path: str = 'config.yaml'):
        self.config = self._load_config(config_path)
        self.last_update = None
        self.transactions = []
        self.ensure_directories()

    def _load_config(self, config_path: str) -> dict:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)

    def ensure_directories(self):
        """Create necessary directories if they don't exist."""
        directories = ['data', 'csv_reports']
        for directory in directories:
            if not os.path.exists(directory):
                os.makedirs(directory)
                logger.info(f"Created directory: {directory}")

    def track_stablecoins(self):
        """Main tracking function."""
        try:
            # Your existing tracking logic here
            logger.info("Tracking stablecoin movements...")
            # ... rest of your tracking code ...
            
            # Save results
            self._save_results()
            
        except Exception as e:
            logger.error(f"Error tracking stablecoins: {e}")

    def _save_results(self):
        """Save tracking results to CSV files."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Save whale transactions
            if self.transactions:
                tx_file = f"csv_reports/whale_transactions_{timestamp}.csv"
                pd.DataFrame(self.transactions).to_csv(tx_file, index=False)
                logger.info(f"Saved transactions to {tx_file}")
            
            self.last_update = datetime.now()
            
        except Exception as e:
            logger.error(f"Error saving results: {e}")

def main():
    tracker = StablecoinTracker()
    logger.info("Starting stablecoin tracker...")
    
    while True:
        try:
            tracker.track_stablecoins()
            time.sleep(60 * 15)  # 15 minutes between updates
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            time.sleep(60)  # Wait 1 minute before retrying on error

if __name__ == "__main__":
    main() 