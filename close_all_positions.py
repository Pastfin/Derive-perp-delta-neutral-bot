from core import TradeManager

if __name__ == "__main__":
    manager = TradeManager(config_path="./config.json", state_path="./data/state.json", tokens_path="./data/tokens.json")
    manager.close_all_positions_with_api_info()