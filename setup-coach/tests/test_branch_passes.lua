-- v2.4.0: branch passes. The shipped chain runner (the whole `do` block,
-- unedited) is extracted from the app and driven Build by Build with stub
-- Build locals: a fake setup, scripted verdicts/rates, and levers that move
-- real section values. The real judgePendingLevers / ledger / branch-store
-- code runs alongside it, and the app's commit step is replayed after each
-- Build exactly as buildOptimalSetup does it.

local appPath = arg[1] or 'D:/SteamLibrary/steamapps/common/assettocorsa/apps/lua/setupcoach/SetupCoach.lua'
local f = assert(io.open(appPath, 'r'))
local src = f:read('a')
f:close()

local pass, fail = 0, 0
local function check(label, got, want)
  if got == want then pass = pass + 1; print(string.format('  PASS  %-78s %s', label, tostring(got)))
  else fail = fail + 1; print(string.format('  FAIL  %-78s got %s want %s', label, tostring(got), tostring(want))) end
end

------------------------------------------------------------------------------
-- Extraction. Counts function / if / do (which covers for and while) against
-- end, after stripping escapes, comments and strings.
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
local function fn(name) local s = src:find('\nlocal function ' .. name .. '%('); assert(s, name); return extractFrom(s + 1) end
local function method(name) local s = src:find('\nfunction engine:' .. name .. '%('); assert(s, name); return extractFrom(s + 1) end
local function const(name) local l = src:match('\nlocal ' .. name .. ' = [^\n]+'); assert(l, name); return l end

local runnerStart = src:find("\n  do\n    local lowV, lowPush, lowSnap, lowNote, lowRate = regimeVerdict%(self, 'low', th%)")
assert(runnerStart, 'chain runner block not found')
local runner = extractFrom(runnerStart + 1)
check('runner block extracted whole (ends with the branches store)', runner:find('self%.branchStoreNext = serialiseBranchStore%(ordered%)') ~= nil, true)

local chunk = 'local engine = {}\n'
for _, nm in ipairs({'SLIGHT_OVERSTEER_PER_100', 'LEVER_EFFECT_DROP', 'LEVER_FREEZE_AFTER', 'LEVER_MAX_JUMP',
    'LEVER_NOISE_K', 'BRANCH_MAX_PASSES', 'BRANCH_KEEP_RECORDS', 'LEDGER_KEEP_CARS', 'KEYED_KEEP'}) do
  chunk = chunk .. const(nm) .. '\n'
end
-- This file drives the put-back / stop-on-no-gain machinery under the
-- stricter rules it was written for; test_v310_relaxed_levers.lua covers
-- the shipped defaults.
chunk = chunk .. 'LEVER_EFFECT_DROP = 0.15\nLEVER_FREEZE_AFTER = 2\nBRANCH_MAX_PASSES = 3\n'
chunk = chunk .. '\nlocal settings = settings or {}\n' .. assert(src:match('\n%-%- BALANCE MODES BEGIN.-%-%- BALANCE MODES END'), 'balance modes block') .. '\n' .. 'function engine:balanceModeNow() return balanceMode() end\n' .. src:match('\nlocal LEVER_CHAINS = %b{}') .. '\n' .. src:match('\nlocal LEVER_MODULE = %b{}') .. '\n'
  .. fn('clamp') .. '\n' .. fn('n') .. '\n'
  .. fn('parseKeyedStore') .. '\n' .. fn('serialiseKeyedStore') .. '\n' .. fn('keyedGet') .. '\n'
  .. fn('keyedPut') .. '\n' .. fn('keyedDropCar') .. '\n'   -- v2.5.0 per car + track
  .. fn('parseLedgerStore') .. '\n' .. fn('fmtNum') .. '\n' .. fn('parseSecList') .. '\n' .. fn('serialiseSecList') .. '\n'
  .. fn('parseBranchStore') .. '\n' .. fn('serialiseBranchStore') .. '\n' .. fn('branchKeepValues') .. '\n'
  .. fn('branchGroupEffect') .. '\n' .. fn('branchGotWorse') .. '\n' .. fn('lapSupportNote') .. '\n'   -- v2.6.0
for _, m in ipairs({'leverLedgerFor', 'leverLedgerSave', 'judgePendingLevers', 'leverHistoryReset'}) do
  chunk = chunk .. method(m) .. '\n'
end
chunk = chunk .. 'local function runRunner()\n' .. runner .. '\nend\n'
  .. 'return {engine = engine, run = runRunner, parseB = parseBranchStore, serB = serialiseBranchStore,'
  .. ' keep = branchKeepValues, group = branchGroupEffect, worse = branchGotWorse, parseL = parseLedgerStore, fmtNum = fmtNum,'
  .. ' parseK = parseKeyedStore, serK = serialiseKeyedStore, getK = keyedGet, putK = keyedPut}'

