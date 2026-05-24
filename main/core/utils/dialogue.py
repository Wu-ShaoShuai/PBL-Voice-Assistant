import re
from typing import List, Dict, Optional
from datetime import datetime


class Message:
    def __init__(self, role: str, content: str = None):
        self.role = role
        self.content = content


class Dialogue:
    def __init__(self):
        self.dialogue: List[Message] = []

    def put(self, message: Message):
        self.dialogue.append(message)

    def update_system_message(self, new_content: str):
        """更新或添加系统消息"""
        system_msg = next((msg for msg in self.dialogue if msg.role == "system"), None)
        if system_msg:
            system_msg.content = new_content
        else:
            self.put(Message(role="system", content=new_content))

    def get_llm_dialogue(self) -> List[Dict[str, str]]:
        """获取不带记忆的 LLM 对话格式（保留兼容性）"""
        return self._build_dialogue(None)

    def get_llm_dialogue_with_memory(self, memory_str: Optional[str] = None) -> List[Dict[str, str]]:
        """获取带记忆增强的 LLM 对话格式"""
        return self._build_dialogue(memory_str)

    def _build_dialogue(self, memory_str: Optional[str]) -> List[Dict[str, str]]:
        dialogue = []

        # 1. 静态系统提示词（如果有）
        system_message = next((msg for msg in self.dialogue if msg.role == "system"), None)
        if system_message:
            # 可选：拆分静态和动态部分（原 <context> 标记仍然支持）
            full_prompt = system_message.content
            static_part = full_prompt
            dynamic_part = ""

            context_match = re.search(r"<context>", full_prompt)
            if context_match:
                static_part = full_prompt[:context_match.start()]
                dynamic_part = full_prompt[context_match.start():]

            dialogue.append({"role": "system", "content": static_part})

            # 2. 动态上下文（记忆、时间等）作为第二条 system 消息
            if dynamic_part or memory_str:
                # 复制一份动态部分，避免修改原内容
                dynamic_content = dynamic_part
                # 替换时间占位符
                dynamic_content = dynamic_content.replace(
                    "{{current_time}}", datetime.now().strftime("%H:%M")
                )
                # 注入记忆（如果有）
                if memory_str is not None:
                    dynamic_content = re.sub(
                        r"<memory>.*?</memory>",
                        f"<memory>\n{memory_str}\n</memory>",
                        dynamic_content,
                        flags=re.DOTALL,
                    )
                if dynamic_content.strip():
                    dialogue.append({"role": "system", "content": dynamic_content})

        # 3. 普通对话历史（忽略 tool 和 temporary 消息）
        for msg in self.dialogue:
            if msg.role == "system":
                continue
            # 只保留 user 和 assistant 消息
            if msg.role in ("user", "assistant") and msg.content is not None:
                dialogue.append({"role": msg.role, "content": msg.content})

        return dialogue