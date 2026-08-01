FROM python:3.11-slim

WORKDIR /app

# las dependencias primero: esta capa se cachea y no se reconstruye
# cada vez que tocas el codigo o el texto de la obra
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY trespesos_audio.py main.py ./
COPY static/ ./static/

# aqui caen los .wav y los .json. Montalo como volumen para conservarlos.
RUN mkdir -p /app/audio

EXPOSE 8000

# un solo worker: la medicion de CPU es una lectura del estado global de la maquina,
# varios procesos midiendo en paralelo se contaminarian entre si.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]