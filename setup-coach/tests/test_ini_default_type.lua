-- v1.9.5/v1.9.6: ac.INIConfig:get's default argument sets its RETURN TYPE.
-- SDK (ac_apps/lib.lua, _ac_INIConfig:get):
--   "defaultValue: Defines type of value to return, is returned if value is
--    missing. If not set, list of strings is returned."
-- Every nil-default read in SetupCoach.lua was therefore getting a string
-- list back and tonumber()ing it to nil. This test models that rule in a
-- stub and runs the app's readers against REAL car data files:
--   tyres.ini   - the Dacia that exposed it (v1.9.5)
--   setup.ini   - four cars, checked against the stored-unit ranges the
--                 live spinners reported for those same cars in real logs
--   aero.ini    - the string.lower(table) crash
--   suspensions - the crossover anchor arithmetic

local appPath = arg[1] or 'D:/SteamLibrary/steamapps/common/assettocorsa/apps/lua/setupcoach/SetupCoach.lua'
local AC = 'D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/'
local EXTRACTED = 'D:/Claude/setupcoach-tools/acd/extracted/'

local f = assert(io.open(appPath, 'r'))
local src = f:read('a')
f:close()

local pass, fail = 0, 0
local function check(label, got, want)
  if got == want then pass = pass + 1; print(string.format('  PASS  %-66s %s', label, tostring(got)))
  else fail = fail + 1; print(string.format('  FAIL  %-66s got %s want %s', label, tostring(got), tostring(want))) end
end

------------------------------------------------------------------------------
-- Minimal INI parser for fixtures (keeps inline comments, as CSP's raw
-- string return might) + a stub that obeys the SDK rule.
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

local function makeStub(sections)
  local ini = {sections = sections}
  function ini:get(section, key, default)
    local sec = self.sections[section]
    local raw = sec and sec[key]
    if default == nil then
      if raw == nil then return {} end        -- "If not set, list of strings is returned."
      return {raw}
    end
    if raw == nil then return default end
    if type(default) == 'number' then return tonumber((raw:gsub(';.*$', ''))) or default end
    if type(default) == 'string' then return raw end
    return default
  end
  return ini
end

------------------------------------------------------------------------------
-- Pull the real helper + reader source out of the app and load them, so the
-- test exercises the shipped code rather than a port of it.
------------------------------------------------------------------------------
local function extractFn(name)
  local s, e = src:find('\nlocal function ' .. name .. '%(')
  assert(s, 'function not found: ' .. name)
  local body = src:sub(s + 1)
  local depth, i, n = 0, 1, #body
  -- crude but sufficient: count function/if/for/do ... end at line granularity
  local out = {}
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

local env = {math = math, string = string, tonumber = tonumber, tostring = tostring, type = type, pcall = pcall, ipairs = ipairs, pairs = pairs, print = print}
local chunk = 'local clamp = function(v,a,b) return math.max(a, math.min(b, v)) end\n'
  .. extractFn('iniGet') .. '\n' .. extractFn('iniStr') .. '\n' .. extractFn('iniNum') .. '\n'
  .. extractFn('peakCamberAngle') .. '\n' .. extractFn('readSetupItem') .. '\n'
  .. extractFn('wingRoleFromName') .. '\n'
  .. 'return {iniGet=iniGet, iniStr=iniStr, iniNum=iniNum, peakCamberAngle=peakCamberAngle, readSetupItem=readSetupItem, wingRoleFromName=wingRoleFromName}'
local loader = assert(load(chunk, 'extracted', 't', env))
local A = loader()

------------------------------------------------------------------------------
print('=== tyres.ini: the real Dacia file (v1.9.5) ===')
local tyres = makeStub(assert(parseIni(AC .. 'cup_dacia_sandero/data/tyres.ini'), 'Dacia tyres.ini missing'))
check('old path (nil default) -> table', type(A.iniGet(tyres, 'FRONT', 'DCAMBER_0', nil)), 'table')
check('old path -> tonumber nil', tonumber(A.iniGet(tyres, 'FRONT', 'DCAMBER_0', nil)), nil)
check('numeric default: PRESSURE_IDEAL reads', tonumber(A.iniGet(tyres, 'FRONT', 'PRESSURE_IDEAL', 0)), 29)
check('iniNum DCAMBER_0', A.iniNum(tyres, 'FRONT', 'DCAMBER_0'), 1.3)
check('iniNum DCAMBER_1', A.iniNum(tyres, 'FRONT', 'DCAMBER_1'), -15)
check('iniNum DY0', A.iniNum(tyres, 'FRONT', 'DY0'), 1.557)
check('iniNum missing key -> nil', A.iniNum(tyres, 'FRONT', 'NOT_A_KEY'), nil)
check('iniNum nil ini -> nil', A.iniNum(nil, 'FRONT', 'DCAMBER_0'), nil)
local peak = A.peakCamberAngle(A.iniNum(tyres, 'FRONT', 'DCAMBER_0'), A.iniNum(tyres, 'FRONT', 'DCAMBER_1'))
check('Dacia tyre peaks at 2.48 deg', string.format('%.2f', peak), '2.48')
check('DCAMBER route on the real session: -1.45 loaded is 1.03 short', string.format('%.2f', (-peak) - (-1.45)), '-1.03')

