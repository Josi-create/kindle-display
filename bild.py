#!/usr/bin/env python3
"""Zeichnet das Bild für die Kindle-Anzeige (600x800, 8-Bit-Graustufen).

Aufruf zum Ausprobieren:  python bild.py entwurf.png
Dann wird ein Bild mit Beispieldaten erzeugt. Im Betrieb liefert später
ein zweites Skript die echten Daten aus Home Assistant an zeichne().
"""
import math
import os
import sys
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont

BREITE, HOEHE = 600, 800
S = 2  # intern doppelt so groß zeichnen, am Ende verkleinern -> glatte Kanten
RAND = 32

SCHWARZ, DUNKEL, GRAU, HELL, WEISS = 0, 70, 120, 200, 255

# Schriften: erst im eigenen Ordner "schrift" suchen (Container), sonst die vom System
_ORDNER = [os.path.join(os.path.dirname(os.path.abspath(__file__)), "schrift"), "/usr/share/fonts/truetype/noto",
           "/usr/share/fonts/noto"]
SCHRIFT = {
    art: next((p for p in (os.path.join(o, datei) for o in _ORDNER) if os.path.exists(p)), datei)
    for art, datei in (("normal", "NotoSans-Regular.ttf"), ("fett", "NotoSans-Bold.ttf"))
}
WOCHENTAGE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
MONATE = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August",
          "September", "Oktober", "November", "Dezember"]

_schriften = {}


def schrift(groesse, art="normal"):
    key = (groesse, art)
    if key not in _schriften:
        _schriften[key] = ImageFont.truetype(SCHRIFT[art], groesse * S)
    return _schriften[key]


def zahl(wert, stellen=1):
    """12.4 -> '12,4' (deutsches Komma)."""
    return f"{wert:.{stellen}f}".replace(".", ",")


class Blatt:
    """Dünne Hülle um ImageDraw: alle Angaben in Kindle-Pixeln (600x800)."""

    def __init__(self):
        self.img = Image.new("L", (BREITE * S, HOEHE * S), WEISS)
        self.d = ImageDraw.Draw(self.img)

    def text(self, x, y, s, groesse, art="normal", farbe=SCHWARZ, anker="ls", max_breite=None):
        f = schrift(groesse, art)
        if max_breite is not None:
            s = self.kuerzen(s, f, max_breite)
        self.d.text((x * S, y * S), s, font=f, fill=farbe, anchor=anker)
        return f.getlength(s) / S

    def kuerzen(self, s, f, max_breite):
        if f.getlength(s) <= max_breite * S:
            return s
        while s and f.getlength(s.rstrip() + "…") > max_breite * S:
            s = s[:-1]
        return s.rstrip() + "…"

    def titel(self, x, y, s, farbe=GRAU):
        """Kleine gesperrte Überschrift in Großbuchstaben."""
        f = schrift(13, "fett")
        for zeichen in s.upper():
            self.d.text((x * S, y * S), zeichen, font=f, fill=farbe, anchor="ls")
            x += f.getlength(zeichen) / S + 2.2
        return x

    def linie(self, x1, y1, x2, y2, dicke=1, farbe=SCHWARZ):
        self.d.line((x1 * S, y1 * S, x2 * S, y2 * S), fill=farbe, width=round(dicke * S))

    def rechteck(self, x1, y1, x2, y2, farbe=SCHWARZ, radius=0, rand=None, dicke=1):
        self.d.rounded_rectangle((x1 * S, y1 * S, x2 * S, y2 * S), radius=radius * S, fill=farbe,
                                 outline=rand, width=round(dicke * S))

    def kreis(self, cx, cy, r, farbe=SCHWARZ):
        self.d.ellipse(((cx - r) * S, (cy - r) * S, (cx + r) * S, (cy + r) * S), fill=farbe)

    def fertig(self):
        return self.img.resize((BREITE, HOEHE), Image.LANCZOS)


# ---------------------------------------------------------------- Symbole

