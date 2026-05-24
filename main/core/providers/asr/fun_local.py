import asyncio
import functools
from funasr import AutoModel
from .base import ASRProviderBase
from .utils import lang_tag_filter


class ASRProvider(ASRProviderBase):
    def __init__(self, config: dict):
        self.model_dir = config.get("model_dir")
        self.model = AutoModel(
            model=self.model_dir,
            vad_kwargs={"max_single_segment_time": 30000},
            disable_update=True,
            hub="hf",
        )

    async def transcribe(self, pcm_bytes: bytes, sample_rate: int = 16000) -> str:
        loop = asyncio.get_event_loop()
        # 使用 functools.partial 将参数绑定，避免关键字参数问题
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