"""
test_setup.py — Verifica instalação e configuração do projeto
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

SKILLS_ESPERADAS = [
    "legenda_feed",
    "legenda_tiktok",
    "roteiro_reel",
    "titulo_youtube",
    "analisar_midia",
    "carrossel",
    "pre_jogo",
]
PASTAS_ESPERADAS = ["skills", "core", "dashboard"]
TABELAS_ESPERADAS = ["games_today", "news_items", "content_queue", "ai_cache", "conteudos"]


def check(nome: str, ok: bool, detalhe: str = "") -> bool:
    mark = "✓" if ok else "✗"
    msg = f"  {mark} {nome}"
    if detalhe:
        msg += f"  —  {detalhe}"
    print(msg)
    return ok


# ─── Teste 1: Skills ────────────────────────────────────────────────────────

def testar_skills() -> bool:
    print("\n[1] Skills (.md)")
    base = os.path.dirname(__file__)
    todos_ok = True
    for skill in SKILLS_ESPERADAS:
        path = os.path.join(base, "skills", f"{skill}.md")
        ok = os.path.exists(path)
        todos_ok = check(skill, ok) and todos_ok
    return todos_ok


# ─── Teste 2: Banco SQLite ───────────────────────────────────────────────────

def testar_banco() -> bool:
    print("\n[2] Banco SQLite")
    try:
        from database import init_db, get_conn
        init_db()
        check("init_db()", True)
        conn = get_conn()
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        conn.close()
        for t in TABELAS_ESPERADAS:
            check(f"tabela {t}", t in tables)
        return True
    except Exception as e:
        check("banco", False, str(e))
        return False


# ─── Teste 3: Estrutura de pastas ───────────────────────────────────────────

def testar_pastas() -> bool:
    print("\n[3] Estrutura de pastas")
    base = os.path.dirname(__file__)
    for pasta in PASTAS_ESPERADAS:
        check(pasta, os.path.isdir(os.path.join(base, pasta)))
    return True


# ─── Teste 4: Conexão Anthropic ─────────────────────────────────────────────

def testar_anthropic() -> bool:
    print("\n[4] Conexão Anthropic")
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        check("ANTHROPIC_API_KEY", False, "não configurado no .env")
        print("  ⚠ Configure ANTHROPIC_API_KEY no .env para teste completo")
        return False
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        r = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=30,
            messages=[{"role": "user", "content": "Responda apenas: OK"}],
        )
        resposta = r.content[0].text.strip()
        check("claude-haiku-4-5-20251001", True, f'resposta: "{resposta}"')
        return True
    except Exception as e:
        check("Anthropic API", False, str(e))
        return False


# ─── Main ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 52)
    print("  test_setup.py — Esportes Mundo Social")
    print("=" * 52)

    resultados = [
        testar_skills(),
        testar_banco(),
        testar_pastas(),
        testar_anthropic(),
    ]

    total_ok = sum(resultados)
    print("\n" + "=" * 52)
    print(f"  Resultado: {total_ok}/4 módulos OK")
    if total_ok == 4:
        print("  🟢 Projeto pronto para uso!")
    else:
        print("  🔴 Corrija os itens com ✗ antes de usar.")
    print("=" * 52)

    sys.exit(0 if total_ok == 4 else 1)
