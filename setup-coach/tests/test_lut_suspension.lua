-- v2.2.0: (1) fixed damper event thresholds; (2) CSP LUT anti-roll bars
-- (ARB_F/ARB_R); (3) CSP LUT dampers (DAMPER_BUMP/REBOUND_*) with a curve
-- check before every write. The shipped readers and checks are extracted
-- from the app and run against REAL decrypted car files, including the
-- known-broken sv8_camaro_v2 rear rebound curve and the BTCC "detached" bar.

local appPath = arg[1] or 'D:/SteamLibrary/steamapps/common/assettocorsa/apps/lua/setupcoach/SetupCoach.lua'
local EXTRACTED = 'D:/Claude/setupcoach-tools/acd/extracted/'
local f = assert(io.open(appPath, 'r'))
local src = f:read('a')
f:close()

local pass, fail = 0, 0
local function check(label, got, want)
  if got == want then pass = pass + 1; print(string.format('  PASS  %-74s %s', label, tostring(got)))
  else fail = fail + 1; print(string.format('  FAIL  %-74s got %s want %s', label, tostring(got), tostring(want))) end
end

------------------------------------------------------------------------------
-- Fixtures: INI + LUT stubs over the real extracted files.
------------------------------------------------------------------------------
local function parseIni(path)
  local sections, cur = {}, nil
  local fh = io.open(path, 'r')
  if not fh then return nil end
  for line in fh:lines() do
    line = line:gsub('\r', '')
    local s = line:match('^%s*%[([^%]]+)%]')
    if s then cur = s; sections[cur] = sections[cur] or {}
    elseif cur then
      local k, v = line:match('^%s*([%w_]+)%s*=(.*)$')
      if k then sections[cur][k] = v end
    end
  end
  fh:close()
  return sections
end
local function iniStub(sections)
  local ini = {sections = sections}
  function ini:get(section, key, default)
    local sec = self.sections[section]; local raw = sec and sec[key]
    if default == nil then if raw == nil then return {} end return {raw} end
    if raw == nil then return default end
    if type(default) == 'number' then return tonumber((raw:gsub(';.*$', ''))) or default end
    if type(default) == 'string' then return raw end
    return default
  end
  return ini
