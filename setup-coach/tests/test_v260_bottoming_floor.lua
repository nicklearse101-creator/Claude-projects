-- v2.6.0: bottoming one fix at a time (travel chains) and ride height to the
-- floor. Nik, 2026-10-05: "Bottoming - one at a time. Ride height least
-- important. Stiffening springs too much loses grip so be cautious." / "it
-- should lower until the car is at minimum available without the body of the
-- car striking the floor." The shipped functions are extracted from the app
-- and run against the numbers the v2.5.1 Builds logged. The chain runner
-- itself is driven Build by Build in test_branch_passes.lua.

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
-- Extraction (as test_v250 / test_v252).
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

local settings = {leverLedger = '', leverPending = '', branchState = ''}
local env = {math = math, string = string, table = table, pairs = pairs, ipairs = ipairs, tostring = tostring,
  tonumber = tonumber, type = type, next = next, pcall = pcall, select = select, settings = settings,
  EV_UNIT = {one = 'lap', many = 'laps'}}
local chunk = 'local engine = {}\n'
for _, c in ipairs({'LEVER_EFFECT_DROP', 'LEVER_FREEZE_AFTER', 'LEVER_NOISE_K', 'LEDGER_KEEP_CARS', 'KEYED_KEEP'}) do
  chunk = chunk .. const(c) .. '\n'
end
for _, name in ipairs({'windowBins', 'regimeCounts', 'lapSupport', 'lapSupportNote', 'travelHitsConsistent', 'travelSignal',
    'parseKeyedStore', 'serialiseKeyedStore', 'keyedGet', 'keyedPut', 'parseLedgerStore'}) do
  chunk = chunk .. fn(name) .. '\n'
end
for _, m in ipairs({'lapRateStats', 'leverLedgerFor', 'leverLedgerSave', 'judgePendingLevers'}) do
  chunk = chunk .. method(m) .. '\n'
end
chunk = chunk .. 'return {engine = engine, travelSignal = travelSignal, putK = keyedPut, serK = serialiseKeyedStore, parseK = parseKeyedStore}\n'
local A = assert(load(chunk, 'chunk', 't', env))()
local E = A.engine

-- a window of clean laps: springsHitsR per lap, 70 corners a lap
local function window(perLap, corners)
  local bins, total = {}, 0
  for i, h in ipairs(perLap) do
    bins[i] = {springsHitsR = h, springsHitsF = 0, corneringSamples = corners or 70}
    total = total + h
  end
  return {lapBins = bins, windowBinsStart = 0, springsHitsR = total, springsHitsF = 0,
    corneringSamples = #perLap * (corners or 70), leverLedgerFor = E.leverLedgerFor, leverLedgerSave = E.leverLedgerSave,
    lapRateStats = E.lapRateStats}
end

------------------------------------------------------------------------------
print('=== 1. the travel signal and judging a travel move ===')
local W1 = window({3, 2, 2, 0, 4, 2, 1})
local v, hits, rate, agree, considered = A.travelSignal(W1, 'R', 2)
check('max-travel hits in 5 of 7 laps -> bottoming', v, 'bottoming')
check('...hits = the window count', hits, 14)
near('...rate = hits per 100 corners (14 / 490)', rate, 14 / 490 * 100, 1e-9)
check('...laps agreeing / laps considered', agree .. '/' .. considered, '5/7')
local W2 = window({3, 0, 2, 0, 4, 0, 1})
check('3 of 7 laps -> not a consistent trait, no verdict', (A.travelSignal(W2, 'R', 2)), nil)
check('front end reads the front counter', (A.travelSignal(W1, 'F', 2)), nil)
local mean, se, nLaps = E.lapRateStats(W1, 'travelR', 'hits')
near('per-lap noise for travel: mean of the per-lap rates', mean, 14 / 490 * 100, 1e-9)
check('...over the 7 laps', nLaps, 7)
check('...with a standard error', type(se) == 'number' and se > 0, true)

-- judging: a bumpR move banked at 10 hits per 100 corners
local CAR, TRACK = 'talbot_sunbeam_lotus_81_works_backup_v6', 'rt_bathurst'
local function pend(track)
  local list = A.parseK('')
  A.putK(list, CAR, track or TRACK, '73#travelR-bottoming:bumpR:10.00:1:-1.00')
  settings.leverPending = A.serK(list)
end
local function judged(Wn, loaded, track)
  Wn.leverJudgements = nil
  local line = E.judgePendingLevers(Wn, CAR, 2, loaded or 'YES', track or TRACK)
  return line, Wn.leverJudgements and Wn.leverJudgements[1] and Wn.leverJudgements[1].result
end
settings.leverLedger = ''
pend()
local Wsame = window({4, 3, 4, 3, 5}, 40); Wsame.springsHitsR, Wsame.corneringSamples = 19, 200   -- 9.5 per 100
local line1, r1 = judged(Wsame)
check('9.5 vs 10.0 per 100 (under 10% down) -> no effect', r1, 'no-effect')
check('...the effect line names the travel key and lever', line1:find('travelR-bottoming via bumpR', 1, true) ~= nil, true)
pend()
local _, r1b = judged(Wsame)
check('a second no-effect: not frozen yet (three tries)', E.leverLedgerFor(Wsame, CAR)['travelR-bottoming'].bumpR.frozen, false)
pend()
judged(Wsame)
check('a third no-effect -> FROZEN for this pass', E.leverLedgerFor(Wsame, CAR)['travelR-bottoming'].bumpR.frozen, true)
pend()
local Wbetter = window({4, 3, 4, 3, 5}, 40); Wbetter.springsHitsR, Wbetter.corneringSamples = 14, 200   -- 7.0 per 100
local _, r2 = judged(Wbetter)
check('7.0 vs 10.0 per 100 -> helped', r2, 'helped')
pend()
local Wgone = window({3, 0, 1, 0, 2}, 40); Wgone.springsHitsR, Wgone.corneringSamples = 19, 200
local _, r3 = judged(Wgone)
check('hits no longer on most laps -> helped (signal gone)', r3, 'helped')
pend()
local lineU, rU = judged(Wsame, 'NO')
check('previous Build not loaded -> not judged', rU, 'unloaded')
pend('spa')
local lineT, rT = judged(Wsame, 'YES', TRACK)
check('a move made at another track is not judged here', rT, nil)

