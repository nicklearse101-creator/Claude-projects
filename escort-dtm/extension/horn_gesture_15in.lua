-- Escort Mk2 15in (Nik 25 Nov): hold the horn -> the driver puts his window-side arm out of the (doorless) door opening,
-- forearm up, and gives the middle finger. Eases in/out over ~0.25 s; the other hand stays on the wheel.
-- The driver rig (driver_70) has no finger bones (the hand is a gripping fist), so the car model carries KK_finger
-- (hidden in the kn5) which is placed on the fist while the gesture is up.
local root = ac.findNodes("carRoot:" .. car.index)
local function bone(n)
  local r = root:findNodes("DRIVER:" .. n)
  if r:size() == 0 then r = root:findNodes(n) end
  return r
end
local ARM, FORE, HAND = bone("RIG_Arm_L"), bone("RIG_ForeArm_L"), bone("RIG_HAND_L")
local finger = root:findNodes("KK_finger")
finger:setVisible(false)
local ok = ARM:size() > 0 and FORE:size() > 0 and HAND:size() > 0
local t = 0

-- rotate world matrix M about point P so that direction `from` turns fraction k of the way to `to` (row-vector maths)
local function aim(M, P, from, to, k)
  local f = from:clone():normalize(); local g = to:clone():normalize()
  local axis = f:cross(g); local s = axis:length()
  if s < 1e-5 or k <= 0 then return M:clone() end
  axis:scale(1 / s)
  local ang = math.atan2(s, f:dot(g)) * k
  return M:mul(mat4x4.translation(-P)):mul(mat4x4.rotation(ang, axis)):mul(mat4x4.translation(P))
end

local function setWorld(ref, world, parentWorld)
  ref:getTransformationRaw():set(world:mul(parentWorld:inverse()))
end

function script.update(dt)
  local want = car.hornActive and 1 or 0
  t = t + (want - t) * math.min(1, dt * 10)
  if not ok then return end
  if t < 0.01 then
    finger:setVisible(false)
    return
  end
  local Aw = ARM:getWorldTransformationRaw():clone()
  local Fw = FORE:getWorldTransformationRaw():clone()
  local Hw = HAND:getWorldTransformationRaw():clone()
  local Ap = ARM:getParent():getWorldTransformationRaw():clone()
  local Fp = FORE:getParent():getWorldTransformationRaw():clone()
  local S, E, W = Aw.position:clone(), Fw.position:clone(), Hw.position:clone()
  -- outward = the driver's side of the car
  local out = car.side:clone()
  if (S - car.position):dot(out) < 0 then out:scale(-1) end
  local d1 = (out * 0.85 + car.up * 0.05 + car.look * 0.2):normalize()     -- upper arm: out of the window, a bit forward
  local d2 = (car.up * 0.92 + out * 0.25 + car.look * 0.05):normalize()    -- forearm: up
  -- upper arm
  local Aw2 = aim(Aw, S, E - S, d1, t)
  local delta1 = Aw:inverse():mul(Aw2)
  local Fw1, Hw1, Fp1 = Fw:mul(delta1), Hw:mul(delta1), Fp:mul(delta1)
  -- forearm
  local E1, W1 = Fw1.position:clone(), Hw1.position:clone()
  local Fw2 = aim(Fw1, E1, W1 - E1, d2, t)
  local Hw2 = Hw1:mul(Fw1:inverse():mul(Fw2))
  setWorld(ARM, Aw2, Ap)
  setWorld(FORE, Fw2, Fp1)
  -- the finger, up out of the fist
  if t > 0.6 then
    local base = Hw2.position:clone():addScaled(d2, 0.07)
    setWorld(finger, mat4x4.look(base, d2, out), finger:getParent():getWorldTransformationRaw())
    finger:setVisible(true)
  else
    finger:setVisible(false)
  end
end
