#!/usr/bin/env sh
# kindle-dash: Einstellungen. Ersetzt /mnt/us/dashboard/local/env.sh auf dem Kindle.

# Zum WLAN-Test anpingen: der eigene Router
export WIFI_TEST_IP=${WIFI_TEST_IP:-192.168.0.1}

# Täglich 6:00 bis 22:30 alle 30 Minuten (Minute Stunde Tag Monat Wochentag).
# Außerhalb davon zeigt der Kindle das Schlafbild.
export REFRESH_SCHEDULE=${REFRESH_SCHEDULE:-"0,30 6-22 * * *"}
export TIMEZONE=${TIMEZONE:-"Europe/Berlin"}

# Nach 4 Teil-Aktualisierungen einmal komplett neu zeichnen (gegen Geisterbilder)
export FULL_DISPLAY_REFRESH_RATE=${FULL_DISPLAY_REFRESH_RATE:-4}

# Liegt die nächste Aktualisierung mindestens so viele Sekunden entfernt: Schlafbild
export SLEEP_SCREEN_INTERVAL=3600

# Akkumeldung läuft über den Server und Home Assistant, nicht über kindle-dash
export LOW_BATTERY_REPORTING=${LOW_BATTERY_REPORTING:-false}
export LOW_BATTERY_THRESHOLD_PERCENT=10
