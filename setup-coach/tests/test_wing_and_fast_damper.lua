-- v1.9.4: two one-way ratchets closed.
--   WINGS: bidirectional + mixed-case handling, mirroring the ARB writer.
--   FAST DAMPERS: the soften direction is floored at the factory default.
-- Both verified against the real numbers that exposed them.

local appPath = arg[1] or 'D:/SteamLibrary/steamapps/common/assettocorsa/apps/lua/setupcoach/SetupCoach.lua'
local f = assert(io.open(appPath, 'r'))
local src = f:read('a')
f:close()

local pass, fail = 0, 0
local function check(label, got, want)
  if got == want then pass = pass + 1; print(string.format('  PASS  %-60s %s', label, tostring(got)))
  else fail = fail + 1; print(string.format('  FAIL  %-60s got %s want %s', label, tostring(got), tostring(want))) end
end
local th = 2

------------------------------------------------------------------------------
-- WINGS: exact port of the v1.9.4 decision (which write happens, and which
-- direction), given current wing values and their schema maxima.
------------------------------------------------------------------------------
local function wingDecision(s, wingFcur, wingFmax, wingRcur, wingRmax, step)
  step = step or 1
  local frontNearMax = wingFcur >= wingFmax - step * 1.5
  local rearNearMax  = wingRcur >= wingRmax - step * 1.5
  local pushW, snapW
  if s.highPush > th then
    if frontNearMax then pushW = {sec='REAR', dir=-1} else pushW = {sec='FRONT', dir=1} end
  end
  if s.highSnap > th then
    if rearNearMax then snapW = {sec='FRONT', dir=-1} else snapW = {sec='REAR', dir=1} end
  end
  if pushW and snapW then
    if s.highPush >= s.highSnap then return pushW, 'push-only (snap noted)' end
    return snapW, 'snap-only (push noted)'
  end
  return pushW or snapW, 'single'
end

-- What v1.9.3 did: both +1, independently, unconditionally.
local function oldWingWrites(s)
  local writes = 0
  if s.highPush > th then writes = writes + 1 end
  if s.highSnap > th then writes = writes + 1 end
  return writes
end

print('=== WINGS: real tester session, kinkl 17:15 - highPush=20 highSnap=108 ===')
-- Ferrari: front splitter 0..4 (already at 4), rear wing 0..10 (at 5).
local s1 = {highPush = 20, highSnap = 108}
check('OLD: both wings written (+1 each)', oldWingWrites(s1), 2)
local w, mode = wingDecision(s1, 4, 4, 5, 10)
check('NEW: exactly one write', w ~= nil, true)
check('NEW: acts on the LARGER signal (snap)', w.sec, 'REAR')
check('NEW: rear wing goes up', w.dir, 1)
check('NEW: push is noted, not written', mode, 'snap-only (push noted)')

print('')
print('=== WINGS: front already at max, push flagged -> reduce REAR instead ===')
local s2 = {highPush = 40, highSnap = 0}
local w2 = wingDecision(s2, 4, 4, 5, 10)
check('write targets the rear', w2.sec, 'REAR')
check('direction is DOWN (less drag, same balance shift)', w2.dir, -1)

print('')
print('=== WINGS: rear at max, snap flagged -> reduce FRONT instead ===')
local s3 = {highPush = 0, highSnap = 40}
local w3 = wingDecision(s3, 2, 4, 10, 10)
check('write targets the front', w3.sec, 'FRONT')
check('direction is DOWN', w3.dir, -1)

print('')
print('=== WINGS: the ratchet is closed - a wing can now come DOWN ===')
check('old code had a -1 wing direction anywhere', src:find("wingFMap%[probe%.section%], probe%.section, %-1") ~= nil, false)
check('new code can write dir=-1 on a wing', src:find("dir = %-1, n = self%.highPush") ~= nil, true)
-- v1.9.8: the mixed case is decided by balanceVerdict (one verdict, one
-- write at most) rather than "larger raw count wins".
check('wings are a chain lever, one write at most (v2.1.0; v2.3.0 jump)', src:find('levers%.wings = function%(regime, direction, jump%)') ~= nil, true)
check('near-max snapshotted BEFORE writes (v1.4.1 lesson)', src:find("local frontNearMax = wingF and nearMax%(wingF, wingFMap%)") ~= nil, true)

------------------------------------------------------------------------------
-- FAST DAMPERS: floor at factory default when softening.
------------------------------------------------------------------------------
local function fastDamperWrites(fastDir, cur, defaultValue)
  local floorHit = fastDir < 0 and defaultValue ~= nil and cur ~= nil and cur <= defaultValue
  return not floorHit
end

print('')
print('=== FAST DAMPERS: Ferrari front fast rebound, range 175..190, default 185 ===')
-- Real log: 185 -> 175 in one Build. Under v1.9.4 the first soften from
-- 185 is BLOCKED because 185 is already AT the default.
check('at default (185): soften is blocked', fastDamperWrites(-1, 185, 185), false)
check('above default (188): soften allowed', fastDamperWrites(-1, 188, 185), true)
check('below default (180): soften blocked', fastDamperWrites(-1, 180, 185), false)
check('STIFFEN (bottoming) is never floored', fastDamperWrites(1, 175, 185), true)
check('no default known: old behaviour (soften allowed)', fastDamperWrites(-1, 180, nil), true)

print('')
print('=== FAST DAMPERS: Lotus rear fast rebound walked 21->18->17->16 ===')
-- If the Lotus default were, say, 18: the 21->18 step is allowed, and the
-- subsequent 18->17 and 17->16 steps are what the floor now prevents.
check('21 -> 18 allowed (above default 18)', fastDamperWrites(-1, 21, 18), true)
check('18 -> 17 BLOCKED (at default)', fastDamperWrites(-1, 18, 18), false)
check('17 -> 16 BLOCKED (below default)', fastDamperWrites(-1, 17, 18), false)

print('')
print('=== FAST DAMPERS: source guards ===')
check('defaultValue captured from the live spinner', src:find("defaultValue = tonumber%(s%.defaultValue%)") ~= nil, true)
-- v2.6.1: the kerb soften writer this floor guarded is gone altogether
-- (Nik: "it's useless. abolish it."); the port above is kept as history.
check('v2.6.1: kerb soften writer removed (no factory-default floor line left)', src:find("already at/below this car\\'s factory default") == nil, true)

print('')
print('=== LABEL: rear low-speed oversteer now says LESS rake ===')
check("'more rake for less low-speed oversteer' gone", src:find('more rake for less low%-speed oversteer') == nil, true)
check("'less rake for less %s-speed oversteer' present (regime-formatted, v2.1.0)", src:find('less rake for less %%s%-speed oversteer') ~= nil, true)

print('')
print('=== RENAME: coastPush -> liftOffSnap (code only; changelog prose untouched) ===')
local codeRefs = 0
for _ in src:gmatch('self%.coastPush') do codeRefs = codeRefs + 1 end
check('no self.coastPush left in code', codeRefs, 0)
check('liftOffSnap counted in detection', src:find('self%.liftOffSnap = self%.liftOffSnap %+ 1') ~= nil, true)
check('experiment line label updated', src:find('liftOffSnap=%%%.1f') ~= nil, true)

print('')
print(string.format('%d passed, %d failed', pass, fail))
os.exit(fail == 0 and 0 or 1)
