-- Escort Mk2 DTM: 1980s-style VFD instrument cluster (replaces the analogue dials). 1200 x 400 canvas.
-- Rev bar graph (green / amber / red), mph, gear, tyre temps + pressures (ProTyres-style colours), fuel bar,
-- indicator and main-beam arrows, lap time.
local ON   = rgbm(0.20, 0.95, 0.63, 1)     -- lit VFD green
local DIM  = rgbm(0.07, 0.23, 0.17, 1)     -- unlit segment ghost
local LBL  = rgbm(0.13, 0.48, 0.34, 1)
local AMB  = rgbm(1.00, 0.69, 0.18, 1)
local RED  = rgbm(1.00, 0.25, 0.18, 1)
local BG   = rgbm(0.02, 0.07, 0.06, 1)
local BLUE = rgbm(0.30, 0.65, 1.00, 1)
local SEGS, X0, X1 = 34, 50, 1150
local screen = ac.findNodes("carRoot:" .. car.index):findMeshes("VFD_SCREEN"):ensureUniqueMaterials()
screen:setMaterialProperty("ksEmissive", rgb(1.4, 1.4, 1.4))
local blink = 0

-- tyre windows from the car's tyres.ini / performance curves: compound index -> optimum temp range (C), ideal psi
local WINDOW = { [0] = { 65, 80, 29 }, [1] = { 70, 90, 29 }, [2] = { 75, 95, 29 } }   -- S, M, H DTM90 slicks

-- ProTyres-style scale: deep blue (cold) -> light blue -> green (in the window) -> yellow -> orange -> red (hot)
local STOPS = {
  { -40, rgbm(0.15, 0.30, 1.00, 1) }, { -20, rgbm(0.20, 0.70, 1.00, 1) }, { 0, rgbm(0.20, 0.95, 0.35, 1) },
  { 10, rgbm(0.95, 0.95, 0.20, 1) }, { 20, rgbm(1.00, 0.60, 0.10, 1) }, { 32, rgbm(1.00, 0.18, 0.12, 1) } }
local function scale(x)   -- x = distance outside the good window (negative = below, positive = above, 0 = inside)
  if x <= STOPS[1][1] then return STOPS[1][2] end
  for i = 2, #STOPS do
    if x <= STOPS[i][1] then
      local a, b = STOPS[i - 1], STOPS[i]
      local t = (x - a[1]) / (b[1] - a[1])
      return rgbm(a[2].r + (b[2].r - a[2].r) * t, a[2].g + (b[2].g - a[2].g) * t, a[2].b + (b[2].b - a[2].b) * t, 1)
    end
  end
  return STOPS[#STOPS][2]
end
local function tempCol(t, lo, hi) return scale(t < lo and t - lo or (t > hi and t - hi or 0)) end
local function presCol(p, ideal)  -- 1 psi either side = green; each psi further = ~6 C on the temp scale
  local d = p - ideal
  return scale(math.abs(d) <= 1 and 0 or (d - (d > 0 and 1 or -1)) * 6)
end

local function txt(s, size, x, y, col)
  ui.dwriteDrawText(s, size, vec2(x, y), col)
end

local function tyre(i, x, y, lo, hi, ideal)
  local wh = car.wheels[i]
  local left = (i % 2 == 0)                      -- 0 FL, 1 FR, 2 RL, 3 RR: outer edge faces outwards
  local temps = left and { wh.tyreOutsideTemperature, wh.tyreMiddleTemperature, wh.tyreInsideTemperature }
                      or { wh.tyreInsideTemperature, wh.tyreMiddleTemperature, wh.tyreOutsideTemperature }
  for k = 1, 3 do                                -- inner / middle / outer surface bands (thin strip on top)
    ui.drawRectFilled(vec2(x + (k - 1) * 37, y), vec2(x + k * 37 - 3, y + 16), tempCol(temps[k], lo, hi))
  end
  local core = wh.tyreCoreTemperature
  txt(string.format("%3d", math.floor(core + 0.5)), 34, x + 18, y + 18, tempCol(core, lo, hi))
  local p = wh.tyrePressure
  txt(string.format("%4.1f", p), 28, x + 20, y + 58, presCol(p, ideal))
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
    txt(tostring(k), 26, X0 + (X1 - X0) * k * 1000 / lim - 6, 136, LBL)
  end
  txt("x1000 RPM", 22, X1 - 130, 8, LBL)
  -- speed
  txt(string.format("%3d", math.floor(car.speedKmh * 0.621371 + 0.5)), 128, 30, 200, ON)
  txt("MPH", 30, 40, 352, LBL)
  -- gear
  local g = car.gear
  local gs = g < 0 and "R" or (g == 0 and "N" or tostring(g))
  txt(gs, 150, 290, 185, (car.rpm > lim * 0.93) and RED or ON)
  txt("GEAR", 30, 292, 352, LBL)
  -- tyres: front row on top, as seen from the driver's seat
  local win = WINDOW[car.compoundIndex]
  local lo, hi, ideal
  if win then lo, hi, ideal = win[1], win[2], win[3]
  else local o = car.wheels[0].tyreOptimumTemperature; lo, hi, ideal = o - 10, o + 10, 37 end   -- Vintage GT70
  tyre(0, 420, 172, lo, hi, ideal); tyre(1, 540, 172, lo, hi, ideal)
  tyre(2, 420, 278, lo, hi, ideal); tyre(3, 540, 278, lo, hi, ideal)
  -- fuel
  local f = car.maxFuel > 0 and math.min(car.fuel / car.maxFuel, 1) or 0
  txt("FUEL", 30, 770, 200, ON)
  ui.drawRectFilled(vec2(770, 245), vec2(1150, 275), DIM)
  ui.drawRectFilled(vec2(770, 245), vec2(770 + 380 * f, 275), f < 0.15 and AMB or ON)
  txt(string.format("%3d L", math.floor(car.fuel + 0.5)), 30, 960, 200, ON)
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
