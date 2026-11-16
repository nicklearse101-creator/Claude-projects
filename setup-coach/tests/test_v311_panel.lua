-- v3.1.1: the panel. v3.1.0 left a stale second slowDamperAdvice inside
-- buildAdvice that shadowed the new one and threw every frame, so the advice
-- list never filled in game. This runs the real app file end to end: load,
-- 300 sim frames with a fake car, then windowMain, and checks what it draws.
local appPath = arg[1] or 'D:/SteamLibrary/steamapps/common/assettocorsa/apps/lua/setupcoach/SetupCoach.lua'
local pass, fail = 0, 0
local function check(label, got, want)
  if got == want then pass = pass + 1; print(string.format('  PASS  %-70s %s', label, tostring(got)))
  else fail = fail + 1; print(string.format('  FAIL  %-70s got %s want %s', label, tostring(got), tostring(want))) end
end
local fsrc = assert(io.open(appPath, 'rb')); local src = fsrc:read('a'):gsub('\r\n', '\n'); fsrc:close()
-- Load the app with permissive stubs, feed a fake car, draw windowMain, print what it shows.
local function anyTable(name)
  local t = {}
  return setmetatable(t, {__index = function(_, k) return 0 end})
end
local function deep()
  local mt = {}
  local proxy = setmetatable({}, mt)
  mt.__index = function(_, k) return proxy end
  mt.__call = function() return proxy end
  mt.__tostring = function() return '' end
  return proxy
end
local out = {}
local function cap(s) out[#out + 1] = tostring(s) end
ui = setmetatable({
  text = cap, textWrapped = cap, textColored = function(t) cap('*'..t) end, getCursorX = function() return 0 end,
  slider = function(l, c) return c end, checkbox = function() return false end,
  inputText = function(l, c) return c end, button = function() return false end,
  Font = {Small = 1, Title = 2, Main = 3},
}, {__index = function() return function() return false end end})
vec2 = function(x, y) return {x = x, y = y} end
vec3 = function(x, y, z) return {x = x or 0, y = y or 0, z = z or 0} end
rgbm = function(r,g,b,a) return {r,g,b,a} end
script = {}
local wheels = {}
for i = 1, 4 do
  wheels[i] = setmetatable({tyrePressure = 26, tyreCoreTemperature = 80, camber = -2, load = 3000,
    suspensionTravel = 0.03, ndSlip = 0.5, slipAngle = 2, position = vec3(), contactPoint = vec3(), contactNormal = vec3(0,1,0), look = vec3(0,0,1), up = vec3(0,1,0), outside = vec3(1,0,0), velocity = vec3()}, {__index = function() return 0 end})
end
local car = setmetatable({wheels = wheels, speedKmh = 120, rpm = 6000, fuel = 30, lapCount = 1,
  name = function() return 'Fake' end, acceleration = vec3(0.5,0,1), velocity = vec3(0,0,30), localVelocity = vec3(0,0,30), angularVelocity = vec3(0,0.1,0), localAngularVelocity = vec3(0,0.1,0), position = vec3(), look = vec3(0,0,1), side = vec3(1,0,0), up = vec3(0,1,0)}, {__index = function() return 0 end})
local sim = setmetatable({isPaused = false, isReplayActive = false}, {__index = function() return 0 end})
ac = setmetatable({
  storage = function(t) return t end,
  getCar = function() return car end, getSim = function() return sim end,
  getCarID = function() return 'fake_car' end, getTrackID = function() return 'fake_track' end,
}, {__index = function(_, k) if k:match("^%u") then return deep() end return function() return nil end end})
io.createDir = io.createDir or function() end
local chunk = assert(loadfile(appPath))
check('app loads', (pcall(chunk)), true)
local updErr
for i = 1, 300 do
  for k = 1, 4 do wheels[k].suspensionTravel = 0.03 + 0.01 * math.sin(i * 0.3 + k) end
  local o, e = pcall(script.onSimUpdate, 0.016)
  if not o then updErr = e break end
end
check('300 sim frames run without an error', updErr, nil)
local o, e = pcall(script.windowMain, 0.016)
check('windowMain draws', o, true)
local all = table.concat(out, '\n')
check('advice list filled (WHAT TO CHANGE header)', all:find('WHAT TO CHANGE', 1, true) ~= nil, true)
check('fine / measuring summary drawn', all:find('Fine: ', 1, true) ~= nil or all:find('Still measuring: ', 1, true) ~= nil, true)
check('live tyre table drawn', all:find('Temp in / mid / out', 1, true) ~= nil, true)
check('balance summary drawn', all:find('Low speed: push', 1, true) ~= nil, true)
local adv = src:match('\nfunction engine:buildAdvice%(.-\nend\n')
local _, nDefs = adv:gsub('local function slowDamperAdvice%(', '')
check('one slowDamperAdvice in buildAdvice', nDefs, 1)
check('buildAdvice does not read DAMPER_HIST_MIN_S (declared below it)', adv:find('DAMPER_HIST_MIN_S', 1, true), nil)

print('')
print(string.format('%d passed, %d failed', pass, fail))
os.exit(fail == 0 and 0 or 1)