def _wolke(b, cx, cy, s, t, innen=WEISS, hof=None, sp=1):
    """Wolke als Umriss: erst schwarz, dann um die Strichdicke kleiner in der Innenfarbe.

    hof: Farbe für einen schmalen Spalt rund um die Wolke (trennt sie vom Mond dahinter).
    sp=-1 zeichnet die Wolke spiegelverkehrt (großer Bogen links).
    """
    for farbe, e in ([(hof, -0.7 * t)] if hof is not None else []) + [(SCHWARZ, 0), (innen, t)]:
        b.rechteck(cx - 0.46 * s + e, cy + 0.02 * s + e, cx + 0.46 * s - e, cy + 0.34 * s - e,
                   farbe=farbe, radius=max(0.16 * s - e, 0))
        b.kreis(cx - sp * 0.20 * s, cy + 0.04 * s, 0.19 * s - e, farbe)
        b.kreis(cx + sp * 0.10 * s, cy - 0.06 * s, 0.27 * s - e, farbe)
    # Zwickel zwischen den Kreisen füllen, sonst bleibt bei großen Symbolen ein Punkt stehen
    x1, x2 = sorted((cx - sp * 0.20 * s, cx + sp * 0.10 * s))
    b.rechteck(x1, cy, x2, cy + 0.20 * s, farbe=innen)


def _sonne(b, cx, cy, s, t, hg=WEISS):
    r = 0.20 * s
    b.kreis(cx, cy, r, SCHWARZ)
    b.kreis(cx, cy, r - t, hg)
    for i in range(8):
        w = i * math.pi / 4
        b.linie(cx + math.cos(w) * 0.30 * s, cy + math.sin(w) * 0.30 * s,
                cx + math.cos(w) * 0.44 * s, cy + math.sin(w) * 0.44 * s, dicke=t)


MOND_STANDARD = (0.3, False)  # (beleuchteter Anteil 0..1, zunehmend?) - ohne Angabe eine Sichel
MOND_NEIGUNG = 35  # Grad: die helle Seite zeigt schräg nach unten, wie am Abend- und Morgenhimmel


def _mond(b, cx, cy, s, t, hg=WEISS, phase=None):
    """Mond in der richtigen Phase: schwarz ist der beleuchtete Teil.

    Zunehmend ist die rechte Seite hell, abnehmend die linke (Nordhalbkugel).
    """
    anteil, zunehmend = phase or MOND_STANDARD
    r, seite = 0.30 * s, 1 if zunehmend else -1
    if anteil < 0.04:  # Neumond: nur ein Ring
        b.kreis(cx, cy, r, SCHWARZ)
        b.kreis(cx, cy, r - 0.6 * t, hg)
        return
    anteil = max(anteil, 0.28)  # schmale Sicheln etwas kräftiger, sonst sind sie kaum zu sehen
    schritte = [math.radians(g) for g in range(-90, 91, 3)]
    aussen = [(r * math.cos(a), r * math.sin(a)) for a in schritte]
    grenze = [(r * (1 - 2 * anteil) * math.cos(a), r * math.sin(a)) for a in reversed(schritte)]
    w = math.radians(MOND_NEIGUNG)
    punkte = [((cx + seite * (x * math.cos(w) - y * math.sin(w))) * S, (cy + x * math.sin(w) + y * math.cos(w)) * S)
              for x, y in aussen + grenze]
    b.d.polygon(punkte, fill=SCHWARZ)


def _tropfen(b, cx, cy, s, anzahl, t):
    abstand = 0.22 * s
    start = cx - abstand * (anzahl - 1) / 2
    for i in range(anzahl):
        x = start + i * abstand
        b.linie(x + 0.04 * s, cy, x - 0.04 * s, cy + 0.16 * s, dicke=t)


