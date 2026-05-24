import os
import sys
import importlib
from config.logger import setup_logging

logger = setup_logging()


def create_instance(class_name, *args, **kwargs):
    """创建意图识别实例的工厂方法"""
    module_path = os.path.join('core', 'providers', 'intent', class_name, f'{class_name}.py')
    if os.path.exists(module_path):
        lib_name = f'core.providers.intent.{class_name}.{class_name}'
        if lib_name not in sys.modules:
            sys.modules[lib_name] = importlib.import_module(lib_name)
        return sys.modules[lib_name].IntentProvider(*args, **kwargs)

    raise ValueError(f"不支持的 intent 类型: {class_name}")