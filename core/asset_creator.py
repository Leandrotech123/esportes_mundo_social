import os
import io
import requests
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
from config import ASSETS_DIR, OUTPUTS_DIR, BRAND_COLOR_BG, BRAND_COLOR_ACCENT, BRAND_COLOR_TEXT, BRAND_COLOR_SECONDARY
from core.ai_generator import generate_image_prompt

POSTS_DIR = os.path.join(OUTPUTS_DIR, "posts")
STORIES_DIR = os.path.join(OUTPUTS_DIR, "stories")
FONTS_DIR = os.path.join(ASSETS_DIR, "fonts")

LEAGUE_LABEL = {
    "bra.1": "🇧🇷 Brasileirão",
    "eng.1": "Premier League",
    "esp.1": "La Liga",
    "uefa.champions": "⭐ Champions",
    "ita.1": "Serie A",
    "nba": "🏀 NBA",
}

os.makedirs(POSTS_DIR, exist_ok=True)
os.makedirs(STORIES_DIR, exist_ok=True)


# ─────────────────────────────────────────────
# Font loader
# ─────────────────────────────────────────────

def _font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    names = (
        ["BigShoulders-Bold.ttf", "BricolageGrotesque-Bold.ttf"]
        if bold else
        ["InstrumentSans-Regular.ttf", "BigShoulders-Bold.ttf"]
    )
    search_dirs = [
        FONTS_DIR,
        os.path.expanduser("~/Origem360_AI/assets"),
        os.path.expanduser("~/Origem360_AI/assets/fonts"),
    ]
    for name in names:
        for d in search_dirs:
            p = os.path.join(d, name)
            if os.path.exists(p):
                try:
                    return ImageFont.truetype(p, size)
                except Exception:
                    continue
    return ImageFont.load_default()


# ─────────────────────────────────────────────
# Background
# ─────────────────────────────────────────────

def _background(prompt: str, w: int, h: int) -> Image.Image:
    safe = prompt.replace(" ", "%20")[:180]
    url = f"https://image.pollinations.ai/prompt/{safe}?width={w}&height={h}&nologo=true&seed=42"
    try:
        r = requests.get(url, timeout=30)
        if r.status_code == 200:
            return Image.open(io.BytesIO(r.content)).convert("RGB").resize((w, h))
    except Exception as e:
        print(f"[ASSET] Background erro: {e}")
    return Image.new("RGB", (w, h), BRAND_COLOR_BG)


# ─────────────────────────────────────────────
# Text wrapper
# ─────────────────────────────────────────────

def _wrap(text: str, max_chars: int) -> list[str]:
    words = text.split()
    lines, line = [], []
    for w in words:
        line.append(w)
        if len(" ".join(line)) > max_chars:
            lines.append(" ".join(line[:-1]))
            line = [w]
    if line:
        lines.append(" ".join(line))
    return lines


# ─────────────────────────────────────────────
# Overlays
# ─────────────────────────────────────────────

def _draw_gradient_overlay(img: Image.Image, start_y_pct: float = 0.45):
    w, h = img.size
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    start_y = int(h * start_y_pct)
    for y in range(start_y, h):
        alpha = min(235, int(235 * (y - start_y) / (h - start_y) * 1.4))
        draw.line([(0, y), (w, y)], fill=(*BRAND_COLOR_BG, alpha))
    img.paste(overlay, mask=overlay)


def _draw_score_card(img: Image.Image, game: dict):
    w, h = img.size
    _draw_gradient_overlay(img, 0.42)
    draw = ImageDraw.Draw(img)

    league_text = LEAGUE_LABEL.get(game.get("league", ""), "⚽ Futebol")
    home = game.get("home_team", "")[:14]
    away = game.get("away_team", "")[:14]
    hs, as_ = game.get("home_score", 0), game.get("away_score", 0)
    status_map = {"live": "⚡ AO VIVO", "finished": "✅ ENCERRADO", "scheduled": "⏰ EM BREVE"}
    status_text = status_map.get(game.get("status", ""), "")

    draw.text((w // 2, int(h * 0.54)), league_text,
              font=_font(38, False), fill=BRAND_COLOR_ACCENT, anchor="mm")
    draw.text((w // 4, int(h * 0.66)), home,
              font=_font(80), fill=BRAND_COLOR_TEXT, anchor="mm")
    draw.text((w * 3 // 4, int(h * 0.66)), away,
              font=_font(80), fill=BRAND_COLOR_TEXT, anchor="mm")
    draw.text((w // 2, int(h * 0.78)), f"{hs}  ×  {as_}",
              font=_font(130), fill=BRAND_COLOR_ACCENT, anchor="mm")
    draw.text((w // 2, int(h * 0.88)), status_text,
              font=_font(40, False), fill=BRAND_COLOR_SECONDARY, anchor="mm")
    draw.rectangle([0, h - 8, w, h], fill=BRAND_COLOR_ACCENT)


def _draw_news_card(img: Image.Image, title: str):
    w, h = img.size
    _draw_gradient_overlay(img, 0.48)
    draw = ImageDraw.Draw(img)

    draw.text((w // 2, int(h * 0.58)), "ESPORTES MUNDO",
              font=_font(38, False), fill=BRAND_COLOR_ACCENT, anchor="mm")
    lines = _wrap(title, 22)
    for i, line in enumerate(lines[:3]):
        draw.text((w // 2, int(h * 0.68) + i * 78), line,
                  font=_font(68), fill=BRAND_COLOR_TEXT, anchor="mm")
    draw.rectangle([0, h - 8, w, h], fill=BRAND_COLOR_ACCENT)


def _paste_logo(img: Image.Image):
    logo_path = os.path.join(ASSETS_DIR, "logos", "logo.png")
    if not os.path.exists(logo_path):
        return
    try:
        logo = Image.open(logo_path).convert("RGBA")
        logo.thumbnail((110, 110))
        img.paste(logo, (img.width - 130, 24), logo)
    except Exception:
        pass


# ─────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────

def create_post_image(content: dict) -> str:
    raw = content.get("raw_data", {})
    is_story = content.get("type") == "story"
    size = (1080, 1920) if is_story else (1080, 1080)
    out_dir = STORIES_DIR if is_story else POSTS_DIR

    vis_prompt = generate_image_prompt(raw)
    img = _background(vis_prompt, *size)

    if "home_team" in raw:
        _draw_score_card(img, raw)
    else:
        _draw_news_card(img, raw.get("title", content.get("title", "")))

    _paste_logo(img)

    slug = (content.get("title") or "post")[:28].replace(" ", "_").replace("/", "-")
    filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{slug}.jpg"
    path = os.path.join(out_dir, filename)
    img.convert("RGB").save(path, "JPEG", quality=92)
    print(f"[ASSET] Criado: {filename}")
    return path