def wettersymbol(b, zustand, cx, cy, s, nacht=False, innen=WEISS, hg=WEISS, mond=None):
    """Zeichnet das Symbol für einen Home-Assistant-Wetterzustand, s = Größe in Pixeln.

    nacht: Mond statt Sonne, mond = (beleuchteter Anteil, zunehmend?) für die Mondphase.
    innen = Füllung der Wolken, hg = Farbe des Untergrunds.
    """
    t = max(s * 0.055, 1.6)
    if zustand == "clear-night" or (zustand == "sunny" and nacht):
        _mond(b, cx, cy, s * 1.15, t, hg, mond)
    elif zustand == "sunny":
        _sonne(b, cx, cy, s, t, hg)
    elif zustand == "partlycloudy":
        if nacht:
            # Mond immer rechts oben hinter der Wolke; der Mittelpunkt der Mondscheibe bleibt
            # in jeder Phase derselbe, nur der helle Teil ändert sich
            _mond(b, cx + 0.27 * s, cy - 0.25 * s, s * 0.92, t, hg, mond)
            _wolke(b, cx - 0.08 * s, cy + 0.06 * s, s * 0.82, t, innen, hof=hg)
        else:
            _sonne(b, cx - 0.16 * s, cy - 0.14 * s, s * 0.78, t, hg)
            _wolke(b, cx + 0.06 * s, cy + 0.04 * s, s * 0.82, t, innen)
    elif zustand in ("rainy", "pouring", "hail", "snowy-rainy"):
        _wolke(b, cx, cy - 0.14 * s, s, t, innen)
        _tropfen(b, cx, cy + 0.28 * s, s, 4 if zustand == "pouring" else 3, t)
    elif zustand == "snowy":
        _wolke(b, cx, cy - 0.14 * s, s, t, innen)
        for i in (-1, 0, 1):
            b.kreis(cx + i * 0.22 * s, cy + 0.36 * s, t * 0.9)
    elif zustand in ("lightning", "lightning-rainy"):
        _wolke(b, cx, cy - 0.14 * s, s, t, innen)
        blitz = [(0.04, 0.18), (-0.10, 0.38), (0.00, 0.38), (-0.06, 0.56), (0.12, 0.30), (0.02, 0.30), (0.10, 0.18)]
        b.d.polygon([((cx + x * s) * S, (cy + y * s) * S) for x, y in blitz], fill=SCHWARZ)
    elif zustand == "fog":
        for i, breite in enumerate((0.34, 0.44, 0.30)):
            y = cy - 0.16 * s + i * 0.16 * s
            b.linie(cx - breite * s, y, cx + breite * s, y, dicke=t)
    else:  # cloudy, windy, exceptional, unbekannt
        _wolke(b, cx, cy - 0.06 * s, s, t, innen)


def akkusymbol(b, x, y, prozent, laedt):
    """Kleine Batterie, x/y = linke obere Ecke, 26x12 Pixel."""
    b.rechteck(x, y, x + 24, y + 12, farbe=WEISS, radius=2.5, rand=DUNKEL, dicke=1.5)
    b.rechteck(x + 24, y + 3.5, x + 26.5, y + 8.5, farbe=DUNKEL, radius=1)
    breite = max(0, min(100, prozent)) / 100 * 18
    if breite > 0.5:
        b.rechteck(x + 3, y + 3, x + 3 + breite, y + 9, farbe=DUNKEL, radius=0.8)
    if laedt:
        b.text(x - 4, y + 11, "+", 14, "fett", DUNKEL, anker="rs")


# ---------------------------------------------------------------- Bereiche

def kopf(b, d):
    jetzt = d["jetzt"]
    b.text(RAND - 2, 76, WOCHENTAGE[jetzt.weekday()], 54, "fett")
    b.text(RAND, 114, f"{jetzt.day}. {MONATE[jetzt.month - 1]}", 27, farbe=DUNKEL)
    b.text(BREITE - RAND, 44, f"Stand {jetzt:%H:%M}", 16, farbe=GRAU, anker="rs")
    if d.get("akku") is not None:
        b.text(BREITE - RAND - 34, 70, f"{d['akku']:.0f} %", 14, farbe=GRAU, anker="rs")
        akkusymbol(b, BREITE - RAND - 27, 58, d["akku"], d.get("laedt"))
    b.linie(RAND, 136, BREITE - RAND, 136, dicke=3)


