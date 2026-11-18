# Installation guide for coding agents

This file is written for a coding agent (Claude Code, Codex, Hermes Agent, pi, …). If you are a
human, hand it to your agent, or follow "Option B" in the [README](README.md).

You are helping a person set up **kindle-display**: a small server that draws a status page from
their Home Assistant data, and an old Kindle that fetches and shows that page. Work through the
phases in order. Each phase ends with a check; do not move on until it passes.

## Ground rules

- **Ask before you change anything** outside this repository's folder: Home Assistant
  configuration, running containers, firewall, the Kindle. Show what you intend to do first.
- **Secrets are entered by the person, not by you.** That means the Home Assistant token, the
  webhook ID and calendar links. Never print them, never put them into a file that is tracked by
  Git, never pass them on a command line that ends up in a shell history. Create the file, tell the
  person which line to fill in, and continue once they confirm.
- **Home Assistant access is read-only.** This project only reads states and calls the two
  read-only services `weather.get_forecasts` and `calendar.get_events`.
- **Back up before editing** any existing Home Assistant file, and restart Home Assistant only
  after the person agrees.
- **You cannot touch the Kindle.** Everything in phase 3 is done by the person. Give one small
  step at a time, say what they should see afterwards, and wait for their answer.
- Do not show the person's real appointments in logs or screenshots you produce for yourself.
  Counting them is enough to verify the calendar.
- Speak the person's language. The page itself is German; the texts live in `bild.py`, `bild2.py`
  and `daten.py` if they want another language.

## Phase 0: take stock

Find out, by looking where you can and asking where you cannot:

1. Which machine will run the server? It must be reachable from the Kindle over plain HTTP in the
   local network and needs Docker with Compose. Note its LAN address.
2. Where is Home Assistant, and at which URL can this machine reach it?
3. Which Kindle model and firmware version? (On the Kindle: Menu → Settings, the version is shown
   at the bottom or under Menu → Device Info.) The layout is drawn for **600×800 pixels**, the
   resolution of the Kindle 4. Other resolutions need changes to the layout code, see the end of
   this file.
4. Which data does the person want on the page? Weather, calendars, waste collection, up to two
   plant sensors and room temperatures are supported. Everything except weather is optional.

Summarise what you found and ask the open questions in one go.

## Phase 1: Home Assistant

1. Ask the person to create a Home Assistant user without admin rights (for example `kindle`),
   log in as that user and create a long-lived access token (profile → Security).
2. Battery level (optional, recommended). The Kindle reports its battery with every request and
   the server forwards it to a webhook. This needs two helpers and one automation; the YAML is in
   the README under "Battery level". The person chooses a long random webhook ID. If helpers are
   defined in YAML, Home Assistant must reload them (Developer tools → Actions →
   `input_number.reload` and `input_boolean.reload`).
3. Calendars (optional). Any `calendar.*` entity works. For public iCloud calendars, Home
   Assistant's Remote Calendar integration often fails with "not valid ICS"; in that case use the
   bundled filter (README, "iCloud calendars") and point Remote Calendar at
   `http://127.0.0.1:5001/<name>.ics`. This only works as written if the filter runs on the same
   machine as Home Assistant.
4. Waste collection (optional). The page reads a calendar entity whose event titles name the
   waste type. The HACS integration "Waste Collection Schedule" provides one for many
   municipalities; an imported ICS file in a Local Calendar works as well.

**Check:** with the token in place (phase 2, step 2), `GET <HA>/api/` answers
`{"message": "API running."}`.

## Phase 2: the server

1. Clone the repository on the server machine:

   ```sh
   git clone https://github.com/Josi-create/kindle-display.git && cd kindle-display
   ```

2. Create the secrets file and let the person fill it in:

   ```sh
   cp ha.env.beispiel ha.env && chmod 600 ha.env
   ```

   `HA_BASE_URL` is the address from phase 0, `HA_ACCESS_TOKEN` the token from phase 1,
   `HA_BATTERY_WEBHOOK` the webhook ID (leave empty to skip battery reporting).
