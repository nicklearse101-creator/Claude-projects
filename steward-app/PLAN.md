# Steward app for Assetto Corsa: plan (2026-11-09)

**Goal:** a tool that helps a race steward at Ratty's Racing review incidents quickly and fairly.
- Find every contact during a race.
- Show what happened on a track map and in the game.
- Suggest who was mainly to blame. A human steward always decides.
- Record the decision and penalty.

**Status:** plan only, nothing built yet. Questions for Nik are at the end.

---

## 1. What we already have to build on

| Source | What it gives the steward app |
|---|---|
| **ac-physics-watchdog** (our Python tool, `C:\Users\nickl\Downloads\ac-physics-watchdog`) | Live connection to the race server's UDP plugin: car positions and speeds, laps, and collision events (car-to-car and car-to-wall, with impact speed and position). It also stores a capture per session (`captures/...`) and reads Server Manager results. Its connection code, capture format and replay-from-CSV code can be reused directly. |
| **Server Manager** on RATBOY's PC | Results JSON per session (laps, cuts, collisions list, penalties). It also has a web API, already used by the watchdog. |
| **AC replay files** (`.acreplay`, saved by the game on a driver's or spectator's PC) | Every car's full movement at 10–30 frames per second: position, rotation, speed, inputs, lights, damage. This is the best source for reviewing an incident. |
| **[Virtual Steward Mk V](https://github.com/Stripe76/VirtualStewardMkV)** (C#, GPL-3.0) and **[ACLibrary](https://github.com/Stripe76/ACLibrary)** (C#, no licence) | An existing replay-review app, used as a reference: replay file layout, track-map review, checkpoints, lap merge, and a fake AC server that plays a replay back into the game. **Learn from it, don't copy it.** GPL code would force our app to be GPL, and ACLibrary has no licence at all. |
| **Track data** in the AC install (`content/tracks/<track>/ai/fast_lane.ai`, `data/map.png` + `map.ini`) | The racing line and the official track map. They let us draw the track and say where on the lap each incident happened. |

## 2. What the app should do (by priority)

**Must have (version 1):**
1. **Incident list after a race:** every car-to-car contact from the watchdog capture or the Server Manager results.
   - Each contact shows the time, lap, both drivers, impact speed and where on the track it happened.
   - Small touches below a threshold, such as < 10 km/h relative speed, are grouped as "minor".
2. **Incident view:** a top-down track map showing both cars (plus anyone close) from 10 s before to 5 s after the contact.
   - Play, pause and scrub.
   - Speed and gap-to-car graphs.
   - The track edge and the racing line drawn underneath.
3. **Blame hints (advisory only):**
   - Which car was behind, and what the closing speed was.
   - Whether either car left its usual line or braked much later than on its other laps.
   - Whether one car rejoined the track unsafely.
   - Each hint is shown with its numbers, never as a verdict.
4. **Decision log:**
   - Per incident: no action, warning or time penalty, plus notes.
   - Saved to a file for the event.
   - Exported as a stewards' report (text or HTML) for posting.

**Should have (version 2):**
5. **Replay files:** load a driver's `.acreplay` for exact car orientation, inputs and damage. Line up its clock with the server capture.
6. **"Watch in game" button:** jump AC's own replay to the incident time. If that turns out to be too hard, give the exact replay time to seek to.
7. **Penalties in results:** apply decided time penalties to the Server Manager results (through its API, or a corrected results file) and show the new order.

**Could have (later):**
8. **Live mode during a race night:** flag incidents as they happen, so the steward can queue them up while racing continues.
9. **Replay through a fake server,** the Virtual Steward method: the game connects to our app, and we play the incident back in-game from any camera. It's powerful but means writing a big part of AC's network protocol. Only worth it if version 2 isn't enough.
10. **Driver reports:** drivers file a report (lap and time) from a simple web form; it lands in the incident list.

## 3. How it would be built

- **Language:** Python, the same as the watchdog, so the server connection and captures are shared.
- **Structure:** start as a module inside the watchdog repo (`steward/`). Split it out only if it grows.
- **Screen:** a local web page served by the app (Python standard library server and plain HTML, with a canvas for the map).
  - Nothing to install for a second steward on another PC; they open a link on the network.
  - It works on RATBOY's PC as well as Nik's.
- **Data flow:** capture or results, then the incident finder, then incident windows (positions resampled to a common clock), then the map view and blame hints, then the decision file, then the report.
- **Replay reader (version 2):** write our own Python reader for `.acreplay`. Use the published layout as a guide, check every field against real replays, and record what we learn in this folder.
- **Tests:** a set of real captured incidents with known outcomes, as the watchdog does. The blame hints must agree with stewards on clear-cut cases before they're shown.

## 4. Steps

| Step | What | Done when |
|---|---|---|
| 0 | **Look at real data:** pull the collisions out of a recent race-night capture and Server Manager result, and pull apart one `.acreplay` | We know the exact fields, time sync and accuracy of each source |
| 1 | **Incident finder + list page** | A past race night lists every contact with time, lap, drivers, impact speed and track position |
| 2 | **Track map + incident playback** | Any incident plays back on the map, with both cars and the track edge |
| 3 | **Blame hints** | Hints match the steward call on clear test incidents |
| 4 | **Decision log + report export** | A stewards' report for a race night can be produced in minutes |
| 5 | **Replay file support + "watch in game"** | Incidents can be checked against the driver's replay |
| 6 | **Penalties into results** | Corrected results produced from decisions |
| 7+ | Live mode, fake-server playback, driver reports | Decided after step 6 |

## 5. Risks and limits
- **Server update rate:** the server sends positions at about 10–20 updates per second, so a contact can fall between samples. Impact speed comes from the collision event itself; the replay file (step 5) gives finer detail.
- **Lag:** each driver's game sees the other cars slightly differently from the server. Hints must allow for ping, which the capture already records.
- **Blame:** no automatic rule is fair in every case. The app only shows evidence and suggestions, and the steward decides.
- **Replay files:** they are local to whoever recorded them and may be missing or cut short. Version 1 must work without them.
- **Licences:** Virtual Steward is GPL-3.0 and ACLibrary has no licence. We read them for understanding only and write our own code.

## 6. Questions for Nik
1. **Who will use it:** you, RATBOY or a steward team? On which PC?
2. **Penalties:** what does Ratty's Racing currently use (time penalties, warnings, points, grid drops)?
3. **Track limits:** should the steward app also handle track limits and corner cuts? The watchdog deliberately ignores these (it's physics-only), but they are normal steward business.
4. **Replays:** does anyone record replays on race nights, and would drivers send theirs in?
5. **Reports:** where should the stewards' report go: Discord, the league website, or a file?
