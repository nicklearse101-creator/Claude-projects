-- v2.3.0: calculated targets. Every shipped calculation is extracted from
-- the app and run against the Huracan's REAL decrypted files and the
-- driver's real session numbers.

local appPath = arg[1] or 'D:/SteamLibrary/steamapps/common/assettocorsa/apps/lua/setupcoach/SetupCoach.lua'
local HUR = 'D:/Claude/setupcoach-tools/acd/extracted/ks_lamborghini_huracan_gt3/'
local f = assert(io.open(appPath, 'r'))
local src = f:read('a')
f:close()

local pass, fail = 0, 0
local function check(label, got, want)
  if got == want then pass = pass + 1; print(string.format('  PASS  %-76s %s', label, tostring(got)))
  else fail = fail + 1; print(string.format('  FAIL  %-76s got %s want %s', label, tostring(got), tostring(want))) end
end
local function near(label, got, want, tol)
  local ok = type(got) == 'number' and math.abs(got - want) <= tol
  if ok then pass = pass + 1; print(string.format('  PASS  %-76s %.3f', label, got))
  else fail = fail + 1; print(string.format('  FAIL  %-76s got %s want %.3f±%.3f', label, tostring(got), want, tol)) end
end

------------------------------------------------------------------------------
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
local function fn(name) return extractBlock('\nlocal function ' .. name .. '%(') end
local function method(name) return extractBlock('\nfunction engine:' .. name .. '%(') end
local function const(name) local l = src:match('\nlocal ' .. name .. ' = [^\n]+'); assert(l, name); return l end

local settings = {rideCal = '', camberGain = '', biasBaselineCars = '', leverLedger = '', leverPending = ''}
local env = {math = math, string = string, tonumber = tonumber, tostring = tostring, type = type,
  pcall = pcall, ipairs = ipairs, pairs = pairs, table = table, settings = settings, next = next}
local names = {'SLIGHT_OVERSTEER_PER_100', 'LEVER_EFFECT_DROP', 'LEVER_FREEZE_AFTER',
  'BIAS_MAX_JUMP', 'SPRING_TARGET_USE', 'SPRING_MAX_STEP', 'RIDE_MAX_CLICKS',   -- v2.6.0: RIDE_PEAK_MARGIN_MM retired
  'ZETA_FLOOR_BUMP', 'ZETA_FLOOR_REBOUND', 'LEVER_MAX_JUMP', 'LEVER_NOISE_K', 'LEDGER_KEEP_CARS',
  'RIDE_CAL_MIN_PAIRS', 'RIDE_CAL_MIN_SLOPE'}
local chunk = 'local engine = {}\n'
for _, nm in ipairs(names) do chunk = chunk .. const(nm) .. '\n' end
chunk = chunk .. '\nlocal settings = settings or {}\n' .. assert(src:match('\n%-%- BALANCE MODES BEGIN.-%-%- BALANCE MODES END'), 'balance modes block') .. '\n'
chunk = chunk .. src:match('\nlocal WINDOW_KEYS = %b{}') .. '\n' .. src:match('\nlocal LEVER_CHAINS = %b{}') .. '\n'
  .. fn('clamp') .. '\n' .. fn('n') .. '\n' .. fn('physicalOf') .. '\n' .. fn('storedOf') .. '\n'
  .. fn('parsePointStore') .. '\n' .. fn('serialisePointStore') .. '\n' .. fn('parseLedgerStore') .. '\n'   -- v2.4.0 per-car ledger
  .. const('KEYED_KEEP') .. '\n' .. fn('parseKeyedStore') .. '\n' .. fn('serialiseKeyedStore') .. '\n'
  .. fn('keyedGet') .. '\n' .. fn('keyedPut') .. '\n'   -- v2.5.0 per car + track
  .. fn('balanceVerdict') .. '\n' .. fn('windowBins') .. '\n' .. fn('regimeCounts') .. '\n' .. fn('regimeVerdict') .. '\n'
for _, m in ipairs({'cornerSprungMass', 'cornerSpringRate', 'rideCalSlope', 'lapRateStats', 'camberGainRecord',
    'camberGain', 'biasBaselineDone', 'markBiasBaselineDone', 'finalDriveTarget', 'biasTarget',
    'leverLedgerFor', 'leverLedgerSave', 'judgePendingLevers'}) do
  chunk = chunk .. method(m) .. '\n'
