-- v1.8.1 regression guard: the live-setup sync must only ever touch sections
-- this app actually tunes. v1.8.0 synced everything the game reported, which
-- silently rewrote the driver's GEAR RATIOS (four INTERNAL_GEAR_n values
-- changed, and an INTERNAL_GEAR_1 section was added to a file that never had
-- one). Gearing is advice-only by design and must not acquire a writer by the
-- side door.
--
-- Reads MANAGED_SECTIONS straight out of the real app source rather than
-- restating the list here - a hand-copied list would drift and would only
-- ever prove itself right.
local appPath = arg[1] or 'D:/SteamLibrary/steamapps/common/assettocorsa/apps/lua/setupcoach/SetupCoach.lua'
local f = assert(io.open(appPath, 'r'))
local src = f:read('a')
f:close()

-- Pull every section name out of SETUP_PROBE, exactly as the app derives
-- MANAGED_SECTIONS from it at load time.
local probeBlock = src:match('local SETUP_PROBE = %{(.-)\n%}')
assert(probeBlock, 'could not locate SETUP_PROBE in the app source')
local managed = {}
for section in probeBlock:gmatch("section = '([A-Z0-9_]+)'") do managed[section] = true end

local pass, fail = 0, 0
local function check(label, got, want)
  if got == want then pass = pass + 1; print(string.format('  PASS  %-58s %s', label, tostring(got)))
  else fail = fail + 1; print(string.format('  FAIL  %-58s got %s want %s', label, tostring(got), tostring(want))) end
end

print('=== sections the app MUST NEVER write ===')
-- Exactly what v1.8.0 wrongly wrote on a real session.
for _, s in ipairs({
  'INTERNAL_GEAR_1', 'INTERNAL_GEAR_2', 'INTERNAL_GEAR_3', 'INTERNAL_GEAR_4',
  'INTERNAL_GEAR_5', 'INTERNAL_GEAR_6', 'INTERNAL_GEAR_7',
  'FINAL_RATIO', 'FINAL_GEAR_RATIO', 'GEAR_1', 'GEAR_2',
  'FUEL', 'TYRES', 'TRACTION_CONTROL', 'ENGINE_LIMITER', 'BRAKE_POWER_MULT',
}) do
  check('not managed: ' .. s, managed[s] or false, false)
end

print('')
print('=== sections the app SHOULD manage (sanity: guard is not vacuous) ===')
for _, s in ipairs({
  'PRESSURE_LF', 'CAMBER_LF', 'TOE_OUT_LF', 'ARB_FRONT', 'SPRING_RATE_LF',
  'ROD_LENGTH_LF', 'DAMP_BUMP_LF', 'DAMP_REBOUND_LR', 'DAMP_FAST_BUMP_LF',
  'PACKER_RANGE_LF', 'BUMP_STOP_RATE_LF', 'WING_1', 'WING_2',
  'FRONT_BIAS', 'DIFF_POWER', 'DIFF_PRELOAD',
}) do
  check('managed: ' .. s, managed[s] or false, true)
end

print('')
print('=== the sync itself is gated on MANAGED_SECTIONS ===')
-- v2.1.1: the sync branches on MANAGED_SECTIONS rather than skipping the
-- rest outright - unmanaged sections are now CARRIED from live (see
-- test_carry_unmanaged.lua). What must stay true: managed sections are the
-- only ones a WRITER may touch, and an unmanaged section is only ever
-- updated in place, never added.
check('sync branches on MANAGED_SECTIONS',
  src:find('elseif MANAGED_SECTIONS%[section%] then') ~= nil, true)
check('unmanaged sections only updated in place, never added',
  src:find('elseif parsed%.valueLineIdx%[section%] then') ~= nil, true)
check('MANAGED_SECTIONS derived from SETUP_PROBE, not hand-listed',
  src:find('for _, list in pairs%(SETUP_PROBE%) do') ~= nil, true)

print('')
print('=== GEARING advice is explicitly advice-only ===')
-- Counts its OWN failures: this used to test the global `fail`, so any
-- earlier failure in the file reported here too and one bug looked like two.
local gearingLines, gearingBad = 0, 0
for line in src:gmatch("[^\n]*item%('GEARING', 'act'[^\n]*") do
  gearingLines = gearingLines + 1
  if not line:find('advice only') then
    gearingBad = gearingBad + 1
    print('  (offending line) ' .. line:sub(1, 120))
  end
end
check('actionable GEARING lines found', gearingLines > 0, true)
check('...all say advice only', gearingBad, 0)

print('')
print('=== v1.9.0: diff / aero / brake bias are three INDEPENDENT gates ===')
for _, gate in ipairs({'writeBrakeBias', 'writeDifferential', 'writeAero'}) do
  check('write gate exists: ' .. gate, src:find('if settings%.' .. gate .. ' then') ~= nil, true)
  check('checkbox exists: ' .. gate, src:find('settings%.' .. gate .. ' = checkbox%(') ~= nil, true)
  check('in All-on list: ' .. gate, src:find("'" .. gate .. "'") ~= nil, true)
end
-- The old combined switch must no longer gate any write; it may only survive
-- as the one-time migration that carries a deliberate "off" across.
check('combined switch no longer gates writes',
  src:find('if settings%.writeDiffAeroBrake then') == nil, true)
check('legacy value is migrated, not discarded',
  src:find('if settings%.writeDiffAeroBrake == false then') ~= nil, true)

print('')
print(string.format('%d passed, %d failed', pass, fail))
os.exit(fail == 0 and 0 or 1)