3. Create the settings file: `cp einstellungen.beispiel.py einstellungen.py`. Then find the right
   entities. List candidates through the API (`GET /api/states`) and propose a mapping:
   - `WETTER`: a `weather.*` entity that supports daily and hourly forecasts.
   - `KALENDER`: the calendars to show. `MUELL`: the waste calendar. Adjust `MUELLNAMEN` so each
     pair is (word that occurs in the event title, short name to display).
   - `PFLANZEN`: up to two soil moisture sensors, each with a watering threshold in percent.
   - `RAEUME`: up to six rooms, each with one or more temperature sensors. The lowest reading per
     room is shown. Check that each sensor really is a measured temperature and not a target
     temperature of a thermostat.
   - `OPEN_METEO`: the chance of rain comes from open-meteo.com and sends the home location,
     rounded to about 1 km. Tell the person and set it to `False` if they do not want that.

   Anything the person does not have can stay as it is in the template; missing entities show up
   as "–" or "keine Daten" and do not break the page. Show the proposed file and get a yes.
4. Build and start:

   ```sh
   docker compose up -d --build kindle-anzeige
   ```

   The container runs as user 1000:1000 with a read-only file system. If port 5000 is taken,
   change the left side of `"5000:5000"` in `docker-compose.yml`.
5. If the machine has a firewall, the port must be open for the local network.

**Check:**

- `curl -s http://127.0.0.1:5000/health` prints `ok`.
- `curl -s -o test.png http://127.0.0.1:5000/` yields a 600×800 PNG. Look at the picture: weather,
  chart or rooms, appointments, waste and plant must be plausible. If it shows "Home Assistant ist
  nicht erreichbar", read `docker logs kindle-anzeige`; the log names what failed without
  revealing secrets.
- `curl -s -o /dev/null "http://127.0.0.1:5000/?batteryLevel=77&isCharging=0"` makes the battery
  helper in Home Assistant read 77.
- From another device in the network, `http://<server>:5000/` shows the picture.

## Phase 3: the Kindle

Say this to the person before you start, and continue only if they agree:

- Jailbreaking is done at their own risk on their own device. It can go wrong, and a Kindle that
  no longer boots is hard to recover.
- The Kindle becomes a display. Reading on it is still possible after stopping the dashboard, but
  this is best done with a device they no longer need for reading.
- A firmware update from Amazon can remove the jailbreak. Keep the device off Amazon's update
  path as the jailbreak guide for the model recommends.

### 3.1 Jailbreak

The method depends on model and firmware, and the guides change. **Do not rely on your memory.**
Look up the current instructions for the exact model and firmware and follow those:

- Kindle Modding Wiki: <https://kindlemodding.org/>
- MobileRead Kindle Developer's Corner: <https://www.mobileread.com/forums/forumdisplay.php?f=150>

Download files only from the sources those guides link to, and let the person do the download.

For orientation, this is how it went on the Kindle 4 (non-touch) this project was built on; the
guide for the device takes precedence wherever it differs:

1. Connect the Kindle by USB. It appears as a drive.
2. Unpack the Kindle 4 jailbreak package and copy its contents (`data.tar.gz`, `ENABLE_DIAGS` and
   the folder `diagnostic_logs`) to the top level of that drive. Eject it properly.
3. Restart the Kindle (Menu → Settings → Menu → Restart). It boots into a diagnostics menu; leave
   it through the menu's reboot entry as the guide describes. A jailbreak notice appears during
   the restart.
4. Keep the uninstaller file from the package in a safe place.

**Check:** the person confirms the jailbreak notice, or the installer in the next step works.

### 3.2 KUAL, MRPI and USBNetwork

Install, in this order and following the guide for the model:

1. **KUAL**, the launcher for extensions. The Kindle 4 needs its own build (`KUAL-KDK-1.0.azw2`,
   copied into `documents`), newer models use the regular one. It then appears as a book.
2. **MRPI** (MobileRead Package Installer), which installs the other packages.
3. **USBNetwork**, which provides SSH on the Kindle.

