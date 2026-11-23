-- Escort Mk2 DTM: 1980s-style VFD instrument cluster (replaces the analogue dials). 1200 x 400 canvas.
-- Rev bar graph (green / amber / red), big mph and gear, fuel bar, indicator and main-beam arrows, lap time.
local ON   = rgbm(0.20, 0.95, 0.63, 1)     -- lit VFD green
local DIM  = rgbm(0.07, 0.23, 0.17, 1)     -- unlit segment ghost
local AMB  = rgbm(1.00, 0.69, 0.18, 1)
local RED  = rgbm(1.00, 0.25, 0.18, 1)
local BG   = rgbm(0.02, 0.07, 0.06, 1)
local BLUE = rgbm(0.30, 0.65, 1.00, 1)
local SEGS, X0, X1 = 34, 50, 1150
local screen = ac.findNodes("carRoot:" .. car.index):findMeshes("VFD_SCREEN"):ensureUniqueMaterials()
screen:setMaterialProperty("ksEmissive", rgb(1.4, 1.4, 1.4))
local blink = 0

local function txt(s, size, x, y, col)
  ui.dwriteDrawText(s, size, vec2(x, y), col)
end

function update(dt)
  blink = (blink + dt) % 0.8
  ui.drawRectFilled(vec2(0, 0), vec2(1200, 400), BG)
  ui.pushDWriteFont("Consolas;Weight=Bold")
  -- rev bar graph
  local lim = car.rpmLimiter > 0 and car.rpmLimiter or 8500
  local lit = math.floor(SEGS * math.min(car.rpm / lim, 1) + 0.5)
  local w = (X1 - X0) / SEGS
  for i = 1, SEGS do
    local col = DIM
    if i <= lit then col = (i > SEGS - 3) and RED or ((i > SEGS - 7) and AMB or ON) end
    local x = X0 + (i - 1) * w
    ui.drawRectFilled(vec2(x + 3, 40), vec2(x + w - 3, 130), col)
  end
  for k = 0, math.floor(lim / 1000) do
    txt(tostring(k), 26, X0 + (X1 - X0) * k * 1000 / lim - 6, 136, DIM.r > 0 and rgbm(0.13, 0.48, 0.34, 1) or ON)
  end
  txt("x1000 RPM", 22, X1 - 130, 8, rgbm(0.13, 0.48, 0.34, 1))
  -- speed
  txt(string.format("%3d", math.floor(car.speedKmh * 0.621371 + 0.5)), 150, 60, 190, ON)
  txt("MPH", 30, 70, 352, rgbm(0.13, 0.48, 0.34, 1))
  -- gear
  local g = car.gear
  local gs = g < 0 and "R" or (g == 0 and "N" or tostring(g))
  txt(gs, 170, 520, 175, (car.rpm > lim * 0.93) and RED or ON)
  txt("GEAR", 30, 528, 352, rgbm(0.13, 0.48, 0.34, 1))
  -- fuel
  local f = car.maxFuel > 0 and math.min(car.fuel / car.maxFuel, 1) or 0
  txt("FUEL", 30, 770, 200, ON)
  ui.drawRectFilled(vec2(770, 245), vec2(1150, 275), DIM)
  ui.drawRectFilled(vec2(770, 245), vec2(770 + 380 * f, 275), f < 0.15 and AMB or ON)
  txt(string.format("%3d L", math.floor(car.fuel + 0.5)), 30, 1050, 200, ON)
  -- lap time
  local t = car.lapTimeMs / 1000
  txt(string.format("LAP %d:%05.2f", math.floor(t / 60), t % 60), 34, 770, 300, ON)
  -- indicators and main beam
  local on = blink < 0.4
  txt("<", 60, 680, 170, (car.turningLeftLights and on) and ON or DIM)
  txt(">", 60, 1110, 170, (car.turningRightLights and on) and ON or DIM)
  txt("MAIN", 26, 680, 255, (car.headlightsActive and not car.lowBeams) and BLUE or DIM)
  ui.popDWriteFont()
end
