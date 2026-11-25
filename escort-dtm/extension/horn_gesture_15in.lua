-- Escort Mk2 15in (Nik 25 Nov): hold the horn -> the driver puts his window-side (left) arm out of the doorless door
-- opening, forearm up, and gives the middle finger with his own hand (the rig has finger joints HAND_Middle1..6 etc:
-- the left hand's middle joints are straightened, the other fingers keep their curled wheel grip = a fist).
-- v2: no feedback jitter - the game's own pose of every bone we touch is cached and only refreshed when the game itself
-- rewrites that bone; we never build on what we wrote last frame. The KK_finger mesh in the model is no longer used.
local root = ac.findNodes("carRoot:" .. car.index)
local function node(n)
  local r = root:findNodes("DRIVER:" .. n)
  if r:size() == 0 then r = root:findNodes(n) end
  return r
end
local CLAVE, ARM, FORE, FEND, HAND = node("RIG_Clave_L"), node("RIG_Arm_L"), node("RIG_ForeArm_L"), node("RIG_ForeArm_END_L"), node("RIG_HAND_L")
root:findNodes("KK_finger"):setVisible(false)
local ok = CLAVE:size() > 0 and ARM:size() > 0 and FORE:size() > 0 and FEND:size() > 0 and HAND:size() > 0
-- the left hand's middle-finger joints (whichever of HAND_Middle1..6 live under RIG_HAND_L)
local MID = {}
if ok then
  for i = 1, 6 do
    local r = HAND:findNodes("DRIVER:HAND_Middle" .. i)
    if r:size() == 0 then r = HAND:findNodes("HAND_Middle" .. i) end
    if r:size() > 0 then MID[#MID + 1] = r end
  end
end

-- ---- game-pose cache: refs -> { ac = game's local, written = what we last wrote }
local cache = {}
local function same(a, b)
  return (a.position - b.position):lengthSquared() < 1e-12 and (a.look - b.look):lengthSquared() < 1e-10 and (a.up - b.up):lengthSquared() < 1e-10
end
local function gameLocal(ref)
  local L = ref:getTransformationRaw(); local c = cache[ref]
  if not c then c = { ac = L:clone() }; cache[ref] = c
  elseif not c.written or not same(L, c.written) then c.ac = L:clone(); c.written = nil end
  return c.ac
end
local function write(ref, m)
  ref:getTransformationRaw():set(m); cache[ref].written = m:clone()
end
local function restore()
  for ref, c in pairs(cache) do
    if c.written then write(ref, c.ac) end
  end
end

-- rotate world matrix M about point P so direction `from` turns fraction k of the way to `to` (row-vector maths)
local function aim(M, P, from, to, k)
  local f = from:clone():normalize(); local g = to:clone():normalize()
  local axis = f:cross(g); local s = axis:length()
  if s < 1e-5 or k <= 0 then return M:clone() end
  axis:scale(1 / s)
  return M:mul(mat4x4.translation(-P)):mul(mat4x4.rotation(math.atan2(s, f:dot(g)) * k, axis)):mul(mat4x4.translation(P))
end

local t, wasUp = 0, false
function script.update(dt)
  if not ok then return end
  local want = car.hornActive and 1 or 0
  t = t + (want - t) * math.min(1, dt * 10)
  -- refresh the cache every frame (also while idle) so we always know the game's own pose
  local aL, fL, eL, hL = gameLocal(ARM), gameLocal(FORE), gameLocal(FEND), gameLocal(HAND)
  local mids = {}
  for i, r in ipairs(MID) do mids[i] = gameLocal(r) end
  if t < 0.01 then
    if wasUp then restore(); wasUp = false end
    return
  end
  wasUp = true
  local Cw = CLAVE:getWorldTransformationRaw():clone()          -- parent of the arm: never written by us
  local Aw = aL:mul(Cw); local Fw = fL:mul(Aw); local Hw = hL:mul(eL:mul(Fw))
  local S, E, W = Aw.position, Fw.position, Hw.position
  local out = car.side:clone()
  if (S - car.position):dot(out) < 0 then out:scale(-1) end      -- the driver's side of the car
  local d1 = (out * 0.85 + car.up * 0.05 + car.look * 0.2):normalize()    -- upper arm: out of the window, a bit forward
  local d2 = (car.up * 0.92 + out * 0.25 + car.look * 0.05):normalize()   -- forearm: up
  local Aw2 = aim(Aw, S, E - S, d1, t)
  local Fw1 = fL:mul(Aw2)
  local W1 = hL:mul(eL:mul(Fw1)).position
  local Fw2 = aim(Fw1, Fw1.position, W1 - Fw1.position, d2, t)
  write(ARM, Aw2:mul(Cw:inverse()))
  write(FORE, Fw2:mul(Aw2:inverse()))
  -- middle finger straight (rotation removed, joint offsets kept) once the arm is mostly up
  for i, r in ipairs(MID) do
    if t > 0.5 then write(r, mat4x4.translation(mids[i].position)) elseif cache[r].written then write(r, mids[i]) end
  end
end
