import os
import time
import schedule
import requests
from datetime import datetime
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed

# Load environment variables
load_dotenv()

# API Keys
ETHERSCAN_API_KEY = os.getenv('ETHERSCAN_API_KEY')
BSCSCAN_API_KEY = os.getenv('BSCSCAN_API_KEY')

# Token addresses and IDs
TOKENS = {
    'USDT': {
        'ethereum': '0xdAC17F958D2ee523a2206206994597C13D831ec7',
        'bsc': '0x55d398326f99059fF775485246999027B3197955',
        'defillama_id': 'USDT'
    },
    'USDC': {
        'ethereum': '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48',
        'bsc': '0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d',
        'defillama_id': 'USDC'
    },
    'BUSD': {
        'ethereum': '0x4Fabb145d64652a948d72533023f6E7A623C7C53',
        'bsc': '0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56',
        'defillama_id': 'BUSD'
    }
}

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
    
    # Get timestamp from 15 minutes ago
    fifteen_mins_ago = int(time.time()) - (15 * 60)
    
    url = (
        f"{base_url}?module=account&action=tokentx"
        f"&contractaddress={token_address}"
        f"&starttime={fifteen_mins_ago}"
        f"&page={page}"
        f"&offset=20"  # Further reduced number of transactions per page
        f"&sort=desc"
        f"&apikey={api_key}"
    )
    
    # Add longer initial delay for BSC
    time.sleep(2 if chain == 'bsc' else 1)
    
    try:
        response = requests.get(url, timeout=10)  # Add timeout
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
    for page in range(1, 3):  # Reduced to 2 pages
        transactions = get_transactions_page(chain, token_address, page)
        if transactions:
            all_transactions.extend(transactions)
    
    print(f"Found {len(all_transactions)} total transactions for {chain}")
    return all_transactions

def format_large_transaction(tx, chain):
    """Format transaction data for display"""
    value = float(tx['value']) / (10 ** int(tx['tokenDecimal']))
    timestamp = datetime.fromtimestamp(int(tx['timeStamp']))
    
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

def track_stablecoins():
    """Main function to track stablecoin metrics"""
    print(f"\n{'=' * 100}")
    print(f"Stablecoin Metrics Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'=' * 100}\n")
    
    # Process all tokens in parallel
    with ThreadPoolExecutor(max_workers=len(TOKENS)) as executor:
        futures = []
        for token_name, token_info in TOKENS.items():
            futures.append(executor.submit(process_token, token_name, token_info))
        
        # Wait for all tokens to be processed
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                print(f"Error processing token: {str(e)}")

def process_token(token_name, token_info):
    """Process a single token's data"""
    print(f"\n{token_name}:")
    
    # Get total supply
    supply = get_supply_from_defillama(token_info)
    print(f"Total Supply: {supply:,.2f}")
    
    # Get large transactions for each chain
    for chain in ['ethereum', 'bsc']:
        address = token_info[chain]
        print(f"\n{chain.upper()} Large Transactions (>1M):")
        transactions = get_large_transactions(chain, address)
        large_txs = [tx for tx in transactions if float(tx['value']) / (10 ** int(tx['tokenDecimal'])) > 1_000_000]
        
        if large_txs:
            # Sort transactions by value in descending order
            large_txs.sort(key=lambda x: float(x['value']) / (10 ** int(x['tokenDecimal'])), reverse=True)
            for tx in large_txs[:10]:  # Show top 10 largest transactions
                print(format_large_transaction(tx, chain))
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