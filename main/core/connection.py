import asyncio
import copy
import uuid
from collections import deque
from typing import Dict, Any

from core.utils.dialogue import Dialogue, Message
from core.utils.prompt_manager import PromptManager
from core.utils.util import get_system_error_response
from core.providers.asr.dto.dto import InterfaceType
from core.providers.tts.default import DefaultTTS
from config.logger import setup_logging


class Asker:
    """
    独立语音问答核心，支持文本输入返回文本，或音频输入返回音频。
    不依赖 WebSocket、设备管理、远程 API、上报等。
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = copy.deepcopy(config)
        self.logger = setup_logging()
        self.session_id = str(uuid.uuid4())

        # 读取固定选择的模块名
        self.asr_provider = self.config.get("asr_provider")
        self.llm_provider = self.config.get("llm_provider")
        self.tts_provider = self.config.get("tts_provider")
        self.vad_provider = self.config.get("vad_provider")
        self.memory_provider = self.config.get("memory_provider", "nomem")

        # 初始化各模块（使用统一的初始化函数，但只初始化需要的）
        self._initialize_modules()

        # 对话管理
        self.dialogue = Dialogue()
        self.prompt_manager = PromptManager(self.config, self.logger)

        # VAD 相关状态（用于音频流处理）
        self.client_audio_buffer = bytearray()
        self.client_have_voice = False
        self.client_voice_window = deque(maxlen=5)
        self.vad_last_voice_time = 0.0
        self.client_voice_stop = False
        self.last_is_voice = False

        # ASR 缓冲
        self.asr_audio = []
        self.asr_audio_queue = None  # 暂时不用队列，直接处理

        # 设置系统提示词
        self._init_prompt()

        # 记忆初始化
        if self.memory:
            self.memory.init_memory(
                role_id="default_user",
                llm=self.llm,
                summary_memory=None,
                save_to_file=True,
            )

    def _initialize_modules(self):
        from core.utils.modules_initialize import (
            initialize_vad, initialize_asr, initialize_llm,
            initialize_tts, initialize_memory
        )

        self.vad = None
        if self.vad_provider and self.vad_provider != "none":
            self.vad = initialize_vad(self.config)

        self.asr = None
        if self.asr_provider and self.asr_provider != "none":
            self.asr = initialize_asr(self.config)

        self.llm = None
        if self.llm_provider and self.llm_provider != "none":
            self.llm = initialize_llm(self.config)

        self.tts = None
        if self.tts_provider and self.tts_provider != "none":
            self.tts = initialize_tts(self.config)
        else:
            # 兜底：使用无输出的默认 TTS（避免 None 引用）
            self.tts = DefaultTTS(self.config)

        self.memory = None
        if self.memory_provider and self.memory_provider != "nomem":
            self.memory = initialize_memory(self.config)

    def _init_prompt(self):
        """初始化系统提示词"""
        user_prompt = self.config.get("prompt")
        if user_prompt:
            prompt = self.prompt_manager.get_quick_prompt(user_prompt)
            self.dialogue.update_system_message(prompt)

    def change_system_prompt(self, prompt: str):
        """动态修改系统提示词"""
        self.dialogue.update_system_message(prompt)

    async def ask_text(self, query: str) -> str:
        """
        纯文本问答，返回文本回复。
        """
        if not query:
            return ""

        self.logger.info(f"用户问题: {query}")

        # 获取记忆上下文
        memory_str = None
        if self.memory:
            memory_str = await self.memory.query_memory(query)

        # 将用户消息加入对话历史
        self.dialogue.put(Message(role="user", content=query))

        # 构建 LLM 所需的对话格式（包含记忆）
        llm_dialogue = self.dialogue.get_llm_dialogue_with_memory(memory_str)

        try:
            # 注意：llm.response 是同步生成器，需要在线程池中运行
            def _iterate():
                full_response = ""
                # 修正参数顺序：先传 dialogue，再传 session_id
                for chunk in self.llm.response(llm_dialogue, self.session_id):
                    if chunk:
                        full_response += chunk
                return full_response

            loop = asyncio.get_event_loop()
            answer = await loop.run_in_executor(None, _iterate)

            # 存储 assistant 回复
            self.dialogue.put(Message(role="assistant", content=answer))
            return answer
        except Exception as e:
            self.logger.error(f"LLM 调用失败: {e}")
            return get_system_error_response(self.config)

    async def ask_audio(self, audio_bytes: bytes, sample_rate: int = 16000) -> bytes:
        """
        音频问答：ASR -> LLM -> TTS，返回生成的音频字节流。
        audio_bytes: PCM 16kHz 单声道音频数据。
        """
        if not audio_bytes:
            return b""

        # 1. ASR 转文本
        text = await self._asr_audio(audio_bytes, sample_rate)
        if not text:
            # ASR 无结果时返回空音频（可替换为错误提示音）
            self.logger.warning("ASR 识别结果为空")
            return b""

        # 2. LLM 生成回复文本
        answer = await self.ask_text(text)
        if not answer or answer == get_system_error_response(self.config):
            # LLM 失败，返回错误提示音频（可自行合成）
            self.logger.warning("LLM 生成失败，返回默认提示")
            return b""

        # 3. TTS 合成音频
        audio = await self._tts_text(answer)
        return audio

    async def _asr_audio(self, audio_bytes: bytes, sample_rate: int) -> str:
        """调用 ASR 识别音频"""
        if not self.asr:
            raise RuntimeError("ASR 未初始化")

        # 检查 ASR 对象是否有 transcribe 或 transcribe_async 方法
        if hasattr(self.asr, "transcribe"):
            transcribe_method = self.asr.transcribe
            # 判断是否为协程函数
            if asyncio.iscoroutinefunction(transcribe_method):
                # 异步方法直接 await
                result = await transcribe_method(audio_bytes, sample_rate)
            else:
                # 同步方法在线程池中执行
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, transcribe_method, audio_bytes, sample_rate)
            return result
        elif hasattr(self.asr, "transcribe_async"):
            return await self.asr.transcribe_async(audio_bytes, sample_rate)
        else:
            raise NotImplementedError("ASR 接口不支持 transcribe")

    async def _tts_text(self, text: str) -> bytes:
        """调用 TTS 合成音频"""
        if not self.tts:
            raise RuntimeError("TTS 未初始化")
        # 所有修改后的 TTS 提供者都实现了 synthesize 方法
        if hasattr(self.tts, "synthesize"):
            return await self.tts.synthesize(text)
        else:
            raise NotImplementedError("TTS 接口不支持 synthesize")

    async def close(self):
        """释放资源"""
        if self.asr:
            await self.asr.close()
        if self.tts:
            await self.tts.close()
        # 其他清理