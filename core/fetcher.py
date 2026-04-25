import requests
from datetime import date, datetime
from config import ESPN_BASE, FOOTBALL_DATA_BASE, FOOTBALL_DATA_KEY, NEWS_API_KEY, NEWS_API_BASE, LEAGUES_ESPN
from database import save_game, save_news

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; EsportesMundo/1.0)"}


# ─────────────────────────────────────────────
# ESPN (unofficial, sem chave)
# ─────────────────────────────────────────────

def _espn_status(name: str) -> str:
    if any(x in name for x in ("IN_PROGRESS", "HALFTIME", "LIVE")):
        return "live"
    if any(x in name for x in ("FINAL", "FULL_TIME", "POST")):
        return "finished"
    return "scheduled"


def fetch_espn_league(sport: str, league_id: str) -> list:
    url = f"{ESPN_BASE}/{sport}/{league_id}/scoreboard"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        data = r.json()
        league_name = (data.get("leagues") or [{}])[0].get("name", league_id)
        games = []
        for event in data.get("events", []):
            comp = (event.get("competitions") or [{}])[0]
            competitors = comp.get("competitors", [])
            if len(competitors) < 2:
                continue
            home = next((c for c in competitors if c.get("homeAway") == "home"), competitors[0])
            away = next((c for c in competitors if c.get("homeAway") == "away"), competitors[1])
            status_name = event.get("status", {}).get("type", {}).get("name", "STATUS_SCHEDULED")
            g = {
                "event_id": f"espn_{event.get('id', '')}",
                "league": league_id,
                "league_name": league_name,
                "home_team": home.get("team", {}).get("displayName", ""),
                "away_team": away.get("team", {}).get("displayName", ""),
                "home_score": int(home.get("score") or 0),
                "away_score": int(away.get("score") or 0),
                "start_time": event.get("date", ""),
                "status": _espn_status(status_name),
            }
            games.append(g)
            save_game(g)
        return games
    except Exception as e:
        print(f"[FETCHER] ESPN {league_id} erro: {e}")
        return []


def fetch_all_football_today() -> list:
    all_games = []
    for name, league_id in LEAGUES_ESPN.items():
        games = fetch_espn_league("soccer", league_id)
        all_games.extend(games)
        print(f"[FETCHER] {league_id}: {len(games)} jogos")
    return all_games


# ─────────────────────────────────────────────
# NBA — Ball Don't Lie (sem chave, grátis)
# ─────────────────────────────────────────────

def fetch_nba_today() -> list:
    today = date.today().isoformat()
    url = "https://api.balldontlie.io/v1/games"
    try:
        r = requests.get(url, params={"dates[]": today}, timeout=10)
        r.raise_for_status()
        games = []
        for g in r.json().get("data", []):
            home = g.get("home_team", {})
            visitor = g.get("visitor_team", {})
            status_raw = str(g.get("status", "1"))
            status = {"1": "scheduled", "2": "live", "3": "finished"}.get(status_raw, "scheduled")
            game = {
                "event_id": f"nba_{g.get('id')}",
                "league": "nba",
                "league_name": "NBA",
                "home_team": home.get("full_name") or home.get("name", ""),
                "away_team": visitor.get("full_name") or visitor.get("name", ""),
                "home_score": g.get("home_team_score") or 0,
                "away_score": g.get("visitor_team_score") or 0,
                "start_time": g.get("date", today),
                "status": status,
            }
            games.append(game)
            save_game(game)
        print(f"[FETCHER] NBA: {len(games)} jogos")
        return games
    except Exception as e:
        print(f"[FETCHER] NBA erro: {e}")
        return []


# ─────────────────────────────────────────────
# Notícias esportivas
# ─────────────────────────────────────────────

def fetch_espn_news() -> list:
    sources = [
        ("soccer", "news", "futebol"),
        ("basketball", "nba/news", "nba"),
    ]
    items = []
    for sport, path, league in sources:
        try:
            r = requests.get(f"{ESPN_BASE}/{sport}/{path}", headers=HEADERS, timeout=10)
            r.raise_for_status()
            for a in r.json().get("articles", [])[:6]:
                url = a.get("links", {}).get("web", {}).get("href", "")
                title = a.get("headline", "")
                if not title or not url:
                    continue
                item = {
                    "source": "ESPN",
                    "title": title,
                    "description": a.get("description", ""),
                    "url": url,
                    "published_at": a.get("published", ""),
                    "league": league,
                }
                items.append(item)
                save_news(item)
        except Exception as e:
            print(f"[FETCHER] ESPN news {sport} erro: {e}")
    return items


def fetch_newsapi() -> list:
    if not NEWS_API_KEY:
        return []
    try:
        r = requests.get(f"{NEWS_API_BASE}/everything", params={
            "q": "futebol OR brasileirão OR \"Premier League\" OR NBA",
            "language": "pt",
            "sortBy": "publishedAt",
            "pageSize": 10,
            "apiKey": NEWS_API_KEY,
        }, timeout=10)
        r.raise_for_status()
        items = []
        for a in r.json().get("articles", []):
            if not a.get("title") or not a.get("url"):
                continue
            item = {
                "source": a.get("source", {}).get("name", "NewsAPI"),
                "title": a["title"],
                "description": a.get("description", ""),
                "url": a["url"],
                "published_at": a.get("publishedAt", ""),
                "league": "geral",
            }
            items.append(item)
            save_news(item)
        return items
    except Exception as e:
        print(f"[FETCHER] NewsAPI erro: {e}")
        return []


def fetch_all() -> dict:
    print(f"\n{'='*52}")
    print(f"[FETCHER] Coleta iniciada — {datetime.now().strftime('%d/%m %H:%M:%S')}")
    games = fetch_all_football_today() + fetch_nba_today()
    news = fetch_espn_news() + fetch_newsapi()
    print(f"[FETCHER] Total: {len(games)} jogos | {len(news)} notícias")
    return {"games": games, "news": news}
