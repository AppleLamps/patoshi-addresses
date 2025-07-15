# Patoshi Addresses

Complete dataset of 21,953 Bitcoin blocks suspected to have been mined by Satoshi Nakamoto, with their public keys.

## Credits

Based on the work of:
- **Sergio Demian Lerner** ([@SDLerner](https://github.com/SDLerner)) - Discovered the Patoshi pattern
- **Jameson Lopp** ([@jlopp](https://github.com/jlopp)) - Curated the Patoshi blocks dataset

## Dataset

- **Blocks**: 21,953 (blocks 3-49,973)
- **Total BTC**: 1,097,650 BTC
- **Format**: CSV with columns: Block Height, Output Index, Address/Pubkey, Amount (BTC), Script Type

## Usage

```bash
# Generate the dataset
python3 extract_patoshi_addresses.py

# View the data
head patoshi_pubkeys_COMPLETE.csv
```

## Files

- `patoshi_pubkeys_COMPLETE.csv` - The complete dataset
- `extract_patoshi_addresses.py` - Script to generate the dataset from block numbers
- `README.md` - This file