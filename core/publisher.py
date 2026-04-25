import os
import shutil
import requests
from datetime import datetime
from config import INSTAGRAM_TOKEN, INSTAGRAM_ACCOUNT_ID
from database import update_queue_item


def publish_instagram(image_url: str, caption: str) -> dict:
    """
    Publica no Instagram via Graph API.
    image_url deve ser uma URL pública acessível (não caminho local).
    """
    if not INSTAGRAM_TOKEN or not INSTAGRAM_ACCOUNT_ID:
        return {"success": False, "error": "Credenciais Instagram não configuradas no .env"}
    try:
        r = requests.post(
            f"https://graph.facebook.com/v19.0/{INSTAGRAM_ACCOUNT_ID}/media",
            data={"image_url": image_url, "caption": caption, "access_token": INSTAGRAM_TOKEN},
            timeout=30,
        )
        container = r.json()
        cid = container.get("id")
        if not cid:
            return {"success": False, "error": container}

        r2 = requests.post(
            f"https://graph.facebook.com/v19.0/{INSTAGRAM_ACCOUNT_ID}/media_publish",
            data={"creation_id": cid, "access_token": INSTAGRAM_TOKEN},
            timeout=30,
        )
        result = r2.json()
        return {"success": "id" in result, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


def export_for_kwai(image_path: str, caption: str, dest_dir: str) -> dict:
    """Copia imagem e salva legenda para upload manual no Kwai."""
    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, os.path.basename(image_path))
    shutil.copy2(image_path, dest)
    with open(os.path.join(dest_dir, "legenda_kwai.txt"), "w", encoding="utf-8") as f:
        f.write(caption)
    return {"success": True, "path": dest_dir}


def mark_published(item_id: int, platform: str):
    update_queue_item(item_id, {
        "status": "published",
        "published_at": datetime.now().isoformat(),
    })
    print(f"[PUBLISHER] Item {item_id} publicado em {platform}")
