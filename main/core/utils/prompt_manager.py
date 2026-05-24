"""
系统提示词管理器模块（独立部署精简版）
负责加载和管理系统提示词模板，支持变量渲染（时间、日期、农历、表情列表等）
"""

import os
from typing import Dict, Any, Optional
from datetime import datetime
from jinja2 import Template
from config.logger import setup_logging

TAG = __name__

WEEKDAY_MAP = {
    "Monday": "星期一",
    "Tuesday": "星期二",
    "Wednesday": "星期三",
    "Thursday": "星期四",
    "Friday": "星期五",
    "Saturday": "星期六",
    "Sunday": "星期日",
}

EMOJI_LIST = [
    "😶", "🙂", "😆", "😂", "😔", "😠", "😭", "😍", "😳", "😲",
    "😱", "🤔", "😉", "😎", "😌", "🤤", "😘", "😏", "😴", "😜", "🙄",
]


class PromptManager:
    """系统提示词管理器（独立部署版）"""

    def __init__(self, config: Dict[str, Any], logger=None):
        self.config = config
        self.logger = logger or setup_logging()
        self.base_prompt_template = None

        # 缓存管理器（用于缓存模板内容）
        from core.utils.cache.manager import cache_manager, CacheType
        self.cache_manager = cache_manager
        self.CacheType = CacheType

        # 上下文数据提供者（可选，从配置的 API 获取动态数据）
        from core.utils.context_provider import ContextDataProvider
        self.context_provider = ContextDataProvider(config, self.logger)
        self.context_data = ""

        self._load_base_template()

    def _load_base_template(self):
        """加载基础提示词模板（支持文件缓存）"""
        try:
            template_path = self.config.get("prompt_template", "agent-base-prompt.txt")
            cache_key = f"prompt_template:{template_path}"

            cached = self.cache_manager.get(self.CacheType.CONFIG, cache_key)
            if cached is not None:
                self.base_prompt_template = cached
                self.logger.bind(tag=TAG).debug("从缓存加载基础提示词模板")
                return

            if os.path.exists(template_path):
                with open(template_path, "r", encoding="utf-8") as f:
                    content = f.read()
                self.cache_manager.set(self.CacheType.CONFIG, cache_key, content)
                self.base_prompt_template = content
                self.logger.bind(tag=TAG).debug("成功加载基础提示词模板并缓存")
            else:
                self.logger.bind(tag=TAG).warning(f"未找到提示词模板文件: {template_path}")
                self.base_prompt_template = ""
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"加载提示词模板失败: {e}")
            self.base_prompt_template = ""

    def get_quick_prompt(self, user_prompt: str, user_id: Optional[str] = None) -> str:
        """获取快速提示词（支持按用户 ID 缓存）"""
        if user_id:
            cache_key = f"device_prompt:{user_id}"
            cached = self.cache_manager.get(self.CacheType.DEVICE_PROMPT, cache_key)
            if cached is not None:
                self.logger.bind(tag=TAG).debug(f"使用用户 {user_id} 的缓存提示词")
                return cached
            # 缓存未命中，存入
            self.cache_manager.set(self.CacheType.DEVICE_PROMPT, cache_key, user_prompt)
            self.logger.bind(tag=TAG).debug(f"用户 {user_id} 的提示词已缓存")
        self.logger.bind(tag=TAG).info(f"使用快速提示词: {user_prompt[:50]}...")
        return user_prompt

    def _get_current_time_info(self):
        """获取当前时间、日期、农历信息"""
        from .current_time import (
            get_current_date,
            get_current_weekday,
            get_current_lunar_date,
        )
        today_date = get_current_date()
        today_weekday = get_current_weekday()
        lunar_date = get_current_lunar_date()
        return today_date, today_weekday, lunar_date

    def fetch_dynamic_context(self, user_id: str = "") -> str:
        """从配置的 API 获取动态上下文数据（如健康、股票等）"""
        try:
            self.context_data = self.context_provider.fetch_all(user_id)
            return self.context_data
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"获取动态上下文失败: {e}")
            return ""

    def build_enhanced_prompt(
        self,
        base_prompt: str,
        user_id: Optional[str] = None,
        memory_str: Optional[str] = None,
    ) -> str:
        """
        构建增强的系统提示词
        :param base_prompt: 用户自定义的基础提示词（将作为 base_prompt 变量传入模板）
        :param user_id: 用户标识（用于缓存和动态上下文）
        :param memory_str: 记忆内容（可选）
        :return: 渲染后的完整提示词
        """
        if not self.base_prompt_template:
            # 没有模板时直接返回基础提示词
            return base_prompt

        try:
            # 获取时间信息
            today_date, today_weekday, lunar_date = self._get_current_time_info()
            current_time_str = datetime.now().strftime("%H:%M")

            # 获取动态上下文（如果有 user_id 且模板需要）
            dynamic_context = ""
            if user_id and self.base_prompt_template and "dynamic_context" in self.base_prompt_template:
                dynamic_context = self.fetch_dynamic_context(user_id)

            # 准备模板变量
            template_vars = {
                "base_prompt": base_prompt,
                "current_time": current_time_str,
                "today_date": today_date,
                "today_weekday": today_weekday,
                "lunar_date": lunar_date,
                "emojiList": EMOJI_LIST,
                "user_id": user_id or "",
                "dynamic_context": dynamic_context,
            }

            # 如果提供了记忆内容，且模板中有 <memory> 标记，则嵌入
            if memory_str is not None and self.base_prompt_template:
                # 先简单替换：将模板中的 <memory></memory> 标签内容替换为记忆字符串
                # 注意：这里直接操作模板字符串，避免使用复杂的正则
                template_content = self.base_prompt_template
                template_content = template_content.replace(
                    "<memory>",
                    f"<memory>\n{memory_str}\n"
                )
                template_content = template_content.replace(
                    "</memory>",
                    "</memory>"
                )
                # 注意：简单替换可能不够精准，更好的方式是在渲染前预处理，但为保持简洁，直接替换
                # 实际应用中可以改进为正则替换
            else:
                template_content = self.base_prompt_template

            template = Template(template_content)
            enhanced_prompt = template.render(**template_vars)

            # 可选：缓存最终的提示词（若提供了 user_id）
            if user_id:
                cache_key = f"device_prompt:{user_id}"
                self.cache_manager.set(self.CacheType.DEVICE_PROMPT, cache_key, enhanced_prompt)

            self.logger.bind(tag=TAG).debug(f"构建增强提示词成功，长度: {len(enhanced_prompt)}")
            return enhanced_prompt

        except Exception as e:
            self.logger.bind(tag=TAG).error(f"构建增强提示词失败: {e}")
            return base_prompt