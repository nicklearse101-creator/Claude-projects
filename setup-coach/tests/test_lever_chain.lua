-- v2.1.0: lever chains, the effectiveness ledger, the cross-regime conflict
-- rule, the rake floor, and the ARB/aero split at 180. Loads the shipped
-- ledger functions out of the app source (they're engine methods, so they
-- are extracted by name) and drives them with a stub engine.

local appPath = arg[1] or 'D:/SteamLibrary/steamapps/common/assettocorsa/apps/lua/setupcoach/SetupCoach.lua'
local f = assert(io.open(appPath, 'r'))
local src = f:read('a')
f:close()

local pass, fail = 0, 0
local function check(label, got, want)
  if got == want then pass = pass + 1; print(string.format('  PASS  %-74s %s', label, tostring(got)))
  else fail = fail + 1; print(string.format('  FAIL  %-74s got %s want %s', label, tostring(got), tostring(want))) end
end

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
local function extractFn(name) return extractBlock('\nlocal function ' .. name .. '%(') end
local function extractMethod(name) return extractBlock('\nfunction engine:' .. name .. '%(') end

local settings = {leverLedger = '', leverPending = ''}
local env = {math = math, string = string, tonumber = tonumber, tostring = tostring, type = type,
  ipairs = ipairs, pairs = pairs, table = table, print = print, settings = settings}
local chunk = 'local engine = {}\n'
  .. src:match('\nlocal SLIGHT_OVERSTEER_PER_100 = %d+') .. '\n' .. '\nlocal settings = settings or {}\n' .. assert(src:match('\n%-%- BALANCE MODES BEGIN.-%-%- BALANCE MODES END'), 'balance modes block') .. '\n'
  .. src:match('\nlocal WINDOW_KEYS = %b{}') .. '\n'
  .. src:match('\nlocal LEVER_CHAINS = %b{}') .. '\n'
  .. src:match('\nlocal LEVER_EFFECT_DROP = [%d%.]+') .. '\n'
  .. src:match('\nlocal LEVER_FREEZE_AFTER = %d+') .. '\n'
  .. src:match('\nlocal LEVER_NOISE_K = [%d%.]+') .. '\n'   -- v2.3.0 noise guard
  .. src:match('\nlocal LEDGER_KEEP_CARS = %d+') .. '\n' .. extractFn('parseLedgerStore') .. '\n'   -- v2.4.0 per-car ledger
  .. src:match('\nlocal KEYED_KEEP = %d+') .. '\n' .. extractFn('parseKeyedStore') .. '\n' .. extractFn('serialiseKeyedStore') .. '\n'
  .. extractFn('keyedGet') .. '\n' .. extractFn('keyedPut') .. '\n' .. extractFn('keyedDropCar') .. '\n'   -- v2.5.0 per car + track
  .. extractFn('balanceVerdict') .. '\n' .. extractFn('windowBins') .. '\n' .. extractFn('regimeCounts') .. '\n'
  .. extractFn('regimeVerdict') .. '\n' .. extractMethod('lapRateStats') .. '\n'
  .. extractMethod('leverLedgerFor') .. '\n' .. extractMethod('leverLedgerSave') .. '\n'
  .. extractMethod('judgePendingLevers') .. '\n' .. extractMethod('leverLedgerLine') .. '\n'
  .. 'return {engine = engine, CHAINS = LEVER_CHAINS, DROP = LEVER_EFFECT_DROP, FREEZE = LEVER_FREEZE_AFTER}'
local A = assert(load(chunk, 'extracted', 't', env))()
local E = A.engine
local th = 2
local CAR = 'ks_lamborghini_huracan_gt3'

