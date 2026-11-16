-- v1.9.7: (1) writeTuned sizes a nudge in STEPS of the control, not as a
-- percentage of its current value; (2) readTyreReference reads the FITTED
-- compound's section, not always [FRONT]; (3) writeDebugLog reports failure.
-- Checked against the real numbers that exposed each.

local appPath = arg[1] or 'D:/SteamLibrary/steamapps/common/assettocorsa/apps/lua/setupcoach/SetupCoach.lua'
local EXTRACTED = 'D:/Claude/setupcoach-tools/acd/extracted/'
local AC = 'D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/'

local f = assert(io.open(appPath, 'r'))
local src = f:read('a')
f:close()

local pass, fail = 0, 0
local function check(label, got, want)
  if got == want then pass = pass + 1; print(string.format('  PASS  %-66s %s', label, tostring(got)))
  else fail = fail + 1; print(string.format('  FAIL  %-66s got %s want %s', label, tostring(got), tostring(want))) end
end

------------------------------------------------------------------------------
-- Shared fixture helpers (same stub as test_ini_default_type.lua).
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
  pcall = pcall, ipairs = ipairs, pairs = pairs, print = print,
  ac = {INIConfig = {}}}
local chunk = 'local clamp = function(v,a,b) return math.max(a, math.min(b, v)) end\n'
  .. 'local function classIdeals() return 27, 27 end\n'
  .. extractFn('iniGet') .. '\n' .. extractFn('iniStr') .. '\n' .. extractFn('iniNum') .. '\n'
  .. extractFn('snapToStep') .. '\n' .. extractFn('fmtSetupValue') .. '\n'
  .. extractFn('readTyreReference') .. '\n'
  .. 'return {snapToStep=snapToStep, fmtSetupValue=fmtSetupValue, readTyreReference=readTyreReference}'
local A = assert(load(chunk, 'extracted', 't', env))()

------------------------------------------------------------------------------
-- (1) Nudge sizing. Exact port of writeTuned's two branches.
------------------------------------------------------------------------------
local function oldNudge(cur, frac, clicks, dir, item)
  local mag = math.max(math.abs(cur) * frac * clicks, 1)
  local raw = cur + dir * mag
  if item then raw = math.max(item.min, math.min(item.max, raw)) end
  local looksInteger = math.abs(cur - math.floor(cur + 0.5)) < 0.01
  local newV = looksInteger and math.floor(raw + 0.5) or (math.floor(raw * 100 + 0.5) / 100)
  if newV == cur then newV = cur + (dir > 0 and 1 or -1); if item then newV = math.max(item.min, math.min(item.max, newV)) end end
  return newV
end
local function newNudge(cur, frac, clicks, dir, item)
  if item and item.step and item.step > 0 then
    return A.snapToStep(cur + dir * clicks * item.step, item.min, item.max, item.step)
  end
  return oldNudge(cur, frac, clicks, dir, item)
end

print('=== nudge sizing: Ferrari fast rebound 175..190 step 1 (the v1.9.4 "185 -> 175 in one press") ===')
local fr = {min = 175, max = 190, step = 1}
check('OLD: 8% of 185 = 15 clicks -> floor', oldNudge(185, 0.08, 1, -1, fr), 175)
check('NEW: 1 click', newNudge(185, 0.08, 1, -1, fr), 184)
check('NEW: 2 clicks', newNudge(185, 0.08, 2, -1, fr), 183)
check('NEW: stiffen 2 clicks', newNudge(185, 0.08, 2, 1, fr), 187)

print('')
print('=== nudge sizing: Ferrari rear rebound 10..32, cur 26 ===')
local rr = {min = 10, max = 32, step = 1}
check('OLD: 8% x 2 clicks of 26 = 4 clicks', oldNudge(26, 0.08, 2, -1, rr), 22)
check('NEW: 2 clicks', newNudge(26, 0.08, 2, -1, rr), 24)

print('')
print('=== nudge sizing: Dacia ARB 10000..25000 step 1000, cur 21079 (off-grid from earlier % writes) ===')
local arb = {min = 10000, max = 25000, step = 1000}
check('OLD: 7% x 2 of 21079 = 2951, stays off-grid', oldNudge(21079, 0.07, 2, -1, arb), 18128)
check('NEW: 2 clicks and back on the grid', newNudge(21079, 0.07, 2, -1, arb), 19000)

print('')
print('=== nudge sizing: small click index behaves as before (Lotus rebound 0..24, cur 9) ===')
local lr = {min = 0, max = 24, step = 1}
check('OLD: 1 click (floored)', oldNudge(9, 0.08, 1, -1, lr), 8)
check('NEW: 1 click', newNudge(9, 0.08, 1, -1, lr), 8)
check('NEW: clamps at min', newNudge(1, 0.08, 2, -1, lr), 0)
check('NEW: clamps at max', newNudge(24, 0.08, 2, 1, lr), 24)

print('')
print('=== nudge sizing: no step known -> percentage path unchanged (E30 toe 35, 16 Sep log wrote 39) ===')
check('no schema: 35 -> 39', newNudge(35, 0.05, 2, 1, nil), 39)
check('schema with step 0 -> percentage', newNudge(35, 0.05, 2, 1, {min = -25, max = 85, step = 0}), 39)
print('=== ...and with the E30\'s real TOE step of 10 ===')
check('step 10: 35 -> 55 (2 clicks, on grid)', newNudge(35, 0.05, 2, 1, {min = -25, max = 85, step = 10}), 55)

