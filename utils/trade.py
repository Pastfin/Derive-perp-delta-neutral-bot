from decimal import Decimal
from eth_account.messages import encode_defunct
from web3 import Web3
import requests

from lyra_v2_action_signing import SignedAction, TradeModuleData, utils
from utils.misc import create_timestamp_signature


DOMAIN_SEPARATOR = "0xd96e5f90797da7ec8dc4e276260c7f3f87fedf68775fbe1ef116e996fc60441b"
ACTION_TYPEHASH = "0x4d7a9f27c403ff9c0f19bce61d76d82f9aa29f8d6d4b0c5474607d9770d1af17"
TRADE_MODULE_ADDRESS = "0xB8D20c2B7a1Ad2EE33Bc50eF10876eD3035b5e7b"
ORDER_ENDPOINT = "https://api.lyra.finance/private/order"
TICKER_ENDPOINT = "https://api.lyra.finance/public/get_ticker"


def get_instrument_ticker(token):
    response = requests.post(
        TICKER_ENDPOINT,
        json= { "instrument_name": f"{token.upper()}-PERP" },
        headers={
            "accept": "application/json",
            "content-type": "application/json"
        }
        # proxies=proxy
    )
    return response.json()["result"]


def generate_signature(wallet, timestamp):
    lyra_message = encode_defunct(text=timestamp)
    return wallet.sign_message(lyra_message).signature.hex()


def create_action(wallet_data, eoa_wallet, instrument_ticker, amount, limit_price, is_bid):
    return SignedAction(
        subaccount_id=wallet_data['subacc_id'],
        owner=wallet_data['derive_wallet'],
        signer=eoa_wallet.address,
        signature_expiry_sec=utils.MAX_INT_32,
        nonce=utils.get_action_nonce(),
        module_address=TRADE_MODULE_ADDRESS,
        module_data=TradeModuleData(
            asset_address=instrument_ticker["base_asset_address"],
            sub_id=int(instrument_ticker["base_asset_sub_id"]),
            limit_price=Decimal(str(limit_price)),
            amount=Decimal(str(amount)),
            max_fee=Decimal("10000"),
            recipient_id=wallet_data['subacc_id'],
            is_bid=is_bid,
        ),
        DOMAIN_SEPARATOR=DOMAIN_SEPARATOR,
        ACTION_TYPEHASH=ACTION_TYPEHASH,
    )


def send_order(wallet_data, instrument_ticker, direction, action, headers):
    payload = {
        "instrument_name": instrument_ticker["instrument_name"],
        "direction": direction,
        "order_type": "market",
        "time_in_force": "gtc",
        **action.to_json(),
    }

    response = requests.post(
        ORDER_ENDPOINT,
        json=payload,
        headers=headers,
        proxies=wallet_data['proxy']
    )
    return response


def open_order(wallet_data, instrument_ticker, amount, direction):
    eoa_wallet = Web3().eth.account.from_key(wallet_data['session_pk'])
    lyra_signature, timestamp_ms = create_timestamp_signature(wallet_data['session_pk'])

    limit_price = instrument_ticker['max_price'] if direction == "long" else instrument_ticker['min_price']
    is_bid = direction == "long"

    action = create_action(wallet_data, eoa_wallet, instrument_ticker, amount, limit_price, is_bid)
    action.sign(wallet_data['session_pk'])

    headers = {
        "X-LyraWallet": wallet_data['derive_wallet'],
        "X-LyraTimestamp": timestamp_ms,
        "X-LyraSignature": lyra_signature
    }

    response = send_order(wallet_data, instrument_ticker, "buy" if is_bid else "sell", action, headers)
    return response


def open_long(wallet_data, instrument_ticker, amount):
    # return
    return open_order(wallet_data, instrument_ticker, amount, "long")


def open_short(wallet_data, instrument_ticker, amount):
    # return
    return open_order(wallet_data, instrument_ticker, amount, "short")
