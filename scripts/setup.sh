#!/usr/bin/env bash
# 一键装本地优先转录栈（FunASR 中文最强，含 VAD+标点+说话人分离）。
# 隐私：装好后录音不出本机。首次跑 transcribe.py 会下载模型(~1-2GB)到 ~/.cache/modelscope。
set -e

PY="${PYTHON:-python3}"
echo "== Python: $($PY --version) =="
echo "== 升级 pip =="
$PY -m pip install --upgrade pip

echo "== 装 FunASR + ModelScope（主引擎）=="
$PY -m pip install -U funasr modelscope

echo "== 装 torch / torchaudio（FunASR 依赖；arm64 走 MPS）=="
$PY -m pip install -U torch torchaudio

echo "== 可选：mlx-whisper（Apple Silicon 本地英文/多语兜底）=="
$PY -m pip install -U mlx-whisper || echo "(mlx-whisper 可选，跳过)"

echo "== 可选：pyannote（仅当主引擎没给说话人时用；需 HF_TOKEN）=="
# huggingface-hub 必须 <1.0：1.x 会在运行时打断 transformers/funasr（见 requirements.txt 注释）。
$PY -m pip install -U "pyannote.audio" "huggingface-hub<1.0" || echo "(pyannote 可选，跳过)"

echo "== 自检（真正执行，而非只打印）=="
$PY -c "import funasr, torch, torchaudio; print('✓ funasr+torch+torchaudio import ok')"

cat <<'EOF'

✓ 本地栈就绪。自检已通过。

可选 API 兜底（会上传音频到云端；须显式 --engine 或 --allow-cloud 才生效，留空则纯本地）：
    export GROQ_API_KEY=gsk_...        # Groq Whisper-large-v3，快，免费额度~9000min/月（US 托管）
    export DASHSCOPE_API_KEY=sk-...    # 阿里 Paraformer，中文优化，~¥0.004/min（大陆托管，注意 PIPL）
    export OPENROUTER_API_KEY=sk-or... # OpenRouter STT，多模型可插拔（纯文本，无说话人分离）
    export HF_TOKEN=hf_...             # 仅 pyannote 说话人分离需要

首次转录（会下载模型）：
    python3 scripts/transcribe.py 你的录音.m4a
EOF
