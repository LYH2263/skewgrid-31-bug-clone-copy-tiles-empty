from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from app.cache import coverage_grid, png_path, read_meta
from app.config import DATA_DIR, DB_PATH
from app.db import init_db
from app.seed import seed_if_empty
from app.store import (
    CloneError,
    all_settings,
    clone_layer,
    create_layer,
    get_layer,
    get_scan,
    list_jobs,
    list_layers,
    list_repairs,
    list_scans,
    repair_tile,
    run_job,
    run_scan,
    set_setting,
)
from app.tiles import tms_y, valid_coord, xyz_y_from_tms


@asynccontextmanager
async def lifespan(_: FastAPI):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    init_db(DB_PATH)
    seed_if_empty(DATA_DIR, DB_PATH)
    yield


app = FastAPI(title="Skewgrid", version="0.2.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class LayerIn(BaseModel):
    slug: str = Field(pattern=r"^[a-z0-9-]{2,40}$")
    name: str
    description: str = ""
    provider: str = "procedural"
    default_scheme: str = "xyz"
    min_z: int = 0
    max_z: int = 3


class ScanIn(BaseModel):
    scheme: str = "xyz"
    max_z: int = 3


class CloneIn(BaseModel):
    target_slug: str = Field(pattern=r"^[a-z0-9-]{2,40}$")
    name: str | None = None
    description: str | None = None
    copy_tiles: bool = False


class JobIn(BaseModel):
    kind: str
    payload: dict = {}


class SettingIn(BaseModel):
    value: str


def _layer_or_404(slug: str) -> dict:
    layer = get_layer(DB_PATH, slug)
    if not layer:
        raise HTTPException(404, f"layer not found: {slug}")
    return layer


@app.get("/health")
def health():
    return {"ok": True, "service": "skewgrid", "version": "0.2.0"}


@app.get("/api/layers")
def api_layers():
    return list_layers(DB_PATH)


@app.post("/api/layers", status_code=201)
def api_create_layer(body: LayerIn):
    if get_layer(DB_PATH, body.slug):
        raise HTTPException(409, "slug exists")
    if body.provider == "http_upstream":
        # 允许建层，但取瓦仍会 501，留给 0-1 实现上游。
        pass
    return create_layer(DB_PATH, body.model_dump())


@app.get("/api/layers/{slug}")
def api_layer(slug: str):
    return _layer_or_404(slug)


@app.post("/api/layers/{slug}/clone", status_code=201)
def api_clone_layer(slug: str, body: CloneIn):
    try:
        return clone_layer(
            DB_PATH,
            DATA_DIR,
            slug,
            body.target_slug,
            name=body.name,
            description=body.description,
            copy_tiles=body.copy_tiles,
        )
    except CloneError as exc:
        raise HTTPException(exc.status_code, str(exc)) from exc


@app.get("/api/layers/{slug}/coverage")
def api_coverage(slug: str, z: int = 2, scheme: str = "xyz"):
    _layer_or_404(slug)
    return coverage_grid(DATA_DIR, slug, scheme, z)


@app.get("/api/layers/{slug}/tile")
def api_tile_info(slug: str, z: int, x: int, y: int, scheme: str = "xyz"):
    _layer_or_404(slug)
    if not valid_coord(z, x, y):
        raise HTTPException(400, "invalid z/x/y")
    path = png_path(DATA_DIR, slug, scheme, z, x, y)
    meta = read_meta(DATA_DIR, slug, scheme, z, x, y)
    aligned = bool(
        meta
        and meta.get("baked_z") == z
        and meta.get("baked_x") == x
        and meta.get("baked_y") == y
    )
    return {
        "layer": slug,
        "scheme": scheme,
        "z": z,
        "x": x,
        "y": y,
        "tms_y": tms_y(z, y),
        "png_exists": path.exists(),
        "path": str(path),
        "meta": meta,
        "aligned": aligned,
    }


@app.post("/api/layers/{slug}/repair")
def api_repair(slug: str, z: int, x: int, y: int, scheme: str = "xyz"):
    _layer_or_404(slug)
    try:
        repair_tile(DB_PATH, DATA_DIR, slug, scheme, z, x, y)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"ok": True}


@app.get("/api/layers/{slug}/repairs")
def api_repairs(slug: str):
    _layer_or_404(slug)
    return list_repairs(DB_PATH, slug)


@app.get("/api/layers/{slug}/upstream")
def api_upstream(slug: str):
    layer = _layer_or_404(slug)
    return {
        "implemented": False,
        "provider": layer["provider"],
        "hint": "在 app/providers/http_upstream.py 实现按模板拉上游瓦，并在本接口改为可拉取。",
    }


@app.post("/api/layers/{slug}/upstream/fetch")
def api_upstream_fetch(slug: str):
    _layer_or_404(slug)
    return JSONResponse(
        {
            "error": "not_implemented",
            "message": "上游拉取未实现，见 app/providers/http_upstream.py",
        },
        status_code=501,
    )


@app.post("/api/layers/{slug}/scans")
def api_scan(slug: str, body: ScanIn):
    _layer_or_404(slug)
    return run_scan(DB_PATH, DATA_DIR, slug, body.scheme, body.max_z)


@app.get("/api/scans")
def api_scans(slug: str | None = None):
    return list_scans(DB_PATH, slug)


@app.get("/api/scans/{run_id}")
def api_scan_detail(run_id: int):
    data = get_scan(DB_PATH, run_id)
    if not data:
        raise HTTPException(404, "scan not found")
    return data


@app.post("/api/layers/{slug}/jobs")
def api_create_job(slug: str, body: JobIn):
    _layer_or_404(slug)
    job = run_job(DB_PATH, DATA_DIR, slug, body.kind, body.payload)
    status = 501 if job["status"] == "blocked" else 200
    return JSONResponse(job, status_code=status)


@app.get("/api/jobs")
def api_jobs():
    return list_jobs(DB_PATH)


@app.get("/api/settings")
def api_settings():
    return all_settings(DB_PATH)


@app.put("/api/settings/{key}")
def api_put_setting(key: str, body: SettingIn):
    set_setting(DB_PATH, key, body.value)
    return {"key": key, "value": body.value}


@app.get("/tiles/{slug}/{scheme}/{z}/{x}/{y}.png")
def serve_tile(slug: str, scheme: str, z: int, x: int, y: int):
    _layer_or_404(slug)
    if scheme == "tms":
        if not valid_coord(z, x, y):
            raise HTTPException(404, "invalid tile")
        y = xyz_y_from_tms(z, y)
        scheme = "xyz"
    if not valid_coord(z, x, y):
        raise HTTPException(404, "invalid tile")
    path = png_path(DATA_DIR, slug, scheme, z, x, y)
    if not path.exists():
        return JSONResponse({"error": "tile not cached"}, status_code=404)
    return FileResponse(path, media_type="image/png", headers={"Cache-Control": "no-store"})
