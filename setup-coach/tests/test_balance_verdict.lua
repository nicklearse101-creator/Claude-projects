-- v1.9.8: "slight oversteer in a normal race car isn't a bad thing."
-- One balance verdict for every push-vs-snap decision. Loads the shipped
-- balanceVerdict / balanceLeftAloneNote / rearHandlingSignal out of the app
-- source and runs them on real session numbers.

local appPath = arg[1] or 'D:/SteamLibrary/steamapps/common/assettocorsa/apps/lua/setupcoach/SetupCoach.lua'
local f = assert(io.open(appPath, 'r'))
local src = f:read('a')
f:close()

local pass, fail = 0, 0
local function check(label, got, want)
  if got == want then pass = pass + 1; print(string.format('  PASS  %-70s %s', label, tostring(got)))
  else fail = fail + 1; print(string.format('  FAIL  %-70s got %s want %s', label, tostring(got), tostring(want))) end
end

local function extractFn(name)
  local s = src:find('\nlocal function ' .. name .. '%(')
  assert(s, 'function not found: ' .. name)
  local body, depth, out = src:sub(s + 1), 0, {}
  for line in body:gmatch('[^\n]*\n?') do
    table.insert(out, line)
    -- comments AND string literals stripped before counting keywords
    -- ("fine for a race car" once counted as a `for`).
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
local slightLine = src:match('\nlocal SLIGHT_OVERSTEER_PER_100 = %d+')
assert(slightLine, 'SLIGHT_OVERSTEER_PER_100 not found')
local env = {math = math, string = string, tonumber = tonumber, tostring = tostring, type = type, ipairs = ipairs, pairs = pairs, table = table}
-- v2.0.0: rearHandlingSignal goes through regimeVerdict (lap consistency);
-- with no lap bins present the consistency test passes through, so the
-- verdict tests below are unchanged.
local chunk = slightLine .. '\n' .. '\nlocal settings = settings or {}\n' .. assert(src:match('\n%-%- BALANCE MODES BEGIN.-%-%- BALANCE MODES END'), 'balance modes block') .. '\n' .. src:match('\nlocal EV_UNIT = %b{}') .. '\n'   -- v2.5.0 unit wording
  .. extractFn('balanceVerdict') .. '\n' .. extractFn('balanceLeftAloneNote') .. '\n'
  .. src:match('\nlocal WINDOW_KEYS = %b{}') .. '\n'
  .. extractFn('counterSnapshot') .. '\n' .. extractFn('windowBins') .. '\n' .. extractFn('regimeCounts') .. '\n'
  .. extractFn('regimeVerdict') .. '\n' .. extractFn('rearHandlingSignal') .. '\n'
  .. 'return {verdict=balanceVerdict, note=balanceLeftAloneNote, rear=rearHandlingSignal, SLIGHT=SLIGHT_OVERSTEER_PER_100, settings=settings, mode=balanceMode}'
local A = assert(load(chunk, 'extracted', 't', env))()
local th = 2

local function S(t) t.corneringSamples = t.corners or 0; return t end

print('=== the driver\'s case: a well-set-up car that rotates a little ===')
-- 100 corners, 15 oversteer events, 3 push. Ratio says "loose" (5x). Rate says 15 per 100.
local s = S({corners = 100})
local v, p, n, note, rate = A.verdict(s, 3, 15, th, true)
check('verdict is nil (left alone)', v, nil)
check('note is slight', note, 'slight')
check('rate 15 per 100', rate, 15)
check('left-alone wording', A.note(note, 3, 15, 'low-speed'), 'slight low-speed oversteer bias (15 oversteer / 3 push) - inside the Normal balance target, left alone')
print('...and the same car with 15 push / 3 oversteer IS a fault (understeer has no rate floor)')
check('push dominant -> tight', (A.verdict(s, 15, 3, th, true)), 'tight')

