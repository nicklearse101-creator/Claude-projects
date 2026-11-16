-- v2.5.1: CSP names the setup-screen gear spinners INTERNAL_GEAR_1..N
-- (forward gear n - the car's setup.ini [GEAR_n]); AC's own saved setups
-- call the same items INTERNAL_GEAR_2..N+1 (AC's gear index: 0 reverse,
-- 1 neutral). Since v2.1.1 the Build CARRIES unmanaged sections from the
-- live spinners by name, so every gear's value went into the gear below.
-- Driven by the real Build of 2026-09-29 18:35:15 (ks_lamborghini_huracan_gt3
-- at ks_silverstone): the file it wrote (fixtures/), that Build's log, and
-- the car's own ratio lists.

local appPath = arg[1] or 'D:/SteamLibrary/steamapps/common/assettocorsa/apps/lua/setupcoach/SetupCoach.lua'
local TOOLS = 'D:/Claude/setupcoach-tools/acd/'
local BUILT = TOOLS .. 'fixtures/huracan_silverstone_2026-09-29_1835_built.ini'
local CAR = TOOLS .. 'extracted/ks_lamborghini_huracan_gt3/'

local f = assert(io.open(appPath, 'r'))
local src = f:read('a')
f:close()

local pass, fail = 0, 0
local function check(label, got, want)
  if got == want then pass = pass + 1; print(string.format('  PASS  %-76s %s', label, tostring(got)))
  else fail = fail + 1; print(string.format('  FAIL  %-76s got %s want %s', label, tostring(got), tostring(want))) end
end

------------------------------------------------------------------------------
-- The app's own readIniFile / getCurVal / ensureSectionValue /
-- alignLiveGearNames, extracted from the shipped file.
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
  io = io, table = table, ipairs = ipairs, pairs = pairs, next = next}
local A = assert(load(
  extractFn('readIniFile') .. '\n' .. extractFn('getCurVal') .. '\n' .. extractFn('ensureSectionValue') .. '\n'
  .. extractFn('alignLiveGearNames') .. '\n'
  .. 'return {read = readIniFile, get = getCurVal, set = ensureSectionValue, align = alignLiveGearNames}', 'x', 't', env))()

-- The car's own ratio lists (setup.ini [GEAR_n] RATIOS=1st.rto .. 6th.rto,
-- [FINAL_GEAR_RATIO] RATIOS=final.rto). A saved VALUE is a 0-based index.
local function rto(name)
  local list = {}
  for line in io.lines(CAR .. name .. '.rto') do
    local r = line:match('|([%d%.]+)%s*$')
    if r then table.insert(list, tonumber(r)) end
  end
  return list
end
local GEAR_RTO = {rto('1st'), rto('2nd'), rto('3rd'), rto('4th'), rto('5th'), rto('6th')}
local FINAL_RTO = rto('final')
-- forward gear g (1..6) is saved as INTERNAL_GEAR_(g+1)
local function ratioIn(parsed, g)
  local v = A.get(parsed, 'INTERNAL_GEAR_' .. (g + 1))
  return v and GEAR_RTO[g][v + 1]
end
local function nearestIndex(list, ratio)
  local best, bestD = nil, math.huge
  for i, r in ipairs(list) do
    if math.abs(r - ratio) < bestD then best, bestD = i - 1, math.abs(r - ratio) end
  end
  return best
end
local STOCK = {}   -- drivetrain.ini [GEARS] GEAR_1..6
for line in io.lines(CAR .. 'drivetrain.ini') do
  local g, r = line:match('^GEAR_(%d)=([%d%.]+)')
  if g then STOCK[tonumber(g)] = tonumber(r) end
end

