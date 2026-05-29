import os
import asyncio
import functools
from funasr import AutoModel
from .base import ASRProviderBase
from .utils import lang_tag_filter
from config.logger import setup_logging

logger = setup_logging()
TAG = __name__

class ASRProvider(ASRProviderBase):
    def __init__(self, config: dict):
        model_dir = config.get("model_dir")
        if not model_dir:
            raise ValueError("配置中缺少 model_dir 字段")
        # 转换为绝对路径，避免工作目录问题
        abs_model_dir = os.path.abspath(model_dir)
        logger.bind(tag=TAG).info(f"FunASR 模型目录: {abs_model_dir}")
        if not os.path.exists(abs_model_dir):
            raise FileNotFoundError(f"模型目录不存在: {abs_model_dir}")
        # 列出目录内容，辅助诊断
        try:
            files = os.listdir(abs_model_dir)
            logger.bind(tag=TAG).info(f"模型目录内容: {files[:10]}")  # 只显示前10个
        except Exception as e:
            logger.bind(tag=TAG).warning(f"无法列出目录内容: {e}")

        self.model = AutoModel(
            model=abs_model_dir,
            vad_kwargs={"max_single_segment_time": 30000},
            disable_update=True,   # 禁止自动更新，避免网络请求
            hub="ms",              # 使用 ModelScope 源
        )
        logger.bind(tag=TAG).info("FunASR 模型加载成功")

    async def transcribe(self, pcm_bytes: bytes, sample_rate: int = 16000) -> str:
        loop = asyncio.get_event_loop()
        # 使用 functools.partial 绑定所有参数，避免关键字参数传递给 run_in_executor
        func = functools.partial(
            self.model.generate,
            pcm_bytes,
            cache={},
            language="auto",
            use_itn=True,
            batch_size_s=60,
        )
        result = await loop.run_in_executor(None, func)
        text = lang_tag_filter(result[0]["text"])
        if isinstance(text, dict):
            return text.get("content", "")
        return text

    async def close(self):
        """释放资源"""
        pass