print('')
print('=== real Dacia session 2026-09-17 20:05 (push 76 / snap 65, 62 corners) ===')
local d = S({corners = 62})
local dv, _, _, dn = A.verdict(d, 76, 65, th, true)
check('Normal (1.15x): 76 push is clearly over 65 -> tight', dv, 'tight')
local dv2, _, _, dn2 = A.verdict(d, 72, 65, th, true)
check('72 / 65 (1.11x) stays mixed', dv2, nil)
check('note mixed (neither > 1.15x the other)', dn2, 'mixed')
check('wording', A.note(dn2, 72, 65, 'low-speed'), 'mixed low-speed balance (72 push / 65 oversteer), neither clearly dominant - left alone')

print('')
print('=== real kinkl Ferrari 17:15: rear signal (mid 215/265, high 20/108, 461 corners) ===')
local k = S({corners = 461, midPush = 215, midSnap = 265, highPush = 20, highSnap = 108})
local kv, ksnap, kpush, kn = A.rear(k, th)
check('rear verdict still loose (v1.9.3 fix stands)', kv, 'loose')
check('snapN', ksnap, 373)
check('pushN', kpush, 235)
print('=== real kinkl Ferrari 20:11: rear signal (mid 407/484, high 63/207, 914 corners) ===')
local k2 = S({corners = 914, midPush = 407, midSnap = 484, highPush = 63, highSnap = 207})
check('rear verdict loose', (A.rear(k2, th)), 'loose')
print('=== kinkl 17:15 LOW-speed only (215 push / 265 snap): ratio 1.23 > 1.15, 57 per 100 ===')
local kl = A.verdict(k, 215, 265, th, true)
check('low verdict loose under Normal', kl, 'loose')

print('')
print('=== rate floor only applies to oversteer, only where asked ===')
local hs = S({corners = 400})
check('high speed, 20 snap / 2 push, no rate floor -> loose', (A.verdict(hs, 2, 20, th, false)), 'loose')
check('same numbers WITH rate floor (5 per 100) -> nil', (A.verdict(hs, 2, 20, th, true)), nil)
local _, _, _, hn = A.verdict(hs, 2, 20, th, true)
check('...note slight', hn, 'slight')
check('push 20 / snap 2 with rate floor -> tight (floor is oversteer-only)', (A.verdict(hs, 20, 2, th, true)), 'tight')

print('')
print('=== early session: corner count floored at 20 so the rate can\'t explode ===')
local e = S({corners = 3})
check('5 snap in 3 corners -> rate uses 20 -> 25 per 100 -> NOT above bar', (A.verdict(e, 0, 5, th, true)), nil)
check('6 snap -> 30 per 100 -> loose', (A.verdict(e, 0, 6, th, true)), 'loose')

print('')
print('=== threshold and neutral ===')
local z = S({corners = 100})
check('nothing over th -> nil', (A.verdict(z, 1, 2, th, true)), nil)
local _, _, _, zn = A.verdict(z, 1, 2, th, true)
check('...no note', zn, nil)
check('note() with nil -> nil', A.note(nil, 1, 2, 'low-speed'), nil)
check('exactly 1.15x is NOT dominant (needs >)', (A.verdict(z, 115, 100, th, true)), nil)
check('1.16x is', (A.verdict(z, 116, 100, th, true)), 'tight')

