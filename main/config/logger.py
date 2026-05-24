import os
import sys
from loguru import logger
from config.config_loader import load_config
from config.settings import check_config_file
from datetime import datetime

SERVER_VERSION = "0.9.3"
_logger_initialized = False


def formatter(record):
    record["extra"].setdefault("tag", record["name"])
    return record["message"]


def setup_logging():
    check_config_file()
    """从配置文件中读取日志配置，并设置日志输出格式和级别"""
    config = load_config()
    log_config = config["log"]
    global _logger_initialized

    # 第一次初始化时配置日志
    if not _logger_initialized:
        # 移除 selected_module 相关的 extra 设置，改为固定服务标识（可选）
        # 如果不需要任何 extra，可以删除整个 configure 调用
        logger.configure(
            extra={
                "service": "voice_qa",   # 固定标识，用于区分服务（可选）
            }
        )

        # 修改日志格式：去掉 {version}_{extra[selected_module]} 部分
        # 改为使用固定的服务标识或直接去掉
        log_format = log_config.get(
            "log_format",
            # 原格式: "<green>{time:YYMMDD HH:mm:ss}</green>[{version}_{extra[selected_module]}][<light-blue>{extra[tag]}</light-blue>]-<level>{level}</level>-<light-green>{message}</light-green>"
            # 新格式: 删除中间的大括号部分，只保留 version 或什么都不加
            "<green>{time:YYMMDD HH:mm:ss}</green>[{version}][<light-blue>{extra[tag]}</light-blue>]-<level>{level}</level>-<light-green>{message}</light-green>",
        )
        log_format_file = log_config.get(
            "log_format_file",
            # 原格式: "{time:YYYY-MM-DD HH:mm:ss} - {version}_{extra[selected_module]} - {name} - {level} - {extra[tag]} - {message}"
            # 新格式: 删除 _{extra[selected_module]}
            "{time:YYYY-MM-DD HH:mm:ss} - {version} - {name} - {level} - {extra[tag]} - {message}",
        )
        # 替换版本号
        log_format = log_format.replace("{version}", SERVER_VERSION)
        log_format_file = log_format_file.replace("{version}", SERVER_VERSION)

        log_level = log_config.get("log_level", "INFO")
        log_dir = log_config.get("log_dir", "tmp")
        log_file = log_config.get("log_file", "server.log")
        data_dir = log_config.get("data_dir", "data")

        os.makedirs(log_dir, exist_ok=True)
        os.makedirs(data_dir, exist_ok=True)

        logger.remove()
        logger.add(sys.stdout, format=log_format, level=log_level, filter=formatter)
        logger.add(
            log_file_path := os.path.join(log_dir, log_file),
            format=log_format_file,
            level=log_level,
            filter=formatter,
            rotation="10 MB",
            retention="30 days",
            compression=None,
            encoding="utf-8",
            enqueue=True,
            backtrace=True,
            diagnose=True,
        )
        _logger_initialized = True

    return logger

