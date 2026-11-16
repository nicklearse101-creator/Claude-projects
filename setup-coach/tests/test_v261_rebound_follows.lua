-- v2.6.1: REBOUND FOLLOWS THE SPRINGS (anti-bounce). The shipped step is
-- cut out of the chain runner as-is and run against a stub corner whose
-- damping ratio is the real formula, c / 2 sqrt(k m).

local appPath = arg[1] or 'D:/SteamLibrary/steamapps/common/assettocorsa/apps/lua/setupcoach/SetupCoach.lua'
local f = assert(io.open(appPath, 'r'))
local src = f:read('a')
f:close()

local pass, fail = 0, 0
local function check(label, got, want)
  if got == want then pass = pass + 1; print(string.format('  PASS  %-72s %s', label, tostring(got)))
  else fail = fail + 1; print(string.format('  FAIL  %-72s got %s want %s', label, tostring(got), tostring(want))) end
end

local s = src:find('\n    local reboundSnap = {}', 1, true)
local e = src:find('\n\n    -- v2.4.0: the branches line for the log', 1, true)
check('step found in the chain runner', s ~= nil and e ~= nil and s < e, true)
local step = src:sub(s + 1, e)
check('...snapshot taken BEFORE the chains run', step:find('reboundSnap', 1, true) < step:find("runTravel('F')", 1, true), true)
check('...and acted on AFTER the balance chains', step:find("run('low'", 1, true) < step:find('local snap = reboundSnap[corner]', 1, true), true)
local floorLine = src:match('\nlocal ZETA_FLOOR_REBOUND = [^\n]+')
check('rebound floor is 0.50', tonumber(floorLine:match('= ([%d%.]+)')), 0.5)

-- Stub world. Rebound c = 2000 + 500 x click (N.s/m); springs in N/m;
-- 300 kg sprung corner.
local M = 300
local function phys(it, v) return it.base + it.per * v end
local function stor(it, c) return (c - it.base) / it.per end
local REB = {}
for _, c in ipairs({'LF', 'RF', 'LR', 'RR'}) do
  REB['DAMP_REBOUND_' .. c] = {section = 'DAMP_REBOUND_' .. c, raw = true, base = 2000, per = 500, step = 1, min = 0, max = 40}
end
local env
local function zetaOf(sec, v)
  local corner = sec:match('^DAMP_REBOUND_(%u%u)$')
  local k = corner and env.parsed['SPRING_RATE_' .. corner]
  if not corner or not k then return nil end
  return phys(REB[sec], v) / (2 * math.sqrt(k * M))
end
local function writeAbs(it, sec, dir, clicks, desc)
  local cur = env.parsed[sec]
  local newV = math.max(it.min, math.min(it.max, cur + dir * clicks * it.step))
  if newV == cur then return true, false end
  if env.calc.touched[sec] then
    table.insert(env.changes, desc .. ': NOT moved - already set by ' .. tostring(env.calc.touched[sec]))
    return true, false
  end
  env.parsed[sec] = newV
  table.insert(env.changes, string.format('%s: %s -> %s', desc, cur, newV))
  return true, true
end

local chunk = floorLine .. '\nreturn function()\n' .. step .. '\nend\n'
local function build(o)
  env = {math = math, string = string, table = table, ipairs = ipairs, pairs = pairs, tostring = tostring,
    settings = {writeDampersFront = o.front ~= false, writeDampersRear = true},
    parsed = {DAMP_REBOUND_LF = 15, DAMP_REBOUND_RF = 15, DAMP_REBOUND_LR = 15, DAMP_REBOUND_RR = 15,
      SPRING_RATE_LF = 200000, SPRING_RATE_RF = 200000, SPRING_RATE_LR = 200000, SPRING_RATE_RR = 200000},
    calc = {touched = o.touched or {}}, changes = {},
    getCurVal = function(p, sec) return p[sec] end,
    zetaOf = zetaOf, calcDamperMap = {REBOUND = REB, BUMP = {}},
    physicalOf = phys, storedOf = stor, writeAbs = writeAbs, NUDGE_FRACTION = {damper = 0.08},
    runTravel = function(en) if o.chain then o.chain(env, en) end end,
    run = function() end,
  }
  if o.pre then o.pre(env) end
  assert(load(chunk, 'step', 't', env))()()
  return env
