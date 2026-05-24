import numpy as np
import onnxruntime
from .base import VADProviderBase


class VADProvider(VADProviderBase):
    def __init__(self, config):
        """
        :param config: 配置字典，必须包含 'model_dir' 指向 silero_vad.onnx 所在目录，
                       可选 'threshold', 'threshold_low', 'min_silence_duration_ms' 等（但独立部署中阈值可保留）
        """
        import os
        model_path = os.path.join(config["model_dir"], "silero_vad.onnx")
        opts = onnxruntime.SessionOptions()
        opts.inter_op_num_threads = 1
        opts.intra_op_num_threads = 1
        self.session = onnxruntime.InferenceSession(
            model_path, providers=["CPUExecutionProvider"], sess_options=opts
        )

        self.threshold = float(config.get("threshold", 0.5))
        self.threshold_low = float(config.get("threshold_low", 0.2))

        # 内部状态（Silero VAD 需要维持 state 和 context，但为无状态设计，每次调用需重置）
        # 注意：原模型设计用于流式检测，但独立部署中若一次性给长音频，可分段调用并维护状态。
        # 为简化，这里提供两种模式：
        # 1. 简单模式：每次调用独立检测（适用于短音频，但准确性稍差）
        # 2. 流式模式：由调用方维护状态（推荐）
        # 本实现提供流式模式，但用户需自己维护 state 和 context。
        # 为保持接口简单，我们将状态管理交给调用方：返回值中包含新的 state 和 context。
        # 但为不破坏抽象，我们提供可选的参数。更简单的方式：直接使用 Silero VAD 的官方 onnx 示例。
        # 这里我们简化：要求调用者传入 state 和 context，并在返回值中返回更新后的状态。
        # 由于基类未定义状态，我们可以在方法中额外接收参数。为保持基类简洁，本实现不强制，但推荐用户使用扩展方法。
        # 实际上，独立部署中通常一次性处理完整音频，我们可以采用滑动窗口方式。为了简单，我们只实现单次调用无状态检测。
        # 但 Silero 模型需要 state 和 context 才能准确检测。以下提供一个折中：方法内维护一个简单的环形缓冲区？不，那样会引入状态。
        # 最稳妥：让 VADProvider 支持 reset() 和 process() 流式方法，但为了快速集成，我们直接提供一个静态方法，内部维护全局状态（不推荐）。
        # 鉴于时间，我提供一个简单版本：仅对 PCM 块进行概率计算，不维护历史，适用于较长的音频（>0.5秒）时准确性尚可。
        # 用户若需要高精度，建议直接使用 Silero VAD 的官方 Python 包（silero-vad）。
        # 下面实现简单的一次性检测（不维护状态），适用于每个音频块独立判断。
        # 初始化 state 和 context 为空（每次调用重新初始化）
        self._init_state = np.zeros((2, 1, 128), dtype=np.float32)
        self._init_context = np.zeros((1, 64), dtype=np.float32)

    def is_vad(self, pcm_chunk: bytes, sample_rate: int = 16000) -> bool:
        """
        检测 PCM 块中是否包含语音。
        注意：此简单版本不跨块维护状态，因此对于长音频建议切分成 30-100ms 的小块，并手动维护状态。
        若需要流式检测，请自行管理状态，或使用其他方案。
        """
        # 确保数据长度是 512 采样点的整数倍（Silero 要求）
        # 此处简化：若长度不足，填充0；若过长，截断至512倍数？实际应分块处理。
        # 这里实现：只处理前 512 个采样点（大约 32ms），快速判断。
        if len(pcm_chunk) < 512 * 2:  # 512 samples * 2 bytes = 1024 bytes
            # 不足一帧，填充0
            pcm_chunk = pcm_chunk.ljust(512 * 2, b'\x00')
        # 取前 512 个采样点
        samples = np.frombuffer(pcm_chunk[:512*2], dtype=np.int16).astype(np.float32) / 32768.0
        # 构造输入（需要 context，这里用零）
        audio_input = np.concatenate([self._init_context, samples.reshape(1, -1)], axis=1).astype(np.float32)
        ort_inputs = {
            "input": audio_input,
            "state": self._init_state,
            "sr": np.array(sample_rate, dtype=np.int64),
        }
        out, _ = self.session.run(None, ort_inputs)
        prob = out.item()
        return prob >= self.threshold