"""
Tres Pesos / Cloud Resonance
Genera un archivo .wav a partir de las metricas de CPU de la maquina que lo ejecuta.

Dos fases separadas:
  1. MEDICION  -> ~2 segundos reales leyendo /proc/stat via psutil
  2. SINTESIS  -> 30 segundos de audio a partir de esas mediciones (milisegundos de calculo)

La separacion mantiene el request HTTP corto para el frontend.
"""

import json
import math
import struct
import time
import uuid
import wave
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import psutil

# ---------------------------------------------------------------- parametros

SR = 44100                  # frecuencia de muestreo
N_MEDICIONES = 20           # numero de lecturas de CPU
INTERVALO = 0.1             # segundos entre lecturas -> 2.0 s de medicion total
DURACION = 30.0             # segundos de audio de salida

FREQ_MIN = 55.0             # Hz - voz principal (busy)
FREQ_MAX = 200.0

# La voz de 'steal' NO se normaliza de forma adaptativa: escala absoluta.
# Si nadie te robo ciclos, este canal queda literalmente en silencio.
STEAL_ESCALA = 0.05         # segundos de CPU robada por intervalo = amplitud maxima
STEAL_GANANCIA = 0.30       # techo de la voz de steal en la mezcla

GANANCIA_PRINCIPAL = 0.70
ARMONICO_2 = 0.15           # un poco de cuerpo, no es un seno puro
FADE = 0.25                 # segundos de fade in / fade out
EPSILON = 1e-9              # umbral para considerar la señal plana

SALIDA = Path(__file__).resolve().parent / "audio"


# ---------------------------------------------------------------- 1. medicion

def medir_cpu(n=N_MEDICIONES, intervalo=INTERVALO):
    """Lee los contadores de CPU y devuelve los deltas entre lecturas consecutivas."""
    lecturas = []
    prev = psutil.cpu_times()
    prev_stats = psutil.cpu_stats()
    t0 = time.time()

    for _ in range(n):
        time.sleep(intervalo)
        cur = psutil.cpu_times()
        cur_stats = psutil.cpu_stats()

        delta_busy = (cur.user - prev.user) + (cur.system - prev.system)
        # 'steal' solo existe en Linux. En Windows getattr devuelve 0.0 y el script corre igual.
        delta_steal = getattr(cur, "steal", 0.0) - getattr(prev, "steal", 0.0)

        lecturas.append({
            "busy": max(0.0, delta_busy),
            "steal": max(0.0, delta_steal),
            # no alimentan el audio, quedan archivadas por si luego sirven
            "ctx_switches": cur_stats.ctx_switches - prev_stats.ctx_switches,
            "interrupts": cur_stats.interrupts - prev_stats.interrupts,
        })

        prev, prev_stats = cur, cur_stats

    return lecturas, time.time() - t0


# ------------------------------------------------------- 2. normalizacion

def normalizar_adaptativo(valores):
    """
    Escala los valores a 0..1 usando su propio min/max.
    En una maquina ociosa esto amplifica el ruido de fondo del sistema,
    que es justo lo que queremos oir. Si no hay variacion, devuelve 0.5.
    """
    v = np.asarray(valores, dtype=np.float64)
    lo, hi = v.min(), v.max()
    if (hi - lo) < EPSILON:
        return np.full_like(v, 0.5), True          # señal plana
    return (v - lo) / (hi - lo), False


# ---------------------------------------------------------------- 3. sintesis

