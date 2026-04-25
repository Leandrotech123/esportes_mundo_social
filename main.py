"""
Esportes Mundo Social — Sistema de automação de conteúdo
Uso: python main.py <comando>
"""
import sys
import json


def cmd_fetch():
    from core.fetcher import fetch_all
    from core.processor import process_and_queue
    data = fetch_all()
    process_and_queue(data)


def cmd_generate():
    """Gera conteúdo para itens ainda pendentes (fallback)."""
    from core.ai_generator import AIGenerator
    from core.asset_creator import create_post_image
    from database import get_queue, update_queue_item

    pending = get_queue("pending")
    if not pending:
        print("[MAIN] Nenhum item pendente.")
        return

    print(f"[MAIN] Gerando para {len(pending)} item(s)...")
    ai = AIGenerator()
    for item in pending:
        raw = json.loads(item.get("raw_data") or "{}")
        evento = {
            "event_id": item.get("event_id"),
            "title":    item.get("title", ""),
            "league":   item.get("league", ""),
            **raw,
        }
        resultado = ai.gerar_conteudo_completo(evento)
        path = create_post_image({**item, "raw_data": raw})
        update_queue_item(item["id"], {
            "status": "gerado",
            "generated_text": resultado.get("legenda_instagram", ""),
            "image_path": path,
        })
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

    t = threading.Thread(target=lambda: (cmd_fetch(), cmd_generate()), daemon=True)
    t.start()
    t.join()

    print("[MAIN] Painel em http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)


COMMANDS = {
    "fetch":     (cmd_fetch,     "Busca jogos e notícias e gera conteúdo automaticamente"),
    "generate":  (cmd_generate,  "Processa itens pendentes na fila (fallback)"),
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
