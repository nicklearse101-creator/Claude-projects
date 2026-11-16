-- v1.9.9: seven findings from the first Corvette Z06 GT3 logs, checked
-- against that car's REAL decrypted data (acd/extracted/corvette_z06_gt3_2024).

local appPath = arg[1] or 'D:/SteamLibrary/steamapps/common/assettocorsa/apps/lua/setupcoach/SetupCoach.lua'
local EXTRACTED = 'D:/Claude/setupcoach-tools/acd/extracted/'
local f = assert(io.open(appPath, 'r'))
local src = f:read('a')
f:close()

local pass, fail = 0, 0
local function check(label, got, want)
  if got == want then pass = pass + 1; print(string.format('  PASS  %-70s %s', label, tostring(got)))
  else fail = fail + 1; print(string.format('  FAIL  %-70s got %s want %s', label, tostring(got), tostring(want))) end
end

------------------------------------------------------------------------------
-- fixture helpers (shared shape with the other v1.9.x tests)
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
    local sec = self.sections[section]; local raw = sec and sec[key]
    if default == nil then if raw == nil then return {} end return {raw} end
    if raw == nil then return default end
    if type(default) == 'number' then return tonumber((raw:gsub(';.*$', ''))) or default end
    if type(default) == 'string' then return raw end
    return default
  end
  return ini
