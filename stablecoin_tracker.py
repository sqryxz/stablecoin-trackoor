import os
import time
import schedule
import requests
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Keys
ETHERSCAN_API_KEY = os.getenv('ETHERSCAN_API_KEY')
BSCSCAN_API_KEY = os.getenv('BSCSCAN_API_KEY')

# Token addresses
TOKENS = {
    'USDT': {
        'ethereum': '0xdAC17F958D2ee523a2206206994597C13D831ec7',
        'bsc': '0x55d398326f99059fF775485246999027B3197955'
    },
    'USDC': {
        'ethereum': '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48',
        'bsc': '0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d'
    },
    'BUSD': {
        'ethereum': '0x4Fabb145d64652a948d72533023f6E7A623C7C53',
        'bsc': '0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56'
    }
}

def get_supply_from_defillama(token):
    """Get token supply from DefiLlama API"""
    url = f"https://api.llama.fi/token/{token}"
    try:
        response = requests.get(url)
        data = response.json()
        return data.get('supply', 0)
    except Exception as e:
        print(f"Error fetching supply for {token}: {e}")
        return 0

def get_large_transactions(chain, token_address):
    """Get large transactions from Etherscan/BscScan"""
    api_key = ETHERSCAN_API_KEY if chain == 'ethereum' else BSCSCAN_API_KEY
    base_url = 'https://api.etherscan.io/api' if chain == 'ethereum' else 'https://api.bscscan.com/api'
    
    url = f"{base_url}?module=account&action=tokentx&contractaddress={token_address}&sort=desc&apikey={api_key}"
    try:
        response = requests.get(url)
        data = response.json()
        if data['status'] == '1':
            return data['result']
        return []
    except Exception as e:
        print(f"Error fetching transactions for {token_address}: {e}")
        return []

def format_large_transaction(tx):
    """Format transaction data for display"""
    value = float(tx['value']) / (10 ** int(tx['tokenDecimal']))
    return f"From: {tx['from'][:8]}...{tx['from'][-6:]} | To: {tx['to'][:8]}...{tx['to'][-6:]} | Value: {value:,.2f}"

def track_stablecoins():
    """Main function to track stablecoin metrics"""
    print(f"\n=== Stablecoin Metrics Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n")
    
    for token, addresses in TOKENS.items():
        print(f"\n{token}:")
        
        # Get total supply
        supply = get_supply_from_defillama(token)
        print(f"Total Supply: {supply:,.2f}")
        
        # Get large transactions for each chain
        for chain, address in addresses.items():
            print(f"\n{chain.upper()} Large Transactions:")
            transactions = get_large_transactions(chain, address)
            large_txs = [tx for tx in transactions if float(tx['value']) / (10 ** int(tx['tokenDecimal'])) > 1_000_000]
            
            if large_txs:
                for tx in large_txs[:5]:  # Show top 5 largest transactions
                    print(format_large_transaction(tx))
            else:
                print("No large transactions found in the last 15 minutes")

def main():
    print("Starting Stablecoin Tracker...")
    print("Press Ctrl+C to stop")
    
    # Run immediately and then every 15 minutes
    track_stablecoins()
    schedule.every(15).minutes.do(track_stablecoins)
    
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    main() 