"""
run.py — Ponto de entrada do sistema EsportesMundo Social
Uso: python run.py
"""
import threading
import uvicorn
from database import init_db

BANNER = """
╔══════════════════════════════════════════════════════════╗
║          ESPORTES MUNDO SOCIAL — Sistema Ativo           ║
╠══════════════════════════════════════════════════════════╣
║  Redes configuradas:                                     ║
║   Instagram  →  graph.facebook.com/v19.0                 ║
║   Facebook   →  graph.facebook.com/v19.0                 ║
║   YouTube    →  youtube.googleapis.com                   ║
║   TikTok     →  open.tiktokapis.com  (pendente aprovacao)║
╠══════════════════════════════════════════════════════════╣
║  Painel de aprovacao  →  http://localhost:8000           ║
║  Scheduler            →  06h | 12h | 16h | 20h | 22h30  ║
╠══════════════════════════════════════════════════════════╣
║  Para enviar midia:                                      ║
║    python input_usuario.py <arquivo>                     ║
╚══════════════════════════════════════════════════════════╝
"""


def _run_scheduler():
    from scheduler import start
    start()


def main():
    init_db()
    print(BANNER)

    t = threading.Thread(target=_run_scheduler, daemon=True, name="scheduler")
    t.start()

    from dashboard.app import app
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")


if __name__ == "__main__":
    main()