------------------------------------------------------------------------------
print('')
print('=== 2. the bottoming levers: order, modules, cautious springs, the old writers retired ===')
local B = assert(load(const('SPRING_TARGET_USE') .. '\n' .. const('SPRING_MAX_STEP') .. '\n' .. fn('cautiousSpringTarget') .. '\n'
  .. src:match('\nlocal LEVER_CHAINS = %b{}') .. '\n' .. src:match('\nlocal LEVER_MODULE = %b{}') .. '\n'
  .. 'return {spring = cautiousSpringTarget, CHAINS = LEVER_CHAINS, MODULE = LEVER_MODULE, USE = SPRING_TARGET_USE, STEP = SPRING_MAX_STEP}',
  'chunkB', 't', {math = math}))()
check('springs aim at 95% of the travel (was 92%)', B.USE, 0.95)
check('...at most 10% stiffer per Build (was 30%)', B.STEP, 0.10)
near('Sunbeam front, median lap 110% of travel: 46 N/mm -> capped at +10%', B.spring(46000, 1.10), 50600, 1e-6)
near('97% of travel -> just enough for 95%', B.spring(46000, 0.97), 46000 * 0.97 / 0.95, 1e-6)
near('90% of travel -> leave the rate alone', B.spring(46000, 0.90), 46000, 1e-9)
check('front chain: packers > bump > fast bump > springs > ride height',
  table.concat(B.CHAINS['travelF-bottoming'], '>'), 'packersF>bumpF>fastBumpF>springRateF>rideRaiseF')
check('rear chain: the same order', table.concat(B.CHAINS['travelR-bottoming'], '>'), 'packersR>bumpR>fastBumpR>springRateR>rideRaiseR')
check('balance chains untouched', table.concat(B.CHAINS['low-loose'], '>'), 'arb>rearDampers>springs>toeRear>toeFront>diff>rake')
local modules = {}
for _, l in ipairs({'packersF', 'packersR', 'bumpF', 'bumpR', 'fastBumpF', 'fastBumpR', 'springRateF', 'springRateR', 'rideRaiseF', 'rideRaiseR'}) do
  table.insert(modules, l .. '=' .. tostring(B.MODULE[l]))
end
check('each bottoming lever answers to its module toggle', table.concat(modules, ' '),
  'packersF=writeSuspension packersR=writeSuspension bumpF=writeDampersFront bumpR=writeDampersRear '
  .. 'fastBumpF=writeFastDampersFront fastBumpR=writeFastDampersRear springRateF=writeSprings springRateR=writeSprings '
  .. 'rideRaiseF=writeSuspension rideRaiseR=writeSuspension')
local factoryAt = src:find('local function travelLeversFor(e)', 1, true)
check('the levers come from one factory per end', factoryAt ~= nil, true)
local factory = factoryAt and extractFrom(factoryAt) or ''
check('...which never writes a rebound setting (too much rebound packs a car down)', factory:find('REBOUND', 1, true), nil)
check('...ride height refuses when it already moved this Build', factory:find('if calc.rideMoved then return false', 1, true) ~= nil, true)
check('...springs tell the springs balance lever to stand aside', factory:find('springsMovedForTravel = true', 1, true) ~= nil, true)
check('retired: slow dampers stiffening bump AND rebound "for bottoming"',
  src:find("' rebound ' .. corner .. ' (stiffer, bottoming needs support)'", 1, true), nil)
check('retired: the packer writer on the raw bottoming count',
  src:find("'Packer range ' .. probe.corner .. ' (more travel before the packers)'", 1, true), nil)
check('retired: the 1-2 click spring step for bottoming',
  src:find("'Spring ' .. probe.corner .. ' (stiffer, less bottoming)'", 1, true), nil)
check('retired: fast dampers stiffened for bottoming', src:find('local fastDir = bottomingNow and 1 or -1', 1, true), nil)
check('v2.6.1: no kerb softener left - fast dampers belong to the chain alone',
  src:find("local fastChainEnd = ", 1, true) == nil and src:find("for _, grp in ipairs(fastGroups) do", 1, true) == nil, true)
check('retired: the bottoming ride-height raise outside the chain',
  src:find("(measured and ' (raise - direction measured in the pits)' or ' (raise - ⚠ verify direction on this car)')", 1, true), nil)
check('rake stands aside when ride height already moved this Build (was: "raised for bottoming")',
  src:find("if calc.rideMoved then return false, 'ride height already moved this Build", 1, true) ~= nil
  and src:find("if bottomingActive then return false, 'ride height already raised for bottoming this Build' end", 1, true) == nil, true)
check('ride direction is known before the levers are built (rideDir hoisted)',
  (src:find('\n  local function rideDir(front)', 1, true) or math.huge) < (src:find('local function travelLeversFor(e)', 1, true) or 0), true)