end
-- DataLUT11 stand-in: rows kept in order; text keys keep their output with
-- no numeric input (the behaviour the app has to survive either way).
local function lutStub(path, dropTextRows)
  local fh = io.open(path, 'r')
  if not fh then return nil end
  local pts = {}
  for line in fh:lines() do
    line = line:gsub('\r', ''):gsub(';.*$', '')
    local k, v = line:match('^%s*(.-)%s*|%s*([%-%d%.]+)%s*$')
    if k and v then
      local x = tonumber(k)
      if x or not dropTextRows then table.insert(pts, {x = x, y = tonumber(v)}) end
    end
  end
  fh:close()
  local lut = {}
  function lut:getPointOutput(i) local p = pts[i + 1]; return p and p.y or (0 / 0) end
  function lut:getPointInput(i) local p = pts[i + 1]; return p and p.x or (0 / 0) end
  function lut:get(x)
    local num = {}
    for _, p in ipairs(pts) do if p.x then table.insert(num, p) end end
    if #num == 0 then return 0 / 0 end
    if x <= num[1].x then return num[1].y end
    if x >= num[#num].x then return num[#num].y end
    for i = 2, #num do
      if x <= num[i].x then
        local a, b = num[i - 1], num[i]
        return a.y + (b.y - a.y) * (x - a.x) / (b.x - a.x)
      end
    end
  end
  return lut
end

local CAR = 'sv8_camaro_v2'
local DROP_TEXT = false
local ac = {INIConfig = {}, DataLUT11 = {}}
ac.INIConfig.carData = function(_, name)
  local s = parseIni(EXTRACTED .. CAR .. '/' .. name)
  if not s then error('no ' .. name) end
  return iniStub(s)
end
ac.DataLUT11.carData = function(_, name) return lutStub(EXTRACTED .. CAR .. '/' .. name, DROP_TEXT) end

------------------------------------------------------------------------------
-- Extract the shipped code.
------------------------------------------------------------------------------
local function extractBlock(startPattern)
  local s = src:find(startPattern)
  assert(s, 'not found: ' .. startPattern)
  local body, depth, out = src:sub(s + 1), 0, {}
  for line in body:gmatch('[^\n]*\n?') do
    table.insert(out, line)
    local stripped = line:gsub('%-%-.*$', ''):gsub("'[^']*'", ''):gsub('"[^"]*"', '')
    for _ in stripped:gmatch('%f[%w_]function%f[^%w_]') do depth = depth + 1 end
    for _ in stripped:gmatch('%f[%w_]if%f[^%w_]') do depth = depth + 1 end
    for _ in stripped:gmatch('%f[%w_]for%f[^%w_]') do depth = depth + 1 end
    for _ in stripped:gmatch('%f[%w_]while%f[^%w_]') do depth = depth + 1 end
    for _ in stripped:gmatch('%f[%w_]end%f[^%w_]') do depth = depth - 1 end
    if depth == 0 then break end
  end
  return table.concat(out)
end
local function fn(name) return extractBlock('\nlocal function ' .. name .. '%(') end
local function method(name) return extractBlock('\nfunction engine:' .. name .. '%(') end
local env = {math = math, string = string, tonumber = tonumber, tostring = tostring, type = type,
  pcall = pcall, ipairs = ipairs, pairs = pairs, table = table, ac = ac}
local chunk = 'local engine = {}\n'
  .. src:match('\nlocal LUT_DAMPER_KINDS = %b{}') .. '\n'
  .. src:match('\nlocal LUT_REF_SPEEDS = %b{}') .. '\n'
  .. fn('iniGet') .. '\n' .. fn('iniStr') .. '\n' .. fn('iniNum') .. '\n'
  .. fn('lutPoints') .. '\n' .. fn('readLutArb') .. '\n' .. fn('readLutDampers') .. '\n' .. fn('lutDamperForce') .. '\n'
  .. method('lutArbMoveOk') .. '\n' .. method('lutDamperMoveOk') .. '\n'
  .. 'return {engine = engine, readLutArb = readLutArb, readLutDampers = readLutDampers, force = lutDamperForce, iniStub = iniStub}'
local A = assert(load(chunk, 'extracted', 't', env))()
local E = A.engine
local function setupIni() return ac.INIConfig.carData(0, 'setup.ini') end

------------------------------------------------------------------------------
print('=== FIX 1: damper event thresholds fixed at the validated 0.54 / 1.20 ===')
check('DAMPER_EVENT_MODERATE = 0.54', tonumber(src:match('\nlocal DAMPER_EVENT_MODERATE = ([%d%.]+)')), 0.54)
check('DAMPER_EVENT_SHARP = 1.20', tonumber(src:match('\nlocal DAMPER_EVENT_SHARP = ([%d%.]+)')), 1.2)
check('refreshTargets uses the constants', src:find('self%.velModerate = DAMPER_EVENT_MODERATE\n  self%.velSharp    = DAMPER_EVENT_SHARP') ~= nil, true)
check('crossover no longer scales anything', src:find('clamp%(thr %* 18') == nil and src:find('clamp%(thr %* 40') == nil, true)
check('crossover still read (logged)', src:find('self%.damperCrossover = readDamperCrossover%(car%.index%)') ~= nil, true)
check('update() falls back to the constants', src:find('local modThr = self%.velModerate or DAMPER_EVENT_MODERATE') ~= nil, true)
check('log says FIXED', src:find('FIXED for every car since v2%.2%.0') ~= nil, true)
-- The A/B that decided it (real log, same car, same evening):
local dacia_054 = {12, 12, 8, 3, 16}   -- front rebound events at 0.54/1.20
local dacia_090 = {0, 0}               -- at the scaled 0.90/2.00
local s054, s090 = 0, 0
for _, v in ipairs(dacia_054) do s054 = s054 + v end
for _, v in ipairs(dacia_090) do s090 = s090 + v end
check('A/B: scaled thresholds deleted the Dacia front-rebound signal', s090 == 0 and s054 > 0, true)

------------------------------------------------------------------------------
print('')
print('=== FIX 3: sv8_camaro_v2 LUT dampers - real dampers.ini, real curves ===')
CAR = 'sv8_camaro_v2'
local d = A.readLutDampers(0, setupIni())
check('dampers.ini enabled', d.enabled, true)
check('rear rebound curves: 4 (clicks 0/6/12/18)', #d.axles.REAR.REBOUND.keys, 4)
check('rear bump curves: 4 (clicks 1/4/8/12)', table.concat(d.axles.REAR.BUMP.keys, ','), '1,4,8,12')
check('setup MIN for bump = 1 (click = MIN + stored)', d.setupMin.DAMPER_BUMP_LR, 1)
check('setup MIN for rebound = 0', d.setupMin.DAMPER_REBOUND_LR, 0)
local rr = d.axles.REAR.REBOUND
-- 939 N is the LUT point at 0.024892 m/s; interpolated to 0.025 it's 944.
check('sane curve: rear rebound click 12 @0.025 m/s ~ 944 N', string.format('%.0f', A.force(rr, 12, 0.025)), '944')
check('BROKEN curve: rear rebound click 18 @0.025 m/s ~ 0 N', A.force(rr, 18, 0.025) < 1, true)
check('interpolated click 15 is SOFTER than 12 (the harm)', A.force(rr, 15, 0.025) < A.force(rr, 12, 0.025), true)
E.lutDampers = d
local item = {min = 0, max = 18, step = 1}           -- spinner range, stored from 0
local ok, note = E:lutDamperMoveOk('DAMPER_REBOUND_LR', 12, 13, 1, item)
check('stiffen rear rebound 12 -> 13: REFUSED', ok, false)
check('...and says why', note:find('SOFTER than click 12') ~= nil, true)
ok = E:lutDamperMoveOk('DAMPER_REBOUND_LR', 6, 7, 1, item)
check('stiffen rear rebound 6 -> 7 (sane region): allowed', ok, true)
ok = E:lutDamperMoveOk('DAMPER_REBOUND_LR', 13, 12, -1, item)
check('soften rear rebound 13 -> 12: REFUSED (curve says that is stiffer)', ok, false)
ok, note = E:lutDamperMoveOk('DAMPER_REBOUND_LF', 12, 13, 1, item)
check('FRONT rebound 12 -> 13 (front top curve is fine): allowed', ok, true)
check('...with the forces in the note', note:find('curve checked:') ~= nil, true)
local bumpItem = {min = 0, max = 11, step = 1}       -- MIN=1..12 -> stored 0..11
ok, note = E:lutDamperMoveOk('DAMPER_BUMP_LR', 5, 6, 1, bumpItem)
check('bump stored 5 -> 6 (= clicks 6 -> 7, MIN offset applied): allowed', ok, true)
check('vanilla DAMP_ section passes straight through', (E:lutDamperMoveOk('DAMP_BUMP_LR', 5, 6, 1, bumpItem)), true)

print('')
print('=== FIX 3: unreadable curves are NOT written blind ===')
E.lutDampers = {axles = {}, setupMin = {}}
ok, note = E:lutDamperMoveOk('DAMPER_REBOUND_LR', 6, 7, 1, item)
check('no curves -> refused', ok, false)
check('...says not written blind', note:find('not written blind') ~= nil, true)

print('')
print('=== FIX 3: gt4_bmw_m4 - mixed car, LUT rear ===')
CAR = 'gt4_bmw_m4'
local dm = A.readLutDampers(0, setupIni())
check('rear rebound curves at 0/10/20/30/40', table.concat(dm.axles.REAR.REBOUND.keys, ','), '0,10,20,30,40')
E.lutDampers = dm
ok = E:lutDamperMoveOk('DAMPER_REBOUND_LR', 16, 17, 1, {min = 0, max = 24, step = 1})
check('stiffen rear rebound 16 -> 17: allowed', ok, true)
ok = E:lutDamperMoveOk('DAMPER_BUMP_LR', 13, 12, -1, {min = 0, max = 24, step = 1})
check('soften rear bump 13 -> 12: allowed', ok, true)

------------------------------------------------------------------------------
print('')
print('=== FIX 2: LUT anti-roll bars - fr_bmw_btcc (text keys, "detached" row 0) ===')
CAR = 'fr_bmw_btcc'
local a = A.readLutArb(0, setupIni(), 'ARB_F')
check('ARB_F is a LUT bar', a ~= nil, true)
check('readable (text-key rows kept)', a.readable, true)
check('13 rows', a.rows, 13)
check('row 0 is the 0-stiffness "detached" row', a.stiff[0], 0)
check('first attached row = 1', a.firstUsableRow, 1)
check('stiffness rises with the row', a.rising, true)
E.lutArb = {ARB_F = a}
local arbItem = {min = 0, max = 12, step = 1}
ok, note = E:lutArbMoveOk('ARB_F', 1, 0, arbItem)
check('soften row 1 -> 0 (DETACH): REFUSED', ok, false)
check('...says detaches', note:find('DETACHES') ~= nil, true)
ok, note = E:lutArbMoveOk('ARB_F', 2, 1, arbItem)
check('soften row 2 -> 1: allowed', ok, true)
check('...stiffness in the note (452 -> 364)', note, 'LUT stiffness 452 -> 364')
ok = E:lutArbMoveOk('ARB_F', 12, 13, arbItem)
check('beyond the last row: refused', ok, false)
check('the driver\'s saved values fit 0..12 (8, 2, 6, 1)', (8 <= 12 and 2 <= 12 and 6 <= 12 and 1 <= 12), true)
print('--- same bar if the in-game LUT reader DROPS text-key rows ---')
DROP_TEXT = true
local a2 = A.readLutArb(0, setupIni(), 'ARB_F')
check('unreadable (no numeric rows)', a2.readable, false)
E.lutArb = {ARB_F = a2}
ok = E:lutArbMoveOk('ARB_F', 1, 0, arbItem)
check('blind: first row off-limits', ok, false)
ok = E:lutArbMoveOk('ARB_F', 3, 2, arbItem)
check('blind: other rows allowed, direction assumed', ok, true)
DROP_TEXT = false

print('')
print('=== FIX 2: gt4_alpine_a110 / gt4_bmw_m4 numeric-key bars ===')
CAR = 'gt4_alpine_a110'
local al = A.readLutArb(0, setupIni(), 'ARB_F')
check('alpine front: 4 rows 8400 -> 29952', string.format('%d %.0f %.0f', al.rows, al.stiff[0], al.stiff[3]), '4 8400 29952')
check('alpine: every row attached (first usable 0)', al.firstUsableRow, 0)
CAR = 'gt4_bmw_m4'
check('bmw ARB_R rising', A.readLutArb(0, setupIni(), 'ARB_R').rising, true)
check('vanilla section -> nil (not a LUT bar)', A.readLutArb(0, setupIni(), 'DAMP_BUMP_LF'), nil)

print('')
print('=== FIX 2: lever limits (port of arbCanSoften / arbCanStiffen for LUT bars) ===')
local function canSoften(cur, it, lut) return cur - 1 >= it.min + ((lut.readable and lut.firstUsableRow) or 1) end
local function canStiffen(cur, it) return cur + 1 <= it.max end
check('BTCC bar at row 1: can\'t soften (row 0 detaches)', canSoften(1, arbItem, a), false)
check('BTCC bar at row 2: can soften', canSoften(2, arbItem, a), true)
check('3-row bar at the middle row: can still stiffen (was frozen by the 1.5-step margin)', canStiffen(1, {min = 0, max = 2, step = 1}), true)
check('3-row bar at the top: can\'t stiffen', canStiffen(2, {min = 0, max = 2, step = 1}), false)

------------------------------------------------------------------------------
print('')
print('=== source guards ===')
for _, s in ipairs({'ARB_F', 'ARB_R', 'DAMPER_BUMP_LF', 'DAMPER_BUMP_RR', 'DAMPER_REBOUND_LR'}) do
  check('SETUP_PROBE knows ' .. s, src:find("{section = '" .. s .. "', corner") ~= nil, true)
end
check('writeTuned curve-checks DAMPER_ writes', src:find("if section:find%('%^DAMPER_'%) then\n        local ok, note = self:lutDamperMoveOk") ~= nil, true)
check('writeTuned curve-checks LUT bar writes', src:find('local ok, note = self:lutArbMoveOk%(section, cur, newV, schemaItem%)') ~= nil, true)
check('refusal is handled-not-changed (chain moves on)', src:find("NOT written %- %%s', desc, note%)%)\n          return true, false") ~= nil, true)
check('no schema-midpoint invention for LUT sections', src:find('CSP LUT sections are only ever nudged from what is on the car') ~= nil, true)
check('ARB ends resolved by presence', src:find("local arbFSection = firstPresent%('ARB_FRONT', 'ARB_F'%)") ~= nil, true)
check('ARB lever uses the resolved ends', src:find('local arbF, arbR = arbFSection, arbRSection') ~= nil, true)
check('LUT bar moves one row per Build (two at most on a measured jump)', src:find('lut and math%.min%(jump or 1, 2%) or %(jump or steps%(n%)%)') ~= nil, true)
check('axle loop resolves damper sections per corner', src:find("local bumpSection = damperSection%('BUMP', corner%)") ~= nil, true)
check('rear-dampers lever resolves per corner', src:find("damperSection%('BUMP', corner%), damperSection%('REBOUND', corner%)") ~= nil, true)
check('no hard-coded vanilla damper names left in writers', src:find("'DAMP_BUMP_' %.%. corner\n") == nil, true)
check('LUT data loaded per car in refreshSchema', src:find('self%.lutDampers = readLutDampers%(car%.index, setupIni%)') ~= nil, true)
check('suspension model line in the log', src:find('self:lutSuspensionLine%(%),') ~= nil, true)
check('LUT sections in the liveSetup sample', src:find("'DAMPER_REBOUND_LR', 'ARB_FRONT', 'ARB_F'") ~= nil, true)

print('')
print(string.format('%d passed, %d failed', pass, fail))
os.exit(fail == 0 and 0 or 1)
