from core import TradeManager
from utils import start_checks, update_accounts_state


if __name__ == "__main__":
    start_checks()
    update_accounts_state()

    manager = TradeManager(config_path="./config.json", state_path="./data/state.json", tokens_path="./data/tokens.json")
    manager.start()
