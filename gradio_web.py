import gradio as gr
import requests
import base64
import time
import os
import tempfile
from typing import List, Dict

BACKEND_URL = "http://localhost:8000"

def call_backend_audio_with_text(audio_file_path: str):
    if not audio_file_path:
        return None, None, None
    with open(audio_file_path, "rb") as f:
        files = {"audio": f}
        try:
            response = requests.post(f"{BACKEND_URL}/ask/audio_with_text", files=files)
            if response.status_code == 200:
                data = response.json()
                user_text = data.get("user_text", "")
                assistant_text = data.get("assistant_text", "")
                audio_base64 = data.get("audio_base64", "")
                if audio_base64:
                    audio_bytes = base64.b64decode(audio_base64)
                    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                        tmp.write(audio_bytes)
                        temp_path = tmp.name
                    abs_path = os.path.abspath(temp_path).replace("\\", "/")
                    print(f"音频文件已生成: {abs_path}")
                    return user_text, assistant_text, abs_path
                else:
                    return user_text, assistant_text, None
            else:
                print("后端错误:", response.status_code)
                return None, None, None
        except Exception as e:
            print("请求失败:", e)
            return None, None, None

def call_backend_text(user_text: str):
    try:
        response = requests.post(f"{BACKEND_URL}/ask/text", json={"text": user_text})
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                return data.get("text", "")
        return "服务错误"
    except Exception as e:
        return f"请求失败: {e}"

def add_message(history: List[Dict], role: str, content: str):
    history.append({"role": role, "content": content})
    return history

def process_audio(audio_path, history_state, status_text):
    if audio_path is None:
        yield gr.update(), history_state, gr.update(), "✅ 准备就绪（已清除录音，请点击麦克风开始新录音）"
        return
    yield gr.update(), history_state, gr.update(), "🎙️ 已接收录音，正在处理..."
    time.sleep(0.5)
    user_text, assistant_text, reply_audio = call_backend_audio_with_text(audio_path)
    if user_text and assistant_text:
        new_history = history_state.copy()
        add_message(new_history, "user", user_text)
        add_message(new_history, "assistant", assistant_text)
        if reply_audio and os.path.exists(reply_audio):
            yield new_history, new_history, gr.update(value=reply_audio), "✅ 回复已生成"
        else:
            yield new_history, new_history, gr.update(value=None), "⚠️ 语音合成失败"
    else:
        new_history = history_state.copy()
        add_message(new_history, "user", "（录音处理失败）")
        add_message(new_history, "assistant", "服务出错，请重试。")
        yield new_history, new_history, gr.update(value=None), "❌ 处理失败"

def process_text(text_input, history_state, status_text):
    if not text_input or not text_input.strip():
        return history_state, history_state, "请输入内容", ""
    assistant_text = call_backend_text(text_input.strip())
    new_history = history_state.copy()
    add_message(new_history, "user", text_input.strip())
    add_message(new_history, "assistant", assistant_text)
    return new_history, new_history, "✅ 回复已生成", ""

def clear_history():
    welcome = [
        {"role": "user", "content": "🌟 欢迎使用智能语音助手"},
        {"role": "assistant", "content": "您可以通过语音或文字与我交流。点击录音按钮可语音输入，或在下方输入文字。"}
    ]
    return welcome, welcome, gr.update(value=None), gr.update(value=None)

def clear_audio_for_new_session():
    """清空录音组件，为新一轮语音对话做准备"""
    return gr.update(value=None)

def build_ui():
    with gr.Blocks(title="智能语音聊天助手") as demo:
        gr.Markdown("# 🎙️ 智能语音聊天助手")
        gr.Markdown("点击下方按钮开始录音，说完后再次点击按钮停止，系统将自动处理并回复。您也可以在下方输入文字进行交流。")
        with gr.Row():
            with gr.Column(scale=3):
                chatbot = gr.Chatbot(label="📋 对话历史", height=500)
            with gr.Column(scale=2):
                audio_input = gr.Audio(
                    sources=["microphone"],
                    type="filepath",
                    label="🎤 录音（点击麦克风开始/停止）",
                    interactive=True
                )
                # 改为“继续语音对话”按钮
                continue_btn = gr.Button("🗣️ 继续语音对话", variant="secondary", size="sm")
                gr.Markdown("💡 点击「继续语音对话」清空当前录音，然后点击上方麦克风开始新录音")
                
                audio_reply = gr.Audio(
                    label="🔊 语音回复",
                    interactive=False,
                    type="filepath"
                )
                status_text = gr.Textbox(
                    label="📡 系统状态",
                    value="✅ 准备就绪",
                    interactive=False,
                    lines=1
                )
                gr.Markdown("🎛️ 默认麦克风设备 | 采样率 16kHz | 智能降噪就绪")
        gr.Markdown("---")
        gr.Markdown("### 💬 文字输入")
        with gr.Row():
            text_input = gr.Textbox(
                label="输入您的问题",
                placeholder="在这里输入文字，然后按回车或点击发送...",
                lines=2,
                scale=4
            )
            send_btn = gr.Button("📤 发送", variant="primary", scale=1)
        clear_history_btn = gr.Button("🧹 清除对话历史")

        history_state = gr.State([])

        # 清除对话历史（同时清空录音和语音回复）
        clear_history_btn.click(
            fn=clear_history,
            outputs=[chatbot, history_state, audio_input, audio_reply]
        )

        # 继续语音对话：清空当前录音，让用户点击麦克风开始新录音
        continue_btn.click(
            fn=clear_audio_for_new_session,
            outputs=[audio_input]
        )

        # 录音变更事件：处理录音并生成回复
        audio_input.change(
            fn=process_audio,
            inputs=[audio_input, history_state, status_text],
            outputs=[chatbot, history_state, audio_reply, status_text],
            queue=True
        )

        send_btn.click(
            fn=process_text,
            inputs=[text_input, history_state, status_text],
            outputs=[chatbot, history_state, status_text, text_input]
        )

        text_input.submit(
            fn=process_text,
            inputs=[text_input, history_state, status_text],
            outputs=[chatbot, history_state, status_text, text_input]
        )

        # 页面加载时初始化
        demo.load(
            fn=clear_history,
            outputs=[chatbot, history_state, audio_input, audio_reply]
        )

    return demo

if __name__ == "__main__":
    demo = build_ui()
    demo.launch(share=False, theme=gr.themes.Soft())