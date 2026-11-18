"""Settings: which Home Assistant entities end up in the picture.

Copy this file to einstellungen.py and adjust it (the copy stays out of Git).
"""

WETTER = "weather.forecast_home"  # weather entity
OPEN_METEO = True  # fetch the chance of rain from open-meteo.com (home location rounded to about 1 km)

KALENDER = ["calendar.privat"]  # calendars; several are possible, their appointments are merged

# Calendar with the waste collection days, e.g. from the HACS integration "Waste Collection Schedule"
MUELL = "calendar.muellabfuhr"
MUELL_HEUTE_BIS = 12  # hour of day after which today's collection counts as done
# (word in the event title, short name in the picture)
MUELLNAMEN = [("Restabfall", "Restmüll"), ("Bio", "Bio"), ("Papier", "Papier"), ("Wertstoff", "Wertstoff")]

# Kindle battery: helpers in Home Assistant that the webhook fills (see README)
AKKU = "input_number.kindle_akku"
LAEDT = "input_boolean.kindle_ladevorgang"

# Plants: (name in the picture, soil moisture sensor, water below ... %) - the first two are shown
PFLANZEN = [("Ficus", "sensor.ficus_feuchtigkeit", 20), ("Yucca", "sensor.yucca_feuchtigkeit", 15)]

# Rooms: all temperature sensors per room; the LOWEST value is shown (no average). At most 6 rooms.
# The rooms only appear when no rain is expected for 24 hours - otherwise the chart takes their place.
RAEUME = [
    ("Wohnzimmer", ["sensor.wohnzimmer_temperatur", "sensor.wohnzimmer_heizung_temperatur"]),
    ("Küche", ["sensor.kueche_temperatur"]),
    ("Bad", ["sensor.bad_temperatur"]),
]
