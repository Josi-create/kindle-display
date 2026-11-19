#!/usr/bin/env python3
"""Holt die Daten für die Kindle-Anzeige aus Home Assistant (nur lesend).

Braucht in der Umgebung:  HA_ACCESS_TOKEN  (Token des HA-Benutzers "kindle")
und HA_BASE_URL. Welche Entitäten gelesen werden, steht in einstellungen.py. sammeln() liefert genau das, was bild.zeichne() erwartet.

Aufruf zum Ausprobieren:  python daten.py   (zeigt nur, wie viel gefunden wurde)
"""
import json
import math
import os
import time
import urllib.request
from datetime import date, datetime, timedelta, timezone

from einstellungen import (AKKU, KALENDER, LAEDT, MUELL, MUELL_HEUTE_BIS, MUELLNAMEN, OPEN_METEO,
                           PFLANZEN, RAEUME, WETTER)

HA = os.environ.get("HA_BASE_URL", "http://homeassistant.local:8123").rstrip("/")
WARTEN = 20  # Sekunden

# Met.no (über HA) liefert außerhalb Skandinaviens keine Regenwahrscheinlichkeit, die kommt von
# Open-Meteo. Der Wohnort geht dafür auf zwei Nachkommastellen gerundet (etwa 1 km) an Open-Meteo.
REGENRISIKO = ("https://api.open-meteo.com/v1/forecast?latitude={:.2f}&longitude={:.2f}"
               "&hourly=precipitation_probability&forecast_days=3&timeformat=unixtime")
REGENRISIKO_ALLE = 30 * 60  # Sekunden zwischen zwei Abrufen

WETTERTEXT = {
    "sunny": "Sonnig", "clear-night": "Klare Nacht", "partlycloudy": "Leicht bewölkt",
    "cloudy": "Bewölkt", "rainy": "Regen", "pouring": "Starkregen", "snowy": "Schnee",
    "snowy-rainy": "Schneeregen", "fog": "Nebel", "hail": "Hagel", "lightning": "Gewitter",
    "lightning-rainy": "Gewitter mit Regen", "windy": "Windig", "windy-variant": "Windig",
    "exceptional": "Unwetter",
}
TAGE = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
TERMINTAGE = 4  # heute, morgen und zwei weitere Tage, falls im Bild Platz ist


def _ha(pfad, daten=None):
    anfrage = urllib.request.Request(
        HA + pfad, data=None if daten is None else json.dumps(daten).encode(),
        headers={"Authorization": "Bearer " + os.environ["HA_ACCESS_TOKEN"].strip(),
                 "Content-Type": "application/json"})
    with urllib.request.urlopen(anfrage, timeout=WARTEN) as antwort:
        return json.load(antwort)


def _dienst(dienst, entitaet, **daten):
    """Ruft einen HA-Dienst auf, der nur Daten zurückgibt (z. B. calendar.get_events)."""
    antwort = _ha(f"/api/services/{dienst.replace('.', '/')}?return_response",
                  {"entity_id": entitaet, **daten})
    return antwort["service_response"][entitaet]


def _zahl(zustaende, entitaet):
    try:
        return float(zustaende[entitaet]["state"])
    except (KeyError, ValueError):
        return None  # fehlt, "unavailable" oder "unknown"


def _zeit(text):
    """'2026-11-16T15:00:00+01:00' -> Ortszeit, '2026-11-16' -> Datum."""
    if len(text) == 10:
        return date.fromisoformat(text)
    return datetime.fromisoformat(text).astimezone()


def _mondphase(jetzt):
    """(beleuchteter Anteil 0..1, zunehmend?) - gerechnet ab dem Neumond vom 6.1.2000.

    Mittlere Umlaufzeit, dadurch höchstens etwa einen halben Tag daneben.
    """
    tage = (jetzt - datetime(2000, 1, 6, 18, 14, tzinfo=timezone.utc)).total_seconds() / 86400
    umlauf = tage / 29.530588853 % 1  # 0 = Neumond, 0,5 = Vollmond
    return (1 - math.cos(2 * math.pi * umlauf)) / 2, umlauf < 0.5


