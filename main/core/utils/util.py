import re
import os
import json
import copy
import socket
import subprocess
from typing import Any, Callable, Optional

TAG = __name__


def get_local_ip() -> str:
    """获取本机局域网 IP 地址"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return "127.0.0.1"


def is_private_ip(ip_addr: str) -> bool:
    """判断 IP 地址是否为私有地址（兼容 IPv4/IPv6）"""
    try:
        if not re.match(
            r"^(\d{1,3}\.){3}\d{1,3}$|^([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$", ip_addr
        ):
            return False
        if "." in ip_addr:
            parts = list(map(int, ip_addr.split(".")))
            if parts[0] == 10:
                return True
            if parts[0] == 172 and 16 <= parts[1] <= 31:
                return True
            if parts[0] == 192 and parts[1] == 168:
                return True
            if ip_addr == "127.0.0.1":
                return True
            if parts[0] == 169 and parts[1] == 254:
                return True
            return False
        else:
            ip_addr = ip_addr.lower()
            if ip_addr.startswith(("fc00:", "fd00:")):
                return True
            if ip_addr == "::1":
                return True
            if ip_addr.startswith("fe80:"):
                return True
            return False
    except (ValueError, IndexError):
        return False


def write_json_file(file_path: str, data: dict) -> None:
    """将数据写入 JSON 文件"""
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def remove_punctuation_and_length(text: str):
    """去除文本中的标点符号和空格，返回 (长度, 清理后文本)"""
    full_width = "！＂＃＄％＆＇（）＊＋，－。／：；＜＝＞？＠［＼］＾＿｀｛｜｝～"
    half_width = r'!"#$%&\'()*+,-./:;<=>?@[\]^_`{|}~'
    space = " "
    full_space = "　"
    result = "".join(
        ch for ch in text
        if ch not in full_width
        and ch not in half_width
        and ch not in space
        and ch not in full_space
    )
    if result == "Yeah":
        return 0, ""
    return len(result), result


def check_model_key(model_type: str, model_key: str) -> Optional[str]:
    """检查 API key 是否含有未配置的占位符"""
    if "你" in model_key:
        return f"配置错误: {model_type} 的 API key 未设置,当前值为: {model_key}"
    return None


def parse_string_to_list(value, separator: str = ";") -> list:
    """将字符串、列表或 None 转换为列表"""
    if value is None or value == "":
        return []
    if isinstance(value, str):
        return [item.strip() for item in value.split(separator) if item.strip()]
    if isinstance(value, list):
        return value
    return []


def check_ffmpeg_installed() -> bool:
    """检查 ffmpeg 是否可用，不可用时抛出详细错误"""
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
        output = (result.stdout + result.stderr).lower()
        if "ffmpeg version" in output:
            return True
        raise ValueError("未检测到有效的 ffmpeg 版本输出。")
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        stderr = ""
        if isinstance(e, subprocess.CalledProcessError):
            stderr = (e.stderr or "").strip()
        else:
            stderr = str(e).strip()
        error_msg = [
            "❌ 检测到 ffmpeg 无法正常运行。\n",
            "建议您：",
            "1. 确认已正确激活 conda 环境；",
            "2. 查阅项目安装文档，了解如何在 conda 环境中安装 ffmpeg。\n",
        ]
        if "libiconv.so.2" in stderr:
            error_msg.append("⚠️ 发现缺少依赖库：libiconv.so.2")
            error_msg.append("解决方法：在当前 conda 环境中执行：")
            error_msg.append("   conda install -c conda-forge libiconv\n")
        elif "no such file or directory" in stderr and "ffmpeg" in stderr.lower():
            error_msg.append("⚠️ 系统未找到 ffmpeg 可执行文件。")
            error_msg.append("解决方法：在当前 conda 环境中执行：")
            error_msg.append("   conda install -c conda-forge ffmpeg\n")
        else:
            error_msg.append("错误详情：")
            error_msg.append(stderr or "未知错误。")
        raise ValueError("\n".join(error_msg)) from e


def extract_json_from_string(input_string: str) -> Optional[str]:
    """从字符串中提取第一个完整的 JSON 对象"""
    pattern = r"(\{.*\})"
    match = re.search(pattern, input_string, re.DOTALL)
    return match.group(1) if match else None


def filter_sensitive_info(config: dict) -> dict:
    """过滤配置中的敏感信息（如 api_key, token 等）"""
    sensitive_keys = [
        "api_key", "personal_access_token", "access_token", "token",
        "secret", "access_key_secret", "secret_key",
    ]

    def _filter(d: dict) -> dict:
        filtered = {}
        for k, v in d.items():
            if any(sensitive in k.lower() for sensitive in sensitive_keys):
                filtered[k] = "***"
            elif isinstance(v, dict):
                filtered[k] = _filter(v)
            elif isinstance(v, list):
                filtered[k] = [
                    _filter(i) if isinstance(i, dict) else i for i in v
                ]
            elif isinstance(v, str):
                try:
                    json_data = json.loads(v)
                    if isinstance(json_data, dict):
                        filtered[k] = json.dumps(_filter(json_data), ensure_ascii=False)
                    else:
                        filtered[k] = v
                except (json.JSONDecodeError, TypeError):
                    filtered[k] = v
            else:
                filtered[k] = v
        return filtered

    return _filter(copy.deepcopy(config))


def is_valid_image_file(file_data: bytes) -> bool:
    """检查文件数据是否为有效的图片格式（基于文件头）"""
    signatures = {
        b"\xff\xd8\xff": "JPEG",
        b"\x89PNG\r\n\x1a\n": "PNG",
        b"GIF87a": "GIF",
        b"GIF89a": "GIF",
        b"BM": "BMP",
        b"II*\x00": "TIFF",
        b"MM\x00*": "TIFF",
        b"RIFF": "WEBP",
    }
    return any(file_data.startswith(sig) for sig in signatures)


def sanitize_tool_name(name: str) -> str:
    """清理工具名称，用于 OpenAI 兼容（保留中文、字母、数字、下划线、连字符）"""
    return re.sub(r"[^a-zA-Z0-9_\-\u4e00-\u9fff]", "_", name)


def validate_mcp_endpoint(mcp_endpoint: str) -> bool:
    """校验 MCP 接入点格式"""
    if not mcp_endpoint.startswith("ws"):
        return False
    if "key" in mcp_endpoint.lower() or "call" in mcp_endpoint.lower():
        return False
    if "/mcp/" not in mcp_endpoint:
        return False
    return True


def get_system_error_response(config: dict) -> str:
    """获取系统错误时的回复文本"""
    return config.get("system_error_response", "主人，小智现在有点忙，我们稍后再试吧。")