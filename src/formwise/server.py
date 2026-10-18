"""Local web interface for formwise."""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .config import output_root, profile_path
from .fields import fill_pdf, inspect_pdf, preview_pdf
from .profile import ProfileLocked, load_profile, value_for_field

STATIC = Path(__file__).resolve().parent / "static"
MAX_UPLOAD = 25 * 1024 * 1024
MAX_PAGES = 100

app = FastAPI(title="formwise", version="0.1.4")
app.mount("/static", StaticFiles(directory=STATIC), name="static")


class FillRequest(BaseModel):
    job: str
    values: dict[str, str]
    flatten: bool = False


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html", media_type="text/html")


@app.get("/healthz")
def health() -> dict[str, object]:
    return {"ok": True}


@app.post("/api/inspect")
async def inspect(file: UploadFile = File(...)) -> JSONResponse:
    if Path(file.filename or "").suffix.lower() != ".pdf":
        raise HTTPException(status_code=400, detail="choose a PDF file")
    payload = await file.read(MAX_UPLOAD + 1)
    if len(payload) > MAX_UPLOAD:
        raise HTTPException(status_code=413, detail="PDF too large (max 25 MB)")
    job = uuid.uuid4().hex
    folder = output_root() / job
    folder.mkdir(parents=True, exist_ok=True)
    source = folder / "source.pdf"
    source.write_bytes(payload)
    try:
        fields, pages = inspect_pdf(source)
    except Exception as exc:
        shutil.rmtree(folder, ignore_errors=True)
        raise HTTPException(status_code=400, detail="not a readable PDF form") from exc
    if pages > MAX_PAGES:
        shutil.rmtree(folder, ignore_errors=True)
        raise HTTPException(status_code=413, detail="PDF has too many pages (max 100)")
    preview_pdf(source).save(folder / "preview.png")
    locked = False
    try:
        profile = load_profile(profile_path())
    except ProfileLocked:
        profile = {}
        locked = True
    items = []
    for field in fields:
        data = field.to_dict()
        data["suggested"] = value_for_field(field.name, profile)
        items.append(data)
    return JSONResponse(
        {
            "job": job,
            "pages": pages,
            "fields": items,
            "profile_keys": sorted(profile.keys()),
            "profile_locked": locked,
            "preview": f"/files/{job}/preview.png",
        }
    )


@app.post("/api/fill")
def fill(request: FillRequest) -> JSONResponse:
    folder = (output_root() / Path(request.job).name).resolve()
    source = folder / "source.pdf"
    if not source.exists():
        raise HTTPException(status_code=404, detail="job not found")
    target = folder / "filled.pdf"
    try:
        result = fill_pdf(source, target, request.values, flatten=request.flatten)
        preview_pdf(target).save(folder / "preview.png")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return JSONResponse(
        {
            "download": f"/files/{request.job}/filled.pdf",
            "preview": f"/files/{request.job}/preview.png?v=2",
            "filled": result["filled"],
        }
    )


@app.get("/files/{job}/{name}")
def download(job: str, name: str) -> FileResponse:
    folder = (output_root() / Path(job).name).resolve()
    target = (folder / Path(name).name).resolve()
    if not target.is_relative_to(folder) or not target.is_file():
        raise HTTPException(status_code=404, detail="not found")
    return FileResponse(target)