_regenrisiko_stand = (0, {})  # (Zeitpunkt des Abrufs, {Stunde als Unixzeit: Prozent})


def _regenrisiko():
    """Regenwahrscheinlichkeit je Stunde; der Wert gilt jeweils für die Stunde DAVOR."""
    global _regenrisiko_stand
    if not OPEN_METEO:
        return {}
    if time.time() - _regenrisiko_stand[0] > REGENRISIKO_ALLE:
        try:
            ort = _ha("/api/config")
            with urllib.request.urlopen(REGENRISIKO.format(ort["latitude"], ort["longitude"]),
                                        timeout=WARTEN) as antwort:
                stunden = json.load(antwort)["hourly"]
            _regenrisiko_stand = (time.time(), dict(zip(stunden["time"], stunden["precipitation_probability"])))
        except Exception as fehler:  # dann weiter mit den alten Werten
            print("Regenwahrscheinlichkeit fehlt:", type(fehler).__name__, flush=True)
    return _regenrisiko_stand[1]


def _wetter(zustaende, jetzt):
    zustand = zustaende[WETTER]["state"]
    w = {"zustand": zustand, "text": WETTERTEXT.get(zustand, zustand),
         "temp": zustaende[WETTER]["attributes"].get("temperature"), "regen_heute": None, "tage": [],
         # Nachts zeigt das Bild einen Mond statt der Sonne (z. B. bei "Leicht bewölkt")
         "nacht": zustaende.get("sun.sun", {}).get("state") == "below_horizon",
         "mond": _mondphase(jetzt),
         "feuchte": zustaende[WETTER]["attributes"].get("humidity"),
         "wind": zustaende[WETTER]["attributes"].get("wind_speed"),
         "wind_einheit": zustaende[WETTER]["attributes"].get("wind_speed_unit", "")}
    try:
        for f in _dienst("weather.get_forecasts", WETTER, type="daily")["forecast"]:
            tag = _zeit(f["datetime"]).date()
            if tag > jetzt.date():
                w["tage"].append((TAGE[tag.weekday()], f["condition"], f["temperature"],
                                  f.get("templow", f["temperature"]), f.get("precipitation") or 0))
        vorhersage = _dienst("weather.get_forecasts", WETTER, type="hourly")["forecast"]
        stunden = [(_zeit(f["datetime"]), f.get("precipitation") or 0) for f in vorhersage]
        # Verlauf der nächsten 24 Stunden: (Beginn der Stunde, Temperatur, Regenwahrscheinlichkeit in %)
        risiko = _regenrisiko()
        w["stunden"] = [(_zeit(f["datetime"]), f.get("temperature"),
                         risiko.get(int(_zeit(f["datetime"]).timestamp()) + 3600)) for f in vorhersage[:24]]
        heute = [(z, mm) for z, mm in stunden if z.date() == jetzt.date()]
        w["regen_heute"] = sum(mm for _, mm in heute)
        nass = [z for z, mm in heute if mm >= 0.1]
        if nass and nass[0] > jetzt:
            w["regen_ab"] = f"{nass[0].hour} Uhr"
    except Exception as fehler:
        print("Wettervorhersage fehlt:", type(fehler).__name__, flush=True)
    return w


def _termine(jetzt):
    """Termine ab heute, je Tag eine Liste aus ('09:00 – 18:00' oder 'ganztägig', Titel)."""
    tag0 = jetzt.replace(hour=0, minute=0, second=0, microsecond=0)
    alle = []
    for kalender in KALENDER:
        alle += _dienst("calendar.get_events", kalender, start_date_time=tag0.isoformat(),
                        end_date_time=(tag0 + timedelta(days=TERMINTAGE)).isoformat())["events"]
    listen = []
    for nr in range(TERMINTAGE):
        frueh = tag0 + timedelta(days=nr)
        spaet, zeilen = frueh + timedelta(days=1), []
        for termin in alle:
            start, ende = _zeit(termin["start"]), _zeit(termin["end"])
            if not isinstance(start, datetime):  # ganztägig, Ende ist der Tag danach
                if start <= frueh.date() < ende:
                    zeilen.append((0, frueh, "ganztägig", termin["summary"]))
            elif start < spaet and ende > frueh and ende > jetzt:  # Vergangenes weglassen
                if start >= frueh:
                    zeit = f"{start:%H:%M}"
                    if start < ende <= spaet:  # endet am selben Tag
                        zeit += f" – {ende:%H:%M}"
                else:  # läuft seit gestern
                    zeit = f"bis {ende:%H:%M}" if ende < spaet else "ganztägig"
                zeilen.append((1, start, zeit, termin["summary"]))
        listen.append([(zeit, titel) for _, _, zeit, titel in sorted(zeilen, key=lambda z: z[:2])])
    return listen


