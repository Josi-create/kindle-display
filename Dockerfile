# Kindle-Anzeige: zeichnet das Bild selbst (Python + Pillow) und liefert es auf Port 5000
FROM python:3.12-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends fonts-noto-core \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir pillow==13.0.0
WORKDIR /app
COPY bild.py bild2.py daten.py server.py ./
# Vorgabe; docker-compose.yml legt die eigene einstellungen.py darüber
COPY einstellungen.beispiel.py einstellungen.py
ENV PYTHONDONTWRITEBYTECODE=1
EXPOSE 5000
CMD ["python", "-u", "server.py"]
