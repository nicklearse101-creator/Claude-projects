-- v2.0.0: evidence window, lap bins, the Build gate, consumption, and lap
-- consistency. Loads the shipped functions out of the app source and drives
-- them with simulated lap bins shaped like the real Corvette GT3 session.

local appPath = arg[1] or 'D:/SteamLibrary/steamapps/common/assettocorsa/apps/lua/setupcoach/SetupCoach.lua'
local f = assert(io.open(appPath, 'r'))
local src = f:read('a')
f:close()

local pass, fail = 0, 0
local function check(label, got, want)
  if got == want then pass = pass + 1; print(string.format('  PASS  %-72s %s', label, tostring(got)))
  else fail = fail + 1; print(string.format('  FAIL  %-72s got %s want %s', label, tostring(got), tostring(want))) end
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
local function extractLocal(pattern) local l = src:match(pattern); assert(l, 'not found: ' .. pattern); return l end

local env = {math = math, string = string, tonumber = tonumber, tostring = tostring, type = type,
  ipairs = ipairs, pairs = pairs, table = table, print = print, os = os, pcall = pcall}
local chunk = extractLocal('\nlocal SLIGHT_OVERSTEER_PER_100 = %d+') .. '\n' .. '\nlocal settings = settings or {}\n' .. assert(src:match('\n%-%- BALANCE MODES BEGIN.-%-%- BALANCE MODES END'), 'balance modes block') .. '\n'
  .. extractLocal('\nlocal HISTOGRAM_MIN_EVENTS = %d+') .. '\n'
  .. extractLocal('\nlocal BUILD_MIN_CORNERS = %d+') .. '\n'
  .. extractLocal('\nlocal WINDOW_KEYS = %b{}') .. '\n'
  .. extractLocal('\nlocal EV_UNIT = %b{}') .. '\n'   -- v2.5.0: 'laps' / 'sections' wording
  .. extractFn('balanceVerdict') .. '\n' .. extractFn('balanceLeftAloneNote') .. '\n'
  .. extractFn('counterSnapshot') .. '\n' .. extractFn('windowBins') .. '\n' .. extractFn('windowLapStats') .. '\n'
  .. extractFn('regimeCounts') .. '\n' .. extractFn('regimeVerdict') .. '\n'
  .. extractFn('lapSupport') .. '\n' .. extractFn('lapSupportNote') .. '\n' .. extractFn('rearHandlingSignal') .. '\n'
  .. 'return {verdict=balanceVerdict, note=balanceLeftAloneNote, snapshot=counterSnapshot, windowBins=windowBins, stats=windowLapStats, regime=regimeVerdict, support=lapSupport, rear=rearHandlingSignal, KEYS=WINDOW_KEYS, MIN_CORNERS=BUILD_MIN_CORNERS}'
local A = assert(load(chunk, 'extracted', 't', env))()
local th = 2

-- A tiny engine stand-in that does what update()'s lap boundary and
-- consumeWindow() do, using the shipped snapshot/keys.
local function newEngine()
  local e = {lapBins = {}, windowBinsStart = 0, corneringSamples = 0}
  for _, k in ipairs(A.KEYS) do e[k] = 0 end
  e.lapBoundary = A.snapshot(e)
  return e
end
local function drive(e, events)  -- add events to the running totals
  for k, v in pairs(events) do e[k] = (e[k] or 0) + v end
end
local function lapDone(e, lap, flags)
  local bin = {lap = lap, pit = flags and flags.pit or false, partial = flags and flags.partial or false, valid = not (flags and flags.invalid)}
  for _, k in ipairs(A.KEYS) do bin[k] = (e[k] or 0) - (e.lapBoundary[k] or 0) end
  table.insert(e.lapBins, bin)
  e.lapBoundary = A.snapshot(e)
end
local function consume(e)
  for _, k in ipairs(A.KEYS) do e[k] = 0 end
  e.lapBoundary = A.snapshot(e)
  e.windowBinsStart = #e.lapBins
