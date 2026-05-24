from abc import ABC, abstractmethod
from typing import List, Dict, Any
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()


class IntentProviderBase(ABC):
    def __init__(self, config: dict):
        self.config = config
        self.llm = None

    def set_llm(self, llm):
        self.llm = llm
        model_name = getattr(llm, "model_name", str(llm.__class__.__name__))
        logger.bind(tag=TAG).info(f"意图识别设置LLM: {model_name}")

    @abstractmethod
    async def detect_intent(self, dialogue_history: List[Dict[str, str]], user_text: str) -> str:
        """
        检测用户最后一句话的意图
        Args:
            dialogue_history: 对话历史记录列表，每条记录包含 role 和 content
            user_text: 当前用户输入
        Returns:
            识别结果，JSON 字符串格式
        """
        pass