print('')
print('=== inline comments: Kunos files carry them on the value line ===')
local commented = makeStub({X = {MIN = '-5\t\t\t;degrees', NAME = 'Toe LF ; front', STEP = '1 \t;step is in degrees / 10'}})
check('iniNum strips ";degrees"', A.iniNum(commented, 'X', 'MIN'), -5)
check('iniStr strips the comment and trims', A.iniStr(commented, 'X', 'NAME'), 'Toe LF')
check('iniNum STEP with comment', A.iniNum(commented, 'X', 'STEP'), 1)
local listAlways = {get = function(self, s, k, d) return {'1.3'} end}
check('belt-and-braces: list returned for a string default still converts', A.iniNum(listAlways, 'A', 'B'), 1.3)

------------------------------------------------------------------------------
-- setup.ini: real files vs the stored-unit ranges the live spinners reported
-- for these exact cars in real debug logs (liveSetup: lines).
------------------------------------------------------------------------------
local cars = {
  {id = 'ferrari_458_gt2',   path = EXTRACTED .. 'ferrari_458_gt2/setup.ini',
   spinner = {CAMBER_LF = {-50, -12}, DAMP_REBOUND_LR = {10, 32}, ARB_FRONT = {0, 15}, PRESSURE_LF = {15, 45}},
   extra = {DAMP_FAST_REBOUND_LF = {175, 190}, TOE_OUT_LR = {0, 20}, ROD_LENGTH_LF = {0, 50}}},
  {id = 'lotus_exos_125_s1', path = EXTRACTED .. 'lotus_exos_125_s1/setup.ini',
   spinner = {CAMBER_LF = {-60, 10}, DAMP_REBOUND_LR = {0, 24}, ARB_FRONT = {0, 35}, PRESSURE_LF = {8, 20}}},
  {id = 'cup_dacia_sandero', path = AC .. 'cup_dacia_sandero/data/setup.ini',
   spinner = {CAMBER_LF = {-50, -5}, ARB_FRONT = {10000, 25000}, PRESSURE_LF = {10, 50}},
   extra = {TOE_OUT_LF = {0, 12}, ROD_LENGTH_LF = {0, 60}}},
  {id = 'abarth500',         path = EXTRACTED .. 'abarth500/setup.ini',
   spinner = {},
   extra = {CAMBER_LF = {-18, -2}, TOE_OUT_LF = {0, 13}}},
}
for _, car in ipairs(cars) do
  print('')
  print('=== setup.ini: ' .. car.id .. ' (real file, vs spinner ranges from real logs) ===')
  local sections = parseIni(car.path)
  if not sections then
    print('  SKIP  file not found: ' .. car.path)
  else
    local ini = makeStub(sections)
    local function cmp(sec, want, srcLabel)
      local item = A.readSetupItem(ini, sec)
      check(string.format('%s %s min (%s)', car.id, sec, srcLabel), item and item.min, want[1])
      check(string.format('%s %s max (%s)', car.id, sec, srcLabel), item and item.max, want[2])
    end
    for sec, want in pairs(car.spinner) do cmp(sec, want, 'spinner-confirmed') end
    for sec, want in pairs(car.extra or {}) do cmp(sec, want, 'rule/baked') end
    -- The old reader: MIN read with nil default -> nil -> item nil.
    check(car.id .. ' old reader returned nothing', tonumber(A.iniGet(ini, 'CAMBER_LF', 'MIN', nil)), nil)
  end
end

print('')
print('=== setup.ini: SHOW_CLICKS=1 rule prediction (unverified by a spinner yet) ===')
local fer = makeStub(assert(parseIni(EXTRACTED .. 'ferrari_458_gt2/setup.ini')))
local toeLF = A.readSetupItem(fer, 'TOE_OUT_LF')
check('Ferrari TOE_OUT_LF (SHOW_CLICKS=1, -100..70/10) predicted min', toeLF.min, -10)
check('Ferrari TOE_OUT_LF predicted max', toeLF.max, 7)
check('TOE_OUT_LF is in the debug sample so the next log settles it', src:find("'TOE_OUT_LF', 'DAMP_REBOUND_LR'") ~= nil, true)