Then set up SSH access as the USBNetwork documentation describes (USB networking first, Wi-Fi
afterwards if the person wants it) and help the person set a password or install a key.

**Check:** `ssh root@<kindle>` from the person's computer gives a shell, and `ls /mnt/us` lists the
same files the USB drive shows.

### 3.3 kindle-dash

1. Download the latest release of [kindle-dash](https://github.com/pascalw/kindle-dash/releases)
   and unpack it on the computer.
2. Replace `local/fetch-dashboard.sh` and `local/env.sh` in the unpacked folder with the two
   files from this repository's `kindle/` folder.
3. In `fetch-dashboard.sh`, set `url` to `http://<server>:5000/`. Use plain HTTP and the IP
   address; the built-in `wget` of old Kindles cannot do modern HTTPS.
4. In `env.sh`, adjust `WIFI_TEST_IP` (the router's address), `TIMEZONE` and `REFRESH_SCHEDULE`.
   The default refreshes every 30 minutes between 6:00 and 22:30.
5. Copy everything to `/mnt/us/dashboard` on the Kindle, either over SSH
   (`rsync -vr ./ root@<kindle>:/mnt/us/dashboard`) or by USB into a folder `dashboard`. After a
   copy by USB, make the scripts executable over SSH: `chmod +x /mnt/us/dashboard/*.sh
   /mnt/us/dashboard/local/*.sh`.
6. Optional: copy the folder `KUAL/kindle-dash` from the kindle-dash sources to
   `/mnt/us/extensions` so the dashboard can be started from KUAL.
7. The Kindle must be in the Wi-Fi network and must not be in airplane mode.
8. Start it: `/mnt/us/dashboard/start.sh` over SSH, or from KUAL. The device suspends about 10 to
   15 seconds after the start; that is intended.

The battery commands in `fetch-dashboard.sh` (`gasgauge-info`, `kdb`) are those of the Kindle 4.
On another model, run them over SSH first. If they do not exist there, find that model's
equivalent or remove the two query parameters from the `wget` line.

**Check:**

- The Kindle shows the page.
- `docker logs --tail 5 kindle-anzeige` on the server shows a line like
  `GET /?batteryLevel=…&isCharging=… -> 200`.
- The battery helper in Home Assistant shows the Kindle's real level.

To stop the dashboard, see the kindle-dash README (`stop.sh`).

## Phase 4: hand over

Tell the person, briefly:

- where the files are and which two files hold their settings (`ha.env`, `einstellungen.py`);
- how to apply a change: after editing `einstellungen.py`, run
  `docker compose restart kindle-anzeige`; after editing code, run
  `docker compose up -d --build kindle-anzeige`;
- that the server answers with the last good picture for up to six hours if Home Assistant is
  down;
- how to stop everything: `docker compose down` on the server, `stop.sh` on the Kindle.

## Troubleshooting

| Symptom | Likely cause |
| --- | --- |
| Picture says "Home Assistant ist nicht erreichbar" | Wrong `HA_BASE_URL`, wrong token, or the container cannot reach Home Assistant. Test with `curl` from the server; as a last resort use `network_mode: host`. |
| "Kalender nicht erreichbar" | The calendar entity name is wrong or the token's user may not read it. |
| No chart, rooms shown instead | No rain expected in the next 24 hours, `OPEN_METEO = False`, or open-meteo.com is unreachable (see the log). |
| Kindle shows nothing new | Wi-Fi off, wrong address in `fetch-dashboard.sh`, firewall, or outside the refresh schedule. Check whether requests arrive in `docker logs kindle-anzeige`. |
| Battery stays empty in Home Assistant | Webhook ID differs between `ha.env` and the automation, or the helpers were not reloaded. |
| Ghost images on the screen | Lower `FULL_DISPLAY_REFRESH_RATE` in `env.sh`. |

## Other screen sizes

`BREITE` and `HOEHE` in `bild.py` set the picture size, but the layout in `bild2.py` uses fixed
pixel positions for 600×800. A Kindle with another resolution needs those positions reworked.
Agree on that with the person before starting; it is a design task, not a setting.
