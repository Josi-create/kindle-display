#!/usr/bin/env python3
"""Zweiter Entwurf für die Kindle-Anzeige: Wetter groß, schwarze Balken, Kacheln.

Nutzt Blatt und die Symbole aus bild.py und dieselben Daten (daten.sammeln()).
Aufruf zum Ausprobieren:  python bild2.py entwurf2.png  (Beispieldaten)
"""
import sys
from datetime import datetime

from bild import (BEISPIEL, BREITE, DUNKEL, GRAU, HELL, HOEHE, MONATE, RAND, SCHWARZ, WEISS,
                  WOCHENTAGE, Blatt, S, schrift, wettersymbol, zahl)

KACHEL = 228  # helles Grau für Kacheln
LUECKE = 8
VERLAUF_AB = 5  # Prozent Regenwahrscheinlichkeit, ab denen das Diagramm gezeigt wird


def pille(b, x, y, s):
    """Überschrift weiß auf schwarzer Pille, dahinter eine Linie bis zum Rand."""
    f = schrift(13, "fett")
    breite = sum(f.getlength(z) / S + 2.2 for z in s.upper()) + 20
    b.rechteck(x, y, x + breite, y + 22, radius=11)
    b.titel(x + 11, y + 16, s, WEISS)
    b.linie(x + breite + 8, y + 11, BREITE - RAND, y + 11, dicke=1.5, farbe=HELL)


def akku_hell(b, x, y, prozent, laedt):
    """Batterie für den schwarzen Balken, x/y = linke obere Ecke."""
    b.rechteck(x, y, x + 24, y + 12, farbe=SCHWARZ, radius=2.5, rand=WEISS, dicke=1.5)
    b.rechteck(x + 24, y + 3.5, x + 26.5, y + 8.5, farbe=WEISS, radius=1)
    breite = max(0, min(100, prozent)) / 100 * 18
    if breite > 0.5:
        b.rechteck(x + 3, y + 3, x + 3 + breite, y + 9, farbe=WEISS, radius=0.8)
    if laedt:
        b.text(x - 4, y + 11, "+", 14, "fett", WEISS, anker="rs")


# ---------------------------------------------------------------- Bereiche

def kopf(b, d):
    """Schwarzer Balken mit Kalenderblatt, Wochentag und Monat. Höhe 88."""
    jetzt = d["jetzt"]
    b.rechteck(0, 0, BREITE, 88)
    b.rechteck(RAND, 13, RAND + 62, 75, farbe=WEISS, radius=9)
    b.text(RAND + 31, 59, str(jetzt.day), 40, "fett", anker="ms")
    b.text(RAND + 78, 47, WOCHENTAGE[jetzt.weekday()], 38, "fett", WEISS)
    b.text(RAND + 79, 73, f"{MONATE[jetzt.month - 1]} {jetzt.year}", 19, farbe=HELL)
    b.text(BREITE - RAND, 36, f"Stand {jetzt:%H:%M}", 15, farbe=HELL, anker="rs")
    if d.get("akku") is not None:
        b.text(BREITE - RAND - 34, 68, f"{d['akku']:.0f} %", 14, farbe=HELL, anker="rs")
        akku_hell(b, BREITE - RAND - 27, 56, d["akku"], d.get("laedt"))
    return 88


def wetter(b, d, y):
    w = d["wetter"]
    # Groß: jetzt
    wettersymbol(b, w["zustand"], RAND + 66, y + 78, 124, nacht=w.get("nacht"), innen=KACHEL, mond=w.get("mond"))
    x = RAND + 146
    temp = "–" if w["temp"] is None else f"{w['temp']:.0f}°"
    ende = x + b.text(x, y + 88, temp, 82, "fett")
    b.text(x + 4, y + 118, w["text"], 23, "fett", DUNKEL, max_breite=BREITE - RAND - x)
    zeigen = verlauf_noetig(w)
    if not zeigen and regentext(w):  # sonst steht das über dem Diagramm
        b.text(x + 4, y + 144, regentext(w), 17, farbe=GRAU)
    # Rechts oben: Wind und Luftfeuchte, wenn daneben Platz ist
    extras = []
    if w.get("wind") is not None:
        extras.append(("Wind", f"{w['wind']:.0f} {w.get('wind_einheit', '')}".strip()))
    if w.get("feuchte") is not None:
        extras.append(("Feuchte", f"{w['feuchte']:.0f} %"))
    if ende < BREITE - RAND - 110:
        for i, (name, wert) in enumerate(extras):
            b.text(BREITE - RAND, y + 32 + i * 42, name.upper(), 11, "fett", GRAU, anker="rs")
            b.text(BREITE - RAND, y + 53 + i * 42, wert, 19, "fett", anker="rs")
    # Darunter das Diagramm - bleibt es trocken, stattdessen die Zimmer
    y = verlauf(b, w, y + 138) if zeigen else raeume(b, d, y + 160)
    # Darunter: die nächsten vier Tage als Kacheln
    y += 10
    breite = (BREITE - 2 * RAND - 3 * LUECKE) / 4
    for i, (tag, zustand, hoch, tief, regen) in enumerate(w["tage"][:4]):
        kx = RAND + i * (breite + LUECKE)
        b.rechteck(kx, y, kx + breite, y + 78, farbe=KACHEL, radius=10)
        b.text(kx + 12, y + 23, tag, 17, "fett")
        wettersymbol(b, zustand, kx + 32, y + 50, 44, hg=KACHEL)
        b.text(kx + breite - 11, y + 36, f"{hoch:.0f}°", 25, "fett", anker="rs")
        b.text(kx + breite - 11, y + 55, f"{tief:.0f}°", 16, farbe=DUNKEL, anker="rs")
        if regen >= 0.1:
            b.text(kx + breite - 11, y + 71, f"{zahl(regen)} mm", 12, "fett", DUNKEL, anker="rs")
    return y + 78


