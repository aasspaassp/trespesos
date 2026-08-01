"""
Escuchando a las maquinas que no funcionan
API minima: sirve la pagina, genera el audio, entrega los .wav
"""

import threading
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from trespesos_audio import generar, SALIDA

BASE = Path(__file__).resolve().parent
ESTATICOS = BASE / "static"

# La medicion es una lectura del estado real de la maquina.
# Si dos visitantes entran a la vez, cada loop contamina al otro:
# uno estaria midiendo el trabajo que hace el otro al medir.
_lock = threading.Lock()

app = FastAPI(title="Escuchando a las maquinas que no funcionan", docs_url=None, redoc_url=None)

SALIDA.mkdir(parents=True, exist_ok=True)
app.mount("/audio", StaticFiles(directory=str(SALIDA)), name="audio")


@app.get("/")
def inicio():
    return FileResponse(ESTATICOS / "index.html")


@app.get("/generar")
def generar_audio():
    """
    Definido como def (no async def): FastAPI lo corre en un threadpool,
    asi los 2 s de time.sleep() no bloquean el event loop ni la carga de la pagina.
    """
    if not _lock.acquire(blocking=False):
        raise HTTPException(
            status_code=409,
            detail="La maquina ya se esta escuchando a si misma. Intenta en unos segundos.",
        )
    try:
        meta = generar()
    finally:
        _lock.release()

    meta["url_audio"] = f"/audio/{meta['archivo']}"
    meta.pop("lecturas", None)   # las 20 lecturas crudas quedan en el .json en disco
    return JSONResponse(meta)


@app.get("/salud")
def salud():
    return {"ok": True}