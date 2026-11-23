# chirok-videos

Turns pictures + a voice file per sentence into a vertical (1080×1920) video with Kurdish (Sorani) subtitles, using GitHub Actions.

## How to make a new video

1. Put your pictures in `images/` (for example from Google Flow).
2. Put one voice file per sentence in `voice/`: `01.wav`, `02.wav`, `03.wav` …
3. Write the story in `story.txt`, one sentence per line (same order as the voice files).
4. In `scenes.txt`, write on each line which picture(s) to show for that sentence, separated by commas.
5. Commit the changes. The video builds by itself, or go to **Actions → Make video → Run workflow**.
6. When it finishes (2–4 minutes), open the run and download **video** under **Artifacts**.

## Settings

- Voice speed: choose it when you press **Run workflow** (1.0 = normal).
- Font, subtitle size and pauses: at the top of `build.py`.

## Run on your own computer

Needs Python 3 and ffmpeg:

```
python3 build.py
```
