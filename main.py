"""
Escuchando a las maquinas que no funcionan
API minima: sirve la pagina, genera el audio, entrega los .wav
"""

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from additiveSineWav import generar, SALIDA

#SALIDA = Path(__file__).resolve().parent / "audio"
BASE = Path(__file__).resolve().parent
ESTATICOS = BASE / "static"

app = FastAPI(
    title="Escuchando a las maquinas que no funcionan",
    docs_url=None,
    redoc_url=None,
)

SALIDA.mkdir(parents=True, exist_ok=True)
app.mount("/audio", StaticFiles(directory=str(SALIDA)), name="audio")
app.mount("/static", StaticFiles(directory=str(ESTATICOS)), name="static")


@app.get("/")
def inicio():
    return FileResponse(ESTATICOS / "index.html")


@app.get("/generar")
def generar_audio():
    try:
        meta = generar()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"No se pudo generar el audio: {e}")

    meta["url_audio"] = f"/audio/{meta['archivo']}"
    return JSONResponse(meta)


@app.get("/lista")
def lista():
    """
    Los .wav se llaman 20260801T053712Z-e15af8c9.wav: como empiezan con la
    fecha en formato ordenable, ordenar alfabetico es ordenar cronologico.
    Cada .wav tiene su .json gemelo con el mismo id, asi que si existe
    se lee de ahi la info para mostrarla junto al audio.
    """
    salida = []
    for wav in sorted(SALIDA.glob("*.wav"), reverse=True):
        item = {
            "id": wav.stem,
            "archivo": wav.name,
            "url_audio": f"/audio/{wav.name}",
        }
        gemelo = wav.with_suffix(".json")
        if gemelo.exists():
            try:
                meta = json.loads(gemelo.read_text(encoding="utf-8"))
                item["generado_utc"] = meta.get("generado_utc")
                item["duracion_audio_s"] = meta.get("duracion_audio_s")
                item["metricas"] = meta.get("metricas")
            except (json.JSONDecodeError, OSError):
                pass
        salida.append(item)
    return JSONResponse(salida)


@app.get("/salud")
def salud():
    return {"ok": True}
