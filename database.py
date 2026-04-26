import sqlite3
import json
import hashlib
from config import DB_PATH


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS games_today (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id TEXT UNIQUE,
            league TEXT,
            league_name TEXT,
            home_team TEXT,
            away_team TEXT,
            home_score INTEGER DEFAULT 0,
            away_score INTEGER DEFAULT 0,
            start_time TEXT,
            status TEXT DEFAULT 'scheduled',
            fetched_at TEXT DEFAULT (datetime('now','localtime'))
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS news_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE,
            source TEXT,
            title TEXT,
            description TEXT,
            league TEXT DEFAULT 'geral',
            processed INTEGER DEFAULT 0,
            published_at TEXT,
            fetched_at TEXT DEFAULT (datetime('now','localtime'))
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS content_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            platform TEXT NOT NULL DEFAULT 'instagram',
            league TEXT,
            event_id TEXT,
            title TEXT,
            raw_data TEXT,
            generated_text TEXT DEFAULT '',
            image_path TEXT DEFAULT '',
            video_path TEXT DEFAULT '',
            status TEXT DEFAULT 'pending',
            scheduled_at TEXT,
            published_at TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS ai_cache (
            key_hash TEXT PRIMARY KEY,
            result_json TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS conteudos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            evento_id TEXT UNIQUE,
            legenda_instagram TEXT DEFAULT '',
            legenda_facebook  TEXT DEFAULT '',
            legenda_tiktok    TEXT DEFAULT '',
            legenda_kwai      TEXT DEFAULT '',
            titulo_youtube    TEXT DEFAULT '',
            descricao_youtube TEXT DEFAULT '',
            roteiro_reel      TEXT DEFAULT '',
            slides_carrossel  TEXT DEFAULT '',
            imagem_path       TEXT DEFAULT '',
            status            TEXT DEFAULT 'gerado',
            created_at        TEXT DEFAULT (datetime('now','localtime'))
        )
    """)
    # Migração: adiciona coluna platforms se ainda não existir
    try:
        c.execute("ALTER TABLE content_queue ADD COLUMN platforms TEXT DEFAULT '[]'")
        conn.commit()
    except Exception:
        pass

    conn.commit()
    conn.close()


def get_approved_ready() -> list:
    """Retorna itens aprovados cujo scheduled_at já chegou."""
    conn = get_conn()
    # replace(scheduled_at, 'T', ' ') normaliza formato ISO 8601 (com T) para
    # o formato do SQLite (com espaço), evitando comparação de string incorreta
    rows = conn.execute("""
        SELECT * FROM content_queue
        WHERE status = 'approved'
          AND scheduled_at IS NOT NULL
          AND replace(scheduled_at, 'T', ' ') <= datetime('now', 'localtime')
        ORDER BY scheduled_at ASC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_cache(raw_key: str) -> dict | None:
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    conn = get_conn()
    row = conn.execute(
        "SELECT result_json FROM ai_cache WHERE key_hash=?", (key_hash,)
    ).fetchone()
    conn.close()
    if row:
        return json.loads(row["result_json"])
    return None


def set_cache(raw_key: str, result: dict):
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO ai_cache (key_hash, result_json) VALUES (?,?)",
        (key_hash, json.dumps(result, ensure_ascii=False)),
    )
    conn.commit()
    conn.close()


def salvar_conteudo(evento_id, resultado: dict):
    conn = get_conn()
    conn.execute("""
        INSERT OR REPLACE INTO conteudos
        (evento_id, legenda_instagram, legenda_facebook, legenda_tiktok, legenda_kwai,
         titulo_youtube, descricao_youtube, roteiro_reel, slides_carrossel, imagem_path, status)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)
    """, (
        str(evento_id) if evento_id else None,
        resultado.get("legenda_instagram", ""),
        resultado.get("legenda_facebook", ""),
        resultado.get("legenda_tiktok", ""),
        resultado.get("legenda_kwai", ""),
        resultado.get("titulo_youtube", ""),
        resultado.get("descricao_youtube", ""),
        resultado.get("roteiro_reel", ""),
        resultado.get("slides_carrossel", ""),
        resultado.get("imagem_path", ""),
        "gerado",
    ))
    conn.commit()
    conn.close()


def get_conteudo_por_evento(evento_id: str) -> dict | None:
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM conteudos WHERE evento_id=?", (evento_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def save_game(game: dict):
    conn = get_conn()
    try:
        conn.execute("""
            INSERT OR REPLACE INTO games_today
            (event_id, league, league_name, home_team, away_team,
             home_score, away_score, start_time, status)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (game["event_id"], game["league"], game["league_name"],
              game["home_team"], game["away_team"],
              game.get("home_score", 0), game.get("away_score", 0),
              game["start_time"], game["status"]))
        conn.commit()
    finally:
        conn.close()


def save_news(news: dict):
    conn = get_conn()
    try:
        conn.execute("""
            INSERT OR IGNORE INTO news_items (url, source, title, description, league, published_at)
            VALUES (?,?,?,?,?,?)
        """, (news["url"], news["source"], news["title"],
              news.get("description", ""), news.get("league", "geral"),
              news.get("published_at", "")))
        conn.commit()
    finally:
        conn.close()


def add_to_queue(item: dict) -> int:
    conn = get_conn()
    try:
        cur = conn.execute("""
            INSERT INTO content_queue
            (type, platform, league, event_id, title, raw_data, generated_text, image_path, status)
            VALUES (?,?,?,?,?,?,?,?,'pending')
        """, (item["type"], item.get("platform", "instagram"), item.get("league"),
              item.get("event_id"), item.get("title"),
              json.dumps(item.get("raw_data", {}), ensure_ascii=False),
              item.get("generated_text", ""), item.get("image_path", "")))
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_queue(status: str = "pending") -> list:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM content_queue WHERE status=? ORDER BY created_at DESC", (status,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_queue_item(item_id: int) -> dict | None:
    conn = get_conn()
    row = conn.execute("SELECT * FROM content_queue WHERE id=?", (item_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_queue_item(item_id: int, updates: dict):
    conn = get_conn()
    sets = ", ".join(f"{k}=?" for k in updates)
    conn.execute(f"UPDATE content_queue SET {sets} WHERE id=?",
                 list(updates.values()) + [item_id])
    conn.commit()
    conn.close()


def get_games_today() -> list:
    conn = get_conn()
    rows = conn.execute("SELECT * FROM games_today ORDER BY start_time").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_queue_stats() -> dict:
    conn = get_conn()
    rows = conn.execute(
        "SELECT status, COUNT(*) as n FROM content_queue GROUP BY status"
    ).fetchall()
    conn.close()
    return {r["status"]: r["n"] for r in rows}
