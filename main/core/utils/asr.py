import importlib
import sys
from typing import Optional
from core.providers.asr.base import ASRProviderBase
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()

def create_instance(class_name: str, *args, **kwargs) -> Optional[ASRProviderBase]:
    """工厂方法创建 ASR 实例，直接尝试导入模块"""
    try:
        lib_name = f'core.providers.asr.{class_name}'
        if lib_name not in sys.modules:
            module = importlib.import_module(lib_name)
        else:
            module = sys.modules[lib_name]
        return module.ASRProvider(*args, **kwargs)
    except ImportError as e:
        logger.bind(tag=TAG).error(f"无法导入 ASR 模块 {class_name}: {e}")
        raise ValueError(f"不支持的 ASR 类型: {class_name}")