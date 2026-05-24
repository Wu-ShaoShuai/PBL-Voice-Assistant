"""
文本处理工具（独立部署版）
提供去除标点/表情、表情检测等功能，不依赖 WebSocket 或连接对象。
"""

EMOJI_MAP = {
    "😂": "funny",
    "😭": "crying",
    "😠": "angry",
    "😔": "sad",
    "😍": "loving",
    "😲": "surprised",
    "😱": "shocked",
    "🤔": "thinking",
    "😌": "relaxed",
    "😴": "sleepy",
    "😜": "silly",
    "🙄": "confused",
    "😶": "neutral",
    "🙂": "happy",
    "😆": "laughing",
    "😳": "embarrassed",
    "😉": "winking",
    "😎": "cool",
    "🤤": "delicious",
    "😘": "kissy",
    "😏": "confident",
}

EMOJI_RANGES = [
    (0x1F600, 0x1F64F),
    (0x1F300, 0x1F5FF),
    (0x1F680, 0x1F6FF),
    (0x1F900, 0x1F9FF),
    (0x1FA70, 0x1FAFF),
    (0x2600, 0x26FF),
    (0x2700, 0x27BF),
]


def get_string_no_punctuation_or_emoji(s: str) -> str:
    """去除字符串首尾的空格、标点符号和表情符号"""
    chars = list(s)
    start = 0
    while start < len(chars) and is_punctuation_or_emoji(chars[start]):
        start += 1
    end = len(chars) - 1
    while end >= start and is_punctuation_or_emoji(chars[end]):
        end -= 1
    return "".join(chars[start: end + 1])


def is_punctuation_or_emoji(char: str) -> bool:
    """检查字符是否为空格、标点符号或表情符号"""
    punctuation_set = {
        "，", ",", "。", ".", "！", "!", "“", "”", '"', "：", ":",
        "-", "－", "、", "[", "]", "【", "】",
    }
    if char.isspace() or char in punctuation_set:
        return True
    return is_emoji(char)


def is_emoji(char: str) -> bool:
    """检查字符是否为 emoji 表情"""
    code_point = ord(char)
    return any(start <= code_point <= end for start, end in EMOJI_RANGES)


def check_emoji(text: str) -> str:
    """去除文本中的所有 emoji 表情和换行符"""
    return "".join(ch for ch in text if not is_emoji(ch) and ch != "\n")