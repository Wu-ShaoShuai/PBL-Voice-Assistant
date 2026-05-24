from ..base import IntentProviderBase
from typing import List, Dict
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()


class IntentProvider(IntentProviderBase):
    async def detect_intent(self, dialogue_history: List[Dict[str, str]], user_text: str) -> str:
        logger.bind(tag=TAG).debug("nointent provider: always return continue_chat")
        return '{"function_call": {"name": "continue_chat"}}'