def termine(b, d, y):
    """Heute (bis 3 Zeilen) und morgen (bis 2 Zeilen). Gibt die neue y-Position zurück."""
    # Die Spalte für die Uhrzeit richtet sich nach der breitesten Angabe ("09:00 – 18:00")
    uhr = schrift(23, "fett")
    zeiten = [zeit for liste in (d["heute"], d["morgen"]) for zeit, _ in liste or [] if zeit[0].isdigit()]
    spalte = max([88] + [round(uhr.getlength(zeit) / S) + 18 for zeit in zeiten])
    for ueberschrift, liste, platz in (("Heute", d["heute"], 3), ("Morgen", d["morgen"], 2)):
        b.titel(RAND, y + 26, ueberschrift)
        y += 26
        if not liste:
            leer = "Kalender nicht erreichbar" if liste is None else "Keine Termine"
            b.text(RAND, y + 34, leer, 22, farbe=GRAU)
            y += 38
            continue
        zeigen = liste if len(liste) <= platz else liste[:platz - 1]
        for zeit, was in zeigen:
            y += 37
            if zeit[0].isdigit():
                b.text(RAND, y, zeit, 23, "fett")
            else:  # "ganztägig", "bis 10:30"
                b.text(RAND, y - 2, zeit, 15, farbe=GRAU)
            b.text(RAND + spalte, y, was, 23, max_breite=BREITE - 2 * RAND - spalte)
        if len(liste) > platz:
            y += 37
            rest = len(liste) - len(zeigen)
            b.text(RAND + spalte, y, f"und {rest} weitere", 20, farbe=GRAU)
        y += 6
    return y + 12


def wetter(b, d, y):
    w = d["wetter"]
    b.linie(RAND, y, BREITE - RAND, y, farbe=HELL)
    # Links: jetzt
    wettersymbol(b, w["zustand"], RAND + 46, y + 62, 92, nacht=w.get("nacht"), mond=w.get("mond"))
    b.text(RAND + 108, y + 78, "–" if w["temp"] is None else f"{w['temp']:.0f}°", 58, "fett")
    b.text(RAND, y + 128, w["text"], 20, farbe=DUNKEL)
    if w.get("regen_heute") is not None:
        if w["regen_heute"] < 0.1:
            regen = "Heute kein Regen mehr"
        elif w.get("regen_ab"):
            regen = f"Regen ab {w['regen_ab']}, {zahl(w['regen_heute'])} mm"
        else:
            regen = f"Regen, heute noch {zahl(w['regen_heute'])} mm"
        b.text(RAND, y + 154, regen, 17, "fett")
    # Rechts: die nächsten Tage
    spalte = 68
    x0 = BREITE - RAND - 4 * spalte + spalte / 2
    for i, (tag, zustand, hoch, tief, regen) in enumerate(w["tage"][:4]):
        x = x0 + i * spalte
        b.text(x, y + 30, tag, 15, "fett", GRAU, anker="ms")
        wettersymbol(b, zustand, x, y + 58, 40)
        b.text(x, y + 106, f"{hoch:.0f}°", 21, "fett", anker="ms")
        b.text(x, y + 128, f"{tief:.0f}°", 16, farbe=GRAU, anker="ms")
        if regen >= 0.1:
            b.text(x, y + 154, f"{zahl(regen)} mm", 13, farbe=DUNKEL, anker="ms")
        else:
            b.text(x, y + 154, "–", 13, farbe=HELL, anker="ms")
    return y + 172


