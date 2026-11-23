#!/usr/bin/env python3
"""Build a vertical (1080x1920) story video with Kurdish subtitles.

Inputs (in the repo):
  story.txt   one sentence per line (the subtitle for that sentence)
  scenes.txt  for each sentence, the image(s) to show, comma separated
  voice/      01.wav, 02.wav, ... one voice file per sentence
  images/     the pictures named in scenes.txt
Output:
  output.mp4
"""
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(ROOT, "_work")
OUT = os.path.join(ROOT, "output.mp4")

# Settings you can change
SPEED = float(os.environ.get("VOICE_SPEED", "1.16"))  # voice speed-up
LEAD, GAP, TAIL = 0.4, 0.35, 1.6                      # seconds of silence
FPS = 30
FONT = "Noto Sans Arabic"
FONT_SIZE = 70


def run(cmd):
    subprocess.run(cmd, check=True)


def duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", path], capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


def ts(x):
    h = int(x // 3600)
    m = int(x % 3600 // 60)
    return f"{h}:{m:02d}:{x % 60:05.2f}"


def main():
    lines = [l.strip() for l in open(os.path.join(ROOT, "story.txt"), encoding="utf-8") if l.strip()]
    scenes = [[s.strip() for s in l.split(",") if s.strip()]
              for l in open(os.path.join(ROOT, "scenes.txt"), encoding="utf-8") if l.strip()]
    if len(lines) != len(scenes):
        sys.exit(f"story.txt has {len(lines)} lines but scenes.txt has {len(scenes)}")
    n = len(lines)

    shutil.rmtree(WORK, ignore_errors=True)
    os.makedirs(WORK)

    # 1. Clean each voice line: trim silence, shorten long pauses, speed up.
    durs = []
    for i in range(n):
        src = os.path.join(ROOT, "voice", f"{i + 1:02d}.wav")
        dst = os.path.join(WORK, f"v{i + 1:02d}.wav")
        af = ("silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.05,"
              "areverse,silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.05,areverse,"
              f"silenceremove=stop_periods=-1:stop_duration=0.45:stop_threshold=-42dB,atempo={SPEED}")
        run(["ffmpeg", "-v", "error", "-y", "-i", src, "-af", af, "-ar", "44100", "-ac", "1", dst])
        durs.append(duration(dst))

    # 2. Place the lines on one timeline.
    starts, t = [], LEAD
    for i, d in enumerate(durs):
        starts.append(t)
        t += d + (GAP if i < n - 1 else TAIL)
    total = t

    inputs, filt = [], []
    for i in range(n):
        inputs += ["-i", os.path.join(WORK, f"v{i + 1:02d}.wav")]
        filt.append(f"[{i}:a]adelay={int(starts[i] * 1000)}:all=1[a{i}]")
    filt.append("".join(f"[a{i}]" for i in range(n)) +
                f"amix=inputs={n}:normalize=0,apad,atrim=0:{total:.3f},loudnorm=I=-15:TP=-1.5[out]")
    voice = os.path.join(WORK, "voice.m4a")
    run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", ";".join(filt),
         "-map", "[out]", "-ar", "44100", "-c:a", "aac", "-b:a", "192k", voice])

    # 3. One clip per image, with a slow zoom.
    bounds = [0] + starts[1:] + [total]
    segs = []
    for i in range(n):
        step = (bounds[i + 1] - bounds[i]) / len(scenes[i])
        segs += [(img, step) for img in scenes[i]]
    frames, acc, cum = [], 0, 0.0
    for _, d in segs:
        cum += d
        f = round(cum * FPS) - acc
        acc += f
        frames.append(f)

    lst_path = os.path.join(WORK, "list.txt")
    with open(lst_path, "w") as lst:
        for j, ((img, _), f) in enumerate(zip(segs, frames)):
            z = f"'1+0.10*on/{f}'" if j % 2 == 0 else f"'1.10-0.10*on/{f}'"
            vf = (f"scale=2160:3840:force_original_aspect_ratio=increase,crop=2160:3840,"
                  f"zoompan=z={z}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={f}:s=1080x1920:fps={FPS},"
                  "format=yuv420p")
            if j == 0:
                vf += ",fade=t=in:st=0:d=0.6"
            if j == len(segs) - 1:
                vf += f",fade=t=out:st={f / FPS - 1.0:.2f}:d=1.0"
            out = os.path.join(WORK, f"s{j:02d}.mp4")
            run(["ffmpeg", "-v", "error", "-y", "-framerate", str(FPS), "-loop", "1",
                 "-t", f"{f / FPS:.4f}", "-i", os.path.join(ROOT, "images", img),
                 "-vf", vf, "-frames:v", str(f), "-c:v", "libx264", "-crf", "18",
                 "-preset", "veryfast", "-pix_fmt", "yuv420p", "-r", str(FPS), out])
            lst.write(f"file '{out}'\n")
    silent = os.path.join(WORK, "silent.mp4")
    run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst_path, "-c", "copy", silent])

    # 4. Kurdish subtitles.
    ass = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: K,{FONT},{FONT_SIZE},&H00FFFFFF,&H00FFFFFF,&H00101010,&H80000000,1,0,0,0,100,100,0,0,1,5,2,2,90,90,430,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    for i in range(n):
        ass += f"Dialogue: 0,{ts(starts[i])},{ts(starts[i] + durs[i] + 0.15)},K,,0,0,0,,{lines[i]}\n"
    ass_path = os.path.join(WORK, "subs.ass")
    open(ass_path, "w", encoding="utf-8").write(ass)

    # 5. Final video.
    tmp = os.path.join(WORK, "final.mp4")
    run(["ffmpeg", "-v", "error", "-y", "-i", silent, "-i", voice, "-vf", f"ass={ass_path}",
         "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-crf", "19", "-preset", "veryfast",
         "-pix_fmt", "yuv420p", "-c:a", "copy", "-shortest", "-movflags", "+faststart", tmp])
    shutil.move(tmp, OUT)
    print(f"Done: output.mp4 ({total:.1f} s, {len(segs)} images)")


if __name__ == "__main__":
    main()
