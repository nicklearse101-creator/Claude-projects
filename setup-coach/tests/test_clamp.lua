-- Replicates writeTuned()'s value math exactly, to verify the baked
-- schema actually stops the rear-rebound runaway seen in real logs.
local function clamp(v, a, b)
  if v < a then return a end
  if v > b then return b end
  return v
end

local function nextValue(cur, direction, frac, clicks, schemaItem)
  local mag = math.max(math.abs(cur) * frac * clicks, 1)
  local raw = cur + direction * mag
  if schemaItem then raw = clamp(raw, schemaItem.min, schemaItem.max) end
  local looksInteger = math.abs(cur - math.floor(cur + 0.5)) < 0.01
  local newV = looksInteger and math.floor(raw + 0.5) or (math.floor(raw * 100 + 0.5) / 100)
  if newV == cur then
    newV = cur + (direction > 0 and 1 or -1)
    if schemaItem then newV = clamp(newV, schemaItem.min, schemaItem.max) end
  end
  if newV == cur then return cur, false end -- no write
  return newV, true
end

local REBOUND = {min = 0, max = 22, step = 1}  -- real decrypted schema
local frac, clicks, dir = 0.08, 2, 1           -- NUDGE_FRACTION.damper, stiffen

print('Simulating repeated "stiffen rear rebound" presses from the real observed start value (24):')
print('')
print(string.format('%-8s %-28s %-28s', 'press', 'WITHOUT schema (current)', 'WITH baked schema (fixed)'))
local a, b = 24, 24
for i = 1, 8 do
  local aNew, aWrote = nextValue(a, dir, frac, clicks, nil)
  local bNew, bWrote = nextValue(b, dir, frac, clicks, REBOUND)
  print(string.format('%-8d %-28s %-28s', i,
    string.format('%d -> %d%s', a, aNew, aWrote and '' or ' (no write)'),
    string.format('%d -> %d%s', b, bNew, bWrote and '' or ' (no write)')))
  a, b = aNew, bNew
end
print('')
print('Real car max rear rebound click index = 22.')
print(string.format('Without schema after 8 presses: %d  (%d clicks past the real limit)', a, a - 22))
print(string.format('With baked schema after 8 presses: %d  (clamped at the real limit)', b))
