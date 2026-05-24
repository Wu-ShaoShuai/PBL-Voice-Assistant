from abc import ABC, abstractmethod


class VADProviderBase(ABC):
    @abstractmethod
    def is_vad(self, pcm_chunk: bytes, sample_rate: int = 16000) -> bool:
        """
        检测 PCM 音频块中是否包含语音活动。
        :param pcm_chunk: 16-bit 小端 PCM 数据（单声道）
        :param sample_rate: 采样率（必须与模型训练时的采样率一致，通常为 16000）
        :return: True 表示检测到语音，False 表示静音
        """
        pass