def raeume(b, d, y):
    b.linie(RAND, y, BREITE - RAND, y, farbe=HELL)
    spalten = 3
    breite = (BREITE - 2 * RAND) / spalten
    for i, (name, temp) in enumerate(d["raeume"][:6]):
        x = RAND + (i % spalten) * breite
        zy = y + 26 + (i // spalten) * 54
        b.text(x, zy, name, 14, farbe=GRAU, max_breite=breite - 10)
        if temp is None:
            b.text(x, zy + 29, "–", 25, "fett", GRAU)
        else:
            b.text(x, zy + 29, f"{zahl(temp)}°", 25, "fett")
    zeilen = math.ceil(min(len(d["raeume"]), 6) / spalten)
    return y + 20 + zeilen * 54


def fuss(b, d, y):
    b.linie(RAND, y, BREITE - RAND, y, farbe=HELL)
    # Links: Müllabfuhr
    b.titel(RAND, y + 24, "Müllabfuhr")
    zy = y + 24
    if not d["muell"]:
        b.text(RAND, zy + 26, "keine Daten", 18, farbe=GRAU)
    for wann, was in d["muell"][:2]:
        zy += 26
        breite = b.text(RAND, zy, wann, 18, "fett")
        b.text(RAND + breite + 8, zy, was, 18, max_breite=290 - breite)
    # Rechts: Pflanzen
    x = 372
    for name, feuchte, grenze in d["pflanzen"][:1]:
        b.titel(x, y + 24, name)
        trocken = feuchte is not None and feuchte < grenze
        if feuchte is None:
            b.text(x, y + 54, "–", 24, "fett", GRAU)
            continue
        b.text(x, y + 54, f"{feuchte:.0f} %", 24, "fett")
        # Balken mit Markierung an der Gieß-Grenze
        bx1, bx2, by = x + 78, BREITE - RAND, y + 40
        b.rechteck(bx1, by, bx2, by + 12, farbe=WEISS, radius=3, rand=DUNKEL, dicke=1.5)
        b.rechteck(bx1 + 3, by + 3, bx1 + 3 + (bx2 - bx1 - 6) * min(feuchte, 100) / 100, by + 9,
                   farbe=SCHWARZ, radius=1)
        gx = bx1 + 3 + (bx2 - bx1 - 6) * grenze / 100
        b.linie(gx, by - 4, gx, by + 16, dicke=1.5, farbe=GRAU)
        if trocken:
            b.text(x, y + 76, "Bitte gießen", 16, "fett")
        else:
            b.text(x, y + 76, f"gießen unter {grenze:.0f} %", 14, farbe=GRAU)


def zeichne(d):
    b = Blatt()
    kopf(b, d)
    y = termine(b, d, 140)
    y = wetter(b, d, max(y, 402))
    y = raeume(b, d, max(y, 580))
    fuss(b, d, max(y, 708))
    return b.fertig()


BEISPIEL = {
    "jetzt": datetime(2026, 11, 16, 18, 15),
    "akku": 77,
    "laedt": False,
    "heute": [("ganztägig", "Beispiel: Geburtstag Oma"), ("09:30", "Beispiel: Zahnarzt"),
              ("17:00", "Beispiel: Elternabend in der Schule, Raum 12")],
    "morgen": [("08:15", "Beispiel: Werkstatt, Auto abgeben"), ("19:30", "Beispiel: Sport")],
    "wetter": {
        "zustand": "rainy", "temp": 7, "text": "Regen", "regen_heute": 4.2,
        "tage": [("Di", "rainy", 12.4, 0.8, 3.1), ("Mi", "rainy", 10.4, 8.6, 6.4),
                 ("Do", "partlycloudy", 9.3, 7.3, 0.4), ("Fr", "sunny", 4.3, 1.9, 0.0)],
    },
    "raeume": [("Wohnzimmer", 19.6), ("Küche", 21.1), ("Arbeitszimmer", 20.8),
               ("Bad", 19.2), ("Kind", 20.3), ("Schlafen", 22.4)],
    "muell": [("Do, 19.11.", "Restmüll"), ("Mo, 23.11.", "Papier")],
    "pflanzen": [("Ficus", 30, 20)],
}

if __name__ == "__main__":
    ziel = sys.argv[1] if len(sys.argv) > 1 else "entwurf.png"
    zeichne(BEISPIEL).save(ziel)
    print("geschrieben:", ziel)
