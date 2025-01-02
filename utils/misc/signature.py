from eth_account.messages import encode_defunct
from web3 import Web3
import time

def create_timestamp_signature(pk):
    eoa_wallet = Web3().eth.account.from_key(pk)
    timestamp = str(int(time.time() * 1000))
    message = encode_defunct(text=timestamp)
    signature = eoa_wallet.sign_message(message).signature.hex()
    return signature, timestamp