import os
import json
import base64
import anthropic
from config import ANTHROPIC_API_KEY, SKILLS_DIR

HAIKU = "claude-haiku-3-5-20251001"
SONNET = "claude-sonnet-4-5"

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    return _client


def _load_skill(name: str) -> str:
    for ext in (".txt", ".md"):
        path = os.path.join(SKILLS_DIR, f"{name}{ext}")
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            continue
    return "Gere uma legenda esportiva engajante em português para Instagram."


SKILL_MAP = {
    "post": "legenda_feed",
    "story": "legenda_story",
    "reel": "roteiro_reel",
}


def generate_caption(content_type: str, raw_data: dict, platform: str = "instagram") -> str:
    """Gera legenda para um item da fila (compatível com main.py)."""
    skill = _load_skill(SKILL_MAP.get(content_type, "legenda_feed"))
    prompt = (
        f"{skill}\n\nDADOS:\n"
        f"{json.dumps(raw_data, ensure_ascii=False, indent=2)}\n\n"
        f"PLATAFORMA: {platform.upper()}"
    )
    model = SONNET if content_type == "reel" else HAIKU
    max_tokens = 900 if content_type == "reel" else 400
    try:
        resp = _get_client().messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.content[0].text.strip()
    except Exception as e:
        print(f"[AI] Anthropic erro: {e}")
        return f"[Legenda não gerada — erro: {e}]"


def generate_image_prompt(raw_data: dict) -> str:
    """Gera prompt visual em inglês para Pollinations.ai."""
    context = json.dumps(raw_data, ensure_ascii=False)[:400]
    prompt = (
        "Based on this sports event data, write a concise English visual prompt "
        "for a dark, dramatic sports graphic (max 40 words). Visuals only, no text.\n\n"
        f"Data: {context}"
    )
    try:
        resp = _get_client().messages.create(
            model=HAIKU,
            max_tokens=100,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.content[0].text.strip()
    except Exception:
        return "dark dramatic football stadium at night, cinematic lighting, crowd energy, epic atmosphere"


def gerar_conteudo_completo(evento: dict) -> dict:
    """Gera todo o conteúdo de texto para um evento esportivo com cache no banco."""
    from database import get_cache, set_cache

    cache_key = json.dumps(evento, ensure_ascii=False, sort_keys=True)
    cached = get_cache(cache_key)
    if cached:
        return cached

    base_prompt = f"\nEVENTO:\n{json.dumps(evento, ensure_ascii=False, indent=2)}\n"
    resultado = {}

    # Legendas curtas — Haiku (mais barato)
    tarefas_haiku = [
        ("legenda_instagram", "legenda_feed",   400, "INSTAGRAM"),
        ("legenda_facebook",  "legenda_feed",   400, "FACEBOOK"),
        ("legenda_tiktok",    "legenda_story",  400, "TIKTOK"),
        ("legenda_kwai",      "legenda_story",  400, "KWAI"),
        ("titulo_youtube",    "legenda_story",  100, "YOUTUBE"),
    ]
    for campo, skill_name, max_tok, plataforma in tarefas_haiku:
        skill = _load_skill(skill_name)
        prompt = f"{skill}\n\nPLATAFORMA: {plataforma}{base_prompt}\nGere apenas o texto pedido."
        try:
            resp = _get_client().messages.create(
                model=HAIKU,
                max_tokens=max_tok,
                messages=[{"role": "user", "content": prompt}],
            )
            resultado[campo] = resp.content[0].text.strip()
        except Exception as e:
            resultado[campo] = f"[Erro: {e}]"

    # Conteúdos longos — Sonnet (mais capaz)
    tarefas_sonnet = [
        ("roteiro_reel",       "roteiro_reel", 900),
        ("descricao_youtube",  "legenda_feed", 600),
        ("slides_carrossel",   "legenda_feed", 900),
    ]
    for campo, skill_name, max_tok in tarefas_sonnet:
        skill = _load_skill(skill_name)
        tarefa_label = campo.replace("_", " ").upper()
        prompt = f"{skill}\n\nTAREFA: {tarefa_label}{base_prompt}\nGere apenas o conteúdo pedido."
        try:
            resp = _get_client().messages.create(
                model=SONNET,
                max_tokens=max_tok,
                messages=[{"role": "user", "content": prompt}],
            )
            resultado[campo] = resp.content[0].text.strip()
        except Exception as e:
            resultado[campo] = f"[Erro: {e}]"

    set_cache(cache_key, resultado)
    return resultado


def gerar_a_partir_de_midia(caminho_arquivo: str) -> dict:
    """Analisa imagem ou vídeo com Vision e retorna dict estruturado do evento."""
    import mimetypes

    skill = _load_skill("analisar_midia")
    ext = os.path.splitext(caminho_arquivo)[1].lower()

    if ext in (".mp4", ".mov", ".avi", ".mkv", ".webm"):
        imagem_path = _extrair_frame_central(caminho_arquivo)
        if not imagem_path:
            return {"erro": "Não foi possível extrair frame do vídeo"}
        media_type = "image/jpeg"
    else:
        imagem_path = caminho_arquivo
        mime, _ = mimetypes.guess_type(caminho_arquivo)
        media_type = mime or "image/jpeg"

    with open(imagem_path, "rb") as f:
        imagem_b64 = base64.b64encode(f.read()).decode()

    raw = ""
    try:
        resp = _get_client().messages.create(
            model=SONNET,
            max_tokens=1000,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": imagem_b64,
                        },
                    },
                    {"type": "text", "text": skill},
                ],
            }],
        )
        raw = resp.content[0].text.strip().strip("```json").strip("```").strip()
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"erro": "Resposta não era JSON válido", "raw": raw}
    except Exception as e:
        return {"erro": str(e)}


def _extrair_frame_central(video_path: str) -> str | None:
    try:
        from moviepy.video.io.VideoFileClip import VideoFileClip
        import tempfile
        clip = VideoFileClip(video_path)
        frame_path = tempfile.mktemp(suffix=".jpg")
        clip.save_frame(frame_path, t=clip.duration / 2)
        clip.close()
        return frame_path
    except Exception as e:
        print(f"[AI] Erro ao extrair frame: {e}")
        return None
