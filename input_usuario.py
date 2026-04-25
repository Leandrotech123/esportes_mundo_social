"""
Uso: python input_usuario.py caminho/do/arquivo.jpg
Analisa uma imagem ou vídeo, gera conteúdo completo e abre o painel.
"""
import sys
import os
import webbrowser
from pathlib import Path

EXTENSOES_VALIDAS = {".jpg", ".jpeg", ".png", ".mp4", ".mov"}


def main():
    if len(sys.argv) < 2:
        print("Uso: python input_usuario.py caminho/do/arquivo.jpg")
        print("Extensões suportadas: jpg, png, mp4, mov")
        sys.exit(1)

    caminho = sys.argv[1]

    if not os.path.exists(caminho):
        print(f"✗ Arquivo não encontrado: {caminho}")
        sys.exit(1)

    ext = Path(caminho).suffix.lower()
    if ext not in EXTENSOES_VALIDAS:
        print(f"✗ Extensão não suportada: {ext}")
        print(f"  Use: {', '.join(sorted(EXTENSOES_VALIDAS))}")
        sys.exit(1)

    from database import init_db, add_to_queue, update_queue_item
    from core.ai_generator import AIGenerator
    from core.asset_creator import create_post_image

    init_db()
    ai = AIGenerator()

    print(f"\n[INPUT] Analisando: {Path(caminho).name}")
    dados_midia = ai.gerar_a_partir_de_midia(caminho)

    if "erro" in dados_midia:
        print(f"✗ Erro na análise: {dados_midia['erro']}")
        sys.exit(1)

    print(f"[INPUT] Detectado: {dados_midia.get('esporte', '?')} | {dados_midia.get('liga', '?')}")
    print(f"[INPUT] Título sugerido: {dados_midia.get('titulo_sugerido', '')}")

    evento = {
        "event_id": f"midia_{Path(caminho).stem}",
        "title":    dados_midia.get("titulo_sugerido", Path(caminho).stem),
        "league":   dados_midia.get("liga", "geral"),
        "type":     dados_midia.get("tipo_conteudo", "post"),
        "platform": "instagram",
        "raw_data": dados_midia,
        **dados_midia,
    }

    print("[INPUT] Criando imagem formatada...")
    imagem_path = create_post_image({**evento, "raw_data": dados_midia})

    print("[INPUT] Gerando legendas para todas as plataformas...")
    conteudo = ai.gerar_conteudo_completo(evento)
    conteudo["imagem_path"] = imagem_path

    from database import salvar_conteudo
    salvar_conteudo(evento["event_id"], conteudo)

    qid = add_to_queue({
        **evento,
        "image_path":     imagem_path,
        "generated_text": conteudo.get("legenda_instagram", ""),
    })
    update_queue_item(qid, {"status": "gerado"})

    print(f"\n✅ Conteúdo criado com sucesso!")
    print(f"   Instagram : {(conteudo.get('legenda_instagram', '')[:80])}...")
    print(f"   TikTok    : {conteudo.get('legenda_tiktok', '')[:80]}")
    print(f"   Imagem    : {imagem_path}")
    print(f"\n   Acesse http://localhost:8000 para aprovar e publicar.")

    try:
        webbrowser.open("http://localhost:8000")
    except Exception:
        pass


if __name__ == "__main__":
    main()
