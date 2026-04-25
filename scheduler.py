import json
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler

scheduler = BlockingScheduler(timezone="America/Sao_Paulo")


def run_cycle():
    from core.fetcher import fetch_all
    from core.processor import process_and_queue
    from core.ai_generator import generate_caption
    from core.asset_creator import create_post_image
    from database import get_queue, update_queue_item

    print(f"\n[SCHEDULER] ▶ Ciclo — {datetime.now().strftime('%d/%m %H:%M')}")
    data = fetch_all()
    count = process_and_queue(data)

    if count > 0:
        pending = get_queue("pending")
        for item in pending[:8]:
            if not item.get("generated_text"):
                raw = json.loads(item.get("raw_data") or "{}")
                text = generate_caption(item["type"], raw, item["platform"])
                path = create_post_image({**item, "raw_data": raw})
                update_queue_item(item["id"], {"generated_text": text, "image_path": path})
                print(f"[SCHEDULER]   ✓ Item {item['id']}: {(item['title'] or '')[:45]}")

    print(f"[SCHEDULER] ■ Ciclo concluído")


def check_live():
    from core.fetcher import fetch_all_football_today, fetch_nba_today
    games = fetch_all_football_today() + fetch_nba_today()
    live = [g for g in games if g.get("status") == "live"]
    if live:
        print(f"[SCHEDULER] ⚡ {len(live)} jogo(s) ao vivo")


# Coletas agendadas (horário de Brasília)
scheduler.add_job(run_cycle, "cron", hour=6,  minute=0,  id="morning")
scheduler.add_job(run_cycle, "cron", hour=12, minute=0,  id="noon")
scheduler.add_job(run_cycle, "cron", hour=16, minute=0,  id="afternoon")
scheduler.add_job(run_cycle, "cron", hour=20, minute=0,  id="evening")
scheduler.add_job(run_cycle, "cron", hour=22, minute=30, id="night")

# Verificação ao vivo a cada 15 min
scheduler.add_job(check_live, "interval", minutes=15, id="live_check")


def start():
    print("[SCHEDULER] Iniciando...")
    print("[SCHEDULER] Coletas: 06:00 | 12:00 | 16:00 | 20:00 | 22:30")
    print("[SCHEDULER] Live check: a cada 15 min")
    print("[SCHEDULER] Ctrl+C para parar\n")
    scheduler.start()


if __name__ == "__main__":
    start()
