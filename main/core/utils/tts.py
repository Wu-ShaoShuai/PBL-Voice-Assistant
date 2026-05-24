import os
import re
import sys
import importlib
from config.logger import setup_logging
from core.utils.textUtils import check_emoji

logger = setup_logging()

punctuation_set = {
    "，", ",", "。", ".", "！", "!", "“", "”", '"', "：", ":",
    "-", "－", "、", "[", "]", "【", "】", "~",
}


def create_instance(class_name, *args, **kwargs):
    """
    创建 TTS 实例的工厂方法（独立部署版）
    :param class_name: TTS 提供者类名（如 'EdgeTTS', 'AliyunTTS'）
    :param args: 额外的位置参数（已弃用，建议仅使用 config 关键字参数）
    :param kwargs: 配置字典（通常作为第一个关键字参数传入）
    :return: TTS 实例
    """
    module_path = os.path.join('core', 'providers', 'tts', f'{class_name}.py')
    if os.path.exists(module_path):
        lib_name = f'core.providers.tts.{class_name}'
        if lib_name not in sys.modules:
            sys.modules[lib_name] = importlib.import_module(lib_name)
        # 修改后的 TTSProvider 只接受 config 参数，不再需要 delete_audio_file
        # 因此，当调用 create_instance 时，应使用关键字参数 config=... 或直接传递配置字典
        # 兼容原有调用方式：如果 kwargs 中有 'config' 则使用，否则假设 args[0] 是 config
        if 'config' in kwargs:
            config = kwargs['config']
        elif args:
            config = args[0]
        else:
            raise ValueError("需要提供配置字典")
        return sys.modules[lib_name].TTSProvider(config)
    raise ValueError(f"不支持的 TTS 类型: {class_name}")


class MarkdownCleaner:
    """
    封装 Markdown 清理逻辑：直接用 MarkdownCleaner.clean_markdown(text) 即可
    """
    NORMAL_FORMULA_CHARS = re.compile(r'[a-zA-Z\\^_{}\+\-\(\)\[\]=]')

    @staticmethod
    def _replace_inline_dollar(m: re.Match) -> str:
        content = m.group(1)
        if MarkdownCleaner.NORMAL_FORMULA_CHARS.search(content):
            return content
        else:
            return m.group(0)

    @staticmethod
    def _replace_table_block(match: re.Match) -> str:
        block_text = match.group('table_block')
        lines = block_text.strip('\n').split('\n')
        parsed_table = []
        for line in lines:
            line_stripped = line.strip()
            if re.match(r'^\|\s*[-:]+\s*(\|\s*[-:]+\s*)+\|?$', line_stripped):
                continue
            columns = [col.strip() for col in line_stripped.split('|') if col.strip() != '']
            if columns:
                parsed_table.append(columns)
        if not parsed_table:
            return ""
        headers = parsed_table[0]
        data_rows = parsed_table[1:] if len(parsed_table) > 1 else []
        lines_for_tts = []
        if len(parsed_table) == 1:
            only_line_str = ", ".join(parsed_table[0])
            lines_for_tts.append(f"单行表格：{only_line_str}")
        else:
            lines_for_tts.append(f"表头是：{', '.join(headers)}")
            for i, row in enumerate(data_rows, start=1):
                row_str_list = []
                for col_index, cell_val in enumerate(row):
                    if col_index < len(headers):
                        row_str_list.append(f"{headers[col_index]} = {cell_val}")
                    else:
                        row_str_list.append(cell_val)
                lines_for_tts.append(f"第 {i} 行：{', '.join(row_str_list)}")
        return "\n".join(lines_for_tts) + "\n"

    REGEXES = [
        (re.compile(r'```.*?```', re.DOTALL), ''),
        (re.compile(r'^#+\s*', re.MULTILINE), ''),
        (re.compile(r'(\*\*|__)(.*?)\1'), r'\2'),
        (re.compile(r'(\*|_)(?=\S)(.*?)(?<=\S)\1'), r'\2'),
        (re.compile(r'!\[.*?\]\(.*?\)'), ''),
        (re.compile(r'\[(.*?)\]\(.*?\)'), r'\1'),
        (re.compile(r'^\s*>+\s*', re.MULTILINE), ''),
        (re.compile(r'(?P<table_block>(?:^[^\n]*\|[^\n]*\n)+)', re.MULTILINE), _replace_table_block),
        (re.compile(r'^\s*[*+-]\s*', re.MULTILINE), '- '),
        (re.compile(r'\$\$.*?\$\$', re.DOTALL), ''),
        (re.compile(r'(?<![A-Za-z0-9])\$([^\n$]+)\$(?![A-Za-z0-9])'), _replace_inline_dollar),
        (re.compile(r'\n{2,}'), '\n'),
    ]

    @staticmethod
    def clean_markdown(text: str) -> str:
        for regex, replacement in MarkdownCleaner.REGEXES:
            text = regex.sub(replacement, text)
        text = check_emoji(text)
        if text and all((c.isascii() or c.isspace() or c in punctuation_set) for c in text):
            return text
        return text.strip()


def convert_percentage_to_range(percentage, min_val, max_val, base_val=None):
    """
    将百分比(-100~100)转换为指定范围的值
    """
    percentage, min_val, max_val = float(percentage), float(min_val), float(max_val)
    base_val = float(base_val) if base_val is not None else (min_val + max_val) / 2
    if percentage < 0:
        result = base_val + (base_val - min_val) * (percentage / 100)
    else:
        result = base_val + (max_val - base_val) * (percentage / 100)
    return max(min_val, min(max_val, result))