end
chunk = chunk .. 'return {engine = engine, physicalOf = physicalOf, storedOf = storedOf, parse = parsePointStore, ser = serialisePointStore}'
local A = assert(load(chunk, 'extracted', 't', env))()
local E = A.engine

-- The Huracan, from its real files (car.ini / suspensions.ini / tyres.ini).
E.carId = 'ks_lamborghini_huracan_gt3'
E.chassis = {mass = 1334, cgFront = 0.43, hubF = 38, hubR = 45, springBaseF = 120000, springBaseR = 150000}
E.tyreRadiusF, E.tyreRadiusR = 0.340, 0.3525
local springItem = {min = 0, max = 9, step = 1, raw = {min = 90, step = 10, showClicks = 0}}   -- SPRING_RATE_LF 90..180/10
local bumpF = {min = 0, max = 12, step = 1, raw = {min = 10600, step = 1200, showClicks = 2}}  -- DAMP_BUMP_LF
local rebR = {min = 0, max = 12, step = 1, raw = {min = 2600, step = 817, showClicks = 2}}     -- DAMP_REBOUND_LR

------------------------------------------------------------------------------
print('=== physical values from stored clicks (real Huracan setup.ini conventions) ===')
check('DAMP_BUMP_LF click 0 = 10600 N·s/m', A.physicalOf(bumpF, 0), 10600)
check('DAMP_BUMP_LF click 3 = 14200 N·s/m', A.physicalOf(bumpF, 3), 14200)
check('storedOf inverts it', A.storedOf(bumpF, 14200), 3)
check('SHOW_CLICKS=0 spring 120 stays 120', A.physicalOf(springItem, 120), 120)
check('SHOW_CLICKS=1 = steps from zero', A.physicalOf({raw = {min = 3780, step = 360, showClicks = 1}}, 26), 9360)

print('')
print('=== sprung mass and wheel rate ===')
near('front corner sprung mass 1334 x 0.43 / 2 - 38', E:cornerSprungMass(true), 248.81, 0.01)
near('rear corner sprung mass 1334 x 0.57 / 2 - 45', E:cornerSprungMass(false), 335.19, 0.01)
check('setup 120 (N/mm) vs base 120000 N/m -> x1000', E:cornerSpringRate(true, springItem, 120), 120000)
check('DWB2 motion-ratio axle -> not trusted', (function() E.chassis.mrF = 'mr.lut'; local k = E:cornerSpringRate(true, springItem, 120); E.chassis.mrF = nil; return k end)(), nil)

print('')
print('=== damping ratio (zeta = c / 2 sqrt(k m)) - Huracan base values ===')
local function zeta(c, k, m) return c / (2 * math.sqrt(k * m)) end
local kF, mF = 120000, E:cornerSprungMass(true)
local kR, mR = 150000, E:cornerSprungMass(false)
near('front bump at its setup minimum 10600', zeta(10600, kF, mF), 0.97, 0.01)
near('rear rebound at its setup minimum 2600 - under the floor', zeta(2600, kR, mR), 0.18, 0.01)
local floorR = tonumber(src:match('\nlocal ZETA_FLOOR_REBOUND = ([%d%.]+)'))
local cT = A.physicalOf(rebR, 0) * (floorR * 1.05 / zeta(2600, kR, mR))
local stored = A.storedOf(rebR, cT)
local clicks = math.max(1, math.ceil(stored - 0 - 1e-6))
-- v2.6.1: rebound floor 0.40 -> 0.50 (anti-bounce). Under 0.40 these were
-- 5957 / 5 clicks / 0.47 (2600 x 0.42 / 0.1834 = 5955, hand-checked).
check('rebound floor is 0.50 (v2.6.1)', floorR, 0.5)
near('floor pre-pass: target c for 0.525 (2600 x 0.525 / 0.1834 = 7443)', cT, 7445, 5)
check('floor pre-pass: rear rebound lifted 0 -> 6 clicks in ONE move', clicks, 6)
check('...which lands at or above 0.525', zeta(A.physicalOf(rebR, 6), kR, mR) >= floorR * 1.05, true)
check('...and 5 clicks would have stopped short of it', zeta(A.physicalOf(rebR, 5), kR, mR) < floorR * 1.05, true)
check('the Huracan night\'s rear rebound at click 4 (zeta 0.41) is now UNDER the floor', zeta(A.physicalOf(rebR, 4), kR, mR) < floorR, true)
check('...and so is click 3 (a soften lever is refused there)', zeta(A.physicalOf(rebR, 3), kR, mR) < floorR, true)