------------------------------------------------------------------------------
print('')
print('=== 2b. the five bottoming levers on a car: one move each, bump never rebound ===')
local P, W, MAPS, LV, BINS = {}, {}, {}, {}, {}
local RIDE_UP, RIDE_MEASURED = 1, false
local function item(sec, mn, mx, st, raw) return {section = sec, min = mn, max = mx, step = st, raw = raw} end
local envT = setmetatable({
  settings = {writeSuspension = true, writeDampersFront = true, writeDampersRear = true,
    writeFastDampersFront = true, writeFastDampersRear = true, writeSprings = true},
  schema = {packerRange = 'packerRange', damperBump = 'damperBump', damperFastBump = 'damperFastBump',
    springRate = 'springRate', rideHeight = 'rideHeight'},
  schemaWithLive = function(cat) return MAPS[cat] or {} end,
  getCurVal = function(_, sec) return P[sec] end, parsed = P,
  writeAbs = function(it, sec, dir, clicks, desc)
    local cur = P[sec]; if not cur then return false, false end
    local nv = cur + dir * clicks * (it and it.step or 1)
    if it then nv = math.max(it.min, math.min(it.max, nv)) end
    if nv == cur then return true, false end
    P[sec] = nv; table.insert(W, desc); return true, true
  end,
  calc = {touched = {}, notes = {}},
  steps = function(count) return math.max(1, math.min(2, math.floor(count / 2))) end,
  th = 2,
  travelSignal = function() return 'bottoming', 14, 2.9, 5, 7 end,
  windowBins = function() return BINS end,
  physicalOf = function(_, v) return v * 1000 end,
  storedOf = function(_, phys) return phys / 1000 end,
  rangeLimits = {},
  EV_UNIT = {one = 'lap', many = 'laps'},
  NUDGE_FRACTION = {bumpStop = 0.1, damper = 0.1, spring = 0.1, ride = 0.1},
  rideDir = function() return RIDE_UP, RIDE_MEASURED end,
  firstPresent = function(a, b) if P[a] then return a end if P[b] then return b end return nil end,
  damperSection = function(kind, corner)
    if P['DAMP_' .. kind .. '_' .. corner] then return 'DAMP_' .. kind .. '_' .. corner end
    if P['DAMPER_' .. kind .. '_' .. corner] then return 'DAMPER_' .. kind .. '_' .. corner end
    return 'DAMP_' .. kind .. '_' .. corner
  end,
  levers = LV, cautiousSpringTarget = B.spring, SPRING_TARGET_USE = B.USE, SPRING_MAX_STEP = B.STEP,
  springsMovedForTravel = false,
}, {__index = _G})
local SELF = {springsHitsF = 14, springsHitsR = 14, cornerSpringRate = function(_, _, _, cur) return cur * 1000 end}
local travelLeversFor = factoryAt and assert(load('return function(self)\n' .. factory .. '\nreturn travelLeversFor\nend', 'factory', 't', envT))()(SELF)
local function fresh()
  for k in pairs(P) do P[k] = nil end
  for k in pairs(W) do W[k] = nil end
  for k in pairs(envT.rangeLimits) do envT.rangeLimits[k] = nil end
  for k in pairs(BINS) do BINS[k] = nil end
  envT.calc.touched, envT.calc.rideMoved, envT.springsMovedForTravel = {}, nil, false
  RIDE_UP, RIDE_MEASURED = 1, false
end
-- the app builds the levers every Build, from that Build's setup items
local function build()
  for k in pairs(LV) do LV[k] = nil end
  travelLeversFor('F'); travelLeversFor('R')
end
-- the Sunbeam v6 front: springs and ride height, no packers, no dampers
local function sunbeam()
  fresh()
  P.SPRING_RATE_LF, P.SPRING_RATE_RF, P.ROD_LENGTH_LF, P.ROD_LENGTH_RF, P.ROD_LENGTH_LR, P.ROD_LENGTH_RR = 46, 46, 10, 10, 10, 10
  MAPS.springRate = {SPRING_RATE_LF = item('SPRING_RATE_LF', 20, 80, 1, {}), SPRING_RATE_RF = item('SPRING_RATE_RF', 20, 80, 1, {})}
  MAPS.rideHeight = {}
  for _, s in ipairs({'ROD_LENGTH_LF', 'ROD_LENGTH_RF', 'ROD_LENGTH_LR', 'ROD_LENGTH_RR'}) do MAPS.rideHeight[s] = item(s, 0, 20, 1) end
  MAPS.packerRange, MAPS.damperBump, MAPS.damperFastBump = {}, {}, {}
  build()
end
-- a GT3: packers, vanilla dampers at the front, CSP LUT dampers at the rear
local function gt3()
  fresh()
  for _, c in ipairs({'LF', 'RF', 'LR', 'RR'}) do P['PACKER_RANGE_' .. c] = 10 end
  P.DAMP_BUMP_LF, P.DAMP_BUMP_RF, P.DAMP_REBOUND_LF, P.DAMP_REBOUND_RF = 5, 5, 8, 8
  P.DAMP_FAST_BUMP_LF, P.DAMP_FAST_BUMP_RF, P.DAMP_FAST_REBOUND_LF, P.DAMP_FAST_REBOUND_RF = 3, 3, 4, 4
  P.DAMPER_BUMP_LR, P.DAMPER_BUMP_RR, P.DAMPER_REBOUND_LR, P.DAMPER_REBOUND_RR = 6, 6, 9, 9
  MAPS.packerRange, MAPS.damperBump, MAPS.damperFastBump = {}, {}, {}
  for _, c in ipairs({'LF', 'RF', 'LR', 'RR'}) do MAPS.packerRange['PACKER_RANGE_' .. c] = item('PACKER_RANGE_' .. c, 0, 30, 1) end
  for _, s in ipairs({'DAMP_BUMP_LF', 'DAMP_BUMP_RF', 'DAMPER_BUMP_LR', 'DAMPER_BUMP_RR'}) do MAPS.damperBump[s] = item(s, 0, 20, 1) end
  for _, s in ipairs({'DAMP_FAST_BUMP_LF', 'DAMP_FAST_BUMP_RF'}) do MAPS.damperFastBump[s] = item(s, 0, 20, 1) end
  MAPS.springRate, MAPS.rideHeight = {}, {}
  build()
