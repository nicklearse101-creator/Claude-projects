-- v1.9.3: rear damper direction is driven by the handling signal, not the
-- event histogram. Verified against the REAL sessions that exposed the bug,
-- and against the old logic so the contrast is on record.
--
-- Evidence behind the direction is AC's own setup tooltips (verbatim in
-- CLAUDE.md, "In-game damper guidance"): higher rear rebound = "less stable
-- under braking and initial turn in"; lower rear bump = "more traction and
-- more stability the moment you release the brakes".
local appPath = arg[1] or 'D:/SteamLibrary/steamapps/common/assettocorsa/apps/lua/setupcoach/SetupCoach.lua'
local f = assert(io.open(appPath, 'r'))
local src = f:read('a')
f:close()

-- Port of rearHandlingSignal. v1.9.8: goes through balanceVerdict, which
-- adds the per-100-corners rate floor for 'loose' (see test_balance_verdict
-- for that on its own); corner counts below are the real sessions'.
local SLIGHT = 25
local function rearHandlingSignal(s, th)
  local snapN = s.midSnap + s.highSnap
  local pushN = s.midPush + s.highPush
  local corners = math.max(s.corners or 0, 20)
  if pushN > th and pushN > snapN * 1.25 then return 'tight', snapN, pushN end
  if snapN > th and snapN > pushN * 1.25 then
    if snapN / corners * 100 <= SLIGHT then return nil, snapN, pushN, 'slight' end
    return 'loose', snapN, pushN
  end
  if snapN > th or pushN > th then return nil, snapN, pushN, 'mixed' end
  return nil, snapN, pushN
end

-- What the OLD (pre-v1.9.3) histogram did for rear rebound: +1 stiffen when
-- rebound events dominate, ignoring handling entirely.
local function oldRearReboundDir(bumpN, rebN)
  local ratio = (bumpN + 1) / (rebN + 1)
  if ratio < 0.625 then return 1 end   -- "rebound comparatively soft" -> stiffen
  if ratio > 1.6 then return 0 end     -- bump path, rebound untouched
  return 0
end

-- What v1.9.3 did for rear rebound (histogram fallback on nil), and what
-- v1.9.8 does (nil = left alone; the rear histogram was structurally biased
-- toward "stiffen rebound", the exact defect on slightly-loose cars).
local function v193RearReboundDir(s, th)
  local h = rearHandlingSignal(s, th)
  if h == 'loose' then return -1 end
  if h == 'tight' then return 1 end
  return oldRearReboundDir(s.dampBumpR, s.dampRebR)  -- histogram fallback
end
local function newRearReboundDir(s, th)
  local h = rearHandlingSignal(s, th)
  if h == 'loose' then return -1 end
  if h == 'tight' then return 1 end
  return 0  -- v1.9.8: left alone
end

local pass, fail = 0, 0
local function check(label, got, want)
  if got == want then pass = pass + 1; print(string.format('  PASS  %-62s %s', label, tostring(got)))
  else fail = fail + 1; print(string.format('  FAIL  %-62s got %s want %s', label, tostring(got), tostring(want))) end
end
local th = 2

print('=== real tester session, kinkl 2026-09-13 17:15 (461 corners) ===')
-- th=2 counters: midPush=215 midSnap=265 highPush=20 highSnap=108 / bumpR=16 rebR=71
local s1 = {midPush=215, midSnap=265, highPush=20, highSnap=108, dampBumpR=16, dampRebR=71, corners=461}
check('handling signal', (rearHandlingSignal(s1, th)), 'loose')
check('OLD logic stiffened rear rebound (what the log shows: 24 -> 28)', oldRearReboundDir(s1.dampBumpR, s1.dampRebR), 1)
check('NEW logic softens it', newRearReboundDir(s1, th), -1)

print('')
print('=== real tester session, kinkl 2026-09-13 20:11 (914 corners) ===')
-- midPush=407 midSnap=484 highPush=63 highSnap=207 / bumpR=46 rebR=216
local s2 = {midPush=407, midSnap=484, highPush=63, highSnap=207, dampBumpR=46, dampRebR=216, corners=914}
check('handling signal', (rearHandlingSignal(s2, th)), 'loose')
check('OLD logic would stiffen', oldRearReboundDir(s2.dampBumpR, s2.dampRebR), 1)
check('NEW logic softens', newRearReboundDir(s2, th), -1)

print('')
print('=== a pushing car: understeer dominant, rear planted ===')
local s3 = {midPush=100, midSnap=20, highPush=30, highSnap=5, dampBumpR=10, dampRebR=40}
check('handling signal', (rearHandlingSignal(s3, th)), 'tight')
check('NEW logic stiffens rear rebound for rotation', newRearReboundDir(s3, th), 1)

print('')
print('=== mixed-balance car: no clear signal -> LEFT ALONE (v1.9.8; was histogram) ===')
local s4 = {midPush=100, midSnap=95, highPush=10, highSnap=12, dampBumpR=10, dampRebR=40, corners=200}
check('handling signal is nil', (rearHandlingSignal(s4, th)), nil)
check('v1.9.3 fell back to the histogram (rebound dominant -> STIFFEN)', v193RearReboundDir(s4, th), 1)
check('v1.9.8 leaves the rear alone', newRearReboundDir(s4, th), 0)

print('')
print('=== slightly loose car: 15 snap / 3 push in 100 corners -> LEFT ALONE, not softened ===')
local s8 = {midPush=3, midSnap=15, highPush=0, highSnap=0, dampBumpR=10, dampRebR=40, corners=100}
local v8, _, _, n8 = rearHandlingSignal(s8, th)
check('handling signal is nil', v8, nil)
check('note is slight', n8, 'slight')
check('rear rebound untouched', newRearReboundDir(s8, th), 0)

print('')
print('=== below threshold: nothing ===')
local s5 = {midPush=0, midSnap=1, highPush=0, highSnap=0, dampBumpR=0, dampRebR=0}
check('handling signal is nil', (rearHandlingSignal(s5, th)), nil)

print('')
print('=== dominance margin: 25% more is required, not just "more" ===')
local s6 = {midPush=100, midSnap=120, highPush=0, highSnap=0, dampBumpR=10, dampRebR=40, corners=200}  -- 120 vs 100: only 20% more
check('20% more snap than push is NOT "clearly loose"', (rearHandlingSignal(s6, th)), nil)
local s7 = {midPush=100, midSnap=126, highPush=0, highSnap=0, dampBumpR=10, dampRebR=40, corners=200}  -- 26% more, 63 per 100
check('26% more IS', (rearHandlingSignal(s7, th)), 'loose')

print('')
print('=== source guards: one shared function, used by BOTH panel and writer ===')
local defs = 0
for _ in src:gmatch('local function rearHandlingSignal%(') do defs = defs + 1 end
check('rearHandlingSignal defined exactly once', defs, 1)
local uses = 0
for _ in src:gmatch('rearHandlingSignal%(self, th%)') do uses = uses + 1 end
check('called from both the advice panel and the writer', uses >= 2, true)
check('advice text promises SOFTEN for loose', src:find('Build will SOFTEN rear rebound and rear bump') ~= nil, true)
check('writer actually softens for loose', src:find("rearHandling == 'loose'") ~= nil, true)
check('front axle is NOT handling-driven (histogram only)',
  src:find("axle%.label == 'Front' and rearHandling") == nil, true)

print('')
print(string.format('%d passed, %d failed', pass, fail))
os.exit(fail == 0 and 0 or 1)