------------------------------------------------------------------------------
-- The stub world.
------------------------------------------------------------------------------
local settings = {writeARB = true, writeDampersRear = true, writeToeRear = true, writeToeFront = true,
  writeSuspension = true, writeAero = true, leverLedger = '', leverPending = '', branchState = '', buildSerial = 0,
  writeDampersFront = true, writeFastDampersFront = true, writeFastDampersRear = true, writeSprings = true}  -- v2.6.0
local W = {}   -- scripted per Build: verdicts, counts, se, refuse
local ITEMS = {
  ARB_FRONT = {min = 0, max = 10, step = 1}, ARB_REAR = {min = 0, max = 10, step = 1},
  DAMP_REBOUND_LR = {min = 0, max = 20, step = 1}, DAMP_REBOUND_RR = {min = 0, max = 20, step = 1},
  TOE_OUT_LR = {min = -10, max = 10, step = 1}, TOE_OUT_RR = {min = -10, max = 10, step = 1},
  WING_2 = {min = 0, max = 12, step = 1},
  -- v2.6.0: the bottoming chains
  PACKER_RANGE_LF = {min = 0, max = 10, step = 1}, PACKER_RANGE_RF = {min = 0, max = 10, step = 1},
  PACKER_RANGE_LR = {min = 0, max = 10, step = 1}, PACKER_RANGE_RR = {min = 0, max = 10, step = 1},
  DAMP_BUMP_LF = {min = 0, max = 20, step = 1}, DAMP_BUMP_RF = {min = 0, max = 20, step = 1},
}
local list, managed = {}, {}
for sec, it in pairs(ITEMS) do it.section = sec; table.insert(list, it); managed[sec] = true end
local env
local function clampN(v, lo, hi) return math.max(lo, math.min(hi, v)) end
local function writeTuned(it, sec, dir, clicks, frac, desc)
  local p, calc, changes = env.parsed, env.calc, env.changes
  local cur = p[sec]
  local newV = clampN(cur + dir * clicks * it.step, it.min, it.max)
  if newV == cur then return true, false end
  if calc.touched[sec] then
    table.insert(changes, desc .. ': NOT moved - already set by ' .. (type(calc.touched[sec]) == 'string' and calc.touched[sec] or 'a calculated target') .. ' this Build')
    return true, false
  end
  if W.refuse and W.refuse[sec] then table.insert(changes, desc .. ': NOT written - floor'); return true, false end
  p[sec] = newV
  table.insert(changes, string.format('%s: %s -> %s', desc, tostring(cur), tostring(newV)))
  calc.lastClicks = math.max(calc.lastClicks, clicks)
  return true, true
end
local function moveAll(secs, dir, clicks, desc)
  local moved = false
  for _, sec in ipairs(secs) do
    local _, ch = writeTuned(ITEMS[sec], sec, dir, clicks, 0.07, desc)
    moved = moved or ch == true
  end
  return moved