def regentext(w):
    if w.get("regen_heute") is None:
        return None
    if w["regen_heute"] < 0.1:
        return "Heute kein Regen mehr"
    if w.get("regen_ab"):
        return f"Regen ab {w['regen_ab']} · {zahl(w['regen_heute'])} mm"
    return f"Heute noch {zahl(w['regen_heute'])} mm Regen"


def verlauf_noetig(w):
    """Das Diagramm lohnt sich nur, wenn in den nächsten 24 Stunden überhaupt Regen droht."""
    return any((risiko or 0) >= VERLAUF_AB for _, _, risiko in w.get("stunden") or [])


def raeume(b, d, y):
    """Eine Reihe Kacheln, Höhe 58."""
    anzahl = min(len(d["raeume"]), 6)
    breite = (BREITE - 2 * RAND - (anzahl - 1) * 4) / max(anzahl, 1)
    for i, (name, temp) in enumerate(d["raeume"][:6]):
        kx = RAND + i * (breite + 4)
        b.rechteck(kx, y, kx + breite, y + 58, farbe=KACHEL, radius=8)
        b.text(kx + breite / 2, y + 19, name, 11.5, farbe=DUNKEL, anker="ms", max_breite=breite - 2)
        b.text(kx + breite / 2, y + 46, "–" if temp is None else f"{zahl(temp)}°", 21, "fett", anker="ms")
    return y + 58


def verlauf(b, w, y):
    """Die nächsten 24 Stunden: Regenwahrscheinlichkeit als Balken, darüber die Temperatur. Höhe 104."""
    pille(b, RAND, y, regentext(w) or "Regenwahrscheinlichkeit")
    stunden = w.get("stunden") or []
    x0, oben, unten = RAND + 40, y + 48, y + 86
    breite = (BREITE - RAND - x0) / 24
    for anteil, name in ((1, "100 %"), (0.5, "50 %")):
        ly = unten - anteil * (unten - oben)
        b.linie(x0, ly, BREITE - RAND, ly, farbe=HELL)
        b.text(x0 - 7, ly + 4, name, 10, farbe=GRAU, anker="rs")
    if not any(risiko is not None for _, _, risiko in stunden):
        b.text((x0 + BREITE - RAND) / 2, unten - 13, "keine Daten", 15, farbe=GRAU, anker="ms")
    for i, (zeit, temp, risiko) in enumerate(stunden[:24]):
        x = x0 + i * breite
        if risiko:
            b.rechteck(x + 1, unten - risiko / 100 * (unten - oben), x + breite - 1, unten, farbe=DUNKEL)
        if zeit.hour % 3:
            continue
        if zeit.hour == 0 and i:  # Tageswechsel
            b.linie(x, oben, x, unten, dicke=1.5, farbe=GRAU)
        b.linie(x, unten, x, unten + 4, dicke=1.5)
        if temp is not None:
            b.text(x, y + 39, f"{temp:.0f}°", 13, "fett", anker="ms")
        if zeit.hour:
            b.text(x, y + 102, f"{zeit.hour} Uhr", 12, farbe=DUNKEL, anker="ms")
        else:
            b.text(x, y + 102, WOCHENTAGE[zeit.weekday()][:2], 12, "fett", anker="ms")
    b.linie(x0, unten, BREITE - RAND, unten, dicke=1.5)
    return y + 104


