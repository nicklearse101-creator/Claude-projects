-- Escort Mk2 DTM: exhaust flames as meshes (v51). CSP particle flames never draw on this car, so the model carries
-- three flame lengths per side-exit (KK_flame_L1..3 / R1..3, glowing alpha texture); this script shows one at a time.
-- Pops on lift-off, upshifts with the foot in, and bouncing off the limiter.
-- (handbrake test mode removed after the flames were confirmed in game, 23 Nov)
-- 15in car (24 Nov): limiter flames turn GREEN when the revs are rising within 200 rpm of the limiter (shift light);
-- lift-off and upshift flames stay orange.
local root = ac.findNodes("carRoot:" .. car.index)
-- 25 Nov (Nik): one flame per cylinder - each of the 8 bonnet stacks has its own flame meshes KK_flame_<L|R><stack>_<len>
-- (stack 1..4 front to back, len 1..3), so pops come from single cylinders in Rover V8 firing order 1-8-4-3-6-5-7-2
-- (odd cylinders = left bank front to back, even = right bank), never a whole bank at once. Backfire sound removed
-- (Nik: it hid too much of the engine); back at half volume 22:10.
local FIRING = { 1, 8, 4, 3, 6, 5, 7, 2 }
local STACK = {}                                   -- cylinder -> { length meshes 1..3 }
local flameMeshes = {}
for cyl = 1, 8 do
  local side, st = cyl % 2 == 1 and "L" or "R", math.ceil(cyl / 2)
  STACK[cyl] = {}
  for k = 1, 3 do
    -- the flame dummies are inactive in the kn5 (hidden in CM's showroom, which runs no scripts); switch the dummy node
    STACK[cyl][k] = root:findNodes("KK_flame_" .. side .. st .. "_" .. k)
    local m = root:findMeshes("KK_flame_" .. side .. st .. "_" .. k)
    m:setMaterialProperty("ksEmissive", rgb(8, 8, 8)); flameMeshes[#flameMeshes + 1] = m
  end
end
local ORANGE, GREEN = rgb(8, 8, 8), rgb(0.15, 9, 1.2)    -- x the flame texture (hot orange) -> orange / bright green
local colour = "orange"
local function setColour(c)
  if c ~= colour then
    for _, m in ipairs(flameMeshes) do m:setMaterialProperty("ksEmissive", c == "green" and GREEN or ORANGE) end
    colour = c
  end
end
local BF_POS = vec3(0, 0.73, 1.31)                       -- between the bonnet stacks (car space)
-- backfire pops with the flames: the car's own soundbank events, a small pool so pops can overlap.
-- 25 Nov 22:10 (Nik): back in at HALF the old volume (was ext 1.8 / int 1.2)
local bfExt, bfInt, bfi, lastPop = {}, {}, 1, 0
for i = 1, 4 do
  bfExt[i] = ac.AudioEvent("cars/:own/backfire_ext", true)
  bfExt[i].volume = 0.9; bfExt[i].cameraInteriorMultiplier = 0; bfExt[i]:setPosition(BF_POS)
  bfInt[i] = ac.AudioEvent("cars/:own/backfire_int", true)
  bfInt[i].volume = 0.6; bfInt[i].cameraExteriorMultiplier = 0; bfInt[i].cameraTrackMultiplier = 0
  bfInt[i].cameraInteriorMultiplier = 1; bfInt[i]:setPosition(BF_POS)
end
-- doorless cockpit (24 Nov): the exterior engine sound also plays quietly in the cockpit, from the bonnet stacks,
-- so you hear the open exhaust directly as well as the soundbank's interior (closed-car) recording
local OPEN_VOL = 0.35                                  -- was 0.45 (Nik: cockpit engine a touch quieter)
local openExh = ac.AudioEvent("cars/:own/engine_ext", true)
openExh.cameraInteriorMultiplier = 1; openExh.cameraExteriorMultiplier = 0; openExh.cameraTrackMultiplier = 0
openExh.volume = OPEN_VOL
openExh:setPosition(BF_POS)

local clock = 0
local function pop()
  if clock - lastPop < 0.07 then return end
  lastPop = clock
  bfExt[bfi].pitch = 0.9 + math.random() * 0.25; bfExt[bfi]:start(); bfInt[bfi]:start()
  bfi = bfi % 4 + 1
end

-- doorless car: keep the door nodes hidden (their animations would otherwise bring them back in game)
local doors = root:findNodes("DOOR_L"):append(root:findNodes("DOOR_R"))
local function hideDoors() doors:setVisible(false) end
hideDoors()

local life, len, shownLen = {}, {}, {}          -- per cylinder: seconds left, flame length 1..3, length on screen (0 = none)
for c = 1, 8 do life[c], len[c], shownLen[c] = 0, 1, -1 end
local function show(c, k)
  if shownLen[c] == k then return end
  for j = 1, 3 do STACK[c][j]:setVisible(j == k) end
  shownLen[c] = k
end
for c = 1, 8 do show(c, 0) end

local gasPeak, prevGear, prevRpm = 0, 0, 0  -- highest throttle in the last ~0.3 s
local greenBurst = false
local popTime, nextFire, fi = 0, 0, 1
local frames, lit = 0, false

local function burst(t, green)
  if t > popTime then popTime = t; greenBurst = green or false end
end

function script.update(dt)
  frames = frames + 1
  clock = clock + dt
  if frames % 30 == 1 then hideDoors() end
  openExh:setParam("rpms", car.rpm); openExh:setParam("throttle", car.gas)
  openExh:resumeIf(car.rpm > 100)
  local lim = car.rpmLimiter > 0 and car.rpmLimiter or 8500
  gasPeak = math.max(car.gas, gasPeak - dt * 2.5)
  if gasPeak > 0.6 and car.gas < 0.2 and car.rpm > 4000 then burst(0.25 + math.random() * 0.45); gasPeak = 0 end
  if car.gear > prevGear and prevGear > 0 and gasPeak > 0.3 and car.rpm > 3000 then burst(0.12) end
  -- revs rising (or bouncing) within 200 rpm of the limiter with the throttle in: green "shift light" flames
  if car.rpm > lim - 200 and car.gas > 0.5 and (car.rpm >= prevRpm - 50) and math.random() < 0.35 then burst(0.08, true) end
  prevGear, prevRpm = car.gear, car.rpm
  setColour(greenBurst and (popTime > 0 or lit) and "green" or "orange")

  if popTime > 0 then
    popTime = math.max(popTime - dt, 0)
    nextFire = nextFire - dt
    while nextFire <= 0 do                            -- step through the firing order; some cylinders pop, most don't
      nextFire = nextFire + 0.02 + math.random() * 0.05
      local c = FIRING[fi]; fi = fi % 8 + 1
      if math.random() < (greenBurst and 0.6 or 0.45) then
        life[c] = 0.04 + math.random() * 0.08
        len[c] = greenBurst and math.random(1, 2) or math.random(1, 3)
        if math.random() < 0.7 then pop() end
      end
    end
  end
  lit = false
  for c = 1, 8 do
    if life[c] > 0 then
      lit = true
      life[c] = life[c] - dt
      if math.random() < 0.15 then len[c] = math.random(1, 3) end   -- a little flicker within one pop
    end
    show(c, life[c] > 0 and len[c] or 0)
  end
end
