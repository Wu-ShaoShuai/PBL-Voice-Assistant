import re
from abc import ABC, abstractmethod
from config.logger import setup_logging
from core.utils.tts import MarkdownCleaner

TAG = __name__
logger = setup_logging()


class TTSProviderBase(ABC):
    def __init__(self, config: dict):
        """
        基类初始化，处理替换词（correct_words）
        """
        # 加载替换词，用于一次性正则替换
        raw_words = config.get("correct_words", [])
        self.correct_words = {}
        for item in raw_words:
            parts = item.split("|", 1)
            if len(parts) == 2:
                self.correct_words[parts[0]] = parts[1]
        # 构建正则表达式，使用最长匹配优先
        if self.correct_words:
            sorted_keys = sorted(self.correct_words.keys(), key=len, reverse=True)
            pattern_str = '|'.join(re.escape(k) for k in sorted_keys)
            self._correct_words_pattern = re.compile(pattern_str)
        else:
            self._correct_words_pattern = None

    def _clean_text(self, text: str) -> str:
        """
        清理文本：去除 Markdown 标记，应用替换词
        """
        text = MarkdownCleaner.clean_markdown(text)
        if self._correct_words_pattern:
            text = self._correct_words_pattern.sub(
                lambda m: self.correct_words[m.group(0)], text
            )
        return text

    @abstractmethod
    async def synthesize(self, text: str) -> bytes:
        """
        合成语音，返回音频二进制数据（格式由具体实现决定，如 wav/mp3/pcm）。
        """
        pass