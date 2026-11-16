-- v2.1.1: unmanaged sections (gearing, tyre compound, TC, limiter, brake
-- power) must be CARRIED from the live setup into the output, not left at
-- the template's stale values - and never ADDED if the template lacks them.
-- The two 2026-09-22 files that exposed it were overwritten by later
-- sessions (the 2026-09-29 Build rewrote SetupCoach_Optimized.ini), so this
-- test read whatever was there that day and broke. Their numbers are kept
-- below as recorded in the v2.1.1 changelog, and the carry runs on a later
-- real file of the same car, copied into fixtures/ (v2.5.1).

local appPath = arg[1] or 'D:/SteamLibrary/steamapps/common/assettocorsa/apps/lua/setupcoach/SetupCoach.lua'
local TEMPLATE = 'D:/Claude/setupcoach-tools/acd/fixtures/huracan_silverstone_2026-09-29_1835_built.ini'
local RTO = 'D:/Claude/setupcoach-tools/acd/extracted/ks_lamborghini_huracan_gt3/final.rto'
-- 2026-09-22 18:20:56 Build vs the driver's own last.ini (v2.1.1 changelog)
local REC = {writtenFinal = 6, lastFinal = 3, writtenTyres = 1, lastTyres = 0}

local f = assert(io.open(appPath, 'r'))
local src = f:read('a')
f:close()

local pass, fail = 0, 0
local function check(label, got, want)
  if got == want then pass = pass + 1; print(string.format('  PASS  %-72s %s', label, tostring(got)))
  else fail = fail + 1; print(string.format('  FAIL  %-72s got %s want %s', label, tostring(got), tostring(want))) end
end

------------------------------------------------------------------------------
-- The app's own readIniFile / getCurVal / ensureSectionValue, extracted.
------------------------------------------------------------------------------
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
  io = io, table = table, ipairs = ipairs, pairs = pairs}
local A = assert(load(
  extractFn('readIniFile') .. '\n' .. extractFn('getCurVal') .. '\n' .. extractFn('ensureSectionValue') .. '\n'
  .. 'return {read = readIniFile, get = getCurVal, set = ensureSectionValue}', 'x', 't', env))()

------------------------------------------------------------------------------
print('=== the 2026-09-22 Build: final.rto says it reverted the driver to the default ===')
local ratios = {}
for line in io.lines(RTO) do
  local r = line:match('|([%d%.]+)%s*$')
  if r then table.insert(ratios, tonumber(r)) end
