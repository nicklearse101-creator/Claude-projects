-- v2.5.2: five bugs found reviewing the 57 v2.5.1 Builds of 29 Sep - 4 Oct
-- 2026 (Sunbeam live / v6 backup / +10% copy, Huracan GT3 Evo2 and Audi R8
-- LMS Evo II at Imola). The shipped functions and blocks are extracted from
-- the app and run against the numbers those Builds logged.

local appPath = arg[1] or 'D:/SteamLibrary/steamapps/common/assettocorsa/apps/lua/setupcoach/SetupCoach.lua'
local f = assert(io.open(appPath, 'r'))
local src = f:read('a')
f:close()

local pass, fail = 0, 0
local function check(label, got, want)
  if got == want then pass = pass + 1; print(string.format('  PASS  %-84s %s', label, tostring(got)))
  else fail = fail + 1; print(string.format('  FAIL  %-84s got %s want %s', label, tostring(got), tostring(want))) end
end
local function near(label, got, want, tol)
  local ok = type(got) == 'number' and math.abs(got - want) <= tol
  if ok then pass = pass + 1; print(string.format('  PASS  %-84s %.4f', label, got))
  else fail = fail + 1; print(string.format('  FAIL  %-84s got %s want %.4f±%.4f', label, tostring(got), want, tol)) end
end

