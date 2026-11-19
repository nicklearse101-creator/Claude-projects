SETUP COACH - HOW TO USE
========================

Setup Coach is a Custom Shaders Patch (CSP) app for Assetto Corsa. It
watches how the car behaves while you drive (tyres, balance, suspension,
brakes), tells you what to change, and can write a new setup for you.


1. INSTALL
----------
Needs Custom Shaders Patch (CSP) installed.

Copy the "apps" folder from the zip into your Assetto Corsa folder, e.g.
  ...\steamapps\common\assettocorsa\
so the app ends up in
  ...\assettocorsa\apps\lua\setupcoach\
Say yes if Windows asks to replace files when you update.


2. OPENING IT
-------------
On track: open the app bar on the right of the screen and click
"Setup Coach". This is the full window.

On the setup screen: Setup Coach is also in the setup screen's own app
list (where Setup Exchange and the car info window are). It's a narrow
version with the tyres, the advice and the Build button. You can drag it
and resize it wherever you like.


3. THE QUICK WAY - LET IT BUILD A SETUP
---------------------------------------
1. Pick your tyres, fuel and gearing in the setup screen as normal.
   Setup Coach never changes those.
2. Sit still in the pits for a moment (it reads your static camber and
   ride height there).
3. Drive at least 2 clean laps at a proper pace (20+ corners). Laps
   through the pits or off track don't count.
4. Press BUILD OPTIMAL SETUP (on track or on the setup screen).
5. In the setup screen, load "SetupCoach_Optimized". It shows in the
   list straight away.
6. Drive 2 more clean laps, Build again, load again. Each Build makes
   small steps and checks whether the last change helped, so expect a
   few rounds.

Your own setups are never overwritten. Build only writes
SetupCoach_Optimized.ini in that car's setup folder for this track.

If Build says it needs more laps, keep driving. It won't build from a
couple of corners.


4. READING THE WINDOW (top to bottom)
-------------------------------------
Header       - car, compound, lap, last / best lap, speed, fuel, temps.

Tyre table   - for each corner: hot pressure against the target, tyre
               temps inside / middle / outside, and core temp against
               the tyre's best temp.
               Green = on target, yellow = close, orange = off.

This window  - what the app has seen since the last Build:
               - clean laps and corners, and whether Build is ready
               - low and high speed balance: push (understeer) and
                 oversteer per 100 corners, with the verdict
               - your balance target, turn-in push, lockups front/rear
               - suspension travel used, times it hit the end of travel,
                 and the damper bump / rebound split

WHAT TO CHANGE - only the things that want changing, most important
               first. Each one says what to do, e.g. "soften the front
               ARB 1-2 clicks".
               "Fine:" lists everything that's OK.
               "Still measuring:" lists things that need more driving.
               Tick "Show every check, with the reasoning" to see the
               lot.


5. SETTING UP THE CAR BY HAND
-----------------------------
You don't have to use Build. To do it yourself:
- Change ONE thing at a time, from the top of WHAT TO CHANGE.
- Drive 2 laps, see if it moved, then the next item.
- Use the tyre table for pressures (aim for green hot pressures) and
  camber (inside a bit hotter than outside is normal).


6. BALANCE TARGET (Normal / Oversteer / Understeer)
---------------------------------------------------
Tells the app how you like the car to feel. It changes when the app
calls the car "understeering" or "oversteering", and the brake bias.

Normal     - a little oversteer is fine (most race cars want this).
Oversteer  - you like a car that rotates: the app fixes push sooner and
             puts up with more oversteer. Brake bias a touch further
             back.
Understeer - you want a stable, safe car: the app fixes oversteer
             sooner and puts up with more push. Brake bias a touch
             further forward.


7. THE OTHER BUTTONS
--------------------
Which modules does Build write?
             Untick anything you're happy with (e.g. pressures, ARB).
             Build then leaves it exactly as it is. "All on" turns them
             all back on for a new car or track.
Re-arm brake-bias write
             Build sets brake bias ONCE per car from the braking data,
             then only advises. Press this to let it set it again.
OVERRIDE LAP GATE (test)
             Lets the next Build run without the 2 clean laps. For
             testing only - setups built this way are based on very
             little data.
RESET TELEMETRY
             Clears everything the app has seen this session. Use it
             when you change something big or swap track.
SAVE PIT NOTES / OPEN NOTES FOLDER
             Saves a text report. The notes and the debug log go to
             Documents\Assetto Corsa\SetupCoach_Notes.
SAVE GRIP BASELINE
             Saves your current grip and best lap for this car/track,
             so after a setup change it can tell you if it helped.


8. GOOD TO KNOW
---------------
- Gearing, tyre compound, fuel, TC and ABS are never changed by Build.
  Gearing advice (shorter / longer final drive) is shown only.
- Rally / gravel: the app treats sliding as a problem, so on loose
  surfaces it will try to stop slides you meant. A rally mode is
  planned.
- Something odd? Press SAVE PIT NOTES and send the SetupCoach_Notes
  folder (debug_log.txt) with what you saw.
