-- Escort Mk2 15in (Nik 25 Nov): hold the horn -> the driver puts his window-side (left) arm straight out of the doorless
-- door opening towards the car alongside, forearm up, wrist straight, tight fist with the middle finger up.
-- v3: ac.updateDriverModel() is called every frame before touching the bones (CSP: "use it before moving driver nodes
-- manually ... next model update possibly overwriting your custom positioning will be skipped") - that is what caused the
-- flicker; we always start from the fresh game pose, never from what we wrote.
-- Fingers: the rig has HAND_Index/Middle/Ring/Pinkie1..6 (3 joints per hand); the left hand's middle joints go straight,
-- the other fingers' grip rotation is doubled (tight fist).
local root = ac.findNodes("carRoot:" .. car.index)
local function node(n)
  local r = root:findNodes("DRIVER:" .. n)
  if r:size() == 0 then r = root:findNodes(n) end
  return r
end
local ARM, FORE, FEND, HAND = node("RIG_Arm_L"), node("RIG_ForeArm_L"), node("RIG_ForeArm_END_L"), node("RIG_HAND_L")
root:findNodes("KK_finger"):setVisible(false)
local ok = ARM:size() > 0 and FORE:size() > 0 and FEND:size() > 0 and HAND:size() > 0
local MIDDLE, CURL = {}, {}
if ok then
  for _, f in ipairs({ "Middle", "Index", "Ring", "Pinkie" }) do
    for i = 1, 6 do
      local r = HAND:findNodes("DRIVER:HAND_" .. f .. i)
      if r:size() == 0 then r = HAND:findNodes("HAND_" .. f .. i) end
      if r:size() > 0 then table.insert(f == "Middle" and MIDDLE or CURL, r) end
    end
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
local function rotOnly(M)       -- M without translation
  local R = M:clone(); R.position = vec3(0, 0, 0); return R
end

local t, active = 0, false
function script.update(dt)
  if not ok then return end
  local want = car.hornActive and 1 or 0
  t = t + (want - t) * math.min(1, dt * 12)
  if t < 0.01 then
    if active then ac.updateDriverModel(); active = false end    -- one clean game update to put everything back
    return
  end
  active = true
  ac.updateDriverModel()                                            -- fresh game pose now; next game update skipped
  local Cw = ARM:getParent():getWorldTransformationRaw():clone()
  local Aw = ARM:getWorldTransformationRaw():clone()
  local Fw = FORE:getWorldTransformationRaw():clone()
  local Hw = HAND:getWorldTransformationRaw():clone()
  local S, E, W = Aw.position:clone(), Fw.position:clone(), Hw.position:clone()
  local out = car.side:clone()
  if (S - car.position):dot(out) < 0 then out:scale(-1) end        -- the driver's side of the car
  local d1 = (out * 0.95 + car.up * 0.12 + car.look * 0.1):normalize()   -- upper arm straight out sideways
  local d2 = (car.up * 0.97 + out * 0.15):normalize()                     -- forearm straight up
  local Aw2 = aim(Aw, S, E - S, d1, t)
  local Fw1 = Fw:mul(Aw:inverse():mul(Aw2))
  local Hw1 = Hw:mul(Aw:inverse():mul(Aw2))
  local Fw2 = aim(Fw1, Fw1.position, Hw1.position - Fw1.position, d2, t)
  ARM:getTransformationRaw():set(Aw2:mul(Cw:inverse()))
  FORE:getTransformationRaw():set(Fw2:mul(Aw2:inverse()))
  if t > 0.5 then
    -- wrist straight: hand continues the forearm
    for _, r in ipairs({ FEND, HAND }) do
      r:getTransformationRaw():set(mat4x4.translation(r:getTransformationRaw().position:clone()))
    end
    for _, r in ipairs(MIDDLE) do                                   -- middle finger straight
      r:getTransformationRaw():set(mat4x4.translation(r:getTransformationRaw().position:clone()))
    end
    for _, r in ipairs(CURL) do                                     -- the rest: twice the grip curl = tight fist
      local L = r:getTransformationRaw(); local R = rotOnly(L)
      local m = R:mul(R); m.position = L.position:clone()
      L:set(m)
    end
  end
end
