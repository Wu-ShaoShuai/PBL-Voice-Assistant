from .base import TTSProviderBase
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()


class DefaultTTS(TTSProviderBase):
    def __init__(self, config):
        super().__init__(config)

    async def synthesize(self, text: str) -> bytes:
        raise NotImplementedError("未配置有效的 TTS 服务，请检查配置文件")