def _muell(jetzt):
    """Die nächsten zwei Abfuhrtage: [('Do, 19.11.', 'Restmüll, Bio'), ...]"""
    tag0 = jetzt.replace(hour=0, minute=0, second=0, microsecond=0)
    termine = _dienst("calendar.get_events", MUELL, start_date_time=tag0.isoformat(),
                      end_date_time=(tag0 + timedelta(days=28)).isoformat())["events"]
    tage = {}
    for termin in termine:
        tag = _zeit(termin["start"])
        tag = tag.date() if isinstance(tag, datetime) else tag
        if tag < jetzt.date() or (tag == jetzt.date() and jetzt.hour >= MUELL_HEUTE_BIS):
            continue
        tage.setdefault(tag, set()).add(termin["summary"])
    zeilen = []
    for tag in sorted(tage)[:2]:
        sorten = [kurz for teil, kurz in MUELLNAMEN if any(teil in name for name in tage[tag])]
        abstand = (tag - jetzt.date()).days
        wann = ("Heute", "Morgen")[abstand] if abstand < 2 else f"{TAGE[tag.weekday()]}, {tag.day}.{tag.month}."
        zeilen.append((wann, ", ".join(sorten) or "Abfuhr"))
    return zeilen


def sammeln(akku=None, laedt=None):
    """Alle Daten für das Bild. akku/laedt: frische Werte vom Kindle, sonst die aus HA."""
    jetzt = datetime.now().astimezone()
    zustaende = {z["entity_id"]: z for z in _ha("/api/states")}
    d = {
        "jetzt": jetzt,
        "akku": akku if akku is not None else _zahl(zustaende, AKKU),
        "laedt": laedt if laedt is not None else zustaende.get(LAEDT, {}).get("state") == "on",
        "wetter": _wetter(zustaende, jetzt),
        "raeume": [(name, min((t for t in (_zahl(zustaende, f) for f in fuehler) if t is not None),
                              default=None)) for name, fuehler in RAEUME],
        "pflanzen": [(name, _zahl(zustaende, fuehler), grenze) for name, fuehler, grenze in PFLANZEN],
    }
    try:
        listen = _termine(jetzt)
        d["heute"], d["morgen"] = listen[:2]
        d["weitere"] = [(jetzt.date() + timedelta(days=nr), liste) for nr, liste in enumerate(listen[2:], 2)]
    except Exception as fehler:
        print("Kalender fehlt:", type(fehler).__name__, flush=True)
        d["heute"] = d["morgen"] = None
        d["weitere"] = []
    try:
        d["muell"] = _muell(jetzt)
    except Exception as fehler:
        print("Müllkalender fehlt:", type(fehler).__name__, flush=True)
        d["muell"] = []
    return d


if __name__ == "__main__":
    d = sammeln()
    print("Stand:", f"{d['jetzt']:%d.%m.%Y %H:%M}", "| Akku:", d["akku"], "| lädt:", d["laedt"])
    print("Termine heute/morgen/weitere:", *(len(l) if l is not None else "fehlt" for l in (d["heute"], d["morgen"])),
          *(len(l) for _, l in d["weitere"]))
    print("Wetter:", {k: v for k, v in d["wetter"].items() if k not in ("tage", "stunden")}, d["wetter"]["tage"])
    print("Stunden:", [(f"{z:%H}", t, p) for z, t, p in d["wetter"].get("stunden", [])])
    print("Räume:", d["raeume"])
    print("Müll:", d["muell"], "| Pflanzen:", d["pflanzen"])
