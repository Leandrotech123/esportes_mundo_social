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

class AssetCreator:
    W, H = 1080, 1080

    def _gradient_bg(self) -> Image.Image:
        img = Image.new("RGB", (self.W, self.H), BRAND_COLOR_BG)
        draw = ImageDraw.Draw(img)
        for y in range(self.H):
            t = y / self.H
            r = int(BRAND_COLOR_BG[0] + (30 - BRAND_COLOR_BG[0]) * t)
            g = int(BRAND_COLOR_BG[1] + (20 - BRAND_COLOR_BG[1]) * t)
            b = int(BRAND_COLOR_BG[2] + (55 - BRAND_COLOR_BG[2]) * t)
            draw.line([(0, y), (self.W, y)], fill=(r, g, b))
        return img

    def _fetch_shield(self, team_id) -> Image.Image | None:
        if not team_id:
            return None
        try:
            url = f"https://img.api-football.com/teams/{team_id}.png"
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                return Image.open(io.BytesIO(r.content)).convert("RGBA")
        except Exception:
            pass
        return None

    def _initials_badge(self, name: str, size: int = 200) -> Image.Image:
        badge = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(badge)
        draw.ellipse([0, 0, size - 1, size - 1], fill=(*BRAND_COLOR_ACCENT, 220))
        initials = "".join(w[0] for w in name.split()[:2]).upper()
        font = _font(int(size * 0.38))
        draw.text((size // 2, size // 2), initials, font=font,
                  fill=BRAND_COLOR_TEXT, anchor="mm")
        return badge

    def _team_badge(self, team_id, name: str, size: int = 200) -> Image.Image:
        shield = self._fetch_shield(team_id)
        if shield:
            shield = shield.resize((size, size), Image.LANCZOS)
            bg = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            bg.paste(shield, mask=shield.split()[3] if shield.mode == "RGBA" else None)
            return bg
        return self._initials_badge(name, size)

    def _footer_bar(self, img: Image.Image, league_label: str):
        draw = ImageDraw.Draw(img)
        bar_h = 72
        draw.rectangle([0, self.H - bar_h, self.W, self.H], fill=BRAND_COLOR_ACCENT)
        draw.text((self.W // 2, self.H - bar_h + bar_h // 2),
                  f"{league_label}  •  @esportes.mundo_",
                  font=_font(32, False), fill=BRAND_COLOR_TEXT, anchor="mm")

    def criar_imagem_jogo(
        self,
        home_team: str,
        away_team: str,
        horario: str,
        liga: str,
        home_team_id=None,
        away_team_id=None,
        evento_id: str | None = None,
    ) -> str:
        os.makedirs(POSTS_DIR, exist_ok=True)
        img = self._gradient_bg().convert("RGBA")
        draw = ImageDraw.Draw(img)

        league_label = LEAGUE_LABEL.get(liga, liga.replace("_", " ").title())

        # league name top
        draw.text((self.W // 2, 80), league_label.upper(),
                  font=_font(44, False), fill=BRAND_COLOR_ACCENT, anchor="mm")

        badge_size = 220
        badge_y = 300

        # home badge (left)
        home_badge = self._team_badge(home_team_id, home_team, badge_size)
        img.paste(home_badge, (self.W // 4 - badge_size // 2, badge_y), home_badge)

        # away badge (right)
        away_badge = self._team_badge(away_team_id, away_team, badge_size)
        img.paste(away_badge, (3 * self.W // 4 - badge_size // 2, badge_y), away_badge)

        # team names
        name_y = badge_y + badge_size + 40
        draw.text((self.W // 4, name_y), home_team.upper(),
                  font=_font(52), fill=BRAND_COLOR_TEXT, anchor="mm")
        draw.text((3 * self.W // 4, name_y), away_team.upper(),
                  font=_font(52), fill=BRAND_COLOR_TEXT, anchor="mm")

        # VS + time center
        vs_y = badge_y + badge_size // 2
        draw.text((self.W // 2, vs_y), "VS",
                  font=_font(110), fill=BRAND_COLOR_TEXT, anchor="mm")
        draw.text((self.W // 2, vs_y + 110), horario,
                  font=_font(58, False), fill=BRAND_COLOR_SECONDARY, anchor="mm")

        # divider lines
        line_x_left  = self.W // 4 + badge_size // 2 + 20
        line_x_right = 3 * self.W // 4 - badge_size // 2 - 20
        draw.line([(line_x_left, vs_y - 50), (line_x_left, vs_y + 50)],
                  fill=(*BRAND_COLOR_ACCENT, 160), width=3)
        draw.line([(line_x_right, vs_y - 50), (line_x_right, vs_y + 50)],
                  fill=(*BRAND_COLOR_ACCENT, 160), width=3)

        self._footer_bar(img, league_label)

        slug = evento_id or f"{home_team}_{away_team}".replace(" ", "_").lower()
        path = os.path.join(POSTS_DIR, f"{slug}.jpg")
        img.convert("RGB").save(path, "JPEG", quality=92)
        print(f"[ASSET] Jogo salvo: {path}")
        return path

    def criar_imagem_noticia(self, titulo: str, evento_id: str) -> str:
        os.makedirs(POSTS_DIR, exist_ok=True)
        prompt = titulo[:120].replace(" ", "%20")
        url = (f"https://image.pollinations.ai/prompt/{prompt}"
               f"?width=1080&height=1080&nologo=true&seed=42")
        try:
            r = requests.get(url, timeout=45)
            img = Image.open(io.BytesIO(r.content)).convert("RGB").resize((self.W, self.H))
        except Exception as e:
            print(f"[ASSET] Pollinations erro: {e} — usando fundo sólido")
            img = self._gradient_bg()

        img = img.convert("RGBA")

        # semi-transparent box bottom
        box_h = 320
        overlay = Image.new("RGBA", (self.W, box_h), (0, 0, 0, 0))
        draw_ov = ImageDraw.Draw(overlay)
        draw_ov.rectangle([0, 0, self.W, box_h], fill=(10, 10, 22, 210))
        img.paste(overlay, (0, self.H - box_h), overlay)

        draw = ImageDraw.Draw(img)
        lines = _wrap(titulo, 24)
        for i, line in enumerate(lines[:3]):
            draw.text((self.W // 2, self.H - box_h + 60 + i * 82), line,
                      font=_font(60), fill=BRAND_COLOR_TEXT, anchor="mm")

        self._footer_bar(img, "Esportes Mundo")

        path = os.path.join(POSTS_DIR, f"news_{evento_id}.jpg")
        img.convert("RGB").save(path, "JPEG", quality=92)
        print(f"[ASSET] Notícia salva: {path}")
        return path


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
