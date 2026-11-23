-- Escort Mk2 DTM: own exhaust flames (CSP's built-in [EXHAUST_FLAMES] never fired for this car).
-- Side exits just behind the rear sill vents. Pops on lift-off, on the limiter and on upshifts.
-- TEST: hold the handbrake with the engine above 2000 rpm -> constant flames (proves the flames render at all).
local TIPS = { vec3(0.960, -0.030, -0.180), vec3(-0.960, -0.030, -0.180) }  -- model space (x left, y up, z forward)
local DIRS = { vec3(0.894, 0, -0.447), vec3(-0.894, 0, -0.447) }           -- out of the side, a bit rearward
local flames = ac.Particles.Flame({ color = rgbm(0.5, 0.5, 0.5, 0.5), size = 0.25, temperatureMultiplier = 1, flameIntensity = 2 })

local gasPeak, prevGear = 0, 0       -- highest throttle in the last ~0.3 s
local popTime = 0
local flicker, lit = 0, false

local function burst(len)
  if len > popTime then popTime = len end
end

local function emitAll()
  for i = 1, 2 do
    local p = car.bodyTransform:transformPoint(TIPS[i])
    local d = car.bodyTransform:transformVector(DIRS[i])
    flames:emit(p, car.velocity + d * (6 + math.random() * 6), 2)
  end
end

function script.update(dt)
  local lim = car.rpmLimiter > 0 and car.rpmLimiter or 8500
  gasPeak = math.max(car.gas, gasPeak - dt * 2.5)                        -- decays ~0.75 per 0.3 s
  -- lift-off: throttle was well open a moment ago, now shut, engine revving
  if gasPeak > 0.6 and car.gas < 0.2 and car.rpm > 4000 then burst(0.25 + math.random() * 0.45); gasPeak = 0 end
  -- upshift with the foot in
  if car.gear > prevGear and prevGear > 0 and gasPeak > 0.3 and car.rpm > 3000 then burst(0.12) end
  -- bouncing off the limiter
  if car.rpm > lim - 300 and car.gas > 0.5 and math.random() < 0.3 then burst(0.08) end
  prevGear = car.gear

  if car.handbrake > 0.5 and car.rpm > 2000 then emitAll() return end   -- test mode

  if popTime > 0 then
    popTime = popTime - dt
    flicker = flicker - dt
    if flicker <= 0 then
      flicker = 0.02 + math.random() * 0.05             -- crackle: on/off every few frames
      lit = math.random() < 0.75
    end
    if lit then emitAll() end
  end
end
