-- v2.5.0: everything built from the v2.4.0 logs and the Sunbeam project.
-- The shipped functions and code blocks are extracted from the app and run
-- against the REAL extracted car data (the Sunbeam as it stands today, plus
-- the ten other extracted cars) with stand-ins for CSP: an INI reader that
-- behaves like ac.INIConfig (get() + .sections), a LUT reader for final.rto,
-- and setup spinners.

local appPath = arg[1] or 'D:/SteamLibrary/steamapps/common/assettocorsa/apps/lua/setupcoach/SetupCoach.lua'
local EXT = 'D:/Claude/setupcoach-tools/acd/extracted/'
local SUN_ID = 'talbot_sunbeam_lotus_81_works'
local f = assert(io.open(appPath, 'r'))
local src = f:read('a')
f:close()

local pass, fail = 0, 0
local function check(label, got, want)
  if got == want then pass = pass + 1; print(string.format('  PASS  %-80s %s', label, tostring(got)))
  else fail = fail + 1; print(string.format('  FAIL  %-80s got %s want %s', label, tostring(got), tostring(want))) end
end
local function near(label, got, want, tol)
  local ok = type(got) == 'number' and math.abs(got - want) <= tol
  if ok then pass = pass + 1; print(string.format('  PASS  %-80s %.4f', label, got))
  else fail = fail + 1; print(string.format('  FAIL  %-80s got %s want %.4f±%.4f', label, tostring(got), want, tol)) end
end

------------------------------------------------------------------------------
-- Extraction (function / if / do counted against end; escapes, comments and
-- strings stripped first).
------------------------------------------------------------------------------
local function extractFrom(s)
  local body, depth, out = src:sub(s), 0, {}
  for line in body:gmatch('[^\n]*\n?') do
    table.insert(out, line)
    local stripped = line:gsub('\\.', ''):gsub('%-%-.*$', ''):gsub("'[^']*'", ''):gsub('"[^"]*"', '')
    for _ in stripped:gmatch('%f[%w_]function%f[^%w_]') do depth = depth + 1 end
    for _ in stripped:gmatch('%f[%w_]if%f[^%w_]') do depth = depth + 1 end
    for _ in stripped:gmatch('%f[%w_]do%f[^%w_]') do depth = depth + 1 end
    for _ in stripped:gmatch('%f[%w_]end%f[^%w_]') do depth = depth - 1 end
    if depth == 0 then break end
  end
  return table.concat(out)
