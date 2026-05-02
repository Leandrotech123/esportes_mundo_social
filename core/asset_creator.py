import os
import io
import requests
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
from config import ASSETS_DIR, OUTPUTS_DIR, BASE_DIR, BRAND_COLOR_BG, BRAND_COLOR_ACCENT, BRAND_COLOR_TEXT, BRAND_COLOR_SECONDARY

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

# Cores por liga para o fallback Pillow
LEAGUE_COLORS = {
    "bra.1":          {"bg": (0, 82, 33),    "accent": (255, 215, 0),  "label": "BRASILEIRÃO"},
    "eng.1":          {"bg": (61, 26, 120),   "accent": (255, 255, 255), "label": "PREMIER LEAGUE"},
    "esp.1":          {"bg": (173, 18, 31),   "accent": (255, 196, 0),  "label": "LA LIGA"},
    "uefa.champions": {"bg": (0, 48, 135),    "accent": (255, 215, 0),  "label": "CHAMPIONS LEAGUE"},
    "ita.1":          {"bg": (0, 70, 170),    "accent": (20, 20, 20),   "label": "SERIE A"},
    "nba":            {"bg": (29, 66, 138),   "accent": (200, 16, 46),  "label": "NBA"},
}

os.makedirs(POSTS_DIR, exist_ok=True)
os.makedirs(STORIES_DIR, exist_ok=True)

MIN_IMAGE_BYTES = 10_000


def _relpath(abs_path: str) -> str:
    return os.path.relpath(abs_path, BASE_DIR).replace("\\", "/")


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
# Busca de imagem: Unsplash → Wikimedia → None
# ─────────────────────────────────────────────

def _buscar_imagem_esportiva(league: str = "", home_team: str = "", away_team: str = "",
                              w: int = 1080, h: int = 1080) -> "Image.Image | None":
    league_lower = str(league).lower()
    is_basketball = any(x in league_lower for x in ["nba", "basketball", "basquete"])

    # — Unsplash (50 req/hora, imagens reais de alta qualidade) —
    unsplash_key = os.getenv("UNSPLASH_ACCESS_KEY", "")
    if unsplash_key:
        query = "NBA basketball arena game" if is_basketball else "soccer football stadium match crowd"
        try:
            r = requests.get(
                "https://api.unsplash.com/photos/random",
                params={"query": query, "orientation": "squarish", "content_filter": "high"},
                headers={"Authorization": f"Client-ID {unsplash_key}"},
                timeout=10,
            )
            if r.status_code == 200:
                img_url = r.json()["urls"]["regular"]
                img_data = requests.get(img_url, timeout=15).content
                if len(img_data) >= MIN_IMAGE_BYTES:
                    print(f"[ASSET] Unsplash: OK ({len(img_data)//1024}KB)")
                    return Image.open(io.BytesIO(img_data)).convert("RGB").resize((w, h))
                print(f"[ASSET] Unsplash: imagem pequena ({len(img_data)} bytes)")
            else:
                print(f"[ASSET] Unsplash: HTTP {r.status_code}")
        except Exception as e:
            print(f"[ASSET] Unsplash erro: {e}")

    # — Wikimedia Commons (gratuito, sem chave) —
    search_term = "NBA basketball game arena" if is_basketball else "football soccer match stadium"
    try:
        r = requests.get(
            "https://commons.wikimedia.org/w/api.php",
            params={
                "action": "query", "generator": "search",
                "gsrsearch": f"file:{search_term}",
                "gsrnamespace": 6, "gsrlimit": 8,
                "prop": "imageinfo", "iiprop": "url|mime|size",
                "iiurlwidth": w, "format": "json",
            },
            timeout=10,
        )
        if r.status_code == 200:
            pages = r.json().get("query", {}).get("pages", {})
            for page in pages.values():
                ii = page.get("imageinfo", [{}])[0]
                mime = ii.get("mime", "")
                if mime.startswith("image/jpeg") or mime.startswith("image/png"):
                    img_url = ii.get("thumburl") or ii.get("url")
                    if img_url:
                        img_data = requests.get(img_url, timeout=15).content
                        if len(img_data) >= MIN_IMAGE_BYTES:
                            print(f"[ASSET] Wikimedia: OK ({len(img_data)//1024}KB)")
                            return Image.open(io.BytesIO(img_data)).convert("RGB").resize((w, h))
        print("[ASSET] Wikimedia: nenhuma imagem válida")
    except Exception as e:
        print(f"[ASSET] Wikimedia erro: {e}")

    return None