end
local function gate(e, minLaps)
  local clean = A.stats(e)
  return clean >= minLaps and (e.corneringSamples or 0) >= A.MIN_CORNERS, clean
end

------------------------------------------------------------------------------
print('=== the Corvette sequence: Builds at 80, 88, 202, 97 corners (Nordschleife ~150/lap) ===')
local e = newEngine()
drive(e, {corneringSamples = 80, midPush = 29, midSnap = 35, highPush = 15, highSnap = 23})
local ok1, clean1 = gate(e, 2)
check('Build 1 at 80 corners, 0 complete laps -> DECLINED', ok1, false)
drive(e, {corneringSamples = 8, midPush = -4, midSnap = -3, highPush = 1, highSnap = 9})
check('Build 2 at 88 corners, still 0 laps -> DECLINED', (gate(e, 2)), false)
lapDone(e, 1, {partial = true})                      -- app loaded mid-lap: the first bin is partial
drive(e, {corneringSamples = 114, midPush = 50, midSnap = 58, highPush = 29, highSnap = 51})
check('Build 3 at 202 corners: 1 partial lap only -> DECLINED', (gate(e, 2)), false)
lapDone(e, 2)
check('...after lap 2 completes: 1 clean lap -> still DECLINED at minLaps=2', (gate(e, 2)), false)
check('...but passes at minLaps=1 (Settings slider)', (gate(e, 1)), true)
drive(e, {corneringSamples = 150, midPush = 40, midSnap = 60, highPush = 20, highSnap = 40})
lapDone(e, 3)
local ok4, clean4 = gate(e, 2)
check('after lap 3: 2 clean laps -> PASS', ok4, true)
check('clean laps counted', clean4, 2)
local _, pit, partial = A.stats(e)
check('partial lap excluded from clean count', partial, 1)

