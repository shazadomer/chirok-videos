import re
import sys
from pathlib import Path

import soundfile as sf
from omegaconf import OmegaConf
from hydra.utils import get_class

sys.path.append(str(Path(__file__).parent / "src"))

import asosoft

from f5_tts.infer.utils_infer import (
    infer_process,
    load_model,
    load_vocoder,
    preprocess_ref_audio_text,
    cfg_strength,
    cross_fade_duration,
    device,
    nfe_step,
    sway_sampling_coef,
    speed,
    target_rms,
    fix_duration,
)


# CONFIG

text_file = Path("input_text.txt") #text input to be synthesized
prompt_wav = Path("prompt-studio-male.wav") #prompt wav file
prompt_text_file = Path("prompt-studio-male.txt") #prompt transcription
output_wav = Path("output-studio-male.wav")

ckpt_path = Path("model-studio-male.pt") # F5 model name
model_cfg_path = "F5TTS_v1_Base.yaml" #main config file

vocab_file = "vocab.txt" #address of vocab file
vocoder_name = "vocos"
load_vocoder_from_local = False
vocoder_local_path = None


# TEXT PREPROCESSING

replacements = {
    "ẍ": "χ",
    "ƹ": "¿",
    "ḧ": "ḥ",
}


def normalize_and_g2p(text: str) -> str:

    text = re.sub(r"(\d{1,8})\s*[-–]\s*(\d{1,8})", r"\1 تا \2", text)

    text = re.sub(
        r"\b\d{9,}\b",
        lambda m: f"<NUM:{m.group(0)}>",
        text,
    )

    norm = asosoft.Normalize(
        text,
        changeInitialR=True,
        deepUnicodeCorrectios=True,
        additionalUnicodeCorrections=True,
    )

    norm = asosoft.NormalizePunctuations(
        norm,
        seprateAllPunctuations=True,
    )

    try:
        norm = asosoft.Number2Word(norm)
    except Exception as e:
        print(f"[Number2Word Error] Skipping conversion: {e}")

    g2p = asosoft.KurdishG2P(norm).replace("ˈ", "")

    for old, new in replacements.items():
        g2p = g2p.replace(old, new)

    return g2p


def read_text_file(path: Path) -> str:
    text = path.read_text(encoding="utf-8").strip()

    if not text:
        raise RuntimeError(f"Empty text file: {path}")

    return text


# LOAD MODEL

def load_tts_model(ckpt_path: Path):
    print(f"Loading model: {ckpt_path}")

    model_cfg = OmegaConf.load(model_cfg_path)
    model_cls = get_class(f"f5_tts.model.{model_cfg.model.backbone}")

    ema_model = load_model(
        model_cls,
        model_cfg.model.arch,
        str(ckpt_path),
        mel_spec_type=vocoder_name,
        vocab_file=vocab_file,
        device=device,
    )

    return ema_model



def main():
    if not prompt_wav.exists():
        raise RuntimeError(f"Prompt wav not found: {prompt_wav}")

    raw_text = read_text_file(text_file)
    raw_prompt_text = read_text_file(prompt_text_file)

    text = normalize_and_g2p(raw_text)
    prompt_text = normalize_and_g2p(raw_prompt_text)

    print("Input text:")
    print(raw_text)

    print("\nNormalized/G2P input:")
    print(text)

    print("\nPrompt transcription:")
    print(raw_prompt_text)

    print("\nNormalized/G2P prompt transcription:")
    print(prompt_text)

    print("\nLoading vocoder...")
    vocoder = load_vocoder(
        vocoder_name=vocoder_name,
        is_local=load_vocoder_from_local,
        local_path=vocoder_local_path,
        device=device,
    )

    ema_model = load_tts_model(ckpt_path)

    ref_audio_proc, ref_text_proc = preprocess_ref_audio_text(
        str(prompt_wav),
        prompt_text,
    )

    print("\nSynthesizing...")

    audio_segment, final_sr, _ = infer_process(
        ref_audio_proc,
        ref_text_proc,
        text,
        ema_model,
        vocoder,
        mel_spec_type=vocoder_name,
        target_rms=target_rms,
        cross_fade_duration=cross_fade_duration,
        nfe_step=nfe_step,
        cfg_strength=cfg_strength,
        sway_sampling_coef=sway_sampling_coef,
        speed=speed,
        fix_duration=fix_duration,
        device=device,
    )

    output_wav.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(output_wav), audio_segment, final_sr)

    print(f"\nSaved wav: {output_wav}")


if __name__ == "__main__":
    main()
