"""
Esportes Mundo Social — Sistema de automação de conteúdo
Uso: python main.py <comando>
"""
import sys
import os


def cmd_fetch():
    from core.fetcher import fetch_all
    from core.processor import process_and_queue
    data = fetch_all()
    process_and_queue(data)


def cmd_generate():
    import json
    from core.ai_generator import generate_caption
    from core.asset_creator import create_post_image
    from database import get_queue, update_queue_item

    pending = get_queue("pending")
    print(f"[MAIN] Gerando para {len(pending)} item(s)...")
    for item in pending:
        if not item.get("generated_text"):
            raw = json.loads(item.get("raw_data") or "{}")
            text = generate_caption(item["type"], raw, item["platform"])
            path = create_post_image({**item, "raw_data": raw})
            update_queue_item(item["id"], {"generated_text": text, "image_path": path})
            print(f"  ✓ [{item['id']}] {(item['title'] or '')[:55]}")


def cmd_dashboard():
    import uvicorn
    from dashboard.app import app
    print("[MAIN] Painel em http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)


def cmd_schedule():
    from scheduler import start
    start()


def cmd_run():
    """Pipeline completo: busca + geração + painel."""
    import threading
    import uvicorn
    from dashboard.app import app

    def pipeline():
        cmd_fetch()
        cmd_generate()

    t = threading.Thread(target=pipeline, daemon=True)
    t.start()
    t.join()

    print("[MAIN] Painel em http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)


COMMANDS = {
    "fetch":     (cmd_fetch,     "Busca jogos e notícias das APIs"),
    "generate":  (cmd_generate,  "Gera legendas e imagens para itens na fila"),
    "dashboard": (cmd_dashboard, "Abre o painel de aprovação (localhost:8000)"),
    "schedule":  (cmd_schedule,  "Inicia o agendador automático"),
    "run":       (cmd_run,       "Pipeline completo (fetch + generate + painel)"),
}


def main():
    from database import init_db
    init_db()

    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print("\nUso: python main.py <comando>\n")
        for name, (_, desc) in COMMANDS.items():
            print(f"  {name:<12} {desc}")
        print()
        return

    COMMANDS[sys.argv[1]][0]()


if __name__ == "__main__":
    main()
