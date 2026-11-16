-- v1.7.2 verification: with the corrected (x10) baked schema, does the
-- camber writer now (a) trust a genuinely-valid current value like -24
-- instead of wrongly treating it as stale, and (b) compute a sensible
-- degree-based result matching the real physics delta?
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

  local anchorVal, anchorNote = baseVal, 'baseVal trusted as-is'
  if schemaItem then
    local margin = schemaItem.max - schemaItem.min
    if baseVal < schemaItem.min - margin or baseVal > schemaItem.max + margin then
      anchorVal = (schemaItem.min + schemaItem.max) / 2
      anchorNote = 'anchor OVERRIDDEN (baseVal treated as stale)'
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

-- Real numbers from the 2026-09-11 22:02:46 session, real CORRECTED schema.
print('=== CAMBER_LF: corrected schema {-50,-12}, baseVal=-24 (real -2.4°), deltaDeg=-0.95 ===')
local newV, src, note = writeCamber(-24, -0.95, {min = -50, max = -12}, nil)
print(string.format('  -24 -> %.2f raw (%.2f° actual)  [%s | %s]', newV, newV/10, src, note))
print(string.format('  expected: -2.4° current + -0.95° delta = -3.35° -> raw -33.5'))

print('')
print('=== CAMBER_LR: corrected schema {-35,5}, baseVal=-18 (real -1.8°), deltaDeg=-1.14 ===')
local newV2, src2, note2 = writeCamber(-18, -1.14, {min = -35, max = 5}, nil)
print(string.format('  -18 -> %.2f raw (%.2f° actual)  [%s | %s]', newV2, newV2/10, src2, note2))
print(string.format('  expected: -1.8° current + -1.14° delta = -2.94° -> raw -29.4'))

print('')
print('=== User-confirmed real value: -35 raw really is -3.5°, must NOT be treated as stale ===')
local newV3, src3, note3 = writeCamber(-35, -0.3, {min = -50, max = -12}, nil)
print(string.format('  -35 -> %.2f raw (%.2f° actual)  [%s | %s]', newV3, newV3/10, src3, note3))
