import os
from config.config_loader import read_config, get_project_dir, load_config


default_config_file = "config.yaml"
config_file_valid = False


def check_config_file():
    global config_file_valid
    if config_file_valid:
        return
    custom_config_file = get_project_dir() + "data/.config.yaml"
    if not os.path.exists(custom_config_file):
        raise FileNotFoundError("找不到data/.config.yaml文件，请按教程确认该配置文件是否存在")
    config_file_valid = True