def sintetizar(lecturas, duracion=DURACION):
    """Convierte las mediciones en una onda. Fase continua entre bloques."""
    n = len(lecturas)
    muestras_bloque = int(SR * duracion / n)

    busy_norm, plana = normalizar_adaptativo([l["busy"] for l in lecturas])
    steal_raw = np.asarray([l["steal"] for l in lecturas], dtype=np.float64)

    # mapeos
    freqs = FREQ_MIN + busy_norm * (FREQ_MAX - FREQ_MIN)
    amps = 0.35 + busy_norm * 0.65
    # escala ABSOLUTA: 0 robado = 0 amplitud. Sin trampas.
    steal_amps = np.clip(steal_raw / STEAL_ESCALA, 0.0, 1.0)

    bloques = []
    fase = 0.0          # voz principal
    fase_steal = 0.0    # sub-octava

    for i in range(n):
        f_ini = freqs[i - 1] if i > 0 else freqs[i]
        a_ini = amps[i - 1] if i > 0 else amps[i]
        s_ini = steal_amps[i - 1] if i > 0 else steal_amps[i]

        # rampas lineales dentro del bloque: sin saltos de tono ni de volumen
        f = np.linspace(f_ini, freqs[i], muestras_bloque, endpoint=False)
        a = np.linspace(a_ini, amps[i], muestras_bloque, endpoint=False)
        s = np.linspace(s_ini, steal_amps[i], muestras_bloque, endpoint=False)

        # la fase se acumula, nunca se reinicia -> sin clicks en los bordes
        fase_arr = fase + np.cumsum(2.0 * math.pi * f / SR)
        fase = float(fase_arr[-1] % (2.0 * math.pi))

        fase_steal_arr = fase_steal + np.cumsum(2.0 * math.pi * (f / 2.0) / SR)
        fase_steal = float(fase_steal_arr[-1] % (2.0 * math.pi))

        voz = np.sin(fase_arr) + ARMONICO_2 * np.sin(2.0 * fase_arr)
        voz *= a * GANANCIA_PRINCIPAL

        # una octava abajo, solo suena si de verdad hubo robo de ciclos
        voz += np.sin(fase_steal_arr) * s * STEAL_GANANCIA

        bloques.append(voz)

    señal = np.concatenate(bloques)

    # fades para que el archivo no truene al abrir ni al terminar
    nf = min(int(SR * FADE), len(señal) // 2)
    if nf > 0:
        señal[:nf] *= np.linspace(0.0, 1.0, nf)
        señal[-nf:] *= np.linspace(1.0, 0.0, nf)

    pcm = np.clip(señal, -1.0, 1.0) * 32767.0
    return pcm.astype("<i2"), plana


# ---------------------------------------------------------------- 4. escritura

def escribir_wav(ruta, pcm):
    with wave.open(str(ruta), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())      # una sola operacion, no un pack por muestra


# ---------------------------------------------------------------- orquestacion

def generar(directorio=SALIDA):
    """
    Mide, sintetiza, guarda .wav + .json y devuelve los metadatos.
    Pensado para que FastAPI lo llame directamente.
    """
    directorio = Path(directorio)
    directorio.mkdir(parents=True, exist_ok=True)

    lecturas, t_medicion = medir_cpu()
    t0 = time.time()
    pcm, plana = sintetizar(lecturas)
    t_sintesis = time.time() - t0

    ident = f"{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex[:8]}"
    ruta_wav = directorio / f"{ident}.wav"
    escribir_wav(ruta_wav, pcm)

    steal_total = sum(l["steal"] for l in lecturas)
    busy_total = sum(l["busy"] for l in lecturas)

    meta = {
        "id": ident,
        "archivo": ruta_wav.name,
        "generado_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "duracion_audio_s": round(len(pcm) / SR, 3),
        "ventana_medicion_s": round(t_medicion, 3),
        "tiempo_sintesis_s": round(t_sintesis, 3),
        "mediciones": len(lecturas),
        "nucleos": psutil.cpu_count(),
        "cpu_busy_total_s": round(busy_total, 4),
        "cpu_steal_total_s": round(steal_total, 6),   # se muestra aunque sea 0.000000
        "steal_audible": bool(steal_total > 0),
        "señal_plana": bool(plana),
        "freq_hz": [round(FREQ_MIN, 1), round(FREQ_MAX, 1)],
        "lecturas": lecturas,
    }

    (directorio / f"{ident}.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return meta


if __name__ == "__main__":
    m = generar()
    print(f"  archivo   : {m['archivo']}")
    print(f"  audio     : {m['duracion_audio_s']} s")
    print(f"  medicion  : {m['ventana_medicion_s']} s")
    print(f"  sintesis  : {m['tiempo_sintesis_s']} s")
    print(f"  cpu busy  : {m['cpu_busy_total_s']} s")
    print(f"  cpu steal : {m['cpu_steal_total_s']} s"
          f"{'  <-- audible' if m['steal_audible'] else '  (silencio)'}")
    print(f"  plana     : {m['señal_plana']}")