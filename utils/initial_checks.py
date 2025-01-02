import requests

from utils.state import get_account_info
from utils.initial_data_extract import extract_data
from utils.tokens import update_tokens_info
from utils.misc import load_json
from utils.logger import logger


def validate_pair_probability(pair_probability: dict):
    if not isinstance(pair_probability, dict):
        raise ValueError("'pair_probability' должно быть словарем.")

    if not all(
        isinstance(key, str) and isinstance(value, (float, int))
        for key, value in pair_probability.items()
    ):
        raise ValueError("Все ключи в 'pair_probability' должны быть строками, а значения — числами.")

    if abs(sum(pair_probability.values()) - 1) > 0.001:
        raise ValueError("Сумма значений в 'pair_probability' должна быть равна 1.")


def validate_numeric_ranges(config: dict):
    numeric_ranges = [
        ("net_order_value_usd", 0, float('inf')),
        ("leverage", 1, float('inf')),
        ("num_of_accounts_per_trade", 1, float('inf')),
        ("delay_open_close_minutes", 0, float('inf')),
        ("delay_between_opening_new_position_minutes", 0, float('inf')),
        ("delay_between_opening_hedge_position_sec", 0, float('inf')),
    ]

    for key, min_value, max_value in numeric_ranges:
        value = config.get(key, {})
        if not isinstance(value, dict):
            raise ValueError(f"'{key}' должно быть словарем с 'min' и 'max'.")

        min_val, max_val = value.get('min'), value.get('max')
        if not isinstance(min_val, (int, float)) or not isinstance(max_val, (int, float)):
            raise ValueError(f"'{key}' должно содержать числовые значения 'min' и 'max'.")

        if min_val > max_val:
            raise ValueError(f"'{key}': 'min' не может быть больше 'max'.")

        if min_val < min_value or max_val > max_value:
            raise ValueError(f"'{key}' должно находиться в диапазоне от {min_value} до {max_value}.")


def validate_tokens(config):
    tokens = [x for x in config.get('pair_probability', [])]
    for token in tokens:
        if token not in ['ETH', 'BTC']:
            raise ValueError(f"Токен {token} не поддерживается, не тестировал его")


def check_config():
    config = load_json("./config.json")

    validate_pair_probability(config.get("pair_probability", {}))
    validate_numeric_ranges(config)
    validate_tokens(config)

    logger.success("✅ config.json")


def parse_creds(file_path: str) -> list:
    with open(file_path, 'r') as file:
        return [line.split(':') for line in file.read().splitlines() if line]


def validate_proxy(proxy: dict):
    try:
        response = requests.get("https://example.com/", proxies=proxy, timeout=5)
        if response.status_code != 200:
            raise ValueError(f"Неверный статус код с прокси {response.status_code}: {proxy['http']}")
    except requests.RequestException:
        raise ValueError(f"Нерабочие прокси: {proxy['http']}")


def check_creds():
    creds = parse_creds('./creds.txt')

    if (len(creds) < 2):
        raise ValueError("Не может быть одного аккаунта, минимум 2. Исправьте creds.txt")

    for cred in creds:
        if len(cred) != 7:
            raise ValueError(f"Строка '{':'.join(cred)}' неправильная.")

        proxy = {
            'http': f'http://{cred[5]}:{cred[6]}@{cred[3]}:{cred[4]}',
            'https': f'http://{cred[5]}:{cred[6]}@{cred[3]}:{cred[4]}'
        }
        validate_proxy(proxy)

    config = load_json("./config.json")

    if config['num_of_accounts_per_trade']['max'] > len(creds):
        raise ValueError(
            f"Кол-во аккаунтов в creds.txt: {len(creds)}. В config.json макс. аккаунтов: {config['num_of_accounts_per_trade']['max']}"
        )
    if config['num_of_accounts_per_trade']['min'] <= 1:
        raise ValueError("Для нейтральной позиции должно быть минимум 2 аккаунта.")

    logger.success("✅ creds.txt (n args)")
    logger.success("✅ proxy")


def calculate_max_nominal_value(config: dict) -> float:
    return config['leverage']['max'] * config['net_order_value_usd']['max']


def validate_account_balance(account_info: dict, derive_wallet: str, max_nominal_value: float, max_leverage: float):
    account_balance = round(float(account_info['subaccount_value']), 3)
    logger.info(f"Баланс для derive wallet {derive_wallet}: {account_balance}$")

    current_max_leverage = round(max_nominal_value / account_balance, 2)
    if current_max_leverage > max_leverage:
        raise ValueError(
            f"Низкий баланс для макс. плеча {max_leverage} и макс. номинальной ставки {max_nominal_value}$ "
            f"для derive wallet {derive_wallet}, при таких параметрах макс плечо: {current_max_leverage}"
        )


def check_balance(from_api: bool):
    data_list = extract_data()
    config = load_json("./config.json")

    max_leverage = config['leverage']['max']
    max_nominal_value = calculate_max_nominal_value(config)

    for data in data_list:
        try:
            if (from_api):
                account_info = get_account_info(data)
            else:
                current_state = load_json("./data/state.json")
                matching_account = next(
                    (item for item in current_state if item['derive_wallet'] == data['derive_wallet']), 
                    None
                )
                if matching_account:
                    account_info = matching_account
                else:
                    raise ValueError(f"Не удалось найти совпадение для derive_wallet в ./data/state.json: {data['derive_wallet']}")
        except Exception:
            raise ValueError(f"Неправильные данные от аккаунта для: {data}")

        validate_account_balance(account_info, data['derive_wallet'], max_nominal_value, max_leverage)


def start_checks():
    logger.info("Проверка config.json")
    check_config()
    logger.info("Проверка creds.txt и прокси")
    check_creds()
    logger.info("Проверка данных от аккаунтов и баланса")
    check_balance(from_api=True)
    logger.success("✅ Данные от аккаунтов в creds.txt правильные")
    logger.info("Обновление данных о выбранных токенах")
    update_tokens_info()
    logger.success("✅ Данные о выбранных токенах обновлены")
    logger.success("✅ Все проверки пройдены")
