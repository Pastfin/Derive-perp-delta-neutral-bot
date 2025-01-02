import random
import time
import math

from utils import (
    open_long,
    open_short,
    update_accounts_state,
    check_balance,
    extract_data,
    get_instrument_ticker,
    get_account_info,
    logger
)
from utils.misc import load_json

class TradeManager:
    RANDOM_PARAMS = {
        "leverage": "leverage",
        "num_accounts": "num_of_accounts_per_trade",
        "delay_open_close": "delay_open_close_minutes",
        "delay_between_positions": "delay_between_opening_new_position_minutes",
        "net_order_value": "net_order_value_usd",
        "delay_between_opening_hedge_position_sec": "delay_between_opening_hedge_position_sec"
    }

    def __init__(self, config_path: str, state_path: str, tokens_path: str):
        self.config_path = config_path
        self.state_path = state_path
        self.tokens_path = tokens_path
        self.wallets_data = extract_data()

        self.state = load_json(state_path)
        self.config = load_json(config_path)
        self.tokens = load_json(tokens_path)

        self._update_dynamic_state()
        logger.info("TradeManager успешно инициализирован")

    def _generate_random_param(self, param_name: str, multiplier: float = 1) -> float:
        param = self.config[self.RANDOM_PARAMS[param_name]]
        return random.uniform(param['min'], param['max']) * multiplier

    def _update_dynamic_state(self):
        self.token = self._select_token()
        self.token_info = self._get_token_info(self.token)
        self.leverage = self._generate_random_param("leverage")
        self.num_accounts = round(self._generate_random_param("num_accounts"))
        self.delay_open_close = self._generate_random_param("delay_open_close", 60)
        self.delay_between_positions = self._generate_random_param(
            "delay_between_positions", 60
        )
        self.net_order_value_usd = self._generate_random_param("net_order_value")

    def _update_states(self):
        update_accounts_state()
        self.state = load_json(self.state_path)
        self._update_dynamic_state()

    def _select_token(self) -> str:
        tokens = list(self.config['pair_probability'].keys())
        probabilities = list(self.config['pair_probability'].values())
        return random.choices(tokens, probabilities, k=1)[0]

    def _get_token_info(self, token: str) -> dict:
        for t in self.tokens:
            if t['instrument_name'].startswith(token):
                return t
        raise ValueError(f"Информация о токене {token} не найдена в tokens.json")

    def _decimals_from_step(self, step: float) -> int:
        return max(0, -math.floor(math.log10(step))) if step > 0 else 16

    def _find_data_wallet_by_derive(self, wallet: str) -> dict:
        for account in self.wallets_data:
            if account.get('derive_wallet') == wallet:
                return account
        raise ValueError(f"Кошелек {wallet} не найден в creds.json")
    
    def _split_amount(self, total_amount: float, num_short_accounts: int) -> list:

        minimum_amount = self.token_info['amount_step'] # Для маркет ордеров minimum_amount не тот, который в API
        amount_step = self.token_info['amount_step']

        allowed_diff = 0  # Ноль!
        
        def round_down(value: float) -> float:
            mod_step = value % amount_step
            value -= mod_step
            return value

        dec_step = self._decimals_from_step(amount_step)
        round_decimals = dec_step

        # 0) Проверка на достаточность
        if total_amount < minimum_amount * num_short_accounts:
            raise ValueError("Недостаточная сумма для распределения по минимумам")

        # Если всего 1 аккаунт:
        if num_short_accounts == 1:
            if total_amount < minimum_amount:
                raise ValueError(f"Сумма {total_amount} < minimum_amount {minimum_amount}")
            return [round(total_amount, round_decimals)]

        # 1) Базовое равномерное распределение + шум
        parts = [minimum_amount] * num_short_accounts
        remaining = total_amount - sum(parts)
        if remaining < 0:
            raise ValueError("remaining < 0 — некорректные входные данные")

        base = remaining / num_short_accounts if remaining > 0 else 0
        raw = []
        for _ in range(num_short_accounts):
            # шум ±15%
            coeff = random.uniform(-0.15, 0.15)
            val = base + base * coeff
            if val < 0:
                val = 0
            raw.append(val)

        # Докидываем разницу в последний элемент
        diff_base = remaining - sum(raw)
        raw[-1] += diff_base

        # Прибавляем к minimum_amount
        for i in range(num_short_accounts):
            raw[i] += minimum_amount

        # Округление «вниз» для каждой части
        for i in range(num_short_accounts):
            down = round_down(raw[i])
            if down < minimum_amount:
                down = minimum_amount
            raw[i] = round(down, round_decimals)

        current_sum = round(sum(raw), round_decimals)
        diff_now = round(total_amount - current_sum, round_decimals)

        # Последний шаг по корректировки эмаунта по аккам, чтобы сумма сходилась
        is_splitted = False
        n_iterations = 10**6

        for n in range(n_iterations):
            for i in range(num_short_accounts):
                adjustment = 0
                
                if diff_now < 0:
                    adjustment = -amount_step
                elif diff_now > 0:
                    adjustment = amount_step
                
                new_val = raw[i] + adjustment
                
                if new_val + raw[i] < 0:
                    continue
                
                diff_now -= round(adjustment, round_decimals)
                raw[i] = round(new_val, round_decimals)

                if round(diff_now, round_decimals) == 0.0:
                    is_splitted = True
                    break
            if is_splitted:
                break

        if not is_splitted:
            raise ValueError(
                "Критическая ошибка: не получилось верно разбить сумму для шорта"
            )


        final_sum = round(sum(raw), round_decimals)
        final_diff = round(total_amount - final_sum, round_decimals)

        if abs(final_diff) > allowed_diff:
            raise ValueError(
                f"Критическая ошибка: итоговая сумма {final_sum} отличается от {total_amount} "
                f"на {final_diff} (> {allowed_diff})"
            )

        random.shuffle(raw)

        for x in raw:
            if x < 0:
                raise ValueError("Критическая ошибка: каким-то образом получилось отрицательное значение по amount")

        return raw
    
    def _calc_amount(self, instrument_ticker: dict) -> float:
        current_price = float(instrument_ticker['best_ask_price'])
        nominal_order_value = self.leverage * self.net_order_value_usd

        raw_amount = nominal_order_value / current_price
        amount = math.floor(raw_amount / self.token_info['amount_step']) * self.token_info['amount_step']
        amount_rounded = round(amount, self._decimals_from_step(self.token_info['amount_step']))

        if amount_rounded < self.token_info['amount_step']:
            raise ValueError(
                f"Рассчитанное количество {amount_rounded} меньше минимально допустимого {self.token_info['amount_step']}"
            )

        return amount_rounded


    def open_delta_neutral_position(self, total_amount: float, instrument_ticker: dict) -> dict:
        if total_amount <= 0:
            raise ValueError("Сумма для торговли должна быть положительной.")
        
        selected_accounts = random.sample(self.state, self.num_accounts)
        positions = {"long": {}, "short": {}}

        long_account = random.choice(selected_accounts)
        selected_accounts.remove(long_account)
        
        logger.info(f"Открытие лонга на аккаунте {long_account['derive_wallet']} на сумму {total_amount}")

        long_wallet_data = self._find_data_wallet_by_derive(long_account['derive_wallet'])
        open_long(long_wallet_data, instrument_ticker, total_amount)
        
        positions["long"][long_account['derive_wallet']] = total_amount

        time.sleep(self._generate_random_param("delay_between_opening_hedge_position_sec"))
        
        num_short_accounts = self.num_accounts - 1
        short_accounts = random.sample(selected_accounts, num_short_accounts)
        short_amounts = self._split_amount(total_amount, num_short_accounts)
        
        for account, amount in zip(short_accounts, short_amounts):
            logger.info(f"Открытие шорта на аккаунте {account['derive_wallet']} на сумму {amount}")
            short_wallet_data = self._find_data_wallet_by_derive(account['derive_wallet'])
            open_short(short_wallet_data, instrument_ticker, amount)
            positions["short"][account['derive_wallet']] = amount

            time.sleep(self._generate_random_param("delay_between_opening_hedge_position_sec"))

        return positions
    
    def close_all_positions(self, opened_positions: dict, instrument_ticker: dict):
        for wallet, amount in opened_positions['long'].items():
            wallet_data = self._find_data_wallet_by_derive(wallet)
            logger.info(f"Закрытие лонга на {self.token} с аккаунта {wallet} на сумму {amount}")
            open_short(wallet_data, instrument_ticker, amount)

        for wallet, amount in opened_positions['short'].items():
            wallet_data = self._find_data_wallet_by_derive(wallet)
            logger.info(f"Закрытие шорта на {self.token} с аккаунта {wallet} на сумму {amount}")
            open_long(wallet_data, instrument_ticker, amount)

    def close_all_positions_with_api_info(self):
        logger.info(f"Экстренное закрытие всех позиций...")
        for wallet_data in self.wallets_data:
            account_info = get_account_info(wallet_data)
            for position in account_info['positions']:
                logger.info(f"Закрытие {float(position['amount'])} {self.token} на аккаунте {wallet_data['derive_wallet']}")
                instrument_ticker = get_instrument_ticker(position['instrument_name'].replace('-PERP', ''))
                position_amount = float(position['amount'])
                if position_amount < 0:
                    open_long(wallet_data, instrument_ticker, position_amount * -1) # Потому что в респонсе отрицательное значение через API при шорте 
                else:
                    open_short(wallet_data, instrument_ticker, position_amount)
        logger.info(f"Все позиции закрыты.")


    def start(self):
        while True:
            try:
                instrument_ticker = get_instrument_ticker(self.token)
                total_amount = self._calc_amount(instrument_ticker)

                opened_positions = self.open_delta_neutral_position(
                    total_amount=total_amount,
                    instrument_ticker=instrument_ticker
                )

                time.sleep(self.delay_open_close)
                self.close_all_positions(opened_positions, instrument_ticker)
                time.sleep(self.delay_between_positions)
                self._update_states()
                check_balance(from_api=False)

            except Exception as e:
                self.close_all_positions_with_api_info()
                logger.exception(f"Произошла ошибка выполнения основной функции: {e}")
                raise ValueError(f"Произошла ошибка выполнения основной функции: {e}")
