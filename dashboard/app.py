import os
import json
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from database import get_queue, get_queue_item, update_queue_item, get_games_today, get_all_queue_stats

DEFAULT_PLATFORMS = ["instagram", "facebook", "youtube", "tiktok", "kwai"]

app = FastAPI(title="Esportes Mundo — Painel")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMPL_DIR = os.path.join(os.path.dirname(__file__), "templates")
OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")

templates = Jinja2Templates(directory=TMPL_DIR)

if os.path.exists(OUTPUTS_DIR):
    app.mount("/outputs", StaticFiles(directory=OUTPUTS_DIR), name="outputs")


# ─── helpers ────────────────────────────────

def _run_pipeline():
    from core.fetcher import fetch_all
    from core.processor import process_and_queue
    data = fetch_all()
    process_and_queue(data)


# ─── routes ─────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    queue = get_queue("gerado")
    agendados = get_queue("approved")
    stats = get_all_queue_stats()
    games = get_games_today()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "queue": queue,
        "agendados": agendados,
        "stats": stats,
        "games": games,
    })


@app.get("/fetch")
async def trigger_fetch():
    _run_pipeline()
    return RedirectResponse("/", status_code=303)


@app.post("/approve/{item_id}")
async def approve(item_id: int, scheduled_at: str = Form(default="")):
    if scheduled_at:
        sched = scheduled_at  # datetime-local: "2026-04-26T14:30"
    else:
        sched = (datetime.now() + timedelta(minutes=15)).strftime("%Y-%m-%dT%H:%M")
    update_queue_item(item_id, {
        "status": "approved",
        "scheduled_at": sched,
        "platforms": json.dumps(DEFAULT_PLATFORMS),
    })
    return RedirectResponse("/", status_code=303)


@app.post("/reject/{item_id}")
async def reject(item_id: int):
    update_queue_item(item_id, {"status": "rejected"})
    return RedirectResponse("/", status_code=303)


@app.get("/edit/{item_id}", response_class=HTMLResponse)
async def edit_form(request: Request, item_id: int):
    item = get_queue_item(item_id)
    if not item:
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse("edit.html", {"request": request, "item": item})


@app.post("/edit/{item_id}")
async def edit_save(item_id: int, generated_text: str = Form(...)):
    update_queue_item(item_id, {"generated_text": generated_text})
    return RedirectResponse("/", status_code=303)


@app.get("/image/{item_id}")
async def serve_image(item_id: int):
    item = get_queue_item(item_id)
    if item and item.get("image_path") and os.path.exists(item["image_path"]):
        return FileResponse(item["image_path"])
    return HTMLResponse("", status_code=404)


@app.post("/regenerate/{item_id}")
async def regenerate(item_id: int):
    item = get_queue_item(item_id)
    if item:
        from core.ai_generator import generate_caption
        from core.asset_creator import create_post_image
        raw = json.loads(item.get("raw_data") or "{}")
        text = generate_caption(item["type"], raw, item["platform"])
        path = create_post_image({**item, "raw_data": raw})
        update_queue_item(item_id, {"generated_text": text, "image_path": path})
    return RedirectResponse("/", status_code=303)


@app.get("/history", response_class=HTMLResponse)
async def history(request: Request):
    approved = get_queue("approved")
    published = get_queue("published")
    rejected = get_queue("rejected")
    return templates.TemplateResponse("history.html", {
        "request": request,
        "approved": approved,
        "published": published,
        "rejected": rejected,
    })
