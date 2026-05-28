"""投稿本文からInstagramリール用の縦動画(1080x1920)を生成する。

- VOICEVOXで文ごとにナレーション音声を生成
- PILで「もち太+字幕」フレームを文ごとに描画
- ffmpegで各文を音声長クリップ化→連結してMP4出力

環境変数:
  POST_TEXT          : 動画にする投稿本文(必須)
  VOICEVOX_URL       : VOICEVOXエンジンのURL(既定 http://localhost:50021)
  VOICEVOX_SPEAKER   : 話者ID(既定 3 = ずんだもん ノーマル)
"""

import json
import os
import re
import subprocess
import sys
import urllib.parse
import urllib.request
import wave
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

POST_TEXT = os.environ["POST_TEXT"]
VOICEVOX_URL = os.environ.get("VOICEVOX_URL", "http://localhost:50021")
SPEAKER = int(os.environ.get("VOICEVOX_SPEAKER", "3"))

REPO_ROOT = Path(__file__).parent
OUT_DIR = REPO_ROOT / "out"
WORK_DIR = OUT_DIR / "work"
ASSETS_DIR = REPO_ROOT / "assets" / "mochita"

W, H = 1080, 1920
BG_TOP = (26, 26, 46)
BG_BOTTOM = (40, 22, 62)
TEXT_COLOR = (245, 245, 245)
STROKE_COLOR = (0, 0, 0)
HANDLE = "@_x_saku_"

FONT_CANDIDATES = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc",
]
FONT_PATH = next((p for p in FONT_CANDIDATES if Path(p).exists()), None)


def split_sentences(text: str) -> list:
    parts = re.split(r"(?<=[。！？\n])", text)
    return [p.strip() for p in parts if p.strip()]


def voicevox_tts(text: str, out_wav: Path) -> None:
    query_req = urllib.request.Request(
        f"{VOICEVOX_URL}/audio_query?speaker={SPEAKER}&text={urllib.parse.quote(text)}",
        method="POST",
    )
    with urllib.request.urlopen(query_req, timeout=60) as r:
        query = json.loads(r.read().decode("utf-8"))
    # 少し抑揚と間を整える
    query["speedScale"] = 1.05
    query["pauseLength"] = 0.4

    synth_req = urllib.request.Request(
        f"{VOICEVOX_URL}/synthesis?speaker={SPEAKER}",
        data=json.dumps(query).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(synth_req, timeout=180) as r:
        out_wav.write_bytes(r.read())


def wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as w:
        return w.getnframes() / float(w.getframerate())


def paint_gradient(img: Image.Image) -> None:
    draw = ImageDraw.Draw(img)
    for y in range(H):
        ratio = y / (H - 1)
        r = int(BG_TOP[0] + (BG_BOTTOM[0] - BG_TOP[0]) * ratio)
        g = int(BG_TOP[1] + (BG_BOTTOM[1] - BG_TOP[1]) * ratio)
        b = int(BG_TOP[2] + (BG_BOTTOM[2] - BG_TOP[2]) * ratio)
        draw.line([(0, y), (W, y)], fill=(r, g, b))


def load_mascot() -> Image.Image | None:
    if not ASSETS_DIR.exists():
        return None
    files = sorted(
        p for p in ASSETS_DIR.iterdir()
        if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp")
    )
    if not files:
        return None
    return Image.open(files[0]).convert("RGBA")


def wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list:
    lines, current = [], ""
    for ch in text:
        trial = current + ch
        if font.getbbox(trial)[2] <= max_width or not current:
            current = trial
        else:
            lines.append(current)
            current = ch
    if current:
        lines.append(current)
    return lines


def render_frame(sentence: str, mascot: Image.Image | None, save_path: Path) -> None:
    img = Image.new("RGB", (W, H), BG_TOP)
    paint_gradient(img)

    # もち太(上半分中央)
    if mascot is not None:
        m = mascot.copy()
        target_w = int(W * 0.55)
        scale = target_w / m.width
        m = m.resize((target_w, int(m.height * scale)))
        x = (W - m.width) // 2
        y = int(H * 0.13)
        img.paste(m, (x, y), m if m.mode == "RGBA" else None)

    draw = ImageDraw.Draw(img)
    padding = 80
    inner = W - padding * 2

    # 字幕(下半分)
    font_size = 64 if len(sentence) <= 40 else 54
    font = ImageFont.truetype(FONT_PATH, font_size, index=0)
    lines = wrap_text(sentence, font, inner)
    line_h = int(font_size * 1.5)
    block_h = line_h * len(lines)
    start_y = int(H * 0.62)
    for i, line in enumerate(lines):
        bbox = font.getbbox(line)
        lw = bbox[2] - bbox[0]
        x = (W - lw) // 2
        y = start_y + i * line_h
        draw.text(
            (x, y), line, font=font, fill=TEXT_COLOR,
            stroke_width=6, stroke_fill=STROKE_COLOR,
        )

    # ハンドル(最下部)
    handle_font = ImageFont.truetype(FONT_PATH, 38, index=0)
    hb = handle_font.getbbox(HANDLE)
    draw.text(
        ((W - (hb[2] - hb[0])) // 2, H - 110),
        HANDLE, font=handle_font, fill=(180, 180, 190),
        stroke_width=3, stroke_fill=STROKE_COLOR,
    )

    img.save(save_path, "PNG")


def make_segment(frame_png: Path, audio_wav: Path, out_mp4: Path) -> None:
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-loop", "1", "-i", str(frame_png),
            "-i", str(audio_wav),
            "-c:v", "libx264", "-tune", "stillimage",
            "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-vf", f"scale={W}:{H}",
            "-shortest",
            str(out_mp4),
        ],
        check=True,
        capture_output=True,
    )


def concat_segments(segments: list, out_mp4: Path) -> None:
    list_file = WORK_DIR / "segments.txt"
    list_file.write_text(
        "".join(f"file '{seg.resolve()}'\n" for seg in segments), encoding="utf-8"
    )
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0", "-i", str(list_file),
            "-c", "copy",
            str(out_mp4),
        ],
        check=True,
        capture_output=True,
    )


def main() -> None:
    if not FONT_PATH:
        print("Japanese font not found.", file=sys.stderr)
        sys.exit(1)

    OUT_DIR.mkdir(exist_ok=True)
    WORK_DIR.mkdir(parents=True, exist_ok=True)

    sentences = split_sentences(POST_TEXT)
    if not sentences:
        print("No sentences in POST_TEXT.", file=sys.stderr)
        sys.exit(1)
    print(f"{len(sentences)} sentences")

    mascot = load_mascot()
    print(f"Mascot: {'loaded' if mascot else 'none (gradient only)'}")

    segments = []
    for i, sentence in enumerate(sentences):
        frame_png = WORK_DIR / f"frame_{i}.png"
        audio_wav = WORK_DIR / f"audio_{i}.wav"
        seg_mp4 = WORK_DIR / f"seg_{i}.mp4"

        voicevox_tts(sentence, audio_wav)
        dur = wav_duration(audio_wav)
        render_frame(sentence, mascot, frame_png)
        make_segment(frame_png, audio_wav, seg_mp4)
        segments.append(seg_mp4)
        print(f"  [{i + 1}/{len(sentences)}] {dur:.1f}s  {sentence[:30]}")

    final = OUT_DIR / "reel.mp4"
    concat_segments(segments, final)
    print(f"Done: {final} ({final.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
