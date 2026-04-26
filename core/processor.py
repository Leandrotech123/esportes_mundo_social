from database import add_to_queue, update_queue_item

LEAGUE_EMOJI = {
    "bra.1": "🇧🇷",
    "eng.1": "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
    "esp.1": "🇪🇸",
    "uefa.champions": "⭐",
    "ita.1": "🇮🇹",
    "nba": "🏀",
}

LEAGUE_LABEL = {
    "bra.1": "Brasileirão",
    "eng.1": "Premier League",
    "esp.1": "La Liga",
    "uefa.champions": "Champions",
    "ita.1": "Serie A",
    "nba": "NBA",
}


def _emoji(league: str) -> str:
    return LEAGUE_EMOJI.get(league, "⚽")


def _highlight_type(game: dict) -> str | None:
    h, a = game.get("home_score", 0), game.get("away_score", 0)
    total = h + a
    if game["league"] == "nba":
        if total >= 240:
            return "placar_alto_nba"
    else:
        if total >= 5:
            return "goleada"
        if abs(h - a) >= 3:
            return "goleada"
        if total >= 3 and h == a:
            return "empate_emocionante"
    return None


def classify_games(games: list) -> list:
    pieces = []
    for g in games:
        emoji = _emoji(g["league"])
        label = LEAGUE_LABEL.get(g["league"], g["league"])

        if g["status"] == "finished":
            hl = _highlight_type(g)
            pieces.append({
                "type": "post",
                "platform": "instagram",
                "league": g["league"],
                "event_id": g["event_id"],
                "title": f"{emoji} {g['home_team']} {g['home_score']}x{g['away_score']} {g['away_team']}",
                "raw_data": {**g, "context": hl or "resultado_final", "label": label},
                "priority": 3 if hl else 2,
            })

        elif g["status"] == "live":
            pieces.append({
                "type": "story",
                "platform": "instagram",
                "league": g["league"],
                "event_id": g["event_id"],
                "title": f"⚡ AO VIVO: {g['home_team']} {g['home_score']}x{g['away_score']} {g['away_team']}",
                "raw_data": {**g, "context": "ao_vivo", "label": label},
                "priority": 4,
            })

        elif g["status"] == "scheduled":
            pieces.append({
                "type": "story",
                "platform": "instagram",
                "league": g["league"],
                "event_id": g["event_id"],
                "title": f"{emoji} HOJE: {g['home_team']} x {g['away_team']} — {label}",
                "raw_data": {**g, "context": "pre_jogo", "label": label},
                "priority": 1,
            })

    pieces.sort(key=lambda x: x["priority"], reverse=True)
    return pieces


def classify_news(news: list) -> list:
    return [
        {
            "type": "post",
            "platform": "instagram",
            "league": n.get("league", "geral"),
            "event_id": None,
            "title": n["title"],
            "raw_data": n,
            "priority": 1,
        }
        for n in news[:6]
    ]


def process_and_queue(data: dict) -> int:
    games = data.get("games", [])
    news = data.get("news", [])

    pieces = classify_games(games) + classify_news(news)
    pieces.sort(key=lambda x: x["priority"], reverse=True)

    added_items = []
    for p in pieces:
        qid = add_to_queue(p)
        added_items.append({"qid": qid, **p})

    if added_items:
        try:
            from core.ai_generator import AIGenerator
            ai = AIGenerator()
            for i in range(0, len(added_items), 5):
                batch = added_items[i:i + 5]
                for item in batch:
                    raw = item.get("raw_data", {})
                    evento = {
                        "event_id": item.get("event_id"),
                        "title":    item.get("title", ""),
                        "league":   item.get("league", ""),
                        **raw,
                    }
                    try:
                        resultado = ai.gerar_conteudo_completo(evento)
                        update_queue_item(item["qid"], {
                            "status": "gerado",
                            "generated_text": resultado.get("legenda_instagram", ""),
                        })
                        title_log = (item.get('title', ''))[:50].encode('ascii', 'replace').decode()
                        print(f"[PROCESSOR] OK {title_log}")
                    except Exception as e:
                        print(f"[PROCESSOR] ERRO ao gerar conteudo: {e}")
        except Exception as e:
            print(f"[PROCESSOR] AIGenerator indisponivel: {e}")

    live = sum(1 for g in games if g.get("status") == "live")
    finished = sum(1 for g in games if g.get("status") == "finished")
    print(f"[PROCESSOR] {len(added_items)} itens na fila | {live} ao vivo | {finished} encerrados")
    return len(added_items)
