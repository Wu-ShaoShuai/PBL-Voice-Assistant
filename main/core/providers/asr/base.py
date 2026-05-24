import os
import tempfile
import wave
from abc import ABC, abstractmethod
from typing import Optional


class ASRProviderBase(ABC):
    """ASR 抽象基类，独立部署版，只提供 transcribe 方法"""

    @abstractmethod
    async def transcribe(self, pcm_bytes: bytes, sample_rate: int = 16000) -> str:
        """
        将 PCM 音频数据转换为文本。
        :param pcm_bytes: 16kHz 单声道 16bit PCM 数据
        :param sample_rate: 采样率，默认 16000
        :return: 识别出的文本，出错返回空字符串
        """
        pass

    @staticmethod
    def save_pcm_to_temp_wav(pcm_bytes: bytes, sample_rate: int = 16000) -> str:
        """将 PCM 数据保存为临时 WAV 文件，返回文件路径"""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = f.name
        with wave.open(temp_path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(pcm_bytes)
        return temp_path

    @staticmethod
    def cleanup_temp_file(file_path: str):
        """删除临时文件"""
        if file_path and os.path.exists(file_path):
            os.unlink(file_path)