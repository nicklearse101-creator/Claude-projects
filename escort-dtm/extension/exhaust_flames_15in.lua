-- Escort Mk2 DTM: exhaust flames as meshes (v51). CSP particle flames never draw on this car, so the model carries
-- three flame lengths per side-exit (KK_flame_L1..3 / R1..3, glowing alpha texture); this script shows one at a time.
-- Pops on lift-off, upshifts with the foot in, and bouncing off the limiter.
-- (handbrake test mode removed after the flames were confirmed in game, 23 Nov)
-- 15in car (24 Nov): limiter flames turn GREEN when the revs are rising within 200 rpm of the limiter (shift light);
-- lift-off and upshift flames stay orange.
local root = ac.findNodes("carRoot:" .. car.index)
local F = { L = {}, R = {} }
for _, s in ipairs({ "L", "R" }) do
  for k = 1, 3 do
    -- the flame dummies are inactive in the kn5 (hidden in CM's showroom, which runs no scripts); switch the dummy node
    F[s][k] = root:findNodes("KK_flame_" .. s .. k)
    root:findMeshes("KK_flame_" .. s .. k):setMaterialProperty("ksEmissive", rgb(8, 8, 8))
  end
end
local ORANGE, GREEN = rgb(8, 8, 8), rgb(0.15, 9, 1.2)    -- x the flame texture (hot orange) -> orange / bright green
local flameMeshes = {}
for _, s in ipairs({ "L", "R" }) do for k = 1, 3 do flameMeshes[#flameMeshes + 1] = root:findMeshes("KK_flame_" .. s .. k) end end
local colour = "orange"
local function setColour(c)
  if c ~= colour then
    for _, m in ipairs(flameMeshes) do m:setMaterialProperty("ksEmissive", c == "green" and GREEN or ORANGE) end
    colour = c
  end
end
-- loud backfire pops with the flames: the car's own soundbank events, a small pool so pops can overlap
local BF_POS = vec3(0, 0.75, 1.15)                       -- between the bonnet stacks (car space)
local bfExt, bfInt, bfi, lastPop = {}, {}, 1, 0
for i = 1, 4 do
  bfExt[i] = ac.AudioEvent("cars/:own/backfire_ext", true)
  bfExt[i].volume = 1.8; bfExt[i].cameraInteriorMultiplier = 0; bfExt[i]:setPosition(BF_POS)
  bfInt[i] = ac.AudioEvent("cars/:own/backfire_int", true)
  bfInt[i].volume = 1.2; bfInt[i].cameraExteriorMultiplier = 0; bfInt[i].cameraTrackMultiplier = 0
  bfInt[i].cameraInteriorMultiplier = 1; bfInt[i]:setPosition(BF_POS)
end
-- doorless cockpit (24 Nov): the exterior engine sound also plays quietly in the cockpit, from the bonnet stacks,
-- so you hear the open exhaust directly as well as the soundbank's interior (closed-car) recording
local OPEN_VOL = 0.45
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

local function hideAll()
  for _, s in ipairs({ "L", "R" }) do for k = 1, 3 do F[s][k]:setVisible(false) end end
end
hideAll()

local gasPeak, prevGear, prevRpm = 0, 0, 0  -- highest throttle in the last ~0.3 s
local greenBurst = false
local popTime, flicker = 0, 0
local frames, shown = 0, 0      -- (counters kept for debugging)

local function burst(len, green)
  if len > popTime then popTime = len; greenBurst = green or false end
end

local function flick(big)
  hideAll()
  for _, s in ipairs({ "L", "R" }) do
    if math.random() < 0.85 then
      local k = big and math.random(2, 3) or math.random(1, 3)
      F[s][k]:setVisible(true); shown = shown + 1
    end
  end
  if math.random() < 0.7 then pop() end
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
  setColour(greenBurst and popTime > 0 and "green" or "orange")

  local test = false                                -- (was the handbrake test)
  if popTime > 0 or test then
    popTime = math.max(popTime - dt, 0)
    flicker = flicker - dt
    if flicker <= 0 then
      flicker = 0.03 + math.random() * 0.05            -- crackle: new flame shape every few frames
      if math.random() < 0.8 then flick(test) else hideAll() end
    end
  elseif flicker ~= -1 then
    hideAll(); flicker = -1
  end
end
