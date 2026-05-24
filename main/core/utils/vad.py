import importlib
import os
import sys
from core.providers.vad.base import VADProviderBase
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()


def create_instance(class_name: str, *args, **kwargs) -> VADProviderBase:
    """
    工厂方法创建 VAD 实例（独立部署版）

    :param class_name: VAD 提供者类名（如 'SileroVAD'）
    :param args: 位置参数，第一个应为配置字典（config）
    :param kwargs: 关键字参数，可包含 'config' 键
    :return: VAD 实例
    """
    module_path = os.path.join("core", "providers", "vad", f"{class_name}.py")
    if not os.path.exists(module_path):
        raise ValueError(f"不支持的 VAD 类型: {class_name}")

    lib_name = f"core.providers.vad.{class_name}"
    if lib_name not in sys.modules:
        sys.modules[lib_name] = importlib.import_module(lib_name)

    # 获取配置字典（兼容两种调用方式）
    if "config" in kwargs:
        config = kwargs["config"]
    elif args:
        config = args[0]
    else:
        raise ValueError("需要提供配置字典")

    # 修改后的 VADProvider 只接受 config 参数
    return sys.modules[lib_name].VADProvider(config)