import os
import json
import shutil
import requests
import cloudinary
import cloudinary.uploader
from datetime import datetime
from config import (
    INSTAGRAM_TOKEN, INSTAGRAM_ACCOUNT_ID,
    FACEBOOK_PAGE_ID, YOUTUBE_API_KEY, OUTPUTS_DIR,
    CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET,
)
from database import update_queue_item, get_approved_ready

cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET,
)

ALL_PLATFORMS = ["instagram", "facebook", "youtube", "tiktok", "kwai"]

PLATFORM_ICONS = {
    "instagram": "📸",
    "facebook":  "👤",
    "youtube":   "▶",
    "tiktok":    "🎵",
    "kwai":      "🎬",
}


# ─── Cloudinary ──────────────────────────────────────────────────────────────

def upload_imagem_publica(caminho_local: str) -> str:
    """Faz upload da imagem local para o Cloudinary e retorna a URL pública."""
    result = cloudinary.uploader.upload(caminho_local, folder="esportes_mundo")
    return result["secure_url"]


# ─── Instagram ───────────────────────────────────────────────────────────────

def publish_instagram(image_path: str, caption: str) -> dict:
    if not INSTAGRAM_TOKEN or not INSTAGRAM_ACCOUNT_ID:
        return {"success": False, "error": "Credenciais Instagram nao configuradas no .env"}
    if not image_path or not os.path.exists(image_path):
        return {"success": False, "error": "Sem imagem local para upload"}
    try:
        image_url = upload_imagem_publica(image_path)
        r = requests.post(
            f"https://graph.facebook.com/v19.0/{INSTAGRAM_ACCOUNT_ID}/media",
            data={"image_url": image_url, "caption": caption, "access_token": INSTAGRAM_TOKEN},
            timeout=30,
        )
        cid = r.json().get("id")
        if not cid:
            return {"success": False, "error": r.json()}
        r2 = requests.post(
            f"https://graph.facebook.com/v19.0/{INSTAGRAM_ACCOUNT_ID}/media_publish",
            data={"creation_id": cid, "access_token": INSTAGRAM_TOKEN},
            timeout=30,
        )
        result = r2.json()
        return {"success": "id" in result, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ─── Facebook ────────────────────────────────────────────────────────────────

def _get_page_access_token(user_token: str) -> str:
    """Troca o User/System User token pelo Page Access Token necessário para postar."""
    r = requests.get(
        f"https://graph.facebook.com/v19.0/{FACEBOOK_PAGE_ID}",
        params={"fields": "access_token", "access_token": user_token},
        timeout=15,
    )
    return r.json().get("access_token", user_token)


def publish_facebook(image_path: str, caption: str) -> dict:
    from config import META_ACCESS_TOKEN
    user_token = META_ACCESS_TOKEN or INSTAGRAM_TOKEN
    if not user_token or not FACEBOOK_PAGE_ID:
        return {"success": False, "error": "Credenciais Facebook nao configuradas no .env"}
    if not image_path or not os.path.exists(image_path):
        return {"success": False, "error": "Sem imagem local para upload"}
    try:
        page_token = _get_page_access_token(user_token)
        image_url = upload_imagem_publica(image_path)
        r = requests.post(
            f"https://graph.facebook.com/v19.0/{FACEBOOK_PAGE_ID}/photos",
            data={"url": image_url, "caption": caption, "access_token": page_token},
            timeout=30,
        )
        result = r.json()
        if "id" in result:
            return {"success": True, "result": result}
        return {"success": False, "error": result.get("error", result)}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ─── YouTube (exporta metadados para upload) ─────────────────────────────────

def export_for_youtube(item: dict, caption: str) -> dict:
    dest = os.path.join(OUTPUTS_DIR, "youtube")
    os.makedirs(dest, exist_ok=True)
    slug = f"item_{item['id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    meta = {
        "titulo": item.get("title", ""),
        "descricao": caption,
        "tags": ["EsportesMundo", "Futebol", "NBA", "Shorts"],
        "imagem": item.get("image_path", ""),
        "agendado_para": item.get("scheduled_at", ""),
    }
    with open(os.path.join(dest, f"{slug}.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    if item.get("image_path") and os.path.exists(item["image_path"]):
        shutil.copy2(item["image_path"], os.path.join(dest, f"{slug}.jpg"))
    return {"success": True, "path": dest, "file": slug}


# ─── TikTok (exporta para upload manual) ─────────────────────────────────────

def export_for_tiktok(item: dict, caption: str) -> dict:
    dest = os.path.join(OUTPUTS_DIR, "tiktok")
    os.makedirs(dest, exist_ok=True)
    slug = f"item_{item['id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    with open(os.path.join(dest, f"{slug}_legenda.txt"), "w", encoding="utf-8") as f:
        f.write(caption)
    if item.get("image_path") and os.path.exists(item["image_path"]):
        shutil.copy2(item["image_path"], os.path.join(dest, f"{slug}.jpg"))
    return {"success": True, "path": dest}


# ─── Kwai (exporta para upload manual) ───────────────────────────────────────

def export_for_kwai(item: dict, caption: str) -> dict:
    dest = os.path.join(OUTPUTS_DIR, "kwai")
    os.makedirs(dest, exist_ok=True)
    slug = f"item_{item['id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    with open(os.path.join(dest, f"{slug}_legenda.txt"), "w", encoding="utf-8") as f:
        f.write(caption)
    if item.get("image_path") and os.path.exists(item["image_path"]):
        shutil.copy2(item["image_path"], os.path.join(dest, f"{slug}.jpg"))
    return {"success": True, "path": dest}


# ─── Publicar item em todas as plataformas selecionadas ──────────────────────

def _publicar_item(item: dict):
    platforms = json.loads(item.get("platforms") or "[]") or ALL_PLATFORMS
    caption = item.get("generated_text", "")
    image_path = item.get("image_path", "")
    results = {}

    for plat in platforms:
        if plat == "instagram":
            results["instagram"] = publish_instagram(image_path, caption)

        elif plat == "facebook":
            results["facebook"] = publish_facebook(image_path, caption)

        elif plat == "youtube":
            results["youtube"] = export_for_youtube(item, caption)

        elif plat == "tiktok":
            results["tiktok"] = export_for_tiktok(item, caption)

        elif plat == "kwai":
            results["kwai"] = export_for_kwai(item, caption)

    return results


def publicar_aprovados():
    """Verifica itens aprovados com scheduled_at vencido e publica em todas as redes."""
    itens = get_approved_ready()
    if not itens:
        return

    print(f"[PUBLISHER] {len(itens)} item(s) para publicar")
    for item in itens:
        try:
            results = _publicar_item(item)
            ok = [p for p, r in results.items() if r.get("success")]
            fail = [p for p, r in results.items() if not r.get("success")]
            update_queue_item(item["id"], {
                "status": "published",
                "published_at": datetime.now().isoformat(),
            })
            print(f"[PUBLISHER] Item {item['id']} publicado | ok={ok} | falhou={fail}")
            for plat, r in results.items():
                if not r.get("success"):
                    print(f"  [{plat}] erro: {r.get('error')}")
        except Exception as e:
            print(f"[PUBLISHER] Erro item {item['id']}: {e}")


def mark_published(item_id: int, platform: str):
    update_queue_item(item_id, {
        "status": "published",
        "published_at": datetime.now().isoformat(),
    })
    print(f"[PUBLISHER] Item {item_id} publicado em {platform}")


class Publisher:
    def publicar_aprovados(self):
        return publicar_aprovados()
