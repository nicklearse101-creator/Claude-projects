-- v1.8.0 live-setup logic, tested against realistic spinner payloads.
-- NOTE ON WHAT THIS CAN AND CANNOT PROVE: it verifies the LOGIC given an
-- assumed shape for ac.getSetupSpinners(). It cannot prove the real API
-- returns that shape - only a running game can, which is what the new
-- `liveSetup:` debug-log line is for. Written deliberately after being
-- bitten this week by a test stub that encoded an assumption instead of
-- reality, so the boundary is stated rather than implied.

-- Exact port of readLiveSetupSpinners' guard + mapping.
local function readLive(spinners)
  if type(spinners) ~= 'table' then return nil, 'no table returned' end
  local map, count, inconsistent, firstBad = {}, 0, 0, nil
  for _, s in ipairs(spinners) do
    if type(s) == 'table' and type(s.name) == 'string' and tonumber(s.value) then
      local it = {
        section = s.name, value = tonumber(s.value),
        min = tonumber(s.min), max = tonumber(s.max), step = tonumber(s.step),
        displayMultiplier = tonumber(s.displayMultiplier),
        readOnly = s.readOnly and true or false,
      }
      if it.min and it.max and it.max > it.min then
        if it.value < it.min - 1e-6 or it.value > it.max + 1e-6 then
          inconsistent = inconsistent + 1
          firstBad = firstBad or it.section
        end
      end
      map[it.section] = it
      count = count + 1
    end
  end
  if count == 0 then return nil, 'returned 0 usable sections' end
  if inconsistent > 0 then
    return nil, string.format('REJECTED - %d/%d self-inconsistent (%s)', inconsistent, count, firstBad)
  end
  return map, string.format('%d sections', count)
end

local pass, fail = 0, 0
local function check(label, got, want)
  if got == want then pass = pass + 1; print(string.format('  PASS  %-52s %s', label, tostring(got)))
  else fail = fail + 1; print(string.format('  FAIL  %-52s got %s want %s', label, tostring(got), tostring(want))) end
end

-- Real numbers: lotus_exos_125_s1, from its own decrypted setup.ini and the
-- values actually observed in the driver's setup files.
print('=== 1. healthy read (real Lotus values) ===')
local live, note = readLive({
  {name='PRESSURE_LF', value=20, min=8,   max=20, step=1, displayMultiplier=1,   readOnly=false, units='psi'},
  {name='CAMBER_LF',   value=-29, min=-60, max=10, step=1, displayMultiplier=0.1, readOnly=false, units='°'},
  {name='ARB_FRONT',   value=30, min=0,   max=40, step=1, displayMultiplier=1,   readOnly=false},
  {name='FUEL',        value=50, min=0,   max=110, step=1, displayMultiplier=1,  readOnly=true},
})
check('read accepted', live ~= nil, true)
check('note', note, '4 sections')
check('pressure value is the LIVE 20, not a stale file', live and live.PRESSURE_LF.value, 20)
check('pressure real max known (was unclamped before)', live and live.PRESSURE_LF.max, 20)
check('camber displayMultiplier present', live and live.CAMBER_LF.displayMultiplier, 0.1)
check('readOnly flagged so it is not written', live and live.FUEL.readOnly, true)

print('')
print('=== 2. camber scale from displayMultiplier (replaces per-car guessing) ===')
local dm = live.CAMBER_LF.displayMultiplier
local scale = 1 / dm
check('scale = 1/displayMultiplier', scale, 10)
check('stored -29 reads as degrees', -29 / scale, -2.9)
-- The Ferrari case the driver confirmed by hand: set -3.5 deg -> stored -35.
check('driver-confirmed case: -3.5 deg stores as -35', -3.5 * scale, -35)

print('')
print('=== 3. consistency guard REJECTS mixed unit spaces ===')
-- Exactly the trap this project already hit: setup.ini declares camber
-- MIN/MAX in degrees (-6..1) while VALUE is stored in tenths (-29). If the
-- live API ever did that too, clamping against it would be nonsense.
local bad, badNote = readLive({
  {name='PRESSURE_LF', value=20,  min=8,  max=20, step=1},
  {name='CAMBER_LF',   value=-29, min=-6, max=1,  step=1},
})
check('rejected outright', bad, nil)
check('reason names the offender', badNote and badNote:find('CAMBER_LF') ~= nil, true)

print('')
print('=== 4. degenerate inputs fall back rather than half-work ===')
check('nil -> rejected', (readLive(nil)), nil)
check('empty list -> rejected', (readLive({})), nil)
local partial = readLive({{name='ARB_FRONT', value=30}})  -- no min/max at all
check('missing min/max still usable as a VALUE source', partial and partial.ARB_FRONT.value, 30)
check('...but carries no range to clamp with', partial and partial.ARB_FRONT.min, nil)

print('')
print(string.format('%d passed, %d failed', pass, fail))
os.exit(fail == 0 and 0 or 1)
