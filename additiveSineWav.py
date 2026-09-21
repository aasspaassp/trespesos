import json
import uuid
import wave
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from dataCollector import collectCPUmetrics
from azureMetric import get_carbon_report

SALIDA = Path(__file__).resolve().parent / "audio"
SR = 44100          # sample rate
DUR = 5.0           # segundos

def sintetizar(metrics, carbon):
    # t linespace is suppoder to be an array with number  
    t = np.linspace(0, DUR, int(SR * DUR), endpoint=False)

    cpuPer = metrics["cpu_percentage"] *10
    cpuFreq = metrics["cpu_frequencyMhz"] / 1000
    diskUsage = metrics["disk_usage"]
    networkSent = metrics["network_io"]["sent"] / 100
    networkReceived = metrics["network_io"]["received"] / 100
    print(carbon["value"][0]["latestMonthEmissions"])
    audio = np.sin(2*np.pi*cpuFreq*t) + np.sin(2*np.pi*cpuPer*t) + np.sin(2*np.pi*networkSent*t) + np.sin(2*np.pi*networkReceived*t) + 0.5* np.sin(2*np.pi*diskUsage*t)  


    # is audio supposer to be an array?
    audio = audio / np.max(np.abs(audio))

    pcm = (audio * 32767).astype(np.int16)

    return pcm


def escribir_wav(ruta, pcm):
    with wave.open(str(ruta), "wb") as w:
        w.setnchannels(1)        # mono
        w.setsampwidth(2)        # 2 bytes = int16
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())

def generar(directorio=SALIDA):
    directorio = Path(directorio)
    directorio.mkdir(parents=True, exist_ok=True)

    cpumetrics = collectCPUmetrics()
    carbonmetrics = get_carbon_report("b4003998-9034-4e5d-86fa-1162338a0a4a", "2026-07-20", "2026-08-20")
    pcm = sintetizar(cpumetrics, carbonmetrics)

    ident = f"{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex[:8]}"
    ruta_wav = directorio / f"{ident}.wav"
    escribir_wav(ruta_wav, pcm)

    meta = {
        "id": ident,
        "archivo": ruta_wav.name,
        "generado_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "duracion_audio_s": round(len(pcm) / SR, 3),
        "metricas": cpumetrics,
        "carbon_metrics": carbonmetrics["value"][0]
    }
    (directorio / f"{ident}.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return meta


if __name__ == "__main__":
    print(json.dumps(generar(), indent=2, ensure_ascii=False))
