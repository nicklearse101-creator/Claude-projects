-- Minimal CSP global stubs - just enough to let the real app file execute
-- as a top-level chunk under stock Lua without erroring. This does NOT
-- exercise game logic (no wheel/car telemetry flows through it) - it only
-- confirms the file parses AND runs cleanly top-to-bottom (catches e.g. an
-- accidental top-level statement, a load-time table-constructor error like
-- the historical p4-5_2011 bug, or a script.* entry point that silently
-- failed to get defined), that the expected CSP entry points exist, and
-- (since v1.7.7) that drawing a settings window doesn't silently CLOBBER
-- persisted settings - see the checkbox note below.
ac = {}

-- Capture every ac.storage table the app creates, so assertions below can
-- inspect real persisted settings after a UI pass.
local storages = {}
function ac.storage(t)
  table.insert(storages, t)
  return t
end

-- ui.* stubs modelling CSP's REAL return-value semantics, taken from CSP's
-- own shipped SDK definitions (extension/internal/lua-sdk/ac_apps/lib.lua).
-- Getting these right matters more than it looks: the previous version of
-- this file stubbed checkbox as `function(label, cur) return cur end`,
-- i.e. "returns the new value" - which is NOT what CSP does, and which
-- encoded the very assumption that caused the v1.7.6 "tick the box and the
-- menu flashes and vanishes" bug. A stub that mirrors your assumption
-- instead of the real API will happily validate broken code.
--
--   ui.checkbox  -> "@return boolean @Returns `true` if checkbox was
--                    clicked."   (NOT the new value)
--   ui.slider    -> "@return number @Possibly updated slider value."
--   ui.inputText -> "@return string" (first return is the text)
ui = {
  text = function() end,
  textWrapped = function() end,
  slider = function(label, cur) return cur end,      -- returns value: correct
  checkbox = function() return false end,            -- "not clicked this frame"
  inputText = function(label, cur) return cur end,   -- returns text
  pushFont = function() end,
  popFont = function() end,
  separator = function() end,
  offsetCursorY = function() end,
  sameLine = function() end,
  button = function() return false end,
  Font = { Small = 'Small', Big = 'Big' },
}
vec2 = function(x, y) return { x = x, y = y } end
rgbm = function(r, g, b, a) return { r = r, g = g, b = b, mult = a } end
script = {}

local path = arg[1]
if not path then
  print("usage: lua smoke_test.lua <path-to-SetupCoach.lua>")
  os.exit(2)
end

local chunk, loadErr = loadfile(path)
if not chunk then
  print("LOAD FAILED: " .. tostring(loadErr))
  os.exit(1)
end

local ok, runErr = pcall(chunk)
if not ok then
  print("EXECUTION FAILED: " .. tostring(runErr))
  os.exit(1)
end

local required = { "windowMain", "windowHud", "windowSettings", "onSimUpdate", "update", "onShow" }
local missing = {}
for _, name in ipairs(required) do
  if type(script[name]) ~= "function" then table.insert(missing, name) end
end
if #missing > 0 then
  print("MISSING ENTRY POINTS: " .. table.concat(missing, ", "))
  os.exit(1)
end

-- Snapshot every boolean in every storage table BEFORE any UI is drawn.
local before = {}
for i, s in ipairs(storages) do
  before[i] = {}
  for k, v in pairs(s) do
    if type(v) == 'boolean' then before[i][k] = v end
  end
end

-- Actually CALL windowSettings, not just confirm it exists - existence-only
-- checking would never run a single checkbox line.
local okSettings, settingsErr = pcall(script.windowSettings, 0)
if not okSettings then
  print("windowSettings EXECUTION FAILED: " .. tostring(settingsErr))
  os.exit(1)
end

-- REGRESSION GUARD for the v1.7.6 bug class. Nothing was clicked (the
-- checkbox stub always reports "not clicked"), so drawing the window must
-- leave every persisted boolean EXACTLY as it was. The broken idiom
-- `flag = ui.checkbox(label, flag)` fails this instantly: it assigns the
-- clicked-flag (false) over the real value, silently turning every setting
-- off one frame after the window is drawn.
local clobbered = {}
for i, s in ipairs(storages) do
  for k, wasValue in pairs(before[i] or {}) do
    if s[k] ~= wasValue then
      table.insert(clobbered, string.format("%s (%s -> %s)", k, tostring(wasValue), tostring(s[k])))
    end
  end
end
if #clobbered > 0 then
  print("SETTINGS CLOBBERED by drawing windowSettings with nothing clicked: " .. table.concat(clobbered, ", "))
  print("  -> ui.checkbox returns WHETHER IT WAS CLICKED, not the new value.")
  print("  -> use `if ui.checkbox(l, v) then v = not v end`, not `v = ui.checkbox(l, v)`.")
  os.exit(1)
end

-- Opposite failure mode: a checkbox that never actually toggles (e.g. a
-- helper that always returns the old value) would pass the guard above
-- while being completely dead to click on. Draw again with every checkbox
-- reporting "clicked", and assert that the number of booleans that FLIPPED
-- equals the number of checkboxes actually drawn.
--
-- Counting the draws matters rather than asserting "every boolean flipped":
-- settings tables legitimately hold booleans that aren't checkboxes at all
-- (internal markers, feature flags), and demanding those flip is a false
-- positive - which this guard produced the first time it ran, on a one-time
-- migration marker. Counting compares like with like.
local clicksDrawn = 0
ui.checkbox = function() clicksDrawn = clicksDrawn + 1 return true end
local beforeClick = {}
for i, s in ipairs(storages) do
  beforeClick[i] = {}
  for k, v in pairs(s) do
    if type(v) == 'boolean' then beforeClick[i][k] = v end
  end
end
local okClick, clickErr = pcall(script.windowSettings, 0)
if not okClick then
  print("windowSettings EXECUTION FAILED (clicked pass): " .. tostring(clickErr))
  os.exit(1)
end
local flipped = 0
for i, s in ipairs(storages) do
  for k, wasValue in pairs(beforeClick[i] or {}) do
    if s[k] ~= wasValue then flipped = flipped + 1 end
  end
end
-- Note: assumes every checkbox drawn by windowSettings is bound to a
-- storage-backed boolean (true today). A checkbox bound to a plain non-
-- persisted field - as windowMain's expand toggle is - would draw without
-- flipping anything here and read as a mismatch.
if flipped ~= clicksDrawn then
  print(string.format(
    "CHECKBOX TOGGLE MISMATCH: %d checkbox(es) drawn but %d setting(s) changed when all were clicked.",
    clicksDrawn, flipped))
  print("  -> a checkbox that doesn't toggle its own value is dead to click.")
  os.exit(1)
end

-- Coverage note, so the next person knows the boundary: both passes detect
-- the broken idiom only via flags whose value differs from what the broken
-- code would force them to. `v = ui.checkbox(l, v)` forces false (unclicked)
-- / true (clicked), so a flag that already held that value looks identical
-- either way. In practice this file has 12 default-true write toggles, so
-- the broken idiom is caught immediately - but a hypothetical file of only
-- default-false flags could slip through the unclicked pass.
print("OK: file loaded, executed top-to-bottom, all script.* entry points defined, windowSettings runs cleanly, settings survive an unclicked UI pass and toggle correctly when clicked.")
