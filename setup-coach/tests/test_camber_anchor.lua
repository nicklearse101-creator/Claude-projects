-- Replicates the camber writer's anchor math exactly (v1.7.1), against the
-- real numbers from the 2026-09-11 22:02:46 session log, to verify the
-- fix produces a sane in-range value instead of collapsing to the schema
-- boundary.
local function clamp(v, a, b)
  if v < a then return a end
  if v > b then return b end
  return v
end

local function writeCamber(baseVal, deltaDeg, schemaItem, curStatic)
  local scale, scaleSrc
  if curStatic and math.abs(curStatic) > 0.15 then
    scale, scaleSrc = baseVal / curStatic, 'scale derived from your static reading'
  elseif schemaItem and math.abs(schemaItem.min) > 15 then
    scale, scaleSrc = 10, 'schema range implies tenths of a degree'
  elseif schemaItem then
    scale, scaleSrc = 1, 'schema range implies raw degrees'
  elseif math.abs(baseVal) > 8 then
    scale, scaleSrc = 10, 'stored value implies tenths of a degree'
  else
    scale, scaleSrc = 1, 'stored value implies raw degrees'
  end
  if math.abs(scale) < 0.5 or math.abs(scale) > 200 then
    scale, scaleSrc = 1, 'derived scale looked wrong, assuming raw degrees'
  end

  local anchorVal, anchorNote = baseVal, nil
  if schemaItem then
    local margin = schemaItem.max - schemaItem.min
    if baseVal < schemaItem.min - margin or baseVal > schemaItem.max + margin then
      anchorVal = (schemaItem.min + schemaItem.max) / 2
      anchorNote = 'anchor replaced (baseVal stale)'
    end
  end

  local newV = anchorVal + deltaDeg * scale
  if schemaItem then newV = clamp(newV, schemaItem.min, schemaItem.max) end
  if math.abs(newV - anchorVal) < 0.5 then
    newV = anchorVal + (deltaDeg > 0 and 1 or -1)
    if schemaItem then newV = clamp(newV, schemaItem.min, schemaItem.max) end
  end
  return newV, scaleSrc, anchorNote
end

print('=== CAMBER_LF: real schema {-5, -1.2}, real session baseVal=-24, deltaDeg=-0.95 ===')
local newV, src, note = writeCamber(-24, -0.95, {min = -5, max = -1.2}, nil)
print(string.format('  OLD (v1.7.0): boundary collapse -> -5.00 (matches actual debug log)'))
print(string.format('  NEW (v1.7.1): -24 -> %.2f  [%s%s]', newV, src, note and (', ' .. note) or ''))

print('')
print('=== CAMBER_LR: real schema {-3.5, 0.5}, real session baseVal=-18, deltaDeg=-1.14 ===')
local newV2, src2, note2 = writeCamber(-18, -1.14, {min = -3.5, max = 0.5}, nil)
print(string.format('  OLD (v1.7.0): boundary collapse -> -3.50 (matches actual debug log)'))
print(string.format('  NEW (v1.7.1): -18 -> %.2f  [%s%s]', newV2, src2, note2 and (', ' .. note2) or ''))

print('')
print('=== Sanity: a genuinely near-edge REAL value should NOT be treated as stale ===')
local newV3, src3, note3 = writeCamber(-4.8, -0.3, {min = -5, max = -1.2}, nil)
print(string.format('  -4.8 -> %.2f  [%s%s] (expect anchor kept = baseVal, no "stale" note)', newV3, src3, note3 and (', ' .. note3) or 'no override'))