------------------------------------------------------------------------------
print('')
print('=== brake bias target (both axles at the limit together) ===')
E.brkLoadN, E.brkZones, E.brkLoadFSum = 10, 1, 6
local bt, why = E:biasTarget()
check('too few zones -> no target', bt, nil)
check('...says why', why:find('needs 4 zones') ~= nil, true)
E.brkLoadN, E.brkZones, E.brkLoadFSum = 200, 8, 200 * 0.60
bt, why = E:biasTarget()
local equal = 100 * 0.60 * 0.340 / (0.60 * 0.340 + 0.40 * 0.3525)
near('front 60% of load, radii 0.340/0.3525 -> equal-limit split', equal, 59.13, 0.01)
near('+1% stability margin = target', bt, 60.13, 0.01)
check('info explains the maths', why:find('both axles at the limit together') ~= nil, true)
print('--- one-time write bookkeeping ---')
check('not done yet', E:biasBaselineDone('ks_lamborghini_huracan_gt3'), false)
E:markBiasBaselineDone('ks_lamborghini_huracan_gt3')
check('marked done', E:biasBaselineDone('ks_lamborghini_huracan_gt3'), true)
check('other car unaffected', E:biasBaselineDone('cup_dacia_sandero'), false)
E:markBiasBaselineDone('ks_lamborghini_huracan_gt3')
check('marking twice does not duplicate', settings.biasBaselineCars, '|ks_lamborghini_huracan_gt3|')

------------------------------------------------------------------------------
print('')
print('=== final drive (advice only) - the Huracan\'s real final.rto ===')
local finals = {}
for line in io.lines(HUR .. 'final.rto') do local r = line:match('|([%d%.]+)'); if r then table.insert(finals, tonumber(r)) end end
E.finalOptions, E.finalOptionsN = {}, #finals
for i, r in ipairs(finals) do E.finalOptions[i - 1] = r end
E.maxGearSeen, E.gearAtVmax = 6, 6
E.finalAtVmax, E.rpmAtVmax = 4.5, 7817          -- 22 Sep: 259 km/h @ 7817 on the driver's 4.5
local fd = E:finalDriveTarget(8000)
near('ideal final on 4.5 @ 7817 rpm', fd.want, 4.4999, 0.01)
check('nearest option = the one fitted -> "your final is right"', fd.bestIdx, fd.curIdx)
E.finalAtVmax, E.rpmAtVmax = 3.9166, 6976      -- the default final, 87% of the limiter at Vmax
fd = E:finalDriveTarget(8000)
near('ideal final from the default', fd.want, 4.379, 0.01)
check('calculation names 4.500 (option 4) - the one the driver picked by hand', fd.bestRatio, 4.5)
check('...option number', fd.bestIdx + 1, 4)
E.finalAtVmax, E.rpmAtVmax = 4.5, 7990          -- on the limiter at Vmax
fd = E:finalDriveTarget(8000)
check('on the limiter -> next LONGER option (4.1666)', fd.bestRatio, 4.1666)
E.gearAtVmax = 5
check('Vmax not in top gear -> no calculation', (E:finalDriveTarget(8000)), nil)
E.gearAtVmax = 6

------------------------------------------------------------------------------
print('')
print('=== per-lap noise (standard error of the per-lap rate) ===')
E.lapBins, E.windowBinsStart = {}, 0
local function bin(c, snap, push) return {corneringSamples = c, midSnap = snap, midPush = push, highSnap = 0, highPush = 0} end
for _, b in ipairs({bin(50, 30, 10), bin(50, 32, 11), bin(50, 28, 9), bin(50, 30, 10)}) do table.insert(E.lapBins, b) end
local mean, se, nl = E:lapRateStats('low', 'snap')
near('mean snap rate 60 per 100', mean, 60, 0.01)
near('standard error (laps 60/64/56/60)', se, 1.63, 0.01)
check('4 laps', nl, 4)

