import json
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler

scheduler = BlockingScheduler(timezone="America/Sao_Paulo")


def run_cycle():
    from core.fetcher import fetch_all
    from core.processor import process_and_queue
    from core.asset_creator import create_post_image
    from database import get_queue, update_queue_item

    print(f"\n[SCHEDULER] >> Ciclo -- {datetime.now().strftime('%d/%m %H:%M')}")
    data = fetch_all()
    count = process_and_queue(data)

    if count > 0:
        gerados = get_queue("gerado")
        for item in gerados[:8]:
            if not item.get("image_path"):
                raw = json.loads(item.get("raw_data") or "{}")
                path = create_post_image({**item, "raw_data": raw})
                update_queue_item(item["id"], {"image_path": path})
                title_log = (item['title'] or '')[:45].encode('ascii', 'replace').decode()
                print(f"[SCHEDULER]   IMG: {title_log}")

    print(f"[SCHEDULER] == Ciclo concluido")


def check_live():
    from core.fetcher import fetch_all_football_today, fetch_nba_today
    games = fetch_all_football_today() + fetch_nba_today()
    live = [g for g in games if g.get("status") == "live"]
    if live:
        print(f"[SCHEDULER] AO VIVO: {len(live)} jogo(s)")


def publicar_aprovados():
    from core.publisher import publicar_aprovados as _pub
    _pub()


# Coletas agendadas (horário de Brasília)
scheduler.add_job(run_cycle, "cron", hour=6,  minute=0,  id="morning")
scheduler.add_job(run_cycle, "cron", hour=12, minute=0,  id="noon")
scheduler.add_job(run_cycle, "cron", hour=16, minute=0,  id="afternoon")
scheduler.add_job(run_cycle, "cron", hour=20, minute=0,  id="evening")
scheduler.add_job(run_cycle, "cron", hour=22, minute=30, id="night")

# Verificação ao vivo a cada 15 min
scheduler.add_job(check_live, "interval", minutes=15, id="live_check")

# Publicação automática de aprovados — verifica a cada 1 minuto
scheduler.add_job(publicar_aprovados, "interval", minutes=1, id="publish_approved")


def start():
    print("[SCHEDULER] Iniciando...")
    print("[SCHEDULER] Coletas: 06:00 | 12:00 | 16:00 | 20:00 | 22:30")
    print("[SCHEDULER] Live check: a cada 15 min")
    print("[SCHEDULER] Publicador: a cada 1 min")
    print("[SCHEDULER] Ctrl+C para parar\n")
    scheduler.start()


if __name__ == "__main__":
    start()