# ─────────────────────────────────────────────
# Text wrapper
# ─────────────────────────────────────────────

def _wrap(text: str, max_chars: int) -> list:
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
# Overlays (usados no create_post_image legado)
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
# AssetCreator
# ─────────────────────────────────────────────

class AssetCreator:
    W, H = 1080, 1080

    def _league_palette(self, liga: str) -> dict:
        return LEAGUE_COLORS.get(liga, {"bg": BRAND_COLOR_BG, "accent": BRAND_COLOR_ACCENT, "label": "ESPORTES"})

    def _gradient_bg(self, color_top=None, color_bottom=None) -> Image.Image:
        top = color_top or BRAND_COLOR_BG
        bot = color_bottom or (max(0, top[0] - 20), max(0, top[1] - 20), min(255, top[2] + 40))
        img = Image.new("RGB", (self.W, self.H), top)
        draw = ImageDraw.Draw(img)
        for y in range(self.H):
            t = y / self.H
            r = int(top[0] + (bot[0] - top[0]) * t)
            g = int(top[1] + (bot[1] - top[1]) * t)
            b = int(top[2] + (bot[2] - top[2]) * t)
            draw.line([(0, y), (self.W, y)], fill=(r, g, b))
        return img

    def _initials_badge(self, name: str, size: int = 220,
                        bg_color=None, text_color=None) -> Image.Image:
        bg = bg_color or BRAND_COLOR_ACCENT
        fg = text_color or BRAND_COLOR_TEXT
        badge = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(badge)
        # círculo preenchido com borda
        draw.ellipse([0, 0, size - 1, size - 1], fill=(*bg, 230))
        draw.ellipse([4, 4, size - 5, size - 5], outline=(*fg, 180), width=3)
        initials = "".join(w[0] for w in name.split()[:2]).upper()
        font = _font(int(size * 0.36))
        draw.text((size // 2, size // 2), initials, font=font,
                  fill=(*fg, 255), anchor="mm")
        return badge

    def _fetch_shield(self, team_id) -> "Image.Image | None":
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

    def _team_badge(self, team_id, name: str, size: int = 220,
                    bg_color=None, text_color=None) -> Image.Image:
        shield = self._fetch_shield(team_id)
        if shield:
            shield = shield.resize((size, size), Image.LANCZOS)
            bg = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            bg.paste(shield, mask=shield.split()[3] if shield.mode == "RGBA" else None)
            return bg
        return self._initials_badge(name, size, bg_color, text_color)

    def _footer_bar(self, img: Image.Image, league_label: str, accent=None):
        draw = ImageDraw.Draw(img)
        color = accent or BRAND_COLOR_ACCENT
        bar_h = 72
        draw.rectangle([0, self.H - bar_h, self.W, self.H], fill=color)
        draw.text((self.W // 2, self.H - bar_h + bar_h // 2),
                  f"{league_label}  •  @esportes.mundo_",
                  font=_font(32, False), fill=BRAND_COLOR_TEXT, anchor="mm")

    def _pillow_fallback(self, titulo: str, home: str = "", away: str = "",
                         liga: str = "") -> Image.Image:
        """Fallback Pillow melhorado com cores da liga e layout profissional."""
        palette = self._league_palette(liga)
        bg_color = palette["bg"]
        accent = palette["accent"]

        img = self._gradient_bg(color_top=bg_color).convert("RGBA")
        draw = ImageDraw.Draw(img)

        # barra superior
        draw.rectangle([0, 0, self.W, 10], fill=(*accent, 255))

        # label da liga
        league_str = palette["label"]
        draw.text((self.W // 2, 60), league_str,
                  font=_font(44, False), fill=(*accent, 255), anchor="mm")

        if home and away:
            badge_size = 230
            badge_y = 220

            home_badge = self._initials_badge(home, badge_size, bg_color=accent, text_color=BRAND_COLOR_TEXT)
            img.paste(home_badge, (self.W // 4 - badge_size // 2, badge_y), home_badge)

            away_badge = self._initials_badge(away, badge_size, bg_color=accent, text_color=BRAND_COLOR_TEXT)
            img.paste(away_badge, (3 * self.W // 4 - badge_size // 2, badge_y), away_badge)

            name_y = badge_y + badge_size + 28
            draw.text((self.W // 4, name_y), home.upper(),
                      font=_font(52), fill=(255, 255, 255, 255), anchor="mm")
            draw.text((3 * self.W // 4, name_y), away.upper(),
                      font=_font(52), fill=(255, 255, 255, 255), anchor="mm")

            vs_y = badge_y + badge_size // 2
            # linhas separadoras verticais
            lx1 = self.W // 4 + badge_size // 2 + 18
            lx2 = 3 * self.W // 4 - badge_size // 2 - 18
            draw.line([(lx1, vs_y - 60), (lx1, vs_y + 60)], fill=(*accent, 160), width=3)
            draw.line([(lx2, vs_y - 60), (lx2, vs_y + 60)], fill=(*accent, 160), width=3)
            draw.text((self.W // 2, vs_y), "VS",
                      font=_font(120), fill=(255, 255, 255, 255), anchor="mm")
        else:
            # notícia sem times: caixa de texto centralizada
            box_top = int(self.H * 0.50)
            overlay = Image.new("RGBA", (self.W, self.H - box_top - 80), (0, 0, 0, 0))
            ImageDraw.Draw(overlay).rectangle(
                [0, 0, self.W, self.H - box_top - 80], fill=(0, 0, 0, 190)
            )
            img.paste(overlay, (0, box_top), overlay)
            lines = _wrap(titulo, 24)
            font_size = max(40, 56 - max(0, len(lines) - 2) * 6)
            line_h = font_size + 16
            total_h = len(lines[:3]) * line_h
            start_y = box_top + (self.H - box_top - 80 - total_h) // 2 + font_size // 2
            for i, line in enumerate(lines[:3]):
                draw.text((self.W // 2, start_y + i * line_h), line,
                          font=_font(font_size), fill=(255, 255, 255, 255), anchor="mm")

        # rodapé
        bar_h = 72
        draw.rectangle([0, self.H - bar_h, self.W, self.H], fill=(*accent, 255))
        draw.text((self.W // 2, self.H - bar_h + bar_h // 2), "@esportes.mundo_",
                  font=_font(36, False), fill=(255, 255, 255, 255), anchor="mm")

        return img

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
        palette = self._league_palette(liga)

        # Tenta buscar imagem real de fundo
        bg_img = _buscar_imagem_esportiva(liga, home_team, away_team, self.W, self.H)

        if bg_img:
            img = bg_img.convert("RGBA")
            # overlay escuro para legibilidade
            overlay = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0))
            for y in range(self.H):
                alpha = int(140 * (y / self.H))
                ImageDraw.Draw(overlay).line([(0, y), (self.W, y)], fill=(0, 0, 0, alpha))
            img.paste(overlay, mask=overlay)
        else:
            print("[ASSET] Usando fallback Pillow para jogo")
            img = self._gradient_bg(color_top=palette["bg"]).convert("RGBA")

        draw = ImageDraw.Draw(img)
        accent = palette["accent"]
        league_label = LEAGUE_LABEL.get(liga, liga.replace("_", " ").title())

        # barra superior
        draw.rectangle([0, 0, self.W, 10], fill=(*accent, 255))

        draw.text((self.W // 2, 70), league_label.upper(),
                  font=_font(44, False), fill=(*accent, 255), anchor="mm")

        badge_size = 220
        badge_y = 280

        home_badge = self._team_badge(home_team_id, home_team, badge_size,
                                      bg_color=accent, text_color=BRAND_COLOR_TEXT)
        img.paste(home_badge, (self.W // 4 - badge_size // 2, badge_y), home_badge)

        away_badge = self._team_badge(away_team_id, away_team, badge_size,
                                      bg_color=accent, text_color=BRAND_COLOR_TEXT)
        img.paste(away_badge, (3 * self.W // 4 - badge_size // 2, badge_y), away_badge)

        name_y = badge_y + badge_size + 36
        draw.text((self.W // 4, name_y), home_team.upper(),
                  font=_font(52), fill=(255, 255, 255, 255), anchor="mm")
        draw.text((3 * self.W // 4, name_y), away_team.upper(),
                  font=_font(52), fill=(255, 255, 255, 255), anchor="mm")

        vs_y = badge_y + badge_size // 2
        lx1 = self.W // 4 + badge_size // 2 + 20
        lx2 = 3 * self.W // 4 - badge_size // 2 - 20
        draw.line([(lx1, vs_y - 50), (lx1, vs_y + 50)], fill=(*accent, 160), width=3)
        draw.line([(lx2, vs_y - 50), (lx2, vs_y + 50)], fill=(*accent, 160), width=3)

        draw.text((self.W // 2, vs_y), "VS",
                  font=_font(110), fill=(255, 255, 255, 255), anchor="mm")
        draw.text((self.W // 2, vs_y + 110), horario,
                  font=_font(58, False), fill=(*accent, 230), anchor="mm")

        self._footer_bar(img, league_label, accent=accent)

        slug = evento_id or f"{home_team}_{away_team}".replace(" ", "_").lower()
        path = os.path.join(POSTS_DIR, f"{slug}.jpg")
        img.convert("RGB").save(path, "JPEG", quality=92)
        print(f"[ASSET] Jogo salvo: {path}")
        return _relpath(path)

    def criar_imagem_noticia(self, titulo: str, evento_id: str,
                              home: str = "", away: str = "", liga: str = "") -> str:
        os.makedirs(POSTS_DIR, exist_ok=True)

        img_result = _buscar_imagem_esportiva(liga, home, away, self.W, self.H)

        if img_result:
            img = img_result.convert("RGBA")
        else:
            print("[ASSET] Pollinations/Unsplash/Wikimedia falharam — usando fallback Pillow")
            img = self._pillow_fallback(titulo, home=home, away=away, liga=liga).convert("RGBA")
            path = os.path.join(POSTS_DIR, f"news_{evento_id}.jpg")
            img.convert("RGB").save(path, "JPEG", quality=92)
            print(f"[ASSET] Noticia salva: {path}")
            return _relpath(path)

        # Caixa de texto sobre imagem real
        box_top = int(self.H * 0.72)
        box_h = self.H - box_top
        overlay = Image.new("RGBA", (self.W, box_h), (0, 0, 0, 0))
        ImageDraw.Draw(overlay).rectangle([0, 0, self.W, box_h], fill=(0, 0, 0, 210))
        img.paste(overlay, (0, box_top), overlay)

        draw = ImageDraw.Draw(img)
        lines = _wrap(titulo, 26)
        font_size = max(38, 52 - max(0, len(lines) - 2) * 6)
        line_h = font_size + 14
        total_text_h = len(lines[:3]) * line_h
        start_y = box_top + (box_h - total_text_h) // 2 + font_size // 2
        for i, line in enumerate(lines[:3]):
            draw.text(
                (self.W // 2, start_y + i * line_h),
                line,
                font=_font(font_size),
                fill=(255, 255, 255),
                anchor="mm",
            )

        self._footer_bar(img, "Esportes Mundo")

        path = os.path.join(POSTS_DIR, f"news_{evento_id}.jpg")
        img.convert("RGB").save(path, "JPEG", quality=92)
        print(f"[ASSET] Noticia salva: {path}")
        return _relpath(path)


# ─────────────────────────────────────────────
# API pública legada (usada pelo main.py)
# ─────────────────────────────────────────────

def create_post_image(content: dict) -> str:
    raw = content.get("raw_data", {})
    is_story = content.get("type") == "story"
    size = (1080, 1920) if is_story else (1080, 1080)
    out_dir = STORIES_DIR if is_story else POSTS_DIR

    home = raw.get("home_team", "")
    away = raw.get("away_team", "")
    liga = raw.get("league", raw.get("liga", ""))
    ac = AssetCreator()

    img = _buscar_imagem_esportiva(liga, home, away, *size) \
          or ac._pillow_fallback(raw.get("title", content.get("title", "")),
                                  home=home, away=away, liga=liga)

    if "home_team" in raw:
        _draw_score_card(img, raw)
    else:
        _draw_news_card(img, raw.get("title", content.get("title", "")))

    _paste_logo(img)

    raw_slug = (content.get("title") or "post")[:40]
    slug = "".join(c if c.isascii() and (c.isalnum() or c in " _-") else "_" for c in raw_slug).strip("_").replace(" ", "_")[:28]
    filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{slug}.jpg"
    path = os.path.join(out_dir, filename)
    img.convert("RGB").save(path, "JPEG", quality=92)
    print(f"[ASSET] Criado: {filename}")
    return _relpath(path)