end

print('')
print('=== front springs +25% by the bottoming chain, rebound left alone ===')
-- Before: c 9500 / (2 sqrt(200000 x 300)) = 0.613. After k 250000: 0.548.
-- Back to 0.613 needs c 10621 -> click 17.24 -> 3 clicks (18, zeta 0.635).
local function stiffenFront(en_, endKey)
  if endKey == 'F' then
    en_.parsed.SPRING_RATE_LF, en_.parsed.SPRING_RATE_RF = 250000, 250000
    en_.calc.touched.SPRING_RATE_LF, en_.calc.touched.SPRING_RATE_RF = 'the bottoming chain', 'the bottoming chain'
  end
end
local E = build({chain = stiffenFront})
check('LF rebound 15 -> 18', E.parsed.DAMP_REBOUND_LF, 18)
check('RF rebound 15 -> 18', E.parsed.DAMP_REBOUND_RF, 18)
check('...ratio back to at least where it was', zetaOf('DAMP_REBOUND_LF', 18) >= zetaOf('DAMP_REBOUND_LF', 15) * math.sqrt(200000 / 250000) and zetaOf('DAMP_REBOUND_LF', 18) >= 0.613, true)
check('...and no further than it needed (17 would fall short)', zetaOf('DAMP_REBOUND_LF', 17) < 9500 / (2 * math.sqrt(200000 * M)), true)
check('rear untouched (its springs did not move)', E.parsed.DAMP_REBOUND_LR, 15)
check('marked as this step\'s move', E.calc.touched.DAMP_REBOUND_LF, 'the rebound-follows-springs step')
check('logged as "rebound follows the springs"', table.concat(E.changes, '\n'):find('rebound follows the springs', 1, true) ~= nil, true)

print('')
print('=== nothing moved -> nothing written ===')
E = build({})
check('no change lines', #E.changes, 0)
check('LF rebound still 15', E.parsed.DAMP_REBOUND_LF, 15)

print('')
print('=== a lever moved rebound on purpose -> left alone ===')
E = build({chain = function(en_, endKey)
  stiffenFront(en_, endKey)
  if endKey == 'F' then en_.parsed.DAMP_REBOUND_LF = 13 end
end})
check('LF (moved by a lever) stays at the lever\'s 13', E.parsed.DAMP_REBOUND_LF, 13)
check('RF (left alone) still follows its spring', E.parsed.DAMP_REBOUND_RF, 18)

print('')
print('=== front damper module off ===')
E = build({chain = stiffenFront, front = false})
check('LF rebound untouched', E.parsed.DAMP_REBOUND_LF, 15)

print('')
print('=== the floor pre-pass lifted it earlier this Build (touched = true) ===')
E = build({chain = stiffenFront, touched = {DAMP_REBOUND_LF = true}})
check('re-checked against the new springs and raised', E.parsed.DAMP_REBOUND_LF, 18)
print('=== ...but a NAMED earlier move is respected ===')
E = build({chain = stiffenFront, touched = {DAMP_REBOUND_LF = 'a balance lever'}})
check('LF not moved over a named move', E.parsed.DAMP_REBOUND_LF, 15)

print('')
print('=== started under the floor: brought to floor x 1.05, not just back ===')
-- click 11: c 7500 -> 0.484 at 200000 (under 0.50); after 250000: 0.433.
-- Target 0.525: c 9093 -> click 14.19 -> 4 clicks (15, zeta 0.548).
E = build({chain = stiffenFront, pre = function(en_) en_.parsed.DAMP_REBOUND_LF = 11 end})
check('LF 11 -> 15', E.parsed.DAMP_REBOUND_LF, 15)
check('...at or above 0.525', zetaOf('DAMP_REBOUND_LF', 15) >= 0.525, true)

print('')
print('=== softer springs never soften rebound ===')
E = build({chain = function(en_, endKey)
  if endKey == 'F' then en_.parsed.SPRING_RATE_LF = 175000 end
end})
check('LF rebound still 15', E.parsed.DAMP_REBOUND_LF, 15)

print('')
print(string.format('%d passed, %d failed', pass, fail))
os.exit(fail == 0 and 0 or 1)
