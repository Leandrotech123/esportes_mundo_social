import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
FOOTBALL_DATA_KEY = os.getenv("FOOTBALL_DATA_KEY", "")
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")
INSTAGRAM_TOKEN = os.getenv("INSTAGRAM_TOKEN", "")
INSTAGRAM_ACCOUNT_ID = os.getenv("INSTAGRAM_ACCOUNT_ID", "")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")
SKILLS_DIR = os.path.join(BASE_DIR, "skills")
DB_PATH = os.path.join(BASE_DIR, "esportes.db")

ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports"
FOOTBALL_DATA_BASE = "https://api.football-data.org/v4"
BALLDONTLIE_BASE = "https://api.balldontlie.io/v1"
NEWS_API_BASE = "https://newsapi.org/v2"

LEAGUES_ESPN = {
    "brasileirao": "bra.1",
    "premier_league": "eng.1",
    "la_liga": "esp.1",
    "champions_league": "uefa.champions",
    "serie_a_ita": "ita.1",
}

BRAND_COLOR_BG = (10, 10, 22)
BRAND_COLOR_ACCENT = (255, 75, 15)
BRAND_COLOR_TEXT = (255, 255, 255)
BRAND_COLOR_SECONDARY = (170, 170, 200)
