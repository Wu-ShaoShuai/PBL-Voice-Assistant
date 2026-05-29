import edge_tts
from .base import TTSProviderBase


class TTSProvider(TTSProviderBase):
    def __init__(self, config):
        super().__init__(config)
        if config.get("private_voice"):
            self.voice = config.get("private_voice")
        else:
            self.voice = config.get("voice")
        self.audio_file_type = config.get("format", "mp3")  # 保留以备参考，但不强制使用

    async def synthesize(self, text: str) -> bytes:
        """合成语音，返回音频二进制数据（MP3 格式）"""
        text = self._clean_text(text)

        communicate = edge_tts.Communicate(text, voice=self.voice)
        audio_bytes = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_bytes += chunk["data"]
        return audio_bytes
    
    async def close(self):
        """释放资源"""
    pass