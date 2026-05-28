"""もち太のシーン静止画(ChatGPT製)に Ken Burns(ゆっくりズーム/パン)演出を付け、
VOICEVOXナレーション + 字幕を重ねてInstagramリール(1080x1920)を生成する無料版。

AI動画API不要。ffmpeg + PIL + VOICEVOX だけで完結。

前提:
- assets/scenes/ に もち太のシーン静止画(1.png, 2.png, ...)を配置(ナレーション順)

環境変数:
  POST_TEXT          : 動画にする投稿本文(必須)
  VOICEVOX_URL       : 既定 http://localhost:50021
  VOICEVOX_SPEAKER   : 既定 3 (ずんだもん)
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
SCENES_DIR = REPO_ROOT / "assets" / "scenes"

W, H = 1080, 1920
FPS = 30
TEXT_COLOR = (255, 255, 255)
STROKE_COLOR = (0, 0, 0)
HANDLE = "@_x_saku_"

FONT_CANDIDATES = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
]
FONT_PATH = next((p for p in FONT_CANDIDATES if Path(p).exists()), None)


def split_sentences(text: str) -> list:
    parts = re.split(r"(?<=[。！？\n])", text)
    return [p.strip() for p in parts if p.strip()]


def voicevox_tts(text: str, out_wav: Path) -> None:
    q = urllib.request.Request(
        f"{VOICEVOX_URL}/audio_query?speaker={SPEAKER}&text={urllib.parse.quote(text)}",
        method="POST",
    )
    with urllib.request.urlopen(q, timeout=60) as r:
        query = json.loads(r.read().decode("utf-8"))
    query["speedScale"] = 1.05
    query["pauseLength"] = 0.4
    s = urllib.request.Request(
        f"{VOICEVOX_URL}/synthesis?speaker={SPEAKER}",
        data=json.dumps(query).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(s, timeout=180) as r:
        out_wav.write_bytes(r.read())


def wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as w:
        return w.getnframes() / float(w.getframerate())


def render_subtitle_png(sentence: str, save_path: Path) -> None:
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    padding = 70
    inner = W - padding * 2

    font_size = 64 if len(sentence) <= 38 else 54
    font = ImageFont.truetype(FONT_PATH, font_size, index=0)

    lines, cur = [], ""
    for ch in sentence:
        t = cur + ch
        if font.getbbox(t)[2] <= inner or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = ch
    if cur:
        lines.append(cur)

    line_h = int(font_size * 1.5)
    block_h = line_h * len(lines)
    start_y = H - 520 - block_h

    draw.rectangle(
        [0, start_y - 30, W, start_y + block_h + 30],
        fill=(0, 0, 0, 115),
    )
    for i, line in enumerate(lines):
        bbox = font.getbbox(line)
        lw = bbox[2] - bbox[0]
        x = (W - lw) // 2
        y = start_y + i * line_h
        draw.text(
            (x, y), line, font=font, fill=TEXT_COLOR,
            stroke_width=6, stroke_fill=STROKE_COLOR,
        )

    handle_font = ImageFont.truetype(FONT_PATH, 36, index=0)
    hb = handle_font.getbbox(HANDLE)
    draw.text(
        ((W - (hb[2] - hb[0])) // 2, H - 120),
        HANDLE, font=handle_font, fill=(230, 230, 235),
        stroke_width=3, stroke_fill=STROKE_COLOR,
    )
    img.save(save_path, "PNG")


def build_segment(scene_img: Path, sub_png: Path, audio_wav: Path,
                  duration: float, scene_index: int, out_mp4: Path) -> None:
    """静止画にKen Burns(ズーム+パン)を付け、字幕を重ね、ナレーションを付与した1セグメント。"""
    frames = max(2, round(duration * FPS))
    big_w, big_h = int(W * 1.5), int(H * 1.5)

    # シーンごとにズーム方向を変えて単調さを回避
    zoom_expr = "min(1+0.0010*on,1.20)"
    if scene_index % 3 == 0:
        x_expr, y_expr = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"   # 中央ズーム
    elif scene_index % 3 == 1:
        x_expr, y_expr = "0", "ih/2-(ih/zoom/2)"                   # 左から
    else:
        x_expr, y_expr = "iw-(iw/zoom)", "ih/2-(ih/zoom/2)"        # 右から

    vf = (
        f"[0:v]scale={big_w}:{big_h}:force_original_aspect_ratio=cover,"
        f"crop={big_w}:{big_h},"
        f"zoompan=z='{zoom_expr}':x='{x_expr}':y='{y_expr}':"
        f"d={frames}:s={W}x{H}:fps={FPS}[bg];"
        f"[bg][2:v]overlay=0:0[v]"
    )
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", str(scene_img),
            "-i", str(audio_wav),
            "-i", str(sub_png),
            "-filter_complex", vf,
            "-map", "[v]", "-map", "1:a",
            "-r", str(FPS),
            "-t", f"{duration:.3f}",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k",
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
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
            str(out_mp4),
        ],
        check=True,
        capture_output=True,
    )


def main() -> None:
    if not FONT_PATH:
        print("Japanese font not found.", file=sys.stderr)
        sys.exit(1)

    scenes = sorted(
        p for p in SCENES_DIR.iterdir()
        if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp")
    ) if SCENES_DIR.exists() else []
    if not scenes:
        print(f"No scene images in {SCENES_DIR}. もち太のシーン画像を置いてください。", file=sys.stderr)
        sys.exit(1)

    OUT_DIR.mkdir(exist_ok=True)
    WORK_DIR.mkdir(parents=True, exist_ok=True)

    sentences = split_sentences(POST_TEXT)
    print(f"{len(sentences)} sentences, {len(scenes)} scene images")

    segments = []
    for i, sentence in enumerate(sentences):
        scene_img = scenes[i] if i < len(scenes) else scenes[-1]
        audio_wav = WORK_DIR / f"audio_{i}.wav"
        sub_png = WORK_DIR / f"sub_{i}.png"
        seg_mp4 = WORK_DIR / f"seg_{i}.mp4"

        voicevox_tts(sentence, audio_wav)
        dur = wav_duration(audio_wav)
        render_subtitle_png(sentence, sub_png)
        build_segment(scene_img, sub_png, audio_wav, dur, i, seg_mp4)
        segments.append(seg_mp4)
        print(f"  [{i + 1}/{len(sentences)}] {dur:.1f}s {scene_img.name}: {sentence[:26]}")

    final = OUT_DIR / "reel.mp4"
    concat_segments(segments, final)
    print(f"Done: {final} ({final.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