end
local levers = {
  arb = function(regime, direction, jump)
    if not settings.writeARB then return false, 'module off' end
    if regime ~= 'low' then return false, 'mechanical lever, low-speed only' end
    local sec = direction == 'loose' and 'ARB_REAR' or 'ARB_FRONT'
    if moveAll({sec}, -1, jump or 1, 'ARB') then return true, 'moved' end
    return false, 'at its limit'
  end,
  rearDampers = function(regime, direction, jump)
    if not settings.writeDampersRear then return false, 'module off' end
    if moveAll({'DAMP_REBOUND_LR', 'DAMP_REBOUND_RR'}, -1, jump or 1, 'Rear rebound') then return true, 'moved' end
    return false, 'at its limit'
  end,
  toeRear = function(regime, direction)
    if not settings.writeToeRear then return false, 'module off' end
    if moveAll({'TOE_OUT_LR', 'TOE_OUT_RR'}, -1, 1, 'Rear toe') then return true, 'moved' end
    return false, 'at its limit'
  end,
  toeFront = function() return false, 'no turn-in signal' end,
  rake = function() return false, 'rake already at its floor' end,
  wings = function(regime, direction, jump)
    if regime ~= 'high' then return false, 'aero lever, high-speed only' end
    if moveAll({'WING_2'}, 1, jump or 1, 'Rear wing') then return true, 'moved' end
    return false, 'at its limit'
  end,
  -- v2.6.0: bottoming levers (the real ones are tested in test_v260_bottoming_floor)
  packersF = function(_, _, jump)
    if W.noPackers then return false, 'no adjustable front packer range on this car' end
    if moveAll({'PACKER_RANGE_LF', 'PACKER_RANGE_RF'}, 1, jump or 1, 'Packer range front') then return true, 'moved' end
    return false, 'front packer range already at its limit'
  end,
  bumpF = function(_, _, jump)
    if moveAll({'DAMP_BUMP_LF', 'DAMP_BUMP_RF'}, 1, jump or 1, 'Front bump') then return true, 'moved' end
    return false, 'front slow bump already at its limit'
  end,
  fastBumpF = function() return false, 'no adjustable front fast bump on this car' end,
  springRateF = function() return false, 'front springs already at their stiffest' end,
  rideRaiseF = function() return false, 'front ride height already at its limit' end,
  packersR = function(_, _, jump)
    if moveAll({'PACKER_RANGE_LR', 'PACKER_RANGE_RR'}, 1, jump or 1, 'Packer range rear') then return true, 'moved' end
    return false, 'rear packer range already at its limit'
  end,
  bumpR = function() return false, 'no adjustable rear slow bump on this car' end,
  fastBumpR = function() return false, 'no adjustable rear fast bump on this car' end,
  springRateR = function() return false, 'rear springs already at their stiffest' end,
  rideRaiseR = function() return false, 'rear ride height already at its limit' end,
}
env = {math = math, string = string, table = table, pairs = pairs, ipairs = ipairs, tostring = tostring,
  tonumber = tonumber, type = type, next = next, select = select, print = print,
  settings = settings, th = 2, levers = levers, MANAGED_SECTIONS = managed, arbMap = {},
  schema = {list}, writeTuned = writeTuned,
  schemaWithLive = function(l) local m = {}; for _, it in ipairs(l) do m[it.section] = it end; return m end,
  getCurVal = function(p, sec) return p[sec] end,
  ensureSectionValue = function(p, sec, text) p[sec] = tonumber(text) end,
  balanceLeftAloneNote = function() return nil end,
  regimeVerdict = function(_, regime) local c = W.counts[regime]; return W.verdict[regime], c.push, c.snap, 'note', 0 end,
  regimeCounts = function(_, regime) local c = W.counts[regime]; return c.push, c.snap end,
  -- v2.6.0: scripted per Build: {verdict, hits, rate per 100, laps agreeing, laps}
  travelSignal = function(_, e) local t = W.travel and W.travel[e]; if t then return t[1], t[2], t[3], t[4], t[5] end; return nil, 0, 0, 0, 0 end,
  EV_UNIT = {one = 'lap', many = 'laps'},
  -- v2.6.1: the rebound-follows-springs step in the runner. No damping
  -- ratio in this stub world, so it stands aside (tested for real in
  -- test_v261_rebound_follows.lua).
  zetaOf = function() return nil end, calcDamperMap = {BUMP = {}, REBOUND = {}},
}
local A = assert(load(chunk, 'extracted', 't', env))()
local E = A.engine
E.branchPutBack, E.branchStopOnNoGain = true, true
E.corneringSamples = 100                       -- rates per 100 corners = the counts
E.lapRateStats = function(_, regime) return 0, W.se, 4 end
env.self = E

local CAR = 'ks_lamborghini_huracan_gt3'
local TRACK = 'ks_silverstone'
env.parsed = {ARB_FRONT = 5, ARB_REAR = 5, DAMP_REBOUND_LR = 10, DAMP_REBOUND_RR = 10, TOE_OUT_LR = -2, TOE_OUT_RR = -2, WING_2 = 4}