------------------------------------------------------------------------------
print('=== 1. the file the 18:35:15 Build wrote ===')
local built = A.read(BUILT)
if not built then print('  FAIL  fixture missing: ' .. BUILT); os.exit(1) end
local gearSections = 0
for sec in pairs(built.valueLineIdx) do if sec:match('^INTERNAL_GEAR_%d+$') then gearSections = gearSections + 1 end end
check('6 gear sections in the file (AC saves 1st..6th as INTERNAL_GEAR_2..7)', gearSections, 6)
check('no INTERNAL_GEAR_1 in it (AC gear index 1 is neutral)', A.get(built, 'INTERNAL_GEAR_1'), nil)
check('5th gear written = 0.8857', ratioIn(built, 5), 0.8857)
check('6th gear written = 0.8857', ratioIn(built, 6), 0.8857)
check('...5th and 6th the same ratio - the gearbox Nik found', ratioIn(built, 5) == ratioIn(built, 6), true)
-- That Build's log: "topGear=7 topGearRatio=0.886 secondTopGearRatio=1.031"
-- (ac.getCarPhysics when the car was loaded).
check('the car\'s physics ran 5th = option 2 (1.0312, log 1.031)', nearestIndex(GEAR_RTO[5], 1.031), 2)
check('...the Build wrote option 7 into 5th', A.get(built, 'INTERNAL_GEAR_6'), 7)
check('the car\'s physics ran 6th = option 7 (0.8857, log 0.886)', nearestIndex(GEAR_RTO[6], 0.886), 7)

------------------------------------------------------------------------------
print('')
print('=== 2. v2.5.1: the same Build with the gear names aligned ===')
-- The template (generic/last.ini as it was at 18:35, since overwritten) =
-- the written file with the values that Build's log gave as the template's:
-- "template was stale on INTERNAL_GEAR_6 2->7, FINAL_RATIO 3->4,
-- INTERNAL_GEAR_2 1->3, INTERNAL_GEAR_4 3->4" (all other gears equal).
local template = A.read(BUILT)
for sec, v in pairs({INTERNAL_GEAR_2 = '1', INTERNAL_GEAR_4 = '3', INTERNAL_GEAR_6 = '2', FINAL_RATIO = '3'}) do
  A.set(template, sec, v)
end
-- The live spinners as CSP named them: the values that Build carried, one
-- name down. INTERNAL_GEAR_1 (1st) was left out and never logged - 1 here is
-- the template's own 1st gear.
local live = {}
for n, v in ipairs({1, 3, 3, 4, 2, 7}) do
  live['INTERNAL_GEAR_' .. n] = {section = 'INTERNAL_GEAR_' .. n, value = v, readOnly = false}
end
live.FINAL_RATIO = {section = 'FINAL_RATIO', value = 4, readOnly = false}
live.ABS = {section = 'ABS', value = 3, readOnly = false}
live.PRESSURE_LF = {section = 'PRESSURE_LF', value = 16, readOnly = false}   -- managed
local aligned, note = A.align(live, template, '60 sections')
-- the v2.1.1 sync/carry decision, on the aligned map
local managed = {PRESSURE_LF = true}
local carried, absent = 0, 0
for section, it in pairs(aligned) do
  local text = string.format('%.0f', it.value)
  if managed[section] then A.set(template, section, text)
  elseif template.valueLineIdx[section] then A.set(template, section, text); carried = carried + 1
  else absent = absent + 1 end
end
check('1st -> INTERNAL_GEAR_2 = 2.6428', ratioIn(template, 1), 2.6428)
check('2nd = 2.0000', ratioIn(template, 2), 2.0)
check('3rd = 1.5600', ratioIn(template, 3), 1.56)
check('4th = 1.2000', ratioIn(template, 4), 1.2)
check('5th = 1.0312 - what the physics ran', ratioIn(template, 5), 1.0312)
check('6th = 0.8857 - what the physics ran', ratioIn(template, 6), 0.8857)
local stock = true
for g = 2, 6 do if math.abs(ratioIn(template, g) - STOCK[g]) > 1e-4 then stock = false end end
check('2nd..6th = drivetrain.ini GEAR_2..6: the stock gearbox, one consistent car', stock, true)
check('final drive = 4.1666 (option 4), as driven (log: fitted 4.167)', FINAL_RTO[A.get(template, 'FINAL_RATIO') + 1], 4.1666)
check('no INTERNAL_GEAR_1 added', A.get(template, 'INTERNAL_GEAR_1'), nil)
check('all 6 gears carried, + FINAL_RATIO + ABS', carried, 8)
check('nothing left out', absent, 0)
check('note keeps the read summary first', note:sub(1, 11), '60 sections')
check('note names the renaming', note:find('INTERNAL_GEAR_1..6', 1, true) ~= nil and note:find('INTERNAL_GEAR_2..7', 1, true) ~= nil, true)
check('note lists the carried values 1st..6th', note:find('1,3,3,4,2,7', 1, true) ~= nil, true)
check('the live map itself is not modified', live.INTERNAL_GEAR_1.section, 'INTERNAL_GEAR_1')
check('renamed items carry their new name', aligned.INTERNAL_GEAR_7 and aligned.INTERNAL_GEAR_7.section, 'INTERNAL_GEAR_7')
check('non-gear items pass through as they are', aligned.FINAL_RATIO, live.FINAL_RATIO)