end
check('15 final drive options', #ratios, 15)
check('written FINAL_RATIO 6 = 3.9166 (drivetrain.ini FINAL=3.9166, the default)', ratios[REC.writtenFinal + 1], 3.9166)
check('driver\'s own FINAL_RATIO 3 = 4.5000 (what the driver chose - shorter)', ratios[REC.lastFinal + 1], 4.5)
-- Lower numeric ratio = LONGER gearing. The driver picked 4.5 (short); the
-- Build wrote the default 3.9166 (long) - the opposite end of the change.
check('...and the default is LONGER gearing than the driver chose', ratios[REC.writtenFinal + 1] < ratios[REC.lastFinal + 1], true)

------------------------------------------------------------------------------
-- Port of the v2.1.1 sync/carry decision.
------------------------------------------------------------------------------
local function syncCarry(parsed, live, managed, carryExclude)
  local synced, carried, readOnly, absent, samples, fuelNote = 0, 0, 0, 0, {}, nil
  for section, it in pairs(live) do
    local looksInteger = math.abs(it.value - math.floor(it.value + 0.5)) < 1e-6
    local text = string.format(looksInteger and '%.0f' or '%.3f', it.value)
    if it.readOnly then readOnly = readOnly + 1
    elseif managed[section] then A.set(parsed, section, text); synced = synced + 1
    elseif carryExclude[section] then fuelNote = tostring(A.get(parsed, section)) .. ' vs ' .. text
    elseif parsed.valueLineIdx[section] then
      local before = A.get(parsed, section)
      A.set(parsed, section, text); carried = carried + 1
      if before and math.abs(before - it.value) > 1e-6 then table.insert(samples, section) end
    else absent = absent + 1 end
  end
  return synced, carried, readOnly, absent, samples, fuelNote
end

print('')
print('=== v2.1.1: the same Build, with carrying ===')
local parsed = A.read(TEMPLATE)       -- a real template of this car
if not parsed then print('  FAIL  fixture missing: ' .. TEMPLATE); os.exit(1) end
A.set(parsed, 'FINAL_RATIO', tostring(REC.writtenFinal))   -- stale template values
A.set(parsed, 'TYRES', tostring(REC.writtenTyres))
local managed = {CAMBER_LF = true, ARB_REAR = true}
local live = {
  CAMBER_LF = {value = -40.7, readOnly = false},
  ARB_REAR  = {value = 0,     readOnly = false},
  FINAL_RATIO = {value = 3,   readOnly = false},   -- what the driver set
  TYRES     = {value = 0,     readOnly = false},
  FUEL      = {value = 12,    readOnly = false},   -- looks like a part tank
  ENGINE_LIMITER = {value = 100, readOnly = false},
  INTERNAL_GEAR_1 = {value = 4, readOnly = false}, -- NOT in the template
  SOME_READONLY = {value = 9, readOnly = true},
}
local synced, carried, readOnly, absent, samples, fuelNote = syncCarry(parsed, live, managed, {FUEL = true})
check('managed synced', synced, 2)
check('FINAL_RATIO carried from live', A.get(parsed, 'FINAL_RATIO'), 3)
check('TYRES carried from live', A.get(parsed, 'TYRES'), 0)
check('the driver\'s final drive survives the Build', A.get(parsed, 'FINAL_RATIO'), REC.lastFinal)
check('the driver\'s compound survives the Build', A.get(parsed, 'TYRES'), REC.lastTyres)
check('stale sections reported', #samples, 2)
check('readOnly skipped', readOnly, 1)
check('INTERNAL_GEAR_1 NOT added (the v1.8.0 lesson)', A.get(parsed, 'INTERNAL_GEAR_1'), nil)
check('...counted as absent instead', absent, 1)
check('FUEL not carried - template value kept', A.get(parsed, 'FUEL'), 30)
check('...and both numbers logged', fuelNote, '30 vs 12')
check('ENGINE_LIMITER carried (unchanged, but now stated from live)', A.get(parsed, 'ENGINE_LIMITER'), 100)

print('')
print('=== a template with no live read at all: old behaviour, nothing invented ===')
local p2 = A.read(TEMPLATE)
local before = A.get(p2, 'FINAL_RATIO')
local s2, c2 = syncCarry(p2, {}, managed, {FUEL = true})
check('nothing synced', s2, 0)
check('nothing carried', c2, 0)
check('template value untouched', A.get(p2, 'FINAL_RATIO'), before)

print('')
print('=== compound cross-check against the car ===')
local function compoundCorrect(parsed, compoundIndex)
  local v = A.get(parsed, 'TYRES')
  if v and compoundIndex and compoundIndex >= 0 and math.abs(v - compoundIndex) > 1e-6 then
    A.set(parsed, 'TYRES', string.format('%d', compoundIndex))
    return true
  end
  return false
end
local p3 = A.read(TEMPLATE); A.set(p3, 'TYRES', '1')
check('TYRES=1 but car runs compound 0 -> corrected', compoundCorrect(p3, 0), true)
check('...to 0', A.get(p3, 'TYRES'), 0)
check('agreement -> no correction', compoundCorrect(p3, 0), false)
check('unknown index -> no correction', compoundCorrect(p3, nil), false)

------------------------------------------------------------------------------
print('')
print('=== source guards ===')
check('CARRY_EXCLUDE is FUEL only', src:match('local CARRY_EXCLUDE = (%b{})'), '{FUEL = true}')
check('carry branch requires the section to exist in the template', src:find('elseif parsed%.valueLineIdx%[section%] then') ~= nil, true)
check('absent unmanaged sections are counted, not added', src:find('liveUnmanagedAbsent = liveUnmanagedAbsent %+ 1') ~= nil, true)
check('managed still gated for WRITERS', src:find('local MANAGED_SECTIONS = {}') ~= nil, true)
check('compound cross-checked against car.compoundIndex', src:find('pcall%(function%(%) idx = tonumber%(car%.compoundIndex%) end%)') ~= nil, true)
check('log says CARRIED', src:find('unmanaged CARRIED from live') ~= nil, true)
check('log names the stale sections', src:find("template was stale on ") ~= nil, true)
check('TYRES + FINAL_RATIO sampled', src:find("'TYRES', 'FINAL_RATIO'}") ~= nil, true)
check('old misleading counter gone', src:find('unmanaged/left alone incl%. gearing') == nil, true)
check('gearing advice says advice-only on every act line (v2.3.0 wording)', select(2, src:gsub('%(advice only %- Build never changes gearing%)', '')) >= 3, true)

print('')
print(string.format('%d passed, %d failed', pass, fail))
os.exit(fail == 0 and 0 or 1)