print('')
print('=== consumption: after a Build the window is empty ===')
consume(e)
check('totals zeroed', e.midSnap, 0)
check('bins fenced (windowBinsStart = 3)', e.windowBinsStart, 3)
check('gate declines again immediately', (gate(e, 2)), false)
check('window has 0 clean laps', (A.stats(e)), 0)
check('bin history kept', #e.lapBins, 3)

------------------------------------------------------------------------------
print('')
print('=== lap consistency: a one-lap oversteer spike is not a trait ===')
local s = newEngine()
-- 4 clean laps, 40 corners each; laps 1-3 balanced, lap 4 a big oversteer spike.
for lap = 1, 3 do drive(s, {corneringSamples = 40, midPush = 6, midSnap = 6}); lapDone(s, lap) end
drive(s, {corneringSamples = 40, midPush = 2, midSnap = 40}); lapDone(s, 4)
local totalsOnly = A.verdict(s, s.midPush, s.midSnap, th, true)
check('totals alone (20 push / 58 snap, 36/100) say loose', totalsOnly, 'loose')
local v, _, _, note, _, agree, considered = A.regime(s, 'low', th)
check('regimeVerdict: nil', v, nil)
check('note names the count', note, 'inconsistent 1/4')
check('agree/considered', agree .. '/' .. considered, '1/4')
check('left-alone wording', A.note(note, s.midPush, s.midSnap, 'low-speed'), 'low-speed totals (20 push / 58 oversteer) point one way but only 1 of 4 laps agree - not a consistent trait of the car, left alone')

print('')
print('=== lap consistency: a trait present in most laps acts ===')
local c = newEngine()
for lap = 1, 4 do drive(c, {corneringSamples = 40, midPush = 4, midSnap = 16}); lapDone(c, lap) end
local cv, _, _, cnote, _, ca, cc = A.regime(c, 'low', th)
check('4/4 laps loose -> loose', cv, 'loose')
check('agree 4/4', ca .. '/' .. cc, '4/4')
print('=== exactly half the laps agree -> passes (>= half) ===')
local h = newEngine()
for lap = 1, 2 do drive(h, {corneringSamples = 40, midPush = 4, midSnap = 16}); lapDone(h, lap) end
for lap = 3, 4 do drive(h, {corneringSamples = 40, midPush = 6, midSnap = 6}); lapDone(h, lap) end
check('2/4 agree -> still loose (totals 20/44, 27/100)', (A.regime(h, 'low', th)), 'loose')

print('')
print('=== fewer than 2 clean laps: consistency passes through (the gate is the guard) ===')
local one = newEngine()
drive(one, {corneringSamples = 40, midPush = 2, midSnap = 20}); lapDone(one, 1)
check('1 lap, loose totals -> loose (no comparison possible)', (A.regime(one, 'low', th)), 'loose')

print('')
print('=== pit laps and the partial first lap are ignored by consistency ===')
local p = newEngine()
drive(p, {corneringSamples = 40, midPush = 2, midSnap = 30}); lapDone(p, 1, {partial = true})
drive(p, {corneringSamples = 40, midPush = 2, midSnap = 30}); lapDone(p, 2, {pit = true})
drive(p, {corneringSamples = 40, midPush = 6, midSnap = 6}); lapDone(p, 3)
drive(p, {corneringSamples = 40, midPush = 6, midSnap = 6}); lapDone(p, 4)
check('windowBins holds only the 2 clean laps', #A.windowBins(p), 2)
local pv = A.regime(p, 'low', th)
check('totals loose (16/72) but both clean laps balanced -> nil', pv, nil)

print('')
print('=== rear signal carries agree/considered ===')
local rv, rsnap, rpush, rnote, ra, rc = A.rear(c, th)
check('rear verdict loose', rv, 'loose')
check('rear agree/considered 4/4', ra .. '/' .. rc, '4/4')

print('')
print('=== lapSupport for scalar signals ===')
local ls = newEngine()
drive(ls, {corneringSamples = 30, lockF = 5}); lapDone(ls, 1)
drive(ls, {corneringSamples = 30, lockF = 0}); lapDone(ls, 2)
drive(ls, {corneringSamples = 30, lockF = 1}); lapDone(ls, 3)
drive(ls, {corneringSamples = 30, lockF = 0}); lapDone(ls, 4)
local a, cnt, okS = A.support(ls, 'lockF')
check('lockF 6 total but in 1/4 laps -> not supported', okS, false)
check('counts', a .. '/' .. cnt, '1/4')
drive(ls, {corneringSamples = 30, lockF = 3}); lapDone(ls, 5)
drive(ls, {corneringSamples = 30, lockF = 2}); lapDone(ls, 6)
local a2, c2, ok2 = A.support(ls, 'lockF')
check('after two more locking laps: 3/6 -> supported', ok2, true)
check('a lap with exactly 2 events counts', a2, 3)

------------------------------------------------------------------------------
print('')
print('=== v2.0.1: session restart - lapCount goes backwards (real Huracan night) ===')
-- Port of update()'s lap-boundary block, including the v2.0.1 drop handling.
local function tick(e, lapCount, inPit)
  if inPit then e.lapPitSeen = true end
  if lapCount < e.lastLapCount then
    e.lastLapCount = lapCount
    e.lapBoundary = A.snapshot(e)
    e.lapPitSeen = true
    e.sessionRestarts = (e.sessionRestarts or 0) + 1
  end
  if lapCount > e.lastLapCount then
    local bin = {lap = lapCount, pit = e.lapPitSeen or false, partial = false, valid = true}
    for _, k in ipairs(A.KEYS) do bin[k] = (e[k] or 0) - (e.lapBoundary[k] or 0) end
    table.insert(e.lapBins, bin)
    e.lapBoundary = A.snapshot(e)
    e.lastLapCount = lapCount
    e.lapPitSeen = false
  end
end
local r = newEngine(); r.lastLapCount = 0; r.lapPitSeen = false
for lap = 1, 3 do drive(r, {corneringSamples = 50, midSnap = 30, midPush = 20}); tick(r, lap, false) end
check('3 laps banked before the restart', #r.lapBins, 3)
consume(r)                                   -- Build #1
tick(r, 0, true)                             -- session restart: lapCount 3 -> 0, car in the pit box
check('restart detected', r.sessionRestarts, 1)
check('lastLapCount re-synced to 0', r.lastLapCount, 0)
drive(r, {corneringSamples = 50, midSnap = 30, midPush = 20}); tick(r, 1, false)   -- out-lap completes
drive(r, {corneringSamples = 50, midSnap = 30, midPush = 20}); tick(r, 2, false)
drive(r, {corneringSamples = 50, midSnap = 30, midPush = 20}); tick(r, 3, false)
check('three laps after the restart banked as THREE bins (was: none until lap 4)', #r.lapBins - r.windowBinsStart, 3)
check('first post-restart lap is flagged pit (out-lap)', r.lapBins[4].pit, true)
check('each post-restart bin holds one lap of corners (was: 205 in one)', r.lapBins[5].corneringSamples, 50)
local okR, cleanR = gate(r, 2)
check('gate passes with 2 clean laps after the restart (was: DECLINED)', okR, true)
check('clean laps = 2 (out-lap excluded)', cleanR, 2)

print('')
print('=== v2.0.1: last Build record round-trips through storage ===')
local rec = table.concat({'ks_lamborghini_huracan_gt3', '22:23:09', 'ARB_REAR=0', 'DAMP_REBOUND_LR=8', 'WING_2=7'}, '|')
local recCar, recAt, rest = rec:match('^([^|]*)|([^|]*)|?(.*)$')
check('car parsed', recCar, 'ks_lamborghini_huracan_gt3')
check('time parsed', recAt, '22:23:09')
local restored = {}
for pair in rest:gmatch('[^|]+') do local sec, v = pair:match('^([^=]+)=(.+)$'); if sec and tonumber(v) then restored[sec] = tonumber(v) end end
check('three sections restored', restored.ARB_REAR == 0 and restored.DAMP_REBOUND_LR == 8 and restored.WING_2 == 7, true)
check('a record for another car is ignored', ('other_car|1|X=1'):match('^([^|]*)|') == 'ks_lamborghini_huracan_gt3', false)

------------------------------------------------------------------------------
print('')
print('=== source guards ===')
check('lapCount drop handled', src:find('if lapCount < self%.lastLapCount then\n    self%.lastLapCount = lapCount') ~= nil, true)
check('post-restart lap flagged pit', src:find('self%.lapBoundary = counterSnapshot%(self%)\n    self%.lapPitSeen = true') ~= nil, true)
check('record persisted to storage (v2.5.0: per car + track)', src:find("settings%.lastBuildRecord = serialiseKeyedStore%(list%)") ~= nil, true)
check('record restored for the same car', src:find("if recCar and recCar == carFolder and rest and rest ~= '' then") ~= nil, true)
check('pressure clamp reported', src:find("CLAMPED at this car\\'s minimum") ~= nil, true)
check('lap boundary banks a bin', src:find('table%.insert%(self%.lapBins, bin%)') ~= nil, true)
check('pit lane flagged per frame', src:find('if car%.isInPitlane then self%.lapPitSeen = true end') ~= nil, true)
check('first-unit partial decided from splinePosition (v2.5.0: within its unit)', src:find('self%.firstLapPartial = into > 0%.03 and into < 0%.97') ~= nil, true)
check('gate runs before the template read', (src:find('THE EVIDENCE GATE') or 0) < (src:find('local parsed, usedBase, templateLabel = findTemplateSetup') or 0), true)
check('declined Build logs its own entry', src:find("'result: DECLINED %- '") ~= nil, true)
check('declined Build does NOT consume', src:find("table%.insert%(logLines, 'result: DECLINED %- ' %.%. self%.setupMsg%)\n      self:writeDebugLog%(logLines%)\n      return false") ~= nil, true)
check('successful Build consumes', src:find('self:consumeWindow%(consumedLabel%)') ~= nil, true)
check('no-changes Build does NOT consume', src:find("table%.insert%(logLines, 'result: no changes %- ' %.%. self%.setupMsg%)\n    self:writeDebugLog%(logLines%)\n    return false") ~= nil, true)
check('lastBuildWritten recorded from managed sections', src:find('for section in pairs%(MANAGED_SECTIONS%) do\n    local v = getCurVal%(parsed, section%)') ~= nil, true)
check('lastBuildLoaded line in the log', src:find('lastBuildLoadedLine,') ~= nil, true)
check('evidence lines in the normal log', src:find("table%.concat%(self:evidenceLogLines%(th%), '\\n'%)") ~= nil, true)
check('no direct balanceVerdict calls outside regimeVerdict', select(2, src:gsub('balanceVerdict%(self, self%.', '')), 0)
local regimeUses = select(2, src:gsub("regimeVerdict%(self, '", ''))
check('regimeVerdict used at every call site (>= 9; v2.1.0 chain runner replaced the per-writer calls)', regimeUses >= 9, true)
check('brake bias entry holds lap-gated (v2.3.0 one-time write)', src:find("local _, _, tinOkB = lapSupport%(self, 'turninPush'%)") ~= nil and src:find("local _, _, loOk = lapSupport%(self, 'liftOffSnap'%)") ~= nil, true)
-- v2.6.0: bottoming is fixed one lever at a time by the travel chains, and
-- each end's chain only runs on a lap-consistent travel signal.
check('bottoming lap-gated (travel signal, v2.6.0 chains)', src:find("local verdict = travelHitsConsistent(self, key, hits, th) and 'bottoming' or nil", 1, true) ~= nil, true)
-- v2.6.1: the fast-damper kerb softener (and its fastChainEnd hand-off) is
-- gone - only the bottoming chain's fastBump lever moves fast dampers.
check('v2.6.1: fast-damper kerb softener removed (only the chain moves fast dampers)',
  src:find("local fastChainEnd = ", 1, true) == nil and src:find("local fastWord = 'softer, absorbs kerbs/bumps better'", 1, true) == nil, true)
-- v2.6.0: the max-travel spring writer is the bottoming chain's springRate
-- lever now; the chain runs on the lap-consistent travel signal.
check('springs lap-gated (v2.6.0: a lever of the bottoming chain)',
  src:find("['travelF-bottoming'] = {'packersF', 'bumpF', 'fastBumpF', 'springRateF', 'rideRaiseF'}", 1, true) ~= nil
  and src:find("levers['springRate' .. e] = function()", 1, true) ~= nil, true)
check('toe front lap-gated', src:find("elseif not tinOk then\n            return false, lapSupportNote%('turn%-in push', tinA, tinC%)") ~= nil, true)
check('toe rear lap-gated', src:find("if not rtOk then return false, lapSupportNote%('rear instability', rtA, rtC%) end") ~= nil, true)
check('diff lap-gated', src:find('and rotN > divN %* 1%.25 and not rotOk then') ~= nil, true)
check('settings slider for min laps', src:find("settings%.buildMinLaps = ui%.slider%('##minlaps'") ~= nil, true)
check('panel BUILD EVIDENCE item first', src:find("item%('BUILD EVIDENCE', 'ok'") ~= nil and src:find('local out = {\n    evidenceItem,') ~= nil, true)
check('consumeWindow keeps static camber (not in WINDOW_KEYS)', src:find("'staticCamberCaptured'") == nil, true)

print('')
print(string.format('%d passed, %d failed', pass, fail))
os.exit(fail == 0 and 0 or 1)
