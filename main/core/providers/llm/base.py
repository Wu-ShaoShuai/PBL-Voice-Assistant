from abc import ABC, abstractmethod
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()

class LLMProviderBase(ABC):
    @abstractmethod
    def response(self, dialogue, session_id=None, **kwargs):
        """LLM response generator (streaming)
        
        Args:
            dialogue: list of messages (each with role, content)
            session_id: optional, for backward compatibility
            **kwargs: additional parameters (max_tokens, temperature, etc.)
        Yields:
            str: text chunks
        """
        pass

    def response_no_stream(self, system_prompt, user_prompt, **kwargs):
        """Non-streaming helper"""
        dialogue = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        result = ""
        for part in self.response(dialogue, **kwargs):
            result += part
        return result
    
    def response_with_functions(self, dialogue, functions=None, session_id=None, **kwargs):
        """
        Default implementation for function calling (streaming)
        Returns: generator that yields (text_token, tool_calls_or_None)
        """
        # For providers that don't support functions, just return regular response
        for token in self.response(dialogue, session_id, **kwargs):
            yield token, None