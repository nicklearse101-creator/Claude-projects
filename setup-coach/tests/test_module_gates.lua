-- Verifies the fixed front/rear "enabled" gating logic (v1.7.4) across all
-- four combinations, after the cond-and-A-or-B ternary bug was caught and
-- replaced with explicit if/else.
local function computeEnabled(front, writeFront, writeRear)
  local enabled
  if front then enabled = writeFront else enabled = writeRear end
  return enabled
end

local cases = {
  {front = true,  writeFront = true,  writeRear = true,  expect = true},
  {front = true,  writeFront = false, writeRear = true,  expect = false}, -- the exact case that was broken
  {front = false, writeFront = true,  writeRear = false, expect = false},
  {front = false, writeFront = false, writeRear = true,  expect = true},
}

local allPass = true
for i, c in ipairs(cases) do
  local got = computeEnabled(c.front, c.writeFront, c.writeRear)
  local pass = (got == c.expect)
  allPass = allPass and pass
  print(string.format('case %d: front=%-5s writeFront=%-5s writeRear=%-5s -> enabled=%-5s (expected %-5s) %s',
    i, tostring(c.front), tostring(c.writeFront), tostring(c.writeRear), tostring(got), tostring(c.expect),
    pass and 'PASS' or 'FAIL'))
end
print('')
print(allPass and 'ALL PASS' or 'SOME FAILED')