print('')
print('=== measured-response: effect vs noise decides whether a per-click value is kept ===')
E.corneringSamples, E.midSnap, E.midPush, E.highSnap, E.highPush = 200, 60, 20, 0, 0   -- after: 30 per 100
settings.leverPending = 'ks_lamborghini_huracan_gt3|7|low-loose:arb:60.00:2:1.63'
local line = E:judgePendingLevers('ks_lamborghini_huracan_gt3', 2, 'YES')
local led = E:leverLedgerFor('ks_lamborghini_huracan_gt3')
near('60 -> 30 over 2 clicks, noise ~4.6: kept as -15 per click', led['low-loose'].arb.sens, -15, 0.01)
check('log says it clears the noise', line:find('clears the noise') ~= nil, true)
-- Next Build: rate 30, target max(25, push 10 x 1.25)=25 -> ceil(5/15) = 1 click.
local target = math.max(12.5, 25)
check('jump sizing from it: 1 click to reach 25/100', math.max(1, math.min(math.ceil((30 - target) / 15), 4)), 1)
print('--- the Huracan wing case: effect inside the noise ---')
E.lapBins = {}
for _, b in ipairs({{corneringSamples = 50, highSnap = 20, highPush = 5, midSnap = 0, midPush = 0},
                    {corneringSamples = 50, highSnap = 12, highPush = 5, midSnap = 0, midPush = 0},
                    {corneringSamples = 50, highSnap = 18, highPush = 5, midSnap = 0, midPush = 0}}) do table.insert(E.lapBins, b) end
E.corneringSamples, E.highSnap, E.highPush, E.midSnap, E.midPush = 150, 50, 15, 0, 0     -- 33.3 per 100
led['high-loose'] = {wings = {tries = 1, ineff = 0, frozen = false, sens = -6}}
settings.leverPending = 'ks_lamborghini_huracan_gt3|8|high-loose:wings:31.50:2:3.00'
line = E:judgePendingLevers('ks_lamborghini_huracan_gt3', 2, 'YES')
check('31.5 -> 33.3 inside the noise: old per-click value CLEARED', led['high-loose'].wings.sens, nil)
check('log says no jumps', line:find('no per%-click value, no jumps') ~= nil, true)
print('--- ledger round-trips the per-click value ---')
E:leverLedgerSave('ks_lamborghini_huracan_gt3')
E.leverLedger, E.leverLedgerCar = nil, nil
near('reloaded ARB value', E:leverLedgerFor('ks_lamborghini_huracan_gt3')['low-loose'].arb.sens, -15, 0.001)
print('--- old pending format (v2.1.x) still parses ---')
settings.leverPending = 'ks_lamborghini_huracan_gt3|9|low-loose:arb:60.0'
check('old record judged without error', E:judgePendingLevers('ks_lamborghini_huracan_gt3', 2, 'YES'):find('low%-loose via arb') ~= nil, true)