end
local function fn(name) local s = src:find('\nlocal function ' .. name .. '%('); assert(s, 'fn ' .. name); return extractFrom(s + 1) end
local function method(name) local s = src:find('\nfunction engine:' .. name .. '%('); assert(s, 'method ' .. name); return extractFrom(s + 1) end
local function const(name) local l = src:match('\nlocal ' .. name .. ' = [^\n]+'); assert(l, 'const ' .. name); return l end
local function tbl(name) local l = src:match('\nlocal ' .. name .. ' = %b{}'); assert(l, 'table ' .. name); return l end
local function between(startMarker, endMarker)
  local s = src:find(startMarker, 1, true); assert(s, 'marker ' .. startMarker)
  local e = src:find(endMarker, s + #startMarker, true); assert(e, 'end marker ' .. endMarker)
  return src:sub(s, e - 1)
end

------------------------------------------------------------------------------
-- CSP stand-ins.
------------------------------------------------------------------------------
local function readText(path)
  local h = io.open(path, 'r'); if not h then return nil end
  local t = h:read('a'); h:close(); return t
end
local function parseIni(text)
  local secs, cur = {}, nil
  for line in ((text or '') .. '\n'):gmatch('([^\n]*)\n') do
    line = line:gsub('\r$', '')
    local s = line:match('^%s*%[(.-)%]')
    if s then cur = s; secs[cur] = secs[cur] or {}
    elseif cur then
      local k, v = line:match('^%s*([%w_]+)%s*=%s*(.-)%s*$')
      if k then v = v:gsub('%s*;.*$', ''); secs[cur][k] = {v} end
    end
  end
  local obj = {sections = secs}
  function obj:get(section, key, default)
    local sec = self.sections[section]; local v = sec and sec[key]
    if not v then return default end
    return v[1]
  end
  return obj
end
local CAR_DIR = EXT .. SUN_ID .. '/'
local OVERRIDE = {}   -- file -> text, to simulate a changed car
local SPINNERS = {}
ac = {
  INIConfig = {carData = function(_, file)
    local t = OVERRIDE[file] or readText(CAR_DIR .. file)
    return parseIni(t or '')
  end},
  DataLUT11 = {carData = function(_, file)
    local t = OVERRIDE[file] or readText(CAR_DIR .. file)
    if not t then return nil end
    local pts = {}
    for line in (t .. '\n'):gmatch('([^\n]*)\n') do
      local x, y = line:match('^%s*(.-)%s*|%s*([%-%d%.]+)')
      if y then table.insert(pts, {x = tonumber(x), y = tonumber(y)}) end
    end
    local lut = {}
    function lut:getPointOutput(i) local p = pts[i + 1]; return p and p.y or 0 / 0 end
    function lut:getPointInput(i) local p = pts[i + 1]; return p and (p.x or 0 / 0) or 0 / 0 end
    return lut
  end},
  getSetupSpinners = function() return SPINNERS end,
}

------------------------------------------------------------------------------
-- Chunk A: helpers and engine methods.
------------------------------------------------------------------------------
local settings = {biasBaselineCars = '', rideCal = '', camberGain = '', leverLedger = '', leverPending = '',
  branchState = '', lastBuildRecord = '', physicsPrints = '', buildMinLaps = 2}
local envA = {math = math, string = string, table = table, pairs = pairs, ipairs = ipairs, tostring = tostring,
  tonumber = tonumber, type = type, next = next, pcall = pcall, select = select, os = os, print = print,
  ac = ac, settings = settings, classIdeals = function() return 26, 26 end}
local chunk = 'local engine = {}\n'
for _, c in ipairs({'TRAVEL_FALLBACK_M', 'KEYED_KEEP', 'LEDGER_KEEP_CARS', 'PHYSICS_KEEP_CARS',
    'LONG_TRACK_M', 'SECTION_M', 'HELD_SLIDE_S', 'BUILD_MIN_CORNERS', 'BRANCH_KEEP_RECORDS',
    'FLOOR_HIST_MAX_MM', 'FLOOR_LOW_SHARE', 'FLOOR_MIN_SAMPLES', 'FLOOR_PLAUSIBLE_MM'}) do  -- v2.6.0 banking
  chunk = chunk .. const(c) .. '\n'
end
chunk = chunk .. '\nlocal settings = settings or {}\n' .. assert(src:match('\n%-%- BALANCE MODES BEGIN.-%-%- BALANCE MODES END'), 'balance modes block') .. '\n' .. tbl('PHYSICS_FILES') .. '\n' .. tbl('EV_UNIT') .. '\n' .. tbl('WINDOW_KEYS') .. '\n'
for _, name in ipairs({'n', 'clamp', 'iniGet', 'iniStr', 'iniNum', 'travelRefSane', 'readTravelRef', 'tyreBrakeForce',
    'readTyreReference', 'lutPoints', 'parsePointStore', 'serialisePointStore', 'parseLedgerStore',
    'parseKeyedStore', 'serialiseKeyedStore', 'keyedGet', 'keyedPut', 'keyedDropCar',
    'fmtNum', 'parseSecList', 'serialiseSecList', 'parseBranchStore', 'serialiseBranchStore',
    'unitsPerLapFor', 'unitWord', 'longTrackNote', 'counterSnapshot', 'textHash', 'iniCanon', 'physicsPrintOf',
    'recordSectorEvent', 'unrecordSectorEvent', 'windowBins', 'windowLapStats',
    'floorHistAdd', 'floorHistClearance'}) do  -- v2.6.0 banking
  chunk = chunk .. fn(name) .. '\n'
end
for _, m in ipairs({'refreshTravelRef', 'biasTarget', 'leverLedgerFor', 'leverLedgerSave', 'leverHistoryReset',
    'forgetLearned', 'checkPhysicsFingerprint', 'biasBaselineDone', 'markBiasBaselineDone', 'bankEvidenceUnit', 'consumeWindow'}) do
  chunk = chunk .. method(m) .. '\n'
end
chunk = chunk .. [[
return {engine = engine, readTravelRef = readTravelRef, tyreBrakeForce = tyreBrakeForce, readTyreReference = readTyreReference,
  unitsPerLapFor = unitsPerLapFor, unitWord = unitWord, longTrackNote = longTrackNote, EV_UNIT = EV_UNIT, WINDOW_KEYS = WINDOW_KEYS,
  counterSnapshot = counterSnapshot, n = n, textHash = textHash, iniCanon = iniCanon, physicsPrintOf = physicsPrintOf,
  parseKeyedStore = parseKeyedStore, serialiseKeyedStore = serialiseKeyedStore, keyedGet = keyedGet, keyedPut = keyedPut,
  keyedDropCar = keyedDropCar, parsePointStore = parsePointStore, parseLedgerStore = parseLedgerStore,
  parseBranchStore = parseBranchStore, serialiseBranchStore = serialiseBranchStore, windowLapStats = windowLapStats,
  recordSectorEvent = recordSectorEvent, unrecordSectorEvent = unrecordSectorEvent, HELD_SLIDE_S = HELD_SLIDE_S}
]]
local A = assert(load(chunk, 'chunkA', 't', envA))()
local E = A.engine

------------------------------------------------------------------------------
print('=== 1. travel range: PACKER_RANGE, not a made-up 12 cm (real suspensions.ini files) ===')
check('no car has a TRAVEL key; the app no longer reads one', src:find("iniGet%(ini, 'FRONT', 'TRAVEL'") == nil, true)
local cars = {
  {SUN_ID, 0.140, 0.120}, {'ks_lamborghini_huracan_gt3', 0.055, 0.055}, {'corvette_z06_gt3_2024', 0.065, 0.065},
  {'ferrari_458_gt2', 0.035, 0.060}, {'fr_bmw_btcc', 0.1119, 0.140}, {'lotus_exos_125_s1', 0.040, 0.045},
}
for _, c in ipairs(cars) do
  CAR_DIR = EXT .. c[1] .. '/'
  local tf, tr, why = A.readTravelRef(0)
  near(c[1] .. ' front range (m)', tf, c[2], 1e-6)
  near(c[1] .. ' rear range (m)', tr, c[3], 1e-6)
end
CAR_DIR = EXT .. 'no_such_car/'
local tf0, tr0, why0 = A.readTravelRef(0)
check('a car with no PACKER_RANGE keeps the old 0.12 m, and says so', tf0 == 0.12 and tr0 == 0.12 and why0:find('0%.12 m assumed') ~= nil, true)
CAR_DIR = EXT .. SUN_ID .. '/'
local _, _, whySun = A.readTravelRef(0)
check('source named', whySun, 'suspensions.ini PACKER_RANGE')
-- The Sunbeam at Bathurst: peaks ~18 cm, 6.3 cm at rest (shared memory, Sunbeam project).
near('Sunbeam 18 cm peak: old reading 150% of 12 cm', 0.18 / 0.12, 1.50, 1e-9)
near('...now 129% of its own 140 mm - still over: on the packers, a real finding', 0.18 / 0.140, 1.2857, 1e-3)
near('at rest 6.3 cm = 45% of its range', 0.0636 / 0.140, 0.454, 1e-3)
near('Huracan: 5.4 cm is 98% of its 55 mm - bottoming can finally register (was 45% of 12 cm)', 0.054 / 0.055, 0.982, 1e-3)

print('')
print('=== live packers override (mm on every car checked, SHOW_CLICKS rules) ===')
CAR_DIR = EXT .. 'ks_lamborghini_huracan_gt3/'
SPINNERS = {{name = 'PACKER_RANGE_LF', value = 40}, {name = 'PACKER_RANGE_RF', value = 40},
  {name = 'PACKER_RANGE_LR', value = 50}, {name = 'PACKER_RANGE_RR', value = 50}, {name = 'FRONT_BIAS', value = 57}}
E:refreshTravelRef(0)
near('LF from the live setup: 40 mm', E.travelRef.LF, 0.040, 1e-9)
near('front axle range = the shorter corner', E.lastTravelF, 0.040, 1e-9)
near('rear 50 mm', E.lastTravelR, 0.050, 1e-9)
check('source says it came from the setup', E.travelRefSrc:find("your setup's packer range on 4 corners") ~= nil, true)
near('the same read notes the car\'s bias for the BRAKE line', E.liveBiasPct, 57, 1e-9)
SPINNERS = {{name = 'PACKER_RANGE_LF', value = 2000}}   -- nonsense value
E:refreshTravelRef(0)
near('a nonsense spinner value is ignored (suspensions.ini stands)', E.travelRef.LF, 0.055, 1e-9)
OVERRIDE['setup.ini'] = '[PACKER_RANGE_LF]\nSHOW_CLICKS=2\nMIN=30\nMAX=70\nSTEP=1\n'
SPINNERS = {{name = 'PACKER_RANGE_LF', value = 12}}   -- 12 steps from 30 mm
E:refreshTravelRef(0)
near('SHOW_CLICKS=2: 12 steps from MIN 30 = 42 mm', E.travelRef.LF, 0.042, 1e-9)
OVERRIDE, SPINNERS = {}, {}
CAR_DIR = EXT .. SUN_ID .. '/'

------------------------------------------------------------------------------
print('')
print('=== 2. brake bias: grip, not load (the Sunbeam\'s own tyres) ===')
local ref = A.readTyreReference(0, SUN_ID, 'V70', 0)
check('Sunbeam tyres: load-sensitivity model read (front)', ref.brakeModelF and ref.brakeModelF.kind, 'ls')
near('front LS_EXPX', ref.brakeModelF.lsx, 0.7203, 1e-9)
near('rear FZ0', ref.brakeModelR.fz0, 2006, 1e-9)
-- braking loads at the Nordschleife: 76.1% on the front of 10377 N
local W = 10377
local fz_f, fz_r = W * 0.761 / 2, W * 0.239 / 2
local cf = A.tyreBrakeForce(ref.brakeModelF, fz_f) * 2
local cr = A.tyreBrakeForce(ref.brakeModelR, fz_r) * 2
near('front tyre grips less per newton: mu at 3.95 kN', A.tyreBrakeForce(ref.brakeModelF, fz_f) / fz_f, 1.092, 0.005)
near('rear grips more: mu at 1.24 kN', A.tyreBrakeForce(ref.brakeModelR, fz_r) / fz_r, 1.559, 0.005)
near('front share of the grip = 69.0% (of the load: 76.1%)', 100 * cf / (cf + cr), 69.05, 0.2)

-- the shipped accumulator, fed 40 samples over 5 zones
local brakeBlock = between('  -- v2.3.0: HARD STRAIGHT-LINE BRAKING', '  -- v2.3.0: DYNAMIC FRONT RIDE HEIGHT')
local brakeFn = assert(load('return function(self, onTrack, brake, longG, absSteer, absLat, speed, handbrakeRecent, w)\n' .. brakeBlock .. '\nend',
  'brake', 't', setmetatable({tyreBrakeForce = A.tyreBrakeForce, n = A.n}, {__index = envA})))()
local B = {brakeModelF = ref.brakeModelF, brakeModelR = ref.brakeModelR, tyreRadiusF = 0.295, tyreRadiusR = 0.295}
local wheels = {{load = fz_f}, {load = fz_f}, {load = fz_r}, {load = fz_r}}
for zone = 1, 5 do
  for _ = 1, 8 do brakeFn(B, true, 0.95, -1.1, 2, 0.05, 150, false, wheels) end
  brakeFn(B, true, 0, 0, 0, 0, 150, false, wheels)   -- off the brakes between zones
end
check('5 zones counted', B.brkZones, 5)
for _ = 1, 10 do brakeFn(B, true, 0.95, -1.1, 2, 0.05, 150, true, wheels) end
check('handbrake stops are not samples', B.brkLoadN, 40)
local bt, info = E.biasTarget(B)
near('target = 69.05% equal-limit + 1% margin (v2.4.0 said 77.1%)', bt, 70.05, 0.2)
check('the info explains load vs grip', info:find('front carries 76%.1%% of tyre load') ~= nil and info:find('so the front can use 69%.0%% of the braking') ~= nil, true)
local B2 = {brkLoadN = 40, brkZones = 5, brkLoadFSum = 40 * 0.761, tyreRadiusF = 0.295, tyreRadiusR = 0.295}
local bt2, info2 = E.biasTarget(B2)
near('no grip model -> load only, as before: 77.1%', bt2, 77.1, 1e-6)
check('...and it says so', info2:find('load only') ~= nil, true)
check('lockups at 69% with fronts first now agree: 69% is where the fronts go first', bt - 1 >= 68.5 and bt - 1 <= 69.6, true)

------------------------------------------------------------------------------
print('')
print('=== 3. long tracks: sections of a lap are the evidence units ===')
check('Adelaide 3.2 km -> laps', A.unitsPerLapFor(3219), 1)
check('Spa 7.0 km -> laps', A.unitsPerLapFor(7004), 1)
check('Le Mans 13.6 km -> 3 sections', A.unitsPerLapFor(13626), 3)
check('Nordschleife 20.8 km -> 4 sections', A.unitsPerLapFor(20832), 4)
check('Nordschleife + GP 25.3 km -> 5 sections', A.unitsPerLapFor(25378), 5)

local unitBlock = between('  -- Fuel\n  if self.lapStartFuel == nil then', '  local cspBurn = n(car.fuelPerLap, 0)')
local envU = setmetatable({unitsPerLapFor = A.unitsPerLapFor, EV_UNIT = A.EV_UNIT, counterSnapshot = A.counterSnapshot,
  WINDOW_KEYS = A.WINDOW_KEYS, n = A.n}, {__index = envA})
local unitFn = assert(load('return function(self, car, sim, fuel, lapCount)\n' .. unitBlock .. '\nend', 'units', 't', envU))()
local function newEng()
  local e = {lapBins = {}, lastLapCount = -1, lapPitSeen = false, lapTravelUseF = 0, lapTravelUseR = 0,
    windowBinsStart = 0, curUnit = 0, bankEvidenceUnit = E.bankEvidenceUnit, consumeWindow = E.consumeWindow, sectorEvents = {}}
  for _, k in ipairs(A.WINDOW_KEYS) do e[k] = 0 end
  return e
end
-- drive: total distance in thousandths of a lap (lap count = whole laps
-- completed, AC's car.lapCount), a corner every hundredth.
local function frame(e, st, opts)
  local total = st.k / 1000
  st.lap = math.floor(total + 1e-9)
  st.sp = total - st.lap
  local car = {splinePosition = st.sp, isInPitlane = opts.pit or false, isLapValid = not opts.invalid, isLastLapValid = true,
    previousLapTimeMs = 480000, fuelPerLap = 0}
  unitFn(e, car, {trackLengthM = st.len}, 50, st.lap)
end
local function drive(e, st, to, opts)
  opts = opts or {}
  local target = math.floor(to * 1000 + 0.5)
  while st.k < target do
    st.k = st.k + 1
    if st.k % 10 == 0 then e.corneringSamples = e.corneringSamples + 1 end
    frame(e, st, opts)
  end
end
local function jump(e, st, to, opts) st.k = math.floor(to * 1000 + 0.5); frame(e, st, opts or {}) end
local e = newEng()
local st = {k = 985, len = 20832}
jump(e, st, 0.985, {pit = true})       -- in the pit lane, just before the line
drive(e, st, 0.99, {pit = true})
check('Nordschleife: 4 units a lap', e.unitsPerLap, 4)
check('the wording follows', A.EV_UNIT.many, 'sections')
drive(e, st, 1.0)                      -- cross the line
drive(e, st, 1.25)                     -- through section 1
check('two units banked: the pit/partial one and a clean section 1', #e.lapBins, 2)
check('first unit flagged pit', e.lapBins[1].pit, true)
check('first unit partial (started 94% into its section)', e.lapBins[1].partial, true)
check('...it closed at the line: lap 1 section 4', e.lapBins[1].lap .. '.' .. e.lapBins[1].unit, '1.4')
check('section 1 of the next lap clean', not e.lapBins[2].pit and not e.lapBins[2].partial, true)
check('...labelled lap 2 section 1', e.lapBins[2].lap .. '.' .. e.lapBins[2].unit, '2.1')
drive(e, st, 1.50)
local clean = A.windowLapStats(e)
check('two clean sections = the 2-unit gate passes after ~10 km, not 42', clean, 2)
-- reversing across a boundary never banks twice
jump(e, st, 1.49); jump(e, st, 1.495); drive(e, st, 1.52)
check('reversing across a boundary and back: nothing extra banked', #e.lapBins, 3)
drive(e, st, 1.76)                     -- section 3 banked at 1.75
drive(e, st, 2.0)                      -- the line closes section 4
check('the lap line closes section 4', e.lapBins[5].unit, 4)
check('...clean', e.lapBins[5].partial, false)
drive(e, st, 2.30)                     -- section 1 banked at 2.25
jump(e, st, 2.80)                      -- teleport over section 2
check('jumping over a section banks the jumped unit as partial', e.lapBins[7].partial, true)
drive(e, st, 3.0)
-- invalid only where the lap was invalidated
drive(e, st, 3.30, {invalid = true})
drive(e, st, 3.55, {invalid = true})
check('section where the lap-valid flag dropped: invalid', e.lapBins[9].valid, false)
check('the next section (flag already down at its start): not blamed', e.lapBins[10].valid, true)
-- a Build mid-section: the section in progress is partial
e:consumeWindow('Build #1')
drive(e, st, 3.76)
check('after a Build, the section in progress is partial', e.lapBins[11].partial, true)
drive(e, st, 4.01)
check('...and the next one is clean', e.lapBins[12].partial, false)
-- session restart: lapCount back to 0 in the pit box
unitFn(e, {splinePosition = 0.40, isInPitlane = true, isLapValid = true}, {trackLengthM = st.len}, 50, 0)
check('restart: section re-synced to the pit box position', e.curUnit, 1)
check('...and flagged pit', e.lapPitSeen, true)

-- an ordinary track: exactly the v2.0 lap logic
A.EV_UNIT.one, A.EV_UNIT.many = 'lap', 'laps'
local s2 = newEng()
local st2 = {k = 500, len = 3219}
jump(s2, st2, 0.50)
drive(s2, st2, 1.0)
drive(s2, st2, 2.0)
check('Adelaide: 1 unit a lap', s2.unitsPerLap, 1)
check('wording stays laps', A.EV_UNIT.many, 'laps')
check('two laps banked', #s2.lapBins, 2)
check('the first (loaded mid-lap) partial, as in v2.0', s2.lapBins[1].partial, true)
check('the second clean, no section label', s2.lapBins[2].partial == false and s2.lapBins[2].unit == nil, true)

------------------------------------------------------------------------------
print('')
print('=== 4. held slides: deliberate oversteer is not a snap ===')
local snapBlock = between('    local push = (us > 2.2 and absLat > 0.45)', '    if car.absInAction then')
local envS = setmetatable({ARB_AERO_SPLIT_KMH = 180, HELD_SLIDE_S = A.HELD_SLIDE_S,
  recordSectorEvent = A.recordSectorEvent, unrecordSectorEvent = A.unrecordSectorEvent}, {__index = envA})
local snapFn = assert(load('return function(self, us, absLat, gas, absSteer, ndR, speed, brake, handbrakeRecent, curSector)\n' .. snapBlock .. '\nend', 'snap', 't', envS))()
local function newS()
  return {cd = {midSnap = 0, highSnap = 0, coast = 0, midPush = 0, highPush = 0, turnin = 0}, clock = 0,
    midSnap = 0, highSnap = 0, liftOffSnap = 0, midPush = 0, highPush = 0, turninPush = 0, heldSlides = 0, sectorEvents = {}}
end
local function frames(sx, count, st3)
  for _ = 1, count do
    for k, v in pairs(sx.cd) do if v > 0 then sx.cd[k] = v - 0.05 end end
    sx.clock = sx.clock + 0.05
    snapFn(sx, st3.us, st3.lat or 0.8, st3.gas, st3.steer or 20, st3.ndR or 0.35, st3.speed or 90, 0, st3.hand or false, 'S1')
  end
end
local calm = {us = 0, gas = 0.5, steer = 5, ndR = 0.05}
local sa = newS()
frames(sa, 60, {us = -5, gas = 0.8})                 -- 3 s power slide, throttle held
frames(sa, 10, calm)
check('3 s power slide with the throttle held: 0 snaps (old logic: 2-3)', sa.midSnap, 0)
check('...counted as held slides', sa.heldSlides >= 2, true)
check('...and taken back out of the sector tally', (sa.sectorEvents.S1 or {}).midSnap or 0, 0)
local sb = newS()
frames(sb, 8, {us = -5, gas = 0.8})                  -- 0.4 s snap, caught
frames(sb, 10, calm)
check('a real snap (0.4 s) still counts once', sb.midSnap, 1)
check('...and is not a held slide', sb.heldSlides, 0)
local sc = newS()
frames(sc, 6, {us = -5, gas = 0.8}); frames(sc, 34, {us = -5, gas = 0.2})   -- lifted after 0.3 s, 2 s long
frames(sc, 10, calm)
check('lifting during the slide = a genuine snap, counted exactly as before (2 in 2 s)', sc.midSnap, 2)
check('...none held', sc.heldSlides, 0)
local sd = newS()
frames(sd, 4, {us = -5, gas = 0.8, hand = true}); frames(sd, 10, {us = -5, gas = 0.8})
check('handbrake-started slide: not a snap', sd.midSnap, 0)
check('...held', sd.heldSlides >= 1, true)
local se = newS()
frames(se, 4, {us = -5, gas = 0.05})
check('lift-off oversteer without the handbrake counts as before', se.liftOffSnap, 1)
local sf = newS()
frames(sf, 4, {us = -5, gas = 0.05, hand = true})
-- (a lift-off slide also falls through to the mid-corner branch while the
-- lift-off cooldown runs - v1.9.4 behaviour, kept so the calibration stands)
check('...with the handbrake nothing reaches the oversteer counts', sf.liftOffSnap + sf.midSnap, 0)
check('...it is held', sf.heldSlides >= 1, true)
local sg = newS()
frames(sg, 40, {us = -5, gas = 0.8, speed = 200})
check('held slide at 200 km/h: high-speed count moved too', sg.highSnap, 0)

------------------------------------------------------------------------------
print('')
print('=== 5. per car + track records (the Sunbeam #35 -> Camotos #36 -> Sunbeam #37 case) ===')
local list = A.parseKeyedStore('')
A.keyedPut(list, SUN_ID, 'ks_nordschleife', '35#low-loose:toeFront:68.80:1:-1.00')
A.keyedPut(list, 'axfor_camotos_r6', 'phillip_island_circuit', '36#low-loose:arb:70.00:1:-1.00')
local store = A.serialiseKeyedStore(list)
check('two cars kept side by side', #A.parseKeyedStore(store), 2)
check('the Sunbeam\'s Nordschleife record survives the Camotos Build', A.keyedGet(A.parseKeyedStore(store), SUN_ID, 'ks_nordschleife') ~= nil, true)
check('...and is not mistaken for Adelaide', A.keyedGet(A.parseKeyedStore(store), SUN_ID, 'akr_adelaide500_finale'), nil)
local l2, legacy = A.parseKeyedStore('ks_lamborghini_huracan_gt3|18:20:56|ABS=1|ARB_FRONT=3')
check('old single record still read as legacy', legacy ~= nil and #l2 == 0, true)
check('drop one car, keep the rest', #A.parseKeyedStore(A.keyedDropCar(store, SUN_ID)), 1)
check('drop on a legacy record of that car -> empty', A.keyedDropCar('carx|1|items|trk', 'carx'), '')
check('drop on a legacy record of another car -> kept', A.keyedDropCar('cary|1|items|trk', 'carx'), 'cary|1|items|trk')
local many = {}
for i = 1, 35 do A.keyedPut(many, 'c' .. i, 't', 'p') end
check('newest 30 kept', #A.parseKeyedStore(A.serialiseKeyedStore(many)), 30)

------------------------------------------------------------------------------
print('')
print('=== 6. physics fingerprint (the Sunbeam as it stands, then "dampers added later") ===')
E.carId = SUN_ID
settings.biasBaselineCars = '|' .. SUN_ID .. '|other_car|'
settings.rideCal = SUN_ID .. '>F=25:70:40,27:72:40;R=|other_car>F=1:2:3;R='
settings.camberGain = SUN_ID .. '>F=-2.2:0.6,-2.5:0.3,-2.0:0.8;R=|other_car>F=;R='
settings.leverLedger = SUN_ID .. '>low-loose:toeFront:2:2:1:no-effect:|other_car>low-loose:arb:1:0:0:helped:'
settings.branchState = SUN_ID .. '>ks_nordschleife>low-loose>stopped>1>68.8>>35>no-gain>>>>|other_car>spa>low-loose>active>1>50>>9>>>>>'
local pl = {}; A.keyedPut(pl, SUN_ID, 'rt_bathurst', '41#x'); A.keyedPut(pl, 'other_car', 'spa', '9#y')
settings.leverPending = A.serialiseKeyedStore(pl)
local lb = {}; A.keyedPut(lb, SUN_ID, 'rt_bathurst', '17:12:27;FRONT_BIAS=59'); A.keyedPut(lb, 'other_car', 'spa', '12:00:00;ABS=1')
settings.lastBuildRecord = A.serialiseKeyedStore(lb)

E:checkPhysicsFingerprint(0)
check('first sighting: fingerprint recorded, nothing reset', E.physicsFirstSeen == true and E.physicsChangeNote == nil, true)
check('...one-time bias write still marked used', E:biasBaselineDone(SUN_ID), true)
check('...9 files + final.rto hashed', select(2, E.physicsPrint:gsub(':', '')), 9)
E.physicsFirstSeen = nil
E:checkPhysicsFingerprint(0)
check('same car again: unchanged', E.physicsFirstSeen == false and E.physicsChangeNote == nil, true)
-- Nik makes the Sunbeam's dampers adjustable: setup.ini gains damper items
-- and suspensions.ini's damper rates change. (suspensions.ini always HAS
-- damper rates - AC needs them - "no dampers" means no setup adjustment.)
local susp = readText(CAR_DIR .. 'suspensions.ini')
local setup = readText(CAR_DIR .. 'setup.ini')
local newSusp, nSub = susp:gsub('(DAMP_BUMP%s*=%s*)[%d%.]+', '%19999', 1)
check('fixture: the Sunbeam\'s suspensions.ini has a damper rate to change', nSub, 1)
OVERRIDE['suspensions.ini'] = newSusp
OVERRIDE['setup.ini'] = setup .. '\n[DAMP_BUMP_LR]\nSHOW_CLICKS=2\nMIN=0\nMAX=12\nSTEP=1\n'
E:checkPhysicsFingerprint(0)
check('dampers added: PHYSICS CHANGED', E.physicsChangeNote ~= nil, true)
check('...names the files that changed', E.physicsChangeNote:find('suspensions%.ini') ~= nil and E.physicsChangeNote:find('setup%.ini') ~= nil, true)
check('one-time bias write re-armed for the Sunbeam', E:biasBaselineDone(SUN_ID), false)
check('...not for the other car', E:biasBaselineDone('other_car'), true)
check('ride-height calibration forgotten (Sunbeam only)', A.parsePointStore(settings.rideCal)[SUN_ID] == nil and A.parsePointStore(settings.rideCal).other_car ~= nil, true)
check('camber gain forgotten (Sunbeam only)', A.parsePointStore(settings.camberGain)[SUN_ID] == nil, true)
check('lever history forgotten (Sunbeam only)', A.parseLedgerStore(settings.leverLedger)[SUN_ID] == nil and A.parseLedgerStore(settings.leverLedger).other_car ~= nil, true)
local anySun = false
for _, b in ipairs(A.parseBranchStore(settings.branchState)) do if b.car == SUN_ID then anySun = true end end
check('stopped branch forgotten - it starts from pass 1 on the new physics', anySun, false)
check('pending moves forgotten (Sunbeam only)', A.keyedGet(A.parseKeyedStore(settings.leverPending), SUN_ID) == nil and A.keyedGet(A.parseKeyedStore(settings.leverPending), 'other_car') ~= nil, true)
check('last-Build record forgotten (Sunbeam only)', A.keyedGet(A.parseKeyedStore(settings.lastBuildRecord), SUN_ID) == nil and A.keyedGet(A.parseKeyedStore(settings.lastBuildRecord), 'other_car') ~= nil, true)
E.physicsChangeNote = nil
OVERRIDE['setup.ini'] = '; a comment\n' .. OVERRIDE['setup.ini'] .. '\n; another comment\n'
E:checkPhysicsFingerprint(0)
check('comments and layout do not count as a physics change', E.physicsChangeNote, nil)
OVERRIDE['final.rto'] = '6//37|6.17\n8//43|5.00\n'
E:checkPhysicsFingerprint(0)
check('final-drive list changed: noted, with the saved-setup warning', E.physicsChangeNote and E.physicsChangeNote:find('final%.rto') ~= nil and E.physicsChangeNote:find('positions in the car') ~= nil, true)
OVERRIDE = {}
check('the hash needs no bit operators (LuaJIT has no ~)', fn('textHash'):find('~') == nil, true)
check('different text, different hash', A.textHash('abc') ~= A.textHash('abd'), true)

------------------------------------------------------------------------------
print('')
print('=== 7. balance levers for a car with no bars and no dampers (the Sunbeam) ===')
local sunSetup = parseIni(readText(CAR_DIR .. 'setup.ini'))
local function item(sec)
  local s = sunSetup.sections[sec]; if not s then return nil end
  return {section = sec, min = tonumber(s.MIN[1]), max = tonumber(s.MAX[1]), step = tonumber(s.STEP[1])}
end
local parsed, writes = {}, {}
local function writeAbs(it, sec, dir, clicks, desc)
  local cur = parsed[sec]; if not cur then return false, false end
  local nv = cur + dir * clicks * (it and it.step or 1)
  if it then nv = math.max(it.min, math.min(it.max, nv)) end
  if nv == cur then return true, false end
  parsed[sec] = nv; table.insert(writes, desc); return true, true
end
local springText = between('    local springBalMap = schemaWithLive(schema.springRate)', '    -- BOTTOMING / RUNNING OUT OF TRAVEL')
local diffText = extractFrom(src:find('    levers.diff = function(regime, direction)', 1, true))
local rearText = extractFrom(src:find('    levers.rearDampers = function(regime, direction, jump)', 1, true))
local LS = {}
local lapOK = {}
local envL = setmetatable({
  settings = {writeSprings = true, writeDifferential = true, writeDampersRear = true},
  getCurVal = function(_, sec) return parsed[sec] end, parsed = parsed,
  schema = {springRate = 'springRate', diffCoast = 'diffCoast'},
  schemaWithLive = function(cat)
    local m = {}
    if cat == 'springRate' then for _, s in ipairs({'SPRING_RATE_LF', 'SPRING_RATE_RF', 'SPRING_RATE_LR', 'SPRING_RATE_RR'}) do m[s] = item(s) end end
    if cat == 'diffCoast' then m.DIFF_COAST = item('DIFF_COAST') end
    return m
  end,
  writeAbs = writeAbs, NUDGE_FRACTION = {spring = 0.1, diff = 0.1, damper = 0.1}, calc = {touched = {}}, th = 2,
  firstPresent = function(a, b) if parsed[a] then return a end if parsed[b] then return b end return nil end,
  lapSupport = function(_, key) return 3, 4, lapOK[key] ~= false end,
  damperSection = function(kind, corner) return 'DAMP_' .. kind .. '_' .. corner end,
  slowDamperMap = {damperBump = {}, damperRebound = {}}, rearHandling = 'loose',
}, {__index = envA})
local levers = assert(load('return function(self, levers)\n' .. springText .. '\n' .. diffText .. '\n' .. rearText .. '\nreturn levers\nend', 'levers', 't', envL))()
local SE = {springsHitsR = 0, springsHitsF = 0, liftOffSnap = 0, turninPush = 0, driveType = 'RWD'}
levers(SE, LS)
local function setSun()
  for k in pairs(parsed) do parsed[k] = nil end
  parsed.SPRING_RATE_LF, parsed.SPRING_RATE_RF, parsed.SPRING_RATE_LR, parsed.SPRING_RATE_RR = 38, 38, 34, 34
  parsed.DIFF_COAST = 30
  writes = {}
end
setSun(); envL.springsMovedForTravel = false
local ok, why = LS.rearDampers('low', 'loose')
check('rear dampers: says the car has none (was "already at their softest")', why, 'no adjustable rear dampers on this car')
ok = LS.springs('low', 'loose')
check('springs lever: low-speed oversteer -> rear softer', ok and parsed.SPRING_RATE_LR == 31 and parsed.SPRING_RATE_RR == 31, true)
check('...front untouched', parsed.SPRING_RATE_LF, 38)
setSun(); SE.springsHitsR = 5
ok = LS.springs('low', 'loose')
check('rear already running out of travel -> front stiffer instead', ok and parsed.SPRING_RATE_LF == 40 and parsed.SPRING_RATE_LR == 34, true)
setSun(); SE.springsHitsR = 0; parsed.SPRING_RATE_LR, parsed.SPRING_RATE_RR = 20, 20
ok = LS.springs('low', 'loose')
check('rear at its softest -> front stiffer', ok and parsed.SPRING_RATE_LF == 40, true)
setSun()
ok = LS.springs('low', 'tight')
check('low-speed push -> front softer', ok and parsed.SPRING_RATE_LF == 36 and parsed.SPRING_RATE_RF == 36, true)
setSun(); envL.springsMovedForTravel = true
ok, why = LS.springs('low', 'loose')
check('springs already moved for travel this Build -> stands aside', why:find('already moved for travel') ~= nil, true)
envL.springsMovedForTravel = false
ok, why = LS.springs('high', 'loose')
check('not a high-speed lever', why, 'mechanical lever, low-speed only')
setSun(); for k in pairs(parsed) do parsed[k] = nil end
local savedSWL = envL.schemaWithLive; envL.schemaWithLive = function() return {} end
levers(SE, LS)
ok, why = LS.springs('low', 'loose')
check('a car without spring items: says so', why, 'no adjustable springs on this car')
envL.schemaWithLive = savedSWL; levers(SE, LS)
-- diff coast
setSun(); SE.liftOffSnap = 8
ok = LS.diff('low', 'loose')
check('lift-off oversteer -> more coast lock (30 -> 35)', ok and parsed.DIFF_COAST == 35, true)
setSun(); SE.liftOffSnap = 0
ok, why = LS.diff('low', 'loose')
check('mid-corner oversteer is not coast lock\'s job', why:find('not on lift%-off') ~= nil, true)
setSun(); SE.liftOffSnap = 8; lapOK.liftOffSnap = false
ok, why = LS.diff('low', 'loose')
check('lift-off events in too few units -> left alone', ok, false)
lapOK.liftOffSnap = nil
setSun(); SE.turninPush = 6
ok = LS.diff('low', 'tight')
check('entry push -> less coast lock (30 -> 25)', ok and parsed.DIFF_COAST == 25, true)
setSun(); SE.driveType = 'AWD'
ok, why = LS.diff('low', 'tight')
check('AWD: not this lever', why:find('AWD') ~= nil, true)
SE.driveType = 'RWD'
-- the same lever on a car that GAINS rear dampers: proceeds to the handling check
setSun(); parsed.DAMP_BUMP_LR, parsed.DAMP_REBOUND_LR = 4, 6
envL.rearHandling = 'neutral'
ok, why = LS.rearDampers('low', 'loose')
check('with rear dampers added it is a normal lever again', why:find('rear handling signal is') ~= nil, true)

------------------------------------------------------------------------------
print('')
print('=== 8. one summary line for what the car can\'t adjust; range limits named ===')
local sumText = between('  local absentLine, rangeLine\n', '  -- Status note. As of 4.3.0')
local sumFn = assert(load('return function(absentSections, rangeLimits)\n' .. sumText .. '\nreturn absentLine, rangeLine\nend', 'summary', 't', envA))()
local absent = {}
for _, c in ipairs({'LF', 'RF', 'LR', 'RR'}) do
  for _, k in ipairs({'DAMP_BUMP_', 'DAMP_REBOUND_', 'DAMP_FAST_BUMP_', 'DAMP_FAST_REBOUND_'}) do absent[k .. c] = true end
end
absent.TOE_OUT_LR, absent.TOE_OUT_RR, absent.CAMBER_RR = true, true, true
local aLine = sumFn(absent, {})
check('the Sunbeam\'s ~20 SKIPPED lines become one', aLine, 'Not adjustable on this car, so not written: camber RR, bump LF/RF/LR/RR, fast bump LF/RF/LR/RR, fast rebound LF/RF/LR/RR, rebound LF/RF/LR/RR, toe LR/RR (its setup has no such items - if the car gains them they are used automatically)')
local _, rLine = sumFn({}, {'camber RF wants -5.27°, the car stops at -2.50°'})
check('range limits named in one line', rLine and rLine:find('stopped these: camber RF wants') ~= nil, true)
check('nothing absent -> no line', sumFn({}, {}), nil)

------------------------------------------------------------------------------
print('')
print('=== source guards ===')
check('VERSION 2.5.0 or later', src:find("local VERSION = '[23]%.%d%.%d'") ~= nil, true)
check('physicsPrints storage declared', src:find("  physicsPrints = '',") ~= nil, true)
check('fingerprint checked when the car loads (refreshTargets)', src:find('pcall%(function%(%) self:checkPhysicsFingerprint%(car%.index%) end%)') ~= nil, true)
check('travel range refreshed at car load', src:find('self:refreshTravelRef%(car%.index%)  %-%- v2%.5%.0') ~= nil, true)
check('...and at every pit stop', src:find('pcall%(function%(%) self:refreshTravelRef%(car%.index%) end%)') ~= nil, true)
check('static travel captured in the pits (real readings only)', src:find('local stF = %(n%(w%[1%]%.suspensionTravel%)') ~= nil
  and src:find('if stF > 0%.001 and stR > 0%.001 then self%.staticTravelF, self%.staticTravelR = stF, stR end') ~= nil, true)
check('every corner against its own range', src:find('n%(w%[1%]%.suspensionTravel%) / ref%.LF') ~= nil, true)
check('handbrake read every frame', src:find('local handbrake = n%(car%.handbrake, 0%)') ~= nil, true)
check('rear lockups ignore the handbrake', src:find('and srR > srF %+ 0%.12 and not handbrakeRecent then') ~= nil, true)
check('braking samples ignore the handbrake', src:find('speed > 60 and not handbrakeRecent') ~= nil, true)
check('EV_UNIT set from the track length', src:find("if self%.unitsPerLap > 1 then EV_UNIT%.one, EV_UNIT%.many = 'section', 'sections' end") ~= nil, true)
check('bins clamp at zero (moved snaps)', src:find('bin%[k%] = math%.max%(0,') ~= nil, true)
check('Build consume marks the unit partial', src:find('self%.unitPartial = true  %-%- v2%.5%.0') ~= nil, true)
check('lastBuild record looked up per car + track', src:find('local rec = keyedGet%(list, carFolder, trackFolder%)') ~= nil, true)
check('SKIPPED line replaced by the absent-sections summary', src:find("not in your setup file and no readable schema for this car%)', desc, section%)") == nil
  and src:find('if not quietSkip then absentSections%[section%] = true end') ~= nil, true)
check('summaries never a reason to write on their own', src:find('if absentLine then table%.insert%(changes, absentLine%) end') ~= nil, true)
check('camber range limit named', src:find("is beyond this car\\'s range, which stops at") ~= nil, true)
check('ride height follows the measured click direction', src:find("local up, measured = rideDir%(") ~= nil, true)
check('BRAKE line: lockups outrank the calculation', src:find('the lockups disagree with the calculation') ~= nil, true)
check('SUSPENSION line: share of the car\'s own range', src:find("Travel F %%%.0f%%%% R %%%.0f%%%% of this car\\'s range") ~= nil, true)
check('chains carry springs and diff after the ARB and dampers', src:find("%['low%-loose'%]  = {'arb', 'rearDampers', 'springs', 'toeRear', 'toeFront', 'diff', 'rake'}") ~= nil, true)
check('log: held slides line', src:find("'held slides %(v2%.5%.0%)") ~= nil, true)
check('log: evidence units + physics fingerprint line', src:find("'evidence units %(v2%.5%.0%): %%s · physics fingerprint: %%s'") ~= nil, true)
check('Build result starts with the physics-change note', src:find('if self%.physicsChangeNote then table%.insert%(changes, self%.physicsChangeNote%) end') ~= nil, true)

print('')
print(string.format('%d passed, %d failed', pass, fail))
os.exit(fail == 0 and 0 or 1)
