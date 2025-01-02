import requests
import json
from utils.logger import logger


def update_tokens_info():
    with open("./config.json", "r", encoding="utf-8") as file:
        config = json.load(file)

    tokens = [x for x in config.get('pair_probability', [])]
    if not tokens:
        raise ValueError("В config.json отсутствуют токены в 'pair_probability'.")

    all_info = []
    url = "https://api.lyra.finance/public/get_ticker"
    headers = {
        "accept": "application/json",
        "content-type": "application/json"
    }

    for token in tokens:
        payload = {
            "instrument_name": f"{token}-PERP"
        }
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()  # Проверяем HTTP ошибки (4xx, 5xx)
            data = response.json()

            result = {
                "instrument_name": data['result']['instrument_name'],
                "tick_size": float(data['result']['tick_size']),
                "amount_step": float(data['result']['amount_step']),
                "minimum_amount": float(data['result']['minimum_amount'])
            }

            all_info.append(result)
            logger.info(f"Данные для токена {token} успешно обновлены.")

        except:
            raise ValueError(f"Ошибка при обработке токена {token}")

    with open("./data/tokens.json", "w", encoding="utf-8") as file:
        json.dump(all_info, file, ensure_ascii=False, indent=4)