print('')
print('=== camber x10 guard: a file already in tenths is not multiplied twice ===')
local tenths = makeStub({CAMBER_LF = {MIN = '-50', MAX = '-12', STEP = '1', SHOW_CLICKS = '0'}})
local t = A.readSetupItem(tenths, 'CAMBER_LF')
check('min untouched', t.min, -50)
check('max untouched', t.max, -12)

------------------------------------------------------------------------------
print('')
print('=== aero.ini: the string.lower(table) crash ===')
local aero = makeStub({WING_0 = {NAME = 'FRONT', LUT_GH_CL = 'wing_front_GH.lut'}, WING_1 = {NAME = 'REAR'}})
local nameOld = A.iniGet(aero, 'WING_0', 'NAME', nil)
check('old NAME read is a table', type(nameOld), 'table')
local okOld = pcall(A.wingRoleFromName, nameOld, 'front')
check('old: wingRoleFromName(table) throws (=> whole aero check died in its pcall)', okOld, false)
check('new: NAME reads as a string', A.iniStr(aero, 'WING_0', 'NAME'), 'FRONT')
check('new: role resolved', A.wingRoleFromName(A.iniStr(aero, 'WING_0', 'NAME'), 'front'), 'front')
check('new: LUT filename reads', A.iniStr(aero, 'WING_0', 'LUT_GH_CL'), 'wing_front_GH.lut')
check('new: missing LUT -> nil (not a table)', A.iniStr(aero, 'WING_1', 'LUT_GH_CL'), nil)

------------------------------------------------------------------------------
print('')
print('=== suspensions.ini: crossover READ (v2.2.0: logged only, no longer scales thresholds) ===')
-- v1.9.6-v2.1.1 scaled the damper event thresholds by the crossover
-- (18x / 40x). Retired in v2.2.0: a same-car A/B showed the scaling
-- deleting the signal (Dacia front rebound 12/12/8/3/16 at 0.54/1.20 vs
-- 0/0 at the scaled 0.90/2.00). Thresholds are now fixed - see
-- test_lut_suspension.lua. What stays tested here is that the crossover
-- itself still READS through iniNum (it is logged, and flags LUT axles).
check('fixed moderate threshold 0.54', tonumber(src:match('\nlocal DAMPER_EVENT_MODERATE = ([%d%.]+)')), 0.54)
check('fixed sharp threshold 1.20', tonumber(src:match('\nlocal DAMPER_EVENT_SHARP = ([%d%.]+)')), 1.2)
local realSusp = parseIni(EXTRACTED .. 'ferrari_458_gt2/suspensions.ini')
if realSusp then
  local si = makeStub(realSusp)
  check('Ferrari suspensions.ini FRONT crossover reads', A.iniNum(si, 'FRONT', 'DAMP_FAST_BUMPTHRESHOLD'), 0.03)
  check('old reader -> nil', tonumber(A.iniGet(si, 'FRONT', 'DAMP_FAST_BUMPTHRESHOLD', nil)), nil)
end

------------------------------------------------------------------------------
print('')
print('=== source guards ===')
check('iniNum defined once', select(2, src:gsub('local function iniNum%(', '')), 1)
check('iniStr defined once', select(2, src:gsub('local function iniStr%(', '')), 1)
local nilDefaultReads = 0
for line in src:gmatch('[^\n]+') do
  local code = line:gsub('%-%-.*$', '')
  if code:find('iniGet%([^)]*,%s*nil%)') then nilDefaultReads = nilDefaultReads + 1 end
end
check('NO nil-default iniGet reads remain in code (comments excluded)', nilDefaultReads, 0)
check('live read takes priority over DCAMBER_LOOKUP',
  src:find('if not self%.peakCamberF then%s+self%.peakCamberF = peakCamberAngle%(L%[1%], L%[2%]%)') ~= nil, true)
check('crossover scaling retired (no 18x)', src:find('clamp%(thr %* 18') == nil, true)
check('crossover scaling retired (no 40x)', src:find('clamp%(thr %* 40') == nil, true)
check('thresholds come from the fixed constants', src:find('self%.velModerate = DAMPER_EVENT_MODERATE') ~= nil, true)
check('pressure writer overlays the live spinner', src:find('for _, it in ipairs%(pressureItems%) do%s+local live = liveSetup%[it%.section%]') ~= nil, true)
check('pressure items are fresh copies, not self.schema', src:find("table%.insert%(pressureItems, {section = it%.section") ~= nil, true)
check('schemaSource labels renamed', src:find("'setup%.ini%+baked'") ~= nil, true)
check('peakCamberSrc logged', src:find('peakCamberSrc=%%s') ~= nil, true)

print('')
print(string.format('%d passed, %d failed', pass, fail))
os.exit(fail == 0 and 0 or 1)