------------------------------------------------------------------------------
print('')
print('=== 3. the offset comes from the two name sets, never assumed ===')
local function gearsLive(from, to)
  local t = {ABS = {section = 'ABS', value = 1}}
  for n = from, to do t['INTERNAL_GEAR_' .. n] = {section = 'INTERNAL_GEAR_' .. n, value = n} end
  return t
end
local function fakeTemplate(from, to)
  local p = {valueLineIdx = {ABS = 1}}
  for n = from, to do p.valueLineIdx['INTERNAL_GEAR_' .. n] = n end
  return p
end
-- (a) CSP names them like the file (a future CSP fix): left as they are
local liveA = gearsLive(2, 7)
local a, na = A.align(liveA, fakeTemplate(2, 7), 'x')
check('names already match the file -> the same map back', a, liveA)
check('...and no renaming in the note', na:find('renamed', 1, true), nil)
-- (b) a car whose 1st gear is fixed: CSP 2..6 (2nd..6th), the file 3..7
local b = A.align(gearsLive(2, 6), fakeTemplate(3, 7), 'x')
check('fixed 1st gear: CSP 2..6 -> the file 3..7 (6th lands in INTERNAL_GEAR_7)', b.INTERNAL_GEAR_7 and b.INTERNAL_GEAR_7.value, 6)
check('...2nd lands in INTERNAL_GEAR_3', b.INTERNAL_GEAR_3 and b.INTERNAL_GEAR_3.value, 2)
check('...nothing left under INTERNAL_GEAR_2', b.INTERNAL_GEAR_2, nil)
-- (c) the sets don't line up either way: gears are NOT carried
local c, nc = A.align(gearsLive(1, 6), fakeTemplate(2, 6), 'x')
local anyGear = false
for sec in pairs(c) do if sec:match('^INTERNAL_GEAR_') then anyGear = true end end
check('no match -> no gear spinner survives (the template keeps its gears)', anyGear, false)
check('...non-gear items still carried', c.ABS ~= nil, true)
check('...and the note says gears were NOT carried', nc:find('NOT carried', 1, true) ~= nil, true)
-- (d) a template with no gear sections: nothing to align, map as it was
local liveD = gearsLive(1, 6)
local d, nd = A.align(liveD, fakeTemplate(1, 0), 'x')
check('template without gears -> the same map back (left out as before)', d, liveD)
check('...note untouched', nd, 'x')
-- (e) no gear spinners at all (most cars): nothing to do
local liveE = {ABS = {section = 'ABS', value = 1}}
local e, ne = A.align(liveE, fakeTemplate(2, 7), 'x')
check('no gear spinners -> the same map back', e, liveE)
check('...note untouched', ne, 'x')
-- (f) the live read failed
local fmap, fnote = A.align(nil, fakeTemplate(2, 7), 'REJECTED - ...')
check('no live read -> nil back', fmap, nil)
check('...its reason untouched', fnote, 'REJECTED - ...')

------------------------------------------------------------------------------
print('')
print('=== 4. source guards ===')
local readAt = src:find('local liveSetup, liveNote = readLiveSetupSpinners()', 1, true)
local alignAt = src:find('liveSetup, liveNote = alignLiveGearNames(liveSetup, parsed, liveNote)', 1, true)
local loopAt = src:find('for section, it in pairs(liveSetup) do', 1, true)
check('the live map is aligned right after it is read', readAt ~= nil and alignAt ~= nil and alignAt > readAt and alignAt - readAt < 600, true)
check('...before the sync/carry loop uses it', alignAt ~= nil and loopAt ~= nil and alignAt < loopAt, true)
check('alignLiveGearNames: one definition, one call', select(2, src:gsub('alignLiveGearNames%(', '')), 2)
check('carry still refuses sections the template lacks', src:find('elseif parsed%.valueLineIdx%[section%] then') ~= nil, true)

print('')
print(string.format('%d passed, %d failed', pass, fail))
os.exit(fail == 0 and 0 or 1)
