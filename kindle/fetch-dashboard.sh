#!/usr/bin/env sh
# kindle-dash: holt das Bild vom Server und meldet dabei Akkustand und Ladezustand
# (der Server gibt sie an Home Assistant weiter).
# Aufruf durch dash.sh: fetch-dashboard.sh <Zieldatei>
# Ersetzt /mnt/us/dashboard/local/fetch-dashboard.sh auf dem Kindle.
# Nutzt das eingebaute wget über einfaches HTTP.

ziel="$1"
url="http://192.168.0.10:5000/"  # Adresse des Servers eintragen

akku=$(gasgauge-info -s | sed 's/.$//')
ladedatei=$(kdb get system/driver/charger/SYS_CHARGING_FILE 2>/dev/null)
laedt=$(cat "$ladedatei" 2>/dev/null || echo 0)

if wget -q -O "$ziel.tmp" "${url}?batteryLevel=${akku}&isCharging=${laedt}"; then
  mv "$ziel.tmp" "$ziel"
else
  rm -f "$ziel.tmp"
  exit 1
fi