end
local ok, why
if travelLeversFor then
  travelLeversFor('F'); travelLeversFor('R')
  local names = {}
  for _, l in ipairs({'packersF', 'bumpF', 'fastBumpF', 'springRateF', 'rideRaiseF', 'packersR', 'bumpR', 'fastBumpR', 'springRateR', 'rideRaiseR'}) do
    if type(LV[l]) == 'function' then table.insert(names, l) end
  end
  check('the factory builds all ten levers', #names, 10)

  sunbeam()
  ok, why = LV.packersF('travelF', 'bottoming')
  check('Sunbeam v6: no packers -> skipped with a reason', ok == false and why:find('no adjustable front packer') ~= nil, true)
  ok, why = LV.bumpF('travelF', 'bottoming')
  check('...no dampers -> slow bump skipped', ok == false and why:find('no adjustable front slow bump') ~= nil, true)
  ok, why = LV.fastBumpF('travelF', 'bottoming')
  check('...fast bump skipped', ok == false and why:find('no adjustable front fast bump') ~= nil, true)
  for i, u in ipairs({1.08, 1.10, 1.12, 1.10, 1.09}) do BINS[i] = {travelUseF = u} end
  ok = LV.springRateF('travelF', 'bottoming')
  check('springs: median lap 110% of travel -> 46 -> 50 (+10% cap, never past it)', ok and P.SPRING_RATE_LF == 50 and P.SPRING_RATE_RF == 50, true)
  check('...the springs balance lever is told to stand aside', envT.springsMovedForTravel, true)
  check('...both corners marked as set by the bottoming chain', envT.calc.touched.SPRING_RATE_LF == 'the bottoming chain' and envT.calc.touched.SPRING_RATE_RF == 'the bottoming chain', true)
  check('...rear springs untouched', P.SPRING_RATE_LR, nil)
  sunbeam(); for i, u in ipairs({0.97, 0.98, 0.96}) do BINS[i] = {travelUseF = u} end
  ok = LV.springRateF('travelF', 'bottoming')
  check('springs: median lap 97% -> one click (46 -> 47 reaches 95%)', ok and P.SPRING_RATE_LF == 47 and W[#W]:find('CALCULATED') ~= nil, true)
  sunbeam()
  ok = LV.springRateF('travelF', 'bottoming')
  check('springs: no per-lap travel yet -> the smallest step, one click', ok and P.SPRING_RATE_LF == 47 and W[#W]:find('not known') ~= nil, true)
  sunbeam(); MAPS.springRate.SPRING_RATE_LF.max, MAPS.springRate.SPRING_RATE_RF.max = 48, 48
  for i, u in ipairs({1.10, 1.10, 1.10}) do BINS[i] = {travelUseF = u} end
  ok = LV.springRateF('travelF', 'bottoming')
  check('springs: the car stops at 48 -> set to 48 and the range limit is reported', ok and P.SPRING_RATE_LF == 48 and #envT.rangeLimits >= 1, true)
  sunbeam(); envT.calc.touched.SPRING_RATE_LF = 'a branch put-back'
  ok, why = LV.springRateF('travelF', 'bottoming')
  check('springs already set by a put-back this Build -> not moved again', ok == false and why:find('a branch put%-back') ~= nil and P.SPRING_RATE_RF == 46, true)
  sunbeam()
  ok = LV.rideRaiseF('travelF', 'bottoming')
  check('ride height last: +1 click, direction not yet measured', ok and P.ROD_LENGTH_LF == 11 and P.ROD_LENGTH_RF == 11, true)
  check('...says to verify the direction', W[#W]:find('verify direction') ~= nil, true)
  check('...and records that ride height moved this Build', envT.calc.rideMoved, true)
  ok, why = LV.rideRaiseR('travelR', 'bottoming')
  check('a second ride-height move in the same Build is refused', ok == false and why:find('already moved this Build') ~= nil and P.ROD_LENGTH_LR == 10, true)
  sunbeam(); RIDE_UP, RIDE_MEASURED = -1, true
  ok = LV.rideRaiseR('travelR', 'bottoming')
  check('rear raise follows the pit calibration (a click DOWN raises this car)', ok and P.ROD_LENGTH_LR == 9 and W[#W]:find('measured in the pits') ~= nil, true)

  gt3()
  ok = LV.packersF('travelF', 'bottoming')
  check('GT3: packers first, front only, +2 (14 hits)', ok and P.PACKER_RANGE_LF == 12 and P.PACKER_RANGE_RF == 12 and P.PACKER_RANGE_LR == 10, true)
  check('...marked as set by the bottoming chain', envT.calc.touched.PACKER_RANGE_LF, 'the bottoming chain')
  gt3()
  ok = LV.bumpF('travelF', 'bottoming')
  check('slow bump stiffer, rebound left alone', ok and P.DAMP_BUMP_LF == 7 and P.DAMP_BUMP_RF == 7 and P.DAMP_REBOUND_LF == 8, true)
  ok = LV.bumpR('travelR', 'bottoming')
  check('rear CSP LUT dampers: the LUT bump section', ok and P.DAMPER_BUMP_LR == 8 and P.DAMPER_REBOUND_LR == 9, true)
  gt3()
  ok = LV.fastBumpF('travelF', 'bottoming')
  check('fast bump stiffer, fast rebound left alone', ok and P.DAMP_FAST_BUMP_LF == 5 and P.DAMP_FAST_REBOUND_LF == 4, true)
  gt3(); envT.settings.writeDampersFront = false
  ok, why = LV.bumpF('travelF', 'bottoming')
  check('module off -> skipped', ok == false and why == 'module off' and P.DAMP_BUMP_LF == 5, true)
  envT.settings.writeDampersFront = true
  gt3(); P.PACKER_RANGE_LF, P.PACKER_RANGE_RF = 30, 30
  ok, why = LV.packersF('travelF', 'bottoming')
  check('packers at their maximum -> skipped, the chain moves on', ok == false and why:find('limit') ~= nil, true)
end

------------------------------------------------------------------------------
print('')
print('=== 3. floor clearance: the lowest point on a lap, a kerb strike ignored ===')
local floorConsts = ''
for _, c in ipairs({'FLOOR_HIST_MAX_MM', 'FLOOR_LOW_SHARE', 'FLOOR_MIN_SAMPLES', 'FLOOR_PLAUSIBLE_MM'}) do
  floorConsts = floorConsts .. (src:match('\nlocal ' .. c .. ' = [^\n]+') or ('local ' .. c .. ' = nil')) .. '\n'
end
local okFloor, FL = pcall(function()
  return assert(load(floorConsts .. fn('floorHistAdd') .. '\n' .. fn('floorHistClearance') .. '\n'
    .. 'return {add = floorHistAdd, clr = floorHistClearance}', 'chunkF', 't', {math = math}))()
end)
check('floorHistAdd / floorHistClearance exist', okFloor, true)
if okFloor then
  local function lap(spec)
    local h = {}
    for _, s in ipairs(spec) do for _ = 1, s[1] do FL.add(h, s[2] / 1000) end end
    return h
  end
  check('1000 samples at 40 mm + 3 at 2 mm (a kerb strike) -> 40 mm', FL.clr(lap({{1000, 40}, {3, 2}})), 40)
  check('1000 at 40 mm + 20 at 15 mm (2% of the lap: a real low point) -> 15 mm', FL.clr(lap({{1000, 40}, {20, 15}})), 15)
  check('150 samples -> not enough for a lap', FL.clr(lap({{150, 40}})), nil)
  check('a car that reports 0 all lap -> no data', FL.clr(lap({{500, 0}})), nil)
  local h = {}; FL.add(h, -0.004)
  check('below the track counts as 0 mm', h[0], 1)

  local bankChunk = src:match('\nlocal WINDOW_KEYS = %b{}') .. '\n' .. fn('counterSnapshot') .. '\n' .. floorConsts
    .. fn('floorHistAdd') .. '\n' .. fn('floorHistClearance') .. '\nlocal engine = {}\n' .. method('bankEvidenceUnit') .. '\nreturn engine'
  local BK = assert(load(bankChunk, 'chunkBK', 't', {math = math, ipairs = ipairs, table = table}))()
  local S = {lapBins = {}, lapFloorHistF = lap({{1000, 40}, {3, 2}}), lapFloorHistR = lap({{1000, 55}}),
    lapTravelUseF = 0.9, lapTravelUseR = 0.8, floorHitsF = 2, floorHitsR = 0}
  BK.bankEvidenceUnit(S, {})
  local bin = S.lapBins[1]
  check('the lap bin carries each end\'s clearance', tostring(bin.clrF) .. '/' .. tostring(bin.clrR), '40/55')
  check('...and the lap\'s floor contacts', bin.floorHitsF, 2)
  check('the histograms start again for the next lap', (S.lapFloorHistF.n or 0) + (S.lapFloorHistR.n or 0), 0)
end
check('sampled only on track and moving', src:find('if onTrack and speed > FLOOR_MIN_SPEED_KMH then', 1, true) ~= nil, true)
-- v2.6.2: the floor height comes from floorSample (the collider when the
-- live check allows it, else the pickups); same 1 mm / 0.5 s rule.
check('floor contacts at 1 mm or less, 0.5 s apart',
  src:find('if fF <= COLLIDER.HIT_M and self.cd.floorF <= 0 then self.floorHitsF = self.floorHitsF + 1; self.cd.floorF = 0.5 end', 1, true) ~= nil
  and src:find('HIT_M = 0.001,', 1, true) ~= nil, true)
check('splitter / diffuser ground heights read under pcall', src:find('local okGH, ghF, ghD = pcall(function()', 1, true) ~= nil, true)
check('track contacts: the track, a real depth, 0.3 s apart',
  src:find("if okC and type(depth) == 'number' and depth > 0 and with == 0 and self.cd.contact <= 0 then", 1, true) ~= nil
  and src:find('self.cd.contact = 0.3', 1, true) ~= nil, true)
check('window counters for floor contacts', src:find("'floorHitsF', 'floorHitsR'", 1, true) ~= nil, true)
check('cooldowns declared at reset', src:find('floorF = 0, floorR = 0, contact = 0,', 1, true) ~= nil, true)
check('window accumulators reset at reset AND consumeWindow',
  select(2, src:gsub('self%.ghFrontSum, self%.ghFrontN, self%.ghDiffSum, self%.ghDiffN = 0, 0, 0, 0', '')), 2)

------------------------------------------------------------------------------
print('')
print('=== 4. ride height to the floor: down to 10 mm off it, never into the aero stall ===')
local stepConsts = ''
for _, c in ipairs({'FLOOR_TARGET_MM', 'FLOOR_LOWER_TRAVEL_MAX', 'RIDE_MAX_CLICKS'}) do
  stepConsts = stepConsts .. (src:match('\nlocal ' .. c .. ' = [^\n]+') or ('local ' .. c .. ' = nil')) .. '\n'
end
local okStep, FS = pcall(function()
  return assert(load(stepConsts .. fn('floorClearanceStep') .. '\n' .. fn('floorClicks') .. '\n'
    .. 'return {step = floorClearanceStep, clicks = floorClicks}', 'chunkS', 't', {math = math, string = string}))()
end)
check('floorClearanceStep / floorClicks exist', okStep, true)
if okStep then
  local function base(over)
    local a = {clrF = 30, clrR = 34, slopeF = 1.0, slopeR = 1.0, reliableF = true, reliableR = true,
      useF = 0.80, useR = 0.85, bottomingF = false, bottomingR = false, stallRoomMm = nil}
    for k, v in pairs(over or {}) do a[k] = v end
    return a
  end
  local act, mm, why = FS.step(base())
  check('30 / 34 mm off the floor, nothing else in the way -> lower 20 mm', act .. ' ' .. mm, 'lower 20')
  act, mm = FS.step(base({stallRoomMm = 6}))
  check('...the splitter 6 mm above its stall -> lower 6 mm only', act .. ' ' .. mm, 'lower 6')
  act, mm, why = FS.step(base({stallRoomMm = 0.5}))
  check('...0.5 mm above the stall -> hold, and says it is the stall', act == 'hold' and why:find('stall') ~= nil, true)
  act, mm = FS.step(base({clrF = 6}))
  check('front 6 mm off the floor -> raise 4 mm', act .. ' ' .. mm, 'raise 4')
  act, mm = FS.step(base({clrF = 6, reliableF = false, reliableR = false, bottomingF = true}))
  check('...raising waits for nothing (no calibration, bottoming)', act .. ' ' .. mm, 'raise 4')
  act, mm, why = FS.step(base({bottomingR = true}))
  check('rear running out of travel -> never lowered', act == 'hold' and why:find('travel') ~= nil, true)
  act = FS.step(base({useF = 0.92}))
  check('front using 92% of its travel -> hold (lowered only under 90%)', act, 'hold')
  act, mm, why = FS.step(base({reliableR = false}))
  check('rear mm-per-click not reliable -> hold, says the calibration', act == 'hold' and why:find('calibration') ~= nil, true)
  act = FS.step(base({clrF = 10.6, clrR = 12}))
  check('0.6 mm to spare at 1.0 mm a click -> hold (within one click)', act, 'hold')
  local noF = base(); noF.clrF = nil
  act = FS.step(noF)
  check('no front clearance measured -> hold', act, 'hold')
  local noUse = base(); noUse.useR = nil
  act = FS.step(noUse)
  check('no rear travel use measured -> hold', act, 'hold')

  local cF, cR, applied = FS.clicks('lower', 20, 1.0, 1.0, true, true)
  check('lower 20 mm at 1 mm a click -> 3 clicks each end (the cap), 3 mm', string.format('%d/%d/%g', cF, cR, applied), '3/3/3')
  cF, cR, applied = FS.clicks('lower', 6, 1.0, 1.5, true, true)
  check('lower: the same millimetres at both ends, rounded down (3 mm: F 3, R 2)', string.format('%d/%d/%g', cF, cR, applied), '3/2/3')
  cF, cR = FS.clicks('lower', 2.6, 1.25, 1.25, true, true)
  check('lower 2.6 mm at 1.25 mm a click -> 2 clicks (never past the target)', cF .. '/' .. cR, '2/2')
  cF, cR = FS.clicks('raise', 4, 1.5, 1.5, true, true)
  check('raise 4 mm at 1.5 mm a click -> 3 clicks (rounded up: a little high beats a strike)', cF .. '/' .. cR, '3/3')
  cF, cR = FS.clicks('raise', 4, nil, 1.0, false, true)
  check('raise without a front calibration -> 1 click at the front', cF .. '/' .. cR, '1/3')
end
check('retired: the v2.3.0 "front to the aero peak" writer', src:find("this car\\'s downforce peaks at", 1, true), nil)
check('retired: RIDE_PEAK_MARGIN_MM', src:find('RIDE_PEAK_MARGIN_MM', 1, true), nil)
check('the floor step marks what it moved', src:find("calc.touched[sec] = 'the floor-clearance target'", 1, true) ~= nil, true)
check('...and tells rake and the bottoming chains that ride height moved',
  src:find('calc.rideMoved = true', 1, true) ~= nil and src:find("if action == 'raise' then calc.floorRaised = true end", 1, true) ~= nil, true)
check('rake refuses when ride height already moved this Build',
  src:find("if calc.rideMoved then return false, 'ride height already moved this Build", 1, true) ~= nil, true)
check('the old Build-wide bottoming gate is gone (the chains and the floor step decide)',
  src:find('local bottomingActive = self.bottoming > bottomTh and botOk', 1, true) == nil
  and src:find("table.insert(changes, 'Bottoming: ' .. lapSupportNote('bottoming', botA, botC))", 1, true) == nil, true)

------------------------------------------------------------------------------
print('')
print('=== 5. the log and the panel say what Build does now ===')
check('log: the floor line', src:find("'floor (v2.6.0): ' .. (calc.notes.floor or", 1, true) ~= nil, true)
check('log: track contacts, logged only', src:find("'track contacts (v2.6.0, logged only): ", 1, true) ~= nil, true)
check('log: calculated targets report the floor step (not the aero peak)',
  src:find("table.insert(parts, string.format('ride height to the floor: %s", 1, true) ~= nil, true)
check('panel: running out of travel = the bottoming chain, one move at a time',
  src:find('bottoming chain one move at a time: packers > slow bump > fast bump > springs', 1, true) ~= nil, true)
check('panel: no promise to raise ride height for bottoming',
  src:find('Build will raise ride height (springs are a separate, stricter check', 1, true), nil)
check('panel: no "stiffen both" slow dampers for bottoming', src:find('with bottoming → stiffen both (try 1 click)', 1, true), nil)
check('panel: fast dampers no longer stiffened for bottoming', src:find("'bottoming too, so support the travel'", 1, true), nil)
check('panel: springs are the chain\'s 4th fix, +10% at most', src:find('springs are the 4th fix of its bottoming chain', 1, true) ~= nil, true)
check('VERSION 3.1.0', src:find("local VERSION = '3.1.0'", 1, true) ~= nil, true)
-- A top-level local is only visible BELOW its declaration: the panel
-- (buildAdvice) would read these as nil globals and error in game.
local adviceAt = src:find('\nfunction engine:buildAdvice(', 1, true) or 0
for _, c in ipairs({'SPRING_MAX_STEP', 'SPRING_TARGET_USE', 'FLOOR_TARGET_MM', 'FLOOR_LOWER_TRAVEL_MAX'}) do
  check(c .. ' declared above the panel code that uses it', (src:find('\nlocal ' .. c .. ' = ', 1, true) or math.huge) < adviceAt, true)
end

------------------------------------------------------------------------------
print('')
print('=== 6. the new code paths run as shipped: the floor step\'s writes, the panel lines ===')
-- The floor step's block from buildOptimalSetup, verbatim, on stub Build locals.
local floorAt = src:find('\n    do\n      local bins = windowBins(self)', 1, true)
check('floor step block found', floorAt ~= nil, true)
if floorAt and okStep then
  local floorBlock = extractFrom(floorAt + 1)
  local FB = {}
  local envF = setmetatable({
    windowBins = function() return FB.bins end,
    travelSignal = function(_, e) return FB.travel and FB.travel[e] or nil end,
    floorClearanceStep = FS.step, floorClicks = FS.clicks, th = 2, FLOOR_TARGET_MM = 10,
    rideDir = function(front) return FB.up, FB.measured end,
    firstPresent = function(a, b) if P[a] then return a end if P[b] then return b end return nil end,
    writeAbs = envT.writeAbs, getCurVal = envT.getCurVal, parsed = P,
    NUDGE_FRACTION = {ride = 0.1}, EV_UNIT = {one = 'lap', many = 'laps'},
  }, {__index = _G})
  local runFloor = assert(load('return function(self, rideMap, calc, rangeLimits)\n' .. floorBlock .. '\nend', 'floorBlock', 't', envF))()
  local function car(o)
    fresh()
    for _, c in ipairs({'LF', 'RF', 'LR', 'RR'}) do P['ROD_LENGTH_' .. c] = o.at or 10 end
    local map = {}
    for _, c in ipairs({'LF', 'RF', 'LR', 'RR'}) do map['ROD_LENGTH_' .. c] = item('ROD_LENGTH_' .. c, 0, 20, 1) end
    FB.bins, FB.travel, FB.up, FB.measured = {}, o.travel, o.up or 1, o.measured
    for i, f in ipairs(o.clrF or {}) do
      FB.bins[i] = {clrF = f, clrR = o.clrR and o.clrR[i], travelUseF = 0.80, travelUseR = 0.85, floorHitsF = o.hits or 0, floorHitsR = 0}
    end
    local S = {aeroPeaks = o.peaks, ghFrontSum = (o.ghF or 0) * 40, ghFrontN = o.ghF and 40 or 0,
      ghDiffSum = (o.ghD or 0) * 40, ghDiffN = o.ghD and 40 or 0, hsRhFSum = 0, hsRhFN = 0,
      rideCalSlope = function(_, e) local s = o.slope and o.slope[e]; if s then return s, 3, true end; return nil, 0, false end}
    local calc, limits = {touched = {}, notes = {}}, {}
    local ok, err = pcall(runFloor, S, map, calc, limits)
    return ok, err, calc, limits
  end
  local ok, err, calc, limits = car({clrF = {29, 30, 31}, clrR = {34, 35, 33}, slope = {F = 1.0, R = 1.0}, measured = true})
  check('GT3 30 / 34 mm off the floor, calibrated: the block runs', ok, true)
  if not ok then print('    ' .. tostring(err)) end
  check('...all four corners down 3 clicks (the cap)', P.ROD_LENGTH_LF .. P.ROD_LENGTH_RF .. P.ROD_LENGTH_LR .. P.ROD_LENGTH_RR, '7777')
  check('...marked, and ride height moved this Build', calc.touched.ROD_LENGTH_LF == 'the floor-clearance target' and calc.rideMoved == true and calc.floorRaised == nil, true)
  check('...the log line says what and why', calc.notes.floor and calc.notes.floor:find('LOWER 3 mm %(F 3 clicks, R 3 clicks%)') ~= nil
    and calc.notes.floor:find('F 30 / R 34 mm over 3 laps') ~= nil, true)
  ok, err, calc = car({clrF = {5, 6, 7}, clrR = {20, 21, 22}})
  check('front 6 mm off the floor, no calibration: raise 1 click a corner', ok and P.ROD_LENGTH_LF == 11 and P.ROD_LENGTH_RR == 11, true)
  if not ok then print('    ' .. tostring(err)) end
  check('...says to verify the direction', W[#W] and W[#W]:find('verify direction') ~= nil, true)
  check('...and holds the bottoming chains this Build', calc.floorRaised, true)
  ok, err, calc, limits = car({clrF = {5, 6, 7}, clrR = {20, 21, 22}, at = 20})
  check('already at the top of the range: nothing moves, the range limit is named', ok and P.ROD_LENGTH_LF == 20 and #limits == 4 and calc.rideMoved == nil, true)
  check('...the log says not moved', calc.notes.floor and calc.notes.floor:find('not moved') ~= nil, true)
  ok, err, calc = car({})
  check('no clearance data: HOLD, nothing written', ok and P.ROD_LENGTH_LF == 10 and calc.notes.floor:find('HOLD %- no floor clearance measured') ~= nil, true)
  ok, err, calc = car({clrF = {29, 30, 31}, clrR = {34, 35, 33}, slope = {F = 2.0, R = 2.0}, measured = true,
    peaks = {front = 0.050, diffuser = 0.040}, ghF = 0.056, ghD = 0.043})
  check('aero car: lowered only to the diffuser\'s stall room (3 mm = 1 click at 2 mm)', ok and P.ROD_LENGTH_LF == 9, true)
  check('...the log names both surfaces', calc.notes.floor and calc.notes.floor:find('splitter 6 mm above its 50 mm peak, diffuser 3 mm above its 40 mm peak') ~= nil, true)
  ok, err, calc = car({clrF = {29, 30, 31}, clrR = {34, 35, 33}, slope = {F = 1.0, R = 1.0}, measured = true, travel = {R = 'bottoming'}})
  check('rear running out of travel: HOLD', ok and P.ROD_LENGTH_LF == 10 and calc.notes.floor:find('HOLD %- the rear runs out of travel') ~= nil, true)
end

-- The panel lines, verbatim from buildAdvice.
local PV = {}
local envP = setmetatable({
  item = function(id, st, text) return {id = id, status = st, text = text} end,
  travelSignal = function(_, e) local t = PV[e] or {}; return t[1], t[2] or 0, 0, t[3] or 0, t[4] or 0 end,
  EV_UNIT = {one = 'lap', many = 'laps'}, SPRING_MAX_STEP = B.STEP, SPRING_TARGET_USE = B.USE, FLOOR_TARGET_MM = 10,
  sectorSuffix = function() return '' end, th = 2, bottomTh = 4, usedF = 97, usedR = 60,
}, {__index = _G})
envP.lapSupportNote = assert(load(fn('lapSupportNote') .. '\nreturn lapSupportNote', 'lsn', 't', envP))()
local susStart = src:find("  local tvF, tvHitsF = travelSignal(self, 'F', th)", 1, true)
local susStop = susStart and src:find('  elseif self.highPush > th or self.highSnap > th then', susStart, true)
local springsAt = src:find('  if self.springsHitsF > th or self.springsHitsR > th then\n', 1, true)
local fastAt = src:find('  local function fastAdvice(e, bumpN, rebN, endWord, id)', 1, true)
local slowAt = src:find('  local function slowDamperAdvice(', 1, true)
check('panel blocks found', susStop ~= nil and springsAt ~= nil and fastAt ~= nil and slowAt ~= nil, true)
if susStop and springsAt and fastAt and slowAt then
  local sus = assert(load('return function(self)\nlocal suspensionItem\n' .. src:sub(susStart, susStop - 1)
    .. 'else suspensionItem = item("SUSPENSION", "rest", "") end\nreturn suspensionItem\nend', 'sus', 't', envP))()
  local spr = assert(load('return function(self)\nlocal springsItem\n' .. extractFrom(springsAt) .. '\nreturn springsItem\nend', 'spr', 't', envP))()
  local fast = assert(load('return function(self)\n' .. extractFrom(fastAt) .. '\nreturn fastAdvice\nend', 'fast', 't', envP))()
  local slow = assert(load('return function(self)\n' .. extractFrom(slowAt) .. '\nreturn slowDamperAdvice\nend', 'slow', 't', envP))()
  PV.F, PV.R = {'bottoming', 14, 5, 7}, {nil, 5, 2, 7}
  local SELF2 = {bottoming = 9, springsHitsF = 14, springsHitsR = 5}
  local ok, it = pcall(sus, SELF2)
  check('SUSPENSION, front running out of travel: names the chain', ok and it.status == 'act' and it.text:find('Running out of travel at the front on most laps') ~= nil
    and it.text:find('springs %(%+10%% max%) > ride height') ~= nil, true)
  if not ok then print('    ' .. tostring(it)) end
  PV.F = {nil, 3, 1, 7}
  ok, it = pcall(sus, SELF2)
  check('SUSPENSION, vertical-G bottoming only: watched, no bottoming change', ok and it.status == 'warn' and it.text:find('so no bottoming change') ~= nil
    and it.text:find('within 10 mm of the track') ~= nil, true)
  PV.F = {'bottoming', 14, 5, 7}
  ok, it = pcall(spr, SELF2)
  check('SPRINGS: front = 4th fix (+10%, 95%), rear = too few laps', ok and it.status == 'act' and it.text:find('springs are the 4th fix of its bottoming chain') ~= nil
    and it.text:find('at most %+10%% a Build, aiming at 95%% travel use') ~= nil and it.text:find('Rear max%-travel hits %(5%) seen in only 2 of 7 laps') ~= nil, true)
  if not ok then print('    ' .. tostring(it)) end
  local fa = fast(SELF2)
  ok, it = pcall(fa, 'F', 5, 3, 'front', 'FAST FRONT DAMPERS')
  check('FAST FRONT, end running out of travel: left to the chain', ok and it.text:find('left to the bottoming chain: fast bump is its 3rd fix') ~= nil, true)
  ok, it = pcall(fa, 'R', 5, 3, 'rear', 'FAST REAR DAMPERS')
  -- v2.6.1: Build no longer softens fast dampers for kerbs, so the panel
  -- reports the hits and promises nothing.
  check('FAST REAR, kerbs only: reported, no soften promised (v2.6.1)', ok and it.status == 'ok'
    and it.text:find('Build leaves fast dampers alone here', 1, true) ~= nil and it.text:find('soften', 1, true) == nil, true)
  ok, it = pcall(fa, 'R', 1, 0, 'rear', 'FAST REAR DAMPERS')
  check('FAST REAR, quiet: good', ok and it.status == 'ok' and it.text == 'Fast rear damping good', true)
  local sda = slow(SELF2)
  SELF2.damperHistVerdict = function() return {text = 'damper histogram F: test'} end
  local okS, st, txt = pcall(sda, 'F', true, 'Front')
  check('FRONT DAMPERS, running out of travel: left to the chain, rebound never', okS and st == 'act' and txt:find('slow bump is its 2nd fix, rebound is never stiffened') ~= nil, true)
end

print('')
print(string.format('%d passed, %d failed', pass, fail))
os.exit(fail == 0 and 0 or 1)
