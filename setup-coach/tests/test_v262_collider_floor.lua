-- v2.6.2: THE COLLIDER IS THE BOTTOM OF THE CAR. The shipped functions are
-- cut out of the app as-is and run against real colliders.ini / car.ini /
-- suspensions.ini text from the extracted cars, a stub world with a flat
-- track at y = 0, and a car transform that can pitch.

local appPath = arg[1] or 'D:/SteamLibrary/steamapps/common/assettocorsa/apps/lua/setupcoach/SetupCoach.lua'
local EX = 'D:/Claude/setupcoach-tools/acd/extracted/'
local f = assert(io.open(appPath, 'r'))
local src = f:read('a')
f:close()

local pass, fail = 0, 0
local function check(label, got, want)
  if got == want then pass = pass + 1; print(string.format('  PASS  %-74s %s', label, tostring(got)))
  else fail = fail + 1; print(string.format('  FAIL  %-74s got %s want %s', label, tostring(got), tostring(want))) end
end
local function near(label, got, want, tol)
  local ok = type(got) == 'number' and math.abs(got - want) <= tol
  if ok then pass = pass + 1; print(string.format('  PASS  %-74s %.4f', label, got))
  else fail = fail + 1; print(string.format('  FAIL  %-74s got %s want %.4f±%.4f', label, tostring(got), want, tol)) end
end
local function fn(name)
  local s = src:find('\nlocal function ' .. name .. '%(')
  assert(s, name)
  local e = src:find('\nend\n', s + 1, true)
  return src:sub(s + 1, e + 4)
end
local function readFile(p) local h = io.open(p, 'r'); if not h then return nil end; local t = h:read('a'); h:close(); return t end

------------------------------------------------------------------------------
-- Stubs: vec3, INI files (CSP-like get), ac, physics, a car transform.
------------------------------------------------------------------------------
local V = {}
V.__index = V
local function vec3(x, y, z) return setmetatable({x = x or 0, y = y or 0, z = z or 0}, V) end
function V:dot(o) return self.x * o.x + self.y * o.y + self.z * o.z end

