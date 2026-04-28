import os
import json
import base64
import anthropic
from datetime import datetime

HAIKU = "claude-haiku-4-5-20251001"
SONNET = "claude-sonnet-4-5"

LEAGUE_LABEL = {
    "bra.1": "Brasileirão",
    "eng.1": "Premier League",
    "esp.1": "La Liga",
    "uefa.champions": "Champions League",
    "ita.1": "Serie A",
    "nba": "NBA",
}
LEAGUE_EMOJI = {
    "bra.1": "🇧🇷",
    "eng.1": "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
    "esp.1": "🇪🇸",
    "uefa.champions": "⭐",
    "ita.1": "🇮🇹",
    "nba": "🏀",
}


class AIGenerator:
    HAIKU = HAIKU
    SONNET = SONNET
    SYSTEM = (
        "Você é um especialista em conteúdo esportivo viral para redes sociais brasileiras. "
        "Responda SEMPRE em português brasileiro informal. Nunca use inglês."
    )

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.skills = self._carregar_skills()

    def _carregar_skills(self) -> dict:
        skills = {}
        skills_dir = os.path.join(os.path.dirname(__file__), "..", "skills")
        if not os.path.isdir(skills_dir):
            return skills
        # Carrega .txt primeiro, depois .md sobrescreve (md tem precedência)
        for ext in (".txt", ".md"):
            for arquivo in os.listdir(skills_dir):
                if arquivo.endswith(ext):
                    nome = arquivo[: -len(ext)]
                    path = os.path.join(skills_dir, arquivo)
                    try:
                        with open(path, "r", encoding="utf-8") as f:
                            skills[nome] = f.read()
                    except OSError:
                        pass
        return skills

    def _montar_prompt(self, skill_nome: str, variaveis: dict) -> str:
        template = self.skills.get(skill_nome, "")
        for chave, valor in variaveis.items():
            template = template.replace(f"{{{chave}}}", str(valor or ""))
        return template

    def _chamar_api(self, prompt: str, modelo: str, max_tokens: int) -> str:
        response = self.client.messages.create(
            model=modelo,
            max_tokens=max_tokens,
            system=self.SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()

    def _checar_cache(self, evento_id) -> dict | None:
        if not evento_id:
            return None
        try:
            from database import get_conteudo_por_evento
            return get_conteudo_por_evento(str(evento_id))
        except Exception:
            return None

    def _variaveis_de_evento(self, evento: dict) -> dict:
        liga = evento.get("league") or evento.get("liga", "")

        start_time = evento.get("start_time", "")
        data_jogo = ""
        if start_time:
            try:
                from datetime import datetime as _dt
                data_jogo = _dt.strptime(str(start_time)[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
            except Exception:
                pass

        return {
            "titulo":     evento.get("titulo") or evento.get("title", ""),
            "liga_nome":  LEAGUE_LABEL.get(liga, liga),
            "emoji_liga": LEAGUE_EMOJI.get(liga, "⚽"),
            "descricao":  evento.get("descricao") or evento.get("description") or evento.get("label", ""),
            "destaque":   evento.get("destaque") or evento.get("context", ""),
            "time_casa":  evento.get("home_team", ""),
            "time_fora":  evento.get("away_team", ""),
            "horario":    start_time,
            "data_jogo":  data_jogo,
            "data_hoje":  datetime.now().strftime("%d/%m/%Y"),
        }

    def gerar_conteudo_completo(self, evento: dict) -> dict:
        evento_id = evento.get("event_id") or evento.get("id")
        cached = self._checar_cache(evento_id)
        if cached:
            return cached

        variaveis = self._variaveis_de_evento(evento)
        resultado = {}

        # Conteúdos curtos — Haiku (mais barato)
        tarefas_haiku = [
            ("legenda_instagram", "legenda_feed",   400),
            ("legenda_facebook",  "legenda_feed",   400),
            ("legenda_tiktok",    "legenda_tiktok", 300),
            ("legenda_kwai",      "legenda_tiktok", 300),
            ("titulo_youtube",    "titulo_youtube", 200),
        ]
        for campo, skill_nome, max_tok in tarefas_haiku:
            prompt = self._montar_prompt(skill_nome, variaveis)
            if not prompt.strip():
                resultado[campo] = ""
                continue
            try:
                resultado[campo] = self._chamar_api(prompt, self.HAIKU, max_tok)
            except Exception as e:
                resultado[campo] = f"[Erro: {e}]"
                print(f"[AI] Haiku erro em {campo}: {e}")

        # Conteúdos longos — Sonnet (mais capaz)
        tarefas_sonnet = [
            ("roteiro_reel",      "roteiro_reel",  900),
            ("descricao_youtube", "titulo_youtube", 600),
            ("slides_carrossel",  "carrossel",     900),
        ]
        for campo, skill_nome, max_tok in tarefas_sonnet:
            prompt = self._montar_prompt(skill_nome, variaveis)
            if not prompt.strip():
                resultado[campo] = ""
                continue
            try:
                resultado[campo] = self._chamar_api(prompt, self.SONNET, max_tok)
            except Exception as e:
                resultado[campo] = f"[Erro: {e}]"
                print(f"[AI] Sonnet erro em {campo}: {e}")

        try:
            from database import salvar_conteudo
            salvar_conteudo(evento_id, resultado)
        except Exception as e:
            print(f"[AI] Erro ao salvar conteúdo no banco: {e}")

        return resultado

    def gerar_a_partir_de_midia(self, caminho_arquivo: str) -> dict:
        import mimetypes

        skill = self.skills.get("analisar_midia", "")
        ext = os.path.splitext(caminho_arquivo)[1].lower()

        if ext in (".mp4", ".mov", ".avi", ".mkv", ".webm"):
            imagem_path = self._extrair_frame_central(caminho_arquivo)
            if not imagem_path:
                return {"erro": "Não foi possível extrair frame do vídeo"}
            media_type = "image/jpeg"
        else:
            imagem_path = caminho_arquivo
            mime, _ = mimetypes.guess_type(caminho_arquivo)
            media_type = mime or "image/jpeg"

        with open(imagem_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode()

        raw = ""
        try:
            response = self.client.messages.create(
                model=self.SONNET,
                max_tokens=1000,
                messages=[{"role": "user", "content": [
                    {"type": "image", "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": img_b64,
                    }},
                    {"type": "text", "text": skill},
                ]}],
            )
            raw = response.content[0].text.strip().strip("```json").strip("```").strip()
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"erro": "Resposta não era JSON válido", "raw": raw}
        except Exception as e:
            return {"erro": str(e)}

    def _extrair_frame_central(self, video_path: str) -> str | None:
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


# ─── Instância singleton e funções de compatibilidade ───────────────────────

_instance: AIGenerator | None = None


def _get_ai() -> AIGenerator:
    global _instance
    if _instance is None:
        _instance = AIGenerator()
    return _instance


_SKILL_MAP = {
    "post":  "legenda_feed",
    "story": "legenda_tiktok",
    "reel":  "roteiro_reel",
}


def generate_caption(content_type: str, raw_data: dict, platform: str = "instagram") -> str:
    ai = _get_ai()
    skill_nome = _SKILL_MAP.get(content_type, "legenda_feed")
    variaveis = ai._variaveis_de_evento(raw_data)
    if not variaveis["titulo"]:
        variaveis["titulo"] = raw_data.get("home_team", "")
    prompt = ai._montar_prompt(skill_nome, variaveis)
    if not prompt.strip():
        prompt = f"Gere uma legenda esportiva sobre: {json.dumps(raw_data, ensure_ascii=False)[:300]}"
    modelo = SONNET if content_type == "reel" else HAIKU
    max_tokens = 900 if content_type == "reel" else 400
    try:
        return ai._chamar_api(prompt, modelo, max_tokens)
    except Exception as e:
        print(f"[AI] erro: {e}")
        return f"[Legenda não gerada — erro: {e}]"


def generate_image_prompt(raw_data: dict) -> str:
    ai = _get_ai()
    context = json.dumps(raw_data, ensure_ascii=False)[:400]
    prompt = (
        "Based on this sports event data, write a concise English visual prompt "
        "for a dark, dramatic sports graphic (max 40 words). Visuals only, no text.\n\n"
        f"Data: {context}"
    )
    try:
        return ai._chamar_api(prompt, HAIKU, 100)
    except Exception:
        return "dark dramatic football stadium at night, cinematic lighting, crowd energy, epic atmosphere"
