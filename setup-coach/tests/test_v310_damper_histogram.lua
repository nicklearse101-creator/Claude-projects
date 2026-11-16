-- Damper histogram (time-weighted wheel velocity per side and band) and the
-- slow-damper verdict it feeds. Runs the shipped functions out of the app.
local appPath = arg[1] or 'D:/SteamLibrary/steamapps/common/assettocorsa/apps/lua/setupcoach/SetupCoach.lua'
local f = assert(io.open(appPath, 'rb'))
local src = f:read('a'):gsub('\r\n', '\n')
f:close()

local pass, fail = 0, 0
local function check(label, got, want)
  if got == want then pass = pass + 1; print(string.format('  PASS  %-70s %s', label, tostring(got)))
  else fail = fail + 1; print(string.format('  FAIL  %-70s got %s want %s', label, tostring(got), tostring(want))) end
end
local function grab(pat) local s = src:match(pat); assert(s, 'not found: ' .. pat); return s end
local function fn(name) return grab('\nlocal function ' .. name .. '%(.-\nend\n') end
local function method(name) return grab('\nfunction engine:' .. name .. '%(.-\nend\n') end

local chunk = 'local engine = {}\n'
  .. grab('\nlocal EV_UNIT = %b{}') .. '\n'
  .. grab('\nlocal DAMPER_HIST_KEYS = %b{}') .. '\n'
  .. grab('\nlocal DAMPER_HIST_MIN_V = [^\n]+') .. '\n'
  .. grab('\nlocal DAMPER_HIST_MAX_V = [^\n]+') .. '\n'
  .. grab('\nlocal DAMPER_KNEE_DEFAULT = [^\n]+') .. '\n'
  .. fn('damperKnee') .. fn('dampHistAdd') .. fn('windowBins')
  .. grab('\nlocal DAMPER_HIST_SHARE_LO, DAMPER_HIST_SHARE_HI = [^\n]+') .. '\n'
  .. grab('\nlocal DAMPER_HIST_MIN_S = [^\n]+') .. '\n'
  .. grab('\nlocal ZETA_CEIL_BUMP, ZETA_CEIL_REBOUND = [^\n]+') .. '\n'
  .. fn('damperHistShare') .. fn('damperHistSide') .. method('damperHistVerdict')
  .. 'return {engine = engine, add = dampHistAdd, knee = damperKnee, keys = DAMPER_HIST_KEYS}'
local env = {math = math, string = string, table = table, ipairs = ipairs, pairs = pairs, tonumber = tonumber, tostring = tostring}
local A = assert(load(chunk, 'extracted', 't', env))()

-- One wheel: a lap of motion where bump strokes take `tb` seconds and
-- rebound strokes `tr` seconds over the same 30 mm, sampled at `fps`.
local function drive(self, axle, tb, tr, fps, cycles)
  local dt = 1 / fps
  for _ = 1, cycles do
    local vb, vr = 0.03 / tb, -0.03 / tr
    for _ = 1, math.floor(tb * fps + 0.5) do A.add(self, axle, vb, dt) end
    for _ = 1, math.floor(tr * fps + 0.5) do A.add(self, axle, vr, dt) end
  end
end
local function fresh(knee) local s = {damperCrossover = knee, lapBins = {}, windowBinsStart = 0}; for _, k in ipairs(A.keys) do s[k] = 0 end; return s end

print('=== knee from the car file, clamped ===')
check('0.060 used', A.knee(fresh(0.06)), 0.06)
check('LUT axle 0.30 -> default 0.05', A.knee(fresh(0.30)), 0.05)
check('missing -> default', A.knee(fresh(nil)), 0.05)

print('=== time-weighted: frame rate does not matter ===')
local s60, s144 = fresh(0.05), fresh(0.05)
drive(s60, 'F', 0.2, 0.4, 60, 100)
drive(s144, 'F', 0.2, 0.4, 144, 100)
local v60 = A.engine.damperHistVerdict(s60, 'F')
local v144 = A.engine.damperHistVerdict(s144, 'F')
check('60 fps share 33%', math.floor(v60.share * 100 + 0.5), 33)
check('144 fps share 33%', math.floor(v144.share * 100 + 0.5), 33)
check('bump moving twice as fast -> bump soft', v60.verdict, 'bumpSoft')
check('bands: 0.15 m/s bump is fast, 0.075 m/s rebound is fast (knee 0.05)', s60.dhSlowBumpF + s60.dhSlowRebF, 0)

print('=== the other way, and even ===')
local r = fresh(0.1); drive(r, 'R', 0.5, 0.25, 100, 60)
check('rebound twice as fast -> rebound soft', A.engine.damperHistVerdict(r, 'R').verdict, 'rebSoft')
check('...slow band used (0.06 m/s < 0.1 knee)', r.dhSlowBumpR > 0, true)
local ev = fresh(0.05); drive(ev, 'F', 0.3, 0.32, 100, 80)
check('near even -> nil', A.engine.damperHistVerdict(ev, 'F').verdict, nil)

print('=== evidence ===')
local short = fresh(0.05); drive(short, 'F', 0.2, 0.4, 100, 10)
local vs = A.engine.damperHistVerdict(short, 'F')
check('6 s of movement -> no verdict', vs.verdict, nil)
check('...says so', vs.text:find('needs 20') ~= nil, true)
local noise = fresh(0.05); A.add(noise, 'F', 0.002, 0.01); A.add(noise, 'F', 4.0, 0.01); A.add(noise, 'F', 0.2, 0.5)
check('friction band and glitches ignored', noise.dhFastBumpF + noise.dhSlowBumpF, 0)

print('=== lap consistency ===')
local c = fresh(0.05); drive(c, 'F', 0.2, 0.4, 100, 100)
c.lapBins = {{dhFastBumpF = 10, dhFastRebF = 20}, {dhFastBumpF = 15, dhFastRebF = 15}, {dhFastBumpF = 15, dhFastRebF = 15}}
check('1 of 3 laps agree -> not acted on', A.engine.damperHistVerdict(c, 'F').verdict, nil)
c.lapBins[2] = {dhFastBumpF = 10, dhFastRebF = 20}
check('2 of 3 agree -> acted on', A.engine.damperHistVerdict(c, 'F').verdict, 'bumpSoft')

print('=== source guards ===')
check('per-frame velocity goes into the histogram for both axles', select(2, src:gsub("dampHistAdd%(self, '[FR]', vel, dt%)", '')), 2)
check('histogram keys are banked per lap', src:find("'dhSlowBumpF', 'dhSlowRebF', 'dhFastBumpF', 'dhFastRebF',") ~= nil, true)
check('slow-damper writer reads the verdict', src:find('local hv = self:damperHistVerdict%(axle%.e%)') ~= nil, true)
check('old count-ratio rule gone', src:find('local ratio = %(axle%.bumpN %+ 1%) / %(axle%.rebN %+ 1%)'), nil)

print('')
print(string.format('%d passed, %d failed', pass, fail))
os.exit(fail == 0 and 0 or 1)