------------------------------------------------------------------------------
print('')
print('=== camber: measured gain once 3+ Builds span 0.3 deg ===')
E:camberGainRecord('F', -3.4, -2.6)
E:camberGainRecord('F', -3.7, -2.9)
check('2 points -> gain unknown (1 assumed)', (E:camberGain('F')), nil)
E:camberGainRecord('F', -4.0, -3.2)
near('3 points, loaded moves 1:1 with static -> gain 1.0', (E:camberGain('F')), 1.0, 0.001)
E:camberGainRecord('F', -4.3, -3.95)
check('gain stays inside 0.5..2.0', (function() local g = E:camberGain('F'); return g >= 0.5 and g <= 2.0 end)(), true)
local ps = A.parse(settings.camberGain)
check('store keeps the last points per axle', #ps['ks_lamborghini_huracan_gt3'].F, 4)

print('')
print('=== ride-height calibration: fuel-matched pairs only ===')
settings.rideCal = A.ser({ks_lamborghini_huracan_gt3 = {F = {{25, 70.0, 30}, {28, 73.1, 31}, {22, 60.0, 80}}, R = {}}}, 6)
local slope, np, reliable = E:rideCalSlope('F')
near('25->28 clicks moved 70.0->73.1 mm at similar fuel: ~1.03 mm/click', slope, 1.033, 0.01)
check('the 80 L point (50 L heavier) is not paired', np, 1)
check('...and one pair is not yet reliable enough to steer by (v2.5.2)', reliable, false)
settings.rideCal = ''
check('no pairs -> uncalibrated', (E:rideCalSlope('F')), nil)

------------------------------------------------------------------------------
print('')
print('=== source guards ===')
check('brake bias: target read in the Build', src:find('local tgt, tgtInfo = self:biasTarget%(%)') ~= nil, true)
check('brake bias: advice only once the one-time write is used', src:find("advice only on this car %(its one calculated write was used") ~= nil, true)
check('brake bias: capped', src:find('clamp%(delta, %-BIAS_MAX_JUMP, BIAS_MAX_JUMP%)') ~= nil, true)
check('brake bias: forward held on entry push', src:find('moving forward adds entry push') ~= nil, true)
check('brake bias: rearward held on entry oversteer', src:find('moving rearward adds entry rotation') ~= nil, true)
check('brake bias: held counts as the one build', src:find("HELD, %%s%. Advice only from here on this car%.', tgt, curPct, hold%)%)\n          self:markBiasBaselineDone%(carFolder%)") ~= nil, true)
check('old lockup +-1 bias writer retired', src:find("'Brake bias %(' %.%. reason %.%. '%)', 0%.02, true%)") == nil, true)
check('BRAKE advice explains the entry trade-off', src:find('forward = steadier entry but more push, rearward = more rotation but looser') ~= nil, true)
check('settings can re-arm the bias write', src:find('Re%-arm one%-time brake%-bias write for this car') ~= nil, true)
check('GEARING stays advice-only', src:find("calculated: set the final drive to %%%.3f") ~= nil and src:find('advice only %- Build never changes gearing%)') ~= nil, true)
check('springs: calculated from median unit travel use (v2.6.0: the bottoming chain, +10% at most)', src:find("Spring %s (CALCULATED, cautious: median %s uses %.0f%% of this car\\'s travel range", 1, true) ~= nil, true)
check('front ride: v2.6.0 to 10 mm off the floor, the aero peak only as the stall limit',
  src:find('local action, mm, why = floorClearanceStep({', 1, true) ~= nil and src:find("this car\\'s downforce peaks at", 1, true) == nil, true)
check('rake stands aside when the front was set (v2.6.0: names who set it)', src:find("'%s already set by %s this Build - rake waits a window'", 1, true) ~= nil, true)
check('damper floor pre-pass', src:find('under the %%%.2f floor %- lifted in one move') ~= nil, true)
check('damper floor guard in writeTuned', src:find("if direction < 0 and section:find%('%^DAMP_%[BR%]'%) then") ~= nil, true)
check('calculated sections protected from lever re-moves (v2.4.0: names who set it)', src:find("NOT moved %- already set by %%s this Build") ~= nil and src:find("or 'a calculated target'") ~= nil, true)
check('camber: noise dead-band', src:find('if math%.abs%(deltaDeg%) <= deadBand then') ~= nil, true)
check('camber: measured gain applied', src:find('deltaDeg = deltaDeg / %(gain or 1%)') ~= nil, true)
check('camber status line no longer claims SKIPPED on writing Builds', src:find("'SKIPPED %- sit stationary in the pits once this session so a static camber reading can be captured%.'\n        or %(self%.corneringSamples") == nil, true)
check('jumps only for ARB / rear dampers / wings', src:find("lever == 'arb' or lever == 'rearDampers' or lever == 'wings'") ~= nil, true)
check('lever calls pass the jump', src:find('acted, why = fn%(regime, verdict, jump%)') ~= nil, true)
check('pending banks clicks and noise', src:find("'%%s:%%s:%%%.2f:%%d:%%%.2f'") ~= nil, true)
check('log line: calculated targets', src:find("'calculated targets %(v2%.3%.0%): '") ~= nil, true)

print('')
print(string.format('%d passed, %d failed', pass, fail))
os.exit(fail == 0 and 0 or 1)