-- One Build: judge (real), run the runner (real), commit (as the app does).
local function build(o)
  W.verdict = {low = o.low, high = o.high}
  W.counts = {low = {push = o.lowPush or 10, snap = o.lowSnap or 0}, high = {push = o.highPush or 5, snap = o.highSnap or 0}}
  W.se, W.refuse = o.se == nil and 3 or (o.se or nil), o.refuse
  W.travel, W.noPackers = {F = o.travelF, R = o.travelR}, o.noPackers   -- v2.6.0
  if o.se == false then W.se = nil end
  env.carFolder, env.trackFolder = o.car or CAR, o.track or TRACK
  env.lastBuildLoadedVerdict = o.loaded or 'YES'
  env.changes, env.calc = {}, {touched = o.touched or {}, lastClicks = 0, floorRaised = o.floorRaised}
  local effect = E:judgePendingLevers(env.carFolder, 2, env.lastBuildLoadedVerdict, env.trackFolder)
  A.run()
  local changes = env.changes
  if #changes == 0 then
    if E.branchStoreNext then settings.branchState = E.branchStoreNext end
    E.branchStoreNext = nil
    E:leverLedgerSave(env.carFolder)
    return changes, effect
  end
  settings.buildSerial = settings.buildSerial + 1
  local items = {}
  for _, p in ipairs(E.leverPendingThisBuild or {}) do
    table.insert(items, string.format('%s:%s:%.2f:%d:%.2f', p.key, p.lever, p.rateBefore, p.clicks or 1, p.se or -1))
  end
  -- v2.5.0 commit, as the app does it: one record per car + track, "serial#items".
  local plist = A.parseK(settings.leverPending)
  A.putK(plist, env.carFolder, env.trackFolder, (#items > 0) and (settings.buildSerial .. '#' .. table.concat(items, ';')) or nil)
  settings.leverPending = A.serK(plist)
  E:leverLedgerSave(env.carFolder)
  if E.branchStoreNext then settings.branchState = E.branchStoreNext end
  E.branchStoreNext = nil
  return changes, effect
end
local function has(changes, pat)
  for _, c in ipairs(changes) do if c:find(pat) then return true end end
  return false
end
local function branch(key, car, track)
  for _, b in ipairs(A.parseB(settings.branchState)) do
    if b.key == key and b.car == (car or CAR) and b.track == (track or TRACK) then return b end
  end
end
local function ledgerEntry(key, lever, car)
  E.leverLedger, E.leverLedgerCar = nil, nil
  local l = E:leverLedgerFor(car or CAR)
  return l[key] and l[key][lever]
end
local P = env.parsed

------------------------------------------------------------------------------
print('=== pure helpers ===')
check('fmtNum trims zeros', A.fmtNum(10), '10')
check('fmtNum keeps decimals, no exponent', A.fmtNum(-2.5), '-2.5')
check('fmtNum big value has no exponent (no + to clash with the move separator)', A.fmtNum(150000), '150000')
local keep, expected, why = A.keep({
  {lever = 'arb', result = 'helped', secs = {ARB_REAR = {5, 4}}},
  {lever = 'arb', result = 'no-effect', secs = {ARB_REAR = {4, 2}}},
  {lever = 'rearDampers', result = 'no-effect', secs = {DAMP_REBOUND_LR = {10, 9}}},
  {lever = 'arb', result = 'unjudged', secs = {ARB_FRONT = {5, 6}}},
})
check('keep: after the last move that helped', keep.ARB_REAR, 4)
check('...the pass left it at', expected.ARB_REAR, 2)
check('...undone lever named', why.ARB_REAR, 'arb')
check('keep: no-effect only -> the pass start value', keep.DAMP_REBOUND_LR, 10)
check('keep: never-judged move is KEPT (not known useless)', keep.ARB_FRONT, 6)
check('...nothing to undo there', why.ARB_FRONT, '')
check('group: 60 -> 44, se 3/3, noise 8.5 -> improved', (A.group(60, 3, 44, 3)), true)
check('group: 45 -> 44 inside the noise -> no gain', (A.group(45, 3, 44, 3)), false)
check('group: no lap stats, 15% rule', (A.group(60, nil, 50, nil)), true)
check('worse: 44 -> 45 inside the noise -> not worse', (A.worse(44, 3, 45, 3)), false)
check('worse: 44 -> 58 beyond it -> worse', (A.worse(44, 3, 58, 3)), true)

print('')
print('=== store round-trip ===')
local sample = {{car = 'c1', track = 't/x', key = 'low-loose', state = 'verify', pass = 2, baseRate = 45.25, baseSe = 3,
  baseBuild = 12, outcome = 'improved', verifyRate = 44, verifySe = 2.5,
  moves = {{lever = 'arb', result = 'no-effect', secs = {ARB_REAR = {4, 3}}}, {lever = 'toeRear', result = 'helped', secs = {TOE_OUT_LR = {-2, -3}, TOE_OUT_RR = {-2, -3}}}},
  reverted = {ARB_REAR = {3, 4}}}}
local back = A.parseB(A.serB(sample))[1]
check('round-trip: state / pass / outcome', back.state .. '/' .. back.pass .. '/' .. back.outcome, 'verify/2/improved')
check('round-trip: baseline', back.baseRate, 45.25)
check('round-trip: negative section values', back.moves[2].secs.TOE_OUT_RR[2], -3)
check('round-trip: reverted', back.reverted.ARB_REAR[2], 4)
check('round-trip: track with a slash', back.track, 't/x')
local many = {}
for i = 1, 45 do table.insert(many, {car = 'c' .. i, track = 't', key = 'low-loose', state = 'done', pass = 1, moves = {}, reverted = {}}) end
local trimmed = A.parseB(A.serB(many))
check('store keeps the newest 40', #trimmed .. ' ' .. trimmed[1].car, '40 c6')

print('')
print('=== ledger: one per car (v2.1-2.3 kept ONE; migration) ===')
settings.leverLedger = 'oldcar|low-loose:arb:3:2:1:no-effect:'
check('old single-car record still read', ledgerEntry('low-loose', 'arb', 'oldcar').frozen, true)
E.leverLedger, E.leverLedgerCar = nil, nil
E:leverLedgerFor('newcar')
E.leverLedger['low-tight'] = {toeFront = {tries = 1, ineff = 0, frozen = false}}
E:leverLedgerSave('newcar')
check('saving a second car keeps the first', ledgerEntry('low-loose', 'arb', 'oldcar') ~= nil, true)
check('...and the second', ledgerEntry('low-tight', 'toeFront', 'newcar') ~= nil, true)
check('new format in storage', settings.leverLedger:find('oldcar>', 1, true) ~= nil and settings.leverLedger:find('newcar>', 1, true) ~= nil, true)
settings.leverLedger = ''

------------------------------------------------------------------------------
print('')
print('=== pass 1: ARB -> rear dampers -> rear toe, then judged as a group ===')
local ch = build({low = 'loose', lowSnap = 60})
check('B1 pass 1 starts, baseline 60', has(ch, 'Branch low%-loose: pass 1 starts %- baseline 60%.0'), true)
check('B1 ARB moved (rear bar softer)', P.ARB_REAR, 4)
check('B1 pending stored for this car at this track (v2.5.0)', A.getK(A.parseK(settings.leverPending), CAR, TRACK) ~= nil, true)
check('B1 branch stored active', branch('low-loose').state, 'active')

ch = build({low = 'loose', lowSnap = 45})
check('B2 ARB helped 60 -> 45 (and measured -15/click -> 2-click jump)', P.ARB_REAR, 2)
check('B2 branch move 1 = helped', branch('low-loose').moves[1].result, 'helped')
build({low = 'loose', lowSnap = 44})
check('B3 ARB no effect -> moved again', P.ARB_REAR, 1)
ch = build({low = 'loose', lowSnap = 44})
check('B4 ARB frozen for this pass', ledgerEntry('low-loose', 'arb').frozen, true)
check('B4 rear dampers take over', P.DAMP_REBOUND_LR, 9)
build({low = 'loose', lowSnap = 43})
check('B5 rear dampers again', P.DAMP_REBOUND_RR, 8)
build({low = 'loose', lowSnap = 44})
check('B6 rear toe takes over', P.TOE_OUT_LR, -3)
build({low = 'loose', lowSnap = 44})
check('B7 rear toe again', P.TOE_OUT_LR, -4)
ch = build({low = 'loose', lowSnap = 44})
check('B8 no lever left in pass 1', has(ch, 'no lever left to move in pass 1'), true)
check('B8 pass ENDED: 60 -> 44 IMPROVED as a group', has(ch, 'Branch low%-loose pass 1 ENDED %(no lever left in the branch%): 60%.0 %(±3%.0%) → 44%.0 %(±3%.0%) per 100 corners since Build #1 %(noise 8%.5%) = IMPROVED as a group'), true)
check('B8 ARB back to 4 (after its move that helped - not 5)', P.ARB_REAR, 4)
check('B8 rear rebound back to 10 (pass start)', P.DAMP_REBOUND_LR .. '/' .. P.DAMP_REBOUND_RR, '10/10')
check('B8 rear toe back to -2', P.TOE_OUT_LR .. '/' .. P.TOE_OUT_RR, '-2/-2')
check('B8 put-back lines name the lever that did nothing', has(ch, 'Branch low%-loose put%-back: DAMP_REBOUND_LR back to 10 %(rearDampers had no effect%)'), true)
check('B8 five sections put back, next window checks', has(ch, '5 sections put back to the starting value'), true)
check('B8 branch now verify', branch('low-loose').state, 'verify')
check('B8 no lever pending (the branch sat the put-back Build out)', settings.leverPending, '')

print('')
print('=== put-backs confirmed -> pass 2 cycles back to the top ===')
ch = build({low = 'loose', lowSnap = 45})
check('B9 put-backs confirmed (44 -> 45, inside the noise)', has(ch, 'put%-backs confirmed'), true)
check('B9 pass 2 from the top, one more try for the frozen levers', has(ch, 'pass 2 starts from the top of the branch %(arb > rearDampers > springs > toeRear > toeFront > diff > rake%), baseline 45%.0 %(±3%.0%) per 100; one more try each for arb, rearDampers, toeRear'), true)
check('B9 ARB (reopened) moves first again', P.ARB_REAR, 3)
check('B9 ...with ONE try left', ledgerEntry('low-loose', 'arb').ineff, 1)
check('B9 move logged against pass 2', has(ch, 'branch pass 2%)'), true)
build({low = 'loose', lowSnap = 44})
check('B10 ARB no effect -> frozen again at once', ledgerEntry('low-loose', 'arb').frozen, true)
check('B10 rear dampers move', P.DAMP_REBOUND_LR, 9)
build({low = 'loose', lowSnap = 44})
check('B11 rear toe moves', P.TOE_OUT_LR, -3)
ch = build({low = 'loose', lowSnap = 44})
check('B12 pass 2 ENDED: 45 -> 44 = NO GAIN', has(ch, 'pass 2 ENDED.* = NO GAIN as a group'), true)
check('B12 all three put back', P.ARB_REAR .. '/' .. P.DAMP_REBOUND_LR .. '/' .. P.TOE_OUT_LR, '4/10/-2')
ch = build({low = 'loose', lowSnap = 44})
check('B13 confirmed -> STOPPED (no gain over a whole pass)', branch('low-loose').state .. '/' .. branch('low-loose').outcome, 'stopped/no-gain')
check('B13 says why', has(ch, 'a whole pass made no difference beyond the lap%-to%-lap noise'), true)
ch = build({low = 'loose', lowSnap = 44})
check('B14 stopped branch: advice only, nothing moves', has(ch, 'branch low%-loose STOPPED %(no gain as a group, pass 2'), true)
check('B14 setup untouched', P.ARB_REAR .. '/' .. P.DAMP_REBOUND_LR .. '/' .. P.TOE_OUT_LR, '4/10/-2')
check('branches log line', E.branchLogLine:find('low%-loose STOPPED pass 2 %(no%-gain%)') ~= nil, true)

print('')
print('=== Settings: reset lever history ===')
E:leverHistoryReset(CAR)
check('branch records gone', branch('low-loose'), nil)
check('ledger gone', settings.leverLedger:find(CAR, 1, true), nil)
ch = build({low = 'loose', lowSnap = 44})
check('next Build starts pass 1 afresh, ARB first', has(ch, 'pass 1 starts') and P.ARB_REAR == 3, true)

------------------------------------------------------------------------------
print('')
print('=== fixed pass; put-back makes it WORSE -> restored ===')
local B = 'car_b'
local keepP = {}
for k, v in pairs(P) do keepP[k] = v end
env.parsed = {ARB_FRONT = 5, ARB_REAR = 5, DAMP_REBOUND_LR = 10, DAMP_REBOUND_RR = 10, TOE_OUT_LR = -2, TOE_OUT_RR = -2, WING_2 = 4}
P = env.parsed
build({car = B, low = 'loose', lowSnap = 50})
build({car = B, low = 'loose', lowSnap = 49})
build({car = B, low = 'loose', lowSnap = 49})
check('ARB frozen, rear rebound moved', P.ARB_REAR .. '/' .. P.DAMP_REBOUND_LR, '3/9')
ch = build({car = B, low = nil, lowSnap = 20})
check('problem gone -> pass ENDED FIXED', has(ch, 'pass 1 ENDED %(the problem is gone%).* = FIXED'), true)
check('ARB put back to 5 (both its moves did nothing)', P.ARB_REAR, 5)
check('rear rebound kept at 9 (it helped)', P.DAMP_REBOUND_LR, 9)
ch = build({car = B, low = 'loose', lowSnap = 40})
check('problem back after the put-back -> WORSE, restored', has(ch, 'made it WORSE.* restored ARB_REAR'), true)
check('ARB restored to 3', P.ARB_REAR, 3)
check('branch DONE (the fix stands)', branch('low-loose', B).state, 'done')
check('restore Build holds the branch', has(ch, 'HELD this Build %- branch low%-loose: restored this Build'), true)
ch = build({car = B, low = 'loose', lowSnap = 40})
check('still there -> the problem is BACK, new pass 1', has(ch, 'the problem is BACK'), true)
check('pass 1 of a new episode keeps the ledger (ARB still frozen, dampers move)', P.DAMP_REBOUND_LR, 8)
check('car_a ledger survived car_b Builds', settings.leverLedger:find(CAR .. '>', 1, true) ~= nil, true)

------------------------------------------------------------------------------
print('')
print('=== what a put-back must NOT touch ===')
local C = 'car_c'
env.parsed = {ARB_FRONT = 5, ARB_REAR = 5, DAMP_REBOUND_LR = 10, DAMP_REBOUND_RR = 10, TOE_OUT_LR = -2, TOE_OUT_RR = -2, WING_2 = 4}
P = env.parsed
build({car = C, low = 'loose', lowSnap = 60})                 -- ARB 5->4
build({car = C, low = 'loose', lowSnap = 59})                 -- no effect, ARB 4->3
build({car = C, low = 'loose', lowSnap = 59})                 -- frozen, dampers 10->9
build({car = C, low = 'loose', lowSnap = 58})                 -- dampers 9->8
build({car = C, low = 'loose', lowSnap = 58})                 -- frozen, toe -2->-3
build({car = C, low = 'loose', lowSnap = 58})                 -- toe -3->-4
P.TOE_OUT_LR = -1                                             -- the driver changes left rear toe by hand
settings.writeDampersRear = false                             -- ...and switches rear dampers off
ch = build({car = C, low = 'loose', lowSnap = 58, refuse = {ARB_REAR = true}})
check('driver-changed section left alone', has(ch, 'TOE_OUT_LR left at %-1 %(changed since the pass left it at %-4'), true)
check('...its partner still put back', P.TOE_OUT_RR, -2)
check('module switched off -> left alone', has(ch, 'DAMP_REBOUND_LR left at 8 %(the rearDampers module is now off%)'), true)
check('guard refusal -> left, reported', has(ch, 'ARB_REAR left at 3 %(refused by a guard'), true)
check('only the one put back', has(ch, '1 section put back'), true)
settings.writeDampersRear = true

print('')
print('=== put-back Build not loaded -> applied again ===')
P.TOE_OUT_RR = -4                                             -- the driver never loaded it
ch = build({car = C, low = 'loose', lowSnap = 58, loaded = 'NO'})
check('put-back applied again', P.TOE_OUT_RR, -2)
check('...and held', has(ch, 'was not loaded %- applied again'), true)
check('...still verify', branch('low-loose', C).state, 'verify')

print('')
print('=== pending moves and tracks ===')
local D = 'car_d'
env.parsed = {ARB_FRONT = 5, ARB_REAR = 5, DAMP_REBOUND_LR = 10, DAMP_REBOUND_RR = 10, TOE_OUT_LR = -2, TOE_OUT_RR = -2, WING_2 = 4}
P = env.parsed
build({car = D, low = 'loose', lowSnap = 60})
local _, effect = build({car = D, track = 'spa', low = nil, lowSnap = 10})
-- v2.5.0: pending moves are kept per car + track - Spa has none of its
-- own, and Silverstone's wait there instead of being lost.
check('a window at another track does not judge Silverstone moves', effect:find('no levers pending from a previous Build on this car at this track') ~= nil, true)
check('...and Silverstone\'s move is still waiting', A.getK(A.parseK(settings.leverPending), D, TRACK) ~= nil, true)
build({car = D, low = 'loose', lowSnap = 55})
check('back at Silverstone: the move is judged there (60 -> 55, under 15% = no effect)', branch('low-loose', D).moves[1].result, 'no-effect')
check('Spa has no branch of its own (no verdict there)', branch('low-loose', D, 'spa'), nil)

print('')
print('=== the pass cap ===')
local capRec = A.serB({{car = 'car_e', track = TRACK, key = 'low-loose', state = 'verify', pass = 3, baseRate = 50, baseSe = 3,
  baseBuild = 20, outcome = 'improved', verifyRate = 30, verifySe = 3, moves = {}, reverted = {ARB_REAR = {3, 4}}}})
settings.branchState = settings.branchState .. '|' .. capRec
env.parsed = {ARB_FRONT = 5, ARB_REAR = 4, DAMP_REBOUND_LR = 10, DAMP_REBOUND_RR = 10, TOE_OUT_LR = -2, TOE_OUT_RR = -2, WING_2 = 4}
P = env.parsed
ch = build({car = 'car_e', low = 'loose', lowSnap = 31})
check('pass 3 improved -> STOPPED (capped), not a 4th pass', branch('low-loose', 'car_e').state .. '/' .. branch('low-loose', 'car_e').outcome, 'stopped/capped')
check('says so', has(ch, 'branch STOPPED after 3 passes'), true)
check('other cars\' records survive in the store', branch('low-loose', C) ~= nil and branch('low-loose', D) ~= nil, true)

------------------------------------------------------------------------------
print('')
print('=== v2.6.0: bottoming chains (packers > bump > fast bump > springs > ride height) ===')
local function at(changes, pat)
  for i, c in ipairs(changes) do if c:find(pat) then return i end end
  return math.huge
end
local function fresh()
  env.parsed = {ARB_FRONT = 5, ARB_REAR = 5, DAMP_REBOUND_LR = 10, DAMP_REBOUND_RR = 10, TOE_OUT_LR = -2, TOE_OUT_RR = -2, WING_2 = 4,
    PACKER_RANGE_LF = 5, PACKER_RANGE_RF = 5, PACKER_RANGE_LR = 5, PACKER_RANGE_RR = 5, DAMP_BUMP_LF = 5, DAMP_BUMP_RF = 5}
  P = env.parsed
end
local T = 'car_t'
local hot = {'bottoming', 10, 10, 5, 7}     -- verdict, hits, rate per 100 corners, laps agreeing, laps
fresh()
ch = build({car = T, travelF = hot})
check('T1 front runs out of travel -> branch travelF-bottoming, pass 1', has(ch, 'Branch travelF%-bottoming: pass 1 starts %- baseline 10%.0'), true)
check('T1 packers first', P.PACKER_RANGE_LF .. '/' .. P.PACKER_RANGE_RF, '6/6')
check('T1 logged as a bottoming move, with the max-travel rate banked',
  has(ch, 'Bottoming front: lever packersF moved 1 click %(first in the chain; branch pass 1%); max%-travel hits 10%.0 per 100 corners banked'), true)
check('T1 one change at a time: slow bump untouched', P.DAMP_BUMP_LF, 5)
check('T1 pending move stored under the travel key', settings.leverPending:find('travelF%-bottoming:packersF:10%.00') ~= nil, true)
check('T1 the rear and the balance untouched', P.PACKER_RANGE_LR .. '/' .. P.ARB_REAR, '5/5')
build({car = T, travelF = {'bottoming', 10, 9.5, 5, 7}})
check('T2 9.5 vs 10.0 per 100 -> no effect', branch('travelF-bottoming', T).moves[1].result, 'no-effect')
check('T2 packers again (one no-effect move does not freeze)', P.PACKER_RANGE_LF, 7)
build({car = T, travelF = {'bottoming', 10, 9.6, 5, 7}})
check('T3 packers frozen after two moves without effect', ledgerEntry('travelF-bottoming', 'packersF', T).frozen, true)
check('T3 slow bump takes over', P.DAMP_BUMP_LF .. '/' .. P.DAMP_BUMP_RF, '6/6')
check('T3 packers not moved again', P.PACKER_RANGE_LF, 7)
ch = build({car = T, travelF = {nil, 1, 1, 0, 7}})
check('T4 hits gone -> pass ENDED, FIXED', has(ch, 'Branch travelF%-bottoming pass 1 ENDED %(the problem is gone%).* = FIXED'), true)
check('T4 packers put back to the start (both moves did nothing)', P.PACKER_RANGE_LF .. '/' .. P.PACKER_RANGE_RF, '5/5')
check('T4 slow bump kept (it fixed it)', P.DAMP_BUMP_LF, 6)
check('T4 the branch checks the put-back next window', branch('travelF-bottoming', T).state, 'verify')

local U = 'car_u'
fresh()
ch = build({car = U, travelF = hot, noPackers = true})
check('car without packers: slow bump first', P.DAMP_BUMP_LF, 6)
check('...says why packers were skipped',
  has(ch, 'Bottoming front: lever bumpF moved 1 click %(#2 in the chain; skipped packersF %(no adjustable front packer range on this car%)'), true)
ch = build({car = U, travelF = hot, noPackers = true, floorRaised = true})
check('floor-clearance step raised ride height -> HELD, one change at a time',
  has(ch, 'Bottoming front: HELD this Build %- the floor%-clearance step raised ride height'), true)
check('...nothing moved', P.DAMP_BUMP_LF, 6)

local V = 'car_v'
fresh()
ch = build({car = V, travelF = {nil, 5, 5, 2, 7}})
check('hits on too few laps -> left alone, and says so',
  has(ch, 'Bottoming front: max%-travel hits seen in only 2 of 7 laps %- not a consistent trait, left alone'), true)
check('...nothing moved, no branch', P.PACKER_RANGE_LF == 5 and branch('travelF-bottoming', V) == nil, true)
ch = build({car = V, travelF = hot, travelR = hot, low = 'loose', lowSnap = 60})
check('both ends and the balance move one lever each', P.PACKER_RANGE_LF .. '/' .. P.PACKER_RANGE_LR .. '/' .. P.ARB_REAR, '6/6/4')
check('rear logged as its own chain', has(ch, 'Bottoming rear: lever packersR moved 1 click'), true)
check('the platform goes first: bottoming before balance',
  at(ch, 'Bottoming front: lever') < at(ch, 'Balance low%-speed %(loose%): lever') and at(ch, 'Bottoming rear: lever') < at(ch, 'Balance low%-speed %(loose%): lever'), true)

local X = 'car_x'
fresh()
build({car = X, travelF = {'bottoming', 20, 20, 6, 7}})
ch = build({car = X, travelF = {'bottoming', 12, 12, 5, 7}})
check('a travel lever that helped is not jumped (no measured-response jump)', P.PACKER_RANGE_LF == 7 and not has(ch, 'measured %d'), true)

------------------------------------------------------------------------------
print('')
print('=== source guards ===')
check('VERSION 2.4.0 or later', src:find("local VERSION = '[23]%.%d%.%d'") ~= nil, true)
check('settings.branchState declared', src:find('  branchState = \'\',') ~= nil, true)
check('judge gets the track', src:find('self:judgePendingLevers%(carFolder, th, lastBuildLoadedVerdict, trackFolder%)') ~= nil, true)
check('pending written per car + track (v2.5.0)', src:find("keyedPut%(list, carFolder, trackFolder, %(#items > 0%) and") ~= nil, true)
check('branch store committed on a written Build', src:find('if self%.branchStoreNext then settings%.branchState = self%.branchStoreNext end') ~= nil, true)
check('...and on a no-changes Build', select(2, src:gsub('if self%.branchStoreNext then settings%.branchState = self%.branchStoreNext end', '')), 2)
check('branches line in the log', src:find("self%.branchLogLine or 'branches: n/a',") ~= nil, true)
check('Settings reset button', src:find("ui%.button%('Reset lever history for this car'") ~= nil, true)
check('put-backs go through writeTuned (every guard applies)', src:find('writeTuned%(it, section, want > cur and 1 or %-1, clicks, 0%.07, desc%)') ~= nil, true)
check('put-back sections protected from levers that Build', src:find("calc%.touched%[sec%] = 'a branch put%-back'") ~= nil, true)
check('frozen reported per pass', src:find('FROZEN for this pass of the branch') ~= nil, true)
check('v2.6.0: bottoming chains run first, on the lap-consistent travel signal',
  src:find("runTravel('F')\n    runTravel('R')\n    run('high', highV, highNote, highPush, highSnap)", 1, true) ~= nil
  and src:find("local verdict, hits, _, agree, considered = travelSignal(self, e, th)", 1, true) ~= nil, true)

print('')
print(string.format('%d passed, %d failed', pass, fail))
os.exit(fail == 0 and 0 or 1)
