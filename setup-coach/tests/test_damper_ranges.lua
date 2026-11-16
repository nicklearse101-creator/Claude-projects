-- v1.9.1 guard: ferrari_458_gt2's baked damper ranges must contain the
-- factory defaults Assetto Corsa states in its OWN setup tooltips.
--
-- This is the check that would have caught the v1.6.0 mistake immediately.
-- That version baked click-index ranges (rear rebound 0..22) and reported
-- that the driver had been "pegged at maximum rear rebound for months" -
-- when 26 is simply the car's DEFAULT. A car's own default cannot sit
-- outside its own range; asserting that one invariant is enough to catch
-- a wrong unit conversion without having to know which conversion is right.
--
-- Reads the ranges out of the real app source, so it tests what ships.
local appPath = arg[1] or 'D:/SteamLibrary/steamapps/common/assettocorsa/apps/lua/setupcoach/SetupCoach.lua'
local f = assert(io.open(appPath, 'r'))
local src = f:read('a')
f:close()

local baked = {}
for section, body in src:gmatch("%['(DAMP_[A-Z_]+)'%]=%{(.-)%}") do
  local lo = tonumber(body:match('min=(-?%d+%.?%d*)'))
  local hi = tonumber(body:match('max=(-?%d+%.?%d*)'))
  baked[section] = {min = lo, max = hi}
end

-- Verbatim from AC's in-game damper tooltips (right-hand corners shown;
-- mirrored counterparts share the range).
local tooltipDefaults = {
  {section = 'DAMP_REBOUND_RR',      value = 26,  label = 'rear rebound'},
  {section = 'DAMP_REBOUND_RF',      value = 29,  label = 'front rebound'},
  {section = 'DAMP_BUMP_RF',         value = 39,  label = 'front bump'},
  {section = 'DAMP_BUMP_RR',         value = 24,  label = 'rear bump'},
  {section = 'DAMP_FAST_REBOUND_RF', value = 185, label = 'front fast rebound'},
  {section = 'DAMP_FAST_BUMP_RF',    value = 81,  label = 'front fast bump'},
}

-- Real values seen in the driver's own setup files, independent of tooltips.
local observed = {
  {section = 'DAMP_FAST_REBOUND_LF', value = 185},
  {section = 'DAMP_FAST_REBOUND_LR', value = 101},
  {section = 'DAMP_FAST_BUMP_LF',    value = 88},
  {section = 'DAMP_FAST_BUMP_LR',    value = 64},
  {section = 'DAMP_BUMP_LF',         value = 43},
  {section = 'DAMP_REBOUND_LF',      value = 34},
  {section = 'DAMP_REBOUND_LR',      value = 32},
}

local pass, fail = 0, 0
local function check(label, ok, detail)
  if ok then pass = pass + 1; print(string.format('  PASS  %-46s %s', label, detail or ''))
  else fail = fail + 1; print(string.format('  FAIL  %-46s %s', label, detail or '')) end
end

print("=== the car's own DEFAULTS must be inside the baked range ===")
for _, d in ipairs(tooltipDefaults) do
  local r = baked[d.section]
  if not r then
    check(d.label, false, d.section .. ' missing from baked schema')
  else
    check(d.label, d.value >= r.min and d.value <= r.max,
      string.format('default %d vs %g..%g', d.value, r.min, r.max))
  end
end

print('')
print('=== real observed setup values must also be inside ===')
for _, o in ipairs(observed) do
  local r = baked[o.section]
  if not r then
    check(o.section, false, 'missing from baked schema')
  else
    check(o.section, o.value >= r.min and o.value <= r.max,
      string.format('observed %d vs %g..%g', o.value, r.min, r.max))
  end
end

print('')
print('=== v1.9.2: DAMP_REBOUND_LR/RR must match the LIVE SPINNER exactly ===')
-- Ground truth, not inference: a real tester's liveSetup: log line reported
-- DAMP_REBOUND_LR=24[10..32] directly from ac.getSetupSpinners(). v1.9.1's
-- ceil(MIN/STEP) gave 11, one off from the game's own 10 - fixed to floor.
-- This is the one field with a live-verified exact bound; pinned exactly
-- rather than just "inside", so a future regression is caught precisely.
for _, sec in ipairs({'DAMP_REBOUND_LR', 'DAMP_REBOUND_RR'}) do
  local r = baked[sec]
  check(sec .. ' min == live-verified 10', r and r.min == 10, r and tostring(r.min) or 'missing')
  check(sec .. ' max == live-verified 32', r and r.max == 32, r and tostring(r.max) or 'missing')
end

print('')
print('=== sanity: ranges are non-degenerate ===')
local n = 0
for section, r in pairs(baked) do
  n = n + 1
  if not (r.min and r.max and r.max > r.min) then
    check(section, false, 'degenerate range')
  end
end
check('damper sections found', n == 16, n .. ' sections')

print('')
print(string.format('%d passed, %d failed', pass, fail))
os.exit(fail == 0 and 0 or 1)
