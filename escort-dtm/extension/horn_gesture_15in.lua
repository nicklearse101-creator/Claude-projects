-- Escort Mk2 15in (Nik 25 Nov): hold the horn -> the driver puts his window-side (left) arm straight out of the doorless
-- door opening towards the car alongside, forearm up, wrist straight, tight fist with the middle finger up.
-- v4: the game has MORE THAN ONE copy of the driver (detailed + distance model), all with the same bone names. v1-v3 only
-- posed the first match, so the other copy kept the old grip arm -> two arms, flicking as the game switched copies.
-- Every copy is now posed identically. ac.updateDriverModel() each frame (CSP: call before moving driver nodes manually,
-- the next model update that would overwrite them is skipped). Always starts from the fresh game pose.
local root = ac.findNodes("carRoot:" .. car.index)
root:findNodes("KK_finger"):setVisible(false)

local function find(ref, n)
  local r = ref:findNodes("DRIVER:" .. n)
  if r:size() == 0 then r = ref:findNodes(n) end
  return r
end

-- one entry per driver copy
local SK = {}
local arms = find(root, "RIG_Arm_L")
for i = 1, arms:size() do
  local arm = arms:at(i)
  local fore, fend, hand = find(arm, "RIG_ForeArm_L"), find(arm, "RIG_ForeArm_END_L"), find(arm, "RIG_HAND_L")
  if fore:size() > 0 and fend:size() > 0 and hand:size() > 0 then
    local s = { arm = arm, fore = fore:at(1), fend = fend:at(1), hand = hand:at(1), middle = {}, curl = {} }
    for _, f in ipairs({ "Middle", "Index", "Ring", "Pinkie" }) do
      for j = 1, 6 do
        local r = find(s.hand, "HAND_" .. f .. j)
        for k = 1, r:size() do table.insert(f == "Middle" and s.middle or s.curl, r:at(k)) end
      end
    end
    SK[#SK + 1] = s
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
local function straight(ref)          -- keep the joint offset, drop its rotation
  local L = ref:getTransformationRaw(); L:set(mat4x4.translation(L.position:clone()))
end
local function doubleCurl(ref)        -- twice the joint's grip rotation
  local L = ref:getTransformationRaw(); local p = L.position:clone()
  local R = L:clone(); R.position = vec3(0, 0, 0)
  local m = R:mul(R); m.position = p; L:set(m)
end

local function pose(s, t)
  local Cw = s.arm:getParent():getWorldTransformationRaw():clone()
  local Aw = s.arm:getWorldTransformationRaw():clone()
  local Fw = s.fore:getWorldTransformationRaw():clone()
  local Hw = s.hand:getWorldTransformationRaw():clone()
  local S, E = Aw.position:clone(), Fw.position:clone()
  local out = car.side:clone()
  if (S - car.position):dot(out) < 0 then out:scale(-1) end      -- the driver's side of the car
  local d1 = (out * 0.95 + car.up * 0.12 + car.look * 0.1):normalize()   -- upper arm straight out sideways
  local d2 = (car.up * 0.97 + out * 0.15):normalize()                     -- forearm straight up
  local Aw2 = aim(Aw, S, E - S, d1, t)
  local dA = Aw:inverse():mul(Aw2)
  local Fw1, Hw1 = Fw:mul(dA), Hw:mul(dA)
  local Fw2 = aim(Fw1, Fw1.position, Hw1.position - Fw1.position, d2, t)
  s.arm:getTransformationRaw():set(Aw2:mul(Cw:inverse()))
  s.fore:getTransformationRaw():set(Fw2:mul(Aw2:inverse()))
  if t > 0.5 then
    straight(s.fend); straight(s.hand)
    for _, r in ipairs(s.middle) do straight(r) end
    for _, r in ipairs(s.curl) do doubleCurl(r) end
  end
end

local t, active = 0, false
function script.update(dt)
  if #SK == 0 then return end
  local want = car.hornActive and 1 or 0
  t = t + (want - t) * math.min(1, dt * 12)
  if t < 0.01 then
    if active then ac.updateDriverModel(); active = false end    -- one clean game update to put everything back
    return
  end
  active = true
  ac.updateDriverModel()                                            -- fresh game pose; next game update skipped
  for _, s in ipairs(SK) do pose(s, t) end
end
