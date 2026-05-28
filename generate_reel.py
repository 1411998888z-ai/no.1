"""もち太のシーン静止画(ChatGPT製)を Kling で動画化し、
VOICEVOXナレーション + 字幕を重ねてInstagramリール(1080x1920)を生成する。

前提:
- assets/scenes/ に もち太のシーン静止画(1.png, 2.png, ...)を配置(ナレーション順)
- Kling は Replicate 経由で呼ぶ(REPLICATE_API_TOKEN が必要)

環境変数:
  POST_TEXT             : 動画にする投稿本文(必須)
  REPLICATE_API_TOKEN   : Replicateのトークン(必須)
  VOICEVOX_URL          : 既定 http://localhost:50021
  VOICEVOX_SPEAKER      : 既定 3 (ずんだもん)
  KLING_MODEL           : Replicateのモデル(既定は下記)
  MOTION_PROMPT         : 動きの指示(英語、既定あり)
"""

import base64
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
import urllib.parse
import wave
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

POST_TEXT = os.environ["POST_TEXT"]
REPLICATE_API_TOKEN = os.environ["REPLICATE_API_TOKEN"]
VOICEVOX_URL = os.environ.get("VOICEVOX_URL", "http://localhost:50021")
SPEAKER = int(os.environ.get("VOICEVOX_SPEAKER", "3"))
KLING_MODEL = os.environ.get("KLING_MODEL", "kwaivgi/kling-v1.6-standard")
MOTION_PROMPT = os.environ.get(
    "MOTION_PROMPT",
    "The cute mascot character moves gently and expressively, subtle idle animation, "
    "soft camera motion, keep the character design consistent, kawaii style.",
)

REPO_ROOT = Path(__file__).parent
OUT_DIR = REPO_ROOT / "out"
WORK_DIR = OUT_DIR / "work"
SCENES_DIR = REPO_ROOT / "assets" / "scenes"

W, H = 1080, 1920
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


def kling_animate(image_path: Path, out_mp4: Path) -> None:
    """Replicate経由でKling image-to-video。生成された動画をout_mp4に保存。"""
    img_b64 = base64.b64encode(image_path.read_bytes()).decode("ascii")
    suffix = image_path.suffix.lower().lstrip(".")
    mime = "jpeg" if suffix in ("jpg", "jpeg") else suffix
    data_uri = f"data:image/{mime};base64,{img_b64}"

    body = {
        "input": {
            "start_image": data_uri,
            "prompt": MOTION_PROMPT,
            "duration": 5,
            "aspect_ratio": "9:16",
            "cfg_scale": 0.5,
        }
    }
    # モデルにバージョン指定が無い場合は owner/name 形式でそのまま使う
    create_url = f"https://api.replicate.com/v1/models/{KLING_MODEL}/predictions"
    req = urllib.request.Request(
        create_url,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {REPLICATE_API_TOKEN}",
            "Content-Type": "application/json",
            "Prefer": "wait",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        pred = json.loads(r.read().decode("utf-8"))

    # Prefer: wait で完了まで待つが、念のためポーリングもする
    get_url = pred.get("urls", {}).get("get")
    status = pred.get("status")
    deadline = time.time() + 600
    while status not in ("succeeded", "failed", "canceled") and time.time() < deadline:
        time.sleep(5)
        gr = urllib.request.Request(
            get_url, headers={"Authorization": f"Bearer {REPLICATE_API_TOKEN}"}
        )
        with urllib.request.urlopen(gr, timeout=60) as r:
            pred = json.loads(r.read().decode("utf-8"))
        status = pred.get("status")

    if status != "succeeded":
        raise RuntimeError(f"Kling failed: status={status} detail={pred.get('error')}")

    output = pred.get("output")
    video_url = output[0] if isinstance(output, list) else output
    with urllib.request.urlopen(video_url, timeout=180) as r:
        out_mp4.write_bytes(r.read())


def render_subtitle_png(sentence: str, save_path: Path) -> None:
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    padding = 70
    inner = W - padding * 2

    font_size = 64 if len(sentence) <= 38 else 54
    font = ImageFont.truetype(FONT_PATH, font_size, index=0)

    # 文字単位折り返し
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
    start_y = H - 520 - block_h  # 下から少し上に配置

    # 半透明の帯で可読性UP
    band_pad = 30
    draw.rectangle(
        [0, start_y - band_pad, W, start_y + block_h + band_pad],
        fill=(0, 0, 0, 110),
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


def build_segment(clip_mp4: Path, sub_png: Path, audio_wav: Path, duration: float, out_mp4: Path) -> None:
    """Klingクリップを9:16にし、字幕を重ね、音声長に合わせて尺調整、音声を付与。"""
    vf = (
        f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,"
        f"crop={W}:{H},tpad=stop_mode=clone:stop_duration=30[v0];"
        f"[v0][1:v]overlay=0:0[v]"
    )
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", str(clip_mp4),
            "-i", str(sub_png),
            "-i", str(audio_wav),
            "-filter_complex", vf,
            "-map", "[v]", "-map", "2:a",
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
        clip_mp4 = WORK_DIR / f"clip_{i}.mp4"
        sub_png = WORK_DIR / f"sub_{i}.png"
        seg_mp4 = WORK_DIR / f"seg_{i}.mp4"

        print(f"  [{i + 1}/{len(sentences)}] TTS...")
        voicevox_tts(sentence, audio_wav)
        dur = wav_duration(audio_wav)

        print(f"  [{i + 1}/{len(sentences)}] Kling animating {scene_img.name}...")
        kling_animate(scene_img, clip_mp4)

        render_subtitle_png(sentence, sub_png)
        build_segment(clip_mp4, sub_png, audio_wav, dur, seg_mp4)
        segments.append(seg_mp4)
        print(f"  [{i + 1}/{len(sentences)}] segment done ({dur:.1f}s): {sentence[:28]}")

    final = OUT_DIR / "reel.mp4"
    concat_segments(segments, final)
    print(f"Done: {final} ({final.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