print('')
print('=== source guards (1) ===')
check('writeTuned has the step branch', src:find('local hasStep = schemaItem and schemaItem%.step and schemaItem%.step > 0') ~= nil, true)
check('step branch snaps to grid', src:find('newV = snapToStep%(raw, schemaItem%.min, schemaItem%.max, schemaItem%.step%)') ~= nil, true)
check('percentage path kept as fallback', src:find('local mag = math%.max%(math%.abs%(cur%) %* frac %* clicks, 1%)') ~= nil, true)
check('log line names the click size', src:find("', %%d click%%s of %%s'") ~= nil, true)

------------------------------------------------------------------------------
-- (2) Compound-aware tyres.ini read, on the E30 drift car's REAL file.
------------------------------------------------------------------------------
print('')
print('=== compound: BMW E30 drift, real tyres.ini (3 compounds) ===')
local e30 = parseIni(EXTRACTED .. 'bmw_m3_e30_drift/tyres.ini')
if not e30 then
  print('  SKIP  E30 tyres.ini not extracted')
else
  env.ac.INIConfig.carData = function() return makeStub(e30) end
  local r0 = A.readTyreReference(0, 'bmw_m3_e30_drift', 'SV', 0)
  check('index 0 -> [FRONT]', r0.compoundSection, 'FRONT')
  check('index 0 hot target 38', r0.hotF, 38)
  check('index 0 DCAMBER_0 1.1', r0.dcamber0F, 1.1)
  local r2 = A.readTyreReference(0, 'bmw_m3_e30_drift', 'SM', 2)
  check('index 2 -> [FRONT_2]', r2.compoundSection, 'FRONT_2')
  check('index 2 is the Semislick', r2.compoundName, 'Semislick')
  check('index 2 hot target 31 (was 38 - 7 psi too high)', r2.hotF, 31)
  check('index 2 rear hot target 31', r2.hotR, 31)
  check('index 2 DCAMBER_0 1.2', r2.dcamber0F, 1.2)
  check('index 2 DY0 1.2922', r2.dy0F, 1.2922)
  check('src names the section and compound', r2.src, 'tyres.ini [FRONT_2 "Semislick"]')
  -- Index unknown (-1) but short name known: found by SHORT_NAME.
  local rsn = A.readTyreReference(0, 'bmw_m3_e30_drift', 'SM', -1)
  check('index unknown, SHORT_NAME "SM" -> [FRONT_2]', rsn.compoundSection, 'FRONT_2')
  -- Index says 1 but short name says SM: SHORT_NAME cross-check wins.
  local rx = A.readTyreReference(0, 'bmw_m3_e30_drift', 'SM', 1)
  check('index/name disagree -> SHORT_NAME wins', rx.compoundSection, 'FRONT_2')
  -- Index 1 with matching name: [FRONT_1]
  local r1 = A.readTyreReference(0, 'bmw_m3_e30_drift', 'ST', 1)
  check('index 1 "ST" -> [FRONT_1]', r1.compoundSection, 'FRONT_1')
  -- Out-of-range index: falls back to [FRONT]
  local r9 = A.readTyreReference(0, 'bmw_m3_e30_drift', '', 9)
  check('index 9 (no such section) -> [FRONT]', r9.compoundSection, 'FRONT')
end

print('')
print('=== compound: Dacia (single compound) still reads [FRONT] ===')
local dacia = parseIni(AC .. 'cup_dacia_sandero/data/tyres.ini')
if dacia then
  env.ac.INIConfig.carData = function() return makeStub(dacia) end
  local r = A.readTyreReference(0, 'cup_dacia_sandero', 'pirelli', 0)
  check('[FRONT]', r.compoundSection, 'FRONT')
  check('hot 29', r.hotF, 29)
  check('DCAMBER_0 1.3', r.dcamber0F, 1.3)
  check('src', r.src, 'tyres.ini [FRONT "pirelli cinturato RW"]')
end

print('')
print('=== compound: unreadable file -> class matrix as before ===')
env.ac.INIConfig.carData = function() error('nope') end
local rc = A.readTyreReference(0, 'x', '', 0)
check('src class matrix', rc.src, 'class matrix')

print('')
print('=== source guards (2)+(3) ===')
check('call site passes compoundIndex', src:find('readTyreReference%(car%.index, carId, compound, compoundIndex%)') ~= nil, true)
check('compoundIndex read from ac.StateCar', src:find('tonumber%(car%.compoundIndex%)') ~= nil, true)
check('writeDebugLog reports open failure', src:find("if not f then return fail%(tostring%(err%)%) end") ~= nil, true)
check('writeDebugLog failure reaches setupMsg', src:find("%[debug log NOT written: ") ~= nil, true)
check('previous failure recorded in the next entry', src:find("previous Build\\'s log write failed") ~= nil, true)

print('')
print(string.format('%d passed, %d failed', pass, fail))
os.exit(fail == 0 and 0 or 1)
