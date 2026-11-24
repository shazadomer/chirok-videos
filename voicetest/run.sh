#!/usr/bin/env bash
# Test free Sorani TTS models on the GitHub runner. Results go to voicetest/out/.
set -x
OUT="$GITHUB_WORKSPACE/voicetest/out"; mkdir -p "$OUT"
TEXT="$(cat "$GITHUB_WORKSPACE/voicetest/text.txt")"
pip install -q huggingface_hub soundfile onnxruntime numpy scipy piper-tts 2>&1 | tail -2

# ---- Vekol-TTS (male, small ONNX) ----
mkdir -p /tmp/vekol && cd /tmp/vekol
python3 - <<'PY'
from huggingface_hub import snapshot_download
p = snapshot_download("RevgeAI/vekol-tts-ckb-edge", local_dir="/tmp/vekol")
import os; print(os.listdir(p))
PY
ls -la /tmp/vekol
if [ -f vekol_tts.py ]; then
  python3 vekol_tts.py "$TEXT" "$OUT/vekol_male.wav" > "$OUT/vekol_log.txt" 2>&1 || true
fi
if [ ! -s "$OUT/vekol_male.wav" ]; then
  echo "$TEXT" | piper -m /tmp/vekol/model.onnx -c /tmp/vekol/model.onnx.json -f "$OUT/vekol_male.wav" >> "$OUT/vekol_log.txt" 2>&1 || true
fi

# ---- F5-TTS Central Kurdish (two male voices) ----
pip install -q f5-tts asosoft 2>&1 | tail -2
mkdir -p /tmp/f5 && cd /tmp/f5
python3 - <<'PY'
from huggingface_hub import hf_hub_download
for f in ["infer.py","F5TTS_v1_Base.yaml","vocab.txt",
          "model-studio-male.pt","prompt-studio-male.wav","prompt-studio-male.txt",
          "model-audiobook-male.pt","prompt-audiobook-male.wav","prompt-audiobook-male.txt"]:
    hf_hub_download("aranemini/central-kurdish-tts", f, local_dir="/tmp/f5")
PY
cp infer.py "$OUT/f5_infer_original.py"
printf "%s" "$TEXT" > input_text.txt
for v in studio-male audiobook-male; do
  sed "s/studio-male/$v/g" infer.py > "infer_$v.py"
  ( time python3 "infer_$v.py" ) > "$OUT/f5_${v}_log.txt" 2>&1 || true
  [ -f "output-$v.wav" ] && cp "output-$v.wav" "$OUT/f5_${v}.wav"
done
ls -la "$OUT"