print('')
print('=== balance modes ===')
local m = S({corners = 100})
A.settings.balanceMode = 'oversteer'
check('Oversteer: 90 push / 100 snap -> tight (wants more rotation)', (A.verdict(m, 90, 100, th, true)), 'tight')
check('Oversteer: 30 push / 45 snap (45 per 100, 1.5x) -> left alone', (A.verdict(m, 30, 45, th, true)), nil)
check('Oversteer: 20 push / 50 snap (2.5x, 50 per 100) -> loose', (A.verdict(m, 20, 50, th, true)), 'loose')
check('Oversteer: 15 / 3 snap 3 per 100 with 1.6x -> tight', (A.verdict(m, 15, 3, th, true)), 'tight')
A.settings.balanceMode = 'understeer'
check('Understeer: 100 push / 90 snap -> loose (wants stability)', (A.verdict(m, 100, 90, th, true)), 'loose')
check('Understeer: 3 push / 15 snap (15 per 100) -> loose', (A.verdict(m, 3, 15, th, true)), 'loose')
check('Understeer: 150 push / 100 snap (1.5x) -> left alone', (A.verdict(m, 150, 100, th, true)), nil)
check('Understeer: 170 push / 100 snap (1.7x) -> tight', (A.verdict(m, 170, 100, th, true)), 'tight')
A.settings.balanceMode = 'nonsense'
check('unknown mode falls back to Normal', (A.verdict(m, 116, 100, th, true)), 'tight')
A.settings.balanceMode = 'normal'
for _, key in ipairs({'normal', 'oversteer', 'understeer'}) do
  A.settings.balanceMode = key
  local md = A.mode()
  check(key .. ': a car can never be tight and loose at once', md.tightRatio * md.looseRatio > 1, true)
end
A.settings.balanceMode = 'normal'

print('')
print('=== source guards: one verdict, used everywhere it should be ===')
check('balanceVerdict defined once', select(2, src:gsub('local function balanceVerdict%(', '')), 1)
-- v2.0.0: every former balanceVerdict call site now goes through
-- regimeVerdict (which adds lap consistency); balanceVerdict itself is
-- only called from inside regimeVerdict.
local uses = select(2, src:gsub("regimeVerdict%(self, '", ''))
check('regimeVerdict called from chain runner (x2), ARB/AERO/TOE panel, debug, evidence, toe, rear signal = 9+', uses >= 9, true)
check('balanceVerdict only called from regimeVerdict', select(2, src:gsub('balanceVerdict%(self, self%.', '')), 0)
check('ARB is a chain lever (v2.1.0; v2.3.0 takes a measured jump)', src:find('levers%.arb = function%(regime, direction, jump%)') ~= nil, true)
check('ARB writer no longer writes push AND snap in one Build', src:find('if pushTarget and snapTarget and pushTarget == snapTarget') == nil, true)
check('rake: high regime through the verdict', src:find("local highVerdict, _, _, highNote = regimeVerdict%(self, 'high', th%)") ~= nil, true)
-- v2.5.0: x `up`, the click direction the pit calibration measured (+1 until measured).
check('rake lever: tight = lower front / raise rear', src:find('local dir = %(front and %-1 or 1%) %* up  %-%- lower front, raise rear = more rake') ~= nil, true)
check('rake lever: loose = raise front / lower rear', src:find('local dir = %(front and 1 or %-1%) %* up  %-%- raise front, lower rear = less rake') ~= nil, true)
check('wings: verdict decides, old "larger wins" gone', src:find('if self%.highPush >= self%.highSnap then%s+doWing') == nil, true)
check('rear dampers: a clear rear handling verdict leaves the rear to the balance chain', src:find("elseif axle%.e == 'R' and rearHandling then") ~= nil, true)
check('slow dampers on both ends come from the time-weighted histogram', src:find('local hv = self:damperHistVerdict%(axle%.e%)') ~= nil, true)
check('panel REAR DAMPERS gets the note', src:find("slowDamperAdvice%('R', bottomingR, 'Rear', rearHandling%)") ~= nil, true)
check('panel ARB uses the verdict', src:find("Low%-speed push dominant %(%%d push / %%d oversteer%)") ~= nil, true)
check('panel AERO uses the verdict', src:find("local highVerdict, _, _, highNote = regimeVerdict%(self, 'high', th%)\n  if highVerdict == 'tight' then") ~= nil, true)
check('debug line logs all three verdicts', src:find("balance verdicts %(%%s target") ~= nil, true)
check('the rule is stated in the code', src:find('SLIGHT OVERSTEER IN A\n%-%- RACE CAR IS NOT A FAULT') ~= nil, true)

print('')
print(string.format('%d passed, %d failed', pass, fail))
os.exit(fail == 0 and 0 or 1)
