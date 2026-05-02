"""
run.py — Ponto de entrada do sistema EsportesMundo Social
Uso: python run.py
"""
import os
import sys
import threading
import uvicorn
from dotenv import load_dotenv
from database import init_db

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

load_dotenv()

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


def _start_ngrok():
    ngrok_token = os.getenv("NGROK_AUTHTOKEN")
    if not ngrok_token:
        return
    try:
        from pyngrok import ngrok as pyngrok_tunnel
        pyngrok_tunnel.set_auth_token(ngrok_token)
        for t in pyngrok_tunnel.get_tunnels():
            try:
                pyngrok_tunnel.disconnect(t.public_url)
            except Exception:
                pass
        tunnel = pyngrok_tunnel.connect(8000)
        print(f"\n URL EXTERNA: {tunnel.public_url}\n")
    except Exception as e:
        err = str(e)
        # ERR_NGROK_334: túnel ainda ativo no servidor — extrai a URL existente
        import re
        match = re.search(r"https://[\w\-]+\.ngrok[\w\-\.]+", err)
        if match:
            print(f"\n URL EXTERNA (sessão anterior ativa): {match.group(0)}")
            print(f" (reinicie em ~1 minuto para renovar o túnel)\n")
        else:
            print(f"[NGROK] Aviso: {err[:120]}")


def _mostrar_ip_local():
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
    except Exception:
        ip = "127.0.0.1"
    print(f"\n{'='*50}")
    print(f" Acesse pelo celular (mesma rede WiFi):")
    print(f" http://{ip}:8000")
    print(f"{'='*50}\n")


def _run_server():
    from dashboard.app import app
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")


def main():
    import time
    import logging

    init_db()
    print(BANNER)

    _mostrar_ip_local()

    t = threading.Thread(target=_run_scheduler, daemon=True, name="scheduler")
    t.start()

    threading.Thread(target=_start_ngrok, daemon=True, name="ngrok").start()

    while True:
        try:
            _run_server()
            break  # saída limpa (Ctrl+C ou shutdown normal)
        except OSError as e:
            if getattr(e, "winerror", None) == 64:
                logging.warning("Rede perdida — reconectando em 10s...")
                print("[WATCHDOG] Rede perdida — reconectando em 10s...")
                time.sleep(10)
            else:
                raise


if __name__ == "__main__":
    main()
