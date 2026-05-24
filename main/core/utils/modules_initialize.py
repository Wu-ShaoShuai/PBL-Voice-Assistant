from typing import Dict, Any
from config.logger import setup_logging
from core.utils import tts, llm, intent, memory, vad, asr

TAG = __name__
logger = setup_logging()


def initialize_modules(
    config: Dict[str, Any],
    init_vad: bool = False,
    init_asr: bool = False,
    init_llm: bool = False,
    init_tts: bool = False,
    init_memory: bool = False,
    init_intent: bool = False,
) -> Dict[str, Any]:
    """
    初始化所有模块组件（独立部署版，使用 xxx_provider 配置项）
    """
    modules = {}

    if init_tts:
        modules["tts"] = initialize_tts(config)
        logger.bind(tag=TAG).info(f"初始化组件: TTS 成功")

    if init_llm:
        modules["llm"] = initialize_llm(config)
        logger.bind(tag=TAG).info(f"初始化组件: LLM 成功")

    if init_intent:
        modules["intent"] = initialize_intent(config)
        logger.bind(tag=TAG).info(f"初始化组件: Intent 成功")

    if init_memory:
        modules["memory"] = initialize_memory(config)
        logger.bind(tag=TAG).info(f"初始化组件: Memory 成功")

    if init_vad:
        modules["vad"] = initialize_vad(config)
        logger.bind(tag=TAG).info(f"初始化组件: VAD 成功")

    if init_asr:
        modules["asr"] = initialize_asr(config)
        logger.bind(tag=TAG).info(f"初始化组件: ASR 成功")

    return modules


def initialize_tts(config: Dict[str, Any]):
    """初始化 TTS 模块"""
    provider_name = config.get("tts_provider")
    if not provider_name:
        raise ValueError("配置中缺少 tts_provider 字段")
    provider_config = config.get("TTS", {}).get(provider_name)
    if not provider_config:
        raise ValueError(f"未找到 TTS 提供商 {provider_name} 的配置")
    # 注意：修改后的 TTS 构造函数不再需要 delete_audio_file 参数
    return tts.create_instance(provider_name, provider_config)


def initialize_asr(config: Dict[str, Any]):
    """初始化 ASR 模块"""
    provider_name = config.get("asr_provider")
    if not provider_name:
        raise ValueError("配置中缺少 asr_provider 字段")
    provider_config = config.get("ASR", {}).get(provider_name)
    if not provider_config:
        raise ValueError(f"未找到 ASR 提供商 {provider_name} 的配置")
    return asr.create_instance(provider_name, provider_config)


def initialize_llm(config: Dict[str, Any]):
    """初始化 LLM 模块"""
    provider_name = config.get("llm_provider")
    if not provider_name:
        raise ValueError("配置中缺少 llm_provider 字段")
    provider_config = config.get("LLM", {}).get(provider_name)
    if not provider_config:
        raise ValueError(f"未找到 LLM 提供商 {provider_name} 的配置")
    return llm.create_instance(provider_name, provider_config)


def initialize_vad(config: Dict[str, Any]):
    """初始化 VAD 模块"""
    provider_name = config.get("vad_provider")
    if not provider_name:
        # 如果没有配置 VAD，可以返回 None 或抛出异常
        return None
    provider_config = config.get("VAD", {}).get(provider_name)
    if not provider_config:
        raise ValueError(f"未找到 VAD 提供商 {provider_name} 的配置")
    return vad.create_instance(provider_name, provider_config)


def initialize_memory(config: Dict[str, Any]):
    """初始化 Memory 模块"""
    provider_name = config.get("memory_provider", "nomem")
    provider_config = config.get("Memory", {}).get(provider_name, {})
    # 注意：MemoryProvider 的 __init__ 可能接受 summary_memory 参数，但独立部署不需要
    return memory.create_instance(provider_name, provider_config, None)


def initialize_intent(config: Dict[str, Any]):
    """初始化 Intent 模块"""
    provider_name = config.get("intent_provider", "nointent")
    provider_config = config.get("Intent", {}).get(provider_name, {})
    return intent.create_instance(provider_name, provider_config)