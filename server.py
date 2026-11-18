#!/usr/bin/env python3
"""Liefert das Bild für die Kindle-Anzeige aus (Port 5000).

    http://<server>:5000/                              -> PNG 600x800, Graustufen
    http://<server>:5000/?batteryLevel=77&isCharging=0 -> dasselbe, Akkustand geht
                                                          per Webhook an Home Assistant

Das Bild wird bei jedem Abruf frisch gezeichnet. Ist Home Assistant gerade nicht
erreichbar, kommt das letzte gelungene Bild (höchstens ein paar Stunden alt).
"""
import io
import json
import os
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

import bild
import bild2
import daten

PORT = 5000
ALT_HOECHSTENS = 6 * 3600  # Sekunden, so lange darf das letzte Bild als Ersatz dienen

_sperre = threading.Lock()
_letztes = (0, None)  # (Zeitpunkt, PNG)


def png(image):
    puffer = io.BytesIO()
    image.save(puffer, "PNG")
    return puffer.getvalue()


def stoerung(text):
    """Schlichtes Bild mit einer Meldung, wenn gar nichts geht."""
    b = bild.Blatt()
    b.text(bild.RAND, 90, "Kindle-Anzeige", 40, "fett")
    b.text(bild.RAND, 140, text, 22, farbe=bild.DUNKEL)
    b.text(bild.RAND, 176, time.strftime("Stand %d.%m. %H:%M"), 18, farbe=bild.GRAU)
    return b.fertig()


def akku_melden(stand, laedt):
    """Gibt den Akkustand an den HA-Webhook weiter (Automation 'Kindle Akkustand übernehmen')."""
    webhook = os.environ.get("HA_BATTERY_WEBHOOK", "").strip()
    if not webhook:
        return
    anfrage = urllib.request.Request(
        f"{daten.HA}/api/webhook/{webhook}",
        data=json.dumps({"batteryLevel": stand, "isCharging": bool(laedt)}).encode(),
        headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(anfrage, timeout=10).close()
    except Exception as fehler:  # Adresse nie ausgeben, sie enthält die Webhook-ID
        print("Akku-Meldung fehlgeschlagen:", type(fehler).__name__, flush=True)


def aktuelles_bild(akku, laedt):
    global _letztes
    with _sperre:
        try:
            _letztes = (time.time(), png(bild2.zeichne(daten.sammeln(akku, laedt))))
        except Exception as fehler:
            print("Bild nicht erneuert:", type(fehler).__name__, flush=True)
            if time.time() - _letztes[0] > ALT_HOECHSTENS:
                return png(stoerung("Home Assistant ist nicht erreichbar."))
        return _letztes[1]


class Anfrage(BaseHTTPRequestHandler):
    def do_GET(self):
        url = urlsplit(self.path)
        if url.path == "/health":
            return self._antwort(200, b"ok\n", "text/plain")
        if url.path not in ("/", "/1"):
            return self._antwort(404, b"nicht gefunden\n", "text/plain")
        angaben = parse_qs(url.query)
        akku, laedt = None, None
        try:
            akku = int(angaben["batteryLevel"][0])
        except (KeyError, ValueError):
            pass
        if akku is not None and 0 <= akku <= 100:
            laedt = angaben.get("isCharging", ["0"])[0] in ("1", "Yes")
            akku_melden(akku, laedt)
        else:
            akku = None
        self._antwort(200, aktuelles_bild(akku, laedt), "image/png")

    def _antwort(self, status, inhalt, art):
        self.send_response(status)
        self.send_header("Content-Type", art)
        self.send_header("Content-Length", str(len(inhalt)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(inhalt)

    def log_message(self, format, *args):
        print(f"{self.command} {self.path} -> {args[1]}", flush=True)


if __name__ == "__main__":
    print(f"Kindle-Anzeige auf Port {PORT}, Home Assistant: {daten.HA}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Anfrage).serve_forever()