------------------------------------------------------------------------------
print('=== chains: physics priority order ===')
check('low-loose: ARB first', A.CHAINS['low-loose'][1], 'arb')
check('low-loose: rear dampers second', A.CHAINS['low-loose'][2], 'rearDampers')
check('low-loose: rake LAST', A.CHAINS['low-loose'][#A.CHAINS['low-loose']], 'rake')
check('high-loose: wings first', A.CHAINS['high-loose'][1], 'wings')
check('high-tight: wings first', A.CHAINS['high-tight'][1], 'wings')
check('no wings at low speed', (function() for _, l in ipairs(A.CHAINS['low-loose']) do if l == 'wings' then return true end end return false end)(), false)
check('no ARB at high speed', (function() for _, l in ipairs(A.CHAINS['high-loose']) do if l == 'arb' then return true end end return false end)(), false)
check('effect drop 10%', A.DROP, 0.10)
check('freeze after 3', A.FREEZE, 3)

------------------------------------------------------------------------------
print('')
print('=== ledger: the Huracan night, replayed - rear wing moved four times, oversteer never dropped ===')
-- Window rates from the real log: high snap per 100 corners: 31.5 -> 33.8 -> 29.4 -> 32.1
local self = E  -- the methods live on engine; in the app self IS engine
self.corneringSamples, self.lapBins, self.windowBinsStart = 130, {}, 0
self.midPush, self.midSnap, self.highPush, self.highSnap = 54, 90, 15, 44
-- Build #1 moved 'wings' for high-loose at 31.5/100 (recorded as pending).
settings.leverPending = CAR .. '|1|high-loose:wings:31.5'
local line = E:judgePendingLevers(CAR, th, 'YES')
check('judged: NO EFFECT (31.5 -> 33.8)', line:find('NO EFFECT') ~= nil, true)
check('ledger: wings 1/3 without effect', line:find('%[1/3 without effect%]') ~= nil, true)
check('not frozen yet', line:find('FROZEN') == nil, true)
check('pending consumed', settings.leverPending, '')
local ledger = E:leverLedgerFor(CAR)
check('ledger entry tries=1 ineff=1', ledger['high-loose'].wings.tries .. '/' .. ledger['high-loose'].wings.ineff, '1/1')
check('persisted', settings.leverLedger:find('high%-loose:wings:1:1:0') ~= nil, true)

-- Build #2 moved wings again at 33.8; next window 31.5 (7% drop - below the 10% bar).
self.highSnap, self.corneringSamples = 63, 200   -- 31.5 per 100
settings.leverPending = CAR .. '|2|high-loose:wings:33.8'
line = E:judgePendingLevers(CAR, th, 'YES')
check('7% drop is NOT enough (bar 10%) -> NO EFFECT', line:find('NO EFFECT') ~= nil, true)
check('two no-effects: NOT frozen yet (three tries)', line:find('FROZEN') == nil, true)
-- Build #3 moved wings a third time at 31.5; next window 32.0.
self.highSnap, self.corneringSamples = 64, 200   -- 32.0 per 100
settings.leverPending = CAR .. '|3|high-loose:wings:31.5'
line = E:judgePendingLevers(CAR, th, 'YES')
check('third no-effect -> FROZEN after 3', line:find('FROZEN') ~= nil, true)
ledger = E:leverLedgerFor(CAR)
check('ledger frozen flag', ledger['high-loose'].wings.frozen, true)
check('ledger line shows it', E:leverLedgerLine(CAR):find('wings=FROZEN') ~= nil, true)

-- A lever that helped clears the count.
self.highSnap, self.corneringSamples = 20, 165   -- 12.1 per 100
settings.leverPending = CAR .. '|4|high-loose:rake:29.4'
line = E:judgePendingLevers(CAR, th, 'YES')
check('rake: 29.4 -> 12.1 = HELPED', line:find('HELPED') ~= nil, true)
ledger = E:leverLedgerFor(CAR)
check('rake ineff reset to 0', ledger['high-loose'].rake.ineff, 0)
check('rake not frozen', ledger['high-loose'].rake.frozen, false)

-- Signal gone counts as helped even if the rate maths says otherwise.
self.highSnap, self.highPush, self.corneringSamples = 5, 30, 100   -- verdict now 'tight'
settings.leverPending = CAR .. '|4|high-loose:toeRear:4.0'
line = E:judgePendingLevers(CAR, th, 'YES')
check('signal gone -> HELPED', line:find('signal gone %- HELPED') ~= nil, true)

print('')
print('=== ledger: not judged when the previous Build was not loaded ===')
settings.leverPending = CAR .. '|5|low-loose:arb:60.0'
line = E:judgePendingLevers(CAR, th, 'NO')
check('says NOT judged', line:find('NOT judged') ~= nil, true)
check('pending still consumed', settings.leverPending, '')
print('=== ledger: another car\'s record is ignored ===')
settings.leverPending = 'other_car|6|low-loose:arb:60.0'
line = E:judgePendingLevers(CAR, th, 'YES')
check('n/a for a different car', line:find('n/a') ~= nil, true)

print('')
print('=== ledger: round-trips through storage for the same car, ignored for another ===')
E.leverLedger, E.leverLedgerCar = nil, nil
local restored = E:leverLedgerFor(CAR)
check('wings still frozen after reload', restored['high-loose'] and restored['high-loose'].wings and restored['high-loose'].wings.frozen, true)
E.leverLedger, E.leverLedgerCar = nil, nil
local other = E:leverLedgerFor('other_car')
check('other car starts clean', next(other), nil)

------------------------------------------------------------------------------
print('')
print('=== runner: chain walk, conflict rule, one lever per regime (simulated) ===')
-- Port of the runner's decision, with lever availability supplied.
local function runChain(key, ledger, avail)
  local tried = {}
  for _, lever in ipairs(A.CHAINS[key]) do
    local e = ledger[key] and ledger[key][lever]
    if e and e.frozen then table.insert(tried, lever .. '(frozen)')
    elseif avail[lever] then return lever, tried
    else table.insert(tried, lever .. '(unavailable)') end
  end
  return nil, tried
end
local L = {['high-loose'] = {wings = {frozen = true}}}
local lever, tried = runChain('high-loose', L, {wings = true, rake = true, toeRear = true})
check('high-loose with wings frozen -> rake', lever, 'rake')
check('...and the skip is named', tried[1], 'wings(frozen)')
lever = runChain('low-loose', {}, {arb = false, rearDampers = true})
check('low-loose with ARB at its limits -> rear dampers', lever, 'rearDampers')
lever, tried = runChain('low-loose', {}, {})
check('nothing available -> nil', lever, nil)
check('...all seven named (v2.5.0: + springs, diff)', #tried, 7)
-- v2.5.0: a car with no ARB and no rear dampers (the Sunbeam) reaches the springs next.
lever = runChain('low-loose', {}, {springs = true, toeFront = true, diff = true})
check('no ARB, no dampers -> springs (the roll-stiffness split)', lever, 'springs')
lever = runChain('low-tight', {}, {toeFront = false, springs = true})
check('low-tight: no bar, front toe spent -> springs', lever, 'springs')
-- conflict: low tight + high loose -> only the high chain runs
local lowV, highV = 'tight', 'loose'
local conflict = lowV and highV and lowV ~= highV
check('opposite verdicts = conflict', conflict, true)
check('same verdicts = no conflict', ('loose' ~= 'loose'), false)

------------------------------------------------------------------------------
print('')
print('=== rake floor ===')
local RAKE_MIN = tonumber(src:match('local RAKE_MIN_MM = (%d+)'))
check('RAKE_MIN_MM = 3', RAKE_MIN, 3)
local function rakeAllowed(front_mm, rear_mm, direction)
  local rake = rear_mm - front_mm
  if direction == 'loose' and rake <= RAKE_MIN then return false, rake end
  return true, rake
end
check('Huracan-style front 72 rear 74 (+2): less rake REFUSED', (rakeAllowed(72, 74, 'loose')), false)
check('front 72 rear 80 (+8): less rake allowed', (rakeAllowed(72, 80, 'loose')), true)
check('negative rake (front 76 rear 70): less rake REFUSED', (rakeAllowed(76, 70, 'loose')), false)
check('more rake is never floored', (rakeAllowed(76, 70, 'tight')), true)

------------------------------------------------------------------------------
print('')
print('=== source guards ===')
check('ARB/aero split raised to 180', src:find('\nlocal ARB_AERO_SPLIT_KMH = 180') ~= nil, true)
check('rear ride height captured', src:find('self%.staticRideHeightR = rh%[1%]') ~= nil, true)
check('rake lever refuses below the floor', src:find("if direction == 'loose' and rake and rake <= RAKE_MIN_MM then") ~= nil, true)
for _, name in ipairs({'arb', 'rearDampers', 'toeFront', 'toeRear', 'rake', 'wings'}) do
  -- v2.3.0: arb / rearDampers / wings take a measured-response jump.
  local jumpy = name == 'arb' or name == 'rearDampers' or name == 'wings'
  check('lever defined: ' .. name, src:find('levers%.' .. name .. ' = function%(regime, direction' .. (jumpy and ', jump' or '') .. '%)') ~= nil, true)
end
check('runner: high chain before low', src:find("run%('high', highV, highNote, highPush, highSnap%)\n    run%('low', lowV, lowNote, lowPush, lowSnap%)") ~= nil, true)
check('runner: conflict holds the low chain', src:find("if conflict and regime == 'low' then") ~= nil, true)
check('runner: frozen levers skipped by name', src:find("if entry and entry%.frozen then") ~= nil, true)
check('runner: banks rateBefore as pending', src:find('table%.insert%(self%.leverPendingThisBuild, {key = key, lever = lever, rateBefore = rateBefore,') ~= nil, true)
check('pending persisted on success (v2.5.0: per car + track)', src:find("keyedPut%(list, carFolder, trackFolder, %(#items > 0%) and") ~= nil and src:find('settings%.leverPending = serialiseKeyedStore%(list%)') ~= nil, true)
check('judged BEFORE the writers run', (src:find('local effectLine = self:judgePendingLevers') or 0) < (src:find('local levers = {}') or 0), true)
-- v2.2.0: a LUT-section skip now sits between the template branch and the
-- schema-midpoint fallback; the (handled, changed) contract is what matters.
check('writeTuned returns (handled, changed)', src:find('return true, true\n    end\n') ~= nil and src:find('return true, false\n') ~= nil, true)
check('override button is one-shot', src:find('self%.gateOverrideOnce = false\n    if not passes then') ~= nil, true)
check('override logged', src:find("GATE OVERRIDDEN %(test button%)") ~= nil, true)
check('effect + ledger + calculated + rake lines in the log (v2.3.0 order)',
  (src:find('effectLine,\n    self:leverLedgerLine%(carFolder%),') or math.huge)
    < (src:find("'calculated targets %(v2%.3%.0%): '") or 0)
  and (src:find("'calculated targets %(v2%.3%.0%): '") or math.huge) < (src:find("string%.format%('rake: static front") or 0), true)

print('')
print(string.format('%d passed, %d failed', pass, fail))
os.exit(fail == 0 and 0 or 1)