-- mode 'vec3' (CSP as documented): a string default gives the first item,
-- a vec3 default parses x, y, z, a number default + offset gives that item;
-- 'offset': as 'vec3' but no vec3 parsing; 'raw': the string default gives
-- the whole line, vec3 / number defaults come back unchanged.
local function parseIni(text, mode)
  local data, sec = {}, nil
  for line in (text or ''):gmatch('[^\r\n]+') do
    local s = line:match('^%s*%[([^%]]+)%]')
    if s then sec = s; data[sec] = data[sec] or {}
    elseif sec then
      local k, v = line:match('^%s*([%w_]+)%s*=%s*(.-)%s*$')
      if k then data[sec][k] = v end
    end
  end
  local ini = {}
  function ini:get(section, key, default, offset)
    local raw = data[section] and data[section][key]
    if raw == nil then return default end
    local clean = raw:gsub(';.*$', '')
    local items = {}
    for it in (clean .. ','):gmatch('([^,]*),') do items[#items + 1] = it:gsub('^%s+', ''):gsub('%s+$', '') end
    if type(default) == 'table' and getmetatable(default) == V then
      if mode ~= 'vec3' then return default end
      return vec3(tonumber(items[1]), tonumber(items[2]), tonumber(items[3]))
    elseif type(default) == 'number' then
      if mode == 'raw' then return default end
      return tonumber(items[offset or 1]) or default
    elseif type(default) == 'string' then
      if mode == 'raw' then return raw end
      return items[1]
    end
    return default
  end
  return ini
end

local FILES, MODE, COLS = {}, 'vec3', nil
local ac = {INIConfig = {carData = function(_, name)
  local t = FILES[name]
  if not t then error('no such file') end
  return parseIni(t, MODE)
end}, getCarColliders = function() if COLS then return COLS end; return {} end}
local GROUND = 0
local physics = {raycastTrack = function(o, dir, len)
  if dir.y >= 0 then return -1 end
  local d = o.y - GROUND
  if d < 0 or d > len then return -1 end
  return d
end}

-- Car at CG position (0, h, 0), pitched nose-DOWN by `deg`.
local function makeCar(h, deg, flipLook)
  local a = math.rad(deg or 0)
  local c, s = math.cos(a), math.sin(a)
  local function rot(v) return vec3(v.x, v.y * c - v.z * s, v.z * c + v.y * s) end
  local tr = {}
  function tr:transformVector(v) return rot(v) end
  function tr:transformPoint(v) local r = rot(v); return vec3(r.x, r.y + h, r.z) end
  local car = {index = 0, transform = tr, up = rot(vec3(0, 1, 0)), look = rot(vec3(0, 0, flipLook and -1 or 1))}
  return car
end
-- What the car itself reports at its pickups (flat track), plus an error.
local function setRideHeight(car, info, err)
  local function at(y, z) local p = car.transform:transformPoint(vec3(0, y, z)); return p.y - GROUND end
  car.rideHeight = {[0] = at(info.pickupF, info.pickZF) + (err or 0), [1] = at(info.pickupR, info.pickZR) + (err or 0)}
end

local env = {math = math, string = string, table = table, ipairs = ipairs, pairs = pairs, tostring = tostring,
  tonumber = tonumber, type = type, pcall = pcall, error = error, vec3 = vec3, ac = ac, physics = physics}
local chunk = fn('iniStr') .. fn('iniNum') .. src:match('\nlocal COLLIDER = %b{}') .. '\n'
  .. fn('readGroundColliders') .. fn('rayClearance') .. fn('colliderMeasure') .. fn('colliderVerdict') .. fn('floorSample')
  .. '\nreturn {read = readGroundColliders, measure = colliderMeasure, verdict = colliderVerdict, sample = floorSample, C = COLLIDER}\n'
local A = assert(load(chunk, 'extracted', 't', env))()

local function useCar(folder)
  FILES = {['colliders.ini'] = readFile(EX .. folder .. '/colliders.ini'), ['car.ini'] = readFile(EX .. folder .. '/car.ini'),
    ['suspensions.ini'] = readFile(EX .. folder .. '/suspensions.ini')}
end

print('')
print('=== Huracan GT3: one ground box, CENTRE 0,-0.25,0.4 SIZE 1.55,0.1,3.75 ===')
useCar('ks_lamborghini_huracan_gt3')
for _, m in ipairs({'vec3', 'offset', 'raw'}) do
  MODE = m
  local pts, info = A.read(0)
  check('[' .. m .. '] source colliders.ini', info.src, 'colliders.ini')
  check('[' .. m .. '] 1 box, 5 points (4 bottom corners + centre)', info.boxes .. '/' .. #pts, '1/5')
  near('[' .. m .. '] lowest face front = -0.25 - 0.05', info.lowF, -0.30, 1e-9)
  near('[' .. m .. '] lowest face rear (box runs back to z -1.475)', info.lowR, -0.30, 1e-9)
end
MODE = 'vec3'
local pts, info = A.read(0)
near('pickup front from car.ini', info.pickupF, -0.300, 1e-9)
near('pickup rear', info.pickupR, -0.304, 1e-9)
near('front axle line 2.620 x (1 - 0.43)', info.pickZF, 1.4934, 1e-4)
near('rear axle line -2.620 x 0.43', info.pickZR, -1.1266, 1e-4)

print('')
print('=== Corvette Z06 GT3: [HEADER] COLLIDERS=3 but four sections ===')
useCar('corvette_z06_gt3_2024')
pts, info = A.read(0)
check('only the first 3 boxes (the header count)', info.boxes, 3)
near('splitter boxes sit higher than the floor (-0.295 vs -0.30)', info.lowF, -0.30, 1e-9)

print('')
print('=== SV8 Camaro: inline comments, no GROUND_ENABLE key ===')
useCar('sv8_camaro_v2')
for _, m in ipairs({'vec3', 'offset', 'raw'}) do
  MODE = m
  pts, info = A.read(0)
  check('[' .. m .. '] read through the comments', info.boxes, 1)
  near('[' .. m .. '] lowest face -0.295 - 0.005', info.lowF, -0.300, 1e-9)
end
MODE = 'vec3'

print('')
print('=== GROUND_ENABLE=0 is not floor ===')
FILES['colliders.ini'] = '[COLLIDER_0]\nCENTRE=0,-0.25,0\nSIZE=1.5,0.1,3\nGROUND_ENABLE=0\n[COLLIDER_1]\nCENTRE=0,-0.2,0\nSIZE=1.5,0.1,3\nGROUND_ENABLE=1\n'
pts, info = A.read(0)
check('only the ground box', info.boxes, 1)
near('...whose face is -0.25', info.lowF, -0.25, 1e-9)

print('')
print('=== no colliders.ini: CSP\'s own list ===')
FILES['colliders.ini'] = nil
COLS = {{position = vec3(0, -0.2, 0.1), size = vec3(1.6, 0.1, 3.0)}}
pts, info = A.read(0)
check('source ac.getCarColliders', info.src, 'ac.getCarColliders')
near('face -0.25', info.lowF, -0.25, 1e-9)
COLS = nil
pts, info = A.read(0)
check('nothing at all -> no boxes', info.boxes, 0)

print('')
print('=== measuring: Huracan, CG 0.40 m above a flat track ===')
useCar('ks_lamborghini_huracan_gt3')
pts, info = A.read(0)
A.C.DOWN = nil
local car = makeCar(0.40, 0)
local mF, mR, pkF, pkR = A.measure(car, pts, info)
near('level: front floor 0.40 - 0.30', mF, 0.100, 1e-9)
near('level: rear floor', mR, 0.100, 1e-9)
near('level: front pickup', pkF, 0.100, 1e-9)
near('level: rear pickup (-0.304)', pkR, 0.096, 1e-9)
car = makeCar(0.40, 1)
mF, mR = A.measure(car, pts, info)
-- front corner z 2.275: 0.40 - 0.30 cos1 - 2.275 sin1 = 0.0603
near('1 deg nose down: the front corner comes 40 mm closer', mF, 0.40 - 0.30 * math.cos(math.rad(1)) - 2.275 * math.sin(math.rad(1)), 1e-9)
near('...and the rear rises (corner z -1.475)', mR, 0.40 - 0.30 * math.cos(math.rad(1)) + 1.475 * math.sin(math.rad(1)), 1e-9)
car = makeCar(0.28, 0)
mF = A.measure(car, pts, info)
near('into the track: negative clearance', mF, -0.020, 1e-9)

print('')
print('=== the live check: pickups through this pipeline vs the car\'s own ride height ===')
local function run(frames, h, deg, err, flip, zeroRh)
  local self = {carId = 'test_car'}
  local a, b
  for i = 1, frames do
    local c = makeCar(h, deg, flip)
    setRideHeight(c, info, err)
    if zeroRh then c.rideHeight = {[0] = 0, [1] = 0} end
    a, b = A.sample(self, c)
  end
  return self, a, b
end
local S, a, b = run(299, 0.40, 0.3, 0.004)
check('299 frames: still pending', (A.verdict(S)), 'pending')
check('...floor data from the ride-height points meanwhile', S.floorSrc, 'ride height')
S, a, b = run(300, 0.40, 0.3, 0.004)
check('300 frames within 25 mm: verified', (A.verdict(S)), 'verified')
check('...floor data from the collider', S.floorSrc, 'collider')
near('...and it is the collider\'s lowest front point', a, 0.40 - 0.30 * math.cos(math.rad(0.3)) - 2.275 * math.sin(math.rad(0.3)), 1e-9)
S, a, b = run(300, 0.40, 0, 0.040)
check('40 mm out: mismatch', (A.verdict(S)), 'mismatch')
check('...ride-height points kept', S.floorSrc, 'ride height')
local _, why = A.verdict(S)
check('...and the log says by how much', why:find('F %-40 / R %-40 mm', 1) ~= nil, true)
S, a, b = run(300, 0.40, 0, 0, false, true)
check('car reports no ride height: unverified, collider used', (A.verdict(S)) .. '/' .. S.floorSrc, 'unverified/collider')
S, a, b = run(5, 0.40, 0, 0, true)
check('transform z not the car\'s look: not used', (A.verdict(S)), 'none')
check('...says why', select(2, A.verdict(S)):find('axes do not match', 1, true) ~= nil, true)
check('...ride-height points kept', S.floorSrc, 'ride height')
FILES['colliders.ini'] = nil
S = run(5, 0.40, 0, 0)
check('no colliders: none, ride-height points', (A.verdict(S)) .. '/' .. S.floorSrc, 'none/ride height')

print('')
print(string.format('%d passed, %d failed', pass, fail))
os.exit(fail == 0 and 0 or 1)
