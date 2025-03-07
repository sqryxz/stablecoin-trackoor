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