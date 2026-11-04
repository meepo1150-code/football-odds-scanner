"""Isolated visual-only football video MVP; never fabricates predictions or scores."""
import argparse
import hashlib
import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

WIDTH, HEIGHT = 1920, 1080


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def fingerprint(record):
    return hashlib.sha256(json.dumps(record, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def iso_time(value):
    result = datetime.fromisoformat(value)
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("All timestamps require UTC offsets")
    return result


def validate(data):
    if not isinstance(data.get("predictions"), list) or not data.get("date"):
        raise ValueError("date and predictions are required")
    published = iso_time(data["published_at"])
    seen = set()
    for item in data["predictions"]:
        required = ("id", "fixture_id", "kickoff", "home", "away", "market", "selection", "label")
        if any(not str(item.get(field, "")).strip() for field in required):
            raise ValueError("Incomplete prediction record")
        if item["id"] in seen:
            raise ValueError("Duplicate prediction id")
        seen.add(item["id"])
        if iso_time(item["kickoff"]) <= published:
            raise ValueError("Prediction cannot be published at/after kickoff")
        if item["market"] in ("AH", "OU") and not isinstance(item.get("line"), (int, float)):
            raise ValueError("AH/OU requires numeric line")
    if data.get("source_type") == "SYNTHETIC_DEMO_DO_NOT_PUBLISH":
        return "DEMO"
    if data.get("source_type") != "REVIEWED_PREDICTION":
        raise ValueError("Only explicitly reviewed predictions accepted")
    return "REVIEWED"


def append_ledger(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    previous = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rec = json.loads(line)
                if rec["id"] in previous and fingerprint(previous[rec["id"]]) != fingerprint(rec):
                    raise ValueError("Existing ledger contains ID conflict")
                previous[rec["id"]] = rec
    to_add = []
    for item in data["predictions"]:
        rec = {**item, "published_at": data["published_at"], "source_type": data["source_type"]}
        if rec["id"] in previous:
            if fingerprint(rec) != fingerprint(previous[rec["id"]]):
                raise ValueError("Immutable prediction conflict: " + rec["id"])
        else:
            to_add.append(rec)
    if to_add:
        with path.open("a", encoding="utf-8") as output:
            for rec in to_add:
                output.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")
    return len(to_add)


def render_card(path, heading, lines, label):
    from PIL import Image, ImageDraw, ImageFont
    image = Image.new("RGB", (WIDTH, HEIGHT), (9, 20, 39))
    draw = ImageDraw.Draw(image)
    fonts = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"]
    fontpath = next((f for f in fonts if Path(f).exists()), None)
    if fontpath is None:
        raise RuntimeError("A TrueType font is required")
    headline = ImageFont.truetype(fontpath, 80)
    body = ImageFont.truetype(fontpath, 47)
    tiny = ImageFont.truetype(fontpath, 32)
    draw.rounded_rectangle((65, 70, 1855, 1010), radius=32, outline=(58, 91, 137), width=5)
    draw.text((115, 115), heading[:35], font=headline, fill=(250, 252, 255))
    draw.line((115, 240, 1805, 240), fill=(57, 199, 175), width=7)
    y = 290
    for line in lines[:9]:
        draw.text((120, y), str(line)[:61], font=body, fill=(222, 235, 246))
        y += 78
    draw.text((120, 930), label[:90], font=tiny, fill=(132, 169, 192))
    image.save(path)


def make_video(out, slides):
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return False
    concat = out / "frames.txt"
    with concat.open("w", encoding="utf-8") as f:
        for i, slide in enumerate(slides):
            f.write("file '" + slide.name + "'\n")
            f.write("duration " + ("4" if i else "3") + "\n")
        f.write("file '" + slides[-1].name + "'\n")
    subprocess.run([ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-safe", "0", "-f", "concat", "-i", str(concat), "-vf", "fps=30,format=yuv420p", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(out / "video.mp4")], cwd=str(out), check=True)
    return True


def build(data, out, ledger):
    status = validate(data)
    out.mkdir(parents=True, exist_ok=True)
    n = append_ledger(ledger, data)
    results = data.get("results", [])
    # Results are display-only pending a verified fixture-id settlement adapter.
    if results:
        raise ValueError("Results display blocked until verified settlement adapter is implemented")
    slides = []
    first = out / "slide-00.png"
    render_card(first, "FOOTBALL PREDICTIONS", [data["date"], "Today's reviewed picks", str(len(data["predictions"])) + " matches"], "Prediction history is archived before kickoff")
    slides.append(first)
    intro = out / "slide-01.png"
    render_card(intro, "YESTERDAY'S RESULTS", ["Results pending verified FT settlement"], "No unverified win-rate claims")
    slides.append(intro)
    for i, item in enumerate(data["predictions"], 2):
        image = out / ("slide-%02d.png" % i)
        render_card(image, "MATCH PREDICTION", [item["home"] + " vs " + item["away"], item["kickoff"], item["label"]], "Fixture: " + item["fixture_id"])
        slides.append(image)
    recap = out / ("slide-%02d.png" % len(slides))
    render_card(recap, "TODAY'S PICKS RECAP", [p["home"] + " vs " + p["away"] + " | " + p["label"] for p in data["predictions"]], "Come back tomorrow for the results")
    slides.append(recap)
    shutil.copyfile(first, out / "thumbnail.png")
    metadata = {"title": data.get("title", "Daily Football Predictions " + data["date"]), "description": "Daily football predictions. Individual results are independently verifiable from the archived picks. No guaranteed outcomes.", "privacyStatus": "private", "demo": status == "DEMO"}
    (out / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    made_video = make_video(out, slides)
    manifest = {"mode": status, "predictions": len(data["predictions"]), "ledger_records_appended": n, "video_created": made_video, "audio_created": False, "verified_results_created": False, "youtube_uploaded": False}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--ledger", required=True)
    opts = parser.parse_args()
    print(json.dumps(build(read_json(opts.input), Path(opts.output), Path(opts.ledger)), indent=2))
