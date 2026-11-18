#!/usr/bin/env python3
"""Reicht öffentliche iCloud-Kalender repariert an Home Assistant weiter.

Hintergrund: Apple schreibt bei Terminen mit mehrzeiliger Adresse einen echten
Zeilenumbruch in die Zeile X-APPLE-STRUCTURED-LOCATION. Das ist kein gültiges
Kalenderformat, die HA-Integration "Remote Calendar" bricht daran ab.

Dieses Programm holt die Kalenderdatei NUR LESEND über den öffentlichen Link,
wirft die Apple-Ortszeilen weg (der normale Ort bleibt erhalten) und liefert
den Rest unverändert aus. Es holt nur, wenn Home Assistant danach fragt.

Die Links stehen in der Datei .env (nie hier im Programm):
    KALENDER_PRIVAT=https://...    ->  http://127.0.0.1:5001/privat.ics
    KALENDER_FAMILIE=https://...   ->  http://127.0.0.1:5001/familie.ics

Aufruf zum Prüfen einer Datei:  python kalenderfilter.py datei.ics
"""
import os
import re
import sys
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = 5001
MERKEN = 300  # Sekunden, so lange wird eine geholte Datei wiederverwendet
WARTEN = 30  # Sekunden, dann gilt iCloud als nicht erreichbar
VORSATZ = "KALENDER_"

# So beginnt eine echte Kalenderzeile: Name in Großbuchstaben, dann ; oder :
_ZEILENANFANG = re.compile(r"[A-Z][A-Z0-9-]*[;:]")
_WEG = ("X-APPLE-STRUCTURED-LOCATION", "X-APPLE-TRAVEL-START")
# Diese Angaben darf es je Termin nur einmal geben, iCloud liefert sie manchmal doppelt
_EINMALIG = {"UID", "DTSTAMP", "DTSTART", "DTEND", "DURATION", "RRULE", "RECURRENCE-ID",
             "SUMMARY", "DESCRIPTION", "LOCATION", "STATUS", "TRANSP", "SEQUENCE",
             "CREATED", "LAST-MODIFIED", "CLASS", "PRIORITY", "URL", "GEO", "ORGANIZER"}

_gemerkt = {}


def reparieren(text):
    """Macht aus dem Text von iCloud eine gültige Kalenderdatei."""
    zeilen = []  # ganze Einträge, umbrochene Zeilen wieder zusammengesetzt
    for roh in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if not roh:
            continue
        if roh[0] in " \t" and zeilen:
            zeilen[-1] += roh[1:]  # regulärer Umbruch nach Vorschrift
        elif _ZEILENANFANG.match(roh) or not zeilen:
            zeilen.append(roh)
        else:
            zeilen[-1] += " " + roh  # verirrter Umbruch mitten im Eintrag
    fertig, offen = [], [set()]  # offen: je Abschnitt (Termin, Wecker ...) schon gesehene Namen
    for zeile in zeilen:
        name = re.split("[;:]", zeile, maxsplit=1)[0]
        if name in _WEG:
            continue
        if name == "BEGIN":
            offen.append(set())
        elif name == "END" and len(offen) > 1:
            offen.pop()
        elif name in _EINMALIG:
            if name in offen[-1]:
                continue  # doppelt vorhanden, der erste Eintrag gilt
            offen[-1].add(name)
        fertig.append(_umbrechen(zeile))
    return "".join(fertig)


def _umbrechen(zeile, laenge=75):
    """Bricht lange Zeilen wieder nach Vorschrift um (höchstens 75 Bytes)."""
    teile, aktuell, platz = [], "", laenge
    for zeichen in zeile:
        breite = len(zeichen.encode("utf-8"))
        if breite > platz:
            teile.append(aktuell)
            aktuell, platz = " ", laenge - 1
        aktuell += zeichen
        platz -= breite
    teile.append(aktuell)
    return "\r\n".join(teile) + "\r\n"


def links():
    """Liest die Kalender-Links aus der Umgebung: {"privat": "https://..."}."""
    gefunden = {}
    for name, wert in os.environ.items():
        wert = wert.strip()
        if not name.startswith(VORSATZ) or not wert:
            continue
        if wert.startswith("webcal://"):
            wert = "https://" + wert[len("webcal://"):]
        if wert.startswith("https://"):
            gefunden[name[len(VORSATZ):].lower()] = wert
    return gefunden


def holen(name, link):
    """Holt einen Kalender von iCloud und repariert ihn."""
    alt = _gemerkt.get(name)
    if alt and time.monotonic() - alt[0] < MERKEN:
        return alt[1]
    with urllib.request.urlopen(link, timeout=WARTEN) as antwort:
        text = antwort.read().decode("utf-8", errors="replace")
    if "BEGIN:VCALENDAR" not in text:
        raise ValueError("Antwort ist keine Kalenderdatei")
    daten = reparieren(text).encode("utf-8")
    _gemerkt[name] = (time.monotonic(), daten)
    return daten


class Anfrage(BaseHTTPRequestHandler):
    def do_GET(self):
        pfad = self.path.split("?", 1)[0]
        if pfad == "/health":
            return self._antwort(200, b"ok\n", "text/plain")
        name = pfad[1:-4] if pfad.endswith(".ics") else None
        link = links().get(name)
        if not link:
            return self._antwort(404, b"unbekannter Kalender\n", "text/plain")
        try:
            daten = holen(name, link)
        except Exception as fehler:  # Link nie ausgeben, nur die Art des Fehlers
            print(f"Fehler bei {name}: {type(fehler).__name__}", flush=True)
            return self._antwort(502, b"Kalender nicht abrufbar\n", "text/plain")
        self._antwort(200, daten, "text/calendar; charset=utf-8")

    def _antwort(self, status, daten, art):
        self.send_response(status)
        self.send_header("Content-Type", art)
        self.send_header("Content-Length", str(len(daten)))
        self.end_headers()
        self.wfile.write(daten)

    def log_message(self, format, *args):
        print(f"{self.command} {self.path.split('?', 1)[0]} -> {args[1]}", flush=True)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        with open(sys.argv[1], encoding="utf-8", newline="") as datei:
            sys.stdout.write(reparieren(datei.read()))
        sys.exit()
    print(f"Kalender: {', '.join(sorted(links())) or 'keine eingetragen'}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Anfrage).serve_forever()
