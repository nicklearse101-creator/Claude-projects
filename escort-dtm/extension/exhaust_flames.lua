-- Escort Mk2 DTM: exhaust flames as meshes (v51). CSP particle flames never draw on this car, so the model carries
-- three flame lengths per side-exit (KK_flame_L1..3 / R1..3, glowing alpha texture); this script shows one at a time.
-- Pops on lift-off, upshifts with the foot in, and bouncing off the limiter.
-- (handbrake test mode removed after the flames were confirmed in game, 23 Nov)
local root = ac.findNodes("carRoot:" .. car.index)
local F = { L = {}, R = {} }
for _, s in ipairs({ "L", "R" }) do
  for k = 1, 3 do
    F[s][k] = root:findMeshes("KK_flame_" .. s .. k)
    F[s][k]:setMaterialProperty("ksEmissive", rgb(8, 8, 8))     -- glow (the kn5 value landed in the wrong slot)
  end
end
local function hideAll()
  for _, s in ipairs({ "L", "R" }) do for k = 1, 3 do F[s][k]:setVisible(false) end end
end
hideAll()

local gasPeak, prevGear = 0, 0       -- highest throttle in the last ~0.3 s
local popTime, flicker = 0, 0
local frames, shown = 0, 0      -- (counters kept for debugging)

local function burst(len)
  if len > popTime then popTime = len end
end

local function flick(big)
  hideAll()
  for _, s in ipairs({ "L", "R" }) do
    if math.random() < 0.85 then
      local k = big and math.random(2, 3) or math.random(1, 3)
      F[s][k]:setVisible(true); shown = shown + 1
    end
  end
end

function script.update(dt)
  frames = frames + 1
  local lim = car.rpmLimiter > 0 and car.rpmLimiter or 8500
  gasPeak = math.max(car.gas, gasPeak - dt * 2.5)
  if gasPeak > 0.6 and car.gas < 0.2 and car.rpm > 4000 then burst(0.25 + math.random() * 0.45); gasPeak = 0 end
  if car.gear > prevGear and prevGear > 0 and gasPeak > 0.3 and car.rpm > 3000 then burst(0.12) end
  if car.rpm > lim - 300 and car.gas > 0.5 and math.random() < 0.3 then burst(0.08) end
  prevGear = car.gear

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
