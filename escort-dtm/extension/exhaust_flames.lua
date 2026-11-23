-- Escort Mk2 DTM: own exhaust flames (CSP's built-in [EXHAUST_FLAMES] never fired for this car).
-- Side exits just behind the rear sill vents. Pops on lift-off, on the limiter and on upshifts.
local TIPS = { vec3(0.960, -0.030, -0.180), vec3(-0.960, -0.030, -0.180) }  -- model space (x left, y up, z forward)
local DIRS = { vec3(0.894, 0, -0.447), vec3(-0.894, 0, -0.447) }           -- out of the side, a bit rearward
local flames = ac.Particles.Flame({ color = rgbm(0.5, 0.5, 0.5, 0.5), size = 0.22, temperatureMultiplier = 1, flameIntensity = 1.5 })

local prevGas, prevGear = 0, 0
local popTime, popLen = 0, 0      -- active burst: time left
local flicker, lit = 0, false

local function burst(len)
  if len > popTime then popTime, popLen = len, len end
end

function script.update(dt)
  local lim = car.rpmLimiter > 0 and car.rpmLimiter or 8500
  -- lift-off: throttle snapped shut from high revs
  if prevGas > 0.5 and car.gas < 0.15 and car.rpm > 4000 then burst(0.25 + math.random() * 0.45) end
  -- upshift with the foot in
  if car.gear > prevGear and prevGear > 0 and prevGas > 0.3 and car.rpm > 3000 then burst(0.12) end
  -- bouncing off the limiter
  if car.rpm > lim - 200 and car.gas > 0.5 and math.random() < 0.25 then burst(0.08) end
  prevGas, prevGear = car.gas, car.gear

  if popTime > 0 then
    popTime = popTime - dt
    flicker = flicker - dt
    if flicker <= 0 then
      flicker = 0.02 + math.random() * 0.05             -- crackle: on/off every few frames
      lit = math.random() < 0.75
    end
    if lit then
      for i = 1, 2 do
        if math.random() < 0.9 then
          local p = car.bodyTransform:transformPoint(TIPS[i])
          local d = car.bodyTransform:transformVector(DIRS[i])
          flames:emit(p, car.velocity + d * (6 + math.random() * 6), 0.6 + math.random() * 0.4)
        end
      end
    end
  end
end