end
local function parseLut(path)
  local pts = {}
  local fh = io.open(path, 'r')
  if not fh then return nil end
  for line in fh:lines() do
    local x, y = line:match('^%s*(-?[%d%.]+)%s*|%s*(-?[%d%.]+)')
    if x then table.insert(pts, {tonumber(x), tonumber(y)}) end
  end
  fh:close()
  table.sort(pts, function(a, b) return a[1] < b[1] end)
  local lut = {}
  function lut:get(x)
    if x <= pts[1][1] then return pts[1][2] end
    if x >= pts[#pts][1] then return pts[#pts][2] end
    for i = 2, #pts do
      if x <= pts[i][1] then
        local x0, y0, x1, y1 = pts[i-1][1], pts[i-1][2], pts[i][1], pts[i][2]
        return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
      end
    end
  end
  return lut
end
local function extractFn(name)
  local s = src:find('\nlocal function ' .. name .. '%(')
  assert(s, 'function not found: ' .. name)
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
local env = {math = math, string = string, tonumber = tonumber, tostring = tostring, type = type,
  pcall = pcall, ipairs = ipairs, pairs = pairs, print = print, ac = {INIConfig = {}}}
local chunk = 'local clamp = function(v,a,b) return math.max(a, math.min(b, v)) end\n'
  .. 'local function classIdeals() return 27, 27 end\n'
  .. extractFn('iniGet') .. '\n' .. extractFn('iniStr') .. '\n' .. extractFn('iniNum') .. '\n'
  .. extractFn('readTyreReference') .. '\n' .. extractFn('readSetupItem') .. '\n'
  .. extractFn('wingRoleFromName') .. '\n' .. extractFn('readDamperCrossover') .. '\n'
  .. 'return {readTyreReference=readTyreReference, readSetupItem=readSetupItem, wingRoleFromName=wingRoleFromName, readDamperCrossover=readDamperCrossover}'
local A = assert(load(chunk, 'extracted', 't', env))()

local CV = EXTRACTED .. 'corvette_z06_gt3_2024/'
local tyres = parseIni(CV .. 'tyres.ini')
local setup = parseIni(CV .. 'setup.ini')
local aero = parseIni(CV .. 'aero.ini')
local susp = parseIni(CV .. 'suspensions.ini')
if not (tyres and setup and aero and susp) then print('Corvette data not extracted - run acd_decoder.py corvette_z06_gt3_2024'); os.exit(1) end

------------------------------------------------------------------------------
print('=== 1) DY0=0 -> DY_REF (the "no DY0 reference" question) ===')
check('file: DY0 is 0', tyres.FRONT.DY0, '0')
check('file: DY_REF is 1.81', tyres.FRONT.DY_REF, '1.81')
env.ac.INIConfig.carData = function() return makeStub(tyres) end
local r = A.readTyreReference(0, 'corvette_z06_gt3_2024', 'S8M', 0)
check('dy0F falls back to DY_REF', r.dy0F, 1.81)
check('dy0R falls back to DY_REF', r.dy0R, 1.81)
check('dyRefUsed flagged', r.dyRefUsed, true)
check('measured F dy 1.41 -> 78% of reference', string.format('%.0f', 1.41 / 1.81 * 100), '78')
check('DCAMBER_LUT name read', r.dcamberLutF, 'cmbr.lut')
check('hot target 26 (matches log)', r.hotF, 26)
-- Dacia still uses DY0 (present and > 0.1)
local dacia = parseIni('D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/cup_dacia_sandero/data/tyres.ini')
if dacia then
  env.ac.INIConfig.carData = function() return makeStub(dacia) end
  local rd = A.readTyreReference(0, 'cup_dacia_sandero', 'pirelli', 0)
  check('Dacia keeps DY0 (1.557), not DY_REF', rd.dy0F, 1.557)
  check('Dacia dyRefUsed false', rd.dyRefUsed, false)
end

------------------------------------------------------------------------------
print('')
print('=== 2) rear wing is WING_3 on this car ===')
check('aero.ini WING_3 NAME', (aero.WING_3.NAME:gsub('%s*;.*$', '')), 'REAR WING')
check('setup.ini has [WING_3]', setup.WING_3 ~= nil, true)
check('setup.ini has NO [WING_2]', setup.WING_2, nil)
local roles = {}
for i = 0, 5 do
  local name = aero['WING_' .. i] and (aero['WING_' .. i].NAME:gsub('%s*;.*$', ''))
  roles[i] = A.wingRoleFromName(name, ({[1]='front',[2]='rear',[3]='diffuser'})[i])
end
check('WING_3 resolves to rear', roles[3], 'rear')
check('WING_1 (SPLITTER R) resolves to front', roles[1], 'front')
check('WING_4 (DIFFUSER R) resolves to diffuser', roles[4], 'diffuser')
check('"REAR DIFFUSER" is a diffuser, not the rear wing', A.wingRoleFromName('REAR DIFFUSER', nil), 'diffuser')
check('writer resolves the section from aeroWingIndex', src:find("local wingR = resolveWingSection%('rear'") ~= nil, true)
check('...and syncs the live value for an unmanaged section', src:find('if not MANAGED_SECTIONS%[sec%] and not it%.readOnly then') ~= nil, true)

------------------------------------------------------------------------------
print('')
print('=== 3) toe: zero position and the verdict gate ===')
local stubSetup = makeStub(setup)
local toeLF = A.readSetupItem(stubSetup, 'TOE_OUT_LF')
check('TOE_OUT_LF -100..100 step 10 SHOW_CLICKS=2 -> 0..20', toeLF.min .. '..' .. toeLF.max, '0..20')
check('zero toe is index 10', toeLF.zero, 10)
local toeLR = A.readSetupItem(stubSetup, 'TOE_OUT_LR')
check('TOE_OUT_LR zero is index 10', toeLR.zero, 10)
-- Ferrari: SHOW_CLICKS=2 -50..150/10 -> zero 5; SHOW_CLICKS=1 -100..70/10 -> zero 0
local fer = parseIni(EXTRACTED .. 'ferrari_458_gt2/setup.ini')
if fer then
  local fs = makeStub(fer)
  check('Ferrari TOE_OUT_LR (-50..150/10, clicks) zero index 5', A.readSetupItem(fs, 'TOE_OUT_LR').zero, 5)
  check('Ferrari TOE_OUT_LF (-100..70/10, steps-from-zero) zero 0', A.readSetupItem(fs, 'TOE_OUT_LF').zero, 0)
  check('Ferrari DAMP_REBOUND_LR (3780..11700) has no zero', A.readSetupItem(fs, 'DAMP_REBOUND_LR').zero, nil)
end
check('real log: front toe walked 11 -> 19 = +0.8 deg toe-out in 4 Builds (the ratchet)', 19 - 11, 8)
check('toe writer: front lever exists (v2.1.0 chain)', src:find('levers%.toeFront = function%(regime, direction%)') ~= nil, true)
check('toe writer: front reverse move needs toe-out present', src:find("if not %(cur and zero and cur > zero%) then return false, 'front toe already at/inside zero") ~= nil, true)
check('toe writer: rear forward move needs loose rear signal', src:find("if toeRearVerdict ~= 'loose' then return false, 'rear handling signal is not loose' end") ~= nil, true)
check('toe writer: rear reverse move needs toe-in present', src:find("if not %(cur and zero and cur < zero%) then return false, 'rear toe already at/inside zero") ~= nil, true)
check('toe writer: one click, front', src:find("writeAbs%(it, probe%.section, 1, 1,\n") ~= nil, true)
check('toe writer: one click, rear', src:find("writeAbs%(it, probe%.section, %-1, 1,\n") ~= nil, true)
check('schemaWithLive carries zero through', src:find('zero = existing and existing%.zero or nil') ~= nil, true)
check('panel FRONT TOE is verdict-gated', src:find("if lowVerdict == 'tight' and self%.turninPush > th and turninRate > 15 then") ~= nil, true)

------------------------------------------------------------------------------
print('')
print('=== 4) rake: one click per end ===')
local rakeCalls = 0
for _ in src:gmatch("_, ch = writeAbs%(schemaItem, probe%.section, dir, 1,") do rakeCalls = rakeCalls + 1 end
check('both rake writes (v2.1.0 lever) pass clicks=1', rakeCalls, 2)
check('no steps() left in rake writes', src:find("steps%(self%.highSnap%),\n            'Ride height") == nil and src:find("steps%(self%.midPush%), 'Ride height") == nil, true)
check('bottoming raise: one click in the measured direction (v2.6.0: the chain\'s last lever)', src:find("local ok, why = moveAll(rideMap, secs, endWord .. ' ride height', up, 1, function(sec)", 1, true) ~= nil, true)
check('real log: 4 Builds moved rake 16 clicks (front 20->28, rear 20->12)', (28 - 20) + (20 - 12), 16)

------------------------------------------------------------------------------
print('')
print('=== 5) evidence floor: histogram and diff ===')
local minEv = tonumber(src:match('\nlocal HISTOGRAM_MIN_EVENTS = (%d+)'))
check('HISTOGRAM_MIN_EVENTS defined', minEv, 6)
check('histogram gated on measured seconds (DAMPER_HIST_MIN_S)', src:find('total < DAMPER_HIST_MIN_S then') ~= nil, true)
check('panel slowDamperAdvice gated too (measured flag)', src:find("return hv%.measured and 'ok' or 'wait'") ~= nil, true)
check('diff: less-lock needs floor + 25% dominance', src:find('if rotN >= HISTOGRAM_MIN_EVENTS and rotN > divN %* 1%.25 then') ~= nil, true)
check('diff: more-lock needs floor + 25% dominance', src:find('elseif divN >= HISTOGRAM_MIN_EVENTS and divN > rotN %* 1%.25 then') ~= nil, true)
check('real log 19:37: 3 rot vs 2 div -> would now be left alone', (3 >= minEv), false)
check('real log 19:42: 4 div vs 3 rot -> left alone', (4 >= minEv), false)
check('real log: front bump on 3/0 events -> left alone', (3 + 0 >= minEv), false)

------------------------------------------------------------------------------
print('')
print('=== 6) damper crossover typo guard (FRONT 0.50 / REAR 0.050) ===')
local function clean(v) return (v:gsub(';.*$', ''):gsub('^%s+', ''):gsub('%s+$', '')) end
check('file: FRONT 0.50', clean(susp.FRONT.DAMP_FAST_BUMPTHRESHOLD), '0.50')
check('file: REAR 0.050', clean(susp.REAR.DAMP_FAST_BUMPTHRESHOLD), '0.050')
env.ac.INIConfig.carData = function() return makeStub(susp) end
check('crossover takes the smaller (0.05), not the typo', A.readDamperCrossover(0), 0.05)
-- v2.2.0: the crossover no longer scales the event thresholds (fixed at
-- 0.54 / 1.20 for every car), so this guard now only matters for the
-- logged value; the typo guard still keeps that value honest.
check('crossover no longer drives thresholds (v2.2.0)', src:find('self%.velModerate = DAMPER_EVENT_MODERATE') ~= nil, true)
local ferSusp = parseIni(EXTRACTED .. 'ferrari_458_gt2/suspensions.ini')
if ferSusp then
  env.ac.INIConfig.carData = function() return makeStub(ferSusp) end
  check('Ferrari 0.030/0.010 = exactly 3x -> keeps front 0.030 (anchor)', A.readDamperCrossover(0), 0.03)
end
env.ac.INIConfig.carData = function() return makeStub({FRONT = {DAMP_FAST_BUMPTHRESHOLD = '0'}, HEAVE_FRONT = {DAMP_FAST_BUMPTHRESHOLD = '0.08'}}) end
check('front 0 -> heave fallback', A.readDamperCrossover(0), 0.08)

------------------------------------------------------------------------------
print('')
print('=== 7) DCAMBER_LUT peak (cmbr.lut) ===')
local lut = parseLut(CV .. 'cmbr.lut')
check('LUT parsed', lut ~= nil, true)
-- same sampling the engine does
local bestX, bestV = nil, -math.huge
for i = 0, 40 do local x = -10 + i * 0.25; local v = lut:get(x); if v > bestV then bestV, bestX = v, x end end
check('LUT peak at -4.00 deg', bestX, -4)
check('LUT peak value 1.040', string.format('%.3f', bestV), '1.040')
local coeffPeak = math.deg(-1.102 / (2 * -7.891))
check('parabola coefficients also say 4.00 (consistent on THIS car)', string.format('%.2f', coeffPeak), '4.00')
check('engine samples the LUT via ac.DataLUT11', src:find('local lutF, lutR = lutPeak%(ref%.dcamberLutF%), lutPeak%(ref%.dcamberLutR%)') ~= nil, true)
check('peakCamberSrc says live-lut', src:find("lutUsed and 'live%-lut' or 'live'") ~= nil, true)

print('')
print(string.format('%d passed, %d failed', pass, fail))
os.exit(fail == 0 and 0 or 1)