def termine(b, d, y, unten):
    """Heute hat immer Vorrang; morgen und die Tage danach bekommen, was bis `unten` übrig bleibt."""
    uhr = schrift(21, "fett")
    tage = [("Heute", d["heute"]), ("Morgen", d["morgen"])]
    tage += [(WOCHENTAGE[tag.weekday()], liste) for tag, liste in d.get("weitere", [])]
    zeiten = [zeit for _, liste in tage for zeit, _ in liste or [] if zeit[0].isdigit()]
    spalte = max([84] + [round(uhr.getlength(zeit) / S) + 16 for zeit in zeiten])
    for ueberschrift, liste in tage:
        platz = int((unten - y - 24) // 32)  # Zeilen unter der Überschrift
        if platz < 1:
            break
        pille(b, RAND, y, ueberschrift)
        y += 24
        if not liste:
            leer = "Kalender nicht erreichbar" if liste is None else "Keine Termine"
            b.text(RAND + 4, y + 28, leer, 20, farbe=GRAU)
            y += 32 + 16
            continue
        for nr, (zeit, was) in enumerate(liste[:platz], 1):
            y += 32
            mehr = nr == platz < len(liste)  # letzte Zeile, aber es gibt noch weitere Termine
            if zeit[0].isdigit():
                b.text(RAND + 4, y, zeit, 21, "fett")
            else:  # "ganztägig", "bis 10:30"
                b.text(RAND + 4, y - 2, zeit, 14, farbe=GRAU)
            b.text(RAND + 4 + spalte, y, was, 21, max_breite=BREITE - 2 * RAND - spalte - 4 - 34 * mehr)
            if mehr:
                b.text(BREITE - RAND, y, "…", 21, "fett", GRAU, anker="rs")
        y += 16
    return y


def fuss(b, d, y):
    """Schwarzer Balken bis zum unteren Rand: Müllabfuhr und Pflanzen."""
    b.rechteck(0, y, BREITE, HOEHE)
    b.titel(RAND, y + 21, "Müllabfuhr", HELL)
    zy = y + 22
    if not d["muell"]:
        b.text(RAND, zy + 22, "keine Daten", 16, farbe=HELL)
    for wann, was in d["muell"][:2]:
        zy += 21
        breite = b.text(RAND, zy, wann, 16, "fett", WEISS)
        b.text(RAND + breite + 8, zy, was, 16, farbe=WEISS, max_breite=300 - breite)
    # Rechts: bis zu zwei Pflanzen, je eine Zeile mit Balken und Markierung an der Gieß-Grenze
    x = 372
    b.titel(x, y + 21, "Pflanzen", HELL)
    for i, (name, feuchte, grenze) in enumerate(d["pflanzen"][:2]):
        zy = y + 43 + i * 21
        b.text(x, zy, name, 16, "fett", WEISS, max_breite=58)
        if feuchte is None:
            b.text(x + 106, zy, "–", 16, farbe=HELL, anker="rs")
            continue
        b.text(x + 106, zy, f"{feuchte:.0f} %", 16, farbe=WEISS, anker="rs")
        if feuchte < grenze:
            b.text(BREITE - RAND, zy, "gießen!", 16, "fett", WEISS, anker="rs")
            continue
        bx1, bx2, by = x + 116, BREITE - RAND, zy - 11
        b.rechteck(bx1, by, bx2, by + 11, farbe=SCHWARZ, radius=3, rand=WEISS, dicke=1.5)
        b.rechteck(bx1 + 3, by + 3, bx1 + 3 + (bx2 - bx1 - 6) * min(feuchte, 100) / 100, by + 8,
                   farbe=WEISS, radius=1)
        gx = bx1 + 3 + (bx2 - bx1 - 6) * grenze / 100
        b.linie(gx, by - 3, gx, by + 14, dicke=1.5, farbe=HELL)


def zeichne(d):
    b = Blatt()
    y = kopf(b, d)
    y = wetter(b, d, y)
    termine(b, d, y + 12, 720)
    fuss(b, d, 724)
    return b.fertig()


if __name__ == "__main__":
    ziel = sys.argv[1] if len(sys.argv) > 1 else "entwurf2.png"
    beispiel = dict(BEISPIEL, wetter=dict(BEISPIEL["wetter"], zustand="partlycloudy", text="Leicht bewölkt",
                                          nacht=True, wind=14, wind_einheit="km/h", feuchte=82,
                                          regen_ab="20 Uhr",
                                          stunden=[(datetime(2026, 11, 16 + (18 + i) // 24, (18 + i) % 24),
                                                    7 - i / 4, max(0, 95 - abs(i - 5) * 14) or None if i < 20 else 30)
                                                   for i in range(24)]))
    zeichne(beispiel).save(ziel)
    print("geschrieben:", ziel)
