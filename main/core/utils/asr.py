import importlib
import os
import sys
from typing import Optional
from core.providers.asr.base import ASRProviderBase
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()


def create_instance(class_name: str, *args, **kwargs) -> Optional[ASRProviderBase]:
    """工厂方法创建 ASR 实例"""
    module_path = os.path.join('core', 'providers', 'asr', f'{class_name}.py')
    if os.path.exists(module_path):
        lib_name = f'core.providers.asr.{class_name}'
        if lib_name not in sys.modules:
            sys.modules[lib_name] = importlib.import_module(lib_name)
        return sys.modules[lib_name].ASRProvider(*args, **kwargs)
    raise ValueError(f"不支持的 ASR 类型: {class_name}")