-- Relaxed lever rules, as shipped: three tries before a lever freezes, a
-- 10% drop counts as helped, no put-backs, and a pass with no measurable
-- gain starts the next pass instead of stopping the branch. Same harness
-- as test_branch_passes.lua (the real chain runner, Build by Build).
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

print('=== shipped constants ===')
check('effect drop 10%', tonumber(src:match('\nlocal LEVER_EFFECT_DROP = ([%d%.]+)')), 0.10)
check('freeze after 3', tonumber(src:match('\nlocal LEVER_FREEZE_AFTER = (%d+)')), 3)
check('4 passes', tonumber(src:match('\nlocal BRANCH_MAX_PASSES = (%d+)')), 4)
check('put-backs off by default', E.branchPutBack, nil)

print('')
print('=== a lever gets three tries; moves are kept ===')
local ch = build({low = 'loose', lowSnap = 60})
check('B1 ARB rear softer', P.ARB_REAR, 4)
build({low = 'loose', lowSnap = 56})            -- 6.7% down: no effect
check('B2 no effect -> ARB again', P.ARB_REAR, 3)
build({low = 'loose', lowSnap = 55})            -- second no effect
check('B3 still not frozen -> ARB a third time', P.ARB_REAR, 2)
check('B3 ledger 2 no-effect, not frozen', ledgerEntry('low-loose', 'arb').frozen, false)
build({low = 'loose', lowSnap = 55})            -- third no effect -> frozen
check('B4 ARB frozen after three tries', ledgerEntry('low-loose', 'arb').frozen, true)
check('B4 rear dampers take over', P.DAMP_REBOUND_LR, 9)
build({low = 'loose', lowSnap = 49})            -- 10.9% down: helped
check('B5 a 10% drop counts as helped -> rear dampers again', branch('low-loose').moves[4].result, 'helped')
check('B5 rear rebound 8', P.DAMP_REBOUND_LR, 8)

print('')
print('=== a pass with no gain: nothing put back, the next pass starts ===')
local B = 'car_relaxed'
env.parsed = {ARB_FRONT = 5, ARB_REAR = 2, DAMP_REBOUND_LR = 2, DAMP_REBOUND_RR = 2, TOE_OUT_LR = -9, TOE_OUT_RR = -9, WING_2 = 4}
P = env.parsed
build({car = B, low = 'loose', lowSnap = 50})   -- ARB 2 -> 1
build({car = B, low = 'loose', lowSnap = 49})   -- ARB 1 -> 0
build({car = B, low = 'loose', lowSnap = 49})   -- ARB at 0: dampers 2 -> 1
build({car = B, low = 'loose', lowSnap = 49})   -- dampers 1 -> 0
build({car = B, low = 'loose', lowSnap = 49})   -- toe -9 -> -10
ch = build({car = B, low = 'loose', lowSnap = 49})   -- nothing left to move
check('pass 1 ENDED with no gain', has(ch, 'pass 1 ENDED.* = NO GAIN as a group'), true)
check('nothing put back', has(ch, 'put back'), false)
check('moves kept: ARB 0, rebound 0, toe -10', P.ARB_REAR .. '/' .. P.DAMP_REBOUND_LR .. '/' .. P.TOE_OUT_LR, '0/0/-10')
check('no-gain starts pass 2 instead of stopping', has(ch, 'pass 2 starts from the top'), true)
check('branch active in pass 2', branch('low-loose', B).state .. '/' .. tostring(branch('low-loose', B).pass), 'active/2')
check('never "STOPPED" after one pass', has(ch, 'STOPPED'), false)

print('')
print(string.format('%d passed, %d failed', pass, fail))
os.exit(fail == 0 and 0 or 1)