------------------------------------------------------------------------------
-- Extraction (as test_v250): function / if / do counted against end, with
-- escapes, comments and strings stripped first.
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
local function between(startMarker, endMarker)
  local s = src:find(startMarker, 1, true); assert(s, 'marker ' .. startMarker)
  local e = src:find(endMarker, s + #startMarker, true); assert(e, 'end marker ' .. endMarker)
  return src:sub(s, e - 1)
end

local SPINNERS, FUEL = {}, 30
ac = {getSetupSpinners = function() return SPINNERS end, getCar = function() return {fuel = FUEL} end}
local settings = {rideCal = '', physicsPrints = '', biasBaselineCars = ''}
local env = {math = math, string = string, table = table, pairs = pairs, ipairs = ipairs, tostring = tostring,
  tonumber = tonumber, type = type, next = next, pcall = pcall, ac = ac, settings = settings}
local chunk = 'local engine = {}\n'
chunk = chunk .. '\nlocal settings = settings or {}\n' .. assert(src:match('\n%-%- BALANCE MODES BEGIN.-%-%- BALANCE MODES END'), 'balance modes block') .. '\n'
for _, c in ipairs({'PHYSICS_KEEP_CARS', 'RIDE_CAL_MIN_PAIRS', 'RIDE_CAL_MIN_SLOPE'}) do
  chunk = chunk .. const(c) .. '\n'
end
-- the fingerprint itself is stubbed: these tests are about the flag, not the hash
chunk = chunk .. 'local PRINT = {now = "p1"}\nlocal function physicsPrintOf() return PRINT.now end\n'
  .. 'function engine:forgetLearned() self.forgotten = (self.forgotten or 0) + 1 end\n'
for _, name in ipairs({'n', 'windowBins', 'lapSupport', 'travelHitsConsistent', 'tyreBrakeForce',
    'parsePointStore', 'serialisePointStore'}) do
  chunk = chunk .. fn(name) .. '\n'
end
for _, m in ipairs({'biasTarget', 'rideCalRecord', 'rideCalSlope', 'checkPhysicsFingerprint'}) do
  chunk = chunk .. method(m) .. '\n'
end
chunk = chunk .. 'return {engine = engine, PRINT = PRINT, n = n, lapSupport = lapSupport, travelHitsConsistent = travelHitsConsistent, '
  .. 'tyreBrakeForce = tyreBrakeForce, parsePointStore = parsePointStore, serialisePointStore = serialisePointStore}\n'
local A = assert(load(chunk, 'chunk', 't', env))()
local E = A.engine

------------------------------------------------------------------------------
print('=== 1. RESET TELEMETRY re-reads the car (16 Builds measured travel against a made-up 120 mm) ===')
check('reset() marks the car data stale', method('reset'):find('self.carDataStale = true', 1, true) ~= nil, true)
local early = src:match('\n(%s*if not self%.carDataStale and carId == self%.carId and compound == self%.compound and self%.targetF > 0 then return end)')
check('refreshTargets only skips the re-read when the data is not stale', early ~= nil, true)
if early then
  local gate = assert(load('return function(self, carId, compound)\n' .. early .. '\nreturn "reread"\nend'))()
  check('same car, data fresh -> skipped (the per-frame fast path)', gate({carId = 'sunbeam', compound = 'V70', targetF = 37}, 'sunbeam', 'V70'), nil)
  check('same car after RESET TELEMETRY -> re-read', gate({carId = 'sunbeam', compound = 'V70', targetF = 37, carDataStale = true}, 'sunbeam', 'V70'), 'reread')
  check('different car -> re-read (as before)', gate({carId = 'sunbeam', compound = 'V70', targetF = 37}, 'audi', 'V70'), 'reread')
end
local rt = method('refreshTargets')
check('...and refreshTargets clears the flag once it has re-read', rt:find('self.carDataStale = false', 1, true) ~= nil, true)
check('the travel range is re-read in that pass (refreshTravelRef)', rt:find('self:refreshTravelRef(car.index)', 1, true) ~= nil, true)

------------------------------------------------------------------------------
print('')
print('=== 2. dampers stiffened "for bottoming" on max-travel hits the same Build called inconsistent ===')
local function bins(spec)   -- spec: list of springsHitsR per clean lap
  local b = {}
  for i, hits in ipairs(spec) do b[i] = {springsHitsR = hits, springsHitsF = 0, corneringSamples = 70} end
  return {lapBins = b, windowBinsStart = 0}
end
-- Huracan Evo2, Build #65: "Rear springs: max-travel hits seen in only 3 of 7 laps - not a consistent
-- trait, left alone" - and in the same Build "Rear bump LR (stiffer, bottoming needs support)".
local evo = bins({3, 0, 2, 0, 4, 0, 1})
local a, c, ok = A.lapSupport(evo, 'springsHitsR')
check('the springs writer\'s own test: 3 of 7 laps -> not consistent', ok, false)
check('the damper gate agrees: 10 hits but 3 of 7 laps -> no "bottoming" stiffen', A.travelHitsConsistent(evo, 'springsHitsR', 10, 2), false)
local real = bins({3, 2, 2, 0, 4, 2, 1})
check('5 of 7 laps -> consistent, the stiffen may run', A.travelHitsConsistent(real, 'springsHitsR', 14, 2), true)
check('count at the threshold -> no stiffen, whatever the laps say', A.travelHitsConsistent(real, 'springsHitsR', 2, 2), false)
check('under 2 clean laps -> passes through, like every lapSupport consumer', A.travelHitsConsistent(bins({5}), 'springsHitsR', 5, 2), true)
check('slow dampers no longer read the raw max-travel count', src:find('bottom=self%.springsHits[FR]>th') == nil, true)
check('front axle goes through the gate', src:find("travelHitsConsistent(self, 'springsHitsF', self.springsHitsF, th)", 1, true) ~= nil, true)
check('rear axle goes through the gate', src:find("travelHitsConsistent(self, 'springsHitsR', self.springsHitsR, th)", 1, true) ~= nil, true)

------------------------------------------------------------------------------
print('')
print('=== 3. brake bias: airborne-wheel samples, the load-only fallback, the overridden gate ===')
-- The Sunbeam's own V70 tyres (tyres.ini VERSION 10).
local mF = {kind = 'ls', dxRef = 1.37, fz0 = 1749, lsx = 0.7203}
local mR = {kind = 'ls', dxRef = 1.37, fz0 = 2006, lsx = 0.7313}
check('an unloaded wheel has no grip-model force', A.tyreBrakeForce(mF, 0), nil)
local brakeBlock = between('  -- v2.3.0: HARD STRAIGHT-LINE BRAKING', '  -- v2.3.0: DYNAMIC FRONT RIDE HEIGHT')
local brakeFn = assert(load('return function(self, onTrack, brake, longG, absSteer, absLat, speed, handbrakeRecent, w)\n'
  .. brakeBlock .. '\nend', 'brake', 't', setmetatable({tyreBrakeForce = A.tyreBrakeForce, n = A.n}, {__index = _G})))()
local S = {brakeModelF = mF, brakeModelR = mR, tyreRadiusF = 0.295, tyreRadiusR = 0.295}
local loaded = {{load = 3600}, {load = 3600}, {load = 1700}, {load = 1700}}
local hop = {{load = 3900}, {load = 3800}, {load = 0}, {load = 2500}}   -- a rear wheel off the ground over a crest
-- England rally stage, Build #99: 5 braking zones, samples over crests among them.
for zone = 1, 5 do
  for _ = 1, 5 do brakeFn(S, true, 0.95, -1.1, 2, 0.05, 120, false, loaded) end
  for _ = 1, 3 do brakeFn(S, true, 0.95, -1.1, 2, 0.05, 120, false, hop) end
  brakeFn(S, true, 0, 0, 0, 0, 120, false, loaded)
end
check('5 zones counted', S.brkZones, 5)
check('a sample with a wheel in the air is not a braking-balance sample', S.brkLoadN, 25)
check('...for the grip sums either - the two counts stay equal', S.brkCapN, S.brkLoadN)
local tgt, why = E.biasTarget(S)
check('25 samples -> no target yet (it was a load-only 69.8% with 40 samples)', tgt, nil)
-- belt and braces: a tyre WITH a grip model never falls back to load alone
local T = {brakeModelF = mF, brakeModelR = mR, brkLoadN = 40, brkZones = 5, brkLoadFSum = 40 * 0.688,
  brkCapN = 12, brkCapFSum = 12 * 7000, brkCapRSum = 12 * 4000, tyreRadiusF = 0.295, tyreRadiusR = 0.295}
local t2, why2 = E.biasTarget(T)
check('grip model on the car, too few grip samples -> no target', t2, nil)
check('...and the reason names the grip model', tostring(why2):find('grip', 1, true) ~= nil, true)
local U = {brkLoadN = 40, brkZones = 5, brkLoadFSum = 40 * 0.688, brkCapN = 0, tyreRadiusF = 0.3, tyreRadiusR = 0.3}
local t3 = E.biasTarget(U)
near('a tyre with NO grip model still gets the load split (68.8% + 1%)', t3, 69.8, 0.05)
check('the one-time decision waits when the gate was overridden',
  src:find("elseif gateOverridden then\n      table.insert(changes, string.format('Brake bias: calculated %.1f%% - the one-time write waits", 1, true) ~= nil, true)

------------------------------------------------------------------------------
print('')
print('=== 4. ride-height direction: one noisy pair, and pairs across spring changes ===')
-- point store: a 4th field (the axle's spring setting), old points still read
local all = A.parsePointStore('sunbeam>F=27.0000:63.1000:30.00,29.0000:64.3000:30.00;R=|old>F=1.0000:50.0000;R=')
check('legacy 3-field point still parses (no spring)', all.sunbeam.F[1][4], nil)
check('legacy 2-field point still parses', all.old.F[1][2], 50)
local all2 = A.parsePointStore(A.serialisePointStore({car = {F = {{27, 63.1, 30, 46}}, R = {}}}, 6))
check('spring setting round-trips through the store', all2.car.F[1][4], 46)
check('...beside setting, mm and fuel', all2.car.F[1][1] == 27 and all2.car.F[1][2] == 63.1 and all2.car.F[1][3] == 30, true)
-- rideCalRecord stores the spring with the point
SPINNERS = {{name = 'ROD_LENGTH_LF', value = 27}, {name = 'SPRING_RATE_LF', value = 46},
  {name = 'ROD_LENGTH_LR', value = 5}, {name = 'SPRING_RATE_LR', value = 40}}
local R = {carId = 'sunbeam', staticRideHeightF = 0.0631, staticRideHeightR = 0.0712}
settings.rideCal = ''
E.rideCalRecord(R)
check('a pit stop records the front spring with the point', settings.rideCal:find('F=27.0000:63.1000:30.00:46', 1, true) ~= nil, true)
check('...and the rear', settings.rideCal:find('R=5.0000:71.2000:30.00:40', 1, true) ~= nil, true)
local function slopeOf(points)
  local entry = {F = points, R = {}}
  settings.rideCal = A.serialisePointStore({sunbeam = entry}, 6)
  return E.rideCalSlope({carId = 'sunbeam'}, 'F')
end
-- Sunbeam, Bathurst 30 Sep: +0.60 mm/click (1 pair) -> -0.09 (1 pair) -> +0.46: the Build "raised" the
-- front 27->29, then 29->27, then 27->29. Springs moved 36->40->44->48 between those stops.
local s1, p1, ok1 = slopeOf({{27, 60.0, 30, 36}, {29, 61.2, 30, 40}})
check('a pair across a spring change is not a ride-height pair', p1, 0)
check('...so the direction is not "measured"', ok1, false)
local s2, p2, ok2 = slopeOf({{27, 60.0, 30, 46}, {29, 61.2, 30, 46}})
check('one same-spring pair: slope computed', p2, 1)
check('...but one pair is not enough to trust its sign', ok2, false)
local s3, p3, ok3 = slopeOf({{25, 58.0, 30, 46}, {27, 59.9, 30, 46}, {29, 62.1, 30, 46}})
check('three same-spring settings: 3 pairs', p3, 3)
check('...all agreeing -> reliable', ok3, true)
near('...median slope', s3, 1.025, 0.001)
local _, _, ok4 = slopeOf({{25, 58.0, 30, 46}, {27, 59.0, 30, 46}, {29, 58.6, 30, 46}})
check('pairs disagreeing on the sign -> not reliable', ok4, false)
local _, _, ok5 = slopeOf({{25, 58.0, 30, 46}, {27, 58.2, 30, 46}, {29, 58.3, 30, 46}})
check('under 0.3 mm a click is settling noise, not a measurement', ok5, false)
local _, p6 = slopeOf({{25, 58.0, 30, 46}, {29, 62.0, 10, 46}})
check('fuel more than 5 L apart -> not a pair (as before)', p6, 0)
local _, _, okLegacy = slopeOf({{25, 58.0, 30}, {27, 59.9, 30}, {29, 62.1, 30}})
check('old points without a spring still pair with each other', okLegacy, true)
check('the bottoming raise follows only a reliable direction',
  src:find('local slope, _, reliable = self:rideCalSlope(front and \'F\' or \'R\')', 1, true) ~= nil, true)
check('the ride-height target needs a reliable calibration too (v2.6.0: the floor step, both ends)',
  src:find('local slopeF, pairsF, reliableF = self:rideCalSlope(\'F\')', 1, true) ~= nil
  and src:find('if not (a.reliableF and a.reliableR and a.slopeF and a.slopeR) then', 1, true) ~= nil, true)

------------------------------------------------------------------------------
print('')
print('=== 5. pressure with no template file ignored the live setup ===')
-- Huracan Evo2, Build #62: template=none, live PRESSURE_LF=18, hot 23.5 vs target 26 -> wrote 28.5 cold.
check('the pressure base is the value on the car (template or live), not "template only"',
  src:find('local baseVal = getCurVal(parsed, it.section)\n', 1, true) ~= nil, true)
check('the old template-only gate is gone', src:find('local baseVal = usedBase and getCurVal', 1, true) == nil, true)
near('Build #62 with the live base: 18 + (26.0 - 23.5) = 20.5 cold (it wrote 28.5)', 18 + (26.0 - 23.5), 20.5, 1e-9)

------------------------------------------------------------------------------
print('')
print('=== 6. log wording: "first time this car is seen", diff "backing up" a preload that never moved ===')
settings.physicsPrints = ''
local P = {carId = 'audi', forgetLearned = E.forgetLearned}
A.PRINT.now = 'a1'
E.checkPhysicsFingerprint(P, 0)
check('first sighting -> first seen', P.physicsFirstSeen, true)
E.checkPhysicsFingerprint(P, 0)   -- re-run in the same session (compound change, or RESET re-read)
check('a re-run before any Build reports it keeps "first seen"', P.physicsFirstSeen, true)
P.physicsFirstSeen = false        -- what the Build does once it has logged it
E.checkPhysicsFingerprint(P, 0)
check('after the Build reported it -> "unchanged" from then on', P.physicsFirstSeen, false)
P.carId = 'sunbeam'
A.PRINT.now = 's1'
E.checkPhysicsFingerprint(P, 0)
check('switching to another car never inherits the flag (new car -> first seen)', P.physicsFirstSeen, true)
P.physicsFirstSeen = false
P.carId = 'audi'
A.PRINT.now = 'a1'
E.checkPhysicsFingerprint(P, 0)
check('...and back to a known car -> not first seen', P.physicsFirstSeen, false)
check('the Build clears the flag when it commits', src:find('self.physicsFirstSeen = false  -- v2.5.2', 1, true) ~= nil, true)
check('"to back up the preload increase" only when the preload actually moved',
  src:find("preCh and 'Diff power (more lock, to back up the preload increase)'", 1, true) ~= nil, true)

print('')
print(string.format('%d passed, %d failed', pass, fail))
os.exit(fail == 0 and 0 or 1)
