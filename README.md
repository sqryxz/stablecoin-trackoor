# Stablecoin Tracker

A Python script that tracks the supply and large transactions (over 1M tokens) for USDT, USDC, and BUSD across Ethereum and BSC networks.

## Features

- Tracks total supply using DefiLlama API
- Monitors large transactions (>1M tokens) on both Ethereum and BSC networks
- Updates every 15 minutes
- Displays formatted transaction information including sender, receiver, and amount

## Setup

1. Clone this repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file in the root directory with your API keys:
   ```
   ETHERSCAN_API_KEY=your_etherscan_api_key
   BSCSCAN_API_KEY=your_bscscan_api_key
   ```

## Usage

Run the script:
```bash
python stablecoin_tracker.py
```

The script will:
1. Start immediately with the first data fetch
2. Continue running and update every 15 minutes
3. Display supply and large transaction information for each stablecoin
4. Press Ctrl+C to stop the script

## API Keys

You'll need to obtain API keys from:
- [Etherscan](https://etherscan.io/apis)
- [BscScan](https://bscscan.com/apis) 