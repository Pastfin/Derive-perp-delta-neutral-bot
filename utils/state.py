import time
import random
import json
import requests

from utils.initial_data_extract import extract_data
from utils.misc import create_timestamp_signature
from utils.logger import logger

API_URL = "https://api.lyra.finance/private/get_all_portfolios"


def get_account_info(data) -> dict:
    signature, timestamp = create_timestamp_signature(data['session_pk'])

    payload = {"wallet": data['derive_wallet']}
    headers = {
        "X-LyraWallet": data['derive_wallet'],
        "X-LyraTimestamp": timestamp,
        "X-LyraSignature": signature,
    }

    response = requests.post(
        API_URL,
        json=payload,
        headers=headers,
        proxies=data['proxy']
    ).json()

    for account in response.get('result', []):
        if account['subaccount_id'] == data['subacc_id']:
            return account

    raise ValueError(
        f"get_account_info: subacc_id {data['subacc_id']} из creds.txt не найден"
    )


def update_accounts_state():
    accounts = extract_data()
    all_info = []

    for account in accounts:
        info = get_account_info(account)
        result = {
            "derive_wallet": account['derive_wallet'],
            "subaccount_value": float(info['subaccount_value'])
        }
        all_info.append(result)
        time.sleep(random.uniform(0.2, 1.0))

    with open("./data/state.json", "w", encoding="utf-8") as file:
        json.dump(all_info, file, ensure_ascii=False, indent=4)

    logger.success("Информация о текущем состоянии аккаунтов обновлена в data/state.json")


if __name__ == "__main__":
    update_accounts_state()
