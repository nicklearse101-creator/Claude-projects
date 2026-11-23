-- RaceLogic lap timer (Escort Mk2 DTM). Running lap time; after crossing the line the finished lap is held
-- for 4 s (like the real unit), then it runs again. Screen backlight always on.
local fg = rgbm(0.86, 0.95, 1.0, 1)
local hold = rgbm(1.0, 0.92, 0.45, 1)
local screen = ac.findNodes("carRoot:" .. car.index):findMeshes("RACE_LOGIC"):ensureUniqueMaterials()
screen:setMaterialProperty("ksEmissive", rgb(0.35, 0.35, 0.35))

local function fmt(ms)
  if not ms or ms <= 0 then return "0:00.00" end
  local m = math.floor(ms / 60000)
  local s = (ms % 60000) / 1000
  return string.format("%d:%05.2f", m, s)
end

function update(dt)
  ui.pushDWriteFont("Impact:fonts/impact.ttf;Weight=Bold;Stretch=Expanded")
  local t, col = car.lapTimeMs, fg
  if car.lapTimeMs < 4000 and car.previousLapTimeMs and car.previousLapTimeMs > 0 then
    t, col = car.previousLapTimeMs, hold
  end
  ui.setCursor(vec2(32, 5))
  ui.dwriteTextAligned(fmt(t), 80, ui.Alignment.End, ui.Alignment.Center, vec2(420, 512), false, col)
  ui.popDWriteFont()
end
