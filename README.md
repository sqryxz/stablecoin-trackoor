# Stablecoin Tracker

A Python-based monitoring tool that tracks key metrics for major stablecoins (USDT, USDC, and BUSD) across Ethereum and BSC networks. The tool provides real-time information about total supply and large transactions, helping users monitor significant stablecoin movements.

## Features

- **Multi-Chain Support**: Monitors transactions on both Ethereum and BSC networks
- **Supply Tracking**: Real-time total supply data from DefiLlama API
- **Large Transaction Monitoring**: Tracks transactions over 1M tokens
- **Automatic Updates**: Refreshes data every 15 minutes
- **Parallel Processing**: Efficiently processes multiple tokens simultaneously
- **Rate Limiting**: Smart handling of API rate limits
- **Detailed Transaction Info**: Shows timestamps, addresses, amounts, and block numbers

## Supported Stablecoins

- **USDT (Tether)**
  - Ethereum: `0xdAC17F958D2ee523a2206206994597C13D831ec7`
  - BSC: `0x55d398326f99059fF775485246999027B3197955`

- **USDC (USD Coin)**
  - Ethereum: `0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48`
  - BSC: `0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d`

- **BUSD (Binance USD)**
  - Ethereum: `0x4Fabb145d64652a948d72533023f6E7A623C7C53`
  - BSC: `0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56`

## Prerequisites

- Python 3.7 or higher
- Active API keys for Etherscan and BscScan

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/sqryxz/stablecoin-trackoor.git
   cd stablecoin-trackoor
   ```

2. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the project root:
   ```env
   ETHERSCAN_API_KEY=your_etherscan_api_key
   BSCSCAN_API_KEY=your_bscscan_api_key
   ```

## Usage

Run the script:
```bash
python stablecoin_tracker.py
```

The script will:
1. Start monitoring immediately
2. Display initial data for all supported stablecoins
3. Update every 15 minutes automatically
4. Show large transactions (>1M tokens) with detailed information
5. Continue running until interrupted (Ctrl+C)

## Sample Output

```
====================================================================================================
Stablecoin Metrics Report - 2025-03-07 10:00:00
====================================================================================================

USDT:
Total Supply: 143,171,664,723.56

ETHEREUM Large Transactions (>1M):
====================================================================================================
Time: 2025-03-07 09:58:23 | Chain: ETHEREUM
Amount: 5,000,000.00
From: 0x7ffbafdc1e4f0a4b97130b075fb4a25f807a1807
To: 0xffe15ff598e719d29dfe5e1d60be1a5521a779ae
Tx Hash: 0x765b8761173d4b63787ec6b1dbd7151358ebcd3e2f17c0ff2f892c853f19da5d
Block: 19475839
====================================================================================================
```

## API Sources

- **DefiLlama**: Used for total supply data
  - Documentation: https://defillama.com/docs/api
  - No API key required

- **Etherscan**: Used for Ethereum transaction data
  - Get API key: https://etherscan.io/apis
  - Documentation: https://docs.etherscan.io

- **BscScan**: Used for BSC transaction data
  - Get API key: https://bscscan.com/apis
  - Documentation: https://docs.bscscan.com

## Rate Limits

- **Etherscan**: 5 calls per second (free tier)
- **BscScan**: 5 calls per second (free tier)
- **DefiLlama**: No strict rate limit, but please be considerate

The script implements automatic rate limiting and error handling to stay within these limits.

## Error Handling

The script includes robust error handling for:
- API rate limits
- Network timeouts
- Invalid responses
- Missing data

Errors are logged to the console with relevant details for troubleshooting.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is open source and available under the MIT License.

## Disclaimer

This tool is for informational purposes only. Please ensure you comply with all API terms of service and applicable regulations when using this tool.

## Support

If you encounter any issues or have questions, please:
1. Check the existing issues in the GitHub repository
2. Create a new issue with detailed information about your problem
3. Include relevant error messages and your environment details

## Code Examples

### Fetching Large Transactions
```python
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
        f"&offset=20"  # Transactions per page
        f"&sort=desc"
        f"&apikey={api_key}"
    )
    
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if data.get('message') == 'OK' and data.get('status') == '1':
            return data['result']
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
    
    # Filter for transactions > 1M tokens
    large_txs = [
        tx for tx in all_transactions 
        if float(tx['value']) / (10 ** int(tx['tokenDecimal'])) > 1_000_000
    ]
    
    # Sort by value in descending order
    large_txs.sort(
        key=lambda x: float(x['value']) / (10 ** int(x['tokenDecimal'])), 
        reverse=True
    )
    
    return large_txs[:10]  # Return top 10 largest transactions
```

### Fetching Total Supply
```python
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
        return 0
```

### Transaction Formatting
```python
def format_large_transaction(tx, chain):
    """Format transaction data for display"""
    value = float(tx['value']) / (10 ** int(tx['tokenDecimal']))
    timestamp = datetime.fromtimestamp(int(tx['timeStamp']))
    
    return (
        f"{'=' * 100}\n"
        f"Time: {timestamp.strftime('%Y-%m-%d %H:%M:%S')} | Chain: {chain.upper()}\n"
        f"Amount: {value:,.2f}\n"
        f"From: {tx['from']}\n"
        f"To: {tx['to']}\n"
        f"Tx Hash: {tx['hash']}\n"
        f"Block: {tx['blockNumber']}\n"
        f"{'=' * 100}"
    )
```

These code snippets demonstrate:
- How to fetch and filter large transactions from blockchain explorers
- How to retrieve total supply data from DefiLlama
- How to format transaction data for display
- Error handling and rate limiting implementation
- Parallel processing of multiple tokens 