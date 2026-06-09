from pathlib import Path

from disco.util.config import Config

config_path = Path('config/config.yaml')

bot_config = None

def load_config():
    global bot_config
    if not config_path.exists():
        return False

    bot_config = Config.from_file("config/config.yaml")
    return True

def is_config_loaded():
    global bot_config
    return bot_config is not None