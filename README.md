# Derive Perp Delta Neutral Bot

https://www.derive.xyz/invite/55NI6

## Description

Automated delta-neutral trading bot for the Derive platform.  
Manages positions using EOA wallets, ensuring security and parameter randomization to minimize risks.

## Features

- Delta-neutral trading strategy with support for ETH, BTC pairs.  
- Flexible configuration via `config.json` and `creds.txt`.  
- Multi-level safety checks before opening positions.  
- Automatic position closure in case of errors.  
- Support for multi-process execution for scalability.

## Requirements

- Python 3.11.5  
- Dependencies listed in `requirements.txt`

## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/Pastfin/Derive-perp-delta-neutral-bot.git
   ```

2. Install the required dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Configure the bot:

- Fill in creds.txt with account details.
- Adjust trading parameters in config.json.

## Usage

- Run the script:

    ```bash
    python3 main.py
    ```
- Close all positions:
    ```bash
    python3 close_all_positions.py
    ```

## Documentation

For detailed instructions, visit: [Full Documentation](https://teletype.in/@pastfin/hlTslS6MvaV)
