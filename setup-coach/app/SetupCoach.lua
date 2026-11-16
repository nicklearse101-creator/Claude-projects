--[[
  Setup Coach - a Custom Shaders Patch Lua app for Assetto Corsa.

  Reads live telemetry and the car's own data files, coaches the setup in
  the panel, and writes a setup .ini that you load from the in-game Setup
  screen (Assetto Corsa does not let a setup change while the car is on
  track). It never overwrites your own setup files.

  Version history: changelog.txt next to this file.
]]

local VERSION = '3.1.1'
local G = 9.80665

-- Speed (km/h) above which a handling balance issue is treated as
-- aero-relevant (wing/splitter) rather than ARB-relevant. Aero force scales
-- with the square of speed, so it climbs steeply through this range - real
-- setup guides for aero-heavy classes (GT3 and similar) treat corners above
-- roughly this speed as where wings start doing more than roll bars. A
-- lighter-aero or open-wheel car would want this lower; a road-car-based
-- class with little aero would want it higher still - it's deliberately a
-- named constant rather than buried in the logic so it's easy to retune per
-- car class.
-- v2.1.0: 160 -> 180 at the driver's direction ("the threshold for arb/aero
-- should be raised to 180 kmh where aero starts to get priority"). Corners
-- taken between 160 and 180 are now judged as mechanical (ARB/dampers/toe)
-- rather than aero; the wing lever only answers what happens above 180.
local ARB_AERO_SPLIT_KMH = 180

local settings = ac.storage{
  threshold = 2,
  -- v2.0.0: clean complete laps the evidence window must hold before Build
  -- will write (see BUILD_MIN_CORNERS). 1..5; 2 is the considered default.
  buildMinLaps = 2,
  -- Balance target for Build: 'normal' | 'oversteer' | 'understeer'
  -- (BALANCE_MODES).
  balanceMode = 'normal',
  -- Lever history from before the relaxed lever rules is cleared once.
  leverRulesVersion = 0,
  -- v2.0.1: the last Build's output and a running serial, persisted so an
  -- app reload (CSP reloads apps on a session restart, which the driver
  -- does after loading each setup) doesn't lose `lastBuildLoaded` or
  -- restart the Build numbering. Record format: "carId|HH:MM:SS|SEC=v|...".
  lastBuildRecord = '',
  buildSerial = 0,
  -- v2.1.0: per-car lever effectiveness ledger and the levers the last
  -- Build moved (judged by the next window). See LEVER_CHAINS.
  leverLedger = '',
  leverPending = '',
  -- v2.3.0: per-car calculated-target records. rideCal = ride-height
  -- setting vs measured mm (pit stops); camberGain = camber setting vs
  -- loaded camber (Builds); biasBaselineCars = cars whose one-time
  -- calculated brake-bias write has been used ("|car1|car2|").
  rideCal = '',
  camberGain = '',
  biasBaselineCars = '',
  -- v2.4.0: branch passes, one record per car + track + signal. See
  -- BRANCH PASSES.
  branchState = '',
  -- v2.5.0: per-car fingerprint of the physics files ("car>hashes|..."),
  -- so a car whose physics changed under the same id (a mod in progress)
  -- doesn't keep what was learned about the old version. See
  -- PHYSICS FINGERPRINT.
  physicsPrints = '',
  psiRise = 3.0,
  compact = false,
  useKpa = false,
  diagnoseTemps = true,
  sampleReplay = true,
  baseSetupName = '',
  -- LEGACY, v1.4.0-v1.8.1: one combined switch for differential + aero +
  -- brake bias. Split into the three separate toggles below at v1.9.0 by
  -- request. Kept ONLY so an existing "I turned that off" choice can be
  -- carried across rather than silently reverted - see the migration just
  -- after this table, which consumes it.
  writeDiffAeroBrake = true,
  writeBrakeBias = true,
  writeDifferential = true,
  writeAero = true,
  -- v1.7.4: per-module write toggles, by direct request - "once a module
  -- is satisfactory it can be left at the desired value". Front/rear are
  -- split wherever the writer already loops per-axle (dampers, toe) since
  -- that's a real, already-used workflow in this project (e.g. rear
  -- rebound direction has been under active debate independently of
  -- front) - ARB stays one toggle because its own logic can redirect a
  -- push/snap signal to the OTHER bar when one is near its limit, so a
  -- front/rear split wouldn't map cleanly onto what the code actually
  -- does. All default true so upgrading never silently narrows what an
  -- existing setup already relied on.
  writePressures = true,
  writeCamber = true,
  writeSuspension = true,
  writeSprings = true,
  writeARB = true,
  writeDampersFront = true,
  writeDampersRear = true,
  writeFastDampersFront = true,
  writeFastDampersRear = true,
  writeToeFront = true,
  writeToeRear = true,
}

-- Every per-module write toggle, in the order they're drawn. One list so the
-- "All on" button can't drift out of sync with the checkbox list itself.
--
-- v1.7.8 deliberately does NOT force these back on when upgrading. An
-- earlier draft did, on the theory that v1.7.4-v1.7.6's ui.checkbox bug had
-- scrambled them behind the driver's back - but the actual report was the
-- opposite: "i ticked the boxes myself and left some unticked, that's not
-- an error". Silently overriding deliberate choices on upgrade would be
-- exactly the wrong behaviour, and a one-time migration would only serve
-- the "start fresh" need once anyway. Fresh installs already begin all-on
-- (every default above is true); the button below covers wanting that state
-- again at the start of each new car/track, which is the recurring need.
local MODULE_GATE_KEYS = {
  'writePressures', 'writeCamber', 'writeSuspension', 'writeSprings', 'writeARB',
  'writeDampersFront', 'writeDampersRear', 'writeFastDampersFront', 'writeFastDampersRear',
  'writeToeFront', 'writeToeRear', 'writeBrakeBias', 'writeDifferential', 'writeAero',
}

-- v1.9.0 migration, runs at most once. The old combined writeDiffAeroBrake
-- switch became three separate toggles; if a driver had deliberately turned
-- the combined one OFF, that choice has to carry across rather than being
-- quietly reverted to on - the same principle applied when the "all modules
-- on" reset was backed out at v1.7.8 ("i ticked the boxes myself and left
-- some unticked, that's not an error"). Setting the legacy key back to true
-- consumes it, so this can't run twice and can never override a later
-- deliberate change to any of the three.
if settings.writeDiffAeroBrake == false then
  settings.writeBrakeBias = false
  settings.writeDifferential = false
  settings.writeAero = false
  settings.writeDiffAeroBrake = true
end

-- Lever history written under the stricter rules (levers frozen after two
-- tries, branches stopped after a pass with no measurable gain) would keep
-- those levers locked; clear it once so every lever starts fresh.
if (tonumber(settings.leverRulesVersion) or 0) < 2 then
  settings.leverLedger = ''
  settings.leverPending = ''
  settings.branchState = ''
  settings.leverRulesVersion = 2
end

-- Grip trend baseline: a single saved reference point (car+track+conditions)
-- to compare the CURRENT session against, so a setup change can be judged
-- on more than lap time alone. ac.storage's confirmed-working pattern in
-- this app is flat primitive fields (see `settings` above) - rather than
-- gamble on nested-table support that hasn't been verified, this stores one
-- baseline at a time using that same flat pattern. That also matches the
-- natural workflow: set a baseline, change one thing, compare, and if it's
-- better, save it as the new baseline before changing the next thing.
local gripBaseline = ac.storage{
  carId = '',
  trackId = '',
  lowG = 0,
  highG = 0,
  peakG = 0,
  dyF = 0,
  dyR = 0,
  bestLapMs = 0,
  roadTemp = 0,
  fuel = 0,
  savedAt = '',
}

local function clamp(v, a, b)
  if v < a then return a end
  if v > b then return b end
  return v
end

local function n(v, d)
  if type(v) == 'number' and v == v then return v end
  return d or 0
end

local function fmtTime(ms)
  ms = n(ms, 0)
  if ms <= 0 then return '--:--.---' end
  local sec = ms / 1000
  local m = math.floor(sec / 60)
  local s = sec - m * 60
  return string.format('%d:%06.3f', m, s)
end

local function psiStr(psi)
  psi = n(psi, 0)
  if settings.useKpa then
    return string.format('%.0f kPa', psi * 6.89476)
  end
  return string.format('%.1f psi', psi)
end

local function getLastLap(car)
  return n(car.previousLapTimeMs or car.lastLapTimeMs or car.lapTimeMs, 0)
end

local function getBestLap(car)
  return n(car.bestLapTimeMs, 0)
end

local function getAirTemp(sim)
  if not sim then return 0 end
  return n(sim.ambientTemperature, 0)
end

local function getRoadGrip(sim)
  if not sim then return 1 end
  return n(sim.roadGrip or sim.surfaceGrip or 1, 1)
end

--------------------------------------------------------------------------------
-- Ideal pressures
--------------------------------------------------------------------------------

local function classIdeals(carId, compound)
  local id = string.lower(carId or '')
  local c  = string.lower(compound or '')
  if string.find(id, 'formula', 1, true) or string.find(id, 'rss_formula', 1, true)
      or string.find(id, 'tatuus', 1, true) or string.find(id, 'sf15', 1, true)
      or string.find(id, 'sf70', 1, true) or string.find(id, 'f2004', 1, true)
      or string.find(id, 'f1', 1, true) or string.find(id, 'ks_ferrari_sf', 1, true)
      or string.find(id, 'fe_', 1, true) then
    return 16.5, 15.5
  end
  if string.find(id, 'lmp', 1, true) or string.find(id, 'p1', 1, true)
      or string.find(id, 'p2', 1, true) or string.find(id, '919', 1, true)
      or string.find(id, 'ts050', 1, true) or string.find(id, 'hypercar', 1, true)
      or string.find(id, 'lmh', 1, true) then
    return 23.0, 22.5
  end
  if string.find(id, 'gt3', 1, true) or string.find(id, 'gt3_', 1, true) then
    return 26.0, 26.0
  end
  if string.find(id, 'gte', 1, true) or string.find(id, 'gt2', 1, true)
      or string.find(id, 'rsr', 1, true) then
    return 25.5, 25.5
  end
  if string.find(id, 'gt4', 1, true) or string.find(id, 'cup', 1, true)
      or string.find(id, 'trofeo', 1, true) then
    return 26.5, 26.5
  end
  if string.find(c, 'street', 1, true) or string.find(c, 'road', 1, true)
      or string.find(c, 'comfort', 1, true) then
    return 32.0, 32.0
  end
  if string.find(c, 'semislick', 1, true) or string.find(c, 'semi', 1, true) then
    return 29.0, 29.0
  end
  return 26.0, 26.0
end

local function iniGet(ini, section, key, default)
  if not ini then return default end
  local ok, v = pcall(function() return ini:get(section, key, default) end)
  if not ok then return default end
  return v
end

-- v1.9.5: numeric read that returns nil when the key is absent. This exists
-- because ac.INIConfig:get's DEFAULT ARGUMENT SETS THE RETURN TYPE - the
-- SDK: "defaultValue: Defines type of value to return, is returned if value
-- is missing. If not set, list of strings is returned." Every read in this
-- file that passed nil as the default (to mean "give me nil if missing")
-- was therefore handed a string LIST even when the key was present, and
-- tonumber(list) is nil. That single mistake is what "DCAMBER_0/1 came back
-- empty" actually was - on every car, encrypted or not - and it was
-- misdiagnosed for six versions as CSP whitelisting tyres.ini fields. The
-- Dacia Sandero Cup settled it: plain-text data/tyres.ini on disk,
-- DCAMBER_0=1.3 / DCAMBER_1=-15 in the file, PRESSURE_IDEAL (read with a
-- numeric default) worked, DCAMBER (read with nil) didn't.
--
-- Ask for a STRING so a present value comes back as text and a missing one
-- as '' - tonumber turns both into exactly what the caller wanted. The
-- table branch is belt-and-braces for a build that returns the list anyway.
--
-- v1.9.6: used by EVERY nil-default read in this file now - tyres.ini,
-- setup.ini, aero.ini, suspensions.ini. v1.9.5 fixed tyres.ini alone and
-- held the other three back as separate decisions; the driver's answer
-- was that live data winning is the whole point of the app. Each of the
-- three had its own regression risk, handled where it lives: readSetupItem
-- (unit conventions verified against the live spinners), checkAeroLutRisk
-- (was crashing on string.lower(table) inside its pcall - never ran), and
-- readDamperCrossover (multipliers re-anchored to the validated car's real
-- number). Inline ';' comments are stripped - Kunos' own files carry them
-- on the value line ("MIN=-5   ;degrees").
local function iniStr(ini, section, key)
  if not ini then return nil end
  local ok, v = pcall(function() return ini:get(section, key, '') end)
  if not ok then return nil end
  if type(v) == 'table' then v = v[1] end
  if type(v) ~= 'string' then return nil end
  v = v:gsub(';.*$', ''):gsub('^%s+', ''):gsub('%s+$', '')
  if v == '' then return nil end
  return v
end

local function iniNum(ini, section, key)
  return tonumber(iniStr(ini, section, key))
end

-- Reads this tyre's own reference numbers straight from its physics data
-- (same technique as tyres.ini/suspensions.ini elsewhere in this file):
--   hotF/hotR   - target HOT (operating) pressure: PRESSURE_IDEAL, falling
--                 back to a per-class matrix guess if tyres.ini can't be read.
--   coldF/coldR - this tyre's own reference COLD/static fill pressure
--                 (PRESSURE_STATIC) - the actual number the tyre was designed
--                 and tested around, when the file states one. nil if
--                 unavailable, or if we had to fall back to the class matrix
--                 (which has no matching cold reference of its own).
--   dy0F/dy0R   - peak lateral friction coefficient reference (DY0). Used to
--                 turn a raw, hard-to-interpret measured grip number into a
--                 "% of this tyre's own peak" figure instead.
-- Reads this tyre's own physics constants straight from tyres.ini. Confirmed
-- readable even on cars whose data/setup.ini is encrypted (the Ferrari 458
-- GT2 test car returns real 26/27 psi targets from here, which are NOT the
-- class-matrix fallback values - proof the file itself is being read).
-- Returns a table so this can keep growing without churning the call site.
--   hotF/hotR   - PRESSURE_IDEAL: the target HOT (operating) pressure.
--   coldF/coldR - PRESSURE_STATIC: this tyre's own reference COLD pressure.
--                 The gap between the two is the tyre designer's own stated
--                 cold->hot rise (e.g. 18 static -> 26 ideal = 8 psi rise),
--                 which matches the ~9 psi rise measured on track.
--   dcamber0/1  - the camber-sensitivity coefficients of AC's tyre model.
--                 Grip vs inclination angle is approximately
--                     grip(c) = 1 + DCAMBER_0*c + DCAMBER_1*c^2   (c in rad)
--                 a downward parabola (DCAMBER_1 is negative), so its peak -
--                 the inclination angle where this tyre makes maximum
--                 lateral force - is at d/dc = 0:
--                     DCAMBER_0 + 2*DCAMBER_1*c = 0
--                     c_peak = -DCAMBER_0 / (2*DCAMBER_1)
--                 Same relationship the "Camber Extravaganza" app uses.
--                 Sanity-checked on two real cars: 4.00 deg and 3.38 deg,
--                 both squarely in the normal range for GT slicks.
--   dy0F/dy0R   - peak lateral friction coefficient reference, used to turn
--                 raw measured grip into a "% of this tyre's own peak".
--
-- v1.9.7: reads the compound that is actually FITTED. AC's tyres.ini holds
-- one [FRONT]/[REAR] pair per compound - [FRONT] (or [FRONT_0]) is index 0,
-- [FRONT_1], [FRONT_2]... the rest - and the numbers differ per compound.
-- Until now this always read [FRONT]. Found on the BMW E30 drift car's own
-- file: compound 0/1 ("Street 90s"/"Street") say PRESSURE_IDEAL=38 and
-- DCAMBER_0=1.1; compound 2 ("Semislick") says 31 and 1.2. A driver on
-- semislicks would have been given a pressure target 7 psi too high. The
-- section is picked by `compoundIndex` (ac.StateCar.compoundIndex, the
-- game's own 0-based index of the fitted set), confirmed by SHORT_NAME
-- when the file states one, falling back to [FRONT] as before.
local function readTyreReference(carIndex, carId, compound, compoundIndex)
  local r = {hotF = 0, hotR = 0}
  local ok, ini = pcall(ac.INIConfig.carData, carIndex, 'tyres.ini')
  if ok and ini then
    local idx = tonumber(compoundIndex) or 0
    if idx < 0 then idx = 0 end
    local secF, secR = 'FRONT', 'REAR'
    if idx > 0 then
      local candF, candR = 'FRONT_' .. idx, 'REAR_' .. idx
      if iniNum(ini, candF, 'PRESSURE_IDEAL') then secF, secR = candF, candR end
    elseif not iniNum(ini, 'FRONT', 'PRESSURE_IDEAL') and iniNum(ini, 'FRONT_0', 'PRESSURE_IDEAL') then
      secF, secR = 'FRONT_0', 'REAR_0'
    end
    -- Cross-check: if the chosen section names a SHORT_NAME and it doesn't
    -- match the fitted set's, search the file for the one that does.
    local want = compound and compound ~= '' and string.upper(compound) or nil
    local have = iniStr(ini, secF, 'SHORT_NAME')
    if want and have and string.upper(have) ~= want then
      for i = 0, 9 do
        local s = i == 0 and 'FRONT' or ('FRONT_' .. i)
        local sn = iniStr(ini, s, 'SHORT_NAME')
        if sn and string.upper(sn) == want then
          secF, secR = s, (i == 0 and 'REAR' or ('REAR_' .. i))
          break
        end
      end
    end
    r.compoundSection = secF
    r.compoundName = iniStr(ini, secF, 'NAME')
    r.hotF = iniNum(ini, secF, 'PRESSURE_IDEAL') or 0
    r.hotR = iniNum(ini, secR, 'PRESSURE_IDEAL') or 0
    r.coldF = iniNum(ini, secF, 'PRESSURE_STATIC')
    r.coldR = iniNum(ini, secR, 'PRESSURE_STATIC')
    -- v1.9.9: DY0 is the peak friction coefficient of AC's OLD linear
    -- load model (D = DY0 + DY1 x load). Modern tyres (the Corvette Z06
    -- GT3's Michelin S8M: DY0=0, DY1=0) use the load-sensitivity model
    -- instead - DY_REF at reference load FZ0 with exponent LS_EXPY - and
    -- leave DY0 at 0. So on those cars "% of tyre peak" had no reference
    -- and the panel showed raw dy. DY_REF is the equivalent reference for
    -- that model (the coefficient AT FZ0; it falls with load above that,
    -- so the % is a slight understatement on a loaded GT3 - labelled).
    -- v2.3.0: rolling radius of the fitted compound, for the brake-bias
    -- target (brake force = torque / radius).
    r.radiusF = iniNum(ini, secF, 'RADIUS')
    r.radiusR = iniNum(ini, secR, 'RADIUS')
    -- v2.5.0: LONGITUDINAL grip model per axle, for the brake-bias target.
    -- AC tyres lose grip per newton as load rises: the version-10 model
    -- gives the braking force limit as DX_REF x FZ0 x (Fz / FZ0)^LS_EXPX
    -- (friction DX_REF at the reference load FZ0, falling above it); the
    -- older linear model gives mu = DX0 + DX1 x Fz (kN). The heavily loaded
    -- front under braking therefore grips LESS per kilo than the rear, and
    -- a bias set to the load split alone sits too far forward - the
    -- Sunbeam's lockups said so (fronts first at 69%, target said 77%).
    local function brakeModel(sec)
      local m = {dxRef = iniNum(ini, sec, 'DX_REF'), fz0 = iniNum(ini, sec, 'FZ0'), lsx = iniNum(ini, sec, 'LS_EXPX'),
        dx0 = iniNum(ini, sec, 'DX0'), dx1 = iniNum(ini, sec, 'DX1')}
      if m.dxRef and m.dxRef > 0.2 and m.fz0 and m.fz0 > 100 and m.lsx and m.lsx > 0.2 and m.lsx <= 1.2 then
        m.kind = 'ls'
      elseif m.dx0 and m.dx0 > 0.2 and m.dx1 and m.dx1 < 0 then
        m.kind = 'linear'
      end
      return m.kind and m or nil
    end
    r.brakeModelF, r.brakeModelR = brakeModel(secF), brakeModel(secR)
    r.dy0F = iniNum(ini, secF, 'DY0')
    r.dy0R = iniNum(ini, secR, 'DY0')
    r.dyRefUsed = false
    if not r.dy0F or r.dy0F < 0.1 then
      r.dy0F = iniNum(ini, secF, 'DY_REF')
      r.dyRefUsed = r.dy0F ~= nil
    end
    if not r.dy0R or r.dy0R < 0.1 then r.dy0R = iniNum(ini, secR, 'DY_REF') end
    r.dcamber0F = iniNum(ini, secF, 'DCAMBER_0')
    r.dcamber1F = iniNum(ini, secF, 'DCAMBER_1')
    r.dcamber0R = iniNum(ini, secR, 'DCAMBER_0')
    r.dcamber1R = iniNum(ini, secR, 'DCAMBER_1')
    -- v1.9.9: a tyre may define its camber-grip curve as a LUT instead of
    -- (or as well as) the DCAMBER_0/1 parabola. When present, the LUT is
    -- what the physics uses; the engine samples it for the real peak.
    r.dcamberLutF = iniStr(ini, secF, 'DCAMBER_LUT')
    r.dcamberLutR = iniStr(ini, secR, 'DCAMBER_LUT')
  end
  if r.hotF >= 10 and r.hotF <= 45 then
    if r.hotR < 10 then r.hotR = r.hotF end
    r.src = 'tyres.ini'
    if r.compoundSection then
      r.src = string.format('tyres.ini [%s%s]', r.compoundSection,
        r.compoundName and (' "' .. r.compoundName .. '"') or '')
    end
  else
    r.hotF, r.hotR = classIdeals(carId, compound)
    r.src = 'class matrix'
    r.coldF, r.coldR = nil, nil
  end
  return r
end

-- Fallback DCAMBER lookup, 4.6.0. Built on the belief that CSP exposes only
-- a WHITELIST of tyres.ini fields on cars with encrypted data, because on
-- the test car PRESSURE_IDEAL read fine while DCAMBER_0/1 came back empty.
-- v1.9.5 CORRECTION: that was never a whitelist. PRESSURE_IDEAL was read
-- with a numeric default and DCAMBER with nil, and ac.INIConfig:get's
-- default argument sets its return type (see iniNum). The live read is now
-- fixed and takes priority; this table remains as the fallback for cars
-- whose tyres.ini genuinely lacks the coefficients.
--
-- 86 entries are Kunos' own official car IDs (from the community
-- "Camber Extravaganza" reference data), guaranteed to match. A further
-- handful are from real cars unpacked and measured directly during this
-- project - bmw_z4_gt3's value (1.65, -13) matches its Kunos base.json
-- entry EXACTLY, cross-validating the extraction. The rest of the newly
-- measured cars use placeholder IDs since their real installed folder
-- names aren't known - they're harmless if unmatched (falls through to
-- thermal, same as today) but won't actually fire until corrected to each
-- car's real ac.getCarID() string.
--
-- Only one compound's coefficients are kept per axle (preferring 'ST',
-- then whatever's available) - DCAMBER does vary a little by compound,
-- but the peak angle it implies rarely shifts enough to matter next to
-- everything else approximated in this calculation.
local DCAMBER_LOOKUP = {
  ['abarth500']={1.1,-13,1.1,-13},
  ['abarth500_s1']={1.1,-13,1.1,-13},
  ['alfa_romeo_giulietta_qv']={1.1,-13,1.1,-13},
  ['alfa_romeo_giulietta_qv_le']={1.1,-13,1.1,-13},
  ['bmw_1m']={1.1,-13,1.1,-13},
  ['bmw_1m_s3']={1.1,-13,1.1,-13},
  ['bmw_m3_e30']={1.1,-13,1.1,-13},
  ['bmw_m3_e30_drift']={1.1,-13,1.1,-13},
  ['bmw_m3_e30_dtm']={1.3,-15,1.3,-15},
  ['bmw_m3_e30_gra']={1.3,-15,1.3,-15},
  ['bmw_m3_e30_s1']={1.1,-13,1.1,-13},
  ['bmw_m3_e92']={1.1,-13,1.1,-13},
  ['bmw_m3_e92_drift']={1.1,-13,1.1,-13},
  ['bmw_m3_e92_s1']={1.1,-13,1.1,-13},
  ['bmw_m3_gt2']={1.65,-14,1.65,-14},
  ['bmw_z4']={1.1,-13,1.1,-13},
  ['bmw_z4_drift']={1.1,-13,1.1,-13},
  ['bmw_z4_gt3']={1.65,-13,1.65,-13},
  ['bmw_z4_s1']={1.1,-13,1.1,-13},
  -- 'escort_mk2_rally' was a guessed slug (wrong folder, but correct
  -- values by luck) - real folder confirmed via decryption is
  -- ford_escort_mk2_rally_spec, with 3 more variants sharing identical
  -- tyre data (checked all 4 directly).
  ['ford_escort_mk2_rally_spec']={1.7,-8,1.7,-8},
  ['ford_escort_mk2_rally_spec_lhd']={1.7,-8,1.7,-8},
  ['ford_escort_mk2_rally_spec_rhd']={1.7,-8,1.7,-8},
  ['ford_escort_mk2_rally_spec_(night)']={1.7,-8,1.7,-8},
  ['ferrari_312t']={1.3,-12,1.3,-12},
  -- Corrected from real tyres.ini (was 1.1,-13 - a guess/typo, not this
  -- car's actual coefficients).
  ['ferrari_458']={1.2,-13,1.2,-13},
  ['ferrari_458_gt2']={1.65,-14,1.65,-14},
  -- Corrected from real tyres.ini (was 1.2,-13 - well off; real DCAMBER_0
  -- is 2.0).
  ['ferrari_458_s3']={2,-13,2,-13},
  ['ferrari_599xxevo']={1.6,-13,1.6,-13},
  ['ferrari_f40']={1.1,-13,1.1,-13},
  ['ferrari_f40_s3']={1.2,-13,1.2,-13},
  ['ferrari_laferrari']={1.2,-13,1.2,-13},
  -- Still unresolved/inert: 'ford_focus_st20' below, and
  -- 'hyundai_elantra_n_tcr'/'mitsubishi_evo6' further down. No installed
  -- car folder matches any of these three even loosely - the only
  -- candidates found were clearly third-party mods (btcc_ford_focus,
  -- fsr_focus_btcc, fw_elantra_tcr_2024, hk51_tcr_hyundai_elantra_n,
  -- streetcarpack_mitsubishi_lancer_evo_gsr, etc.), which is exactly the
  -- kind of guess this audit is trying to eliminate, not repeat - a
  -- mod's specific coefficients aren't safely assumed to match a
  -- differently-named guess. Left inert (harmless: falls through to the
  -- thermal method) rather than force-matched.
  ['ford_focus_st20']={2,-13,2,-13},
  -- Renamed from 'formula_hybrid_2024' - real installed folder confirmed
  -- via decryption is rss_formula_hybrid_2024; values matched exactly.
  ['rss_formula_hybrid_2024']={1.042,-6.861,1.211,-11.584},
  -- Renamed from 'formula_rss_4' - real folder is rss_formula_rss_4;
  -- values matched (stored was truncated to 6 decimals, same number).
  ['rss_formula_rss_4']={0.982213,-8.03953,0.982213,-8.03953},
  ['hyundai_elantra_n_tcr']={2,-13,2,-13},
  ['ks_abarth_595ss']={0,-3,0,-3},
  ['ks_abarth_595ss_s1']={0,-3,0,-3},
  ['ks_abarth_595ss_s2']={0,-3,0,-3},
  ['ks_alfa_33_stradale']={0,-3,0,-3},
  ['ks_alfa_giulia_qv']={1.2,-13,1.2,-13},  -- corrected from real tyres.ini, was 1.1
  ['ks_alfa_mito_qv']={1.1,-13,1.1,-13},
  ['ks_audi_a1s1']={1.2,-13,1.2,-13},  -- corrected from real tyres.ini, was 1.1
  ['ks_audi_r8_plus']={1.1,-13,1.1,-13},
  ['ks_audi_sport_quattro']={1.1,-13,1.1,-13},
  ['ks_audi_sport_quattro_rally']={1.2,-15,1.2,-15},
  ['ks_audi_sport_quattro_s1']={1.1,-13,1.1,-13},
  ['ks_corvette_c7_stingray']={1.1,-13,1.1,-13},
  ['ks_ford_mustang_2015']={1.1,-13,1.1,-13},
  ['ks_lamborghini_huracan_performante']={1.2,-13,1.2,-13},
  ['ks_lamborghini_miura_sv']={1,-13,1,-13},
  ['ks_lamborghini_sesto_elemento']={1.2,-13,1.2,-13},
  ['ks_maserati_alfieri']={1.1,-13,1.1,-13},
  ['ks_maserati_levante']={1.1,-13,1.1,-13},
  ['ks_maserati_quattroporte']={1.1,-13,1.1,-13},
  ['ks_mazda_787b']={1.1,-12,1.1,-12},
  ['ks_mazda_miata']={1.1,-13,1.1,-13},
  ['ks_nissan_gtr']={1.2,-13,1.2,-13},
  ['ks_pagani_huayra_bc']={1.2,-13,1.2,-13},
  ['ks_porsche_718_boxster_s']={1.2,-13,1.2,-13},  -- corrected, was 1.1
  ['ks_porsche_718_boxster_s_pdk']={1.2,-13,1.2,-13},  -- corrected, was 1.1
  ['ks_porsche_718_spyder_rs']={0,-4,0,-4},
  ['ks_porsche_911_gt1']={1.1,-12,1.1,-12},
  ['ks_porsche_911_gt3_rs']={1.2,-12,1.2,-12},
  ['ks_porsche_919_hybrid_2015']={1.65,-13,1.65,-13},
  ['ks_porsche_962c_longtail']={1.1,-12,1.1,-12},
  ['ks_porsche_962c_shorttail']={1.1,-12,1.1,-12},
  ['ks_porsche_cayenne']={1.1,-13,1.1,-13},
  ['ks_porsche_cayman_gt4_std']={1.2,-13,1.2,-13},
  ['ks_porsche_macan']={1.1,-13,1.1,-13},
  ['ks_porsche_panamera']={1.2,-12,1.2,-12},
  ['ks_toyota_gt86']={1.1,-13,1.1,-13},
  ['ktm_xbow_r']={1.2,-13,1.2,-13},
  ['lotus_2_eleven']={1.2,-13,1.2,-13},
  ['lotus_2_eleven_gt4']={1.2,-13,1.2,-13},
  ['lotus_49']={0,-3,0,-3},
  ['lotus_98t']={1.1,-12,1,-12},
  ['lotus_elise_sc']={1.1,-13,1.1,-13},
  ['lotus_elise_sc_s1']={1.1,-13,1.1,-13},
  ['lotus_elise_sc_s2']={1.1,-13,1.1,-13},
  ['lotus_evora_gtc']={1.65,-13,1.65,-13},
  ['lotus_evora_gte']={1.1,-13,1.1,-13},
  ['lotus_evora_gte_carbon']={1.1,-13,1.1,-13},
  ['lotus_evora_gx']={1.65,-14,1.65,-14},
  ['lotus_evora_s']={1.1,-13,1.1,-13},
  ['lotus_evora_s_s2']={1.1,-13,1.1,-13},
  ['lotus_exige_240']={1.1,-13,1.1,-13},
  ['lotus_exige_240_s3']={1.1,-13,1.1,-13},
  ['lotus_exige_s']={1.1,-13,1.1,-13},
  ['lotus_exige_s_roadster']={1.1,-13,1.1,-13},
  ['lotus_exige_scura']={1.1,-13,1.1,-13},
  ['lotus_exige_v6_cup']={1.1,-13,1.1,-13},
  ['lotus_exos_125']={1.4,-13,1.4,-13},
  ['lotus_exos_125_s1']={1.4,-13,1.4,-13},
  ['ks_mclaren_f1_gtr']={1.1,-12,1.1,-12},  -- renamed from 'mclaren_f1_gtr' (wrong folder, real values matched)
  ['mclaren_mp412c']={1.2,-13,1.2,-13},  -- corrected from real tyres.ini, was 1.1
  ['mclaren_mp412c_gt3']={1.65,-13,1.65,-13},
  ['mercedes_sls']={1.1,-13,1.1,-13},
  ['mercedes_sls_gt3']={1.65,-13,1.65,-13},
  ['mitsubishi_evo6']={1.2,-13,1.2,-13},
  ['p4-5_2011']={1.65,-14,1.65,-14},
  ['pagani_huayra']={1.2,-13,1.2,-13},
  ['pagani_zonda_r']={1.6,-13,1.6,-13},
  ['ruf_yellowbird']={1.1,-13,1.1,-13},
  ['shelby_cobra_427sc']={0,-3,0,-3},
  ['tatuusfa1']={1.5,-13,1.5,-13},
}

-- Same idea as DCAMBER_LOOKUP above, for the same reason: v1.2.0's live
-- aero-peak-height/dynamic-controller detection (checkAeroLutRisk) reads
-- aero.ini through ac.INIConfig.carData, which is confirmed DEAD in
-- practice on at least one real encrypted car - aeroLutChecked=false and
-- aeroPeaks/aeroDynamic empty in every real debug log seen this project,
-- despite this project's own offline decryption confirming the car
-- genuinely has real GH_CL curves and a dynamic controller. Same
-- whitelist-shaped gap as DCAMBER, so the same fix: bake real numbers,
-- extracted offline via the acd_decoder.py tool (see
-- D:\Claude\setupcoach-tools\acd), used ONLY when the live read comes
-- back with nothing. peaks are in METRES (same units as car.rideHeight
-- and the live GH_CL check), dynamic is the same {wing, input} shape
-- checkAeroLutRisk already returns.
local AERO_LOOKUP = {
  ['ferrari_458_gt2'] = {
    peaks = { front = 0.050, diffuser = 0.050 },
    dynamic = { { wing = 'diffuser', input = 'SPEED_KMH' } },
  },
}

-- Peak-grip inclination angle in DEGREES, always returned as a positive
-- magnitude. nil when this tyre doesn't publish usable coefficients.
local function peakCamberAngle(dcamber0, dcamber1)
  if not dcamber0 or not dcamber1 then return nil end
  if dcamber1 >= -0.001 then return nil end
  local rad = -dcamber0 / (2 * dcamber1)
  local deg = math.abs(math.deg(rad))
  if deg < 0.2 or deg > 9 then return nil end
  return deg
end


-- v2.5.0: THE CAR'S OWN TRAVEL LIMIT, per axle, for every "% of travel"
-- (bottoming, spring hits, the calculated spring target, the SUSPENSION
-- panel line). Until now this read a [FRONT]/[REAR] TRAVEL key that no car
-- has - none of ten real cars checked - so EVERY car was measured against
-- a made-up 0.12 m: short-travel GT cars (Huracan packers 55 mm) could
-- never register bottoming at all (0 in every log), long-travel cars (the
-- Sunbeam's 140 mm front) registered it early and had ride height raised
-- and springs stiffened on every Build. AC's own limit is PACKER_RANGE
-- ("total suspension movement range before hitting packers"), and
-- telemetry's suspensionTravel counts from full droop (the Sunbeam reads
-- 63 mm sitting in the pits, 45% of its range), so PACKER_RANGE is the 100%
-- mark. Returns front, rear (m) and where they came from; the live setup's
-- adjustable packers override this per corner (engine:refreshTravelRef).
local TRAVEL_FALLBACK_M = 0.12
local function travelRefSane(v) return type(v) == 'number' and v >= 0.01 and v <= 0.5 end
local function readTravelRef(carIndex)
  local ok, ini = pcall(ac.INIConfig.carData, carIndex, 'suspensions.ini')
  local tf, tr
  if ok and ini then
    tf = iniNum(ini, 'FRONT', 'PACKER_RANGE')
    tr = iniNum(ini, 'REAR', 'PACKER_RANGE')
  end
  local fOk, rOk = travelRefSane(tf), travelRefSane(tr)
  local src = (fOk and rOk) and 'suspensions.ini PACKER_RANGE'
    or ((fOk or rOk) and 'suspensions.ini PACKER_RANGE (one axle missing - 0.12 m assumed there)'
    or 'no PACKER_RANGE in suspensions.ini - 0.12 m assumed')
  return fOk and tf or TRAVEL_FALLBACK_M, rOk and tr or TRAVEL_FALLBACK_M, src
end

-- v2.5.0: braking force limit (N) of one tyre at load fz (N), from the
-- axle's grip model (see readTyreReference). nil when the tyre states none.
local function tyreBrakeForce(m, fz)
  if not m or type(fz) ~= 'number' or fz <= 0 then return nil end
  if m.kind == 'ls' then return m.dxRef * m.fz0 * (fz / m.fz0) ^ m.lsx end
  if m.kind == 'linear' then
    local mu = m.dx0 + m.dx1 * fz / 1000
    if mu < 0.1 then mu = 0.1 end
    return mu * fz
  end
  return nil
end

-- The car's own slow/fast damper crossover velocity, from suspensions.ini
-- (DAMP_FAST_BUMPTHRESHOLD). Above this shaft speed AC applies the FAST
-- damper curve; below it, the slow curve.
--
-- Worth knowing why this matters: this app's damper event detection used
-- fixed thresholds of 0.55 and 1.2 m/s, but a real car's crossover is around
-- 0.06 m/s - so BOTH of those sit well inside the fast-damper regime, and
-- what was labelled "slow damper" advice was really being driven by
-- fast-regime data. Rather than rip out detection that is calibrated and
-- working, the thresholds are now derived from this value as multiples,
-- chosen so a typical 0.06 car lands on ~0.54 and ~1.2 (i.e. unchanged),
-- while a car with unusually stiff or soft damping scales with it.
-- Checks this car's OWN aero curves for a real peak or stall within their
-- defined range - see the AERO advice comment for the full reasoning.
-- ac.DataLUT11.carData's existence in APP context (not just physics
-- scripts) is now confirmed directly from CSP's own shipped Lua type
-- definitions (extension/internal/lua-sdk) rather than assumed - the exact
-- signature ac.DataLUT11.carData(carIndex, fileName) is right there. What's
-- still a genuine assumption is the SAMPLING itself: the definitions
-- confirm the function exists, not that :get() extrapolates safely outside
-- a LUT's defined domain, so this stays defensive - if aero.ini doesn't
-- parse or a sample throws, it returns "unchecked" and the caller falls
-- back to the class-based static caveat, so a failure here still costs
-- nothing.
--
-- Domain-appropriate sampling matters: AOA curves are in degrees (roughly
-- -15 to +30), GH curves are in metres (roughly 0 to 0.15) - sampling the
-- wrong range risks the LUT extrapolating into meaningless territory and
-- producing a false alarm, so each file is sampled only in the range that
-- matches which aero.ini field referenced it.
--
-- Extended this version with two more things read from the same aero.ini,
-- both confirmed directly against real GT3 cars' own unencrypted data
-- (ks_lamborghini_huracan_gt3, trr_mclaren_720_gt3, fsr_audi_lms_evo_ii_gt3
-- - the test car's own aero.ini is encrypted, same as everywhere else this
-- kind of cross-check has been needed in this project):
--
--   1) The actual PEAK HEIGHT of the GH_CL curve for the front splitter
--      (WING_1) and diffuser (WING_3) - the same WING_1/WING_2 convention
--      SETUP_PROBE.wingFront/wingRear already assumes. Real numbers from
--      two independent GT3 mods: both peak right around 0.045-0.050m
--      (1.02-1.07x multiplier), falling to near-zero BELOW ~0.038m (a hard
--      near-ground stall, not a gentle taper) and down to ~20% of peak by
--      0.155m. The REAR wing (WING_2) had no GH_CL curve at all on either
--      car - rake's aero benefit runs through the front/diffuser only,
--      confirming the mechanical/CoG reasoning already behind the RAKE
--      writer. Returned so the caller can compare it against the car's own
--      live ride height (car.rideHeight, confirmed in meters, same units
--      as this LUT's x-axis) - a rake nudge that's already at or below
--      this peak would push toward the stall side, not away from it.
--   2) DYNAMIC_CONTROLLER_N sections - not part of the static AOA/GH
--      curves at all. All three real GT3 cars checked had one, all keyed
--      on INPUT=SPEED_KMH driving WING=3 (diffuser): confirmed on the
--      Huracan specifically, +12deg of extra angle below ~70 km/h, ramping
--      (FILTER=0.80) to +0deg by 120 km/h. Full INPUT vocabulary these
--      sections can use (per CSP modding references, not all observed
--      directly here): SPEED_KMH, BRAKE, GAS, STEER, LATG, LONG, RPMS,
--      GEAR, SUS_TRAVEL_LR/RR, AVG_TRAVEL_REAR, LOAD_SPREAD_LF/RF,
--      SLIPANGLE_*/SLIPRATIO_*, OVERSTEER_FACTOR, REAR_SPEED_RATIO,
--      WHEEL_STEER_DEG, CONST - so on some cars a wing's real angle (and
--      therefore a manual click's actual effect) isn't constant, it's
--      reactive to speed or even handling state. Detected here purely to
--      surface as an advice caveat - the live added angle itself isn't
--      read (would need the controller's own LUT sampled against current
--      telemetry, a bigger lift than this needs to claim).
-- Which real aero surface WING_i actually is, if any. The fixed
-- WING_1=front/WING_2=rear/WING_3=diffuser convention (the one
-- SETUP_PROBE.wingFront/wingRear already assumed, pre-dating this) holds
-- on every real GT3 car checked (Huracan, McLaren 720, Audi LMS Evo II -
-- all NAME their wings FRONT/REAR/DIFFUSER at exactly those indices), but
-- does NOT hold universally - confirmed directly on a real kart
-- (gokart100): its WING_1/WING_2 are NAMEd MID_L/MID_R, side wings that
-- model driver body-lean drag, not front/rear aero at all; the real wing
-- NAMEd FRONT sits at WING_3 instead. Trusting position alone there would
-- mislabel real data. NAME is checked first and wins when it clearly
-- names a role; the positional convention is only a fallback for wings
-- whose NAME is blank or unrecognised, never used to override a NAME that
-- says something else.
local function wingRoleFromName(name, positionalGuess)
  if name and name ~= '' then
    local n = string.lower(name)
    -- v1.9.9: diffuser checked FIRST - a "REAR DIFFUSER" is a diffuser, and
    -- with 'rear' tested first it was the rear wing.
    if string.find(n, 'diffuser', 1, true) then return 'diffuser' end
    if string.find(n, 'front', 1, true) or string.find(n, 'splitter', 1, true) then return 'front' end
    if string.find(n, 'rear', 1, true) then return 'rear' end
    -- Named, but not with a recognised keyword (e.g. this kart's MID_L/
    -- MID_R, or a BODY/DRIVER_* aero-drag proxy) - don't guess from
    -- position, say unknown instead. Better to lose a caveat than mislabel
    -- real data with a role it isn't.
    return nil
  end
  return positionalGuess
end

local function checkAeroLutRisk(carIndex)
  local ok, ini = pcall(ac.INIConfig.carData, carIndex, 'aero.ini')
  if not ok or not ini then return false, false end

  local function sampleShape(lutFile, xs)
    if not lutFile or lutFile == '' or lutFile:lower() == 'empty.lut' or lutFile:lower() == '1.lut' then
      return nil
    end
    local okLut, lut = pcall(function() return ac.DataLUT11.carData(carIndex, lutFile) end)
    if not okLut or not lut then return nil end
    local samples, sampleXs = {}, {}
    for _, x in ipairs(xs) do
      local okV, v = pcall(function() return lut:get(x) end)
      if okV and type(v) == 'number' then
        table.insert(samples, v)
        table.insert(sampleXs, x)
      end
    end
    if #samples < 4 then return nil end
    local maxV, maxX, sawFall, sawFlip = samples[1], sampleXs[1], false, false
    for i = 2, #samples do
      if (samples[i-1] >= 0 and samples[i] < 0) or (samples[i-1] < 0 and samples[i] >= 0) then sawFlip = true end
      if samples[i] > maxV then maxV, maxX = samples[i], sampleXs[i]
      elseif maxV > 0.01 and samples[i] < maxV * 0.85 then sawFall = true end
    end
    return sawFall or sawFlip, maxX
  end

  local aoaXs = {-15, -10, -8, -5, -2, 0, 1, 2, 3, 4, 5, 6, 8, 10, 12, 15, 20, 25, 30}
  local ghXs = {0, 0.005, 0.010, 0.020, 0.030, 0.040, 0.050, 0.060, 0.070, 0.080, 0.090, 0.100, 0.120, 0.150}
  local POSITIONAL_GUESS = {[1] = 'front', [2] = 'rear', [3] = 'diffuser'}

  -- Resolve every WING_i's role ONCE (name-verified, see
  -- wingRoleFromName), reused below for both the GH-peak detection and the
  -- DYNAMIC_CONTROLLER lookup, and returned so the caller can use the same
  -- confirmed indices for live per-frame reads (ac.getCarPhysics().wings)
  -- instead of assuming position there too.
  -- v1.9.6: iniStr, not iniGet(..., nil). The nil default returned a
  -- string LIST (see iniNum), which is truthy and ~= '', so
  -- wingRoleFromName called string.lower() on a table and threw - inside
  -- this function's pcall, so the whole check silently returned nothing.
  -- That is what "aeroLutChecked=false" in every log ever written was:
  -- not a CSP limitation, a crash on the first line of the loop.
  local roleByIndex, indexByRole = {}, {}
  for i = 0, 9 do
    local name = iniStr(ini, 'WING_' .. i, 'NAME')
    local role = wingRoleFromName(name, POSITIONAL_GUESS[i])
    if role then
      roleByIndex[i] = role
      indexByRole[role] = i
    end
  end

  local checked, risk, peaks = false, false, {}
  for i = 0, 9 do
    local sec = 'WING_' .. i
    local aoaFile = iniStr(ini, sec, 'LUT_AOA_CL')
    local ghFile = iniStr(ini, sec, 'LUT_GH_CL')
    if aoaFile then
      local r = sampleShape(aoaFile, aoaXs)
      if r ~= nil then checked = true; if r then risk = true end end
    end
    if ghFile then
      local r, peakX = sampleShape(ghFile, ghXs)
      if r ~= nil then
        checked = true
        if r then risk = true end
        local role = roleByIndex[i]
        if role and peakX then peaks[role] = peakX end
      end
    end
  end

  local dynamicInputs, seenDynamic = {}, {}
  for i = 0, 9 do
    local sec = 'DYNAMIC_CONTROLLER_' .. i
    local wingIdx = iniNum(ini, sec, 'WING')
    local input = iniStr(ini, sec, 'INPUT')
    if wingIdx and input then
      local role = roleByIndex[wingIdx] or ('wing ' .. wingIdx)
      local key = role .. ':' .. tostring(input)
      if not seenDynamic[key] then
        seenDynamic[key] = true
        table.insert(dynamicInputs, {wing = role, input = tostring(input)})
      end
    end
  end

  return checked, risk, peaks, dynamicInputs, indexByRole
end

-- Shared by the RAKE advice text and the RAKE ride-height writer below -
-- compares the car's live static front ride height (car.rideHeight[0],
-- confirmed in metres) against the aero peak height checkAeroLutRisk found
-- from the same car's own GH_CL curve, same units, so the comparison is
-- direct rather than another unit-guessing exercise like ride height's
-- existing sign-convention caveat. Deliberately only ever ADDS a caveat -
-- never reverses or skips the rake write. The mechanical/CoG rake benefit
-- (weight transfer, floor angle) is real regardless of where the aero
-- curve peaks, so silently second-guessing the direction risks being
-- confidently wrong in a NEW way, the same reasoning that kept front-
-- rebound softening unautomated in v1.0.0 pending better evidence.
local function rideHeightStallCaveat(self)
  if not (self.rideHeightCaptured and self.aeroPeaks and self.aeroPeaks.front) then return '' end
  if self.staticRideHeightF > self.aeroPeaks.front then return '' end
  return string.format(
    ' [⚠ front is already at/below this car\'s own aero peak height (~%.0fmm, currently ~%.0fmm) - the mechanical rake benefit still applies, but lowering further may cost front downforce rather than add it, per this car\'s own curve]',
    self.aeroPeaks.front * 1000, self.staticRideHeightF * 1000)
end

-- v2.2.0: damper EVENT thresholds (wheel-travel velocity, m/s) - fixed for
-- every car; see refreshTargets for why the crossover no longer scales them.
local DAMPER_EVENT_MODERATE = 0.54
local DAMPER_EVENT_SHARP = 1.20

-- v1.9.6: reads for real now (iniNum). Real values from four cars' own
-- suspensions.ini: Ferrari 458 GT2 0.030 front / 0.010 rear, Lotus Exos
-- 0.050, Dacia Sandero Cup 0.050, Abarth 500 0.100. The "typical 0.06"
-- this fell back to for every car until now sits above three of them.
local function readDamperCrossover(carIndex)
  local ok, ini = pcall(ac.INIConfig.carData, carIndex, 'suspensions.ini')
  local thr = nil
  if ok and ini then
    local front = iniNum(ini, 'FRONT', 'DAMP_FAST_BUMPTHRESHOLD')
    local rear = iniNum(ini, 'REAR', 'DAMP_FAST_BUMPTHRESHOLD')
    local heave = iniNum(ini, 'HEAVE_FRONT', 'DAMP_FAST_BUMPTHRESHOLD')
    local function valid(v) return v and v > 0.001 and v <= 0.5 end
    -- v1.9.9: typo guard. The Corvette Z06 GT3's own file says FRONT 0.50
    -- and REAR 0.050 - a tenfold disagreement between two axles of one car
    -- is a slipped decimal, not physics (every other real value seen is
    -- 0.01..0.11). When front and rear are both present and more than 3x
    -- apart, take the SMALLER; typos add a magnitude far more often than
    -- they lose one. The Ferrari's genuine 0.030/0.010 is exactly 3x and
    -- keeps its front value - the calibration anchor.
    if valid(front) and valid(rear) and math.max(front, rear) / math.min(front, rear) > 3 then
      thr = math.min(front, rear)
    elseif valid(front) then
      thr = front
    elseif valid(heave) then
      -- Cars that expose dampers through the setup screen often leave the
      -- suspension file's copy at 0, so fall back to the heave/3rd-spring
      -- section which usually carries a real number.
      thr = heave
    elseif valid(rear) then
      thr = rear
    end
  end
  if not thr or thr <= 0.001 or thr > 0.5 then return nil end
  return thr
end

--------------------------------------------------------------------------------
-- v2.2.0: CSP EXTENDED SUSPENSION - LUT anti-roll bars and LUT dampers.
--
-- Found by a separate research session (CLAUDE.md, "CSP extended
-- suspension") and sized on the driver's own saved setups: 19 cars use
-- ARB_F/ARB_R (the whole fr_*_btcc grid, the 2024 TCRs, Ferrari 296/488
-- GT3, Lexus RC F GT3...) and 11 use DAMPER_BUMP/REBOUND_* (the sv8 V2
-- trio, several GT4s). Until now the ARB and slow-damper writers only knew
-- the vanilla names, so on those cars the app's primary balance lever and
-- its damper levers simply didn't exist.
--
-- Both are INDEX sliders whose physical effect lives in a LUT, so a write
-- is only as safe as the curve behind it. Verified on real files:
--   * sv8_camaro_v2 slow_rrebound4.lut (rear rebound, click 18) has the
--     force values copied into the speed column (2686.7|2686.7 ...): at
--     real shaft speeds it gives ~0 N, so clicks 12->18 interpolate DOWN
--     from a sane curve to almost no rebound damping. "+1 = stiffer" there
--     removes damping.
--   * fr_bmw_btcc's bar LUTs start with a "detached|0" row - one click
--     softer from row 1 disconnects the bar entirely.
-- So every LUT write is checked against the car's own curve (see
-- lutDamperMoveOk / lutArbMoveOk). Damper curves that can't be read are
-- NOT written blind (a broken curve is known to exist); bar LUTs that
-- can't be read are written with the direction assumed (every bar LUT
-- seen rises with the row) but never onto their first row.
--------------------------------------------------------------------------------
local LUT_DAMPER_KINDS = {'BUMP', 'REBOUND'}
-- Shaft speeds (m/s) the direction check samples: the body-control range,
-- where the research found LUT clicks mostly act (top clicks are strongly
-- digressive below 0.025 m/s and flatten above 0.05).
local LUT_REF_SPEEDS = {0.025, 0.10}

-- All points of a car-data LUT as {x, y} (x nil for text keys), plus the
-- DataLUT11 object for interpolated reads. nil when it can't be read.
local function lutPoints(carIndex, file)
  if not file or file == '' then return nil end
  local okL, lut = pcall(function() return ac.DataLUT11.carData(carIndex, file) end)
  if not okL or not lut then return nil end
  local pts = {}
  for i = 0, 255 do
    local okO, y = pcall(function() return lut:getPointOutput(i) end)
    if not okO or type(y) ~= 'number' or y ~= y then break end
    local okI, x = pcall(function() return lut:getPointInput(i) end)
    table.insert(pts, {x = (okI and type(x) == 'number' and x == x) and x or nil, y = y})
  end
  if #pts == 0 then return nil end
  return pts, lut
end

-- A LUT anti-roll bar: nil if `section` isn't a LUT bar on this car.
-- stiff[row] is 0-based by row, matching VALUE.
local function readLutArb(carIndex, setupIni, section)
  local file = iniStr(setupIni, section, 'LUT')
  if not file then return nil end
  local info = {file = file, readable = false}
  local pts = lutPoints(carIndex, file)
  if not pts then return info end
  info.readable, info.rows, info.stiff = true, #pts, {}
  local rising = true
  for i, p in ipairs(pts) do
    info.stiff[i - 1] = p.y
    if info.firstUsableRow == nil and p.y > 0 then info.firstUsableRow = i - 1 end
    if i > 1 and p.y < pts[i - 1].y then rising = false end
  end
  info.rising = rising and pts[#pts].y > pts[1].y
  info.firstUsableRow = info.firstUsableRow or 0
  return info
end

-- LUT damper curves: axles[FRONT|REAR][BUMP|REBOUND] = {keys = {n...},
-- luts = {[n] = DataLUT11}}, where n is the setup click in the section's
-- own MIN..MAX units; setupMin[section] converts a stored VALUE (steps from
-- MIN) to that click. Clicks without their own curve are linearly
-- interpolated between neighbours, as CSP does.
local function readLutDampers(carIndex, setupIni)
  local out = {axles = {}, setupMin = {}, anyCurves = false}
  local okD, dIni = pcall(ac.INIConfig.carData, carIndex, 'dampers.ini')
  if okD and dIni then
    out.enabled = (iniNum(dIni, 'HEADER', 'ENABLE') or 0) == 1
    for _, axle in ipairs({'FRONT', 'REAR'}) do
      out.axles[axle] = {}
      for _, kind in ipairs(LUT_DAMPER_KINDS) do
        local curves = {keys = {}, luts = {}, unreadable = 0}
        for click = 0, 100 do
          local file = iniStr(dIni, axle, kind .. '_SLOW_' .. click)
          if file then
            local pts, lut = lutPoints(carIndex, file)
            if pts and lut then
              table.insert(curves.keys, click)
              curves.luts[click] = lut
              out.anyCurves = true
            else
              curves.unreadable = curves.unreadable + 1
            end
          end
        end
        out.axles[axle][kind] = curves
      end
    end
  end
  for _, kind in ipairs(LUT_DAMPER_KINDS) do
    for _, corner in ipairs({'LF', 'RF', 'LR', 'RR'}) do
      local sec = 'DAMPER_' .. kind .. '_' .. corner
      out.setupMin[sec] = iniNum(setupIni, sec, 'MIN')
    end
  end
  return out
end

-- Force (N) of a LUT damper at `click` (MIN..MAX units) and `speed` (m/s).
local function lutDamperForce(curves, click, speed)
  local keys = curves and curves.keys
  if not keys or #keys == 0 then return nil end
  local function at(k)
    local ok, v = pcall(function() return curves.luts[k]:get(speed) end)
    if ok and type(v) == 'number' and v == v then return v end
    return nil
  end
  if click <= keys[1] then return at(keys[1]) end
  if click >= keys[#keys] then return at(keys[#keys]) end
  for i = 2, #keys do
    if click <= keys[i] then
      local lo, hi = keys[i - 1], keys[i]
      local a, b = at(lo), at(hi)
      if not a or not b then return nil end
      return a + (b - a) * (click - lo) / (hi - lo)
    end
  end
  return nil
end

--------------------------------------------------------------------------------
-- Setup schema: which items THIS car exposes in its setup screen, and their
-- legal range. AC's Lua ini reader has no "list all sections" call, so - same
-- spirit as classIdeals()'s fallback matrix above - we probe a broad list of
-- section names used by the large majority of Kunos and community car mods.
-- A car simply won't resolve the ones it doesn't have, and we skip those.
--------------------------------------------------------------------------------

local SETUP_PROBE = {
  pressure = {
    {section = 'PRESSURE_LF', corner = 'LF'}, {section = 'PRESSURE_RF', corner = 'RF'},
    {section = 'PRESSURE_LR', corner = 'LR'}, {section = 'PRESSURE_RR', corner = 'RR'},
  },
  camber = {
    {section = 'CAMBER_LF', corner = 'LF'}, {section = 'CAMBER_RF', corner = 'RF'},
    {section = 'CAMBER_LR', corner = 'LR'}, {section = 'CAMBER_RR', corner = 'RR'},
  },
  toe = {
    {section = 'TOE_OUT_LF', corner = 'LF'}, {section = 'TOE_OUT_RF', corner = 'RF'},
    {section = 'TOE_OUT_LR', corner = 'LR'}, {section = 'TOE_OUT_RR', corner = 'RR'},
  },
  -- v2.2.0: ARB_F / ARB_R are CSP extended ("LUT") bars - `[ARB] EXTEND=1`,
  -- setup section with LUT=file.lut and no MIN/MAX/STEP; VALUE is a 0-based
  -- ROW index into that LUT (proven by fr_bmw_btcc, whose LUT keys are text
  -- like "1.25in 90°" and "detached", so VALUE can only be a row). A car has
  -- one or the other per end (gt4_audi_r8 mixes a LUT front with a vanilla
  -- rear); the ARB lever resolves per end, by presence.
  arb = {
    {section = 'ARB_FRONT', corner = 'F'}, {section = 'ARB_REAR', corner = 'R'},
    {section = 'ARB_F', corner = 'F'}, {section = 'ARB_R', corner = 'R'},
  },
  brakeBias = {
    {section = 'FRONT_BIAS', corner = 'F'}, {section = 'BRAKE_BIAS', corner = 'F'},
  },
  -- RWD/FWD only - see the DIFFERENTIAL module notes for why AWD is excluded.
  -- DIFF_RAMP_POWER/DIFF_RAMP_COAST added v1.3.1 - confirmed via a scan of
  -- 1561 real saved setup files (~400+ cars) that this alternate naming is
  -- genuinely common (92 real setup files use it), not a one-off - same
  -- "probe both conventions" pattern already used for ride height and
  -- brake bias below.
  diffPower = {
    {section = 'DIFF_POWER', corner = 'F'}, {section = 'DIFF_RAMP_POWER', corner = 'F'},
  },
  diffCoast = {
    {section = 'DIFF_COAST', corner = 'F'}, {section = 'DIFF_RAMP_COAST', corner = 'F'},
  },
  diffPreload = {
    {section = 'DIFF_PRELOAD', corner = 'F'},
  },
  springRate = {
    {section = 'SPRING_RATE_LF', corner = 'LF'}, {section = 'SPRING_RATE_RF', corner = 'RF'},
    {section = 'SPRING_RATE_LR', corner = 'LR'}, {section = 'SPRING_RATE_RR', corner = 'RR'},
  },
  rideHeight = {
    {section = 'ROD_LENGTH_LF', corner = 'LF'},  {section = 'ROD_LENGTH_RF', corner = 'RF'},
    {section = 'ROD_LENGTH_LR', corner = 'LR'},  {section = 'ROD_LENGTH_RR', corner = 'RR'},
    {section = 'RIDE_HEIGHT_LF', corner = 'LF'}, {section = 'RIDE_HEIGHT_RF', corner = 'RF'},
    {section = 'RIDE_HEIGHT_LR', corner = 'LR'}, {section = 'RIDE_HEIGHT_RR', corner = 'RR'},
  },
  -- v2.2.0: DAMPER_BUMP_* / DAMPER_REBOUND_* are CSP LUT dampers (DWB2 axles
  -- with [_EXTENSION] DAMPER_LUTS=1): integer clicks, SHOW_CLICKS=2, stored
  -- as steps from MIN, each click selecting / interpolating a force curve
  -- in dampers.ini. Resolved PER CORNER - gt4_bmw_m4 has a vanilla strut
  -- front (DAMP_BUMP_LF, N·s/m) and a LUT rear (DAMPER_BUMP_LR, clicks).
  damperBump = {
    {section = 'DAMP_BUMP_LF', corner = 'LF'}, {section = 'DAMP_BUMP_RF', corner = 'RF'},
    {section = 'DAMP_BUMP_LR', corner = 'LR'}, {section = 'DAMP_BUMP_RR', corner = 'RR'},
    {section = 'DAMPER_BUMP_LF', corner = 'LF'}, {section = 'DAMPER_BUMP_RF', corner = 'RF'},
    {section = 'DAMPER_BUMP_LR', corner = 'LR'}, {section = 'DAMPER_BUMP_RR', corner = 'RR'},
  },
  damperRebound = {
    {section = 'DAMP_REBOUND_LF', corner = 'LF'}, {section = 'DAMP_REBOUND_RF', corner = 'RF'},
    {section = 'DAMP_REBOUND_LR', corner = 'LR'}, {section = 'DAMP_REBOUND_RR', corner = 'RR'},
    {section = 'DAMPER_REBOUND_LF', corner = 'LF'}, {section = 'DAMPER_REBOUND_RF', corner = 'RF'},
    {section = 'DAMPER_REBOUND_LR', corner = 'LR'}, {section = 'DAMPER_REBOUND_RR', corner = 'RR'},
  },
  damperFastBump = {
    {section = 'DAMP_FAST_BUMP_LF', corner = 'LF'}, {section = 'DAMP_FAST_BUMP_RF', corner = 'RF'},
    {section = 'DAMP_FAST_BUMP_LR', corner = 'LR'}, {section = 'DAMP_FAST_BUMP_RR', corner = 'RR'},
  },
  damperFastRebound = {
    {section = 'DAMP_FAST_REBOUND_LF', corner = 'LF'}, {section = 'DAMP_FAST_REBOUND_RF', corner = 'RF'},
    {section = 'DAMP_FAST_REBOUND_LR', corner = 'LR'}, {section = 'DAMP_FAST_REBOUND_RR', corner = 'RR'},
  },
  wingFront = { {section = 'WING_1', corner = 'F'} },
  wingRear  = { {section = 'WING_2', corner = 'R'} },
  bumpStopRate = {
    {section = 'BUMP_STOP_RATE_LF', corner = 'LF'}, {section = 'BUMP_STOP_RATE_RF', corner = 'RF'},
    {section = 'BUMP_STOP_RATE_LR', corner = 'LR'}, {section = 'BUMP_STOP_RATE_RR', corner = 'RR'},
  },
  -- Total suspension travel available before the packers are reached.
  -- Increasing this is the standard first answer to running out of travel -
  -- it gives the suspension more room to work rather than making the stop
  -- it eventually hits harsher.
  packerRange = {
    {section = 'PACKER_RANGE_LF', corner = 'LF'}, {section = 'PACKER_RANGE_RF', corner = 'RF'},
    {section = 'PACKER_RANGE_LR', corner = 'LR'}, {section = 'PACKER_RANGE_RR', corner = 'RR'},
  },
}

-- Every section this app is allowed to touch, derived from SETUP_PROBE so it
-- can never drift from what the writers actually handle.
--
-- v1.8.1: this exists because v1.8.0's live-setup sync had no such limit. It
-- wrote ALL 62 sections the game reported straight into the output file -
-- including GEARING, fuel, tyre compound, traction control, engine limiter
-- and brake power, none of which this app reasons about at all. On a real
-- session that changed four INTERNAL_GEAR_n values and even ADDED an
-- INTERNAL_GEAR_1 section the driver's own setup never had. Reported
-- immediately and correctly: "gearing shouldnt be getting changed by the
-- app - only recommend shortening or lengthening final gear".
--
-- Anything outside this set is now left exactly as the base file had it -
-- the app reads it, reasons about it, advises on it, and writes nothing.
-- GEARING in particular is advice-only BY DESIGN and always has been: it has
-- never had a writer, and must not acquire one by the side door.
-- v2.1.1: unmanaged sections the output file must NOT carry from live.
-- Only fuel - see the carry block in buildSetup for the reasoning.
local CARRY_EXCLUDE = {FUEL = true}

local MANAGED_SECTIONS = {}
for _, list in pairs(SETUP_PROBE) do
  for _, probe in ipairs(list) do MANAGED_SECTIONS[probe.section] = true end
end

-- Fallback ranges used ONLY for pressure/camber when a car's setup.ini can't
-- be read in full (most commonly: the car uses Assetto Corsa's "encrypted"
-- data.acd protection - common on several licensed/payware cars - which CSP
-- can still open, but only returns a few limited fields from, so our normal
-- section-by-section probe comes back empty even though the file "loaded").
-- Pressure (psi) and camber (degrees) are real physical units that are the
-- same convention on essentially every car, unlike ARB/damper/spring click
-- counts which are genuinely per-car, so a generic wide-but-safe range is
-- a reasonable stand-in here specifically. If the guessed section name
-- doesn't actually exist on a given car, AC just ignores that block.
local GENERIC_PRESSURE_RANGE = {min = 8, max = 45, step = 0.1}
local GENERIC_CAMBER_RANGE = {min = -6, max = 2, step = 0.1}

local function genericItems(corners, range)
  local out = {}
  for _, c in ipairs(corners) do
    table.insert(out, {section = c.section, corner = c.corner, min = range.min, max = range.max, step = range.step})
  end
  return out
end

-- Critical detail confirmed against a real car's data/setup.ini (Ferrari
-- 458 GT2 reference, provided for this exact purpose): when SHOW_CLICKS is
-- 1 or 2, the number actually written into a saved setup file's VALUE= line
-- is a 0-based CLICK INDEX (how many STEPs above MIN), not the raw physical
-- value - e.g. ARB_FRONT with MIN=32072, MAX=117024, STEP=2072 saves VALUE=6
-- meaning "click 6", i.e. an actual stiffness of 32072+6*2072, NOT literally
-- 6 Nm. Only SHOW_CLICKS=0 items (pressure, camber, brake bias, diff, wing
-- in the reference file) store the raw value directly. Getting this wrong
-- means doing raw-unit arithmetic (e.g. "+1 click = +2072") on a value
-- that's actually already just a small index (6), corrupting the result.
-- This normalises min/max/step to whatever domain the VALUE field is
-- actually stored in, so every consumer of a schema item can just do
-- cur +/- N*step without needing to know which convention this item uses.
--
-- v1.9.6: this reader had NEVER returned an item on any car - MIN/MAX/STEP
-- were read with nil defaults (see iniNum), so schemaLimited=true in every
-- log ever written and BAKED_SETUP_SCHEMA was born to work around a bug in
-- this function. Now that it runs, the conversion to STORED units is
-- checked against the live spinners (ac.getSetupSpinners reports ranges in
-- the units VALUE is actually stored in) on four cars' real setup.ini:
--   SHOW_CLICKS=2 -> 0-based click index from MIN, 0..(MAX-MIN)/STEP.
--       Lotus DAMP_REBOUND_LR 7000..19000/500 -> spinner [0..24]. Ferrari
--       ARB_FRONT 19000..154000/9000 -> [0..15]. Dacia TOE 120/20 -> [0..12].
--   SHOW_CLICKS=1 -> count of STEPs from ZERO: floor(MIN/STEP)..floor(MAX/STEP).
--       Ferrari DAMP_REBOUND_LR 3780..11700/360 -> spinner [10..32].
--       Ferrari DAMP_FAST_REBOUND_LF 3500..3800/20 -> 175..190 (log value 185).
--       The old code treated 1 and 2 identically (0..numSteps) - wrong for
--       every SHOW_CLICKS=1 damper, which is why gen_baked_schema.py grew a
--       per-car 'step_multiple' override. That override is now the rule.
--   CAMBER_* (SHOW_CLICKS=0) -> MIN/MAX are DEGREES, STEP and VALUE are
--       TENTHS. Kunos' own abarth500 setup.ini says it in a comment:
--       "STEP=1 ;step is in degrees / 10". Ferrari -5..-1.2 -> spinner
--       [-50..-12]; Lotus -6..1 -> [-60..10]; Dacia -5..-0.5 -> [-50..-5];
--       BMW E30 -> [-32..-2]. Four for four. Guarded on |MIN|,|MAX| <= 15
--       so a file that already stores tenths isn't multiplied twice.
-- The spinner still out-ranks all of this at Build time (schemaWithLive);
-- this is the fallback for a session where the spinner read is rejected,
-- and it must not be a worse fallback than the baked table it replaces.
local function readSetupItem(ini, section)
  local minV = iniNum(ini, section, 'MIN')
  local maxV = iniNum(ini, section, 'MAX')
  if not minV or not maxV or minV == maxV then return nil end
  local stepV = iniNum(ini, section, 'STEP')
  if not stepV or stepV <= 0 then stepV = math.abs(maxV - minV) / 20 end
  local label = iniStr(ini, section, 'NAME') or section
  local showClicks = iniNum(ini, section, 'SHOW_CLICKS') or 0
  local realMin, realMax, realStep = math.min(minV, maxV), math.max(minV, maxV), stepV
  local indexBased = showClicks == 1 or showClicks == 2
  -- v1.9.9: where "zero" sits in STORED units, when the raw range straddles
  -- it. Toe needs this: TOE_OUT_LF -100..100 step 10 SHOW_CLICKS=2 stores a
  -- 0..20 click index where 10 is zero toe; the writer can't tell toe-out
  -- from toe-in without it. nil when the range doesn't include zero.
  local zero = nil
  local straddles = realMin <= 0 and realMax >= 0
  if showClicks == 2 then
    local numSteps = math.floor((realMax - realMin) / realStep + 0.5)
    if straddles then zero = math.floor((0 - realMin) / realStep + 0.5) end
    realMin, realMax, realStep = 0, math.max(numSteps, 1), 1
  elseif showClicks == 1 then
    realMin, realMax, realStep = math.floor(realMin / realStep), math.floor(realMax / realStep), 1
    if realMax <= realMin then realMax = realMin + 1 end
    if straddles then zero = 0 end
  elseif section:find('^CAMBER_') and math.abs(realMin) <= 15 and math.abs(realMax) <= 15 then
    realMin, realMax = realMin * 10, realMax * 10
    if straddles then zero = 0 end
  elseif straddles then
    zero = 0
  end
  return {
    section = section,
    min = realMin,
    max = realMax,
    step = realStep,
    label = label,
    indexBased = indexBased,
    zero = zero,
    -- v2.3.0: the ini's own MIN/STEP/SHOW_CLICKS, so a stored VALUE can be
    -- turned back into the physical number (N/m, N·s/m) - see physicalOf.
    raw = {min = math.min(minV, maxV), step = stepV, showClicks = showClicks},
  }
end

-- v2.3.0: stored VALUE <-> physical value, by the same conventions
-- readSetupItem uses (and the live spinners confirm): SHOW_CLICKS=2 is
-- steps from MIN, =1 is steps from zero, =0 is the value itself. nil when
-- the item carries no raw data (baked or spinner-only).
local function physicalOf(item, v)
  local r = item and item.raw
  if not r or v == nil then return nil end
  if r.showClicks == 2 then return r.min + v * r.step end
  if r.showClicks == 1 then return v * r.step end
  return v
end
local function storedOf(item, phys)
  local r = item and item.raw
  if not r or phys == nil or not r.step or r.step == 0 then return nil end
  if r.showClicks == 2 then return (phys - r.min) / r.step end
  if r.showClicks == 1 then return phys / r.step end
  return phys
end

-- Real setup.ini schema, generated offline from the car's own decrypted
-- setup.ini by gen_baked_schema.py (D:\Claude\setupcoach-tools\acd).
-- Built (v1.6.0) on the belief that live setup.ini isn't readable
-- in-game on encrypted cars - v1.9.6: it always was; readSetupItem's
-- reads were broken (see iniNum). This table is now the THIRD source,
-- behind the live spinners and the live setup.ini read, kept as a
-- fallback for a session where both are unavailable.
--
-- This matters more than "nicer advice text". Without a schema, the
-- writer falls back to nudging a PERCENTAGE of whatever number is in
-- your setup file, with NO ceiling - confirmed doing real harm on the
-- test car: DAMP_REBOUND_* legally tops out at click index 22, but the
-- writer had walked rear rebound to 24, 26, 28, 30, 34, 35 across real
-- sessions, every one of them out of range, silently clamped by AC on
-- load. So the log kept reporting "26 -> 30" as a real change while the
-- car had actually been pegged at its stiffest rear rebound the whole
-- time. With the real schema present, the existing clamp in writeTuned
-- (raw = clamp(raw, schemaItem.min, schemaItem.max)) stops it dead.
local BAKED_SETUP_SCHEMA = {
  ['ferrari_458_gt2'] = {
    ['PRESSURE_LF']={min=15,max=45,step=1,indexBased=false,label='Pressure LF'},
    -- v1.7.2: x10 vs the ini's literal MIN/MAX/STEP - see the CAMBER UNITS
    -- note above this table. The ini's own MIN=-5/MAX=-1.2 are genuine
    -- degrees for the SLIDER, but VALUE itself is stored in tenths of a
    -- degree (decidegrees), a legacy Kunos alignment-field convention the
    -- ini text doesn't reflect. Confirmed directly by the user: setting
    -- -3.5° via Content Manager's own camber slider produced a stored
    -- VALUE of -35, not -3.5.
    ['CAMBER_LF']={min=-50,max=-12,step=10,indexBased=false,label='CAMBER_LF'},
    ['TOE_OUT_LF']={min=0,max=17,step=1,indexBased=true,label='Toe LF'},
    ['SPRING_RATE_LF']={min=110,max=160,step=10,indexBased=false,label='Wheel rate LF'},
    ['ROD_LENGTH_LF']={min=0,max=50,step=1,indexBased=true,label='Height LF'},
    ['DAMP_BUMP_LF']={min=23,max=43,step=1,indexBased=true,label='Bump'},
    ['DAMP_REBOUND_LF']={min=14,max=36,step=1,indexBased=true,label='Rebound'},
    ['DAMP_FAST_BUMP_LF']={min=66,max=88,step=1,indexBased=true,label='FST Bump'},
    ['DAMP_FAST_REBOUND_LF']={min=175,max=190,step=1,indexBased=true,label='FST Rebound'},
    ['BUMP_STOP_RATE_LF']={min=100,max=160,step=5,indexBased=false,label='Packer rate'},
    ['PACKER_RANGE_LF']={min=30,max=60,step=1,indexBased=false,label='Travel range'},
    ['PRESSURE_RF']={min=15,max=45,step=1,indexBased=false,label='Pressure RF'},
    ['CAMBER_RF']={min=-50,max=-12,step=10,indexBased=false,label='CAMBER_RF'},
    ['TOE_OUT_RF']={min=0,max=17,step=1,indexBased=true,label='Toe RF'},
    ['SPRING_RATE_RF']={min=110,max=160,step=10,indexBased=false,label='Wheel rate RF'},
    ['ROD_LENGTH_RF']={min=0,max=50,step=1,indexBased=true,label='Height RF'},
    ['DAMP_BUMP_RF']={min=23,max=43,step=1,indexBased=true,label='Bump'},
    ['DAMP_REBOUND_RF']={min=14,max=36,step=1,indexBased=true,label='Rebound'},
    ['DAMP_FAST_BUMP_RF']={min=66,max=88,step=1,indexBased=true,label='FST Bump'},
    ['DAMP_FAST_REBOUND_RF']={min=175,max=190,step=1,indexBased=true,label='FST Rebound'},
    ['BUMP_STOP_RATE_RF']={min=100,max=160,step=5,indexBased=false,label='Packer rate'},
    ['PACKER_RANGE_RF']={min=30,max=60,step=1,indexBased=false,label='Travel range'},
    ['PRESSURE_LR']={min=15,max=45,step=1,indexBased=false,label='Pressure LR'},
    ['CAMBER_LR']={min=-35,max=5,step=10,indexBased=false,label='CAMBER_LR'},
    ['TOE_OUT_LR']={min=0,max=20,step=1,indexBased=true,label='Toe LR'},
    ['SPRING_RATE_LR']={min=100,max=150,step=5,indexBased=false,label='Wheel rate LR'},
    ['ROD_LENGTH_LR']={min=0,max=60,step=1,indexBased=true,label='Height LR'},
    ['DAMP_BUMP_LR']={min=11,max=31,step=1,indexBased=true,label='Bump'},
    ['DAMP_REBOUND_LR']={min=10,max=32,step=1,indexBased=true,label='Rebound'},
    ['DAMP_FAST_BUMP_LR']={min=44,max=64,step=1,indexBased=true,label='FST Bump'},
    ['DAMP_FAST_REBOUND_LR']={min=95,max=110,step=1,indexBased=true,label='FST Rebound'},
    ['BUMP_STOP_RATE_LR']={min=100,max=160,step=5,indexBased=false,label='Packer rate'},
    ['PACKER_RANGE_LR']={min=35,max=60,step=1,indexBased=false,label='Travel range'},
    ['PRESSURE_RR']={min=15,max=45,step=1,indexBased=false,label='Pressure RR'},
    ['CAMBER_RR']={min=-35,max=5,step=10,indexBased=false,label='CAMBER_RR'},
    ['TOE_OUT_RR']={min=0,max=20,step=1,indexBased=true,label='Toe RR'},
    ['SPRING_RATE_RR']={min=100,max=150,step=5,indexBased=false,label='Wheel rate RR'},
    ['ROD_LENGTH_RR']={min=0,max=60,step=1,indexBased=true,label='Height RR'},
    ['DAMP_BUMP_RR']={min=11,max=31,step=1,indexBased=true,label='Bump'},
    ['DAMP_REBOUND_RR']={min=10,max=32,step=1,indexBased=true,label='Rebound'},
    ['DAMP_FAST_BUMP_RR']={min=44,max=64,step=1,indexBased=true,label='FST Bump'},
    ['DAMP_FAST_REBOUND_RR']={min=95,max=110,step=1,indexBased=true,label='FST Rebound'},
    ['BUMP_STOP_RATE_RR']={min=100,max=160,step=5,indexBased=false,label='Packer rate'},
    ['PACKER_RANGE_RR']={min=35,max=60,step=1,indexBased=false,label='Travel range'},
    ['ARB_FRONT']={min=0,max=15,step=1,indexBased=true,label='ARB Front'},
    ['ARB_REAR']={min=0,max=9,step=1,indexBased=true,label='ARB Rear'},
    ['FRONT_BIAS']={min=52,max=80,step=1,indexBased=false,label='Brake Bias'},
    ['DIFF_POWER']={min=10,max=90,step=10,indexBased=false,label='Diff Power'},
    ['DIFF_COAST']={min=10,max=85,step=10,indexBased=false,label='Diff Coast'},
    ['WING_1']={min=0,max=4,step=1,indexBased=true,label='Front splitter'},
    ['WING_2']={min=0,max=10,step=1,indexBased=false,label='Rear wing'},
  },
}

-- Returns the schema plus a source label for the debug log: 'setup.ini',
-- 'baked', 'setup.ini+baked' (live file read worked but only partially,
-- baked filled the gaps) or 'none'. (v1.9.6: labels renamed from
-- 'live' - "live" now means the spinners, which overlay all of this at
-- Build time in schemaWithLive.)
local function readSetupSchema(carIndex, carId)
  local schema = {}
  local baked = carId and carId ~= '' and BAKED_SETUP_SCHEMA[carId] or nil
  local usedLive, usedBaked = false, false

  local ok, ini = pcall(ac.INIConfig.carData, carIndex, 'setup.ini')
  local liveOk = ok and ini

  for category, list in pairs(SETUP_PROBE) do
    local found = {}
    for _, probe in ipairs(list) do
      local item = nil
      if liveOk then
        local okItem, itemOrErr = pcall(readSetupItem, ini, probe.section)
        if okItem and itemOrErr then
          item = itemOrErr
          usedLive = true
        end
      end
      -- Baked fills in per-SECTION, not just per-car, so a car whose live
      -- read exposes some sections but not others still gets real limits
      -- everywhere they're known rather than all-or-nothing.
      if not item and baked and baked[probe.section] then
        local b = baked[probe.section]
        item = {section = probe.section, min = b.min, max = b.max, step = b.step,
                label = b.label, indexBased = b.indexBased}
        usedBaked = true
      end
      if item then
        item.section = item.section or probe.section
        item.corner = probe.corner
        table.insert(found, item)
      end
    end
    if #found > 0 then schema[category] = found end
  end

  local src = (usedLive and usedBaked and 'setup.ini+baked')
    or (usedLive and 'setup.ini') or (usedBaked and 'baked') or 'none'
  return schema, src
end

--------------------------------------------------------------------------------
-- Setup file helpers: locating the setups folder, reading an existing setup
-- as a numeric baseline, and writing a modified copy back out. Plain io.open
-- is already relied on elsewhere in this app (pit notes export), including
-- writing into a brand-new subfolder that doesn't exist yet, so the same
-- approach is used here for the setups/<car>/<track> tree.
--------------------------------------------------------------------------------

local function findDocsRoot()
  local root
  pcall(function()
    if ac.FolderID and ac.FolderID.ACDocuments then
      root = ac.getFolder(ac.FolderID.ACDocuments)
    end
  end)
  if not root or root == '' then
    pcall(function() root = ac.getFolder(ac.FolderID.Documents) .. '/Assetto Corsa' end)
  end
  return root
end

local function getTrackFolder()
  local ok, id = pcall(ac.getTrackID)
  if ok and id and id ~= '' then return id end
  return 'generic'
end

local function setupsDir(carFolder, trackFolder)
  local root = findDocsRoot()
  if not root or root == '' then return nil end
  return string.format('%s/setups/%s/%s', root, carFolder, trackFolder or 'generic')
end

-- Keeps every original line so anything we don't recognise round-trips
-- untouched, and indexes which line holds each section's VALUE= so it can
-- be patched precisely.
local function readIniFile(path)
  local f = io.open(path, 'r')
  if not f then return nil end
  local lines, valueLineIdx, curSection = {}, {}, nil
  for line in f:lines() do
    table.insert(lines, line)
    local sec = line:match('^%s*%[(.-)%]%s*$')
    if sec then
      curSection = sec
    elseif curSection then
      local key = line:match('^%s*([%a_]+)%s*=')
      if key and string.upper(key) == 'VALUE' then
        valueLineIdx[curSection] = #lines
      end
    end
  end
  f:close()
  return {lines = lines, valueLineIdx = valueLineIdx}
end

local function getCurVal(parsed, section)
  local idx = parsed.valueLineIdx[section]
  if not idx then return nil end
  return tonumber(parsed.lines[idx]:match('=%s*(-?[%d%.]+)'))
end

-- Finds an existing setup file to use as a TEMPLATE - a plain, unencrypted
-- .ini with real current values for every section this car supports. This
-- is what makes the whole thing work without needing the car's (often
-- encrypted) data/setup.ini schema: we don't need to know an item's legal
-- MIN/MAX/STEP if we already know a real, valid, in-range value for it.
--
-- Priority order, and why:
--   1) last.ini - AC rewrites this every session with whatever setup the
--      driver actually ran, so it's the truest picture of "what the car is
--      set to right now". Checked in the track folder first, then generic
--      (AC's usual home for it).
--   2) our own previous output - lets successive Build presses refine
--      rather than restart, and guarantees a template exists from run 2
--      onward even if last.ini somehow isn't there.
--   3) a name the user set in Settings - kept purely for back-compat; it's
--      no longer required for anything and the UI no longer asks for it.
-- Returns parsed, path, label - all nil if nothing at all was found.
local function findTemplateSetup(carFolder, trackFolder, userName)
  local trackDir = setupsDir(carFolder, trackFolder)
  local genericDir = setupsDir(carFolder, 'generic')
  local candidates = {}
  local function add(dir, name, label)
    if dir then table.insert(candidates, {path = dir .. '/' .. name, label = label}) end
  end
  add(trackDir, 'last.ini', 'last.ini (this track)')
  add(genericDir, 'last.ini', 'last.ini (generic)')
  add(trackDir, 'SetupCoach_Optimized.ini', 'previous Setup Coach output')
  add(genericDir, 'SetupCoach_Optimized.ini', 'previous Setup Coach output (generic)')
  if userName and userName ~= '' then
    add(trackDir, userName .. '.ini', userName .. '.ini')
    add(genericDir, userName .. '.ini', userName .. '.ini (generic)')
  end
  for _, c in ipairs(candidates) do
    local parsed = readIniFile(c.path)
    -- Require at least a couple of real VALUE= sections, so a stray empty
    -- or malformed file doesn't get picked as a "template" and then have
    -- every lookup silently miss.
    if parsed then
      local count = 0
      for _ in pairs(parsed.valueLineIdx) do count = count + 1 end
      if count >= 5 then return parsed, c.path, c.label end
    end
  end
  return nil, nil, nil
end

local function ensureSectionValue(parsed, section, valueText)
  local text = 'VALUE=' .. valueText
  local idx = parsed.valueLineIdx[section]
  if idx then
    parsed.lines[idx] = text
  else
    table.insert(parsed.lines, '[' .. section .. ']')
    table.insert(parsed.lines, text)
    parsed.valueLineIdx[section] = #parsed.lines
  end
end

local function snapToStep(value, minV, maxV, step)
  if not step or step <= 0 then return clamp(value, minV, maxV) end
  local steps = math.floor((value - minV) / step + 0.5)
  return clamp(minV + steps * step, minV, maxV)
end

local function fmtSetupValue(v, step)
  if step and step >= 0.999 and math.abs(step - math.floor(step)) < 0.001 then
    return string.format('%.0f', v)
  end
  return string.format('%.3f', v)
end

-- Applies one clamped, step-snapped nudge to a schema item already present
-- in `parsed` (i.e. it exists in the base setup file), logging a human
-- readable before/after line. No-ops quietly if the section isn't in the
-- base file or the nudge doesn't move it off the current grid point.
local function writeClick(parsed, changes, it, delta, desc)
  local cur = getCurVal(parsed, it.section)
  if not cur then return end
  local newV = snapToStep(cur + delta, it.min, it.max, it.step)
  if math.abs(newV - cur) < 1e-9 then return end
  ensureSectionValue(parsed, it.section, fmtSetupValue(newV, it.step))
  table.insert(changes, string.format('%s: %s → %s', desc, fmtSetupValue(cur, it.step), fmtSetupValue(newV, it.step)))
end

-- Used when this car's setup.ini couldn't be read (so no real MIN/MAX/STEP
-- is known for `section`) but a base setup file DOES have a real current
-- value for it. Nudges by a PERCENTAGE of that value's own magnitude rather
-- than an assumed absolute unit, with a floor of 1 raw unit so a small
-- integer (a click index, which is common - see the SHOW_CLICKS note above)
-- still moves by at least one real step. This stays sensible whether the
-- stored number turns out to be a raw physical quantity, a click index, or
-- some other per-car scale, since it never assumes which.
local function writeClickPercent(parsed, changes, section, sign, fracPerStep, stepCount, desc)
  local cur = getCurVal(parsed, section)
  if not cur then return end
  local mag = math.max(math.abs(cur) * fracPerStep * stepCount, 1)
  local raw = cur + sign * mag
  local looksInteger = math.abs(cur - math.floor(cur + 0.5)) < 0.01
  local newV = looksInteger and math.floor(raw + 0.5) or (math.floor(raw * 100 + 0.5) / 100)
  if newV == cur then return end
  local fmt = looksInteger and '%.0f' or '%.2f'
  ensureSectionValue(parsed, section, string.format(fmt, newV))
  table.insert(changes, string.format('%s: %s → %s', desc, string.format(fmt, cur), string.format(fmt, newV)))
end

-- Small helper: turn a schema category's item list into a section->item map
-- for quick lookup while iterating the fixed SETUP_PROBE candidate list.
local function schemaBySection(schemaList)
  local map = {}
  if schemaList then
    for _, it in ipairs(schemaList) do map[it.section] = it end
  end
  return map
end

-- THE LIVE SETUP, v1.8.0. Everything below this comment exists because for
-- most of this project's life it was assumed the car's ACTUAL current setup
-- couldn't be read at runtime - hence the whole template-file mechanism
-- (findTemplateSetup, nudging from last.ini). CSP exposes it directly:
--
--   ac.getSetupSpinners() -> { {name, label, min, max, step, value,
--                               displayMultiplier, readOnly, units,
--                               showClicksMode}, ... }
--
-- `name` matches setup INI section names (PRESSURE_LF, CAMBER_LF, ...) and
-- `value` is what's on the car RIGHT NOW. That single call addresses five
-- separate long-standing problems at once:
--
--   1) ACCUMULATION. last.ini is only written on session exit, so Build
--      always re-nudged from a stale base - eight consecutive Builds in one
--      real session produced byte-identical output (ARB 30->34, ride height
--      24->23, toe 12->13 every single time) because the base never moved.
--   2) "UNTICKED = LEAVE IT ALONE" actually meaning it. A skipped module
--      now carries the value that's really on the car, not whatever a stale
--      file happened to hold - which is what made unticking pressures write
--      20psi (that car's literal MAXIMUM) instead of the ~16 it was running.
--   3) schemaLimited cars. min/max/step come back for EVERY car, so the
--      unclamped percentage-nudge path (which walked one car's rear rebound
--      to 78 against a real limit of 22) stops being reachable.
--   4) The camber units mess - displayMultiplier is the authoritative
--      raw->degrees factor, replacing per-car guessing about whether a
--      stored -29 means -29 or -2.9 degrees.
--   5) No decryption needed for any of it.
--
-- NOT yet verified against a running game (these are SDK definitions, and
-- this project has been bitten this week by assuming a read matches the
-- documented shape). So: everything is pcall-guarded, every field is
-- type-checked, and the whole thing is REJECTED unless the data is
-- self-consistent - see the guard below. Callers keep their old template
-- path as fallback, and the debug log records exactly what came back.
-- v1.9.3: the rear axle's handling signal, defined ONCE and shared by the
-- REAR DAMPERS advice item and the slow-damper writer, so the panel can
-- never promise one direction while Build does another (the exact
-- panel-vs-writer mismatch that caused the v1.4-era "only pressure and
-- camber got written" reports). Returns 'loose' when oversteer clearly
-- dominates, 'tight' when understeer clearly does, nil when neither - plus
-- the raw counts, since the writer sizes its step from them.
--
-- "Clearly" = above the event threshold AND at least 25% more than the
-- opposing signal. A mixed-balance car (push at some corners, snap at
-- others, roughly equal) gets nil and falls back to the damper histogram,
-- the same "act only on a clear signal" stance the ARB writer takes.
-- mid+high are summed because rear damper effects span both regimes: AC's
-- tooltip names "initial turn in" and "brake release" (any speed) as well
-- as "slow turns that need the whole car to rotate".
-- v1.9.8: ONE balance verdict for every push-vs-snap decision in the app
-- (ARB, rake, wings, rear dampers, and the advice lines that promise what
-- Build will do), built around the driver's rule: SLIGHT OVERSTEER IN A
-- RACE CAR IS NOT A FAULT. A car that rotates a little is faster and nicer
-- to drive than one that pushes; the app must not tune that out.
--
--   'tight'  push clearly dominant  (push > th, push > 1.25 x snap)
--   'loose'  snap clearly dominant  (snap > th, snap > 1.25 x push)
--            AND frequent enough to be a real problem - more than
--            SLIGHT_OVERSTEER_PER_100 snap events per 100 corners. Below
--            that rate it's the rotation a race car should have, whatever
--            the ratio says (a car with 3 push and 15 snap events in 100
--            corners is not loose, it's set up well).
--   nil      neither - with a note: 'slight' (oversteer present, under the
--            bar), 'mixed' (both present, neither dominant), or nothing.
--
-- Understeer gets no rate floor on purpose: it is slow and unpleasant at
-- any rate, and the driver's point was specifically about oversteer.
-- useRateFloor is off for the HIGH-speed pair (wings, high-speed rake):
-- high-speed corners are a fraction of all corners so a per-100-corners
-- rate would understate them, and a high-speed loose car is a genuine
-- problem at a lower rate than a low-speed one.
--
-- The corner count is floored at 20 so the first few corners of a session
-- can't produce a wild rate - early on this errs to 'slight' (leave it),
-- which is the safe direction.
local SLIGHT_OVERSTEER_PER_100 = 25
-- BALANCE MODES BEGIN (tests extract this block)
-- BALANCE MODE (Settings / main window): what balance Build aims for.
--   tight  = push > tightRatio x snap      (more rotation wanted)
--   loose  = snap > looseRatio x push AND, on the rate-floored regimes,
--            more than `slight` snaps per 100 corners
-- Normal keeps the driver's rule (slight oversteer is fine). Oversteer
-- calls the car tight as soon as push comes near the snaps and tolerates
-- far more rotation; Understeer does the opposite. tightRatio x looseRatio
-- stays above 1 in every mode so a car can never be both. biasMargin is the
-- brake-bias stability margin (% forward of the equal-limit split): more
-- forward = more stable entry.
local BALANCE_MODES = {
  normal     = {label = 'Normal',     tightRatio = 1.15, looseRatio = 1.15, slight = SLIGHT_OVERSTEER_PER_100, biasMargin = 1.0},
  oversteer  = {label = 'Oversteer',  tightRatio = 0.85, looseRatio = 1.60, slight = 40, biasMargin = 0.0},
  understeer = {label = 'Understeer', tightRatio = 1.60, looseRatio = 0.85, slight = 8,  biasMargin = 2.0},
}
local BALANCE_MODE_ORDER = {'normal', 'oversteer', 'understeer'}
local function balanceMode()
  return BALANCE_MODES[settings.balanceMode] or BALANCE_MODES.normal
end
-- BALANCE MODES END
-- v1.9.9: minimum evidence before a COUNT-RATIO rule (front damper
-- histogram, differential) may write. `th` (2) is fine as "did anything
-- happen"; it is far too low for "is A clearly more than B". Shared by
-- both so the same handful of events can't move two subsystems.
local HISTOGRAM_MIN_EVENTS = 6
local function balanceVerdict(self, push, snap, th, useRateFloor)
  local mode = balanceMode()
  local corners = math.max(self.corneringSamples or 0, 20)
  local snapPer100 = snap / corners * 100
  local slightRate = useRateFloor and snapPer100 <= mode.slight
  if push > th and push > snap * mode.tightRatio + 1e-9 then return 'tight', push, snap, nil, snapPer100 end
  if snap > th and snap > push * mode.looseRatio + 1e-9 then
    if slightRate then return nil, push, snap, 'slight', snapPer100 end
    return 'loose', push, snap, nil, snapPer100
  end
  if snap > th or push > th then return nil, push, snap, 'mixed', snapPer100 end
  return nil, push, snap, nil, snapPer100
end

-- v2.5.0: the EVIDENCE UNIT is a lap on ordinary tracks and a section of a
-- lap on long ones (see LONG TRACKS in the evidence block). One word for
-- every message that names it; the engine sets it when the track is known.
local EV_UNIT = {one = 'lap', many = 'laps'}
local function unitWord(count) return count == 1 and EV_UNIT.one or EV_UNIT.many end
-- ' (20.8 km track: 4 sections a lap)' on long tracks, '' otherwise.
local function longTrackNote(self)
  if (self.unitsPerLap or 1) <= 1 then return '' end
  return string.format(' (%.1f km track: %d sections a lap)', (self.trackLengthM or 0) / 1000, self.unitsPerLap)
end

-- Wording shared by the advice panel and the Build log for a nil verdict,
-- so the two can never describe the same numbers differently.
local function balanceLeftAloneNote(note, push, snap, regime, agree, considered)
  if note == 'slight' then
    return string.format('slight %s oversteer bias (%d oversteer / %d push) - inside the %s balance target, left alone', regime, snap, push, balanceMode().label)
  elseif note == 'mixed' then
    return string.format('mixed %s balance (%d push / %d oversteer), neither clearly dominant - left alone', regime, push, snap)
  elseif type(note) == 'string' and note:sub(1, 12) == 'inconsistent' then
    -- The counts ride inside the note ('inconsistent 1/4') so every
    -- existing call site gets them without threading two more values.
    local a, c = note:match('(%d+)/(%d+)')
    return string.format('%s totals (%d push / %d oversteer) point one way but only %s of %s %s agree - not a consistent trait of the car, left alone',
      regime, push, snap, a or tostring(agree or 0), c or tostring(considered or 0), EV_UNIT.many)
  end
  return nil
end

--------------------------------------------------------------------------------
-- v2.0.0: EVIDENCE WINDOW AND LAP CONSISTENCY.
--
-- The app's aim - agreed with the driver in plain terms - is an optimal
-- setup for THE LAP AS A WHOLE, from full-lap telemetry, not a reaction to
-- a couple of corners. Until this version the machinery only half did
-- that: every counter accumulated for the whole session (good), but Build
-- would act on THREE events (th=2), never consumed what it had acted on,
-- and had no idea what a lap was. A real Corvette GT3 log shows four
-- Builds inside two Nordschleife laps - corner samples 80, 88, 202, 97 -
-- each re-applying 2 clicks to the same evidence. Three things fix that:
--
--   1) LAP BINS. At every lap boundary the counters since the previous
--      boundary are banked as one bin (with pit-lane / partial / invalid
--      flags). The totals still accumulate as before for every existing
--      consumer; the bins are the per-lap view of the same numbers.
--   2) THE WINDOW. A successful Build CONSUMES its evidence: counters,
--      corner samples, camber/grip sums and pressure peaks go to zero, the
--      bins banked before it are fenced off. The next Build sees only
--      what was driven after the last one - on the setup it wrote. What
--      is NOT consumed: the static camber / ride-height captures (sit in
--      the pits once per session still applies), the tyre reference,
--      the schema, fuel, and the bin history (kept for the log).
--   3) THE GATE. Build writes nothing until the window holds at least
--      settings.buildMinLaps CLEAN complete laps (not pit laps, not the
--      partial lap the app loaded into) and BUILD_MIN_CORNERS corner
--      samples. Below that it says exactly what it has and what it needs.
--   4) LAP CONSISTENCY. A balance verdict from the totals only acts if at
--      least half the window's clean laps, judged individually, agree
--      with it. A signal that came from one lap in five is a mistake or a
--      moment, not a setup trait. Scalar signals (lockups, bottoming,
--      turn-in push, rear instability, the two diff signals) get the same
--      test: present (>= 2 events) in at least half the laps.
--   5) LONG TRACKS (v2.5.0). The Nordschleife is 20.8 km: two clean laps
--      there is 42 km and the best part of half an hour, so in the logs
--      the gate was overridden on every Build there, no clean lap was ever
--      banked, and nothing that needs per-lap statistics ever ran (noise,
--      measured jumps, group verdicts, the spring target). A lap longer
--      than LONG_TRACK_M is split into sections of about SECTION_M
--      (Nordschleife: 4 of 5.2 km, by spline position) and each section is
--      one UNIT of evidence - banked, flagged (pit / partial / invalid),
--      gated, consistency-checked and noise-measured exactly like a lap.
--      Ordinary tracks are unchanged: one unit = one lap.
--      Also v2.5.0: the unit that was in progress when a Build consumed the
--      window is PARTIAL - only its post-Build part is in the window, and
--      it was driven on the old setup.
--
-- All of it is on the debug log: `evidence:`, `laps:`, `consistency:`,
-- `lastBuildLoaded:`. A declined Build writes its own entry.
--------------------------------------------------------------------------------
local BUILD_MIN_CORNERS = 20
local HELD_SLIDE_S = 1.0   -- v2.5.0: throttle held this long through a slide = deliberate
local LONG_TRACK_M = 7500
local SECTION_M = 5000
local function unitsPerLapFor(trackLengthM)
  local L = tonumber(trackLengthM) or 0
  if L <= LONG_TRACK_M then return 1 end
  return math.max(2, math.floor(L / SECTION_M + 0.5))
end
local WINDOW_KEYS = {
  'midPush', 'midSnap', 'highPush', 'highSnap', 'turninPush', 'rearToeEvents',
  'lockF', 'lockR', 'spinR', 'liftOffSnap', 'bottoming', 'kerbs', 'springsHitsF', 'springsHitsR',
  'dampBumpF', 'dampRebF', 'dampBumpR', 'dampRebR',
  'fastDampBumpF', 'fastDampRebF', 'fastDampBumpR', 'fastDampRebR',
  'diffEvents', 'diffRotationEvents', 'corneringSamples',
  'heldSlides',  -- v2.5.0: deliberate slides (see HELD SLIDES), logged, never a verdict
  'floorHitsF', 'floorHitsR',  -- v2.6.0: the floor at 1 mm or less (FLOOR CLEARANCE), logged
  -- damper histogram: seconds of wheel velocity per side and band (DAMPER HISTOGRAM)
  'dhSlowBumpF', 'dhSlowRebF', 'dhFastBumpF', 'dhFastRebF',
  'dhSlowBumpR', 'dhSlowRebR', 'dhFastBumpR', 'dhFastRebR',
}

-- DAMPER HISTOGRAM. Seconds of wheel (damper) velocity per axle, split by
-- side (bump +, rebound -) and by band at the car's own slow/fast crossover
-- (DAMP_FAST_*THRESHOLD: the slow settings act below it, the fast ones
-- above). Time-weighted, so it doesn't depend on frame rate, and both sides
-- are measured the same way. Below DAMPER_HIST_MIN_V is friction and noise;
-- above DAMPER_HIST_MAX_V is a glitch (a frame across a pit exit or reset).
-- Velocity is the frame-to-frame change of suspensionTravel, which reads
-- short peaks low - fine for time shares, which is all this feeds.
local DAMPER_HIST_KEYS = {'dhSlowBumpF', 'dhSlowRebF', 'dhFastBumpF', 'dhFastRebF',
  'dhSlowBumpR', 'dhSlowRebR', 'dhFastBumpR', 'dhFastRebR'}
local DAMPER_HIST_MIN_V = 0.005
local DAMPER_HIST_MAX_V = 3.0
local DAMPER_KNEE_DEFAULT = 0.05
local function damperKnee(self)
  local k = tonumber(self.damperCrossover)
  if not k or k < 0.02 or k > 0.15 then return DAMPER_KNEE_DEFAULT end
  return k
end
local function dampHistAdd(self, axle, vel, dt)
  if not dt or dt <= 0 or dt > 0.1 then return end
  local a = math.abs(vel)
  if a < DAMPER_HIST_MIN_V or a > DAMPER_HIST_MAX_V then return end
  local band = (a < damperKnee(self)) and 'Slow' or 'Fast'
  local key = 'dh' .. band .. ((vel > 0) and 'Bump' or 'Reb') .. axle
  self[key] = (self[key] or 0) + dt
end

local function counterSnapshot(self)
  local s = {}
  for _, k in ipairs(WINDOW_KEYS) do s[k] = self[k] or 0 end
  return s
end

-- Complete, clean laps in the current window: not a pit lap, not the
-- partial lap the app loaded into, and (logged but not excluded) valid.
local function windowBins(self)
  local out = {}
  for i = (self.windowBinsStart or 0) + 1, #(self.lapBins or {}) do
    local b = self.lapBins[i]
    if not b.pit and not b.partial then table.insert(out, b) end
  end
  return out
end

local function windowLapStats(self)
  local clean, pit, partial, invalid = 0, 0, 0, 0
  for i = (self.windowBinsStart or 0) + 1, #(self.lapBins or {}) do
    local b = self.lapBins[i]
    if b.pit then pit = pit + 1
    elseif b.partial then partial = partial + 1
    else clean = clean + 1 end
    if b.valid == false then invalid = invalid + 1 end
  end
  return clean, pit, partial, invalid
end

local function regimeCounts(src, regime)
  local mp, ms, hp, hs = src.midPush or 0, src.midSnap or 0, src.highPush or 0, src.highSnap or 0
  if regime == 'low' then return mp, ms end
  if regime == 'high' then return hp, hs end
  return mp + hp, ms + hs
end

-- The verdict every push-vs-snap consumer now calls: balanceVerdict on the
-- window totals, then the lap-consistency test on the window's clean laps.
-- Returns (verdict, push, snap, note, snapRate, agree, considered).
local function regimeVerdict(self, regime, th)
  local push, snap = regimeCounts(self, regime)
  local useRate = regime ~= 'high'
  local verdict, _, _, note, rate = balanceVerdict(self, push, snap, th, useRate)
  local bins = windowBins(self)
  local agree, considered = 0, #bins
  if considered >= 2 then
    local target = verdict
    for _, b in ipairs(bins) do
      local bp, bs = regimeCounts(b, regime)
      local bv = balanceVerdict({corneringSamples = b.corneringSamples or 0}, bp, bs, th, useRate)
      if target and bv == target then agree = agree + 1 end
    end
    if verdict and agree * 2 < considered then
      verdict, note = nil, string.format('inconsistent %d/%d', agree, considered)
    end
  end
  return verdict, push, snap, note, rate, agree, considered
end

-- Scalar signal support across the window's clean laps: how many laps had
-- at least two of these events. Returns (agree, considered, ok) where ok is
-- true when the check passes or can't be run (fewer than 2 laps).
local function lapSupport(self, key)
  local bins = windowBins(self)
  local considered = #bins
  if considered < 2 then return 0, considered, true end
  local agree = 0
  for _, b in ipairs(bins) do if (b[key] or 0) >= 2 then agree = agree + 1 end end
  return agree, considered, agree * 2 >= considered
end

local function lapSupportNote(label, agree, considered)
  return string.format('%s seen in only %d of %d %s - not a consistent trait, left alone', label, agree, considered, EV_UNIT.many)
end

-- v2.5.2: max-travel hits on an axle, above the threshold AND in at least
-- half the window's clean laps - the test the spring writer has applied
-- since v2.0.0. The slow-damper "stiffer, bottoming needs support" move
-- read the raw count instead (> th = 3 hits in the whole window), so a
-- Build could say "Rear springs: max-travel hits seen in only 3 of 7 laps
-- - not a consistent trait, left alone" and stiffen all four rear damper
-- settings for the same hits (Huracan GT3 Evo2, Imola, 2 Oct). key =
-- 'springsHitsF' | 'springsHitsR'.
local function travelHitsConsistent(self, key, count, th)
  if (count or 0) <= th then return false end
  local _, _, ok = lapSupport(self, key)
  return ok
end

-- v2.6.0: the BOTTOMING signal of one end, for the travel chains
-- (LEVER_CHAINS 'travelF-bottoming' / 'travelR-bottoming'): verdict
-- 'bottoming' when that end's max-travel hits pass travelHitsConsistent;
-- the window's hits; the rate the chain is judged by (hits per 100
-- corners, like the balance rates); and the lap agreement for the log.
-- endKey = 'F' | 'R'.
local function travelSignal(self, endKey, th)
  local key = 'springsHits' .. endKey
  local hits = self[key] or 0
  local agree, considered = lapSupport(self, key)
  local verdict = travelHitsConsistent(self, key, hits, th) and 'bottoming' or nil
  local rate = hits / math.max(self.corneringSamples or 0, 20) * 100
  return verdict, hits, rate, agree, considered
end

--------------------------------------------------------------------------------
-- v2.6.0: FLOOR CLEARANCE. Nik: "App shouldn't just lower a car to aero
-- peak - it should lower until the car is at minimum available without the
-- body of the car striking the floor." car.rideHeight[0/1] is the height
-- of the floor at the car's own ride-height pickup points (car.ini [RIDE]
-- PICKUP_FRONT/REAR_HEIGHT - 0.30 m under the CG on the Huracan GT3, 0.37 m
-- on the Sunbeam), in metres, front / rear. Each clean lap keeps a 1 mm
-- histogram per end (only on track, above FLOOR_MIN_SPEED_KMH), and the
-- lap's clearance is the height it stayed above for all but its lowest
-- 0.5 % of samples - a kerb strike or one bump is not the car's ride
-- height; a low point held for 2 % of the lap is. A lap whose MEDIAN sits
-- under FLOOR_PLAUSIBLE_MM is a car that reports 0 - no data.
--------------------------------------------------------------------------------
local FLOOR_TARGET_MM = 10          -- the lowest end's median lap keeps this off the floor
local FLOOR_LOWER_TRAVEL_MAX = 0.90 -- lowered only while both ends use less of their travel
-- v2.6.0: the spring target lives here too - the panel (buildAdvice) names
-- it, and a top-level local is only visible below its declaration.
local SPRING_TARGET_USE = 0.95      -- median peak travel use to aim for (v2.6.0: was 0.92)
local SPRING_MAX_STEP = 0.10        -- max +10% rate in one Build (v2.6.0: was 30% - "be cautious")
local FLOOR_MIN_SPEED_KMH = 30
local FLOOR_HIST_MAX_MM = 300
local FLOOR_LOW_SHARE = 0.005       -- the lowest 0.5 % of a lap's samples are ignored
local FLOOR_MIN_SAMPLES = 200       -- per end and lap, else no clearance for that lap
local FLOOR_PLAUSIBLE_MM = 10

local function floorHistAdd(hist, metres)
  local mm = math.floor((metres or 0) * 1000 + 0.5)
  if mm < 0 then mm = 0 elseif mm > FLOOR_HIST_MAX_MM then mm = FLOOR_HIST_MAX_MM end
  hist[mm] = (hist[mm] or 0) + 1
  hist.n = (hist.n or 0) + 1
end

-- The lap's clearance in mm, or nil (too few samples, or implausible).
local function floorHistClearance(hist)
  local total = hist and hist.n or 0
  if total < FLOOR_MIN_SAMPLES then return nil end
  local skip = math.floor(total * FLOOR_LOW_SHARE)
  local seen, low, median = 0, nil, nil
  for mm = 0, FLOOR_HIST_MAX_MM do
    local c = hist[mm]
    if c then
      seen = seen + c
      if not low and seen > skip then low = mm end
      if seen * 2 >= total then median = mm; break end
    end
  end
  if not median or median < FLOOR_PLAUSIBLE_MM then return nil end
  return low
end

--------------------------------------------------------------------------------
-- v2.6.2: THE COLLIDER IS THE BOTTOM OF THE CAR. Nik: "add something that
-- tells if the car is hitting the floor. it should look at the collider and
-- treat that as the bottom of the car." car.rideHeight is measured at two
-- pickup points (car.ini [RIDE]), which are not where the body touches the
-- track: the Abarth's collider floor sits 20 mm BELOW its pickups (it
-- scrapes while ride height still reads 20 mm), the Sunbeam's 40 mm above.
-- The ground colliders (colliders.ini: CENTRE / SIZE in metres from the CG -
-- Kunos' own comment in the Camaro's file - GROUND_ENABLE, [HEADER]
-- COLLIDERS) are the boxes the physics scrapes along the track, so their
-- bottom faces are the car's real floor. Each frame on track the four bottom
-- corners and the bottom centre of every ground box go into the world with
-- the car's physics transform (car.transform, origin the CG) and a ray is
-- cast straight down onto the track (physics.raycastTrack): the lowest point
-- per end (front = ahead of the CG) feeds the floor histograms and the
-- floor-hit counts in place of the pickups.
-- CHECKED LIVE, NOT ASSUMED: the same pipeline also casts from the two
-- ride-height pickups (car.ini height, axle line from suspensions.ini) and
-- compares with the car's own car.rideHeight. Within CHECK_TOL over
-- CHECK_MIN frames the collider is used ('verified'); outside it the
-- transform reading is wrong for this car and the pickups stay in use
-- ('mismatch', both numbers logged). A car with no pickups, or one that
-- reports no ride height, can't be checked: the collider is used,
-- 'unverified'. The transform's axes are checked against car.look/up first.
--------------------------------------------------------------------------------
local COLLIDER = {
  RAY_UP = 0.5,        -- each ray starts this far above its point (m)
  RAY_LEN = 1.5,       -- ...and looks this far down
  MAX_BOXES = 12,
  CHECK_MIN = 300,     -- paired frames per end before the live check decides
  CHECK_TOL = 0.025,   -- m: pickup clearance (this pipeline) vs car.rideHeight
  HIT_M = 0.001,       -- a floor point within 1 mm of the track = the floor hitting it
  DOWN = nil,          -- vec3(0, -1, 0), made on first use
}

-- The car's ground colliders as bottom-face sample points in CG space
-- ({x, y, z, front}), and what the files say ({src, boxes, actual, lowF,
-- lowR, pickupF, pickupR, pickZF, pickZR}).
local function readGroundColliders(carIndex)
  local boxes, info = {}, {src = nil, boxes = 0}
  local okI, ini = pcall(function() return ac.INIConfig.carData(carIndex, 'colliders.ini') end)
  if okI and ini then
    -- Three ways to read "x, y, z": the whole string when it comes back
    -- whole, a vec3 default (sentinel = missing), CSP's per-item offset.
    local function triple(sec, key)
      local raw = iniStr(ini, sec, key)
      if not raw then return nil end
      local t = {}
      for s in raw:gmatch('[-+]?%d*%.?%d+') do t[#t + 1] = tonumber(s) end
      if t[1] and t[2] and t[3] then return t end
      local okV, v = pcall(function() return ini:get(sec, key, vec3(math.huge, math.huge, math.huge)) end)
      if okV and type(v) ~= 'number' and v and type(v.x) == 'number' and v.x < math.huge and v.y < math.huge and v.z < math.huge then
        return {v.x, v.y, v.z}
      end
      t = {}
      for i = 1, 3 do
        local okN, x = pcall(function() return ini:get(sec, key, 0, i) end)
        t[i] = okN and tonumber(x) or nil
      end
      if t[1] and t[2] and t[3] then return t end
      return nil
    end
    local limit = math.min(iniNum(ini, 'HEADER', 'COLLIDERS') or COLLIDER.MAX_BOXES, COLLIDER.MAX_BOXES)
    for i = 0, limit - 1 do
      local sec = 'COLLIDER_' .. i
      local c, s = triple(sec, 'CENTRE'), triple(sec, 'SIZE')
      if c and s and iniNum(ini, sec, 'GROUND_ENABLE') ~= 0 then
        table.insert(boxes, {c[1], c[2], c[3], math.abs(s[1]), math.abs(s[2]), math.abs(s[3])})
      end
    end
    if #boxes > 0 then info.src = 'colliders.ini' end
  end
  local okC, list = pcall(function() return ac.getCarColliders(carIndex, true) end)
  if okC and type(list) == 'table' then
    info.actual = #list
    if #boxes == 0 then
      for _, b in ipairs(list) do
        local okB, cx, cy, cz, sx, sy, sz = pcall(function() return b.position.x, b.position.y, b.position.z, b.size.x, b.size.y, b.size.z end)
        if okB and type(cx) == 'number' and type(cy) == 'number' and type(cz) == 'number' and type(sy) == 'number' then
          table.insert(boxes, {cx, cy, cz, math.abs(sx or 0), math.abs(sy), math.abs(sz or 0)})
        end
      end
      if #boxes > 0 then info.src = 'ac.getCarColliders' end
    end
  end
  local pts = {}
  for _, b in ipairs(boxes) do
    local cx, cy, cz, sx, sy, sz = b[1], b[2], b[3], b[4], b[5], b[6]
    local y = cy - sy / 2
    for _, p in ipairs({{cx - sx / 2, cz - sz / 2}, {cx + sx / 2, cz - sz / 2},
                        {cx - sx / 2, cz + sz / 2}, {cx + sx / 2, cz + sz / 2}, {cx, cz}}) do
      local front = p[2] >= 0
      table.insert(pts, {x = p[1], y = y, z = p[2], front = front})
      if front then info.lowF = math.min(info.lowF or y, y) else info.lowR = math.min(info.lowR or y, y) end
    end
  end
  info.boxes = #boxes
  local okR, carIni = pcall(function() return ac.INIConfig.carData(carIndex, 'car.ini') end)
  if okR and carIni then
    info.pickupF, info.pickupR = iniNum(carIni, 'RIDE', 'PICKUP_FRONT_HEIGHT'), iniNum(carIni, 'RIDE', 'PICKUP_REAR_HEIGHT')
  end
  -- The pickups' fore/aft position: the axle lines, from the wheelbase and
  -- the weight split (the CG is the origin). Only the live check uses it.
  local okS, susp = pcall(function() return ac.INIConfig.carData(carIndex, 'suspensions.ini') end)
  local wb, cgl = okS and susp and iniNum(susp, 'BASIC', 'WHEELBASE'), okS and susp and iniNum(susp, 'BASIC', 'CG_LOCATION')
  if wb and cgl and wb > 0 and cgl > 0 and cgl < 1 then
    info.pickZF, info.pickZR = wb * (1 - cgl), -wb * cgl
  end
  return pts, info
end

-- Clearance (m, negative = into the track) of one CG-space point.
local function rayClearance(tr, x, y, z)
  local w = tr:transformPoint(vec3(x, y, z))
  local d = physics.raycastTrack(vec3(w.x, w.y + COLLIDER.RAY_UP, w.z), COLLIDER.DOWN, COLLIDER.RAY_LEN)
  if type(d) == 'number' and d >= 0 then return d - COLLIDER.RAY_UP end
  return nil
end

-- Lowest floor point per end, and the two pickup clearances for the check.
local function colliderMeasure(car, pts, info)
  COLLIDER.DOWN = COLLIDER.DOWN or vec3(0, -1, 0)
  local tr = car.transform
  local minF, minR
  for i = 1, #pts do
    local p = pts[i]
    local c = rayClearance(tr, p.x, p.y, p.z)
    if c then
      if p.front then
        if not minF or c < minF then minF = c end
      else
        if not minR or c < minR then minR = c end
      end
    end
  end
  local pkF = info.pickupF and rayClearance(tr, 0, info.pickupF, info.pickZF or 0) or nil
  local pkR = info.pickupR and rayClearance(tr, 0, info.pickupR, info.pickZR or 0) or nil
  return minF, minR, pkF, pkR
end

-- 'verified' | 'unverified' (collider used) | 'pending' | 'mismatch' | 'none'
-- (ride-height points used), and why.
local function colliderVerdict(self)
  local info = self.colliderInfo
  if not info or (info.boxes or 0) == 0 then return 'none', 'no ground colliders in this car\'s files' end
  if self.colliderFail then return 'none', self.colliderFail end
  if not (info.pickupF or info.pickupR) then return 'unverified', 'no ride-height pickups in car.ini to check it against' end
  local cf, cr = self.colChkF or {n = 0, sum = 0}, self.colChkR or {n = 0, sum = 0}
  if cf.n + cr.n == 0 and (self.colRhMissN or 0) >= COLLIDER.CHECK_MIN then
    return 'unverified', 'the car reports no ride height to check it against'
  end
  local function mean(chk) return chk.n > 0 and chk.sum / chk.n or nil end
  local function state(chk, known)
    if not known then return 'ok' end
    if chk.n < COLLIDER.CHECK_MIN then return 'pending' end
    return math.abs(chk.sum / chk.n) <= COLLIDER.CHECK_TOL and 'ok' or 'bad'
  end
  local sf, sr = state(cf, info.pickupF), state(cr, info.pickupR)
  local nums = string.format('pickups measured through the collider pipeline vs the car\'s own ride height: F %s / R %s mm over %d / %d frames',
    mean(cf) and string.format('%+.0f', mean(cf) * 1000) or 'n/a', mean(cr) and string.format('%+.0f', mean(cr) * 1000) or 'n/a', cf.n, cr.n)
  if sf == 'bad' or sr == 'bad' then
    return 'mismatch', string.format('%s - more than %.0f mm out, so this car\'s transform is not read right', nums, COLLIDER.CHECK_TOL * 1000)
  end
  if sf == 'ok' and sr == 'ok' then return 'verified', nums end
  return 'pending', nums
end

-- One frame: the floor height per end to bank (m), from the collider when
-- it is usable, else from the pickups (car.rideHeight); runs the live check.
local function floorSample(self, car)
  local okRH, rh = pcall(function() return car.rideHeight end)
  local rhF, rhR
  if okRH and rh and type(rh[0]) == 'number' and type(rh[1]) == 'number' then rhF, rhR = rh[0], rh[1] end
  if self.colliderCar ~= self.carId then
    self.colliderCar = self.carId
    local okL, pts, info = pcall(readGroundColliders, car.index)
    self.colliderPts = okL and pts or {}
    self.colliderInfo = okL and info or {boxes = 0}
    self.colliderFail = (not okL) and ('reading the colliders failed: ' .. tostring(pts)) or nil
    self.colliderAxesOk = false
    self.colChkF, self.colChkR, self.colRhMissN = {n = 0, sum = 0}, {n = 0, sum = 0}, 0
  end
  local cF, cR, pkF, pkR
  if #self.colliderPts > 0 and not self.colliderFail then
    if not self.colliderAxesOk then
      local okA, zd, yd = pcall(function()
        local t = car.transform
        return t:transformVector(vec3(0, 0, 1)):dot(car.look), t:transformVector(vec3(0, 1, 0)):dot(car.up)
      end)
      if okA and type(zd) == 'number' and type(yd) == 'number' and zd > 0.9 and yd > 0.9 then
        self.colliderAxesOk = true
      else
        self.colliderFail = okA and string.format('the physics transform\'s axes do not match the car (z.look %.2f, y.up %.2f)', tonumber(zd) or 0, tonumber(yd) or 0)
          or ('the physics transform is not readable here: ' .. tostring(zd))
      end
    end
    if self.colliderAxesOk then
      local okM, a, b, c, d = pcall(colliderMeasure, car, self.colliderPts, self.colliderInfo)
      if okM then cF, cR, pkF, pkR = a, b, c, d else self.colliderFail = 'the floor rays failed: ' .. tostring(a) end
    end
  end
  local rhOkF, rhOkR = rhF and rhF > 0.003, rhR and rhR > 0.003
  if pkF and rhOkF then self.colChkF.n, self.colChkF.sum = self.colChkF.n + 1, self.colChkF.sum + (pkF - rhF) end
  if pkR and rhOkR then self.colChkR.n, self.colChkR.sum = self.colChkR.n + 1, self.colChkR.sum + (pkR - rhR) end
  if (pkF or pkR) and not (rhOkF or rhOkR) then self.colRhMissN = (self.colRhMissN or 0) + 1 end
  local verdict = colliderVerdict(self)
  if verdict == 'verified' or verdict == 'unverified' then
    self.floorSrc = 'collider'
    -- An end no collider point reaches keeps its pickup.
    return cF or rhF, cR or rhR
  end
  self.floorSrc = 'ride height'
  return rhF, rhR
end

-- The debug-log line.
local function colliderLogLine(self)
  local info = self.colliderInfo or {boxes = 0}
  local verdict, why = colliderVerdict(self)
  local function m(v) return v and string.format('%.3f', v) or 'n/a' end
  local function mm(v) return v and string.format('%.0f', v * 1000) or 'n/a' end
  return string.format('collider floor (v2.6.2): %s - %s · source %s, %d ground box%s (CSP reports %s) · lowest face F %s / R %s m vs ride-height pickups F %s / R %s m (from the CG) · floor data used: %s · this window: closest F %s / R %s mm, floor hits F %d / R %d',
    string.upper(verdict), why, info.src or 'none', info.boxes or 0, (info.boxes == 1) and '' or 'es', info.actual and tostring(info.actual) or 'n/a',
    m(info.lowF), m(info.lowR), m(info.pickupF), m(info.pickupR), self.floorSrc or 'none yet',
    mm(self.floorMinF), mm(self.floorMinR), self.floorHitsF or 0, self.floorHitsR or 0)
end

-- Rear axle handling signal: mid+high summed because rear damper effects
-- span both regimes (AC's tooltip names "initial turn in" and "brake
-- release" as well as "slow turns"). Returns (verdict, snapN, pushN, note,
-- agree, considered).
local function rearHandlingSignal(self, th)
  local verdict, push, snap, note, _, agree, considered = regimeVerdict(self, 'rear', th)
  return verdict, snap, push, note, agree, considered
end

local function readLiveSetupSpinners()
  local ok, spinners = pcall(ac.getSetupSpinners)
  if not ok then return nil, 'ac.getSetupSpinners errored' end
  if type(spinners) ~= 'table' then return nil, 'no table returned' end

  local map, count, inconsistent, firstBad = {}, 0, 0, nil
  for _, s in ipairs(spinners) do
    if type(s) == 'table' and type(s.name) == 'string' and tonumber(s.value) then
      local it = {
        section = s.name,
        value = tonumber(s.value),
        min = tonumber(s.min),
        max = tonumber(s.max),
        step = tonumber(s.step),
        displayMultiplier = tonumber(s.displayMultiplier),
        readOnly = s.readOnly and true or false,
        units = type(s.units) == 'string' and s.units or nil,
        -- v1.9.4: the control's factory default, per the SDK's spinner
        -- shape. Used as a floor for "speculative" softening - see the fast
        -- damper writer. nil when the API doesn't supply one.
        defaultValue = tonumber(s.defaultValue),
      }
      -- CONSISTENCY GUARD, the whole safety of this feature. min/max/value
      -- are only usable together if they're in the SAME unit space - and
      -- that's exactly the kind of assumption that has gone wrong here
      -- before (setup.ini declares camber MIN/MAX in degrees while VALUE is
      -- stored in tenths). A live value sitting outside its own reported
      -- range proves they aren't comparable, so rather than clamp against
      -- numbers that don't mean what we think, the entire read is thrown
      -- away and the old template path takes over.
      if it.min and it.max and it.max > it.min then
        if it.value < it.min - 1e-6 or it.value > it.max + 1e-6 then
          inconsistent = inconsistent + 1
          firstBad = firstBad or string.format('%s value=%s outside %s..%s',
            it.section, tostring(it.value), tostring(it.min), tostring(it.max))
        end
      end
      map[it.section] = it
      count = count + 1
    end
  end

  if count == 0 then return nil, 'returned 0 usable sections' end
  if inconsistent > 0 then
    return nil, string.format('REJECTED - %d/%d sections self-inconsistent (%s)',
      inconsistent, count, tostring(firstBad))
  end
  return map, string.format('%d sections', count)
end

-- v2.5.1: GEAR SPINNER NAMES ARE ONE BELOW THE SAVED FILE'S. CSP's
-- ac.getSetupSpinners() calls the gear spinners INTERNAL_GEAR_1..N -
-- forward gear n, as in the car's setup.ini [GEAR_n] - while AC's own saved
-- setups call the same items INTERNAL_GEAR_2..N+1 (AC's gear index: 0 is
-- reverse, 1 neutral). None of the 1500+ saved setups on this PC has an
-- INTERNAL_GEAR_1; v1.8.0's "invented" one came from CSP. Carried by name
-- (v2.1.1), every gear's value landed in the gear below: the Huracan GT3 at
-- Silverstone, 2026-09-29, got 6th's 0.8857 as its 5th (physics had
-- 1.0312), 1st/3rd/4th shifted too, and 1st's own value was dropped.
-- The offset is read from the two name sets, never assumed - the template
-- is AC's own file: live + 1 == template -> renamed; live == template ->
-- CSP already matches (a future fix), left as is; anything else -> the gear
-- spinners are dropped, so nothing is carried and the template's gears
-- stand. The note goes on the liveSetup log line, after the read summary.
local function alignLiveGearNames(live, parsed, note)
  if not live or not parsed or not parsed.valueLineIdx then return live, note end
  local liveGears, fileGears, liveCount, fileCount = {}, {}, 0, 0
  for section in pairs(live) do
    local n = tonumber(section:match('^INTERNAL_GEAR_(%d+)$'))
    if n then liveGears[n] = true; liveCount = liveCount + 1 end
  end
  for section in pairs(parsed.valueLineIdx) do
    local n = tonumber(section:match('^INTERNAL_GEAR_(%d+)$'))
    if n then fileGears[n] = true; fileCount = fileCount + 1 end
  end
  if liveCount == 0 or fileCount == 0 then return live, note end
  local function linesUp(offset)
    if liveCount ~= fileCount then return false end
    for n in pairs(liveGears) do
      if not fileGears[n + offset] then return false end
    end
    return true
  end
  local offset = nil
  if linesUp(1) then offset = 1 elseif linesUp(0) then offset = 0 end
  if offset == 0 then return live, tostring(note) .. ' · gear spinners named as the file saves them' end
  local out = {}
  for section, it in pairs(live) do
    local n = tonumber(section:match('^INTERNAL_GEAR_(%d+)$'))
    if not n then
      out[section] = it
    elseif offset then
      local renamed = {}
      for k, v in pairs(it) do renamed[k] = v end
      renamed.section = 'INTERNAL_GEAR_' .. (n + offset)
      out[renamed.section] = renamed
    end
  end
  if not offset then
    return out, string.format('%s · gear spinners (%d) do not line up with the template gear sections (%d) - gears NOT carried, the template keeps its own',
      tostring(note), liveCount, fileCount)
  end
  local lo, hi = math.huge, 0
  for n in pairs(liveGears) do lo = math.min(lo, n); hi = math.max(hi, n) end
  local values = {}
  for n = lo, hi do
    local it = live['INTERNAL_GEAR_' .. n]
    table.insert(values, it and string.format('%g', it.value) or '-')
  end
  return out, string.format('%s · gears renamed: CSP INTERNAL_GEAR_%d..%d = the file INTERNAL_GEAR_%d..%d, values %s',
    tostring(note), lo, hi, lo + offset, hi + offset, table.concat(values, ','))
end

--------------------------------------------------------------------------------
-- Engine
--------------------------------------------------------------------------------

local engine = {}

-- v2.6.2: a method, not a direct call from the Build - the Build function
-- already carries 68 upvalues and this keeps it from gaining another.
function engine:colliderLogLine() return colliderLogLine(self) end

function engine:reset()
  self.samples = 0
  self.corneringSamples = 0
  self.cd = {
    bottoming = 0, kerb = 0, turnin = 0, midPush = 0, midSnap = 0,
    highPush = 0, highSnap = 0, lockup = 0, spin = 0, coast = 0, diff = 0, diffLock = 0, rearToe = 0,
    fastBumpF = 0, fastRebF = 0, fastBumpR = 0, fastRebR = 0, springsF = 0, springsR = 0,
    floorF = 0, floorR = 0, contact = 0,  -- v2.6.0: FLOOR CLEARANCE
  }
  self.turninPush = 0
  self.midPush = 0
  self.midSnap = 0
  self.highPush = 0
  self.highSnap = 0
  self.bottoming = 0
  self.kerbs = 0
  self.lockF = 0
  self.lockR = 0
  self.spinR = 0
  self.liftOffSnap = 0
  -- v2.5.0: HELD SLIDES - deliberate slides (throttle kept on for over a
  -- second, or started with the handbrake), counted apart from snaps.
  self.heldSlides = 0
  self.slideEp = nil           -- the oversteer episode in progress, if any
  self.lastHandbrakeAt = -1e9  -- clock of the last handbrake pull
  self.clock = 0
  self.diffEvents = 0
  self.diffRotationEvents = 0
  self.sectorEvents = {}
  self.sectorsAvailable = false
  self.rearToeEvents = 0
  self.fCamSum = 0
  self.rCamSum = 0
  -- v2.3.0: calculated-target accumulators (see consumeWindow).
  self.fCamSqSum, self.rCamSqSum = 0, 0
  self.brkLoadFSum, self.brkLoadN, self.brkZones, self.brkInZone = 0, 0, 0, false
  self.brkCapFSum, self.brkCapRSum, self.brkCapN = 0, 0, 0  -- v2.5.0: grip-limited braking force
  self.hsRhFSum, self.hsRhFN = 0, 0
  self.lapTravelUseF, self.lapTravelUseR = 0, 0
  -- v2.6.0: FLOOR CLEARANCE - per-lap histograms, floor contacts, the
  -- splitter/diffuser ground height in fast corners, track contacts.
  self.lapFloorHistF, self.lapFloorHistR = {}, {}
  self.floorHitsF, self.floorHitsR = 0, 0
  self.floorMinF, self.floorMinR = nil, nil  -- v2.6.2: closest the floor came this window
  self.colliderCar = nil                     -- v2.6.2: colliders and the live check re-read
  self.ghFrontSum, self.ghFrontN, self.ghDiffSum, self.ghDiffN = 0, 0, 0, 0
  self.trackContacts, self.trackContactMinY, self.trackContactSumAbsX, self.trackContactPosN = 0, nil, 0, 0
  self.finalAtVmax = nil
  self.fInOutSum = 0
  self.rInOutSum = 0
  self.fMidEdgeSum = 0
  self.rMidEdgeSum = 0
  self.inCorner = false
  self.cornerDirty = false
  self.cornerPeakLat = 0
  self.cornerPeakFCam = 0
  self.cornerPeakRCam = 0
  self.cornerPeakFInOut = 0
  self.cornerPeakRInOut = 0
  self.cornerPeakFMidEdge = 0
  self.cornerPeakRMidEdge = 0
  self.topSpeed = 0
  self.rpmAtVmax = 0
  self.gearAtVmax = 0
  self.limiterTime = 0
  -- Top gear only, from ac.getCarPhysics().gearRatios - see refreshTargets.
  self.topGearNum = nil
  self.topGearRatio = nil
  self.secondTopGearRatio = nil
  self.gearPhysDiag = 'not read yet'
  -- v1.7.3: highest gear actually USED this session - a fallback "which
  -- gear is top gear" signal that works even when the physics-API read
  -- above fails outright (see gearPhysDiag), used only to detect gearing
  -- that's too TALL (see the new GEARING branch in buildAdvice).
  self.maxGearSeen = 0
  self.peakDecel = 0
  self.peakAccel = 0
  self.peakLat = 0
  self.latLow = 0
  self.latLowN = 0
  self.latHigh = 0
  self.latHighN = 0
  self.rollSum = 0
  self.pitchSum = 0
  self.attitudeN = 0
  self.loadFSum = 0
  self.loadRSum = 0
  self.loadN = 0
  self.travelFMax = 0
  self.travelRMax = 0
  self.travelUsePeakF, self.travelUsePeakR = 0, 0  -- v2.5.0: peak share of the car's own range
  self.staticTravelF, self.staticTravelR = nil, nil  -- v2.5.0: at rest in the pits (m)
  self.dampBumpF = 0
  self.dampRebF = 0
  self.dampBumpR = 0
  self.dampRebR = 0
  self.fastDampBumpF = 0
  self.fastDampRebF = 0
  self.fastDampBumpR = 0
  self.fastDampRebR = 0
  self.springsHitsF = 0
  self.springsHitsR = 0
  self.lastTravel = {0, 0, 0, 0}
  for _, k in ipairs(DAMPER_HIST_KEYS) do self[k] = 0 end
  self.lapStartFuel = nil
  self.lastLapCount = -1
  self.fuelPerLap = 0
  self.completedLaps = 0
  -- v2.0.0: evidence window + lap bins (see the block comment above
  -- BUILD_MIN_CORNERS). A full reset starts a fresh window at 'reset'.
  self.lapBins = {}
  self.lapBoundary = nil          -- counter snapshot at the last lap boundary
  self.lapPitSeen = false         -- pit lane entered during the current lap
  self.firstLapPartial = nil      -- app loaded mid-lap? decided on first frame
  -- v2.5.0: evidence units (LONG TRACKS). unitsPerLap = 1 on ordinary
  -- tracks, where every unit is a lap and nothing below changes.
  self.unitsPerLap = nil          -- decided from sim.trackLengthM on the first frame
  self.curUnit = 0                -- section of the lap the car is in
  self.unitPartial = false        -- current unit started mid-way (or skipped track)
  self.unitInvalid = false        -- lap-valid flag dropped during the current unit
  self.windowBinsStart = 0
  self.windowLabel = 'session start'
  self.windowStartedAt = nil
  self.buildsThisSession = 0
  self.lastBuildWritten = nil     -- {section = value} the last Build wrote
  self.lastBuildAt = nil
  self.livePressFL = 0
  self.livePressFR = 0
  self.livePressRL = 0
  self.livePressRR = 0
  self.minWearRemain = 100
  self.maxDirt = 0
  self.avgCore = 0
  self.avgOpt = 80
  self.absHits = 0
  self.tcHits = 0
  self.absHitsF = 0
  self.absHitsR = 0
  self.exportMsg = 'Drive clean laps to build a live profile.'
  self.lastAdvice = {}
  -- v2.5.0: lastTravelF/R are the car's own travel range per axle (the
  -- shorter corner of the two), travelRef the same per corner; both set by
  -- refreshTravelRef from PACKER_RANGE. 0.12 m only until a car is read.
  self.lastTravelF = TRAVEL_FALLBACK_M
  self.lastTravelR = TRAVEL_FALLBACK_M
  self.travelRef = {LF = TRAVEL_FALLBACK_M, RF = TRAVEL_FALLBACK_M, LR = TRAVEL_FALLBACK_M, RR = TRAVEL_FALLBACK_M}
  self.travelRefSrc = 'not read yet'
  -- v2.5.2: RESET TELEMETRY resets the telemetry, not the car. This
  -- function also clears what refreshTargets read from the car's files
  -- (travel range above, the gear-ratio reads), but refreshTargets skips
  -- re-reading while the car and compound are unchanged - so after a reset
  -- the travel range stayed at the made-up 0.12 m until a pit stop: 16 of
  -- the 57 Builds of 29 Sep - 4 Oct logged "F 120 / R 120 mm (not read
  -- yet)", springs sized and bottoming judged against it. Stale -> the next
  -- frame re-reads the car.
  self.carDataStale = true
  -- 3.0.0: static camber reading (captured while stationary in the pits)
  -- and the state of the last "Build Optimal Setup" run.
  self.staticCFL = 0
  self.staticCFR = 0
  self.staticCRL = 0
  self.staticCRR = 0
  self.staticCamberCaptured = false
  self.setupMsg = 'Drive a few laps, then press Build.'
  self.setupChanges = {}
  self.setupOutPath = nil
  self.gripMsg = ''
  -- 4.0.0: cold (garage) tyre pressure, captured once per reset the first
  -- time the car is stationary in the pits AND the tyre core temperature
  -- looks genuinely cold (not just "currently stationary", which could mean
  -- freshly back in the pits with still-hot tyres) - and the peak HOT
  -- pressure actually reached on track this session. Together these give a
  -- real, measured cold->hot rise for THIS session/track/setup, used to
  -- work out what cold-fill pressure will reach the desired hot target.
  self.coldPressFL = nil
  self.coldPressFR = nil
  self.coldPressRL = nil
  self.coldPressRR = nil
  self.coldPressCaptured = false
  self.peakPressFL = 0
  self.peakPressFR = 0
  self.peakPressRL = 0
  self.peakPressRR = 0
  -- 4.0.0: peak-corner grip utilisation (dy = realised lateral friction
  -- coefficient relative to the tyre's own peak, from CSP's per-wheel
  -- .dy field) - tracked alongside the existing peak-corner camber sample.
  self.dyPeakFSum = 0
  self.dyPeakRSum = 0
  self.dyPeakN = 0
  self.cornerPeakDyF = 0
  self.cornerPeakDyR = 0
  -- Static front ride height (captured while stationary in the pits, see
  -- the stoppedInPit block) and live peak-corner aero CL (from
  -- ac.getCarPhysics().wings, banked at the same instant as camber/.dy
  -- above) - both new this version, see checkAeroLutRisk's comment.
  self.staticRideHeightF = 0
  self.staticRideHeightR = 0
  self.rideHeightCaptured = false
  self.cornerPeakClF = 0
  self.cornerPeakClR = 0
  self.cornerHasAeroCl = false
  self.aeroClFSum = 0
  self.aeroClRSum = 0
  self.aeroClN = 0
end

engine:reset()
engine.targetF = 26
engine.targetR = 26
engine.targetSrc = 'class matrix'
engine.coldTargetF = nil
engine.coldTargetR = nil
engine.dy0F = nil
engine.dy0R = nil
engine.dyRefUsed = false
engine.peakCamberSrc = 'none'
engine.carId = ''
engine.compound = ''
engine.schema = nil
engine.schemaCarId = ''
engine.schemaSource = 'none'
engine.aeroPeaks = {}
engine.aeroDynamic = {}
engine.aeroWingIndex = {}
engine.topGearNum = nil
engine.topGearRatio = nil
engine.secondTopGearRatio = nil
engine.gearPhysDiag = 'not read yet'
engine.maxGearSeen = 0
engine.gearAtVmax = 0
-- v1.7.5: plain engine field, NOT settings/ac.storage - this is pure UI
-- show/hide state (expand/collapse the module-toggle checkboxes in
-- windowMain) with no real need to survive an app restart. Moved off
-- ac.storage specifically because it was a brand-new key with no prior
-- on-disk value, and the reported symptom (tick it, the revealed content
-- flashes and immediately collapses again) matches a storage round-trip
-- not completing before the very next frame re-reads the old value - a
-- plain in-memory field can't have that problem at all, whatever the
-- exact mechanism was.
engine.showModuleToggles = false
-- v2.1.0: one-shot lap-gate override (test button in windowMain).
engine.gateOverrideOnce = false

local function wheelWearRemain(w)
  local wear = n(w.tyreWear, 0)
  if wear > 1.5 then wear = wear / 100 end
  wear = clamp(wear, 0, 1)
  local remain = (1 - wear) * 100
  if remain < 1 and wear < 0.05 then remain = 100 end
  return remain
end

-- Named-corner analysis, 4.8.0. Turns "Low-speed push (53)" into "31 at
-- Bruxelles, 14 at La Source" by tagging every corner-triggered counter
-- with WHERE it happened, not just how often. Built entirely on
-- ac.getTrackSectorName(splinePosition) - confirmed working via a real,
-- shipped app (Track Walker) that does exactly this in one line - rather
-- than parsing sections.ini ourselves, which CSP already does internally.
--
-- Every part of this degrades gracefully: if a track has no sector data
-- (common on plain/mod tracks without a proper sections.ini), the read
-- returns nothing useful, sectorsAvailable stays false, and every module's
-- advice text falls back to its existing lap-aggregate count exactly as
-- before - this is purely additive, never a dependency.
local function currentSectorName(car)
  local ok, name = pcall(ac.getTrackSectorName, car.splinePosition)
  if ok and type(name) == 'string' and name ~= '' then return name end
  return nil
end

local function recordSectorEvent(self, sector, eventType)
  if not sector then return end
  self.sectorEvents[sector] = self.sectorEvents[sector] or {}
  self.sectorEvents[sector][eventType] = (self.sectorEvents[sector][eventType] or 0) + 1
  self.sectorsAvailable = true
end

-- v2.5.0: take one event back (a snap that turned out to be a held slide).
local function unrecordSectorEvent(self, sector, eventType)
  local s = sector and self.sectorEvents[sector]
  if s and (s[eventType] or 0) > 0 then s[eventType] = s[eventType] - 1 end
end

-- Formats the top few sectors for one event type as "31 at X, 14 at Y".
-- Returns '' (not nil) when there's nothing to show, so callers can always
-- safely concatenate the result without a separate nil check.
local function topSectorsFor(self, eventType, limit)
  local rows = {}
  for sector, counts in pairs(self.sectorEvents) do
    local c = counts[eventType]
    if c and c > 0 then table.insert(rows, {sector = sector, count = c}) end
  end
  if #rows == 0 then return '' end
  table.sort(rows, function(a, b) return a.count > b.count end)
  local parts = {}
  for i = 1, math.min(limit or 2, #rows) do
    table.insert(parts, string.format('%d at %s', rows[i].count, rows[i].sector))
  end
  return table.concat(parts, ', ')
end

-- Upgraded to prefer surfaceValidTrack (a direct boolean per wheel) now
-- that it's confirmed to exist, straight from CSP's own shipped Lua type
-- definitions - a real, purpose-built field for exactly this question,
-- rather than the surfaceGrip<0.55 proxy this app had been using since
-- before that confirmation was available. Kept the old proxy as a
-- fallback for the rare case the field comes back nil (e.g. a genuinely
-- old CSP build) so this never regresses to no filtering at all.
local function isOnTrack(car)
  if car.isInPit or car.isInPitlane then return false end
  local out = n(car.wheelsOutside, 0)
  if out >= 3 then return false end
  local off = 0
  for i = 0, 3 do
    local w = car.wheels[i]
    if w then
      local valid = w.surfaceValidTrack
      if valid == nil then
        -- Fallback proxy, only reached if the field itself is unavailable.
        if n(w.surfaceGrip, 1) < 0.55 then off = off + 1 end
      elseif not valid then
        off = off + 1
      end
    end
  end
  return off < 3
end

---@param car ac.StateCar
function engine:refreshTargets(car)
  local carId = ''
  pcall(function() carId = ac.getCarID(car.index) or '' end)
  if carId == '' then pcall(function() carId = car:id() or '' end) end
  local compound = ''
  pcall(function() compound = car:tyresName() or '' end)
  -- v1.9.7: the fitted set's 0-based index, so readTyreReference can pick
  -- the matching [FRONT_n]/[REAR_n] section. A compound change already
  -- forces a re-read (the guard below keys on the name); the index rides
  -- along with it.
  local compoundIndex = -1
  pcall(function() compoundIndex = tonumber(car.compoundIndex) or -1 end)
  if not self.carDataStale and carId == self.carId and compound == self.compound and self.targetF > 0 then return end
  self.carDataStale = false  -- v2.5.2: re-read after RESET TELEMETRY (see engine:reset)
  self.carId = carId
  self.compound = compound
  local ref = readTyreReference(car.index, carId, compound, compoundIndex)
  self.targetF, self.targetR, self.targetSrc = ref.hotF, ref.hotR, ref.src
  self.coldTargetF, self.coldTargetR = ref.coldF, ref.coldR
  self.dy0F, self.dy0R = ref.dy0F, ref.dy0R
  self.tyreRadiusF, self.tyreRadiusR = ref.radiusF, ref.radiusR  -- v2.3.0
  self.brakeModelF, self.brakeModelR = ref.brakeModelF, ref.brakeModelR  -- v2.5.0
  self.dyRefUsed = ref.dyRefUsed or false
  -- Peak-grip inclination angle for this exact tyre, in degrees (positive
  -- magnitude). This is what the outer tyre WANTS to be sitting at when the
  -- corner is loaded up - the whole basis of the camber calculation below.
  self.peakCamberF = peakCamberAngle(ref.dcamber0F, ref.dcamber1F)
  self.peakCamberR = peakCamberAngle(ref.dcamber0R, ref.dcamber1R)
  -- v1.9.9: DCAMBER_LUT, when the tyre has one, is the curve the physics
  -- actually uses; the parabola coefficients may or may not agree with it
  -- (the Corvette Z06 GT3's cmbr.lut peaks at -4.0 deg and its
  -- coefficients say 4.00 - consistent on that car, not guaranteed on
  -- any other). Sampled at 0.25 deg over -10..0 with ac.DataLUT11, the
  -- same API the aero check has proven in app context. The LUT's x-axis
  -- is camber in degrees, negative = negative camber; the peak is the
  -- argmax, kept only if it lands where a real peak can (0.2..9 deg).
  local lutUsed = false
  local function lutPeak(lutFile)
    if not lutFile or lutFile == '' then return nil end
    local okLut, lut = pcall(function() return ac.DataLUT11.carData(car.index, lutFile) end)
    if not okLut or not lut then return nil end
    local bestX, bestV, samples = nil, -math.huge, 0
    for i = 0, 40 do
      local x = -10 + i * 0.25
      local okV, v = pcall(function() return lut:get(x) end)
      if okV and type(v) == 'number' then
        samples = samples + 1
        if v > bestV then bestV, bestX = v, x end
      end
    end
    if samples < 20 or not bestX then return nil end
    local deg = math.abs(bestX)
    if deg < 0.2 or deg > 9 then return nil end
    return deg
  end
  local lutF, lutR = lutPeak(ref.dcamberLutF), lutPeak(ref.dcamberLutR)
  if lutF then self.peakCamberF = lutF; lutUsed = true end
  if lutR then self.peakCamberR = lutR; lutUsed = true end
  -- v1.9.5: which route supplied the peak angle, for the debug log. Until
  -- this version the live read never succeeded on any car (see iniNum),
  -- so every peakCamber ever logged came from DCAMBER_LOOKUP.
  local liveAny = (self.peakCamberF or self.peakCamberR) ~= nil
  local lookupAny = false
  -- Fallback to the bundled lookup when live tyres.ini didn't expose usable
  -- DCAMBER coefficients.
  if (not self.peakCamberF or not self.peakCamberR) and carId ~= '' and DCAMBER_LOOKUP[carId] then
    local L = DCAMBER_LOOKUP[carId]
    if not self.peakCamberF then
      self.peakCamberF = peakCamberAngle(L[1], L[2])
      lookupAny = lookupAny or self.peakCamberF ~= nil
    end
    if not self.peakCamberR then
      self.peakCamberR = peakCamberAngle(L[3], L[4])
      lookupAny = lookupAny or self.peakCamberR ~= nil
    end
  end
  if liveAny and lookupAny then self.peakCamberSrc = 'live+lookup'
  elseif liveAny then self.peakCamberSrc = lutUsed and 'live-lut' or 'live'
  elseif lookupAny then self.peakCamberSrc = 'lookup'
  else self.peakCamberSrc = 'none' end
  self:refreshTravelRef(car.index)  -- v2.5.0: PACKER_RANGE, live packers override
  -- v2.5.0: PHYSICS FINGERPRINT - has this car's physics changed since the
  -- app last saw it? If so, what was learned about the old version is reset.
  pcall(function() self:checkPhysicsFingerprint(car.index) end)
  -- Damper event thresholds, scaled off the car's own slow/fast crossover.
  -- The multipliers were set so "a typical 0.06 m/s car" reproduces the
  -- original hard-coded 0.54 / 1.20 m/s - the calibration every damper
  -- rule in this app was tuned against on track. v1.9.6: the crossover
  -- read works for the first time, and the car that calibration came from
  -- (the Ferrari 458 GT2) actually says 0.030, not 0.06. So the anchor is
  -- moved to the real number: 0.030 x 18 = 0.54, 0.030 x 40 = 1.20. That
  -- keeps the validated car's behaviour byte-identical and scales the
  -- others off their own files (Lotus/Dacia 0.05 -> 0.90 / 2.00, Abarth
  -- 0.10 -> the clamps). Leaving 9x/20x would have HALVED the Ferrari's
  -- thresholds the moment the read started working - a re-tune of the
  -- most-tested car, disguised as a bug fix. A car whose file is unreadable
  -- still gets 0.030, i.e. the old 0.54 / 1.20.
  --
  -- v2.2.0: SCALING RETIRED - fixed 0.54 / 1.20 m/s for every car. The
  -- thresholds above are compared against WHEEL-TRAVEL velocity (the rate
  -- of change of suspensionTravel), and 0.54 / 1.20 m/s sit 5-50x above
  -- every crossover ever read (0.010-0.113 vanilla, 0.30-0.40 on CSP LUT
  -- axles). The crossover says where a damper's force curve changes
  -- slope; it says nothing about how fast this car's wheels move over a
  -- kerb, so scaling by it had no physical basis - and it never ran at
  -- all until v1.9.6 (nil-default bug), so the calibration every car was
  -- validated on, through v1.9.5, is exactly the fixed 0.54 / 1.20.
  -- The first week of the scaling live was an A/B on the same car: the
  -- Dacia at 0.54/1.20 logged front rebound events 12/12/8/3/16 per
  -- session; the same car the same evening at the scaled 0.90/2.00 logged
  -- 0 and 0 (the second over 248 corners); the Huracan, pinned at the
  -- 1.00/2.20 clamps by its 0.060 crossover, logged 0-1 across 1,100+
  -- corners - which is why every Huracan window read "only 3 bump / 0
  -- rebound events - not enough to judge". The scaling deleted the
  -- signal on any car with a crossover above 0.056. The crossover is still
  -- read and logged (it flags CSP LUT axles) but moves nothing.
  self.damperCrossover = readDamperCrossover(car.index)
  self.velModerate = DAMPER_EVENT_MODERATE
  self.velSharp    = DAMPER_EVENT_SHARP

  -- Drive type, for the DIFFERENTIAL module. AWD cars route their centre
  -- diff through a completely different system - a chain of EXT_CONTROLLER
  -- entries reading GEAR/SPEED_RATIO/BRAKE through their own LUTs, not the
  -- simple POWER/COAST/PRELOAD fields RWD and FWD cars use (confirmed by
  -- unpacking an actual AWD car's data: it had no DIFFERENTIAL section at
  -- all, just a controller chain). Analysing that is a genuinely different,
  -- harder problem, so AWD is explicitly excluded rather than given
  -- confidently wrong advice built for the wrong architecture.
  self.driveType = 'RWD'
  local okDrive, driveIni = pcall(ac.INIConfig.carData, car.index, 'drivetrain.ini')
  if okDrive and driveIni then
    local t = iniGet(driveIni, 'TRACTION', 'TYPE', 'RWD')
    if t then self.driveType = tostring(t):upper():gsub('%s+', '') end
  end

  -- Bonus aero curve-shape check - best-effort, see checkAeroLutRisk.
  local okAero, aeroChecked, aeroRisk, aeroPeaks, aeroDynamic, aeroWingIndex = pcall(checkAeroLutRisk, car.index)
  self.aeroLutChecked = okAero and aeroChecked or false
  self.aeroLutRisk = okAero and aeroRisk or false
  self.aeroPeaks = (okAero and aeroPeaks) or {}
  self.aeroDynamic = (okAero and aeroDynamic) or {}
  -- v1.5.0 believed the live read above was dead on encrypted cars; v1.9.6:
  -- it was dead on EVERY car (string.lower on a list - see
  -- checkAeroLutRisk). When it comes back with nothing, fall back to baked,
  -- offline-verified numbers for cars this project has already decrypted.
  if not next(self.aeroPeaks) and #self.aeroDynamic == 0 and carId ~= '' and AERO_LOOKUP[carId] then
    self.aeroPeaks = AERO_LOOKUP[carId].peaks or {}
    self.aeroDynamic = AERO_LOOKUP[carId].dynamic or {}
  end
  -- Name-verified WING_i index for 'front'/'rear'/'diffuser', nil for any
  -- role this car's aero.ini didn't confirm - used by the live peak-corner
  -- CL capture in engine:update so it never mislabels a wing that isn't
  -- actually the front or rear aero surface (see wingRoleFromName).
  self.aeroWingIndex = (okAero and aeroWingIndex) or {}

  -- Physics-engine gear ratios. ac.getCarPhysics(index) exposes
  -- .gearRatios directly (confirmed on ac.StateCarPhysics in CSP's shipped
  -- type definitions) - documented "Not available in replays or for
  -- remote cars", and .isAvailable exists as its own field, a strong hint
  -- it can be false even when the struct itself isn't nil (same shape of
  -- caveat as the DCAMBER whitelist elsewhere in this file).
  --
  -- v1.5.0: only TOP gear (and the one below it, needed to predict the
  -- final upshift) is kept - by request, since GEARING's only actual
  -- advice is "you're hitting the limiter, get a taller top gear",
  -- reading every gear never served that. Index alignment with car.gear
  -- (gearRatios[N] = gear N's ratio) is now trusted rather than logged as
  -- an open question: confirmed across multiple real sessions on the same
  -- car with a physically sane, consistent, monotonically-decreasing
  -- shape (e.g. 2:2.846 3:2.000 4:1.611 5:1.320 6:1.160 7:1.000), and the
  -- old live-measurement system this replaces never once produced a
  -- value to cross-check against in any real session logged this project.
  self.topGearNum, self.topGearRatio, self.secondTopGearRatio = nil, nil, nil
  -- v1.7.3: diagnostic breadcrumb, added after this read came back totally
  -- empty (topGear=nil) on lotus_exos_125_s1 with no way to tell WHY from
  -- the log alone - okPhys/isAvailable/gearRatios presence/count are all
  -- separate possible failure points documented in the comment above, and
  -- guessing which one without this would just be another guess.
  local okPhys, physCar = pcall(ac.getCarPhysics, car.index)
  self.gearPhysDiag = string.format('okPhys=%s physCar=%s isAvailable=%s gearRatios=%s',
    tostring(okPhys), tostring(physCar ~= nil),
    tostring(okPhys and physCar and physCar.isAvailable or false),
    (okPhys and physCar and physCar.gearRatios) and tostring(#physCar.gearRatios) or 'nil')
  if okPhys and physCar and physCar.isAvailable and physCar.gearRatios then
    local okTop = pcall(function()
      local n_gears = #physCar.gearRatios - 1  -- 0-based last index = top gear
      local top = physCar.gearRatios[n_gears]
      if type(top) == 'number' and top > 0 then
        self.topGearNum = n_gears
        self.topGearRatio = top
        local second = physCar.gearRatios[n_gears - 1]
        if type(second) == 'number' and second > 0 then self.secondTopGearRatio = second end
      end
    end)
    if not okTop then self.topGearNum, self.topGearRatio, self.secondTopGearRatio = nil, nil, nil end
  end
end

-- Only re-reads data/setup.ini when the car actually changes; this file read
-- is heavier than the tyres.ini/suspensions.ini ones (many more sections
-- probed), so it's done on demand rather than every frame.
---@param car ac.StateCar
function engine:refreshSchema(car)
  if not car then return end
  if self.schema and self.schemaCarId == self.carId then return end
  self.schema, self.schemaSource = readSetupSchema(car.index, self.carId)
  self.schemaCarId = self.carId
  -- v2.2.0: CSP extended suspension data, same per-car cache.
  local okS, setupRead = pcall(ac.INIConfig.carData, car.index, 'setup.ini')
  local setupIni = okS and setupRead or nil
  self.lutArb = {
    ARB_F = readLutArb(car.index, setupIni, 'ARB_F'),
    ARB_R = readLutArb(car.index, setupIni, 'ARB_R'),
  }
  self.lutDampers = readLutDampers(car.index, setupIni)
  local okP, suspRead = pcall(ac.INIConfig.carData, car.index, 'suspensions.ini')
  local suspIni = okP and suspRead or nil
  self.damperLutsFlag = suspIni and iniNum(suspIni, '_EXTENSION', 'DAMPER_LUTS') or nil

  -- v2.3.0: chassis numbers for the calculated targets (damper ratio,
  -- spring rate for bottoming). Sprung mass per corner = TOTALMASS x axle
  -- share / 2 - HUB_MASS. Axles with a MOTION_RATIO LUT (CSP DWB2) are
  -- flagged: there SPRING_RATE may be the spring, not the wheel rate, so
  -- the wheel-rate maths is not trusted.
  local okC, carRead = pcall(ac.INIConfig.carData, car.index, 'car.ini')
  local carIni = okC and carRead or nil
  self.chassis = {
    mass = carIni and iniNum(carIni, 'BASIC', 'TOTALMASS') or nil,
    cgFront = suspIni and iniNum(suspIni, 'BASIC', 'CG_LOCATION') or nil,
    hubF = suspIni and iniNum(suspIni, 'FRONT', 'HUB_MASS') or nil,
    hubR = suspIni and iniNum(suspIni, 'REAR', 'HUB_MASS') or nil,
    springBaseF = suspIni and iniNum(suspIni, 'FRONT', 'SPRING_RATE') or nil,
    springBaseR = suspIni and iniNum(suspIni, 'REAR', 'SPRING_RATE') or nil,
    mrF = suspIni and iniStr(suspIni, 'FRONT', 'MOTION_RATIO') or nil,
    mrR = suspIni and iniStr(suspIni, 'REAR', 'MOTION_RATIO') or nil,
  }
  -- v2.3.0: final-drive options, from setup.ini [FINAL_GEAR_RATIO]
  -- RATIOS=final.rto (rows = the saved FINAL_RATIO index; keys are text
  -- like "12//47", the outputs are the ratios). nil when the car has a
  -- fixed final drive or the file can't be read.
  self.finalOptions = nil
  local rto = setupIni and iniStr(setupIni, 'FINAL_GEAR_RATIO', 'RATIOS') or nil
  if rto then
    local pts = lutPoints(car.index, rto)
    if pts and #pts > 1 then
      self.finalOptions = {}
      for i, p in ipairs(pts) do self.finalOptions[i - 1] = p.y end
      self.finalOptionsN = #pts
    end
  end
end

-- v2.5.0: per-corner travel range (m) - suspensions.ini PACKER_RANGE, then
-- the live setup's PACKER_RANGE_xx wherever the car makes packers
-- adjustable. Stored in MILLIMETRES on every car checked (Huracan 30..70,
-- Corvette 30..80, BTCC 98..148, Exos 10..50 against 0.03-0.14 m in their
-- suspensions.ini), converted with the same SHOW_CLICKS rule as every
-- other setup item. Re-read at car load and whenever the car settles in
-- the pits, which is where setups change.
function engine:refreshTravelRef(carIndex)
  local f, r, src = readTravelRef(carIndex)
  local ref = {LF = f, RF = f, LR = r, RR = r}
  local okS, setupRead = pcall(ac.INIConfig.carData, carIndex, 'setup.ini')
  local setupIni = okS and setupRead or nil
  local okL, spinners = pcall(ac.getSetupSpinners)
  local live = 0
  if okL and type(spinners) == 'table' then
    for _, s in ipairs(spinners) do
      -- (the same read notes the brake bias on the car, for the BRAKE
      -- line's lockups-vs-calculation check)
      if type(s) == 'table' and (s.name == 'FRONT_BIAS' or s.name == 'BRAKE_BIAS') and tonumber(s.value) then
        local b = tonumber(s.value)
        self.liveBiasPct = (b <= 1.5) and b * 100 or b
      end
      local corner = type(s) == 'table' and type(s.name) == 'string' and s.name:match('^PACKER_RANGE_(%u%u)$')
      local v = corner and tonumber(s.value)
      if v and ref[corner] then
        local sc = setupIni and iniNum(setupIni, s.name, 'SHOW_CLICKS') or 0
        local mn = setupIni and iniNum(setupIni, s.name, 'MIN') or 0
        local st = setupIni and iniNum(setupIni, s.name, 'STEP') or 1
        local phys = (sc == 2) and (mn + v * st) or ((sc == 1) and (v * st) or v)
        local m = phys > 1 and phys / 1000 or phys
        if travelRefSane(m) then ref[corner] = m; live = live + 1 end
      end
    end
  end
  self.travelRef = ref
  self.lastTravelF = math.min(ref.LF, ref.RF)
  self.lastTravelR = math.min(ref.LR, ref.RR)
  self.travelRefSrc = live > 0
    and string.format('your setup\'s packer range on %d corner%s%s', live, live == 1 and '' or 's', live < 4 and ('; ' .. src .. ' for the rest') or '')
    or src
end

-- v2.3.0: sprung mass (kg) at one corner, nil if the car data didn't read.
function engine:cornerSprungMass(front)
  local c = self.chassis
  if not c or not c.mass or not c.cgFront then return nil end
  local share = front and c.cgFront or (1 - c.cgFront)
  local hub = (front and c.hubF or c.hubR) or 0
  local m = c.mass * share / 2 - hub
  if m < 30 then return nil end
  return m
end

-- v2.3.0: wheel spring rate (N/m) at one corner for the value on the car.
-- Setup files usually store springs in N/mm while suspensions.ini states
-- N/m; the car's own base rate decides which (Huracan: setup 90..180,
-- base 120000 -> x1000). nil on DWB2 motion-ratio axles or unknown units.
function engine:cornerSpringRate(front, springItem, storedValue)
  local c = self.chassis or {}
  if (front and c.mrF) or ((not front) and c.mrR) then return nil end
  local base = front and c.springBaseF or c.springBaseR
  if not springItem or storedValue == nil then return base end
  local phys = physicalOf(springItem, storedValue)
  if not phys or phys <= 0 then return base end
  if base and base > 0 then
    local ratio = base / phys
    if ratio > 300 and ratio < 3000 then return phys * 1000 end
    if ratio > 0.3 and ratio < 3 then return phys end
    return nil
  end
  return (phys < 1000) and phys * 1000 or phys
end

-- v2.2.0: the curve checks. Both return (ok, note); ok=false means "don't
-- write this", note says why (or, when ok, what the curve says).
-- `schemaItem.min` is where the spinner's stored range starts, so a stored
-- VALUE maps to a LUT row / click by offset from it.
function engine:lutArbMoveOk(section, cur, newV, schemaItem)
  local info = self.lutArb and self.lutArb[section]
  if not info then return true end
  local base = (schemaItem and schemaItem.min) or 0
  if info.readable then
    if not info.rising then
      return false, 'this bar\'s own LUT does not rise with the row - direction unknown, not written'
    end
    local s1 = info.stiff[newV - base]
    if s1 == nil then return false, string.format('row %d is outside this bar\'s %d-row LUT', newV - base, info.rows) end
    if s1 <= 0 then return false, 'that row DETACHES the bar (0 stiffness in its LUT) - never a one-click nudge' end
    local s0 = info.stiff[cur - base]
    return true, string.format('LUT stiffness %s -> %.0f', s0 and string.format('%.0f', s0) or '?', s1)
  end
  if newV <= base then
    return false, 'bar LUT not readable and that is its first row ("detached" on some cars) - not written blind'
  end
  return true, 'bar LUT not readable - direction assumed (every LUT bar seen stiffens with the row)'
end

function engine:lutDamperMoveOk(section, cur, newV, direction, schemaItem)
  local kind, corner = section:match('^DAMPER_(%u+)_(%u%u)$')
  if not kind then return true end
  local axle = (corner == 'LF' or corner == 'RF') and 'FRONT' or 'REAR'
  local d = self.lutDampers
  local curves = d and d.axles and d.axles[axle] and d.axles[axle][kind]
  if not curves or #curves.keys == 0 then
    return false, 'CSP LUT damper whose curves could not be read (dampers.ini) - not written blind (a real car\'s top rear-rebound curve is known to be broken)'
  end
  local offset = ((d.setupMin and d.setupMin[section]) or 0) - ((schemaItem and schemaItem.min) or 0)
  local c0, c1 = cur + offset, newV + offset
  local parts = {}
  for _, v in ipairs(LUT_REF_SPEEDS) do
    local f0, f1 = lutDamperForce(curves, c0, v), lutDamperForce(curves, c1, v)
    if not f0 or not f1 then return false, 'curve lookup failed - not written' end
    if direction > 0 and f1 < f0 - 1 then
      return false, string.format('this car\'s own curve makes click %g SOFTER than click %g at %.3f m/s (%.0f N vs %.0f N) - broken or inverted LUT; "stiffer" would remove damping', c1, c0, v, f1, f0)
    elseif direction < 0 and f1 > f0 + 1 then
      return false, string.format('this car\'s own curve makes click %g STIFFER than click %g at %.3f m/s (%.0f N vs %.0f N) - broken or inverted LUT', c1, c0, v, f1, f0)
    end
    table.insert(parts, string.format('%.0f->%.0f N @%.3f', f0, f1, v))
  end
  return true, 'curve checked: ' .. table.concat(parts, ', ') .. ' m/s'
end

-- One log line: which model each axle / bar uses on this car and whether
-- the curves behind the LUT ones could be read. Filled from
-- self.suspensionModel, which buildOptimalSetup sets per Build.
function engine:lutSuspensionLine()
  local m = self.suspensionModel or {}
  local d = self.lutDampers or {}
  local function damperDesc(axle, sec)
    if not sec then return 'n/a' end
    if not sec:find('^DAMPER_') then return 'vanilla N·s/m' end
    local c = d.axles and d.axles[axle] or {}
    local nb = c.BUMP and #c.BUMP.keys or 0
    local nr = c.REBOUND and #c.REBOUND.keys or 0
    return string.format('CSP LUT clicks (%d bump / %d rebound curves %s)', nb, nr,
      (nb + nr > 0) and 'read - every write curve-checked' or 'NOT readable - writes refused')
  end
  local function arbDesc(sec)
    if not sec then return 'none' end
    local info = self.lutArb and self.lutArb[sec]
    if not info then return sec .. ' vanilla' end
    if not info.readable then return sec .. ' CSP LUT (' .. tostring(info.file) .. ' not readable - direction assumed, first row off-limits)' end
    return string.format('%s CSP LUT (%d rows %.0f->%.0f%s%s)', sec, info.rows, info.stiff[0] or 0, info.stiff[info.rows - 1] or 0,
      info.firstUsableRow > 0 and string.format(', row %d first attached', info.firstUsableRow) or '',
      info.rising and '' or ', NOT RISING - not written')
  end
  return string.format('suspension model: dampers F %s · R %s · ARB F %s · R %s%s',
    damperDesc('FRONT', m.dampF), damperDesc('REAR', m.dampR), arbDesc(m.arbF), arbDesc(m.arbR),
    self.damperLutsFlag and (' · suspensions.ini DAMPER_LUTS=' .. tostring(self.damperLutsFlag)) or '')
end

-- v2.5.0: bank one evidence unit (a lap, or a section of a long lap):
-- the counters since the last unit boundary, plus the unit's own flags in
-- `bin` (lap, unit/units on long tracks, pit, partial, valid, timeMs).
function engine:bankEvidenceUnit(bin)
  local base = self.lapBoundary or {}
  -- (>= 0: a snap counted in the previous unit and moved to heldSlides in
  -- this one would otherwise show here as -1)
  for _, k in ipairs(WINDOW_KEYS) do bin[k] = math.max(0, (self[k] or 0) - (base[k] or 0)) end
  bin.travelUseF, bin.travelUseR = self.lapTravelUseF or 0, self.lapTravelUseR or 0  -- v2.3.0
  self.lapTravelUseF, self.lapTravelUseR = 0, 0
  -- v2.6.0: the unit's floor clearance per end, mm (nil: not enough data).
  bin.clrF, bin.clrR = floorHistClearance(self.lapFloorHistF), floorHistClearance(self.lapFloorHistR)
  self.lapFloorHistF, self.lapFloorHistR = {}, {}
  table.insert(self.lapBins, bin)
  self.lapBoundary = counterSnapshot(self)
  self.lapPitSeen = false
  self.unitPartial, self.unitInvalid = false, false
end

---@param dt number
---@param car ac.StateCar?
---@param sim ac.StateSim
function engine:update(dt, car, sim)
  if not car then return end
  if sim and sim.isReplayActive and not settings.sampleReplay then return end
  if sim and sim.isPaused then return end

  dt = n(dt, 0.016)
  if dt <= 0 or dt > 0.25 then dt = 0.016 end

  self.samples = self.samples + 1
  self:refreshTargets(car)

  for k, v in pairs(self.cd) do
    if v > 0 then self.cd[k] = v - dt end
  end

  local speed    = n(car.speedKmh, 0)
  local rpm      = n(car.rpm, 0)
  local limiter  = n(car.rpmLimiter, 0)
  local gas      = n(car.gas, 0)
  local brake    = n(car.brake, 0)
  local steer    = n(car.steer, 0)
  local absSteer = math.abs(steer)
  local fuel     = n(car.fuel, 0)
  local lapCount = n(car.lapCount, 0)
  -- v2.5.0: handbrake (0..1). A pulled handbrake locks the rears and
  -- rotates the car on purpose: it must not read as a brake-bias lockup or
  -- an oversteer snap (see HELD SLIDES and the lockup check).
  self.clock = (self.clock or 0) + dt
  local handbrake = n(car.handbrake, 0)
  if handbrake > 0.05 then self.lastHandbrakeAt = self.clock end
  local handbrakeRecent = (self.clock - (self.lastHandbrakeAt or -1e9)) < 1.5

  local acc = car.acceleration
  local latMs2  = acc and n(acc.x, 0) or 0
  local vertMs2 = acc and n(acc.y, 0) or 0
  local longMs2 = acc and n(acc.z, 0) or 0

  local scale = 1
  if math.abs(latMs2) > 20 or math.abs(longMs2) > 20 or math.abs(vertMs2) > 25 then
    scale = 1 / G
  end
  local latG  = latMs2  * scale
  local vertG = vertMs2 * scale
  local longG = longMs2 * scale
  local absLat = math.abs(latG)

  local onTrack = isOnTrack(car)
  local curSector = onTrack and currentSectorName(car) or nil
  local w = {}
  for i = 0, 3 do w[i + 1] = car.wheels[i] end

  -- Fuel
  if self.lapStartFuel == nil then
    self.lapStartFuel = fuel
    self.lastLapCount = lapCount
  end
  if fuel > self.lapStartFuel + 1.0 then self.lapStartFuel = fuel end
  -- v2.0.0: lap bins. First frame decides whether the app loaded into the
  -- middle of a lap (that first bin is then 'partial' and never counts as
  -- a clean lap); every frame notes a pit-lane visit; every lap boundary
  -- banks the counters since the previous boundary as one bin.
  -- v2.5.0: EVIDENCE UNITS. A lap longer than LONG_TRACK_M is split into
  -- unitsPerLap sections by spline position and each section banks its own
  -- bin (see LONG TRACKS). With unitsPerLap = 1 - every ordinary track -
  -- a unit is the lap and this is exactly the v2.0 logic.
  if self.unitsPerLap == nil then
    self.trackLengthM = sim and n(sim.trackLengthM, 0) or 0
    self.unitsPerLap = unitsPerLapFor(self.trackLengthM)
    EV_UNIT.one, EV_UNIT.many = 'lap', 'laps'
    if self.unitsPerLap > 1 then EV_UNIT.one, EV_UNIT.many = 'section', 'sections' end
  end
  local unitsN = self.unitsPerLap
  local sp = n(car.splinePosition, 0)
  if self.firstLapPartial == nil then
    local into = sp * unitsN - math.floor(sp * unitsN)  -- how far into the current unit
    self.firstLapPartial = into > 0.03 and into < 0.97
    self.curUnit = math.min(unitsN - 1, math.floor(sp * unitsN))
    self.unitStartValid = car.isLapValid
    self.lapBoundary = counterSnapshot(self)
  end
  if car.isInPitlane then self.lapPitSeen = true end
  if self.unitStartValid ~= false and car.isLapValid == false then self.unitInvalid = true end
  if unitsN > 1 then
    local u = math.min(unitsN - 1, math.floor(sp * unitsN))
    if u > self.curUnit then
      -- Forward into a later section: bank the one just finished (a jump
      -- of more than one section skipped track, so it isn't clean). A
      -- lower index is reversing or the lap wrapping - the lap boundary
      -- below closes the last section.
      self:bankEvidenceUnit({lap = self.lastLapCount + 1, unit = self.curUnit + 1, units = unitsN,
        pit = self.lapPitSeen, partial = ((#self.lapBins == 0) and self.firstLapPartial) or (u - self.curUnit > 1) or self.unitPartial,
        valid = not self.unitInvalid, timeMs = 0})
      self.curUnit = u
      self.unitStartValid = car.isLapValid
    end
  end
  -- v2.0.1: the lap counter can go BACKWARDS while the app keeps its state
  -- - a session restart resets car.lapCount to 0. The first v2.0.0 night
  -- showed exactly that: after each Build the driver loaded the setup and
  -- restarted, lapCount fell from 3 to 0, `lapCount > lastLapCount` stayed
  -- false for three whole laps, and the first boundary that did fire (lap
  -- 4) banked 205 corners as ONE bin (L4, then L5 with 242) - so the gate
  -- saw "0 clean laps" across three real laps and declined Builds it
  -- should have allowed. A drop is a new session: re-sync the counter,
  -- start the current lap's bin from here, and flag it a pit lap (the car
  -- always starts a restarted session from the pit box, so this first lap
  -- is an out-lap). Nothing else is reset - the window and its bins from
  -- before the restart stay, because whatever was consumed was consumed.
  if lapCount < self.lastLapCount then
    self.lastLapCount = lapCount
    self.lapBoundary = counterSnapshot(self)
    self.lapPitSeen = true
    self.lapStartFuel = fuel
    self.sessionRestarts = (self.sessionRestarts or 0) + 1
    self.curUnit = math.min(unitsN - 1, math.floor(sp * unitsN))  -- v2.5.0: the pit box's section
    self.unitPartial, self.unitInvalid, self.unitStartValid = false, false, car.isLapValid
  end
  if lapCount > self.lastLapCount then
    if self.lapStartFuel and fuel > 0 then
      local burned = self.lapStartFuel - fuel
      if burned >= 0.2 and burned <= 15 then self.fuelPerLap = burned end
    end
    self.lapStartFuel = fuel
    self.lastLapCount = lapCount
    self.completedLaps = lapCount
    -- The lap line closes the last unit of the lap (the whole lap when
    -- unitsPerLap = 1). v2.5.0: validity of a section is its own; of a
    -- whole lap, AC's last-lap flag as before.
    local unitValid
    if unitsN > 1 then unitValid = not self.unitInvalid else unitValid = car.isLastLapValid ~= false end
    self:bankEvidenceUnit({
      lap = lapCount, unit = unitsN > 1 and (self.curUnit + 1) or nil, units = unitsN > 1 and unitsN or nil,
      pit = self.lapPitSeen,
      partial = ((#self.lapBins == 0) and self.firstLapPartial) or (unitsN > 1 and self.curUnit < unitsN - 1) or self.unitPartial or false,
      valid = unitValid,
      timeMs = n(car.previousLapTimeMs, 0),
    })
    self.curUnit = 0
    self.unitStartValid = car.isLapValid
  end
  local cspBurn = n(car.fuelPerLap, 0)
  if self.fuelPerLap <= 0 and cspBurn > 0.2 and cspBurn < 15 then
    self.fuelPerLap = cspBurn
  end

  -- Live tyre data (FL, FR, RL, RR)
  if w[1] and w[2] and w[3] and w[4] then
    self.livePressFL = n(w[1].tyrePressure)
    self.livePressFR = n(w[2].tyrePressure)
    self.livePressRL = n(w[3].tyrePressure)
    self.livePressRR = n(w[4].tyrePressure)
    local remain, dirt, core, opt = 100, 0, 0, 0
    for i = 1, 4 do
      remain = math.min(remain, wheelWearRemain(w[i]))
      dirt   = math.max(dirt, n(w[i].tyreDirty, 0))
      core   = core + n(w[i].tyreCoreTemperature, 0)
      opt    = opt  + n(w[i].tyreOptimumTemperature, 0)
    end
    self.minWearRemain = remain
    self.maxDirt = dirt > 1.5 and dirt / 100 or dirt
    self.avgCore = core / 4
    self.avgOpt  = opt > 40 and opt / 4 or 85
    -- Peak HOT pressure actually reached on track this session, used
    -- (together with the cold capture below) to work out the real,
    -- measured cold->hot rise rather than trusting whatever the gauge
    -- happens to read the instant the Build button is pressed - which
    -- could be mid-cooldown back in the pits and badly understate it.
    if onTrack then
      if self.livePressFL > self.peakPressFL then self.peakPressFL = self.livePressFL end
      if self.livePressFR > self.peakPressFR then self.peakPressFR = self.livePressFR end
      if self.livePressRL > self.peakPressRL then self.peakPressRL = self.livePressRL end
      if self.livePressRR > self.peakPressRR then self.peakPressRR = self.livePressRR end
    end
  end

  -- Static camber capture: refreshed every time the car is stationary in the
  -- pits, so it always reflects whatever setup is actually loaded right now.
  -- This is a real physics reading (car.wheels[i].camber), not an estimate.
  local stoppedInPit = (car.isInPit or car.isInPitlane) and speed < 1.5 and absSteer < 3
  if stoppedInPit and w[1] and w[2] and w[3] and w[4] then
    self.staticCFL = n(w[1].camber, self.staticCFL)
    self.staticCFR = n(w[2].camber, self.staticCFR)
    self.staticCRL = n(w[3].camber, self.staticCRL)
    self.staticCRR = n(w[4].camber, self.staticCRR)
    self.staticCamberCaptured = true

    -- Static front ride height, new this version. car.rideHeight (confirmed
    -- on ac.StateCar in CSP's shipped type definitions: a 2-item array, 0
    -- for front/1 for rear, in METRES) is captured the same way as static
    -- camber above, for the same reason - a stable, driver-relatable
    -- baseline rather than whatever the suspension happens to be doing on
    -- a live lap. Same units as the aero GH_CL LUT's x-axis this app
    -- already samples in checkAeroLutRisk, so the two can be compared
    -- directly - see the RAKE advice/writer for what that comparison is
    -- used for (a caveat only, never silently reverses the writer).
    local okRH, rh = pcall(function() return car.rideHeight end)
    if okRH and rh and type(rh[0]) == 'number' and rh[0] > 0.005 and rh[0] < 0.5 then
      self.staticRideHeightF = rh[0]
      self.rideHeightCaptured = true
      -- v2.1.0: rear too, so the rake lever knows the car's actual rake
      -- (rear minus front) and can refuse to take it below its floor.
      if type(rh[1]) == 'number' and rh[1] > 0.005 and rh[1] < 0.5 then
        self.staticRideHeightR = rh[1]
      end
    end
    -- v2.3.0: RIDE-HEIGHT CALIBRATION. After 2 s settled in the pits, pair
    -- the ride-height setting on the car (live spinner) with the measured
    -- static ride height. Two different settings give millimetres per
    -- click, which is what lets Build put the front at the aero peak in one
    -- move instead of feeling for it a click at a time. Once per stop.
    self.pitStillTime = (self.pitStillTime or 0) + dt
    if self.pitStillTime > 2 and not self.rideCalDoneThisStop and self.rideHeightCaptured then
      self.rideCalDoneThisStop = true
      pcall(function() self:rideCalRecord() end)
    end
    -- v2.5.0: STATIC TRAVEL - where the suspension sits at rest in its own
    -- range (the Sunbeam: 63 mm of 140 mm front), and the range itself
    -- re-read once per stop, because setups (and adjustable packers)
    -- change in the pits.
    if self.pitStillTime > 2 then
      local stF = (n(w[1].suspensionTravel) + n(w[2].suspensionTravel)) / 2
      local stR = (n(w[3].suspensionTravel) + n(w[4].suspensionTravel)) / 2
      if stF > 0.001 and stR > 0.001 then self.staticTravelF, self.staticTravelR = stF, stR end
      if not self.travelRefDoneThisStop then
        self.travelRefDoneThisStop = true
        pcall(function() self:refreshTravelRef(car.index) end)
      end
    end

    -- Cold pressure: captured ONCE per reset, and only when the tyre core
    -- temperature is genuinely close to ambient - being "stationary in the
    -- pits" alone isn't enough, since tyres take a while to cool after a
    -- run and a reading taken right after boxing would still be warm, not
    -- truly cold. Gated this way so a mid-session Reset doesn't silently
    -- bank a still-warm reading as if it were a cold one.
    if not self.coldPressCaptured then
      local air = 0
      pcall(function() air = n(ac.getSim().ambientTemperature, 0) end)
      local looksCold = self.avgCore > 0 and air > 0 and math.abs(self.avgCore - air) < 15
      if looksCold then
        self.coldPressFL = self.livePressFL
        self.coldPressFR = self.livePressFR
        self.coldPressRL = self.livePressRL
        self.coldPressRR = self.livePressRR
        self.coldPressCaptured = true
      end
    end
  end
  if not stoppedInPit then
    -- v2.3.0: leaving the box re-arms the next stop's ride-height pairing.
    self.pitStillTime = 0
    self.rideCalDoneThisStop = false
    self.travelRefDoneThisStop = false  -- v2.5.0
  end

  -- Camber / contact-patch proxy: true contact-patch pressure distribution
  -- isn't exposed by the sim (confirmed - even dedicated telemetry tools use
  -- the same inside/outside tyre temperature split as their proxy for it),
  -- so this remains the best available signal. What CAN be improved is WHEN
  -- we sample it: instead of averaging every above-threshold frame equally
  -- (which mixes in corner entry/exit moments where the tyre isn't fully
  -- loaded), track the single highest-lateral-G instant within each corner
  -- and bank only that one peak-load sample when the corner ends. That
  -- moment is when the contact patch is closest to its limit and is what
  -- actually matters for camber optimisation. Corners compromised by a
  -- concurrent spin/lockup are skipped - the car's attitude isn't
  -- representative of a clean corner then.
  --
  -- Also banked at that same peak-load instant: each axle's outer-wheel
  -- .dy, CSP's own per-wheel realised lateral friction coefficient - now
  -- confirmed working in practice (real dy values observed on a live run).
  -- .abs from the same changelog entry was NOT actually present on this
  -- struct at runtime (see the pcall note further down) - a reminder that
  -- a changelog mention isn't the same as confirmation for this exact
  -- execution context, so .dy is trusted here because it's been seen
  -- working, not just documented. Averaged per axle, it becomes the basis
  -- for the MECHANICAL GRIP item and the Grip Trend comparison further
  -- down, normalised against this tyre's own DY0 reference (peak
  -- coefficient from tyres.ini) where available so it reads as "% of this
  -- tyre's own limit" rather than a raw, hard-to-interpret number.
  if onTrack and w[1] and w[4] then
    if absLat > 0.6 then
      if not self.inCorner then
        self.inCorner = true
        self.cornerPeakLat = 0
        self.cornerDirty = false
        self.cornerHasAeroCl = false
      end
      if self.cd.spin > 0 or self.cd.lockup > 0 then self.cornerDirty = true end
      if absLat > self.cornerPeakLat then
        self.cornerPeakLat = absLat
        local outF = latG > 0 and w[2] or w[1]
        local outR = latG > 0 and w[4] or w[3]
        self.cornerPeakFCam = n(outF.camber, 0)
        self.cornerPeakRCam = n(outR.camber, 0)
        self.cornerPeakFInOut = n(outF.tyreInsideTemperature) - n(outF.tyreOutsideTemperature)
        self.cornerPeakRInOut = n(outR.tyreInsideTemperature) - n(outR.tyreOutsideTemperature)
        local fEdge = (n(outF.tyreInsideTemperature) + n(outF.tyreOutsideTemperature)) * 0.5
        local rEdge = (n(outR.tyreInsideTemperature) + n(outR.tyreOutsideTemperature)) * 0.5
        self.cornerPeakFMidEdge = n(outF.tyreMiddleTemperature) - fEdge
        self.cornerPeakRMidEdge = n(outR.tyreMiddleTemperature) - rEdge
        self.cornerPeakDyF = math.abs(n(outF.dy, 0))
        self.cornerPeakDyR = math.abs(n(outR.dy, 0))
        -- Live aero CL, new this version, banked at the same peak-load
        -- instant as everything above - see checkAeroLutRisk's comment for
        -- the ac.getCarPhysics().wings sourcing. Uses the NAME-verified
        -- front/rear wing indices from aeroWingIndex, not a fixed
        -- WING_1/WING_2 guess - confirmed necessary on at least one real
        -- car (a kart whose WING_1/2 are driver-lean side wings, not
        -- front/rear aero) where guessing by position would have banked
        -- the wrong wings under the "F"/"R" labels. Silently does nothing
        -- when this car's aero.ini didn't confirm a front/rear wing.
        -- Purely informational in the advice text either way; never feeds
        -- the writer.
        local frontIdx, rearIdx = self.aeroWingIndex.front, self.aeroWingIndex.rear
        if frontIdx or rearIdx then
          local okPhys, physCar = pcall(ac.getCarPhysics, car.index)
          if okPhys and physCar and physCar.isAvailable and physCar.wings then
            local wingF = frontIdx and physCar.wings[frontIdx]
            local wingR = rearIdx and physCar.wings[rearIdx]
            if wingF and type(wingF.cl) == 'number' then
              self.cornerPeakClF = wingF.cl
              self.cornerHasAeroCl = true
            end
            if wingR and type(wingR.cl) == 'number' then
              self.cornerPeakClR = wingR.cl
              self.cornerHasAeroCl = true
            end
          end
        end
      end
    elseif self.inCorner then
      self.inCorner = false
      if not self.cornerDirty then
        self.corneringSamples = self.corneringSamples + 1
        self.fCamSum = self.fCamSum + self.cornerPeakFCam
        self.rCamSum = self.rCamSum + self.cornerPeakRCam
        -- v2.3.0: squares too, so the camber writer knows how noisy its
        -- own loaded-camber average is (standard error).
        self.fCamSqSum = (self.fCamSqSum or 0) + self.cornerPeakFCam * self.cornerPeakFCam
        self.rCamSqSum = (self.rCamSqSum or 0) + self.cornerPeakRCam * self.cornerPeakRCam
        self.fInOutSum = self.fInOutSum + self.cornerPeakFInOut
        self.rInOutSum = self.rInOutSum + self.cornerPeakRInOut
        self.fMidEdgeSum = self.fMidEdgeSum + self.cornerPeakFMidEdge
        self.rMidEdgeSum = self.rMidEdgeSum + self.cornerPeakRMidEdge
        if self.cornerPeakDyF > 0.05 or self.cornerPeakDyR > 0.05 then
          self.dyPeakFSum = self.dyPeakFSum + self.cornerPeakDyF
          self.dyPeakRSum = self.dyPeakRSum + self.cornerPeakDyR
          self.dyPeakN = self.dyPeakN + 1
        end
        if self.cornerHasAeroCl then
          self.aeroClFSum = self.aeroClFSum + (self.cornerPeakClF or 0)
          self.aeroClRSum = self.aeroClRSum + (self.cornerPeakClR or 0)
          self.aeroClN = self.aeroClN + 1
        end
      end
    end
  end


  -- v2.3.0: HARD STRAIGHT-LINE BRAKING - front axle's share of the tyre
  -- load, for the calculated brake-bias baseline. Only near-peak,
  -- near-straight braking counts: that's where the bias decides which
  -- axle reaches the limit first. Aero load is included automatically
  -- (these are the tyres' real loads). Zones counted separately so a
  -- single long stop can't pass as enough evidence.
  do
    -- v2.5.0: not with the handbrake in use (a rally-style stop is not a
    -- measure of the foot-brake balance).
    local hardBrake = onTrack and brake > 0.7 and longG < -0.9 and absSteer < 15 and absLat < 0.3 and speed > 60 and not handbrakeRecent
    if hardBrake and w[1] and w[4] then
      local l1, l2, l3, l4 = n(w[1].load), n(w[2].load), n(w[3].load), n(w[4].load)
      local lf, lr = l1 + l2, l3 + l4
      -- v2.5.2: all four wheels on the ground. With one in the air (a crest
      -- on a gravel stage) the grip model has no force for it, so the
      -- sample counted for the load split but not the grip sums - enough of
      -- them (England rally, 4 Oct: 5 zones) pushed the grip count under 30
      -- while the load count passed, and the one-time write went out on
      -- load alone. A wheel in the air isn't a braking-balance sample.
      if lf + lr > 100 and l1 > 0 and l2 > 0 and l3 > 0 and l4 > 0 then
        self.brkLoadFSum = (self.brkLoadFSum or 0) + lf / (lf + lr)
        self.brkLoadN = (self.brkLoadN or 0) + 1
        if not self.brkInZone then self.brkZones = (self.brkZones or 0) + 1 end
        -- v2.5.0: what each axle can actually stop with at these loads,
        -- from the tyre's own grip model (less grip per newton as load
        -- rises), summed per axle.
        local c1, c2 = tyreBrakeForce(self.brakeModelF, l1), tyreBrakeForce(self.brakeModelF, l2)
        local c3, c4 = tyreBrakeForce(self.brakeModelR, l3), tyreBrakeForce(self.brakeModelR, l4)
        if c1 and c2 and c3 and c4 then
          self.brkCapFSum = (self.brkCapFSum or 0) + c1 + c2
          self.brkCapRSum = (self.brkCapRSum or 0) + c3 + c4
          self.brkCapN = (self.brkCapN or 0) + 1
        end
      end
    end
    self.brkInZone = hardBrake
  end

  -- v2.3.0: DYNAMIC FRONT RIDE HEIGHT in fast corners (> ARB_AERO_SPLIT),
  -- where front downforce matters - compared at Build with the car's own
  -- ground-effect peak (aeroPeaks.front).
  if onTrack and speed > ARB_AERO_SPLIT_KMH and absLat > 0.5 then
    local okRH, rh = pcall(function() return car.rideHeight end)
    if okRH and rh and type(rh[0]) == 'number' and rh[0] > 0.003 and rh[0] < 0.3 then
      self.hsRhFSum = (self.hsRhFSum or 0) + rh[0]
      self.hsRhFN = (self.hsRhFN or 0) + 1
    end
    -- v2.6.0: the ground height of the splitter and the diffuser here
    -- too (name-verified indices, aeroWingIndex) - the floor-clearance
    -- step keeps them above the height where their downforce falls away.
    local fi, di = self.aeroWingIndex.front, self.aeroWingIndex.diffuser
    if fi or di then
      local okGH, ghF, ghD = pcall(function()
        local ph = ac.getCarPhysics(car.index)
        if not (ph and ph.isAvailable and ph.wings) then return nil, nil end
        local wf, wd = fi and ph.wings[fi], di and ph.wings[di]
        return wf and wf.groundHeight, wd and wd.groundHeight
      end)
      if okGH and type(ghF) == 'number' and ghF > -0.05 and ghF < 0.5 then
        self.ghFrontSum, self.ghFrontN = (self.ghFrontSum or 0) + ghF, (self.ghFrontN or 0) + 1
      end
      if okGH and type(ghD) == 'number' and ghD > -0.05 and ghD < 0.5 then
        self.ghDiffSum, self.ghDiffN = (self.ghDiffSum or 0) + ghD, (self.ghDiffN or 0) + 1
      end
    end
  end

  -- v2.6.0: FLOOR CLEARANCE (see floorHistClearance) - both ends into this
  -- lap's histograms; the floor at 1 mm or less counted as a contact.
  -- v2.6.2: the floor is the car's ground collider when the live check
  -- allows it (floorSample / colliderVerdict), else the ride-height pickups.
  if onTrack and speed > FLOOR_MIN_SPEED_KMH then
    local okFS, fF, fR = pcall(floorSample, self, car)
    if okFS then
      self.lapFloorHistF, self.lapFloorHistR = self.lapFloorHistF or {}, self.lapFloorHistR or {}
      if type(fF) == 'number' then
        floorHistAdd(self.lapFloorHistF, fF)
        if not self.floorMinF or fF < self.floorMinF then self.floorMinF = fF end
        if fF <= COLLIDER.HIT_M and self.cd.floorF <= 0 then self.floorHitsF = self.floorHitsF + 1; self.cd.floorF = 0.5 end
      end
      if type(fR) == 'number' then
        floorHistAdd(self.lapFloorHistR, fR)
        if not self.floorMinR or fR < self.floorMinR then self.floorMinR = fR end
        if fR <= COLLIDER.HIT_M and self.cd.floorR <= 0 then self.floorHitsR = self.floorHitsR + 1; self.cd.floorR = 0.5 end
      end
    end
    -- TRACK CONTACTS: the body touching the track (collidedWith 0 is the
    -- track - walls included - with a real collision depth), and where on
    -- the car. Logged only: these fields are unverified in this app.
    local okC, depth, with, pos = pcall(function() return car.collisionDepth, car.collidedWith, car.collisionPosition end)
    if okC and type(depth) == 'number' and depth > 0 and with == 0 and self.cd.contact <= 0 then
      self.trackContacts = (self.trackContacts or 0) + 1
      self.cd.contact = 0.3
      local okP, x, y = pcall(function() return pos.x, pos.y end)
      if okP and type(x) == 'number' and type(y) == 'number' then
        self.trackContactMinY = math.min(self.trackContactMinY or y, y)
        self.trackContactSumAbsX = (self.trackContactSumAbsX or 0) + math.abs(x)
        self.trackContactPosN = (self.trackContactPosN or 0) + 1
      end
    end
  end

  -- Gearing
  if onTrack and absLat < 0.25 and gas > 0.9 then
    if speed > self.topSpeed then
      self.topSpeed = speed
      self.rpmAtVmax = rpm
      -- v2.3.0: the final drive fitted when that top speed was set, so the
      -- advice can calculate the exact final that uses the rev range.
      pcall(function()
        local ph = ac.getCarPhysics(car.index)
        if ph and ph.isAvailable and type(ph.finalRatio) == 'number' and ph.finalRatio > 0.5 then
          self.finalAtVmax = ph.finalRatio
        end
      end)
      -- v1.7.3: which gear this peak-speed sample was taken in, so
      -- buildAdvice can tell whether the car was already in its highest
      -- gear (see maxGearSeen below) when it stopped accelerating - the
      -- "too tall" detection needs this independently of whether the
      -- ac.getCarPhysics() ratio read below succeeded.
      self.gearAtVmax = n(car.gear, 0)
    end
    if limiter > 4000 and rpm >= limiter - 80 and speed > 120 then
      self.limiterTime = self.limiterTime + dt
    end
  end
  if onTrack then
    local curGearNow = n(car.gear, 0)
    if curGearNow > self.maxGearSeen then self.maxGearSeen = curGearNow end
  end

  -- Per-gear live ratio measurement (rpm vs driven-wheel angularSpeed,
  -- clutch-gated, 15-frame stability streak) was retired in v1.5.0. It
  -- never once produced a value across every real session logged this
  -- project - "gearRatios ... = none measured yet" in every debug log
  -- seen so far - while ac.getCarPhysics().gearRatios (read once per car
  -- in refreshTargets, no per-frame measurement needed) has now shown
  -- physically sane, consistent, monotonically-decreasing ratios across
  -- several real sessions on the same car, which is real evidence its
  -- indexing lines up with car.gear directly. GEARING now uses that
  -- directly, and only for top gear - see refreshTargets and the GEARING
  -- advice section for why just top gear, not every gear.

  -- Peaks
  if onTrack then
    if longG < self.peakDecel then self.peakDecel = longG end
    if longG > self.peakAccel then self.peakAccel = longG end
    if absLat > self.peakLat then self.peakLat = absLat end
    if speed < 110 and absLat > 0.4 then
      self.latLow = self.latLow + absLat
      self.latLowN = self.latLowN + 1
    elseif speed >= ARB_AERO_SPLIT_KMH and absLat > 0.4 then
      self.latHigh = self.latHigh + absLat
      self.latHighN = self.latHighN + 1
    end
  end

  -- Platform
  if onTrack and speed > 20 then
    local roll, pitch = 0, 0
    pcall(function()
      local side = car.side
      local look = car.look
      if side then roll = math.deg(math.atan2(side.y, math.sqrt(side.x*side.x + side.z*side.z))) end
      if look then pitch = math.deg(math.atan2(-look.y, math.sqrt(look.x*look.x + look.z*look.z))) end
    end)
    self.rollSum = self.rollSum + math.abs(roll)
    self.pitchSum = self.pitchSum + pitch
    self.attitudeN = self.attitudeN + 1
    if w[1] and w[4] then
      local lf = n(w[1].load) + n(w[2].load)
      local lr = n(w[3].load) + n(w[4].load)
      if lf + lr > 100 then
        self.loadFSum = self.loadFSum + lf
        self.loadRSum = self.loadRSum + lr
        self.loadN = self.loadN + 1
      end
    end
  end

  -- Suspension & Separated Front/Rear Dampers, Fast Dampers, and Springs
  if onTrack and w[1] and w[4] then
    local maxF = math.max(n(w[1].suspensionTravel), n(w[2].suspensionTravel))
    local maxR = math.max(n(w[3].suspensionTravel), n(w[4].suspensionTravel))
    if maxF > self.travelFMax then self.travelFMax = maxF end
    if maxR > self.travelRMax then self.travelRMax = maxR end

    local bumpF, rebF, bumpR, rebR = false, false, false, false
    -- Damper event thresholds - fixed for every car since v2.2.0 (see
    -- refreshTargets); wheel-travel velocity in m/s.
    local modThr = self.velModerate or DAMPER_EVENT_MODERATE
    local sharpThr = self.velSharp or DAMPER_EVENT_SHARP
    local fastBumpF, fastRebF, fastBumpR, fastRebR = false, false, false, false
    for i = 1, 2 do
      local t = n(w[i].suspensionTravel)
      local vel = (t - self.lastTravel[i]) / dt
      self.lastTravel[i] = t
      dampHistAdd(self, 'F', vel, dt)
      if vel > modThr then bumpF = true end
      if vel < -modThr then rebF = true end
      if vel > sharpThr then fastBumpF = true end
      if vel < -sharpThr then fastRebF = true end
    end
    for i = 3, 4 do
      local t = n(w[i].suspensionTravel)
      local vel = (t - self.lastTravel[i]) / dt
      self.lastTravel[i] = t
      dampHistAdd(self, 'R', vel, dt)
      if vel > modThr then bumpR = true end
      if vel < -modThr then rebR = true end
      if vel > sharpThr then fastBumpR = true end
      if vel < -sharpThr then fastRebR = true end
    end

    if bumpF and self.cd.kerb <= 0 then self.dampBumpF = self.dampBumpF + 1 recordSectorEvent(self, curSector, 'dampBumpF') end
    if rebF and absSteer > 12 and self.cd.turnin <= 0 then self.dampRebF = self.dampRebF + 1 recordSectorEvent(self, curSector, 'dampRebF') end
    if bumpR and self.cd.kerb <= 0 then self.dampBumpR = self.dampBumpR + 1 recordSectorEvent(self, curSector, 'dampBumpR') end
    if rebR and self.cd.spin <= 0 then self.dampRebR = self.dampRebR + 1 recordSectorEvent(self, curSector, 'dampRebR') end

    if fastBumpF and self.cd.fastBumpF <= 0 then self.fastDampBumpF = self.fastDampBumpF + 1 self.cd.fastBumpF = 0.8 recordSectorEvent(self, curSector, 'fastDampBumpF') end
    if fastRebF and self.cd.fastRebF <= 0 then self.fastDampRebF = self.fastDampRebF + 1 self.cd.fastRebF = 0.8 recordSectorEvent(self, curSector, 'fastDampRebF') end
    if fastBumpR and self.cd.fastBumpR <= 0 then self.fastDampBumpR = self.fastDampBumpR + 1 self.cd.fastBumpR = 0.8 recordSectorEvent(self, curSector, 'fastDampBumpR') end
    if fastRebR and self.cd.fastRebR <= 0 then self.fastDampRebR = self.fastDampRebR + 1 self.cd.fastRebR = 0.8 recordSectorEvent(self, curSector, 'fastDampRebR') end

    -- v2.5.0: every corner against its OWN range (PACKER_RANGE, the live
    -- setup's packers where adjustable) - not the axle's deepest wheel over
    -- a made-up 0.12 m. See readTravelRef.
    local ref = self.travelRef
    local usedF = math.max(n(w[1].suspensionTravel) / ref.LF, n(w[2].suspensionTravel) / ref.RF)
    local usedR = math.max(n(w[3].suspensionTravel) / ref.LR, n(w[4].suspensionTravel) / ref.RR)
    if usedF > (self.travelUsePeakF or 0) then self.travelUsePeakF = usedF end
    if usedR > (self.travelUsePeakR or 0) then self.travelUsePeakR = usedR end
    -- v2.3.0: this lap's peak travel use per axle, banked into the lap bin
    -- at the boundary. The spring target uses the MEDIAN lap, so one kerb
    -- strike can't size a spring.
    if usedF > (self.lapTravelUseF or 0) then self.lapTravelUseF = usedF end
    if usedR > (self.lapTravelUseR or 0) then self.lapTravelUseR = usedR end

    -- SPRINGS moved out to its own top-level check (v1.7.0) - it used to be
    -- nested inside the bottoming branch below, which only worked by
    -- accident because 0.95 already implied the old 0.92 bottoming gate.
    -- Bottoming's gate is being raised past 0.95 below, so nesting would
    -- have silently stopped springsHits from ever firing in the 0.95-0.97
    -- band. Kept independent now on principle, not just to dodge that.
    if usedF > 0.95 and self.cd.springsF <= 0 then self.springsHitsF = self.springsHitsF + 1 self.cd.springsF = 2.0 recordSectorEvent(self, curSector, 'springsHitsF') end
    if usedR > 0.95 and self.cd.springsR <= 0 then self.springsHitsR = self.springsHitsR + 1 self.cd.springsR = 2.0 recordSectorEvent(self, curSector, 'springsHitsR') end

    -- BOTTOMING, tightened in v1.7.0. 92% travel usage is routine under hard
    -- braking on a stiffly-sprung race setup and does NOT by itself mean the
    -- floor touched down - raised to 97%, genuinely close to the packers,
    -- rather than just "high in the travel band" (which SPRINGS above
    -- already covers on its own, stricter 95% bar). The vertG spikes are
    -- now also required to co-occur with travel usage that's at least close
    -- to the limit (85%+ on either axle): a kerb can slap a wheel hard
    -- enough to spike vertical G with the chassis nowhere near the ground,
    -- and a crest/compression can produce a sharp NEGATIVE vertG (the old
    -- vertG < -0.4 alone) with the suspension nowhere near full travel
    -- either - neither is bottoming, both were being counted as bottoming
    -- before. A pure high-G hit that doesn't clear the travel bar now falls
    -- through to the existing kerb bucket below instead, which carries no
    -- setup-writing consequence - matching the fact that a little kerb
    -- scrape is normal and shouldn't chase ride height upward on its own.
    local nearMaxTravel = usedF > 0.85 or usedR > 0.85
    if usedF > 0.97 or usedR > 0.97 or ((vertG > 3.2 or vertG < -0.6) and nearMaxTravel) then
      if self.cd.bottoming <= 0 then
        self.bottoming = self.bottoming + 1
        recordSectorEvent(self, curSector, 'bottoming')
        self.cd.bottoming = 1.2
      end
    elseif vertG > 2.15 or bumpF or bumpR then
      if self.cd.kerb <= 0 then
        self.kerbs = self.kerbs + 1
        self.cd.kerb = 0.8
      end
    end
  end

  -- Handling, Differential, Rear Toe
  if onTrack and w[1] and w[4] then
    local ndF = math.max(n(w[1].ndSlip), n(w[2].ndSlip))
    local ndR = math.max(n(w[3].ndSlip), n(w[4].ndSlip))
    local srF = math.max(math.abs(n(w[1].slipRatio)), math.abs(n(w[2].slipRatio)))
    local srR = math.max(math.abs(n(w[3].slipRatio)), math.abs(n(w[4].slipRatio)))
    local srL = math.abs(n(w[3].slipRatio))
    local srRight = math.abs(n(w[4].slipRatio))
    local saF = (math.abs(n(w[1].slipAngle)) + math.abs(n(w[2].slipAngle))) * 0.5
    local saR = (math.abs(n(w[3].slipAngle)) + math.abs(n(w[4].slipAngle))) * 0.5
    local us = saF - saR

    -- DIFFERENTIAL: two independent signals, since "too little lock" and
    -- "too much lock" have opposite fixes and need to be told apart rather
    -- than lumped into one hedge. Grounded in how diff behaviour actually
    -- shows up in wheel data: a diff forces the two driven wheels toward
    -- the SAME speed in proportion to how much it's locked. Too little
    -- lock lets them diverge more than the load difference would justify;
    -- too much lock holds them together even when the load difference
    -- (from cornering) says they should differ.
    --
    -- Signal A (existing) - too little lock: near-straight-line (very low
    -- lateral G, so there's no real cornering load difference to explain
    -- an asymmetry), yet the two rear wheels' slip ratios diverge a lot.
    -- That divergence with nothing to explain it points at insufficient
    -- lock/preload letting one wheel spin more freely than the other.
    if gas > 0.4 and absLat < 0.3 and math.abs(srL - srRight) > 0.15 and speed > 40 then
      if self.cd.diff <= 0 then
        self.diffEvents = self.diffEvents + 1
        recordSectorEvent(self, curSector, 'diffEvents')
        self.cd.diff = 1.2
      end
    end

    -- Signal B (new) - too much lock: genuinely cornering under power, both
    -- rear wheels show real, roughly EQUAL slip (rather than the outside
    -- wheel gripping while the inside spins, which is what a diff with
    -- some give would allow), and the rear is sliding more than the front.
    -- A diff forcing near-identical wheel speed despite the cornering load
    -- difference is the direct signature of excessive lock - whether that
    -- shows up as the car resisting rotation (exit push) or both tyres
    -- letting go together (snap oversteer) depends on how much throttle
    -- margin is left, which is why the advice doesn't commit to just one
    -- of those symptoms.
    if gas > 0.4 and absLat > 0.35 and speed > 25
       and srL > 0.12 and srRight > 0.12 and math.abs(srL - srRight) < 0.06
       and saR > saF + 1.0 then
      if self.cd.diffLock <= 0 then
        self.diffRotationEvents = self.diffRotationEvents + 1
        recordSectorEvent(self, curSector, 'diffRotationEvents')
        self.cd.diffLock = 1.2
      end
    end

    -- Rear toe monitoring via slip angle asymmetry / instability
    local saR_diff = math.abs(n(w[3].slipAngle) - n(w[4].slipAngle))
    if saR_diff > 3.0 and speed > 80 and absLat > 0.4 then
      if self.cd.rearToe <= 0 then
        self.rearToeEvents = self.rearToeEvents + 1
        recordSectorEvent(self, curSector, 'rearToeEvents')
        self.cd.rearToe = 1.5
      end
    end

    if brake > 0.2 and speed > 25 and self.cd.lockup <= 0 then
      if (srF > 0.38 or ndF > 0.40) and srF > srR + 0.12 then
        self.lockF = self.lockF + 1
        recordSectorEvent(self, curSector, 'lockF')
        self.cd.lockup = 1.0
      elseif (srR > 0.38 or ndR > 0.40) and srR > srF + 0.12 and not handbrakeRecent then
        -- v2.5.0: not while the handbrake is (or was just) pulled - that
        -- locks the rears on purpose and said nothing about brake bias.
        self.lockR = self.lockR + 1
        recordSectorEvent(self, curSector, 'lockR')
        self.cd.lockup = 1.0
      end
    end

    if gas > 0.55 and speed > 30 and srR > 0.28 and srR > srF + 0.1 and self.cd.spin <= 0 then
      self.spinR = self.spinR + 1
      recordSectorEvent(self, curSector, 'spinR')
      self.cd.spin = 1.2
    end

    local push = (us > 2.2 and absLat > 0.45) or (absSteer > 18 and absLat < 0.75 and speed > 120)
    local snap = (us < -2.2 and absLat > 0.45) or (gas > 0.4 and absSteer > 12 and ndR > 0.28)

    -- v2.5.0: HELD SLIDES. Every car in the v2.4 logs showed 50-140 "snaps"
    -- per 100 corners - the rally Escort and Sunbeam, but the Dacia too - so
    -- the loose verdict fired on nearly every Build. Two kinds of oversteer
    -- are not a setup fault: a slide started with the handbrake, and a
    -- slide the driver HOLDS on the throttle for over a second (steering
    -- the car with the rear). Each oversteer episode is tracked. Snaps are
    -- still counted the moment they happen, on exactly the old cooldowns -
    -- so a real snap (sudden, caught, lifted off) counts as it always did
    -- and the 25-per-100 calibration stands - but once an episode shows
    -- it's deliberate, its counts move to heldSlides: logged, never a
    -- verdict. The episode ends 0.3 s after the last oversteer frame.
    local ep = self.slideEp
    if snap and not push then
      if not ep then
        ep = {start = self.clock, last = self.clock, throttle = gas >= 0.4, hand = handbrakeRecent, deliberate = false, counts = {}}
        self.slideEp = ep
      end
      ep.last = self.clock
      if gas < 0.4 then ep.throttle = false end
      if handbrakeRecent then ep.hand = true end
      if not ep.deliberate and (ep.hand or (ep.throttle and self.clock - ep.start >= HELD_SLIDE_S)) then
        ep.deliberate = true
        for _, c in ipairs(ep.counts) do
          self[c.key] = math.max(0, (self[c.key] or 0) - 1)
          unrecordSectorEvent(self, c.sector, c.key)
          self.heldSlides = self.heldSlides + 1
        end
        ep.counts = {}
      end
    elseif ep and self.clock - ep.last > 0.3 then
      self.slideEp, ep = nil, nil
    end

    if push then
      if speed < ARB_AERO_SPLIT_KMH then
        if brake > 0.05 and self.cd.turnin <= 0 then
          self.turninPush = self.turninPush + 1
          recordSectorEvent(self, curSector, 'turninPush')
          self.cd.turnin = 1.5
        elseif self.cd.midPush <= 0 then
          self.midPush = self.midPush + 1
          recordSectorEvent(self, curSector, 'midPush')
          self.cd.midPush = 1.5
        end
      elseif self.cd.highPush <= 0 then
        self.highPush = self.highPush + 1
        recordSectorEvent(self, curSector, 'highPush')
        self.cd.highPush = 1.5
      end
    elseif snap then
      -- v1.9.4: renamed from `coastPush`. This branch is inside `snap`
      -- (oversteer), gated on gas < 0.15 - it's LIFT-OFF OVERSTEER, the
      -- rear stepping out when the throttle is closed mid-corner. Nothing
      -- about it is push. The old name was a genuine misdirection for
      -- anyone reading the experiment line, where it sits (correctly)
      -- alongside the other oversteer signals. Diagnostic only; no writer
      -- consumes it.
      -- v2.5.0: a deliberate episode (see HELD SLIDES) counts as a held
      -- slide; an undecided one notes each count so it can be moved later.
      local deliberate = ep and ep.deliberate
      if gas < 0.15 and absSteer > 12 and self.cd.coast <= 0 then
        if deliberate or handbrakeRecent then
          self.heldSlides = self.heldSlides + 1
        else
          self.liftOffSnap = self.liftOffSnap + 1
          recordSectorEvent(self, curSector, 'liftOffSnap')
        end
        self.cd.coast = 1.5
      elseif speed < ARB_AERO_SPLIT_KMH and self.cd.midSnap <= 0 then
        if deliberate then
          self.heldSlides = self.heldSlides + 1
        else
          self.midSnap = self.midSnap + 1
          recordSectorEvent(self, curSector, 'midSnap')
          if ep then table.insert(ep.counts, {key = 'midSnap', sector = curSector}) end
        end
        self.cd.midSnap = 1.5
      elseif speed >= ARB_AERO_SPLIT_KMH and self.cd.highSnap <= 0 then
        if deliberate then
          self.heldSlides = self.heldSlides + 1
        else
          self.highSnap = self.highSnap + 1
          recordSectorEvent(self, curSector, 'highSnap')
          if ep then table.insert(ep.counts, {key = 'highSnap', sector = curSector}) end
        end
        self.cd.highSnap = 1.5
      end
    end

    if car.absInAction then self.absHits = self.absHits + dt end
    if car.tractionControlInAction then self.tcHits = self.tcHits + dt end
    -- Per-wheel ABS: wrapped in pcall because this field turned out NOT to
    -- exist on every CSP build's wheel struct (confirmed by a real runtime
    -- error: 'struct_state_wheel' has no member named 'abs') despite being
    -- listed in a CSP changelog - that changelog entry most likely described
    -- the physics-SCRIPT wheel struct (a different, more privileged
    -- execution context), not the app-level one this Lua app actually runs
    -- in. Left in behind a pcall so it's used automatically wherever it DOES
    -- exist, but can never again take the whole advice refresh down with it -
    -- this bug was serious: because it was an uncaught error, not just a
    -- wrong value, it aborted the rest of this function every single time it
    -- was hit, which meant self.lastAdvice below never updated while on
    -- track at all, only while stationary. Fixed and correctly scoped now.
    local absF, absR = false, false
    pcall(function()
      absF = (n(w[1].abs, 0) > 0) or (n(w[2].abs, 0) > 0)
      absR = (n(w[3].abs, 0) > 0) or (n(w[4].abs, 0) > 0)
    end)
    if absF then self.absHitsF = self.absHitsF + dt end
    if absR then self.absHitsR = self.absHitsR + dt end
  end

  self.lastAdvice = self:buildAdvice(car, sim)
end

local function item(id, st, text)
  return {id = id, status = st, text = text}
end

-- v2.6.2: the FLOOR panel line - is the car's real bottom (its ground
-- collider) reaching the track? Reports; promises nothing (the Build's
-- floor step reads the same data - see the "floor" log line).
local function floorAdvice(self, th)
  local verdict, why = colliderVerdict(self)
  local usingCollider = (verdict == 'verified' or verdict == 'unverified')
  local src = usingCollider and 'measured at the car\'s collider - its real bottom' or 'measured at the ride-height points'
  local function mm(v) return v and string.format('%.0f mm', v * 1000) or 'n/a' end
  local hitsF, hitsR = self.floorHitsF or 0, self.floorHitsR or 0
  local tail = ''
  if verdict == 'pending' then tail = ' - checking the collider against the car\'s ride height first'
  elseif verdict == 'unverified' then tail = ' (collider unchecked: ' .. why .. ')'
  elseif verdict == 'mismatch' or verdict == 'none' then tail = ' - collider not used: ' .. why end
  if hitsF + hitsR > 0 then
    return item('FLOOR', hitsF + hitsR > th and 'warn' or 'ok', string.format('Floor hitting the track this window: front %d / rear %d times, closest F %s / R %s (%s)%s',
      hitsF, hitsR, mm(self.floorMinF), mm(self.floorMinR), src, tail))
  end
  if not (self.floorMinF or self.floorMinR) then
    return item('FLOOR', 'ok', 'Floor: no data yet - drive on track above 30 km/h' .. tail)
  end
  return item('FLOOR', 'ok', string.format('Floor clear: closest F %s / R %s off the track this window (%s)%s',
    mm(self.floorMinF), mm(self.floorMinR), src, tail))
end

-- Rebuilt for 3.0.0: every category still computes exactly the same way it
-- did in 2.1.0 (same thresholds, same counters) - the only changes are (a)
-- the camber fix described at the top of the file, and (b) the final
-- ordering, which now mirrors how a real setup session is actually worked
-- through: mechanical platform first (pressure, ride height, springs,
-- dampers, ARB), then fine alignment (camber, toe) which depends on that
-- platform being settled, then drivetrain/aero/brake balance, then gearing,
-- then car-state info last.
---@param car ac.StateCar
---@param sim ac.StateSim
function engine:buildAdvice(car, sim)
  local th = math.max(1, math.floor(n(settings.threshold, 2)))
  -- v1.7.0: bottoming now needs a clearly stronger signal than the generic
  -- threshold before it's allowed to eat the SUSPENSION slot and lock out
  -- rake advice - direct response to it dominating over rake far too
  -- readily. Rake itself is unchanged, still gated at the plain `th`.
  local bottomTh = th * 2

  -- Small formatting helper shared by every module below that shows
  -- per-sector detail: turns the raw "31 at Bruxelles, 14 at La Source"
  -- into a bracketed suffix, or '' when there's nothing to show (no
  -- sector data on this track, or this event type hasn't fired anywhere
  -- yet) - so every call site can just concatenate it unconditionally.
  local function sectorSuffix(eventType)
    local s = topSectorsFor(self, eventType, 2)
    if s == '' then return '' end
    return ' [' .. s .. ']'
  end

  -- Moved here (from its original spot near AERO) so SUSPENSION's rake
  -- message can also use it - both need it, and this is early enough in
  -- the function for either to reach it. Lua locals aren't hoisted, so
  -- definition order genuinely matters here.
  local function carLikelyHasRealAero(carId)
    local id = string.lower(carId or '')
    for _, tag in ipairs({'gt3', 'gte', 'gt2', 'lmp', 'p1', 'p2', 'hypercar', 'lmh',
                          'formula', 'f1', 'f2004', 'sf15', 'sf70', 'tatuus', 'rss_formula'}) do
      if string.find(id, tag, 1, true) then return true end
    end
    return false
  end

  -- PRESSURES
  local rise = n(settings.psiRise, 3)
  local pressureItem
  if self.livePressFL < 5 then
    pressureItem = item('PRESSURES', 'wait', 'Waiting for live tyre pressures...')
  else
    -- Tyres read low relative to the hot target while they're still coming
    -- up to temperature - that's normal, not a setup problem. Judge cold
    -- readings against a projected cold target (hot target minus the
    -- configured cold->hot rise) instead of the hot target directly, so an
    -- out-lap doesn't trigger a false "add pressure" flag.
    local tyresWarm = self.avgCore > 0 and self.avgCore >= self.avgOpt - 10
    local tgtF = tyresWarm and self.targetF or (self.targetF - rise)
    local tgtR = tyresWarm and self.targetR or (self.targetR - rise)
    local flD = tgtF - self.livePressFL
    local frD = tgtF - self.livePressFR
    local rlD = tgtR - self.livePressRL
    local rrD = tgtR - self.livePressRR
    local pSt = (math.abs(flD) <= 0.3 and math.abs(frD) <= 0.3 and math.abs(rlD) <= 0.3 and math.abs(rrD) <= 0.3) and 'ok'
        or (math.abs(flD) > 1.2 or math.abs(frD) > 1.2 or math.abs(rlD) > 1.2 or math.abs(rrD) > 1.2) and 'act' or 'warn'
    local warmNote = tyresWarm and '' or string.format(' [tyres still warming, comparing to projected cold target - hot target %s]', psiStr(self.targetF))
    -- Cross-check against tread profile (middle vs both edges), the OTHER
    -- classic 3-point pyrometer read: hot middle relative to the edges
    -- means overinflated for the load/pace right now, hot edges relative
    -- to the middle means underinflated - independent of what the gauge
    -- pressure itself reads, and occasionally disagrees with it (e.g. a
    -- worn or unusually-built tyre where gauge pressure alone is
    -- misleading).
    local treadNote = ''
    if self.corneringSamples > 8 then
      local meF = self.fMidEdgeSum / self.corneringSamples
      local meR = self.rMidEdgeSum / self.corneringSamples
      if meF > 8 or meR > 8 then
        treadNote = ' | tread profile hints overinflated despite gauge reading'
      elseif meF < -8 or meR < -8 then
        treadNote = ' | tread profile hints underinflated despite gauge reading'
      end
    end
    pressureItem = item('PRESSURES', pSt, string.format(
      'FL: %s (tgt %s) | FR: %s (tgt %s) | RL: %s (tgt %s) | RR: %s (tgt %s)%s%s',
      psiStr(self.livePressFL), psiStr(tgtF),
      psiStr(self.livePressFR), psiStr(tgtF),
      psiStr(self.livePressRL), psiStr(tgtR),
      psiStr(self.livePressRR), psiStr(tgtR), warmNote, treadNote))
  end

  -- SUSPENSION (ride height / bottoming) - cross-referenced with springs,
  -- since bottoming is fixed by EITHER raising ride height OR stiffening
  -- springs (or both): ride height costs some aero platform/CoG height,
  -- stiffer springs cost a bit of mechanical grip over bumps. Which is the
  -- better call depends on how much margin you have in each direction, so
  -- both options are given rather than picking one for you.
  -- v2.5.0: peak share of each corner's OWN range (see readTravelRef).
  local usedF = (self.travelUsePeakF or 0) * 100
  local usedR = (self.travelUsePeakR or 0) * 100
  local restNote = ''
  if self.staticTravelF and self.staticTravelR and self.lastTravelF > 0 and self.lastTravelR > 0 then
    restNote = string.format(' (at rest F %.0f%% R %.0f%%)', self.staticTravelF / self.lastTravelF * 100, self.staticTravelR / self.lastTravelR * 100)
  end
  local suspensionItem
  -- v2.6.0: the panel promises what Build does now. Running out of travel
  -- on most laps at an end -> that end's bottoming chain, one move a
  -- Build; vertical-G bottoming without that -> watched, not acted on (the
  -- floor-clearance step raises ride height if the floor itself comes
  -- within FLOOR_TARGET_MM of the track).
  local tvF, tvHitsF = travelSignal(self, 'F', th)
  local tvR, tvHitsR = travelSignal(self, 'R', th)
  if tvF or tvR then
    suspensionItem = item('SUSPENSION', 'act', string.format(
      'Running out of travel at %s on most %s (max-travel hits F %d / R %d) · F %.0f%% R %.0f%% → Build works that end\'s bottoming chain one move at a time: packers > slow bump > fast bump > springs (+%.0f%% max) > ride height',
      (tvF and tvR) and 'both ends' or (tvF and 'the front' or 'the rear'), EV_UNIT.many, tvHitsF, tvHitsR, usedF, usedR, SPRING_MAX_STEP * 100))
  elseif self.bottoming > bottomTh then
    suspensionItem = item('SUSPENSION', 'warn', string.format(
      'Bottoming (%d)%s · F %.0f%% R %.0f%% - not running out of travel on most %s (max-travel hits F %d / R %d), so no bottoming change; Build raises ride height only if the floor itself comes within %d mm of the track',
      self.bottoming, sectorSuffix('bottoming'), usedF, usedR, EV_UNIT.many, tvHitsF, tvHitsR, FLOOR_TARGET_MM))
  elseif self.highPush > th or self.highSnap > th then
    -- RAKE, new since v1.0.0. More rake (front lower relative to rear)
    -- reduces understeer; less rake increases it - unanimous across nine
    -- independent sources checked before writing this (Rennlist,
    -- SPRINGRATES, iRacing, rwmgaming, Las Motorsport, Popometer,
    -- simrace.app, Nerdgasm, F1Race), both through the aero mechanism
    -- (steeper diffuser/floor) and the plain mechanical one (raising one
    -- end shifts weight, and CG, toward the other). Tied to the HIGH-speed
    -- signal specifically because every source that discussed WHY singled
    -- out cornering speed as what makes rake's effect strong - it is
    -- fundamentally a speed-dependent, load-dependent lever, unlike ARB.
    -- Several sources also warned rake's effect can be "peaky" and narrow
    -- in window, which is why the writer moves it in smaller, paired
    -- steps rather than a single big jump.
    local aeroNote = carLikelyHasRealAero(self.carId) and ' (this class runs real aero, so rake matters more here than on a simple car)' or ''
    if self.highPush > th then
      suspensionItem = item('SUSPENSION', 'act', string.format(
        'High-speed understeer (%d)%s → Build will increase rake (lower front / raise rear slightly)%s%s',
        self.highPush, sectorSuffix('highPush'), aeroNote, rideHeightStallCaveat(self)))
    else
      suspensionItem = item('SUSPENSION', 'act', string.format(
        'High-speed oversteer (%d)%s → Build will reduce rake (raise front / lower rear slightly)%s', self.highSnap, sectorSuffix('highSnap'), aeroNote))
    end
  else
    suspensionItem = item('SUSPENSION', self.travelFMax > 0 and 'ok' or 'wait', string.format('Travel F %.0f%% R %.0f%% of this car\'s range%s', usedF, usedR, restNote))
  end

  -- SPRINGS
  local springsItem
  if self.springsHitsF > th or self.springsHitsR > th then
    -- v2.6.0: springs are one fix of each end's bottoming chain, and only
    -- on a lap-consistent signal (the same travelSignal the chain runs on).
    local sParts, anyAct = {}, false
    for _, e in ipairs({'F', 'R'}) do
      local v, hits, _, agree, considered = travelSignal(self, e, th)
      local endWord = (e == 'F') and 'Front' or 'Rear'
      if v then
        anyAct = true
        table.insert(sParts, string.format('%s max-travel hits (%d) on most %s → springs are the 4th fix of its bottoming chain (after packers, slow bump, fast bump), at most +%.0f%% a Build, aiming at %.0f%% travel use',
          endWord, hits, EV_UNIT.many, SPRING_MAX_STEP * 100, SPRING_TARGET_USE * 100))
      elseif hits > th then
        table.insert(sParts, lapSupportNote(string.format('%s max-travel hits (%d)', endWord, hits), agree, considered))
      end
    end
    springsItem = item('SPRINGS', anyAct and 'act' or 'warn', table.concat(sParts, ' | '))
  else
    springsItem = item('SPRINGS', 'ok', 'Spring rates balanced')
  end

  -- FRONT / REAR DAMPERS (slow), rebuilt in 4.6.0. Real damper diagnosis
  -- uses a velocity histogram - checking whether time is BALANCED across
  -- bump and rebound, not counting raw threshold crossings. A busy circuit
  -- naturally produces many events on both sides; that's a working damper,
  -- not a problem. Only a genuine IMBALANCE (one side dominating) indicates
  -- a mistuned damper, and the professional fix for that is to bring the
  -- histogram back into symmetry - which means stiffening the dominant
  -- (higher-count, comparatively softer) side, or softening the recessive
  -- side to match it. Over-damping is also a real
  -- and common mistake in its own right: it's confirmed to cost peak grip
  -- (not just comfort) despite feeling more "planted", because a locked-
  -- down suspension leaves the tyre working alone over every bump. The
  -- previous version always said "stiffen" on any high count, which is
  -- exactly the mistake this rebuild corrects.
  --
  -- The correlation with bottoming carries over from the fast-damper logic
  -- (4.4.0): events WITH bottoming mean the suspension is genuinely running
  -- out of support and stiffening is right regardless of balance. Events
  -- WITHOUT bottoming are judged purely on bump:rebound balance.
  -- v1.9.3: `handling` ('loose' | 'tight' | nil) is only passed for the
  -- rear axle and mirrors the writer's rearHandling exactly - the panel
  -- must promise what Build will actually do. See the writer's SLOW
  -- DAMPERS block for the tooltip evidence behind each direction.
  -- Slow dampers: the same verdict the Build writer uses (damperHistVerdict).
  local function slowDamperAdvice(e, bottomingOnAxle, axleLabel, handling)
    local hv = self:damperHistVerdict(e)
    if bottomingOnAxle then
      return 'act', string.format('%s running out of travel on most %s → left to the bottoming chain: slow bump is its 2nd fix, rebound is never stiffened for bottoming (%s)',
        axleLabel, EV_UNIT.many, hv.text)
    end
    if axleLabel == 'Rear' and handling == 'loose' then
      return 'act', string.format('Rear oversteer dominant → Build will SOFTEN rear rebound and rear bump (AC: lower rear rebound = more stable at turn-in; lower rear bump = more traction on brake release) · %s', hv.text)
    elseif axleLabel == 'Rear' and handling == 'tight' then
      return 'act', string.format('Rear planted, front pushing → Build will STIFFEN rear rebound for rotation, within 30%% of its limit · %s', hv.text)
    end
    if hv.verdict == 'bumpSoft' then
      return 'act', string.format('%s: %s → Build will stiffen slow bump one click (or soften rebound if bump is at its limit)', axleLabel, hv.text)
    elseif hv.verdict == 'rebSoft' then
      return 'act', string.format('%s: %s → Build will stiffen slow rebound one click (or soften bump if rebound is at its limit)', axleLabel, hv.text)
    end
    return hv.measured and 'ok' or 'wait', string.format('%s dampers: %s', axleLabel, hv.text)
  end

  -- FRONT / REAR DAMPERS (slow)
  -- v2.6.0: the writer's lap-consistent test (travelSignal), not the raw count.
  local bottomingF = (travelSignal(self, 'F', th)) ~= nil
  local bottomingR = (travelSignal(self, 'R', th)) ~= nil
  local fSt, fTxt = slowDamperAdvice('F', bottomingF, 'Front')
  local frontDampItem = item('FRONT DAMPERS', fSt, fTxt)

  local rearHandling, rearSnapN, rearPushN, rearNote = rearHandlingSignal(self, th)
  local rSt, rTxt = slowDamperAdvice('R', bottomingR, 'Rear', rearHandling)
  local rearDampItem = item('REAR DAMPERS', rSt, rTxt)


  -- FAST DAMPERS - direction depends on WHY they're being worked. Fast
  -- damping handles sharp single events (kerbs, bumps, ripples), and AC's
  -- own in-game description is explicit: lower fast-bump values let the
  -- suspension absorb more energy over bumps and kerbs, while a very stiff
  -- setting means the damper barely moves, absorbing nothing and launching
  -- the car. So repeated fast-damper hits WITHOUT bottoming call for
  -- SOFTER (compliance, keeps the tyre on the road, real mechanical grip);
  -- only when the suspension is also running out of travel does stiffer
  -- become the right answer (v2.6.0: as the bottoming chain's 3rd fix, one
  -- change at a time). Previous versions always said stiffen, which
  -- was backwards for the common kerb-riding case.
  -- v2.6.0: per end, matching the writer. An end that runs out of travel
  -- on most laps is left to its bottoming chain (fast bump is its 3rd fix;
  -- fast rebound is never stiffened for bottoming - too much rebound packs
  -- a car down). Otherwise fast hits mean kerbs: until v2.6.1 the panel
  -- said soften; the kerb softener is gone from Build (v2.6.1), so the
  -- panel now just reports the hits and promises nothing.
  local function fastAdvice(e, bumpN, rebN, endWord, id)
    if bumpN <= th and rebN <= th then return item(id, 'ok', 'Fast ' .. endWord .. ' damping good') end
    if (travelSignal(self, e, th)) then
      return item(id, 'act', string.format('Fast hits %s (bump %d / rebound %d) while running out of travel on most %s → left to the bottoming chain: fast bump is its 3rd fix, fast rebound is never stiffened for bottoming',
        e, bumpN, rebN, EV_UNIT.many))
    end
    return item(id, 'ok', string.format('Fast hits %s (bump %d / rebound %d) without running out of travel - kerbs/bumps; Build leaves fast dampers alone here (v2.6.1: only the bottoming chain moves them)',
      e, bumpN, rebN))
  end
  local fastFrontItem = fastAdvice('F', self.fastDampBumpF, self.fastDampRebF, 'front', 'FAST FRONT DAMPERS')
  local fastRearItem = fastAdvice('R', self.fastDampBumpR, self.fastDampRebR, 'rear', 'FAST REAR DAMPERS')

  -- ARB. v1.9.8: same balanceVerdict the writer uses, so the panel can't
  -- promise a rear-ARB change on a car Build will (rightly) leave alone.
  -- Before this, any push count over threshold won here regardless of the
  -- oversteer count next to it - a slightly loose car read "soften front".
  local arbItem
  local lowVerdict, _, _, lowNote, lowSnapRate = regimeVerdict(self, 'low', th)
  -- v2.1.0: Build moves ONE lever per regime, ARB first in the low-speed
  -- chain (ARB > rear dampers > toe > rake), skipping any the ledger has
  -- frozen for this car - so "soften ARB" is the first candidate, not a
  -- promise. The Build log names the lever that actually moved.
  if lowVerdict == 'tight' then
    arbItem = item('ARB', 'act', string.format('Low-speed understeer (%d push / %d oversteer)%s → soften the front ARB 1-2 clicks. Build tries one lever a Build in this order: ARB, front toe, springs, rear dampers, rear toe, diff, rake', self.midPush, self.midSnap, sectorSuffix('midPush')))
  elseif lowVerdict == 'loose' then
    arbItem = item('ARB', 'act', string.format('Low-speed oversteer (%d oversteer / %d push, %.0f per 100 corners)%s → soften the rear ARB 1-2 clicks. Build tries one lever a Build in this order: ARB, rear dampers, springs, rear toe, front toe, diff, rake', self.midSnap, self.midPush, lowSnapRate, sectorSuffix('midSnap')))
  else
    local why = balanceLeftAloneNote(lowNote, self.midPush, self.midSnap, 'low-speed')
    arbItem = item('ARB', 'ok', why and ('ARB: ' .. why) or 'ARB balance good')
  end

  -- CAMBER (bug fix: if/elseif per side so contradictory advice can't both
  -- fire on the same corner; the inside/outside thermal split - the same
  -- 3-point pyrometer method used trackside - takes priority over the
  -- coarser static-angle check since it reflects what THIS tyre is doing
  -- right now, on this track, in this session)
  local camberItem
  -- CAMBER advice, rebuilt in 4.4.0. The old version had a real bug: after
  -- checking the tyre-temperature spread it fell through to a bare angle
  -- check, "static camber more negative than -1.15° is too much". Any GT
  -- car runs -2° to -3.5° as a matter of course, so that branch fired on
  -- essentially every lap of every race car and the panel permanently read
  -- "looks high → reduce neg camber" regardless of what the tyres were
  -- actually doing. Removed entirely - there is no universal "correct"
  -- static camber number to compare against, which is the whole reason the
  -- thermal method exists.
  --
  -- What's left is the real trackside technique: the inside-vs-outside
  -- temperature spread across the tread of the LOADED OUTER tyre, sampled
  -- at peak corner load. Correct negative camber makes the inside edge run
  -- slightly hotter than the outside, because it's doing slightly more of
  -- the work when the tyre is loaded and rolled onto its shoulder. Target
  -- band is inside 0-12°C hotter than outside; above that there's too much
  -- negative camber (riding the inside edge, outside edge going cold and
  -- lazy), below it too little (outside edge overheating, tyre rolling onto
  -- its shoulder).
  --
  -- Sizing: a widely used pyrometer rule of thumb is that roughly 10-12°C
  -- of inside-outside spread corresponds to about 1° of camber. Advice is
  -- given in CLICKS on the assumption 1 click = 0.1°, the most common
  -- convention (the Ferrari test car's setup stores -20 for -2.0°), and
  -- capped at 8 clicks so a single wild reading can't suggest something
  -- absurd.
  -- v1.5.0: now takes the DCAMBER peak angle + measured loaded camber
  -- first, falling back to the thermal spread only when this car's
  -- tyres.ini has no usable DCAMBER coefficients at all (no live read,
  -- no DCAMBER_LOOKUP match). Before this, the ADVICE PANEL - what's
  -- actually visible on screen - used ONLY the thermal method regardless
  -- of whether real DCAMBER data existed; the Build writer had the
  -- precise route, the panel never did. The thermal method's [0,12]°C
  -- dead zone reports 'ok' for ANY spread inside that whole band, not
  -- just near its middle - confirmed from real sessions reading "in the
  -- window" at +3 to +5°C consistently, which is genuinely inside that
  -- band but not evidence the underlying static camber is actually
  -- correct, just that the thermal proxy isn't sensitive enough to say
  -- otherwise. The DCAMBER route's dead zone is a real ±0.05° around a
  -- computed target instead.
  local function camberAdvice(peakAngle, measured, spread, axleLabel)
    if peakAngle then
      local deltaDeg = (-peakAngle) - measured
      if math.abs(deltaDeg) <= 0.05 then
        return 'ok', string.format('%s loaded %.2f° vs this tyre\'s %.2f° peak - in the window', axleLabel, measured, -peakAngle)
      end
      -- Same 1 click = 0.1° convention every other advice line already
      -- assumes; the precise scale (derived from the actual setup file)
      -- only exists at Build time, this is a rough guide like the rest
      -- of the panel. Capped at 40 clicks (4°), matching the writer's own
      -- DCAMBER sanity bound.
      local clicks = clamp(math.floor(math.abs(deltaDeg) * 10 + 0.5), 1, 40)
      local dir = deltaDeg < 0 and 'add' or 'reduce'
      return 'act', string.format('%s loaded %.2f° vs this tyre\'s %.2f° peak (%+.2f°) → %s neg camber ~%d click%s',
        axleLabel, measured, -peakAngle, deltaDeg, dir, clicks, clicks == 1 and '' or 's')
    end

    local TARGET_LO, TARGET_HI = 0, 12
    local DEG_PER_C = 1 / 12
    if spread > TARGET_HI then
      local clicks = clamp(math.floor(((spread - TARGET_HI) * DEG_PER_C) * 10 + 0.5), 1, 8)
      return 'act', string.format('%s inside %.0f°C hotter than outside (want 0-12) → reduce neg camber ~%d click%s',
        axleLabel, spread, clicks, clicks == 1 and '' or 's')
    elseif spread < TARGET_LO then
      local clicks = clamp(math.floor(((TARGET_LO - spread) * DEG_PER_C) * 10 + 0.5), 1, 8)
      return 'act', string.format('%s outside %.0f°C hotter than inside → add neg camber ~%d click%s',
        axleLabel, -spread, clicks, clicks == 1 and '' or 's')
    end
    return 'ok', string.format('%s spread %+.0f°C - in the window', axleLabel, spread)
  end

  if self.corneringSamples > 8 then
    local avgF = self.fCamSum / self.corneringSamples
    local avgR = self.rCamSum / self.corneringSamples
    local dF = self.fInOutSum / self.corneringSamples
    local dR = self.rInOutSum / self.corneringSamples
    local stF, txtF = camberAdvice(self.peakCamberF, avgF, dF, 'F')
    local stR, txtR = camberAdvice(self.peakCamberR, avgR, dR, 'R')
    local st = (stF == 'act' or stR == 'act') and 'act' or 'ok'
    camberItem = item('CAMBER', st, string.format('%s | %s  [loaded F %+.2f° R %+.2f° at peak]', txtF, txtR, avgF, avgR))
  else
    camberItem = item('CAMBER', 'wait', string.format('Sampling corners (%d/8)...', self.corneringSamples))
  end

  -- MECHANICAL GRIP: how much of THIS tyre's own peak lateral grip is
  -- actually being used at the limit of each corner, straight from CSP's
  -- per-wheel .dy (realised friction coefficient), not an inferred proxy.
  -- Normalised against DY0 (this tyre's peak coefficient reference, from
  -- tyres.ini) into a %-of-limit figure where available, since a raw dy
  -- number alone isn't very readable and different compounds have very
  -- different absolute peaks. Distinct from the camber read above: camber
  -- affects how much grip is AVAILABLE, this shows how much is actually
  -- being USED - a genuine, direct measurement rather than a car-level
  -- lateral-G proxy (which the Grip Trend comparison also now uses this
  -- for, alongside lateral G, further down).
  local mechGripItem
  if self.dyPeakN > 4 then
    local dyF = self.dyPeakFSum / self.dyPeakN
    local dyR = self.dyPeakRSum / self.dyPeakN
    local pctF = (self.dy0F and self.dy0F > 0.1) and (dyF / self.dy0F * 100) or nil
    local pctR = (self.dy0R and self.dy0R > 0.1) and (dyR / self.dy0R * 100) or nil
    local text
    if pctF and pctR then
      -- v1.9.9: says which reference. DY_REF is the coefficient at the
      -- tyre's reference load; a heavily loaded tyre has less than that
      -- available, so on aero cars the % reads a little low.
      text = string.format('F using %.0f%% of tyre peak · R using %.0f%% of tyre peak (%d corners%s)', pctF, pctR, self.dyPeakN,
        self.dyRefUsed and ', vs DY_REF at reference load' or '')
    else
      text = string.format('F dy %.2f · R dy %.2f (%d corners, this tyre states no DY0/DY_REF to normalise against)', dyF, dyR, self.dyPeakN)
    end
    local st = 'ok'
    if (pctF and pctF < 78) or (pctR and pctR < 78) then st = 'warn' end
    mechGripItem = item('MECHANICAL GRIP', st, text)
  else
    mechGripItem = item('MECHANICAL GRIP', 'wait', 'Sampling corners for grip utilisation...')
  end

  -- TOE. v1.9.9: verdict-gated like the writer, so the panel promises what
  -- Build does. "Turn-in push" alone used to light this up in every session.
  local toeCorners = math.max(self.corneringSamples or 0, 20)
  local turninRate = self.turninPush / toeCorners * 100
  local frontToeItem
  if lowVerdict == 'tight' and self.turninPush > th and turninRate > 15 then
    frontToeItem = item('FRONT TOE', 'act', string.format('Car pushing, turn-in sluggish in %.0f%% of corners (%d)%s → Build adds 1 click front toe-out', turninRate, self.turninPush, sectorSuffix('turninPush')))
  elseif lowVerdict == 'loose' then
    frontToeItem = item('FRONT TOE', 'act', 'Car is loose → Build takes 1 click of front toe-out back toward zero (calmer turn-in), if there is any')
  elseif self.turninPush > th then
    frontToeItem = item('FRONT TOE', 'ok', string.format('Turn-in push (%d, %.0f%% of corners) but balance is %s - toe left alone', self.turninPush, turninRate, lowNote or 'not clearly tight'))
  else
    frontToeItem = item('FRONT TOE', 'ok', 'Front toe response good')
  end

  local rearToeItem
  if rearHandling == 'loose' and self.rearToeEvents > th then
    rearToeItem = item('REAR TOE', 'act', string.format('Rear loose, instability events (%d)%s → Build adds 1 click rear toe-in', self.rearToeEvents, sectorSuffix('rearToeEvents')))
  elseif rearHandling == 'tight' then
    rearToeItem = item('REAR TOE', 'act', 'Car pushing → Build takes 1 click of rear toe-in back toward zero (frees the rear), if there is any')
  elseif self.rearToeEvents > th then
    rearToeItem = item('REAR TOE', 'ok', string.format('Rear instability events (%d) but balance is %s - toe left alone', self.rearToeEvents, rearNote or 'not clearly loose'))
  else
    rearToeItem = item('REAR TOE', 'ok', 'Rear toe stability good')
  end

  -- DIFFERENTIAL, rebuilt 4.6.0 with two distinct signals instead of one
  -- hedge. TC intervention time still corroborates when available, since
  -- it's the car's own electronics confirming a traction problem rather
  -- than us inferring one from slip data alone.
  --
  -- AWD cars are excluded outright: their centre diff runs through a
  -- controller chain reading GEAR/SPEED_RATIO/BRAKE via its own LUTs, not
  -- the POWER/COAST/PRELOAD fields this module (and its writer) work from.
  -- Confirmed by unpacking a real AWD car's data - it had no DIFFERENTIAL
  -- section at all. Giving this module's advice to an AWD car's centre
  -- diff would be confidently wrong, so it says so plainly instead.
  local diffItem
  if self.driveType == 'AWD' or self.driveType == '4WD' then
    diffItem = item('DIFFERENTIAL', 'ok', 'AWD centre diff uses a different control system - not analysed by this app')
  else
    local tcNote = self.tcHits > 1 and string.format(' (TC active %.1fs)', self.tcHits) or ''
    -- v1.9.9: same evidence floor + 25% dominance as the writer.
    local rotN, divN = self.diffRotationEvents, self.diffEvents
    if rotN >= HISTOGRAM_MIN_EVENTS and rotN > divN * 1.25 then
      -- Signal B dominant: both rear wheels forced to near-equal slip while
      -- cornering under power - the signature of too much lock.
      diffItem = item('DIFFERENTIAL', 'act', string.format(
        'Rear wheels locked together under power while cornering (%d vs %d diverging)%s%s → too much lock, try -5%% power lock or -10 preload',
        rotN, divN, tcNote, sectorSuffix('diffRotationEvents')))
    elseif divN >= HISTOGRAM_MIN_EVENTS and divN > rotN * 1.25 then
      -- Signal A dominant: asymmetric slip with no cornering load to
      -- explain it - the signature of too little lock.
      diffItem = item('DIFFERENTIAL', 'act', string.format(
        'Rear wheels diverging under power with no cornering load to explain it (%d vs %d forced-together)%s%s → too little lock, try +10 preload or +5%% power lock',
        divN, rotN, tcNote, sectorSuffix('diffEvents')))
    elseif rotN > th or divN > th then
      diffItem = item('DIFFERENTIAL', 'ok', string.format('%d forced-together / %d diverging events - %s, left alone%s',
        rotN, divN, (math.max(rotN, divN) < HISTOGRAM_MIN_EVENTS) and ('not enough evidence yet (needs ' .. HISTOGRAM_MIN_EVENTS .. ')') or 'neither clearly dominant', tcNote))
    else
      diffItem = item('DIFFERENTIAL', 'ok', 'Differential behavior stable' .. tcNote)
    end
  end

  -- AERO - leads with a concrete number to try, same as every other
  -- category, but ALSO checks whether the SAME direction of imbalance is
  -- showing up mechanically (low/med-speed push/snap, fixed by ARB/
  -- springs/dampers/rake above) and says so - adding wing on top of an
  -- unsorted mechanical platform still costs drag for no lasting gain,
  -- since the same imbalance still shows up at low speed where the wing
  -- does nothing. Confirmed against real setup guidance: aero is a mid/
  -- high-speed fine-tuning layer on top of a sorted mechanical platform,
  -- not a substitute for one.
  -- AERO, extended in 4.7.0 with a real, hard-won caveat. Unpacking real
  -- cars directly showed splitter/diffuser aero can be genuinely non-
  -- monotonic - the McLaren F1 GTR 96's front splitter peaks at 3° and is
  -- essentially stalled by 8°, and TWO different open-wheel ground-effect
  -- cars showed ride height sensitivity so extreme one of them actually
  -- flips from downforce to lift past a certain height. "Add a click, get
  -- more downforce" is not a safe assumption on cars with real aero. A
  -- TCR car, a hot hatch, and a classic rally car with no meaningful aero
  -- at all showed nothing like this - their curves were simple and mild.
  --
  -- Attempting to read this exact car's own curve at runtime and locate
  -- its peak precisely is the ideal fix, and depends on
  -- ac.DataLUT11.carData - now CONFIRMED to exist in APP context, not just
  -- physics scripts, straight from CSP's own shipped Lua type definitions
  -- (extension/internal/lua-sdk), independently checked against multiple
  -- separate copies of those definitions. The class-based version below
  -- remains as the reliable fallback for when a car's aero.ini doesn't
  -- parse or the LUT read throws for some other reason - cars in classes
  -- confirmed or expected to run real splitter/diffuser aero get the
  -- caveat; simpler classes don't.
  -- The runtime read is attempted first: if it works, the caveat gets
  -- more specific and confident; if it doesn't, nothing breaks, and the
  -- debug log records which path actually fired.
  local aeroCaveat = ''
  if self.aeroLutRisk then
    -- The precise, car-specific signal took priority over the class guess.
    aeroCaveat = ' [this car\'s own aero curve shows a real peak or stall within its adjustment range - more clicks won\'t always mean more downforce; watch tyre temps/balance and back off if it stops helping]'
  elseif carLikelyHasRealAero(self.carId) then
    aeroCaveat = ' [this class often runs real splitter/diffuser aero - downforce can peak partway through the range rather than always increasing, so watch tyre temps/balance as you add clicks and back off if it stops helping]'
  end
  -- Peak height appended whenever known, from EITHER source - real numbers
  -- from real GT3 cars' own data put this around 0.045-0.050m with a hard
  -- near-ground stall below ~0.038m, not a gentle taper. v1.5.0: no longer
  -- nested inside the aeroLutRisk branch - that flag only reflects the
  -- LIVE read specifically and stays false whenever AERO_LOOKUP's baked
  -- fallback had to be used instead (confirmed the normal case on at
  -- least one real encrypted car), which used to mean this number never
  -- showed at all on exactly the cars it would matter most for.
  if self.aeroPeaks and self.aeroPeaks.front then
    aeroCaveat = aeroCaveat .. string.format(' (front peaks near %.0fmm ride height on this car)', self.aeroPeaks.front * 1000)
  end
  -- Dynamic aero controllers, new this version - see checkAeroLutRisk's
  -- comment for the sourcing (confirmed on 3 real GT3 cars, all keyed on
  -- SPEED_KMH driving the diffuser). Appended regardless of aeroCaveat
  -- above since it's a separate mechanism from the static curve shape.
  if self.aeroDynamic and #self.aeroDynamic > 0 then
    local parts = {}
    for _, d in ipairs(self.aeroDynamic) do
      table.insert(parts, string.format('%s/%s', d.wing, d.input))
    end
    aeroCaveat = aeroCaveat .. string.format(
      ' [this car also dynamically adjusts %s based on live telemetry, not just the static curve - a manual click\'s effect isn\'t constant (on the real cars checked, typically strongest below ~110-120 km/h)]',
      table.concat(parts, ', '))
  end

  -- Live peak-corner CL, new this version - purely informational, from
  -- ac.getCarPhysics().wings (see the corner-peak-load capture in
  -- engine:update). Appended to whichever AERO line fires, including the
  -- 'ok' case, since it's a status readout, not a warning.
  local aeroLiveNote = ''
  if self.aeroClN > 4 then
    aeroLiveNote = string.format(' · live cl F %.2f R %.2f (peak-corner avg, %d corners)',
      self.aeroClFSum / self.aeroClN, self.aeroClRSum / self.aeroClN, self.aeroClN)
  end

  -- v1.9.8: verdict-driven, same as the wing writer. "push > th" used to
  -- win this line outright even with more oversteer events beside it.
  local aeroItem
  local highVerdict, _, _, highNote = regimeVerdict(self, 'high', th)
  if highVerdict == 'tight' then
    if self.midPush > th then
      aeroItem = item('AERO', 'act', string.format(
        'High-speed understeer (%d push / %d oversteer)%s → try +1 click front wing, but low-speed push (%d) too - sort ARB/springs/rake above first for a lasting fix rather than just adding drag%s%s',
        self.highPush, self.highSnap, sectorSuffix('highPush'), self.midPush, aeroCaveat, aeroLiveNote))
    else
      aeroItem = item('AERO', 'act', string.format('High-speed understeer (%d push / %d oversteer)%s, mechanical balance looks fine → try +1 click front wing%s%s', self.highPush, self.highSnap, sectorSuffix('highPush'), aeroCaveat, aeroLiveNote))
    end
  elseif highVerdict == 'loose' then
    if self.midSnap > th then
      aeroItem = item('AERO', 'act', string.format(
        'High-speed oversteer (%d oversteer / %d push)%s → try +1 click rear wing, but low-speed snap (%d) too - sort ARB/springs/rake above first for a lasting fix rather than just adding drag%s%s',
        self.highSnap, self.highPush, sectorSuffix('highSnap'), self.midSnap, aeroCaveat, aeroLiveNote))
    else
      aeroItem = item('AERO', 'act', string.format('High-speed oversteer (%d oversteer / %d push)%s, mechanical balance looks fine → try +1 click rear wing%s%s', self.highSnap, self.highPush, sectorSuffix('highSnap'), aeroCaveat, aeroLiveNote))
    end
  else
    local why = balanceLeftAloneNote(highNote, self.highPush, self.highSnap, 'high-speed')
    aeroItem = item('AERO', 'ok', (why and ('Aero: ' .. why) or 'Aero balance good') .. aeroLiveNote)
  end

  -- BRAKE (per-wheel ABS time is a more precise, direct corroborating
  -- signal than the combined car-level counter - straight from the car's
  -- own ABS logic rather than inferred from slip ratios)
  local brakeItem
  local absNote = ''
  if self.absHitsF > 1 or self.absHitsR > 1 then
    absNote = string.format(' (ABS F %.1fs / R %.1fs)', self.absHitsF, self.absHitsR)
  end
  -- v2.3.0: + the calculated target (both axles at the limit together, +1%
  -- stability margin) and what a move does to ENTRY - forward = more stable,
  -- more push on turn-in; rearward = more rotation, looser entry. Build
  -- writes bias once per car (capped, entry-guarded); after that this line
  -- is the only way bias changes, in the driver's hands.
  local bt, btInfo = self:biasTarget()
  local biasTail
  if bt then
    biasTail = string.format(' · calculated target %.1f%% front (%s)', bt, btInfo)
  else
    biasTail = ' · calculated target: ' .. tostring(btInfo)
  end
  local carKey = self.carId or ''
  biasTail = biasTail .. (carKey ~= '' and self:biasBaselineDone(carKey)
    and ' · Build no longer writes bias on this car (its one calculated write is used) - trim by hand: forward = steadier entry but more push, rearward = more rotation but looser'
    or ' · the next Build may make its ONE calculated bias write on this car (capped at 3%, held if it would feed an entry problem)')
  -- v2.5.0: the lockups are the car's own answer. When they point the other
  -- way from the calculation, say so - they outrank it.
  local cur = self.liveBiasPct
  if bt and cur then
    if self.lockF > self.lockR and self.lockF >= th and bt > cur + 0.5 then
      biasTail = biasTail .. string.format(' · the lockups disagree with the calculation: the fronts lock first at your %.1f%%, so the balance point is BEHIND it - trust the lockups', cur)
    elseif self.lockR > self.lockF and self.lockR >= th and bt < cur - 0.5 then
      biasTail = biasTail .. string.format(' · the lockups disagree with the calculation: the rears lock first at your %.1f%%, so the balance point is AHEAD of it - trust the lockups', cur)
    end
  end
  if self.lockF > self.lockR and self.lockF >= th then
    brakeItem = item('BRAKE', 'act', string.format('Front lockups (%d)%s%s → move bias rearward (try 1-2%%)%s', self.lockF, absNote, sectorSuffix('lockF'), biasTail))
  elseif self.lockR > self.lockF and self.lockR >= th then
    brakeItem = item('BRAKE', 'act', string.format('Rear lockups (%d)%s%s → move bias forward (try 1-2%%)%s', self.lockR, absNote, sectorSuffix('lockR'), biasTail))
  else
    brakeItem = item('BRAKE', 'ok', 'Brake bias balanced' .. absNote .. biasTail)
  end

  -- GEARING. v1.5.0: predicted-rpm text now only concerns the FINAL
  -- upshift, into top gear - the only thing GEARING's advice actually
  -- talks about is whether you're hitting the limiter (which only matters
  -- in top gear), so knowing every intermediate gear's ratio never served
  -- that. Shown only while currently in the gear just below top, since
  -- that's the one real "should I have a taller top gear" moment.
  --
  -- v1.7.3: GEARING could only ever say "you're hitting the limiter, get a
  -- taller top gear" - the mirror-image problem (gearing already too
  -- TALL, never getting near the limiter) had no detection at all, and a
  -- real report was exactly that: "barely got into top gear, nowhere near
  -- limiter". Uses maxGearSeen (the highest gear actually driven this
  -- session) rather than self.topGearNum (the ac.getCarPhysics() ratio
  -- read) specifically because that read failed outright on the car this
  -- was reported on (see gearPhysDiag in the debug log) - this new check
  -- still works when it does. NOTE: this is advice only, same as the
  -- existing limiter-hit branch - GEARING has never had a Build-time
  -- writer on any car (see the changelog for why: this car's own gearing
  -- is a ratio-SET selection, not a raw value, and picking a new ratio
  -- safely needs that set's real contents, not decrypted yet for this car).
  local gearingItem
  if self.topSpeed > 0 then
    local curGear = n(car.gear, 0)
    local predictNote = ''
    if self.topGearNum and self.topGearRatio and self.secondTopGearRatio and curGear == self.topGearNum - 1 then
      local predictedRpm = n(car.rpm, 0) * (self.topGearRatio / self.secondTopGearRatio)
      predictNote = string.format(' · upshift now → ~%.0f rpm in top gear (%d)', predictedRpm, self.topGearNum)
    end
    local limiterRpm = n(car.rpmLimiter, 0)
    -- v2.3.0: the exact final drive, when the maths has what it needs. Advice
    -- only - Build never changes gearing.
    local fd = self:finalDriveTarget(limiterRpm)
    self.finalDriveCalc = fd
    local fdNote = ''
    if fd and fd.bestIdx and fd.curIdx and fd.bestIdx ~= fd.curIdx then
      fdNote = string.format(' · calculated: set the final drive to %.3f (option %d of %d; you are on %.3f, option %d) so Vmax lands at ~97%% of the limiter',
        fd.bestRatio, fd.bestIdx + 1, fd.n, fd.cur, fd.curIdx + 1)
    elseif fd and fd.bestIdx and fd.curIdx then
      fdNote = string.format(' · calculated: your final drive %.3f is the closest this car offers to the ideal %.3f', fd.cur, fd.want)
    elseif fd then
      fdNote = string.format(' · calculated ideal final drive ~%.3f (fitted %.3f; this car\'s options could not be read)', fd.want, fd.cur)
    end
    local fdAct = fd and fd.bestIdx and fd.curIdx and fd.bestIdx ~= fd.curIdx
    if self.limiterTime > 0.6 then
      gearingItem = item('GEARING', 'act', string.format('Vmax %.0f @ %.0f rpm%s · hitting limiter → LENGTHEN the final drive%s (advice only - Build never changes gearing)', self.topSpeed, self.rpmAtVmax, predictNote, fdNote))
    elseif self.maxGearSeen > 0 and self.gearAtVmax == self.maxGearSeen and limiterRpm > 4000 and self.rpmAtVmax < limiterRpm * 0.88 then
      gearingItem = item('GEARING', 'act', string.format('Vmax %.0f @ %.0f rpm in top gear (%d), limiter %.0f%s · well under the limiter → SHORTEN the final drive%s (advice only - Build never changes gearing)', self.topSpeed, self.rpmAtVmax, self.maxGearSeen, limiterRpm, predictNote, fdNote))
    elseif fdAct then
      gearingItem = item('GEARING', 'act', string.format('Vmax %.0f @ %.0f rpm%s%s (advice only - Build never changes gearing)', self.topSpeed, self.rpmAtVmax, predictNote, fdNote))
    else
      gearingItem = item('GEARING', 'ok', string.format('Vmax %.0f @ %.0f rpm%s%s', self.topSpeed, self.rpmAtVmax, predictNote, fdNote))
    end
  else
    gearingItem = item('GEARING', 'wait', 'Accelerate on straight...')
  end

  -- TYRES, band width made compound-aware in 4.7.0. tyreOptimumTemperature
  -- is already live, real, per-car data for the CENTER of the window - the
  -- part that was wrong was treating every compound as having the same
  -- WIDTH of acceptable range around that center. Real per-compound
  -- thermal curves (checked directly for three GT3 compounds) show the
  -- plateau is genuinely wider on a hard compound than a soft one: soft
  -- 70-85°C and medium 80-95°C are both ~15° windows, but hard runs
  -- 80-105°C, a ~25° window. A soft compound run at "hard-compound-normal"
  -- temperatures really is past its window; treating them the same
  -- (the previous flat +18/-20 for every compound) risked both false
  -- "HOT" calls on a hard compound that's actually fine, and under-
  -- reacting on a soft compound that's already too hot.
  local hotMargin, coldMargin = 18, 20
  if self.compound and string.find(string.lower(self.compound), 'hard') then
    hotMargin, coldMargin = 23, 20
  end
  local tStatus = self.avgCore <= 0 and 'temps n/a'
      or (self.avgCore < self.avgOpt - coldMargin and string.format('COLD %.0f°', self.avgCore)
      or (self.avgCore > self.avgOpt + hotMargin and string.format('HOT %.0f°', self.avgCore)
      or string.format('OK %.0f°', self.avgCore)))
  local tSt = (self.minWearRemain < 35 or self.maxDirt > 0.35) and 'act' or 'ok'
  local tyresItem = item('TYRES', tSt, string.format('%s · remain %.0f%% · dirt %.0f%%', tStatus, self.minWearRemain, self.maxDirt * 100))

  -- FUEL
  local fuel = n(car.fuel, 0)
  local fuelItem
  if self.fuelPerLap > 0 then
    fuelItem = item('FUEL', 'ok', string.format('%.1f L · %.2f L/lap · ≈%.1f laps left', fuel, self.fuelPerLap, fuel / self.fuelPerLap))
  else
    fuelItem = item('FUEL', 'wait', string.format('%.1f L · complete 1 full lap', fuel))
  end

  -- PERFORMANCE
  local perfItem = item('PERFORMANCE', 'ok', string.format('Last %s · best %s · lap %d',
    fmtTime(getLastLap(car)), fmtTime(getBestLap(car)), self.completedLaps))

  -- WEATHER
  local weatherItem
  if sim then
    local air = getAirTemp(sim)
    local road = n(sim.roadTemperature, 0)
    local grip = getRoadGrip(sim)
    weatherItem = item('WEATHER', 'ok', string.format('air %.0f° · road %.0f° · grip %.2f', air, road, grip))
  end

  -- v2.0.0: BUILD EVIDENCE - first line of the panel, so "why won't it
  -- build" / "is it ready" is never a mystery. Same numbers as the gate.
  local evidenceItem
  do
    local passes, clean, pit, partial, invalid, minLaps, corners = self:buildEvidence()
    local since = tostring(self.windowLabel or 'session start')
    -- v2.5.0: counted in laps, or in sections of a lap on a long track.
    local physicsNote = self.physicsChangeNote and ' · physics changed since last time - what was learned about this car was reset' or ''
    if passes then
      evidenceItem = item('BUILD EVIDENCE', 'ok', string.format('%d clean %s%s, %d corners since %s - enough to Build (advice below is from this window)%s',
        clean, unitWord(clean), longTrackNote(self), corners, since, physicsNote))
    else
      evidenceItem = item('BUILD EVIDENCE', 'wait', string.format('%d/%d clean %s%s, %d/%d corners since %s%s - keep driving, Build will decline until then%s',
        clean, minLaps, unitWord(minLaps), longTrackNote(self), corners, BUILD_MIN_CORNERS, since,
        (pit + partial > 0) and string.format(' (%d pit/partial %s not counted)', pit + partial, unitWord(pit + partial)) or '', physicsNote))
    end
  end

  local okFloor, floorItem = pcall(floorAdvice, self, th)  -- v2.6.2
  if not okFloor then floorItem = item('FLOOR', 'ok', 'Floor: ' .. tostring(floorItem)) end
  local out = {
    evidenceItem,
    pressureItem, suspensionItem, floorItem, springsItem, frontDampItem, rearDampItem,
    fastFrontItem, fastRearItem, arbItem, camberItem, mechGripItem, frontToeItem, rearToeItem,
    diffItem, aeroItem, brakeItem, gearingItem, tyresItem, fuelItem, perfItem,
  }
  if weatherItem then table.insert(out, weatherItem) end
  return out
end

function engine:urgent()
  local list = {}
  for i = 1, #self.lastAdvice do
    local a = self.lastAdvice[i]
    if a.status == 'act' or a.status == 'warn' then
      table.insert(list, a)
    end
  end
  if #list == 0 then
    table.insert(list, item('STATUS', 'ok', 'No setup flags'))
  end
  return list
end

-- Grip trend: lateral G achieved in a given speed band is a direct
-- real-world proxy for how much grip the car is actually using (F = m*a,
-- so more sustained lateral G at the same speed band means more total
-- grip, mechanical + aero combined) - averaged over a band rather than a
-- single peak so one good/lucky corner doesn't skew the read. Comparing it
-- session-to-session is a more setup-sensitive signal than lap time alone,
-- which is also affected by traffic, fuel load and driver variance.
---@param car ac.StateCar?
---@param sim ac.StateSim
function engine:saveGripBaseline(car, sim)
  -- ac.getCar(0) is documented nilable; windowMain doesn't guard before
  -- calling this on the button press, so guard here instead - same class
  -- of bug as the .abs crash (an uncaught error here would silently kill
  -- the rest of that frame's draw).
  if not car then return end
  local trackId = getTrackFolder()
  gripBaseline.carId = self.carId
  gripBaseline.trackId = trackId
  gripBaseline.lowG = self.latLowN > 0 and (self.latLow / self.latLowN) or 0
  gripBaseline.highG = self.latHighN > 0 and (self.latHigh / self.latHighN) or 0
  gripBaseline.peakG = self.peakLat
  gripBaseline.dyF = self.dyPeakN > 0 and (self.dyPeakFSum / self.dyPeakN) or 0
  gripBaseline.dyR = self.dyPeakN > 0 and (self.dyPeakRSum / self.dyPeakN) or 0
  gripBaseline.bestLapMs = getBestLap(car)
  gripBaseline.roadTemp = sim and n(sim.roadTemperature, 0) or 0
  gripBaseline.fuel = n(car.fuel, 0)
  local okDate, dateStr = pcall(os.date, '%Y-%m-%d %H:%M')
  gripBaseline.savedAt = okDate and dateStr or 'this session'
  self.gripMsg = 'Baseline saved - future runs on this car/track will compare against it'
end

---@param car ac.StateCar?
---@param sim ac.StateSim
function engine:gripCompareText(car, sim)
  -- Called unconditionally every UI frame in windowMain with a raw
  -- ac.getCar(0) result, which is documented nilable - guard here rather
  -- than trust the call site, same reasoning as saveGripBaseline above.
  if not car then return nil end
  local trackId = getTrackFolder()
  if gripBaseline.carId == '' or gripBaseline.carId ~= self.carId or gripBaseline.trackId ~= trackId then
    return nil
  end
  local curLow = self.latLowN > 0 and (self.latLow / self.latLowN) or nil
  local curHigh = self.latHighN > 0 and (self.latHigh / self.latHighN) or nil
  local parts = {}
  if curLow and gripBaseline.lowG > 0.05 then
    table.insert(parts, string.format('low-spd grip %+.1f%%', (curLow / gripBaseline.lowG - 1) * 100))
  end
  if curHigh and gripBaseline.highG > 0.05 then
    table.insert(parts, string.format('high-spd grip %+.1f%%', (curHigh / gripBaseline.highG - 1) * 100))
  end
  if self.peakLat > 0 and gripBaseline.peakG > 0.05 then
    table.insert(parts, string.format('peak %+.1f%%', (self.peakLat / gripBaseline.peakG - 1) * 100))
  end
  -- Direct tyre grip utilisation (dy), independent of the car-level
  -- lateral-G proxies above - a setup change can raise achieved lateral G
  -- mostly through aero at speed while the tyre itself is working the same
  -- or worse, so this is tracked and compared separately rather than
  -- folded into the lateral-G figures.
  if self.dyPeakN > 4 and gripBaseline.dyF > 0.05 then
    local curDyF = self.dyPeakFSum / self.dyPeakN
    table.insert(parts, string.format('tyre grip F %+.1f%%', (curDyF / gripBaseline.dyF - 1) * 100))
  end
  if self.dyPeakN > 4 and gripBaseline.dyR > 0.05 then
    local curDyR = self.dyPeakRSum / self.dyPeakN
    table.insert(parts, string.format('R %+.1f%%', (curDyR / gripBaseline.dyR - 1) * 100))
  end
  local bestNow = getBestLap(car)
  if bestNow > 0 and gripBaseline.bestLapMs > 0 then
    table.insert(parts, string.format('lap %+.3fs', (bestNow - gripBaseline.bestLapMs) / 1000))
  end
  if #parts == 0 then
    return string.format('Baseline saved %s - drive some clean laps to compare', gripBaseline.savedAt)
  end
  local text = string.format('vs baseline (%s): %s', gripBaseline.savedAt, table.concat(parts, ' | '))
  local roadNow = sim and n(sim.roadTemperature, 0) or 0
  if gripBaseline.roadTemp > 0 and math.abs(roadNow - gripBaseline.roadTemp) > 5 then
    text = text .. string.format(' [road temp %+.0f° vs then - take with caution]', roadNow - gripBaseline.roadTemp)
  end
  local fuelDelta = n(car.fuel, 0) - gripBaseline.fuel
  if math.abs(fuelDelta) > 8 then
    text = text .. ' [fuel load differs a fair bit too - lap-time delta especially is less trustworthy here]'
  end
  return text
end

-- Debug log: appends one structured, timestamped block per "Build Optimal
-- Setup" press to a plain text file, covering exactly the kind of state
-- that's been needed to diagnose issues so far (schema read results, base
-- file found or not, every change computed, any error) - so a problem can
-- be diagnosed from the log itself rather than by guessing from symptoms.
-- Written into the same notes folder already confirmed working for pit
-- notes; append-only, no rotation - if it grows large, delete it manually.
-- v2.0.0: a successful Build consumes its evidence. Everything Build
-- decided from goes to zero; everything that describes the CAR or the
-- SESSION rather than the driving stays (static camber / ride height
-- captures, cold-pressure capture, tyre reference, schema, fuel, lap
-- history). The bins banked so far are fenced off behind windowBinsStart
-- so lap-consistency and the gate only see laps driven after this Build.
function engine:consumeWindow(label)
  for _, k in ipairs(WINDOW_KEYS) do self[k] = 0 end
  self.fCamSum, self.rCamSum, self.fInOutSum, self.rInOutSum = 0, 0, 0, 0
  self.fMidEdgeSum, self.rMidEdgeSum = 0, 0
  self.dyPeakFSum, self.dyPeakRSum, self.dyPeakN = 0, 0, 0
  self.aeroClFSum, self.aeroClRSum, self.aeroClN = 0, 0, 0
  self.peakPressFL, self.peakPressFR, self.peakPressRL, self.peakPressRR = 0, 0, 0, 0
  -- v2.3.0: calculated-target accumulators belong to the window too.
  self.fCamSqSum, self.rCamSqSum = 0, 0
  self.brkLoadFSum, self.brkLoadN, self.brkZones = 0, 0, 0
  self.brkCapFSum, self.brkCapRSum, self.brkCapN = 0, 0, 0  -- v2.5.0
  self.hsRhFSum, self.hsRhFN = 0, 0
  -- v2.6.0: FLOOR CLEARANCE accumulators (floorHitsF/R are WINDOW_KEYS);
  -- the unit in progress is partial, its histograms start again.
  self.ghFrontSum, self.ghFrontN, self.ghDiffSum, self.ghDiffN = 0, 0, 0, 0
  self.trackContacts, self.trackContactMinY, self.trackContactSumAbsX, self.trackContactPosN = 0, nil, 0, 0
  self.lapFloorHistF, self.lapFloorHistR = {}, {}
  self.floorMinF, self.floorMinR = nil, nil  -- v2.6.2 (the live collider check is per car, not per window)
  self.sectorEvents = {}
  self.slideEp = nil       -- v2.5.0: an episode can't straddle two windows
  self.unitPartial = true  -- v2.5.0: the unit in progress started before this Build
  self.lapBoundary = counterSnapshot(self)
  self.windowBinsStart = #self.lapBins
  self.windowLabel = label
  local okDate, dateStr = pcall(os.date, '%H:%M:%S')
  self.windowStartedAt = okDate and dateStr or '?'
end

--------------------------------------------------------------------------------
-- v2.1.0: LEVER CHAINS AND THE EFFECTIVENESS LEDGER.
--
-- The driver's requirement, verbatim: "if adjusting arb doesn't stop the
-- problem in a few clicks, prioritise the next module that would have an
-- effect and measure how one affects the other". So:
--   * Per regime and direction there is a CHAIN of levers in physics
--     priority order. One Build moves ONE lever per regime - the first in
--     the chain that is available (module on, section present, not at its
--     limit, trigger signal present) and not frozen.
--   * When a lever moves, the signal's rate (oversteer or push events per
--     100 corners, this window) is banked as `pending` with the Build.
--   * The NEXT Build (a fresh window, on the setup that Build wrote)
--     compares the same rate. Helped = the verdict is gone, or the rate
--     fell by at least LEVER_EFFECT_DROP (15%). Two consecutive moves
--     without effect FREEZE that lever for that signal on that car; the
--     chain moves on to the next lever. A move that helped clears the
--     count - keep using what works until it stops working or hits its
--     limit.
--   * Ledger and pending persist in ac.storage per car (the driver's
--     routine restarts the session, which reloads the app).
--   * Cross-regime conflict (push at low speed, loose at high, or the
--     reverse): mechanical levers bleed into high speed; wings don't touch
--     low speed. The aero lever goes first and the low chain is HELD for
--     that Build, so the next window can attribute the change.
-- Chains (first = tried first):
--   low-loose  ARB -> rear dampers -> springs (rear softer / front stiffer)
--              -> rear toe-in -> less front toe-out -> diff coast (more lock,
--              lift-off/entry oversteer only) -> less rake
--   low-tight  ARB -> front toe-out -> springs (front softer / rear stiffer)
--              -> rear rebound stiffer -> less rear toe-in -> diff coast
--              (less lock, entry push only) -> more rake
--   high-loose wings -> less rake -> rear toe-in
--   high-tight wings -> more rake -> front toe-out
-- Rake sits last on the low chains and second on the high chains because
-- every source that explained its effect pointed at speed and load.
-- v2.5.0: springs and diff coast added. On a car with no anti-roll bars
-- and no adjustable dampers (the Sunbeam today: live rear axle, springs,
-- ride heights, front camber/toe, diff) front toe was the ONLY lever left;
-- the spring split IS the roll-stiffness balance there, and coast lock
-- governs lift-off/entry. Both come after the ARB and dampers, so a car
-- that has those uses them first, and a car that gains them later does
-- so automatically.
--------------------------------------------------------------------------------
local LEVER_CHAINS = {
  ['low-loose']  = {'arb', 'rearDampers', 'springs', 'toeRear', 'toeFront', 'diff', 'rake'},
  ['low-tight']  = {'arb', 'toeFront', 'springs', 'rearDampers', 'toeRear', 'diff', 'rake'},
  ['high-loose'] = {'wings', 'rake', 'toeRear'},
  ['high-tight'] = {'wings', 'rake', 'toeFront'},
  -- v2.6.0: BOTTOMING, one fix at a time per end. Nik: "Bottoming - one at
  -- a time. Ride height least important. Stiffening springs too much loses
  -- grip so be cautious." Packers first (more travel before the stop,
  -- costs no platform), then slow bump, fast bump, springs (+10% a Build
  -- at most), ride height last.
  ['travelF-bottoming'] = {'packersF', 'bumpF', 'fastBumpF', 'springRateF', 'rideRaiseF'},
  ['travelR-bottoming'] = {'packersR', 'bumpR', 'fastBumpR', 'springRateR', 'rideRaiseR'},
}
-- Lever judging. One click is often smaller than the lap-to-lap noise, so
-- "no effect" usually means "not measurable yet", not "useless": a lever
-- gets three tries before it is frozen for the pass, a 10% drop counts as
-- helped, a pass that shows no gain starts another pass instead of stopping
-- the branch, and moves are kept rather than put back. The stricter
-- behaviour (put-backs, a no-gain pass stops the branch) is still in the
-- runner behind engine.branchPutBack / engine.branchStopOnNoGain, off.
local LEVER_EFFECT_DROP = 0.10
local LEVER_FREEZE_AFTER = 3
-- v2.3.0 calculated-target constants (see the CALCULATED TARGETS block).
-- (brake-bias stability margin: balanceMode().biasMargin, per BALANCE_MODES)
local BIAS_MAX_JUMP = 3.0           -- % per the single write
-- (SPRING_TARGET_USE / SPRING_MAX_STEP: with the FLOOR CLEARANCE constants,
-- above the panel code that names them.)
local RIDE_MAX_CLICKS = 3
local ZETA_FLOOR_BUMP = 0.30
local ZETA_FLOOR_REBOUND = 0.50     -- v2.6.1: was 0.40 - a corner at 0.40 overshoots ~25% after a bump, 0.50 ~16% (anti-bounce)
local LEVER_MAX_JUMP = 4            -- clicks, measured-response jump (LUT bars: 2)
local LEVER_NOISE_K = 2             -- effect must exceed 2 x combined standard error
-- v2.4.0 branch passes (see BRANCH PASSES).
local BRANCH_MAX_PASSES = 4         -- passes per branch before it stops (advice only)
local BRANCH_KEEP_RECORDS = 40      -- car + track + signal records kept in storage
local LEDGER_KEEP_CARS = 30         -- cars whose lever ledger is kept
-- The module toggle behind each lever: a put-back never touches a module
-- the driver has since switched off.
local LEVER_MODULE = {arb = 'writeARB', rearDampers = 'writeDampersRear', toeFront = 'writeToeFront',
  toeRear = 'writeToeRear', rake = 'writeSuspension', wings = 'writeAero',
  springs = 'writeSprings', diff = 'writeDifferential',  -- v2.5.0
  -- v2.6.0: the bottoming levers
  packersF = 'writeSuspension', packersR = 'writeSuspension',
  bumpF = 'writeDampersFront', bumpR = 'writeDampersRear',
  fastBumpF = 'writeFastDampersFront', fastBumpR = 'writeFastDampersRear',
  springRateF = 'writeSprings', springRateR = 'writeSprings',
  rideRaiseF = 'writeSuspension', rideRaiseR = 'writeSuspension'}

-- v2.6.0: the spring rate that brings the median lap's peak travel use
-- down to SPRING_TARGET_USE - travel under a given load scales with 1/k -
-- but never more than SPRING_MAX_STEP stiffer in one Build. A median lap
-- already inside the target needs no stiffer rate.
local function cautiousSpringTarget(k, use)
  if use <= SPRING_TARGET_USE then return k end
  return k * math.min(use / SPRING_TARGET_USE, 1 + SPRING_MAX_STEP)
end

-- v2.6.0: RIDE HEIGHT TO THE FLOOR (replaces v2.3.0's "front to the aero
-- peak", which on the Huracan GT3 Evo2 meant "lower to 22 mm" on a car
-- running 62). Nik: "it should lower until the car is at minimum available
-- without the body of the car striking the floor." The lowest end's median
-- lap keeps FLOOR_TARGET_MM off the floor (see FLOOR CLEARANCE); never into
-- the aero stall; never lowered while an end runs out of travel or uses
-- FLOOR_LOWER_TRAVEL_MAX of it, or without a reliable pit calibration at
-- both ends. Raising needs none of that - a car striking the floor comes up.
-- (FLOOR_TARGET_MM / FLOOR_LOWER_TRAVEL_MAX are declared with the FLOOR
-- CLEARANCE constants, above the panel code that names them.)

-- a = {clrF, clrR (median lap clearance, mm; nil = not measured), slopeF,
-- slopeR (mm per click), reliableF, reliableR, useF, useR (median lap peak
-- travel use, 0-1), bottomingF, bottomingR (lap-consistent max-travel
-- hits), stallRoomMm (mm above the height where downforce falls away; nil
-- = no ground-effect data)}. Returns 'lower' | 'raise' | 'hold', mm, why.
local function floorClearanceStep(a)
  if not a.clrF or not a.clrR then
    return 'hold', 0, 'no floor clearance measured at both ends yet (2 clean laps with ride-height data)'
  end
  local clr = math.min(a.clrF, a.clrR)
  if clr < FLOOR_TARGET_MM then
    return 'raise', FLOOR_TARGET_MM - clr, string.format('the lowest end is %.0f mm off the floor, under the %d mm target', clr, FLOOR_TARGET_MM)
  end
  if a.bottomingF or a.bottomingR then
    return 'hold', 0, string.format('the %s runs out of travel - never lowered while it does', a.bottomingF and 'front' or 'rear')
  end
  if not a.useF or not a.useR then return 'hold', 0, 'travel use not measured at both ends yet' end
  if a.useF >= FLOOR_LOWER_TRAVEL_MAX or a.useR >= FLOOR_LOWER_TRAVEL_MAX then
    return 'hold', 0, string.format('travel use F %.0f%% / R %.0f%% - lowered only under %.0f%%', a.useF * 100, a.useR * 100, FLOOR_LOWER_TRAVEL_MAX * 100)
  end
  if not (a.reliableF and a.reliableR and a.slopeF and a.slopeR) then
    return 'hold', 0, 'mm-per-click calibration not reliable at both ends yet - sit in the pits on three ride-height settings, same springs, similar fuel'
  end
  local mm, limit = clr - FLOOR_TARGET_MM, 'the floor target'
  if a.stallRoomMm and a.stallRoomMm < mm then mm, limit = math.max(a.stallRoomMm, 0), 'the aero stall' end
  local click = math.max(math.abs(a.slopeF), math.abs(a.slopeR))
  if mm < click then
    return 'hold', 0, string.format('%.1f mm to %s - under one click (%.2f mm)', mm, limit, click)
  end
  return 'lower', mm, string.format('%.0f mm off the floor at the lowest end, %.0f mm to %s', clr, mm, limit)
end

-- Clicks per end for the floor step: the same millimetres at both ends so
-- the rake the balance levers chose is kept. Lowering rounds DOWN (never
-- past the target) and only as far as both ends can go in RIDE_MAX_CLICKS;
-- raising rounds UP (a little high beats a strike), one click at an end
-- whose calibration isn't reliable. Returns clicksF, clicksR, mm applied.
local function floorClicks(action, mm, slopeF, slopeR, reliableF, reliableR)
  if action == 'lower' then
    local applied = math.min(mm, RIDE_MAX_CLICKS * math.min(math.abs(slopeF), math.abs(slopeR)))
    return math.floor(applied / math.abs(slopeF) + 1e-6), math.floor(applied / math.abs(slopeR) + 1e-6), applied
  end
  local function up(slope, reliable)
    if not reliable or not slope or slope == 0 then return 1 end
    return math.min(math.max(1, math.ceil(mm / math.abs(slope) - 1e-6)), RIDE_MAX_CLICKS)
  end
  return up(slopeF, reliableF), up(slopeR, reliableR), mm
end

-- v2.4.0: every car keeps its own ledger. Stored as "car1>items|car2>items"
-- (a car folder name can't contain | or >). The v2.1-2.3 form "car|items"
-- held ONE car - a Build on a second car overwrote the first car's history
-- - and is read and migrated here. Returns {car = items}, order (oldest
-- first).
local function parseLedgerStore(s)
  s = tostring(s or '')
  local out, order = {}, {}
  if s == '' then return out, order end
  if not s:find('>', 1, true) then
    local car, items = s:match('^([^|]*)|(.*)$')
    if car and car ~= '' then out[car] = items; table.insert(order, car) end
    return out, order
  end
  for block in s:gmatch('[^|]+') do
    local car, items = block:match('^([^>]+)>(.*)$')
    if car then
      if not out[car] then table.insert(order, car) end
      out[car] = items
    end
  end
  return out, order
end

-- Ledger: { [key] = { [lever] = {tries, ineff, frozen, last, sens} } }, per
-- car. Items: "key:lever:tries:ineff:frozen:last:sens;...".
function engine:leverLedgerFor(carId)
  if self.leverLedger and self.leverLedgerCar == carId then return self.leverLedger end
  local ledger = {}
  local rest = parseLedgerStore(settings.leverLedger)[carId]
  if rest then
    for item in rest:gmatch('[^;]+') do
      -- v2.3.0: optional 7th field = measured effect per click (sens).
      local key, lever, tries, ineff, frozen, last, sens = item:match('^([%a%-]+):(%a+):(%d+):(%d+):([01]):([^:]*):?([%-%d%.]*)$')
      if key and lever then
        ledger[key] = ledger[key] or {}
        ledger[key][lever] = {tries = tonumber(tries) or 0, ineff = tonumber(ineff) or 0, frozen = frozen == '1',
          last = last ~= '' and last or nil, sens = tonumber(sens)}
      end
    end
  end
  self.leverLedger, self.leverLedgerCar = ledger, carId
  return ledger
end

function engine:leverLedgerSave(carId)
  local parts = {}
  for key, levers in pairs(self.leverLedger or {}) do
    for lever, e in pairs(levers) do
      table.insert(parts, string.format('%s:%s:%d:%d:%s:%s:%s', key, lever, e.tries or 0, e.ineff or 0, e.frozen and '1' or '0', e.last or '',
        e.sens and string.format('%.3f', e.sens) or ''))
    end
  end
  table.sort(parts)
  local all, order = parseLedgerStore(settings.leverLedger)
  for i = #order, 1, -1 do if order[i] == carId then table.remove(order, i) end end
  table.insert(order, carId)   -- most recent last
  all[carId] = table.concat(parts, ';')
  while #order > LEDGER_KEEP_CARS do all[table.remove(order, 1)] = nil end
  local blocks = {}
  for _, car in ipairs(order) do table.insert(blocks, car .. '>' .. (all[car] or '')) end
  settings.leverLedger = table.concat(blocks, '|')
end

--------------------------------------------------------------------------------
-- v2.4.0: BRANCH PASSES. The driver: once a branch has been worked through,
-- cycle back to its start and monitor the group as a whole; put moves that
-- had no effect back to their starting value.
--   branch  = one signal (key, e.g. 'low-loose') on one car at one track.
--   state   = 'active' (a pass is running) | 'verify' (put-backs applied,
--             the next window checks them) | 'done' (fixed, watching) |
--             'stopped' (no gain / pass cap - advice only until reset).
--   pass    = 1..BRANCH_MAX_PASSES; baseline = the signal's rate per 100
--             corners, its per-lap standard error and the Build, when the
--             pass started.
--   moves   = {lever, result, secs = {SEC = {before, after}}} in order;
--             result 'pending' (not judged yet) | 'helped' | 'no-effect' |
--             'unjudged' (a Build on another car/track came between).
--   reverted = {SEC = {from, to}} while 'verify', to restore if needed.
-- Stored in settings.branchState as records joined by '|', fields by '>'
-- (car/track folder names can't contain either), moves by '+', a move's
-- parts by '~', sections by ',' as SEC=before/after.
--------------------------------------------------------------------------------
local function fmtNum(v)
  local s = string.format('%.4f', tonumber(v) or 0)
  s = s:gsub('0+$', '')
  s = s:gsub('%.$', '')
  if s == '-0' then s = '0' end
  return s
end

local function parseSecList(s)
  local out = {}
  for part in tostring(s or ''):gmatch('[^,]+') do
    local sec, a, b = part:match('^([%w_]+)=([%-%d%.]+)/([%-%d%.]+)$')
    if sec and tonumber(a) and tonumber(b) then out[sec] = {tonumber(a), tonumber(b)} end
  end
  return out
end

local function serialiseSecList(t)
  local keys = {}
  for k in pairs(t or {}) do table.insert(keys, k) end
  table.sort(keys)
  local parts = {}
  for _, k in ipairs(keys) do table.insert(parts, k .. '=' .. fmtNum(t[k][1]) .. '/' .. fmtNum(t[k][2])) end
  return table.concat(parts, ',')
end

local function parseBranchStore(s)
  local list = {}
  for rec in tostring(s or ''):gmatch('[^|]+') do
    local f = {}
    for field in (rec .. '>'):gmatch('([^>]*)>') do table.insert(f, field) end
    if #f >= 13 and f[1] ~= '' and f[3]:match('^%a+%-%a+$') then
      local b = {car = f[1], track = f[2], key = f[3], state = f[4], pass = tonumber(f[5]) or 1,
        baseRate = tonumber(f[6]), baseSe = tonumber(f[7]), baseBuild = tonumber(f[8]) or 0,
        outcome = f[9] ~= '' and f[9] or nil, verifyRate = tonumber(f[10]), verifySe = tonumber(f[11]),
        moves = {}, reverted = parseSecList(f[13])}
      for mv in f[12]:gmatch('[^+]+') do
        local lever, result, secs = mv:match('^(%a+)~(%a[%a%-]*)~(.*)$')
        if lever then table.insert(b.moves, {lever = lever, result = result, secs = parseSecList(secs)}) end
      end
      table.insert(list, b)
    end
  end
  return list
end

local function serialiseBranchStore(list, keep)
  local recs = {}
  for i = math.max(1, #list - (keep or BRANCH_KEEP_RECORDS) + 1), #list do
    local b = list[i]
    local mv = {}
    for _, m in ipairs(b.moves or {}) do
      table.insert(mv, m.lever .. '~' .. m.result .. '~' .. serialiseSecList(m.secs))
    end
    table.insert(recs, table.concat({b.car, b.track, b.key, b.state, tostring(b.pass or 1),
      b.baseRate and fmtNum(b.baseRate) or '', b.baseSe and fmtNum(b.baseSe) or '', tostring(b.baseBuild or 0),
      b.outcome or '', b.verifyRate and fmtNum(b.verifyRate) or '', b.verifySe and fmtNum(b.verifySe) or '',
      table.concat(mv, '+'), serialiseSecList(b.reverted)}, '>'))
  end
  return table.concat(recs, '|')
end

-- What each section a pass moved should hold when the pass ends. Moves are
-- cumulative, so a section keeps the value after the LAST move on it that
-- helped - or whose effect was never judged (not known to be useless) -
-- and otherwise goes back to the value the pass found it at. Returns
-- keep[sec], expected[sec] (where the pass's last move left it), and
-- why[sec] = the no-effect levers being undone.
local function branchKeepValues(moves)
  local keep, expected, start, lastKeep, why = {}, {}, {}, {}, {}
  for i, m in ipairs(moves or {}) do
    for sec, ba in pairs(m.secs or {}) do
      if start[sec] == nil then start[sec] = ba[1] end
      expected[sec] = ba[2]
      if m.result ~= 'no-effect' then keep[sec] = ba[2]; lastKeep[sec] = i end
    end
  end
  for sec, v in pairs(start) do
    if keep[sec] == nil then keep[sec] = v end
    local names, seen = {}, {}
    for i, m in ipairs(moves) do
      if m.secs[sec] and m.result == 'no-effect' and i > (lastKeep[sec] or 0) and not seen[m.lever] then
        seen[m.lever] = true
        table.insert(names, m.lever)
      end
    end
    why[sec] = table.concat(names, '+')
  end
  return keep, expected, why
end

-- The group verdict: baseline -> now, against the same noise test as the
-- per-click values (2 x combined per-lap standard error); without lap
-- statistics, the ledger's 15% drop.
local function branchGroupEffect(baseRate, baseSe, rateNow, seNow)
  local effect = (baseRate or 0) - (rateNow or 0)
  if baseSe and baseSe >= 0 and seNow and seNow >= 0 then
    local noise = LEVER_NOISE_K * math.sqrt(baseSe * baseSe + seNow * seNow)
    return effect > noise and effect > 0, effect, noise
  end
  return (rateNow or 0) <= (baseRate or 0) * (1 - LEVER_EFFECT_DROP) and effect > 0, effect, nil
end

-- Did the put-backs make it worse? The rate rose beyond the same noise test
-- (without lap statistics: rose 15%+).
local function branchGotWorse(beforeRate, beforeSe, rateNow, seNow)
  local up = (rateNow or 0) - (beforeRate or 0)
  if beforeSe and beforeSe >= 0 and seNow and seNow >= 0 then
    local noise = LEVER_NOISE_K * math.sqrt(beforeSe * beforeSe + seNow * seNow)
    return up > noise and up > 0, up, noise
  end
  return up > 0 and (rateNow or 0) >= (beforeRate or 0) * (1 + LEVER_EFFECT_DROP), up, nil
end

--------------------------------------------------------------------------------
-- v2.5.0: PER CAR + TRACK RECORDS. The "was the last Build loaded?" record
-- and the lever moves waiting to be judged held ONE record: after a Camotos
-- Build the next Sunbeam Build had none (log Build #37), and a Sunbeam
-- Build at Adelaide was compared with the Nordschleife Build's setup and
-- reported NO (#40, then Bathurst against Adelaide #41), so those lever
-- moves were never judged. Now one record per car + track, newest last,
-- "car>track>payload|..." (car/track folder names can't contain | or >).
-- The v2.0-2.4 single-record forms (no '>') are still read, as belonging
-- to their car at any track, and dropped on the next save.
--------------------------------------------------------------------------------
local KEYED_KEEP = 30
local function parseKeyedStore(s)
  local list = {}
  s = tostring(s or '')
  if s == '' then return list, nil end
  if not s:find('>', 1, true) then return list, s end
  for rec in s:gmatch('[^|]+') do
    local car, track, payload = rec:match('^([^>]*)>([^>]*)>(.*)$')
    if car and car ~= '' then table.insert(list, {car = car, track = track, payload = payload}) end
  end
  return list, nil
end
local function serialiseKeyedStore(list, keep)
  local recs = {}
  for i = math.max(1, #list - (keep or KEYED_KEEP) + 1), #list do
    local r = list[i]
    table.insert(recs, r.car .. '>' .. (r.track or '') .. '>' .. (r.payload or ''))
  end
  return table.concat(recs, '|')
end
-- The record for car + track (track nil = the car's newest at any track).
local function keyedGet(list, car, track)
  for i = #list, 1, -1 do
    if list[i].car == car and (track == nil or list[i].track == track) then return list[i], i end
  end
  return nil
end
-- Replace (payload) or remove (payload nil) the record for car + track;
-- a replaced record moves to the end, so the trim drops the oldest.
local function keyedPut(list, car, track, payload)
  for i = #list, 1, -1 do
    if list[i].car == car and list[i].track == track then table.remove(list, i) end
  end
  if payload then table.insert(list, {car = car, track = track, payload = payload}) end
end
-- Drop every record of one car (all tracks).
local function keyedDropCar(s, car)
  local list, legacy = parseKeyedStore(s)
  if legacy then return (legacy:sub(1, #car + 1) == car .. '|') and '' or legacy end
  local kept = {}
  for _, r in ipairs(list) do if r.car ~= car then table.insert(kept, r) end end
  return serialiseKeyedStore(kept)
end

-- Settings button: forget this car's ledger and every branch record.
function engine:leverHistoryReset(carId)
  if not carId or carId == '' then return end
  local all, order = parseLedgerStore(settings.leverLedger)
  local blocks = {}
  for _, car in ipairs(order) do
    if car ~= carId then table.insert(blocks, car .. '>' .. (all[car] or '')) end
  end
  settings.leverLedger = table.concat(blocks, '|')
  local kept = {}
  for _, b in ipairs(parseBranchStore(settings.branchState)) do
    if b.car ~= carId then table.insert(kept, b) end
  end
  settings.branchState = serialiseBranchStore(kept)
  settings.leverPending = keyedDropCar(settings.leverPending, carId)
  self.leverLedger, self.leverLedgerCar = nil, nil
end

-- Called at the top of a Build that passed the gate, BEFORE any writer:
-- judges the levers the previous Build moved against this window's rates.
-- `loadedVerdict` is the lastBuildLoaded result ('YES' / 'PARTLY' / 'NO' /
-- nil); a window driven on some other setup can't judge anything.
function engine:judgePendingLevers(carId, th, loadedVerdict, trackId)
  -- v2.4.0: every judgement is also handed to the branch passes
  -- ({key, lever, result}); 'unloaded' = the move never reached the car
  -- (or was made on another track), so the branch drops it.
  self.leverJudgements = {}
  local list, legacy = parseKeyedStore(settings.leverPending)
  local serial, rest, recTrack
  if legacy then
    -- v2.1-2.4 single record "car|serial|items[|track]".
    local recCar
    recCar, serial, rest, recTrack = legacy:match('^([^|]*)|([^|]*)|([^|]*)|?(.*)$')
    if not recCar or recCar ~= carId or not rest or rest == '' then
      return 'effect: n/a (no levers pending from a previous Build on this car)'
    end
    settings.leverPending = ''  -- consumed either way
  else
    -- v2.5.0: this car at this track only; other tracks' moves wait there.
    local rec = keyedGet(list, carId, trackId)
    if not rec then
      return 'effect: n/a (no levers pending from a previous Build on this car at this track)'
    end
    serial, rest = tostring(rec.payload or ''):match('^([^#]*)#(.*)$')
    recTrack = rec.track
    keyedPut(list, carId, rec.track, nil)  -- consumed either way
    settings.leverPending = serialiseKeyedStore(list)
    if not rest or rest == '' then
      return 'effect: n/a (no levers pending from a previous Build on this car at this track)'
    end
  end
  local function markAll(result)
    for item in rest:gmatch('[^;]+') do
      local key, lever = item:match('^([%a%-]+):(%a+):')
      if key then table.insert(self.leverJudgements, {key = key, lever = lever, result = result}) end
    end
  end
  if loadedVerdict == 'NO' then
    markAll('unloaded')
    return string.format('effect: NOT judged - the previous Build (#%s) was not loaded, so this window says nothing about its levers', serial)
  end
  if trackId and recTrack and recTrack ~= '' and recTrack ~= trackId then
    markAll('unloaded')
    return string.format('effect: NOT judged - the previous Build (#%s) was made at %s and this window was driven at %s; rates at different tracks don\'t compare', serial, recTrack, trackId)
  end
  local ledger = self:leverLedgerFor(carId)
  local parts = {}
  for item in rest:gmatch('[^;]+') do
    -- v2.3.0: + clicks moved and the window's standard error (older
    -- records without them still parse).
    local key, lever, rateBefore, clicksS, seBS = item:match('^([%a%-]+):(%a+):([%d%.]+):?(%d*):?([%-%d%.]*)$')
    if key and lever then
      local regime, dir = key:match('^(%a+)%-(%a+)$')
      local verdictNow, rateAfter, which
      local travelEnd = regime and regime:match('^travel([FR])$')
      if travelEnd then
        -- v2.6.0: a bottoming move - judged on that end's max-travel hits.
        local tv, _, tr = travelSignal(self, travelEnd, th)
        verdictNow, rateAfter, which = tv, tr, 'hits'
      else
        verdictNow = regimeVerdict(self, regime, th)
        local push, snap = regimeCounts(self, regime)
        local corners = math.max(self.corneringSamples or 0, 20)
        rateAfter = (dir == 'loose' and snap or push) / corners * 100
        which = (dir == 'loose') and 'snap' or 'push'
      end
      rateBefore = tonumber(rateBefore) or 0
      local gone = verdictNow ~= dir
      local dropped = rateAfter <= rateBefore * (1 - LEVER_EFFECT_DROP)
      local helped = gone or dropped
      ledger[key] = ledger[key] or {}
      local e = ledger[key][lever] or {tries = 0, ineff = 0, frozen = false}
      e.tries = e.tries + 1
      if helped then e.ineff = 0 else e.ineff = e.ineff + 1 end
      e.frozen = e.ineff >= LEVER_FREEZE_AFTER
      e.last = helped and 'helped' or 'no-effect'
      -- v2.3.0: per-click effect, kept ONLY when it clears the noise.
      -- effect > LEVER_NOISE_K x sqrt(seBefore^2 + seAfter^2), both windows
      -- having 2+ clean laps. A measurement that doesn't clear it (the
      -- Huracan's wing: 31.5 -> 33.8 -> 29.4 -> 32.1 per 100, scatter
      -- bigger than the effect) clears any earlier estimate, so no jump is
      -- ever sized from noise.
      local clicks = tonumber(clicksS) or 1
      local seB = tonumber(seBS)
      local _, seA = self:lapRateStats(regime, which)
      local effect = rateBefore - rateAfter
      local sensNote
      if seB and seB >= 0 and seA then
        local noise = LEVER_NOISE_K * math.sqrt(seB * seB + seA * seA)
        if effect > noise and effect > 0 then
          e.sens = -effect / math.max(clicks, 1)
          sensNote = string.format('; effect %.1f over %d click%s clears the noise (%.1f) -> %.1f per click measured', effect, clicks, clicks == 1 and '' or 's', noise, -e.sens)
        else
          e.sens = nil
          sensNote = string.format('; effect %.1f is inside the lap-to-lap noise (%.1f) - no per-click value, no jumps', effect, noise)
        end
      else
        sensNote = '; too few clean laps to measure the noise - per-click value unchanged'
      end
      ledger[key][lever] = e
      table.insert(self.leverJudgements, {key = key, lever = lever, result = helped and 'helped' or 'no-effect'})
      table.insert(parts, string.format('%s via %s: %.1f -> %.1f per 100 corners %s%s%s%s',
        key, lever, rateBefore, rateAfter,
        gone and '(signal gone - HELPED)' or (dropped and '(HELPED)' or '(NO EFFECT)'),
        (not helped) and string.format(' [%d/%d without effect]', e.ineff, LEVER_FREEZE_AFTER) or '',
        e.frozen and ' -> FROZEN for this pass of the branch' or '', sensNote))
    end
  end
  self:leverLedgerSave(carId)
  return 'effect (previous Build #' .. tostring(serial) .. '): ' .. (#parts > 0 and table.concat(parts, ' · ') or 'nothing to judge')
end

function engine:leverLedgerLine(carId)
  local ledger = self:leverLedgerFor(carId)
  local parts = {}
  for key, chain in pairs(LEVER_CHAINS) do
    local states = {}
    for _, lever in ipairs(chain) do
      local e = ledger[key] and ledger[key][lever]
      if e then
        table.insert(states, string.format('%s%s(%d tries, %d no-effect%s)', lever, e.frozen and '=FROZEN' or '', e.tries, e.ineff, e.last and (', last ' .. e.last) or ''))
      else
        table.insert(states, lever)
      end
    end
    table.insert(parts, key .. ': ' .. table.concat(states, ' > '))
  end
  table.sort(parts)
  return 'levers (chain order, ledger for this car): ' .. table.concat(parts, ' · ')
end

--------------------------------------------------------------------------------
-- v2.3.0: CALCULATED TARGETS. The driver asked whether Build calculates an
-- optimum or just steps 1-2 clicks, and asked for a calculated jump
-- wherever one genuinely exists. Researched per module against the
-- Huracan's own files and the logs:
--   * brake bias      - the front's share of tyre load under hard braking,
--                       corrected for tyre radii, is the split where both
--                       axles reach the limit together. ONE write per car,
--                       capped and entry-guarded (bias also sets entry
--                       rotation - the driver's point), then advice only.
--   * final drive     - rpm at Vmax vs the limiter gives the exact ratio;
--                       advice only (Build never changes gearing).
--   * springs         - the rate needed to stop bottoming, from the median
--                       lap's peak travel use (not one kerb strike).
--   * front ride h.   - the car's own ground-effect peak vs the measured
--                       front ride height in fast corners, sized with a
--                       mm-per-click calibration learned in the pits.
--   * damper ratio    - a FLOOR, not a target: under-damped settings are
--                       lifted back to a sane ratio in one move.
--   * camber          - (already calculated) now uses a measured per-car
--                       gain and a noise dead-band.
--   * balance levers  - no first-principles optimum exists (the Huracan's
--                       roll-stiffness split says "understeer"; every log
--                       says loose), so they are SOLVED FROM MEASUREMENT:
--                       once a lever's per-click effect is measured above
--                       the lap-to-lap noise, the chain jumps it the
--                       clicks needed instead of stepping.
--------------------------------------------------------------------------------
-- (constants for all of the above are declared with LEVER_CHAINS, above -
-- judgePendingLevers needs them and is defined before this block.)

-- Parse/serialise "car>F=a:b:c,a:b:c;R=...|car2>..." per-car point stores.
local function parsePointStore(s)
  local all = {}
  for carBlock in tostring(s or ''):gmatch('[^|]+') do
    local car, body = carBlock:match('^([^>]+)>(.*)$')
    if car then
      local entry = {F = {}, R = {}}
      for axleBlock in body:gmatch('[^;]+') do
        local axle, pts = axleBlock:match('^([FR])=(.*)$')
        if axle then
          for pt in pts:gmatch('[^,]+') do
            -- v2.5.2: 2 to 4 numeric fields (ride-height points gained the
            -- axle's spring setting as a 4th; older points still read).
            local v = {}
            for field in pt:gmatch('[^:]+') do table.insert(v, tonumber(field)) end
            if v[1] and v[2] then table.insert(entry[axle], {v[1], v[2], v[3], v[4]}) end
          end
        end
      end
      all[car] = entry
    end
  end
  return all
end
local function serialisePointStore(all, keep)
  local blocks = {}
  for car, entry in pairs(all) do
    local axles = {}
    for _, axle in ipairs({'F', 'R'}) do
      local pts = {}
      local list = entry[axle] or {}
      for i = math.max(1, #list - keep + 1), #list do
        local p = list[i]
        table.insert(pts, string.format('%.4f:%.4f%s%s', p[1], p[2], p[3] and string.format(':%.2f', p[3]) or '',
          (p[3] and p[4]) and string.format(':%.4f', p[4]) or ''))
      end
      table.insert(axles, axle .. '=' .. table.concat(pts, ','))
    end
    table.insert(blocks, car .. '>' .. table.concat(axles, ';'))
  end
  table.sort(blocks)
  return table.concat(blocks, '|')
end

-- v2.5.2: what makes a ride-height calibration trustworthy. The direction
-- the bottoming raise and rake follow ("measured in the pits", v2.5.0) was
-- the SIGN of the median pair slope, accepted from 0.05 mm a click and one
-- pair - and pairs mixed spring settings, which move static height on
-- their own. The Sunbeam at Bathurst, 30 Sep, within ten minutes: +0.60
-- mm/click (1 pair), -0.09 (1 pair), +0.46 - so "raise" went 27->29,
-- 29->27, 27->29 on a car that was bottoming. Logged slopes ranged -0.78
-- to +8.95 mm/click. Now: pairs only at the same spring setting, at least
-- RIDE_CAL_MIN_PAIRS of them, all agreeing on the sign, and a median of at
-- least RIDE_CAL_MIN_SLOPE (below that a click is settling noise).
local RIDE_CAL_MIN_PAIRS = 2
local RIDE_CAL_MIN_SLOPE = 0.3

-- Ride-height calibration: points {setting, mm, fuel, spring}. One point
-- per setting value (latest wins). spring (v2.5.2) = that axle's spring
-- setting at the time, nil on a car without spring spinners.
function engine:rideCalRecord()
  if not self.carId or self.carId == '' then return end
  local ok, spinners = pcall(ac.getSetupSpinners)
  if not ok or type(spinners) ~= 'table' then return end
  local vals = {}
  for _, s in ipairs(spinners) do
    if type(s) == 'table' and type(s.name) == 'string' then vals[s.name] = tonumber(s.value) end
  end
  local fuel = 0
  pcall(function() fuel = n(ac.getCar(0).fuel, 0) end)
  local all = parsePointStore(settings.rideCal)
  local entry = all[self.carId] or {F = {}, R = {}}
  local function put(axle, v, mm, spring)
    if not v or not mm or mm <= 0 then return end
    local list = entry[axle]
    for i = #list, 1, -1 do if math.abs(list[i][1] - v) < 1e-6 then table.remove(list, i) end end
    table.insert(list, {v, mm, fuel, spring})
  end
  put('F', vals.ROD_LENGTH_LF or vals.RIDE_HEIGHT_LF, self.staticRideHeightF * 1000, vals.SPRING_RATE_LF)
  put('R', vals.ROD_LENGTH_LR or vals.RIDE_HEIGHT_LR, (self.staticRideHeightR or 0) * 1000, vals.SPRING_RATE_LR)
  all[self.carId] = entry
  settings.rideCal = serialisePointStore(all, 6)
end

-- mm of static ride height per stored click, from pairs at similar fuel
-- (within 5 L - fuel alone moves ride height about a millimetre) and, since
-- v2.5.2, the same spring setting. Median of the pairwise slopes. Returns
-- slope, pairsUsed, reliable (see RIDE_CAL_MIN_PAIRS).
function engine:rideCalSlope(axle)
  local all = parsePointStore(settings.rideCal)
  local list = (all[self.carId or ''] or {})[axle] or {}
  local slopes = {}
  for i = 1, #list do
    for j = i + 1, #list do
      local a, b = list[i], list[j]
      local fuelOk = (not a[3]) or (not b[3]) or math.abs(a[3] - b[3]) <= 5
      local springOk = (a[4] == nil and b[4] == nil) or (a[4] ~= nil and b[4] ~= nil and math.abs(a[4] - b[4]) < 1e-6)
      if fuelOk and springOk and math.abs(a[1] - b[1]) >= 1 then
        table.insert(slopes, (b[2] - a[2]) / (b[1] - a[1]))
      end
    end
  end
  if #slopes == 0 then return nil, 0, false end
  table.sort(slopes)
  local median = slopes[math.floor((#slopes + 1) / 2)]
  local agree = true
  for _, s in ipairs(slopes) do
    if s * median <= 0 then agree = false end
  end
  local reliable = #slopes >= RIDE_CAL_MIN_PAIRS and agree and math.abs(median) >= RIDE_CAL_MIN_SLOPE
  return median, #slopes, reliable
end

-- Mean and standard error of a regime's per-lap rate (events per 100
-- corners) across the window's clean laps. which = 'snap' | 'push', or
-- (v2.6.0) 'hits' with regime 'travelF' | 'travelR' - max-travel hits.
function engine:lapRateStats(regime, which)
  local travelKey = (which == 'hits') and ('springsHits' .. tostring(regime):sub(-1)) or nil
  local rates = {}
  for _, b in ipairs(windowBins(self)) do
    local corners = b.corneringSamples or 0
    if corners >= 5 then
      if travelKey then
        table.insert(rates, (b[travelKey] or 0) / corners * 100)
      else
        local p, s = regimeCounts(b, regime)
        table.insert(rates, (which == 'snap' and s or p) / corners * 100)
      end
    end
  end
  if #rates < 2 then return nil, nil, #rates end
  local sum = 0
  for _, r in ipairs(rates) do sum = sum + r end
  local mean = sum / #rates
  local ss = 0
  for _, r in ipairs(rates) do ss = ss + (r - mean) ^ 2 end
  local sd = math.sqrt(ss / (#rates - 1))
  return mean, sd / math.sqrt(#rates), #rates
end

-- Camber gain: points {settingDeg, loadedDeg} per axle, per car.
function engine:camberGainRecord(axle, settingDeg, loadedDeg)
  if not self.carId or self.carId == '' or not settingDeg or not loadedDeg then return end
  local all = parsePointStore(settings.camberGain)
  local entry = all[self.carId] or {F = {}, R = {}}
  table.insert(entry[axle], {settingDeg, loadedDeg})
  all[self.carId] = entry
  settings.camberGain = serialisePointStore(all, 6)
end

-- Least-squares d(loaded)/d(setting) once 3+ points span 0.3 deg; clamped
-- 0.5..2.0. nil = not known yet (gain 1 is assumed).
function engine:camberGain(axle)
  local all = parsePointStore(settings.camberGain)
  local list = (all[self.carId or ''] or {})[axle] or {}
  if #list < 3 then return nil, #list end
  local lo, hi, sx, sy = math.huge, -math.huge, 0, 0
  for _, p in ipairs(list) do
    lo, hi = math.min(lo, p[1]), math.max(hi, p[1])
    sx, sy = sx + p[1], sy + p[2]
  end
  if hi - lo < 0.3 then return nil, #list end
  local mx, my = sx / #list, sy / #list
  local num, den = 0, 0
  for _, p in ipairs(list) do
    num = num + (p[1] - mx) * (p[2] - my)
    den = den + (p[1] - mx) ^ 2
  end
  if den <= 0 then return nil, #list end
  return clamp(num / den, 0.5, 2.0), #list
end

-- Brake-bias one-shot, per car.
function engine:biasBaselineDone(carId)
  return tostring(settings.biasBaselineCars or ''):find('|' .. carId .. '|', 1, true) ~= nil
end
function engine:markBiasBaselineDone(carId)
  if self:biasBaselineDone(carId) then return end
  local s = tostring(settings.biasBaselineCars or '')
  if s == '' then s = '|' end
  settings.biasBaselineCars = s .. carId .. '|'
end

--------------------------------------------------------------------------------
-- v2.5.0: PHYSICS FINGERPRINT. A car id is not a physics version: the
-- Sunbeam went from v1 to v3 in one day under one id (rear axle, diff,
-- final drives, brakes), and the app carried everything it had learned
-- straight over - its one-time brake-bias write counted as used on the old
-- Escort brakes, the ride-height mm/click came from the old rear geometry,
-- the lever history and branch passes judged a different car. Every file
-- the app reasons from is hashed (every section, key and value, through
-- ac.INIConfig's `sections`), plus the final-drive list; when the hashes
-- differ from the ones stored for this car, what was learned about it is
-- reset and the next Build says so. A car seen for the first time only
-- has its fingerprint recorded. So adding dampers, bars or anything else
-- to a car in progress starts it with a clean slate, automatically.
--------------------------------------------------------------------------------
local PHYSICS_FILES = {'car.ini', 'suspensions.ini', 'setup.ini', 'brakes.ini', 'drivetrain.ini', 'tyres.ini', 'aero.ini', 'engine.ini'}
local PHYSICS_KEEP_CARS = 60

-- Two polynomial hashes, 16 hex chars. No bit operators: CSP runs LuaJIT,
-- where `~` is not an operator.
local function textHash(s)
  local h1, h2 = 0, 0
  for i = 1, #s do
    local b = s:byte(i)
    h1 = (h1 * 31 + b) % 4294967291
    h2 = (h2 * 131 + b) % 2147483647
  end
  return string.format('%08x%08x', h1, h2)
end

-- An INI file's parsed content in a fixed order (comments and formatting
-- don't count - only what the physics reads).
local function iniCanon(ini)
  local secs = ini and ini.sections
  if type(secs) ~= 'table' then return '' end
  local names = {}
  for name in pairs(secs) do table.insert(names, tostring(name)) end
  table.sort(names)
  local parts = {}
  for _, name in ipairs(names) do
    local sec = secs[name]
    if type(sec) == 'table' then
      local keys = {}
      for k in pairs(sec) do table.insert(keys, tostring(k)) end
      table.sort(keys)
      table.insert(parts, '[' .. name .. ']')
      for _, k in ipairs(keys) do
        local v = sec[k]
        table.insert(parts, k .. '=' .. (type(v) == 'table' and table.concat(v, ',') or tostring(v)))
      end
    end
  end
  return table.concat(parts, '\n')
end

-- "file:hash,file:hash,..." for a car's physics as loaded now.
local function physicsPrintOf(carIndex)
  local parts = {}
  for _, file in ipairs(PHYSICS_FILES) do
    local ok, ini = pcall(ac.INIConfig.carData, carIndex, file)
    local canon = ''
    if ok and ini then
      local okC, c = pcall(iniCanon, ini)
      canon = okC and c or ''
    end
    table.insert(parts, file .. ':' .. textHash(canon))
    if file == 'setup.ini' and ok and ini then
      local rto = iniStr(ini, 'FINAL_GEAR_RATIO', 'RATIOS')
      local pts = rto and lutPoints(carIndex, rto) or nil
      local ys = {}
      for _, p in ipairs(pts or {}) do table.insert(ys, string.format('%.4f', p.y)) end
      table.insert(parts, 'final.rto:' .. textHash(table.concat(ys, ',')))
    end
  end
  return table.concat(parts, ',')
end

-- Forget everything learned about one car (its physics changed).
function engine:forgetLearned(carId)
  settings.biasBaselineCars = tostring(settings.biasBaselineCars or ''):gsub('|' .. carId:gsub('%p', '%%%0') .. '|', '|')
  for _, key in ipairs({'rideCal', 'camberGain'}) do
    local all = parsePointStore(settings[key])
    all[carId] = nil
    settings[key] = serialisePointStore(all, 6)
  end
  self:leverHistoryReset(carId)  -- lever history, branch passes, pending moves
  settings.lastBuildRecord = keyedDropCar(settings.lastBuildRecord, carId)
  self.lastBuildWritten, self.lastBuildKey = nil, nil
end

function engine:checkPhysicsFingerprint(carIndex)
  local carId = self.carId or ''
  if carId == '' then return end
  local now = physicsPrintOf(carIndex)
  local stored, order = {}, {}
  for block in tostring(settings.physicsPrints or ''):gmatch('[^|]+') do
    local car, pr = block:match('^([^>]+)>(.*)$')
    if car then
      if not stored[car] then table.insert(order, car) end
      stored[car] = pr
    end
  end
  local before = stored[carId]
  for i = #order, 1, -1 do if order[i] == carId then table.remove(order, i) end end
  table.insert(order, carId)
  stored[carId] = now
  while #order > PHYSICS_KEEP_CARS do stored[table.remove(order, 1)] = nil end
  local blocks = {}
  for _, car in ipairs(order) do table.insert(blocks, car .. '>' .. stored[car]) end
  settings.physicsPrints = table.concat(blocks, '|')
  self.physicsPrint = now
  -- v2.5.2: "first time this car is seen" holds until a Build has reported
  -- it (the commit clears it) - a re-run for the same car (tyre change,
  -- RESET TELEMETRY's re-read) no longer turns it into "unchanged" before
  -- any Build said it, and a later Build in the same session no longer
  -- repeats it. Never carried over to another car.
  self.physicsFirstSeen = (before == nil) or (self.physicsFirstSeen == true and self.physicsSeenCar == carId)
  self.physicsSeenCar = carId
  if not before or before == now then return end
  local old, changed, listChanged = {}, {}, false
  for f, h in before:gmatch('([^:,]+):(%x+)') do old[f] = h end
  for f, h in now:gmatch('([^:,]+):(%x+)') do
    if old[f] ~= h then
      table.insert(changed, f)
      if f == 'final.rto' or f == 'setup.ini' then listChanged = true end
    end
  end
  self:forgetLearned(carId)
  self.physicsChangeNote = string.format('PHYSICS CHANGED on this car since the app last saw it (%s) - what was learned about the old version is reset: the one-time brake-bias write is re-armed, and ride-height calibration, camber gain, lever history, branch passes, pending lever moves and the last-Build record start again%s',
    #changed > 0 and table.concat(changed, ', ') or 'files differ',
    listChanged and '. Saved setups store some settings (final drive among them) as positions in the car\'s own lists - setups saved before the change may now load different values' or '')
end

-- Final drive (advice only - Build never changes gearing). The ratio that
-- puts rpm at the session's top speed at 97.5% of the limiter, and the
-- nearest option this car offers. Needs a top-speed run in top gear with
-- the fitted final read from physics. Returns a table or nil + why.
function engine:finalDriveTarget(limiterRpm)
  if not self.finalAtVmax or (self.rpmAtVmax or 0) <= 0 or not limiterRpm or limiterRpm < 4000 then
    return nil, 'no top-speed run with the fitted final drive read yet'
  end
  if (self.maxGearSeen or 0) > 0 and self.gearAtVmax ~= self.maxGearSeen then
    return nil, 'top speed was not reached in top gear'
  end
  local r = {cur = self.finalAtVmax, onLimiter = self.rpmAtVmax >= limiterRpm - 80}
  r.want = self.finalAtVmax * (0.975 * limiterRpm / self.rpmAtVmax)
  local opts, nOpt = self.finalOptions, self.finalOptionsN or 0
  if opts and nOpt > 1 then
    local bd, cd = math.huge, math.huge
    for i = 0, nOpt - 1 do
      if math.abs(opts[i] - r.cur) < cd then cd, r.curIdx = math.abs(opts[i] - r.cur), i end
      if math.abs(opts[i] - r.want) < bd then bd, r.bestIdx = math.abs(opts[i] - r.want), i end
    end
    if r.onLimiter then
      -- On the limiter at Vmax: how far past it the car wanted to go is not
      -- measurable, so the advice is the next LONGER option (lower ratio).
      local longer
      for i = 0, nOpt - 1 do
        if opts[i] < r.cur - 1e-4 and (not longer or opts[i] > opts[longer]) then longer = i end
      end
      r.bestIdx = longer or r.curIdx
    end
    r.bestRatio, r.n = opts[r.bestIdx], nOpt
  end
  return r
end

-- Calculated brake-bias target (% front torque), or nil + why.
function engine:biasTarget()
  local nS, zones = self.brkLoadN or 0, self.brkZones or 0
  if nS < 30 or zones < 4 then
    return nil, string.format('%d hard straight-line braking zones (%d samples) so far - needs 4 zones', zones, nS)
  end
  local x = self.brkLoadFSum / nS
  local rf, rr = self.tyreRadiusF, self.tyreRadiusR
  if not rf or not rr or rf <= 0 or rr <= 0 then rf, rr = 1, 1 end
  -- v2.5.0: GRIP, NOT LOAD. Each axle can stop with what its tyres grip at
  -- their loads, and AC tyres grip less per newton as load rises (see
  -- readTyreReference) - so the loaded front's share of the braking it can
  -- use is below its share of the load. The Sunbeam at the Nordschleife:
  -- 76.1% of the load, ~69% of the grip - and the fronts did lock first
  -- at 69%. Without the tyre's grip model: load alone, flagged as such.
  local capN = self.brkCapN or 0
  if capN >= 30 and (self.brkCapFSum or 0) > 0 and (self.brkCapRSum or 0) > 0 then
    local cf, cr = self.brkCapFSum / capN, self.brkCapRSum / capN
    local g = cf / (cf + cr)
    local equal = 100 * cf * rf / (cf * rf + cr * rr)
    local mf, mr = self.brakeModelF, self.brakeModelR
    local modelText = (mf and mf.kind == 'ls' and mr and mr.kind == 'ls')
      and string.format('load-sensitivity exponent %.2f F / %.2f R', mf.lsx, mr.lsx) or 'its load-sensitivity data'
    return equal + balanceMode().biasMargin, string.format('front carries %.1f%% of tyre load under hard braking (%d zones), but tyres grip less per kilo as load rises (%s), so the front can use %.1f%% of the braking -> both axles at the limit together at %.1f%% front, +%.0f%% stability margin = %.1f%%',
      x * 100, zones, modelText, g * 100, equal, balanceMode().biasMargin, equal + balanceMode().biasMargin)
  end
  -- v2.5.2: a car whose tyres HAVE a grip model never falls back to load
  -- alone - on the Sunbeam the two differ by 7% (77% vs 70%), and the
  -- fallback is exactly the number v2.5.0 established was wrong. Load
  -- alone is only for tyres with no model.
  if self.brakeModelF and self.brakeModelR then
    return nil, string.format('%d of %d hard-braking samples have the tyre grip model (needs 30)', capN, nS)
  end
  local equal = 100 * x * rf / (x * rf + (1 - x) * rr)
  return equal + balanceMode().biasMargin, string.format('front carries %.1f%% of tyre load under hard braking (%d zones) -> both axles at the limit together at %.1f%% front, +%.0f%% stability margin = %.1f%% (load only - this tyre states no load-sensitivity data, so the real balance point may sit a little further back)',
    x * 100, zones, equal, balanceMode().biasMargin, equal + balanceMode().biasMargin)
end

-- The gate's numbers, one place: (passes, cleanLaps, pitLaps, partialLaps,
-- invalidLaps, minLaps, corners).
function engine:buildEvidence()
  local clean, pit, partial, invalid = windowLapStats(self)
  local minLaps = clamp(math.floor(n(settings.buildMinLaps, 2)), 1, 5)
  local corners = self.corneringSamples or 0
  local passes = clean >= minLaps and corners >= BUILD_MIN_CORNERS
  return passes, clean, pit, partial, invalid, minLaps, corners
end

-- Debug-log lines for the evidence window, the per-lap bins, and the lap
-- consistency of every signal a writer acts on. Written for BOTH a
-- declined and a completed Build so the two can be compared.
function engine:evidenceLogLines(th)
  local passes, clean, pit, partial, invalid, minLaps, corners = self:buildEvidence()
  local lines = {}
  -- v2.5.0: on a long track the units are sections of a lap (LONG TRACKS).
  local unitsKey = (self.unitsPerLap or 1) > 1 and 'sections' or 'laps'
  table.insert(lines, string.format('evidence: window since %s%s · %s: clean=%d pit=%d partial=%d (invalid-flagged %d)%s · corners=%d · gate: %d clean %s and %d corners -> %s',
    tostring(self.windowLabel or 'session start'), self.windowStartedAt and (' @' .. self.windowStartedAt) or '',
    unitsKey, clean, pit, partial, invalid, longTrackNote(self), corners, minLaps, unitWord(minLaps), BUILD_MIN_CORNERS,
    passes and 'PASS' or 'DECLINED'))
  -- Per-unit bins in the window (last 8), most recent last.
  local parts = {}
  local first = math.max((self.windowBinsStart or 0) + 1, #self.lapBins - 7)
  for i = first, #self.lapBins do
    local b = self.lapBins[i]
    local flags = (b.pit and 'P' or '') .. (b.partial and '~' or '') .. (b.valid == false and 'X' or '')
    table.insert(parts, string.format('L%s%s[c%d push %d/%d hi %d/%d held %d tin %d rtoe %d lk %d/%d bot %d dmp %d/%d|%d/%d dif %d/%d]',
      b.unit and string.format('%d.%d', b.lap, b.unit) or tostring(b.lap), flags ~= '' and ('(' .. flags .. ')') or '', b.corneringSamples or 0,
      b.midPush or 0, b.midSnap or 0, b.highPush or 0, b.highSnap or 0, b.heldSlides or 0, b.turninPush or 0, b.rearToeEvents or 0,
      b.lockF or 0, b.lockR or 0, b.bottoming or 0,
      b.dampBumpF or 0, b.dampRebF or 0, b.dampBumpR or 0, b.dampRebR or 0,
      b.diffRotationEvents or 0, b.diffEvents or 0))
  end
  table.insert(lines, unitsKey .. ': ' .. (#parts > 0 and table.concat(parts, ' ') or 'none banked in this window yet') .. '  (L3.2 = lap 3 section 2 on a long track; P=pit, ~=partial, X=invalid; push/snap = push/oversteer, hi = high-speed, held = deliberate slides (not oversteer), tin = turn-in push, rtoe = rear instability, lk = lockups F/R, dmp = bump/reb F|R, dif = forced-together/diverging)')
  -- Consistency of each acted-on signal across the window's clean laps.
  local lowV, _, _, lowN, _, lowA, lowC = regimeVerdict(self, 'low', th)
  local highV, _, _, highN, _, highA, highC = regimeVerdict(self, 'high', th)
  local rearV, _, _, rearN, rearA, rearC = rearHandlingSignal(self, th)
  local function sup(key) local a, c = lapSupport(self, key); return string.format('%d/%d', a, c) end
  table.insert(lines, string.format('consistency (>= half the clean %s must agree): low=%s %d/%d · high=%s %d/%d · rear=%s %d/%d · lockF %s lockR %s turnin %s rearToe %s bottoming %s diffRot %s diffDiv %s',
    EV_UNIT.many, lowV or lowN or 'neutral', lowA, lowC, highV or highN or 'neutral', highA, highC, rearV or rearN or 'neutral', rearA, rearC,
    sup('lockF'), sup('lockR'), sup('turninPush'), sup('rearToeEvents'), sup('bottoming'), sup('diffRotationEvents'), sup('diffEvents')))
  return lines
end

-- v1.9.7: a failed log write is no longer silent. A Build on 2026-09-18
-- left a setup file with no matching log entry and it took real detective
-- work (Content Manager's own logs, file timestamps) to establish the
-- Build had never been pressed at all. Now any failure here is appended to
-- setupMsg so the UI says it, and the reason is kept for the next log.
function engine:writeDebugLog(lines)
  local function fail(why)
    self.debugLogError = why
    if self.setupMsg then self.setupMsg = self.setupMsg .. ' [debug log NOT written: ' .. why .. ']' end
  end
  local root = findDocsRoot()
  if not root or root == '' then return fail('Documents folder not found') end
  local path = root .. '/SetupCoach_Notes/debug_log.txt'
  local f, err = io.open(path, 'a')
  if not f then return fail(tostring(err)) end
  local okDate, dateStr = pcall(os.date, '%Y-%m-%d %H:%M:%S')
  local okWrite, werr = pcall(function()
    f:write('==== ' .. (okDate and dateStr or '?') .. ' ====\n')
    if self.debugLogError then
      f:write('(previous Build\'s log write failed: ' .. tostring(self.debugLogError) .. ')\n')
      self.debugLogError = nil
    end
    for _, l in ipairs(lines) do f:write(tostring(l) .. '\n') end
    f:write('\n')
  end)
  f:close()
  if not okWrite then fail(tostring(werr)) end
end

function engine:export()
  local root = findDocsRoot()
  if not root or root == '' then
    self.exportMsg = 'ERROR: cannot find Documents folder'
    return false
  end

  local notesDir = root .. '/SetupCoach_Notes'
  local filepath = notesDir .. '/pit_notes.txt'

  -- Append with a timestamped session separator instead of overwriting.
  -- Confirmed a real gap by checking the original Python prototype this
  -- project grew from: it appended every save with a header, building up
  -- a genuine history across a test day. Our Lua version was silently
  -- overwriting the file on every press - the SAME bug in spirit as
  -- SetupCoach_Notes/pit_notes.txt already showed in practice, where an
  -- old session (a completely different car, f302_fer_f360_gt) was the
  -- only thing ever preserved because nothing since had been saved twice
  -- in the same session without wiping the prior save.
  local file, err = io.open(filepath, 'a')
  if not file then
    self.exportMsg = 'ERROR writing notes'
    return false
  end

  local okDate, dateStr = pcall(os.date, '%Y-%m-%d %H:%M:%S')
  local lines = {
    '',
    '======================================',
    'SETUP COACH PIT NOTES - ' .. (okDate and dateStr or 'unknown time'),
    '======================================',
    string.format('Car: %s | Compound: %s', self.carId, self.compound),
    string.format('Samples: %d | Laps: %d', self.samples, self.completedLaps),
    string.format('Pressures FL: %.1f | FR: %.1f | RL: %.1f | RR: %.1f', self.livePressFL, self.livePressFR, self.livePressRL, self.livePressRR),
    '',
    '--- ADVICE ---',
  }
  for i = 1, #self.lastAdvice do
    local a = self.lastAdvice[i]
    table.insert(lines, string.format('[%s] %s  %s', string.upper(a.status), a.id, a.text))
  end

  if self.setupChanges and #self.setupChanges > 0 then
    table.insert(lines, '')
    table.insert(lines, '--- LAST OPTIMAL SETUP BUILD (' .. tostring(self.setupOutPath) .. ') ---')
    for i = 1, #self.setupChanges do
      table.insert(lines, self.setupChanges[i])
    end
  end

  file:write(table.concat(lines, '\n'))
  file:close()

  self.exportMsg = 'Pit notes saved'
  pcall(ac.setMessage, 'Setup Coach', 'Pit notes saved')
  return true
end

-- Builds a complete, loadable setup .ini from live telemetry + (optionally)
-- an existing saved setup as the numeric baseline. See the file header for
-- exactly what is and isn't safe to auto-write and why.
-- Damper histogram verdict for one end ('F' | 'R'), window totals plus the
-- same lap-consistency rule as every other verdict. share = bump time /
-- moving time. Over a lap the wheel goes up as far as it comes down, so the
-- side with LESS of the time is the faster-moving, under-damped side:
-- share < DAMPER_HIST_SHARE_LO -> 'bumpSoft', > _HI -> 'rebSoft'.
-- Ceilings stop a damping ratio being pushed past what costs grip.
local DAMPER_HIST_SHARE_LO, DAMPER_HIST_SHARE_HI = 0.44, 0.56
local DAMPER_HIST_MIN_S = 20
local ZETA_CEIL_BUMP, ZETA_CEIL_REBOUND = 1.25, 1.80
local function damperHistShare(src, e)
  local bt = (src['dhSlowBump' .. e] or 0) + (src['dhFastBump' .. e] or 0)
  local rt = (src['dhSlowReb' .. e] or 0) + (src['dhFastReb' .. e] or 0)
  if bt + rt <= 0 then return nil, 0, 0 end
  local slow = (src['dhSlowBump' .. e] or 0) + (src['dhSlowReb' .. e] or 0)
  return bt / (bt + rt), bt + rt, slow / (bt + rt)
end
local function damperHistSide(share)
  if not share then return nil end
  if share < DAMPER_HIST_SHARE_LO then return 'bumpSoft' end
  if share > DAMPER_HIST_SHARE_HI then return 'rebSoft' end
  return nil
end
function engine:damperHistVerdict(e)
  local share, total, slowShare = damperHistShare(self, e)
  local out = {share = share, total = total, ceilBump = ZETA_CEIL_BUMP, ceilRebound = ZETA_CEIL_REBOUND}
  if not share or total < DAMPER_HIST_MIN_S then
    out.text = string.format('damper histogram %s: %.0f s of wheel movement measured, needs %d', e, total or 0, DAMPER_HIST_MIN_S)
    return out
  end
  out.measured = true
  local v = damperHistSide(share)
  local bins = windowBins(self)
  local agree = 0
  for _, bin in ipairs(bins) do
    if v and damperHistSide((damperHistShare(bin, e))) == v then agree = agree + 1 end
  end
  local txt = string.format('damper histogram %s: bump %.0f%% / rebound %.0f%% of the moving time (even = %.0f-%.0f%%), %.0f%% below the %.3f m/s slow/fast knee, %.0f s',
    e, share * 100, (1 - share) * 100, DAMPER_HIST_SHARE_LO * 100, DAMPER_HIST_SHARE_HI * 100, slowShare * 100, damperKnee(self), total)
  if v and #bins >= 2 and agree * 2 < #bins then
    txt = txt .. string.format(' - only %d of %d %s agree, not consistent', agree, #bins, EV_UNIT.many)
    v = nil
  elseif v == 'bumpSoft' then
    txt = txt .. ' - bump side moves faster: bump soft for its rebound'
  elseif v == 'rebSoft' then
    txt = txt .. ' - rebound side moves faster: rebound soft for its bump'
  else
    txt = txt .. ' - even'
  end
  out.verdict, out.text = v, txt
  return out
end

-- The balance mode, as a method so the Build function reads it through self.
function engine:balanceModeNow() return balanceMode() end

function engine:buildOptimalSetup()
  local car = ac.getCar(0)
  if not car then
    self.setupMsg = 'No car loaded'
    return false
  end

  self:refreshSchema(car)
  local schema = self.schema or {}
  -- A car with encrypted/protected data can make ac.INIConfig.carData return
  -- almost nothing here even though the read itself didn't error - pressure
  -- and camber get a generic fallback range below specifically to survive
  -- that case, so we no longer hard-bail just because `schema` is sparse.
  local schemaLimited = not next(schema)
  local schemaCategoryCount = 0
  for _ in pairs(schema) do schemaCategoryCount = schemaCategoryCount + 1 end

  local carFolder = self.carId
  if carFolder == '' then
    self.setupMsg = 'Unknown car id'
    return false
  end
  local trackFolder = getTrackFolder()
  local dir = setupsDir(carFolder, trackFolder)
  if not dir then
    self.setupMsg = 'ERROR: cannot find Documents/Assetto Corsa folder'
    return false
  end

  -- v2.0.0: THE EVIDENCE GATE. Nothing is written until the window holds
  -- enough clean laps and corners - see the block comment above
  -- BUILD_MIN_CORNERS. A declined Build still writes a log entry with the
  -- full evidence block so "why didn't it build" is answerable, and nothing
  -- is consumed, so the next press sees everything this one did plus what
  -- was driven in between.
  local gateOverridden = false
  do
    local gateTh = math.max(1, math.floor(n(settings.threshold, 2)))
    local passes, clean, pit, partial, invalid, minLaps, corners = self:buildEvidence()
    if not passes and self.gateOverrideOnce then
      -- v2.1.0: one-shot test override from the main window button.
      passes, gateOverridden = true, true
    end
    self.gateOverrideOnce = false
    if not passes then
      local need = {}
      -- v2.5.0: laps, or sections of a lap on a long track.
      if clean < minLaps then table.insert(need, string.format('%d more clean %s', minLaps - clean, unitWord(minLaps - clean))) end
      if corners < BUILD_MIN_CORNERS then table.insert(need, string.format('%d more corners', BUILD_MIN_CORNERS - corners)) end
      self.setupMsg = string.format('Build declined - not enough evidence yet: %d clean %s and %d corners since %s (need %d %s / %d corners)%s. Drive %s, then Build.%s',
        clean, unitWord(clean), corners, tostring(self.windowLabel or 'session start'),
        minLaps, unitWord(minLaps), BUILD_MIN_CORNERS, longTrackNote(self), table.concat(need, ' and '),
        (pit + partial > 0) and string.format(' [%d pit / %d partial %s not counted]', pit, partial, unitWord(pit + partial)) or '')
      self.setupChanges = {}
      local logLines = {
        string.format('car=%s track=%s (v%s)', carFolder, trackFolder, VERSION),
      }
      for _, l in ipairs(self:evidenceLogLines(gateTh)) do table.insert(logLines, l) end
      table.insert(logLines, 'result: DECLINED - ' .. self.setupMsg)
      self:writeDebugLog(logLines)
      return false
    end
  end

  -- Template setup: found AUTOMATICALLY now (4.3.0). No Settings entry, no
  -- name to type, no gate. See findTemplateSetup above for the search order.
  -- The template is what makes ARB/springs/dampers/toe/etc. writable on cars
  -- whose data/setup.ini is encrypted: a real current value is all we need
  -- to nudge from, and last.ini always has one.
  local parsed, usedBase, templateLabel = findTemplateSetup(carFolder, trackFolder, settings.baseSetupName)
  if not parsed then
    parsed = {lines = {}, valueLineIdx = {}}
    templateLabel = 'none found'
  end

  -- v1.8.0: overwrite the template's values with the car's ACTUAL current
  -- setup wherever it can be read (see readLiveSetupSpinners). Doing it here,
  -- straight into `parsed`, is deliberate: every writer below already reads
  -- its starting value via getCurVal(parsed, section), so this single sync
  -- makes ALL of them nudge from what's really on the car - no call site
  -- changes, nothing to keep in step. It also means any section nobody
  -- writes (an unticked module) carries the live value into the output
  -- rather than a stale file's, which is what "leave that module alone"
  -- was always supposed to mean.
  --
  -- readOnly spinners are skipped - those are values the game won't let the
  -- driver change anyway, so writing them into a setup file is pointless at
  -- best. If the live read is unavailable or failed its consistency guard,
  -- nothing happens here and the old template values stand exactly as before.
  --
  -- v2.1.1: UNMANAGED SECTIONS ARE PRESERVED FROM LIVE, NOT LEFT STALE.
  -- The output file is a full copy of the template with the managed values
  -- patched - so every section it contains is APPLIED when the driver loads
  -- it, whether this app reasons about that section or not. v1.8.1 stopped
  -- SYNCING the unmanaged ones (correct: no writer may touch gearing), but
  -- that left them at whatever the template file happened to hold, and the
  -- template is last.ini - written only when a session ENDS. Anything set
  -- in the setup screen before driving (tyre compound, final drive, TC,
  -- fuel) is therefore missing from it, and loading the Build reverted the
  -- driver's choices to the stale file's. Confirmed exactly, Huracan GT3
  -- 2026-09-22: written FINAL_RATIO=6 (3.9166, the car's DEFAULT) against a
  -- live/driven 3 (4.5000), and TYRES=1 against a live 0 - the compound the
  -- same log's tyreDataSrc had correctly read as [FRONT] "Slick Soft".
  --
  -- The distinction that was missing: WRITING a section (a writer choosing
  -- a new value) versus CARRYING it (the file stating what is already on
  -- the car). Unmanaged sections are now carried - synced from the live
  -- spinner like everything else - but with one hard rule kept from
  -- v1.8.1's other finding: NEVER ADD a section the template doesn't
  -- already have. v1.8.0 invented an INTERNAL_GEAR_1 the driver's setup
  -- never contained; ensureSectionValue appends when a section is missing,
  -- which is right for a managed value and wrong for an unmanaged one.
  -- Writers are still gated by MANAGED_SECTIONS, so gearing still has no
  -- writer - it simply now survives a Build instead of being reset.
  local liveSetup, liveNote = readLiveSetupSpinners()
  -- v2.5.1: CSP names the gear spinners one below the saved file (see
  -- alignLiveGearNames) - renamed here, before anything looks them up.
  liveSetup, liveNote = alignLiveGearNames(liveSetup, parsed, liveNote)
  local liveSynced, liveSkippedReadOnly, liveCarried, liveUnmanagedAbsent = 0, 0, 0, 0
  local carriedSamples = {}
  local liveFuelNote = ''
  if liveSetup then
    for section, it in pairs(liveSetup) do
      local looksInteger = math.abs(it.value - math.floor(it.value + 0.5)) < 1e-6
      local text = string.format(looksInteger and '%.0f' or '%.3f', it.value)
      if it.readOnly then
        liveSkippedReadOnly = liveSkippedReadOnly + 1
      elseif MANAGED_SECTIONS[section] then
        ensureSectionValue(parsed, section, text)
        liveSynced = liveSynced + 1
      elseif CARRY_EXCLUDE[section] then
        -- FUEL only. Every other unmanaged spinner describes the CAR; fuel
        -- describes the stint, and it is not yet established whether this
        -- API reports the setup's starting fuel or the tank right now. A
        -- live-tank reading carried into a setup file would write a
        -- part-empty tank as someone's race fuel, so it keeps the template
        -- value until a log settles which it is - both are printed below.
        liveFuelNote = string.format(' · FUEL not carried: template %s vs live %s (settling whether this reads the setup or the tank)',
          tostring(getCurVal(parsed, section) or 'n/a'), text)
      elseif parsed.valueLineIdx[section] then
        -- Unmanaged but present in the template: carry the LIVE value so
        -- loading this file leaves it exactly as the driver set it.
        local before = getCurVal(parsed, section)
        ensureSectionValue(parsed, section, text)
        liveCarried = liveCarried + 1
        if before and math.abs(before - it.value) > 1e-6 and #carriedSamples < 4 then
          table.insert(carriedSamples, string.format('%s %s->%s', section, tostring(before), text))
        end
      else
        -- Unmanaged and NOT in the template: left out entirely rather than
        -- invented (the v1.8.0 INTERNAL_GEAR_1 lesson).
        liveUnmanagedAbsent = liveUnmanagedAbsent + 1
      end
    end
  end
  -- Cross-check the compound against the game's own fitted-compound index
  -- (the one readTyreReference uses). If the TYRES section and
  -- car.compoundIndex disagree, the file would change compound on load.
  local compoundCheck = ''
  do
    local tyresVal = getCurVal(parsed, 'TYRES')
    local idx = nil
    pcall(function() idx = tonumber(car.compoundIndex) end)
    if tyresVal and idx and idx >= 0 then
      if math.abs(tyresVal - idx) > 1e-6 then
        compoundCheck = string.format(' · ⚠ TYRES=%s but the car is running compound %d - corrected to %d', tostring(tyresVal), idx, idx)
        ensureSectionValue(parsed, 'TYRES', string.format('%d', idx))
      else
        compoundCheck = string.format(' · compound %d confirmed against the car', idx)
      end
    end
  end

  -- v2.2.0: which section each corner / bar really uses on THIS car -
  -- vanilla or CSP LUT - by presence in the live setup or the template.
  -- Resolved per corner, not per car: gt4_bmw_m4 has DAMP_BUMP_LF (vanilla
  -- strut front) and DAMPER_BUMP_LR (LUT rear); gt4_audi_r8 has a LUT
  -- front bar and a vanilla rear one. Vanilla wins a tie so a car that
  -- somehow carried both keeps its old behaviour.
  local function sectionPresent(sec)
    return (liveSetup and liveSetup[sec] ~= nil) or parsed.valueLineIdx[sec] ~= nil
  end
  local function firstPresent(a, b)
    if sectionPresent(a) then return a end
    if sectionPresent(b) then return b end
    return nil
  end
  local function damperSection(kind, corner)
    return firstPresent('DAMP_' .. kind .. '_' .. corner, 'DAMPER_' .. kind .. '_' .. corner)
      or ('DAMP_' .. kind .. '_' .. corner)
  end
  local arbFSection = firstPresent('ARB_FRONT', 'ARB_F')
  local arbRSection = firstPresent('ARB_REAR', 'ARB_R')
  self.suspensionModel = {
    dampF = firstPresent('DAMP_BUMP_LF', 'DAMPER_BUMP_LF'),
    dampR = firstPresent('DAMP_BUMP_LR', 'DAMPER_BUMP_LR'),
    arbF = arbFSection, arbR = arbRSection,
  }

  -- v2.0.0: was the PREVIOUS Build's setup actually loaded? The live
  -- spinners say what is on the car now; lastBuildWritten says what the
  -- last Build wrote. If they differ on most managed sections, this
  -- window's telemetry was driven on some other setup and the log should
  -- say so before anyone reads the numbers as a response to that Build.
  local lastBuildLoadedLine = 'lastBuildLoaded: n/a (no previous Build recorded for this car at this track)'
  local lastBuildLoadedVerdict = nil
  -- v2.0.1: after an app reload the in-memory record is gone; restore it
  -- from storage when it belongs to this car.
  -- v2.5.0: ...and this TRACK (PER CAR + TRACK RECORDS) - a Build at another
  -- track wrote that track's setup, which says nothing about this one.
  local restoredNote = ''
  local buildKey = carFolder .. '>' .. trackFolder
  if self.lastBuildKey ~= buildKey then self.lastBuildWritten = nil end
  if not self.lastBuildWritten then
    local list, legacy = parseKeyedStore(settings.lastBuildRecord)
    if legacy then
      local recCar, recAt, rest = legacy:match('^([^|]*)|([^|]*)|?(.*)$')
      if recCar and recCar == carFolder and rest and rest ~= '' then
        self.lastBuildWritten = {}
        for pair in rest:gmatch('[^|]+') do
          local sec, v = pair:match('^([^=]+)=(.+)$')
          if sec and tonumber(v) then self.lastBuildWritten[sec] = tonumber(v) end
        end
        self.lastBuildAt = recAt
        restoredNote = ' [restored from storage after app reload; recorded before tracks were kept, so it may be another track\'s]'
      end
    else
      local rec = keyedGet(list, carFolder, trackFolder)
      local recAt, rest = nil, nil
      if rec then recAt, rest = tostring(rec.payload or ''):match('^([^;]*);(.*)$') end
      if recAt and rest and rest ~= '' then
        self.lastBuildWritten = {}
        for pair in rest:gmatch('[^,]+') do
          local sec, v = pair:match('^([^=]+)=(.+)$')
          if sec and tonumber(v) then self.lastBuildWritten[sec] = tonumber(v) end
        end
        self.lastBuildAt = recAt
        restoredNote = ' [restored from storage after app reload]'
      end
    end
    self.lastBuildKey = buildKey
  end
  if self.lastBuildWritten and liveSetup then
    local same, differ, examples = 0, 0, {}
    for section, wrote in pairs(self.lastBuildWritten) do
      local it = liveSetup[section]
      if it and it.value then
        if math.abs(it.value - wrote) < 1e-6 then same = same + 1
        else
          differ = differ + 1
          if #examples < 3 then table.insert(examples, string.format('%s live %s vs written %s', section, tostring(it.value), tostring(wrote))) end
        end
      end
    end
    if same + differ > 0 then
      local verdict = (differ == 0) and 'YES' or ((differ * 2 > same + differ) and 'NO' or 'PARTLY')
      lastBuildLoadedVerdict = verdict
      lastBuildLoadedLine = string.format('lastBuildLoaded: %s - %d/%d sections match the previous Build (%s)%s%s',
        verdict, same, same + differ, tostring(self.lastBuildAt or '?'),
        differ > 0 and (' · differs: ' .. table.concat(examples, '; ')) or '', restoredNote)
    end
  end

  -- REAR REBOUND EXPERIMENT snapshot, v1.9.2. Must be taken HERE - right
  -- after the live sync settles `parsed` to what the driver actually ran,
  -- and BEFORE any writer below can touch it - not down in logLines where
  -- this used to live. That read `parsed` after every writer had already
  -- run, so a session where the app stiffened rear rebound logged the
  -- WRITTEN value ("28") as "rearRebound(as driven)" - the exact thing this
  -- line exists to avoid conflating. Caught from a real tester's log: the
  -- Build wrote 24->28 and the experiment line reported 28 as driven,
  -- silently corrupting the one row that session contributed to answering
  -- the rebound-direction question. (v1.9.1's in-game tooltip evidence has
  -- since answered that question directly - see CLAUDE.md - but the line
  -- stays for now to keep collecting real per-session data alongside it.)
  local rearReboundAsDriven = {
    rebLR = getCurVal(parsed, damperSection('REBOUND', 'LR')),
    rebRR = getCurVal(parsed, damperSection('REBOUND', 'RR')),
    bumpLR = getCurVal(parsed, damperSection('BUMP', 'LR')),
  }

  -- Schema lookups, now preferring the live setup's OWN min/max/step over
  -- anything read from setup.ini or baked in. Two wins: cars whose data
  -- can't be read (schemaLimited, previously the unclamped percentage-nudge
  -- path that let values walk far past their real limits) get real clamping
  -- for the first time, and cars that DO have a baked schema get their
  -- numbers checked against the game's own rather than a decrypt done weeks
  -- ago. Live entries are copied into fresh tables so the shared
  -- self.schema items are never mutated by a Build.
  local function schemaWithLive(schemaList)
    local map = schemaBySection(schemaList)
    if not liveSetup then return map end
    for section, it in pairs(liveSetup) do
      if it.min and it.max and it.max > it.min then
        local existing = map[section]
        map[section] = {
          section = section,
          min = it.min,
          max = it.max,
          step = (it.step and it.step > 0) and it.step or (existing and existing.step) or 1,
          label = (existing and existing.label) or section,
          indexBased = existing and existing.indexBased or nil,
          -- v1.9.9: the spinner can't say where zero is in a click index;
          -- the setup.ini reader can (see readSetupItem). Carried through.
          zero = existing and existing.zero or nil,
          -- v2.3.0: physical-value conversion data from setup.ini.
          raw = existing and existing.raw or nil,
        }
      end
    end
    return map
  end

  local changes = {}
  -- v2.5.0: say first when this car's physics changed (PHYSICS FINGERPRINT).
  if self.physicsChangeNote then table.insert(changes, self.physicsChangeNote) end
  -- v2.5.0: sections a writer wanted that this car's setup simply doesn't
  -- have (one summary line at the end, not a SKIPPED line per write - the
  -- Sunbeam logged ~20 a Build for dampers, rear toe and rear camber it has
  -- no adjustment for), and calculated targets the car's own range stopped
  -- short (worth knowing when you build the car: widen the range).
  local absentSections = {}
  local rangeLimits = {}
  local th = math.max(1, math.floor(n(settings.threshold, 2)))
  local cap = 2
  local function steps(count) return clamp(math.floor(count / th), 1, cap) end
  -- v2.6.0: the Build-wide bottoming gate (v1.7.0 bottomTh, v2.0.0 lap
  -- support on the vertical-G `bottoming` count) is gone with the writers
  -- it gated. Each end's bottoming chain runs on its own lap-consistent
  -- travel signal (travelSignal) and says so when the hits are on too few
  -- laps; the floor-clearance step measures the floor itself.
  -- v2.1.0: judge the levers the previous Build moved against THIS window
  -- (before any writer touches anything), so a frozen lever is frozen
  -- before its chain runs.
  local effectLine = self:judgePendingLevers(carFolder, th, lastBuildLoadedVerdict, trackFolder)

  -- Pressures: AC's setup VALUE for pressure is a "cold" (garage) fill that
  -- rises as the tyre heats up on track. The math to get the right cold
  -- fill for a desired HOT target, in order of preference:
  --
  --   1) DELTA FROM BASE FILE (used whenever a base setup file is given).
  --      This is straight target-minus-current, applied as a signed delta
  --      to the base file's cold-fill value:
  --          new_cold = base_cold + (hot_target - current_hot)
  --      Worked example, real numbers from an actual debug log:
  --          base_cold = 23, current_hot = 31.9, target = 26
  --          -> 23 + (26 - 31.9) = 17.1 psi cold fill
  --      Physical sanity check: 23 -> 31.9 is a real observed rise of
  --      +8.9 psi on this exact car/track/session. To land at 26 hot
  --      instead we need 26 - 8.9 = 17.1 cold. Same answer. This works
  --      because a cold-fill change translates roughly 1-for-1 into a
  --      hot-reading change (the tyre still rises by ~the same amount),
  --      which is exactly how a real engineer does this: "we're 6 psi over
  --      target - take 6 psi out."
  --   2) DELTA FROM TARGET (no base file - can't do (1) without one).
  --      Same reasoning inverted: instead of "how far off is the current
  --      value's OUTPUT?" we ask "if a live reading of L hot corresponds
  --      to whatever cold fill produced it, and target T is (L - T) psi
  --      below that, then a cold fill of T - (L - T) = 2T - L would land
  --      us on target." Uses the same target-minus-current gap, just
  --      expressed as an absolute cold fill instead of a delta. Falls back
  --      to target - configured-rise only when no live reading exists yet
  --      (e.g. haven't left the pits at all).
  -- v1.9.6: pressure was the one writer still clamping against the file
  -- schema alone. Fresh copies (never mutate self.schema), then the live
  -- spinner's own min/max/step overlaid - same priority every other module
  -- gets via schemaWithLive: spinner > setup.ini > baked > generic.
  local pressureItems = {}
  for _, it in ipairs(schema.pressure or {}) do
    table.insert(pressureItems, {section = it.section, corner = it.corner, min = it.min, max = it.max, step = it.step})
  end
  if #pressureItems == 0 then
    pressureItems = genericItems({
      {section = 'PRESSURE_LF', corner = 'LF'}, {section = 'PRESSURE_RF', corner = 'RF'},
      {section = 'PRESSURE_LR', corner = 'LR'}, {section = 'PRESSURE_RR', corner = 'RR'},
    }, GENERIC_PRESSURE_RANGE)
  end
  if liveSetup then
    for _, it in ipairs(pressureItems) do
      local live = liveSetup[it.section]
      if live and live.min and live.max and live.max > live.min then
        it.min, it.max = live.min, live.max
        if live.step and live.step > 0 then it.step = live.step end
      end
    end
  end
  local pressureMethod = 'target - live delta (no base file)'
  if not settings.writePressures then
    pressureMethod = 'disabled (module unticked)'
    table.insert(changes, 'Pressures: SKIPPED (module disabled in Settings)')
  end
  if settings.writePressures then
    local hotByCorner = {LF = self.targetF, RF = self.targetF, LR = self.targetR, RR = self.targetR}
    local liveByCorner = {LF = self.livePressFL, RF = self.livePressFR, LR = self.livePressRL, RR = self.livePressRR}
    local peakByCorner = {LF = self.peakPressFL, RF = self.peakPressFR, LR = self.peakPressRL, RR = self.peakPressRR}
    local genericRise = n(settings.psiRise, 3)

    for _, it in ipairs(pressureItems) do
      local hot = hotByCorner[it.corner]
      if hot and hot > 0 then
        -- v2.5.2: the value on the car, from the template OR the live sync.
        -- This read "template only" (it predates v1.8.0's live sync), so a
        -- car with no setup file ignored the live pressure: Huracan GT3
        -- Evo2, Imola, 2 Oct - live 18 psi, hot 23.5 vs 26 -> wrote 28.5
        -- cold ("no base file"), next window 33-37 hot. Now 18 + 2.5 = 20.5.
        local baseVal = getCurVal(parsed, it.section)
        -- Prefer this session's peak hot reading over the current live
        -- one - the peak reflects real driving-induced heat, the live
        -- number could be a still-cooling reading from just after boxing.
        local peak = peakByCorner[it.corner]
        local live = liveByCorner[it.corner]
        local currentHot = (peak and peak > 5) and peak or live
        local newV, note
        if baseVal and currentHot and currentHot > 5 then
          -- Method 1: delta from base.
          local delta = hot - currentHot
          newV = clamp(baseVal + delta, it.min, it.max)
          note = string.format('base %s, hot ran %.1f, target %.1f, so delta %+.1f -> cold %.1f',
            tostring(baseVal), currentHot, hot, delta, newV)
          -- v2.0.1: say when the car's own limit bound. Real Huracan log:
          -- rears ran 29.7 / 29.9 hot against a 26 target with cold already
          -- at the 15 psi minimum - three Builds wrote "-> cold 15.0" as if
          -- that were the answer. It is the floor; the heat is from the
          -- rear sliding, and pressure can't fix that.
          if baseVal + delta < it.min - 1e-6 then
            note = note .. string.format(' [CLAMPED at this car\'s minimum %.0f - wanted %.1f; this much heat is coming from sliding, not pressure - fix the balance first]', it.min, baseVal + delta)
            table.insert(rangeLimits, string.format('pressure %s wants %.1f cold, the car stops at %.0f', it.corner, baseVal + delta, it.min))  -- v2.5.0
          elseif baseVal + delta > it.max + 1e-6 then
            note = note .. string.format(' [CLAMPED at this car\'s maximum %.0f - wanted %.1f]', it.max, baseVal + delta)
            table.insert(rangeLimits, string.format('pressure %s wants %.1f cold, the car stops at %.0f', it.corner, baseVal + delta, it.max))  -- v2.5.0
          end
          pressureMethod = 'delta from base setup + this session\'s peak hot reading'
        elseif currentHot and currentHot > 5 then
          -- Method 2: no base, but we have a live/peak reading.
          newV = clamp(2 * hot - currentHot, it.min, it.max)
          note = string.format('no base file, hot ran %.1f vs target %.1f -> cold %.1f (adjust by %+.1f from target)',
            currentHot, hot, newV, newV - hot)
          pressureMethod = 'target - live delta (no base file)'
        else
          -- No base, no meaningful live reading yet: rise estimate.
          newV = clamp(hot - genericRise, it.min, it.max)
          note = string.format('no base, no hot reading yet -> cold %.1f (target %.1f minus configured %.1f rise)',
            newV, hot, genericRise)
          pressureMethod = 'configured rise (no base file, no hot reading)'
        end
        table.insert(changes, string.format('Pressure %s: %s', it.corner, note))
        ensureSectionValue(parsed, it.section, string.format('%.1f', newV))
      end
    end
  end

  -- CAMBER - now real physics rather than a heuristic (4.3.0).
  --
  -- AC's tyre model scales grip with inclination angle roughly as
  --     grip(c) = 1 + DCAMBER_0*c + DCAMBER_1*c^2      (c in radians)
  -- a downward parabola, so peak grip is at c = -DCAMBER_0/(2*DCAMBER_1).
  -- Both coefficients come straight out of this car's own tyres.ini, which
  -- is readable even on cars whose data/setup.ini is encrypted. Sanity
  -- checked on two real cars: 4.00 deg and 3.38 deg - normal GT slick range.
  --
  -- What we then do with it, and why it isn't just "set camber to -4":
  -- that peak angle is what the tyre wants at the moment it's WORKING - at
  -- peak corner load, after body roll and camber gain have had their say.
  -- We already measure exactly that: the outer wheel's real camber at the
  -- highest-lateral-G instant of each clean corner. So:
  --     deficit   = -peakAngle - measuredCamberAtPeakLoad
  --     newStatic = currentStaticCamber + deficit
  -- i.e. shift static camber by however far the loaded tyre is currently
  -- missing its own optimum. Static camber is used only as the reference
  -- point to shift FROM, never as the thing being optimised - which is the
  -- distinction that was wrong before.
  local camberSchemaMap = schemaWithLive(schema.camber)
  local camberNote = nil
  -- 4.5.0: camber no longer requires a live static-camber reading. That
  -- requirement was the reason camber silently never got written in real
  -- sessions: the debug log showed staticCamberCaptured=false while every
  -- other module wrote fine, because camber was the ONLY module computing
  -- an absolute target instead of nudging the template value like the rest.
  -- It now works exactly like ARB/springs/dampers - take the value already
  -- in your setup and move it by N clicks - so it writes on every run. The
  -- absolute path is still used, but only as a bonus when the data for it
  -- happens to be available.
  if not settings.writeCamber then
    camberNote = 'camber: SKIPPED (module disabled in Settings)'
  elseif self.corneringSamples > 8 then
    local measF = self.fCamSum / self.corneringSamples
    local measR = self.rCamSum / self.corneringSamples
    local spreadF = self.fInOutSum / self.corneringSamples
    local spreadR = self.rInOutSum / self.corneringSamples
    local staticByCorner = self.staticCamberCaptured
      and {LF = self.staticCFL, RF = self.staticCFR, LR = self.staticCRL, RR = self.staticCRR}
      or {}

    for _, probe in ipairs(SETUP_PROBE.camber) do
      local front = (probe.corner == 'LF' or probe.corner == 'RF')
      local peakAngle = front and self.peakCamberF or self.peakCamberR
      local measured = front and measF or measR
      local spread = front and spreadF or spreadR
      local curStatic = staticByCorner[probe.corner]
      local baseVal = getCurVal(parsed, probe.section)
      local schemaItem = camberSchemaMap[probe.section]

      -- How much camber change is wanted, in DEGREES. Two routes:
      --   1) DCAMBER (principled): this tyre's own peak-grip inclination
      --      angle vs what the loaded tyre actually ran. Needs DCAMBER_0/1
      --      from tyres.ini AND a static reading to shift from.
      --   2) THERMAL (always available, and what a real engineer does with
      --      a pyrometer): inside-vs-outside tread temperature of the
      --      loaded outer tyre. Target band is inside 0-12°C hotter, and
      --      roughly 12°C of spread is worth about 1° of camber.
      -- Route 2 was believed to matter because CSP "whitelists" tyres.ini
      -- fields on encrypted cars. v1.9.5: it doesn't - the live DCAMBER
      -- read had never worked on ANY car (see iniNum). Route 2 is now
      -- genuinely the fallback for a tyres.ini without the coefficients.
      local deltaDeg, method
      -- v1.5.0: gate loosened from "peakAngle AND curStatic" to just
      -- peakAngle. curStatic was never actually needed for this branch's
      -- own math (deltaDeg only uses peakAngle + measured, the LOADED
      -- camber from corner sampling, which is already gated on
      -- corneringSamples>8 above and has nothing to do with a pit-stop
      -- capture) - it was only ever used a few lines down, for deriving
      -- the degrees-to-setup-units SCALE, which already has its own
      -- complete fallback chain (schema range, then stored-value
      -- magnitude) for exactly the case where curStatic is nil. The old,
      -- stricter gate meant a single missed pit-stop capture (forgetting
      -- to sit stationary once that session) silently downgraded EVERY
      -- camber read for the rest of the session to the much coarser
      -- thermal-spread proxy below, which uses a wide 0-12°C dead zone
      -- and can read "in the window" across a real range of static
      -- camber settings - confirmed from real sessions where this
      -- looked like it was reporting "fine" regardless of actual camber.
      if peakAngle then
        deltaDeg = (-peakAngle) - measured
        method = string.format('tyre peaks at %.2f°, loaded tyre ran %.2f°', -peakAngle, measured)
        -- v2.3.0: NOISE DEAD-BAND + MEASURED GAIN. The known "camber
        -- overshoots ~1.4x" item did not survive the logs: the Corvette's
        -- loaded-camber change per static change was 0.48, 0.78 and 1.6
        -- across three Builds - scatter, not a fixed gain. So (a) a deficit
        -- inside twice the loaded average's own standard error is left
        -- alone (it's noise), and (b) once 3+ Builds on this car span 0.3°
        -- of setting, the measured d(loaded)/d(static) replaces 1.
        local sq = front and self.fCamSqSum or self.rCamSqSum
        local nS = self.corneringSamples
        local se = 0
        if sq and nS > 1 then
          local var = math.max(sq / nS - measured * measured, 0) * nS / (nS - 1)
          se = math.sqrt(var / nS)
        end
        local deadBand = math.max(0.05, 2 * se)
        local gain, gainN = self:camberGain(front and 'F' or 'R')
        -- Bank this window's (setting, loaded) point for the gain, once
        -- per axle per Build.
        if probe.corner == 'LF' or probe.corner == 'LR' then
          local liveCam = liveSetup and liveSetup[probe.section]
          local dm = liveCam and liveCam.displayMultiplier
          if baseVal and dm and dm > 0 then self:camberGainRecord(front and 'F' or 'R', baseVal * dm, measured) end
        end
        method = method .. string.format('; noise ±%.2f°; gain %s', deadBand,
          gain and string.format('%.2f measured over %d Builds', gain, gainN) or string.format('1 assumed (%d of 3 points)', gainN or 0))
        if math.abs(deltaDeg) <= deadBand then
          deltaDeg = 0
        else
          deltaDeg = deltaDeg / (gain or 1)
        end
        -- DCAMBER route: this is a real, computed physics target, not a
        -- proxy - go straight to it in one Build press rather than nudging
        -- toward it over several, which was the whole point of having the
        -- lookup table. Confirmed as a real bug from an actual session: a
        -- -3.38° target against a -2.43° measured loaded reading needs a
        -- -0.95° change, but the shared ±0.8° cap below (meant for the
        -- thermal route) silently capped it to -0.80° instead. Still
        -- sanity-bounded at ±4° so a corrupted read can't write something
        -- absurd - every real car studied in this project peaks well
        -- inside that (2.6° to 6.1° across eight real cars), so 4° of
        -- CHANGE in one press comfortably covers reaching the optimum from
        -- any realistic starting point.
        deltaDeg = clamp(deltaDeg, -4, 4)
      else
        local TARGET_HI, TARGET_LO, DEG_PER_C = 12, 0, 1 / 12
        if spread > TARGET_HI then
          deltaDeg = (spread - TARGET_HI) * DEG_PER_C      -- too much neg → less negative
        elseif spread < TARGET_LO then
          deltaDeg = (spread - TARGET_LO) * DEG_PER_C      -- too little neg → more negative
        else
          deltaDeg = 0
        end
        method = string.format('tread spread %+.0f°C vs 0-12 target', spread)
        -- Thermal route: the target here is a proxy (temperature spread),
        -- not a precise computed answer, so a conservative per-press cap
        -- stays appropriate - unlike DCAMBER above, there's no confident
        -- single "right" number to jump straight to.
        deltaDeg = clamp(deltaDeg, -0.8, 0.8)
      end

      if math.abs(deltaDeg) <= 0.02 then
        camberNote = string.format('camber: already in the window (%s) - left alone', method)
      elseif baseVal then
        -- Convert degrees to this file's units. Preference order:
        -- the live setup's OWN display multiplier (v1.8.0 - authoritative,
        -- ends the guessing) > a real derived scale (static reading vs
        -- stored value) > the schema range's implied scale > the common
        -- tenths-of-a-degree convention. Sanity-checked to land near
        -- 1 / 10 / 100.
        --
        -- displayMultiplier is the game's own raw->displayed factor, so its
        -- reciprocal is exactly the raw-units-per-degree this needs: a car
        -- storing camber in tenths reports 0.1, giving scale 10, which is
        -- precisely what was reverse-engineered by hand for one car (the
        -- driver set -3.5 deg and the file stored -35) and then could NOT
        -- be generalised safely to other cars - the ini's own MIN/MAX are
        -- in degrees while VALUE isn't, and nothing in the file says so.
        -- This asks the game instead of inferring.
        local liveCamber = liveSetup and liveSetup[probe.section]
        local scale, scaleSrc
        if liveCamber and liveCamber.displayMultiplier and liveCamber.displayMultiplier > 0 then
          scale, scaleSrc = 1 / liveCamber.displayMultiplier, 'live setup display multiplier'
        elseif curStatic and math.abs(curStatic) > 0.15 then
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

        -- v1.7.1: baseVal itself can be stale, independently of scale being
        -- right. Confirmed from a real session: this car's real schema
        -- (from its own decrypted setup.ini) says CAMBER_LF is genuinely
        -- -5..-1.2 raw degrees - ground truth, not a guess - but last.ini
        -- still held -24, left over from before this car ever had a real
        -- schema (camber was ALWAYS schemaLimited until this session).
        -- baseVal=-24 taken at face value in real degrees isn't a camber
        -- angle any car runs, so adding a small physics delta to it and
        -- clamping just slams the result onto the schema boundary (-5.00,
        -- reported as if it were the answer) with no real connection to
        -- the computed target - which is exactly what "camber goes to
        -- max/min regardless of the advice panel's number" turned out to
        -- be. Falls back to the schema's own midpoint as the anchor
        -- instead, same fallback this function already uses when there's
        -- no template value at all - a real answer near the middle of the
        -- legal range beats a boundary that happens to catch a garbage
        -- input.
        local anchorVal, anchorNote = baseVal, nil
        if schemaItem then
          local margin = schemaItem.max - schemaItem.min
          if baseVal < schemaItem.min - margin or baseVal > schemaItem.max + margin then
            anchorVal = (schemaItem.min + schemaItem.max) / 2
            anchorNote = string.format(" - your setup's current value (%s) doesn't fit this car's real camber range at all, probably stale from before it had one; started from mid-range instead", tostring(baseVal))
          end
        end

        local wanted = anchorVal + deltaDeg * scale
        local newV = wanted
        if schemaItem then newV = clamp(newV, schemaItem.min, schemaItem.max) end
        -- v2.5.0: when the car's range - not the calculation - is what stops
        -- the target, say so (the Sunbeam wanted -5.3 deg static and stopped
        -- at its -2.5 limit; widening a car's range is the fix).
        local limitNote = ''
        if schemaItem and math.abs(newV - wanted) > 0.5 then
          limitNote = string.format('; the target %.2f° is beyond this car\'s range, which stops at %.2f°', wanted / scale, newV / scale)
          table.insert(rangeLimits, string.format('camber %s wants %.2f°, the car stops at %.2f°', probe.corner, wanted / scale, newV / scale))
        end
        -- Always move by at least one whole unit, so a flagged axle never
        -- rounds away to no change at all.
        if math.abs(newV - anchorVal) < 0.5 then
          newV = anchorVal + (deltaDeg > 0 and 1 or -1)
          if schemaItem then newV = clamp(newV, schemaItem.min, schemaItem.max) end
        end
        if math.abs(newV - baseVal) > 1e-9 then
          ensureSectionValue(parsed, probe.section, string.format('%.2f', newV))
          table.insert(changes, string.format('Camber %s: %s → %.2f (%+.2f°, %s; %s%s%s)',
            probe.corner, tostring(baseVal), newV, deltaDeg, method, scaleSrc, anchorNote or '', limitNote))
        end
      elseif not schemaItem then
        -- v2.5.0: no such adjustment on this car (the summary line says so).
        absentSections[probe.section] = true
      else
        camberNote = string.format('camber %s: SKIPPED (%s not in your setup file)', probe.corner, probe.section)
      end
    end
  else
    camberNote = 'camber: need more clean corners before the loaded-tyre reading is trustworthy - left alone'
  end
  if camberNote then table.insert(changes, camberNote) end

  -- 4.3.0: two independent ways to produce a value, tried in order. Between
  -- them, a car needs only ONE of "readable schema" or "an existing setup
  -- file" - and last.ini basically always exists, so in practice this works
  -- on encrypted cars too, which was the whole blocker before.
  --
  --   1) TEMPLATE (preferred): the car already has a real, valid, in-range
  --      value for this section in last.ini. Nudge it by a percentage of
  --      its own magnitude, floored at one whole unit so small integers
  --      (click indices) still move. No knowledge of the item's units,
  --      legal range or step size required - which is exactly why this
  --      works where the schema approach couldn't.
  --   2) SCHEMA: if there's no template value but data/setup.ini IS
  --      readable, fall back to "midpoint of the legal range, shifted N
  --      clicks in the flagged direction".
  --
  -- Categories the telemetry didn't flag are not written at all, so loading
  -- the result only changes what needs changing and leaves everything else
  -- at whatever the currently-loaded setup has.

  -- Per-step nudge size as a fraction of the value's own magnitude. Damper
  -- and spring rates tolerate slightly larger relative steps than alignment
  -- or aero, which is why these differ.
  local NUDGE_FRACTION = {
    arb = 0.07, spring = 0.08, damper = 0.08, bumpStop = 0.06,
    ride = 0.05, toe = 0.05, wing = 0.08, diff = 0.08,
    -- Smaller than the plain ride-height fraction on purpose: multiple
    -- independent sources warned rake's effect can be "peaky" and works
    -- within a narrow window, so a rake nudge moves less per press than
    -- an ordinary bottoming-driven ride-height raise does.
    rake = 0.03,
  }

  local function absFromSchema(schemaItem, direction, clicks)
    if not schemaItem then return nil end
    local mid = (schemaItem.min + schemaItem.max) / 2
    local raw = mid + direction * clicks * schemaItem.step
    return snapToStep(raw, schemaItem.min, schemaItem.max, schemaItem.step)
  end

  -- Writes a value for `section`, preferring the template. Logs exactly
  -- which route was taken so the debug log stays self-explaining.
  -- Returns true if something was written.
  --
  -- `quietSkip` suppresses the SKIPPED line. Used for probe lists that
  -- deliberately contain several naming conventions for the SAME physical
  -- item (ROD_LENGTH_* vs RIDE_HEIGHT_*, FRONT_BIAS vs BRAKE_BIAS) - a car
  -- only ever has one of them, so reporting the other as "skipped" is pure
  -- noise. The caller reports once if none of the variants matched.
  --
  -- v2.3.0: three helpers shared by the calculated targets.
  --   calc.touched[section] - written by a calculated jump this Build; a
  --     lever or the damper histogram must not move it again on top.
  --   calc.lastClicks       - largest click move of the current lever call,
  --     so the chain banks how far the lever actually went.
  --   zetaOf(section, v)    - damping ratio of a VANILLA damper setting at
  --     that corner: c / (2 sqrt(k m)), c and k wheel rates, m sprung corner
  --     mass. nil when any input is unknown (LUT dampers, DWB2 motion
  --     ratios, unreadable car data).
  local calc = {touched = {}, lastClicks = 0, notes = {}}
  local calcSpringMap = schemaWithLive(schema.springRate)
  local calcDamperMap = {BUMP = schemaWithLive(schema.damperBump), REBOUND = schemaWithLive(schema.damperRebound)}
  local function zetaOf(section, storedValue)
    local kind, corner = section:match('^DAMP_(%u+)_(%u%u)$')
    if not kind or not calcDamperMap[kind] then return nil end
    local front = (corner == 'LF' or corner == 'RF')
    local c = physicalOf(calcDamperMap[kind][section], storedValue)
    local m = self:cornerSprungMass(front)
    local springSec = 'SPRING_RATE_' .. corner
    local k = self:cornerSpringRate(front, calcSpringMap[springSec], getCurVal(parsed, springSec))
    if not c or not m or not k or c <= 0 or k <= 0 then return nil end
    return c / (2 * math.sqrt(k * m)), kind
  end

  local function writeTuned(schemaItem, section, direction, clicks, frac, desc, quietSkip)
    local cur = getCurVal(parsed, section)
    if cur then
      -- v1.9.7: a nudge is `clicks` STEPS of this control when the step is
      -- known - and since v1.8.0 (spinners) + v1.9.6 (setup.ini) it always
      -- is. Until now the size was a PERCENTAGE OF THE CURRENT VALUE
      -- (`frac`), which was the only option when no car had a readable
      -- schema, and which is wildly wrong for anything stored as a big
      -- number: the Ferrari's fast rebound lives at 175..190, so 8% of 185
      -- is 15 clicks - the ENTIRE range in one press. That is the real
      -- mechanism behind v1.9.4's "185 -> 175 in ONE Build" (the direction
      -- ratchet decided which way; this decided how far). The same nudge
      -- on a 0..24 click index floored to 1 click, so small-index cars
      -- looked fine and hid it. Off-grid values (a Dacia ARB at 21079 on
      -- a 1000 N/m step, left by earlier percentage writes) are snapped
      -- back onto the car's own grid on the way through. The percentage
      -- path survives only for a section with no step at all.
      local hasStep = schemaItem and schemaItem.step and schemaItem.step > 0
      local newV, fmt
      if hasStep then
        local raw = cur + direction * clicks * schemaItem.step
        newV = snapToStep(raw, schemaItem.min, schemaItem.max, schemaItem.step)
        local intStep = schemaItem.step >= 0.999 and math.abs(schemaItem.step - math.floor(schemaItem.step)) < 0.001
        fmt = intStep and '%.0f' or '%.2f'
      else
        local mag = math.max(math.abs(cur) * frac * clicks, 1)
        local raw = cur + direction * mag
        local looksInteger = math.abs(cur - math.floor(cur + 0.5)) < 0.01
        newV = looksInteger and math.floor(raw + 0.5) or (math.floor(raw * 100 + 0.5) / 100)
        if newV == cur then
          -- Nudge rounded away to nothing; push one whole unit so a flagged
          -- item always actually moves.
          newV = cur + (direction > 0 and 1 or -1)
        end
        fmt = looksInteger and '%.0f' or '%.2f'
      end
      -- v2.1.0: second return = did the value actually move. A write that
      -- lands on the same number (already at the clamp) is "handled" but
      -- not a change, and the lever chain must know the difference.
      if math.abs(newV - cur) < 1e-9 then return true, false end
      -- v2.3.0: a calculated target already set this section this Build.
      -- v2.4.0: or a branch put-back / restore (touched = its name).
      if calc.touched[section] then
        table.insert(changes, string.format('%s: NOT moved - already set by %s this Build', desc,
          type(calc.touched[section]) == 'string' and calc.touched[section] or 'a calculated target'))
        return true, false
      end
      -- v2.3.0: damping-ratio floor. No softening may take a vanilla slow
      -- damper below a sane ratio (bump 0.30, rebound 0.40). On the Huracan
      -- the setup allows rear rebound down to a ratio of 0.18, and the
      -- oversteer lever took it from 10 to 4 clicks in one night.
      if direction < 0 and section:find('^DAMP_[BR]') then
        local z1, kind = zetaOf(section, newV)
        local floorZ = (kind == 'BUMP') and ZETA_FLOOR_BUMP or ZETA_FLOOR_REBOUND
        if z1 and z1 < floorZ then
          table.insert(changes, string.format('%s: NOT written - would take the damping ratio to %.2f, below the %.2f floor for %s', desc, z1, floorZ, string.lower(tostring(kind))))
          return true, false
        end
      end
      -- v2.2.0: CSP LUT sections are checked against the car's own curve
      -- before anything is written - here, so no write path can skip it.
      -- A refusal is "handled, not changed", which lets a lever chain move
      -- on to its next lever exactly as it does at a hard limit.
      local curveNote = nil
      if section:find('^DAMPER_') then
        local ok, note = self:lutDamperMoveOk(section, cur, newV, direction, schemaItem)
        if not ok then
          table.insert(changes, string.format('%s: NOT written - %s', desc, note))
          return true, false
        end
        curveNote = note
      elseif self.lutArb and self.lutArb[section] then
        local ok, note = self:lutArbMoveOk(section, cur, newV, schemaItem)
        if not ok then
          table.insert(changes, string.format('%s: NOT written - %s', desc, note))
          return true, false
        end
        curveNote = note
      end
      ensureSectionValue(parsed, section, string.format(fmt, newV))
      calc.lastClicks = math.max(calc.lastClicks,
        hasStep and math.floor(math.abs(newV - cur) / schemaItem.step + 0.5) or 1)  -- v2.3.0
      table.insert(changes, string.format('%s: %s → %s (from your current setup%s%s)',
        desc, string.format(fmt, cur), string.format(fmt, newV),
        hasStep and string.format(', %d click%s of %s', clicks, clicks == 1 and '' or 's', fmtSetupValue(schemaItem.step, schemaItem.step)) or '',
        curveNote and ('; ' .. curveNote) or ''))
      return true, true
    end
    -- v2.2.0: a CSP LUT section with no current value has nothing to check
    -- a direction from - don't invent one from the schema midpoint.
    if section:find('^DAMPER_') or (self.lutArb and self.lutArb[section]) then
      if not quietSkip then
        table.insert(changes, string.format('%s: SKIPPED (%s has no current value to move from - CSP LUT sections are only ever nudged from what is on the car)', desc, section))
      end
      return false, false
    end
    local newV = absFromSchema(schemaItem, direction, clicks)
    if newV == nil then
      -- v2.5.0: the car has no such adjustment - listed once in the
      -- "Not adjustable on this car" summary instead of a line per write.
      if not quietSkip then absentSections[section] = true end
      return false, false
    end
    ensureSectionValue(parsed, section, fmtSetupValue(newV, schemaItem.step))
    table.insert(changes, string.format('%s: → %s (car schema midpoint %+d clicks)',
      desc, fmtSetupValue(newV, schemaItem.step), direction * clicks))
    return true, true
  end
  -- Back-compat shim so the call sites below stay readable.
  local function writeAbs(schemaItem, section, direction, clicks, desc, frac, quietSkip)
    return writeTuned(schemaItem, section, direction, clicks, frac or 0.07, desc, quietSkip)
  end

  do
  -----------------------------------------------------------------------------
  -- v2.1.0: BALANCE LEVERS. Every balance-driven writer (ARB, rear
  -- dampers, toe, rake, wings) is now a function in `levers`, and a CHAIN
  -- RUNNER at the end of this Build decides which ONE lever acts per
  -- regime, in physics priority order, so that the next window can
  -- measure what that lever did. See LEVER_CHAINS and runLeverChains.
  -- Each lever returns true only if it actually moved something; a lever
  -- that is unavailable (module off, section missing, at its limit,
  -- trigger signal absent) returns false and the chain moves to the next.
  -----------------------------------------------------------------------------
  local levers = {}
  -- v2.5.0: set when the travel checks (bottoming / max-travel springs)
  -- move a spring this Build - the spring balance lever then stands aside,
  -- so one window never carries two spring moves for different reasons.
  -- v2.6.0: the bottoming chain's springRate lever sets it.
  local springsMovedForTravel = false
  -- v2.5.0: DIRECTION FROM THE PIT CALIBRATION. The ride-height writers
  -- assumed "one click up = a higher car" and said "verify direction".
  -- The pit calibration (v2.3.0) measures millimetres per click, and its
  -- SIGN is the direction: measured -> follow it, no warning; not yet
  -- measured -> as before. Returns the click direction that RAISES that
  -- end, and whether it was measured. v2.6.0: defined here, before the
  -- levers - the bottoming chain's ride raise and the rake lever use it.
  local function rideDir(front)
    -- v2.5.2: only a reliable calibration counts as measured (see
    -- RIDE_CAL_MIN_PAIRS) - a single noisy pair once flipped "raise".
    local slope, _, reliable = self:rideCalSlope(front and 'F' or 'R')
    if reliable then return slope > 0 and 1 or -1, true end
    return 1, false
  end

  -- ARB. What actually matters for balance is the RATIO of front to rear
  -- roll stiffness, not either bar's absolute value - understeer is cured
  -- either by softening the front bar or stiffening the rear, and the two
  -- are equivalent in effect. If the bar we want to soften is already near
  -- the bottom of its range, the opposite bar is stiffened instead.
  -- Both bars' near-minimum status is snapshotted before any write (the
  -- v1.4.1 self-cancellation lesson).
  --
  -- v2.2.0: resolved PER END between vanilla ARB_FRONT/ARB_REAR and CSP LUT
  -- ARB_F/ARB_R (19 of the driver's cars). A LUT bar moves ONE row per
  -- Build (a row on those LUTs is a 15-70% stiffness change - gt4_alpine
  -- front 8400 -> 11856 -> 17902 -> 29952), is limited "at the limit"
  -- rather than 1.5 steps short (a 3-row bar would otherwise be frozen
  -- whole), and never softens onto a row whose stiffness is 0 ("detached"
  -- on the BTCC cars) - lutArbMoveOk in writeTuned is the backstop.
  -- Also fixed in passing: a push verdict on a car with only a REAR bar
  -- used to report "no ARB section" instead of stiffening that rear bar;
  -- and a soften refused at write time now falls through to the other end.
  local arbMap = schemaWithLive(schema.arb)
  local arbF, arbR = arbFSection, arbRSection
  -- LUT bar with no spinner range: its own LUT row count is the range.
  for _, sec in ipairs({'ARB_F', 'ARB_R'}) do
    local lut = self.lutArb and self.lutArb[sec]
    if lut and lut.readable and lut.rows and lut.rows > 1 and not arbMap[sec] then
      arbMap[sec] = {section = sec, min = 0, max = lut.rows - 1, step = 1, label = sec}
    end
  end
  local function arbProblem(section)
    local lut = self.lutArb and self.lutArb[section]
    if lut and lut.readable and not lut.rising then return 'its LUT does not rise with the row - direction unknown' end
    if lut and not arbMap[section] then return 'CSP LUT bar with no known range (no spinner, LUT not readable)' end
    if lut and not getCurVal(parsed, section) then return 'CSP LUT bar with no current value' end
    return nil
  end
  local function arbCanSoften(section)
    local cur, it = getCurVal(parsed, section), arbMap[section]
    local lut = self.lutArb and self.lutArb[section]
    if not cur then return true end  -- vanilla, not in the template: writeTuned's schema fallback, as before
    if lut then
      local floor = it.min + ((lut.readable and lut.firstUsableRow) or 1)
      return cur - 1 >= floor
    end
    if it then return cur > it.min + it.step * 1.5 end
    return cur > 2
  end
  local function arbCanStiffen(section)
    local cur, it = getCurVal(parsed, section), arbMap[section]
    local lut = self.lutArb and self.lutArb[section]
    if not cur then return true end  -- vanilla, not in the template: as before
    if lut then return cur + 1 <= it.max end
    if it then return cur < it.max - it.step * 1.5 end
    return true
  end
  levers.arb = function(regime, direction, jump)
    if not settings.writeARB then return false, 'module off' end
    if regime ~= 'low' then return false, 'mechanical lever, low-speed only' end
    if not arbF and not arbR then return false, 'no ARB section on this car (neither ARB_FRONT/ARB_REAR nor CSP ARB_F/ARB_R)' end
    local n = direction == 'tight' and self.midPush or self.midSnap
    local softenEnd = direction == 'tight' and arbF or arbR
    local stiffenEnd = direction == 'tight' and arbR or arbF
    local why = {}
    -- v2.3.0: `jump` = clicks the measured response says are needed (see
    -- the chain runner); LUT bars take at most 2 rows even then.
    local function move(section, dir, desc)
      local lut = self.lutArb and self.lutArb[section]
      local clicks = lut and math.min(jump or 1, 2) or (jump or steps(n))
      local _, ch = writeAbs(arbMap[section], section, dir, clicks,
        desc .. (lut and ' [CSP LUT bar]' or '') .. (jump and string.format(' [measured-response jump: %d]', clicks) or ''), NUDGE_FRACTION.arb)
      return ch == true
    end
    if softenEnd then
      local p = arbProblem(softenEnd)
      if p then
        table.insert(why, softenEnd .. ': ' .. p)
      elseif not arbCanSoften(softenEnd) then
        table.insert(why, softenEnd .. ': at its softest usable setting')
      elseif move(softenEnd, -1, direction == 'tight'
          and string.format('ARB front (softer, less low-speed push; %d push vs %d oversteer)', self.midPush, self.midSnap)
          or string.format('ARB rear (softer, less low-speed oversteer; %d oversteer vs %d push)', self.midSnap, self.midPush)) then
        return true, 'moved'
      else
        table.insert(why, softenEnd .. ': no change possible')
      end
    end
    if stiffenEnd then
      local p = arbProblem(stiffenEnd)
      if p then
        table.insert(why, stiffenEnd .. ': ' .. p)
      elseif not arbCanStiffen(stiffenEnd) then
        table.insert(why, stiffenEnd .. ': at its stiffest')
      elseif move(stiffenEnd, 1, direction == 'tight'
          and 'ARB rear (stiffer - front bar can\'t go softer, so shift balance from the other end)'
          or 'ARB front (stiffer - rear bar can\'t go softer, so shift balance from the other end)') then
        return true, 'moved'
      else
        table.insert(why, stiffenEnd .. ': no change possible')
      end
    end
    return false, table.concat(why, '; ')
  end

    -- v2.5.0: SPRINGS as a balance lever - the front/rear roll-stiffness
    -- split. On a car with no anti-roll bars (the Sunbeam today) the
    -- springs ARE the roll balance the ARB lever would otherwise set.
    -- Loose -> rear softer (or front stiffer if the rear is at its softest
    -- or already running out of travel); tight -> front softer (or rear
    -- stiffer). One click, both corners of that axle. Stands aside when the
    -- bottoming chain's spring lever (v2.6.0) already moved a spring this
    -- Build - the chain runs first.
    local springBalMap = schemaWithLive(schema.springRate)
    local function springAxle(front)
      local have = {}
      for _, s in ipairs(front and {'SPRING_RATE_LF', 'SPRING_RATE_RF'} or {'SPRING_RATE_LR', 'SPRING_RATE_RR'}) do
        if getCurVal(parsed, s) or springBalMap[s] then table.insert(have, s) end
      end
      return have
    end
    local function springRoom(sec, dir)
      local cur, it = getCurVal(parsed, sec), springBalMap[sec]
      if not cur or not it or not it.step then return cur ~= nil end
      if dir < 0 then return cur - it.step >= it.min - 1e-9 end
      return cur + it.step <= it.max + 1e-9
    end
    levers.springs = function(regime, direction)
      if not settings.writeSprings then return false, 'module off' end
      if regime ~= 'low' then return false, 'mechanical lever, low-speed only' end
      local front, rear = springAxle(true), springAxle(false)
      if #front == 0 and #rear == 0 then return false, 'no adjustable springs on this car' end
      if springsMovedForTravel then return false, 'springs already moved for travel this Build - measured next window first' end
      for _, s in ipairs(front) do if calc.touched[s] then return false, 'springs set by a calculated target this Build' end end
      for _, s in ipairs(rear) do if calc.touched[s] then return false, 'springs set by a calculated target this Build' end end
      local plan
      if direction == 'loose' then
        plan = {
          {axle = rear, dir = -1, what = 'rear softer', why = 'less rear roll stiffness = more rear grip', skip = (self.springsHitsR or 0) > th},
          {axle = front, dir = 1, what = 'front stiffer', why = 'the front takes more of the load transfer'},
        }
      else
        plan = {
          {axle = front, dir = -1, what = 'front softer', why = 'less front roll stiffness = more front grip', skip = (self.springsHitsF or 0) > th},
          {axle = rear, dir = 1, what = 'rear stiffer', why = 'the rear takes more of the load transfer'},
        }
      end
      for _, p in ipairs(plan) do
        local ok = (#p.axle > 0) and not p.skip
        for _, s in ipairs(p.axle) do if not springRoom(s, p.dir) then ok = false end end
        if ok then
          local moved = false
          for _, s in ipairs(p.axle) do
            local _, ch = writeAbs(springBalMap[s], s, p.dir, 1,
              string.format('Spring %s (%s for %s-speed %s - %s)', s:sub(-2), p.what, regime, direction == 'loose' and 'oversteer' or 'push', p.why),
              NUDGE_FRACTION.spring)
            moved = moved or (ch == true)
          end
          if moved then return true, 'moved' end
        end
      end
      return false, 'springs at their limits that way (or that axle already running out of travel)'
    end

    -- BOTTOMING / RUNNING OUT OF TRAVEL. v2.6.0: ONE FIX AT A TIME, per
    -- end. Until v2.5.2 every Build that saw bottoming changed springs,
    -- slow AND fast dampers (bump and rebound), packers and ride height at
    -- once - on the Sunbeam the dampers climbed 2 clicks a Build and no
    -- window could say which change did anything. Nik: "Bottoming - one at
    -- a time. Ride height least important. Stiffening springs too much
    -- loses grip so be cautious." Now each end has a chain (LEVER_CHAINS
    -- travelF-/travelR-bottoming) that the chain runner works like the
    -- balance chains: one lever per end per Build, judged next window,
    -- frozen after two moves that did nothing, put back at the end of a
    -- pass that made no difference. Only on a lap-consistent signal (the
    -- end's max-travel hits on most clean laps - travelSignal).
    --   packers    more travel before the packers (costs no platform)
    --   bump       slow bump stiffer - more support through the stroke
    --   fastBump   fast bump stiffer - the hit that reaches the end
    --   springRate the calculated rate, +10% a Build at most
    --   rideRaise  ride height up one click - last: it costs aero/grip
    -- Bump only, never rebound: too much rebound packs a car down over a
    -- run of bumps (each one compresses again before the wheel is back) -
    -- the old "stiffer rebound against creep" had it backwards. Bump stop
    -- RATE stays alone (4.5.0: a stiffer stop makes the hit harsher, not
    -- rarer). Each lever needs the item on this car: a car without packers
    -- (the Sunbeam v6) skips that lever with its reason. Every section a
    -- lever moves is marked calc.touched, so no balance lever moves it
    -- again this Build.
    local function travelLeversFor(e)
      local front = (e == 'F')
      local endWord = front and 'front' or 'rear'
      local corners = front and {'LF', 'RF'} or {'LR', 'RR'}
      local packerMap = schemaWithLive(schema.packerRange)
      local bumpMap = schemaWithLive(schema.damperBump)
      local fastMap = schemaWithLive(schema.damperFastBump)
      local springMap = schemaWithLive(schema.springRate)
      local rideMap = schemaWithLive(schema.rideHeight)
      local function signal()
        local _, hits, _, agree, considered = travelSignal(self, e, th)
        return hits or 0, string.format('%s runs out of travel on %d of %d %s', endWord, agree or 0, considered or 0, EV_UNIT.many)
      end
      -- The sections of this lever the car has (current value or setup item).
      local function present(map, secs, what)
        local have = {}
        for _, sec in ipairs(secs) do
          if sec and (getCurVal(parsed, sec) or map[sec]) then table.insert(have, sec) end
        end
        if #have == 0 then return nil, 'no adjustable ' .. what .. ' on this car' end
        for _, sec in ipairs(have) do
          local by = calc.touched[sec]
          if by then return nil, string.format('%s already set by %s this Build', sec, type(by) == 'string' and by or 'a calculated target') end
        end
        return have
      end
      -- Moves every present section the same way; returns moved, why.
      local function moveAll(map, secs, what, dir, clicks, descOf, frac)
        local have, why = present(map, secs, what)
        if not have then return false, why end
        local moved = false
        for _, sec in ipairs(have) do
          local _, ch = writeAbs(map[sec], sec, dir, clicks, descOf(sec), frac, true)
          if ch then calc.touched[sec] = 'the bottoming chain'; moved = true end
        end
        if not moved then return false, what .. ' already at its limit' end
        return true, 'moved'
      end
      local function enabled(frontKey, rearKey)
        if front then return settings[frontKey] end
        return settings[rearKey]
      end

      levers['packers' .. e] = function()
        if not settings.writeSuspension then return false, 'module off' end
        local hits, sig = signal()
        local secs = {}
        for _, c in ipairs(corners) do table.insert(secs, 'PACKER_RANGE_' .. c) end
        return moveAll(packerMap, secs, endWord .. ' packer range', 1, steps(hits), function(sec)
          return string.format('Packer range %s (more travel before the packers - %s)', sec:sub(-2), sig)
        end, NUDGE_FRACTION.bumpStop)
      end

      levers['bump' .. e] = function()
        if not enabled('writeDampersFront', 'writeDampersRear') then return false, 'module off' end
        local hits, sig = signal()
        local secs = {}
        for _, c in ipairs(corners) do table.insert(secs, damperSection('BUMP', c)) end  -- vanilla or CSP LUT
        return moveAll(bumpMap, secs, endWord .. ' slow bump', 1, steps(hits), function(sec)
          return string.format('%s bump %s (stiffer, more support through the stroke - %s; rebound left alone)', front and 'Front' or 'Rear', sec:sub(-2), sig)
        end, NUDGE_FRACTION.damper)
      end

      levers['fastBump' .. e] = function()
        if not enabled('writeFastDampersFront', 'writeFastDampersRear') then return false, 'module off' end
        local hits, sig = signal()
        local secs = {}
        for _, c in ipairs(corners) do table.insert(secs, 'DAMP_FAST_BUMP_' .. c) end
        return moveAll(fastMap, secs, endWord .. ' fast bump', 1, steps(hits), function(sec)
          return string.format('Fast bump %s (stiffer, the hit that reaches the end of the travel - %s; fast rebound left alone)', sec:sub(-2), sig)
        end, NUDGE_FRACTION.damper)
      end

      -- The calculated rate (cautiousSpringTarget) from the median clean
      -- lap's peak travel use, rounded up onto the car's grid but never
      -- past +SPRING_MAX_STEP (rounded down when the cap binds); one click
      -- at least - the smallest move the car allows. One click when the
      -- rate or the per-lap travel isn't known.
      levers['springRate' .. e] = function()
        if not settings.writeSprings then return false, 'module off' end
        local _, sig = signal()
        local secs = {}
        for _, c in ipairs(corners) do table.insert(secs, 'SPRING_RATE_' .. c) end
        local have, why = present(springMap, secs, endWord .. ' springs')
        if not have then return false, why end
        local uses = {}
        for _, b in ipairs(windowBins(self)) do
          local u = front and b.travelUseF or b.travelUseR
          if u and u > 0 then table.insert(uses, u) end
        end
        table.sort(uses)
        local medianUse = (#uses >= 2) and uses[math.floor((#uses + 1) / 2)] or nil
        local moved = false
        for _, sec in ipairs(have) do
          local it, cur = springMap[sec], getCurVal(parsed, sec)
          local k = cur and self:cornerSpringRate(front, it, cur)
          local clicks, desc = 1, nil
          if medianUse and k and k > 0 and it and it.raw and it.step and it.step > 0 then
            local phys = physicalOf(it, cur)
            local kTarget = cautiousSpringTarget(k, medianUse)
            local stored = phys and storedOf(it, phys * (kTarget / k))
            local capStored = phys and storedOf(it, phys * (1 + SPRING_MAX_STEP))
            if stored and capStored then
              if medianUse <= SPRING_TARGET_USE then
                desc = string.format('Spring %s (stiffer 1 click - %s, though the median %s uses %.0f%% of this car\'s travel range, inside the %.0f%% target)',
                  sec:sub(-2), sig, EV_UNIT.one, medianUse * 100, SPRING_TARGET_USE * 100)
              else
                clicks = math.max(1, math.ceil((stored - cur) / it.step - 1e-6))
                while clicks > 1 and cur + clicks * it.step > capStored + 1e-6 do clicks = clicks - 1 end
                desc = string.format('Spring %s (CALCULATED, cautious: median %s uses %.0f%% of this car\'s travel range -> %.0f -> %.0f N/mm aims for %.0f%%%s)',
                  sec:sub(-2), EV_UNIT.one, medianUse * 100, k / 1000, kTarget / 1000, SPRING_TARGET_USE * 100,
                  (medianUse / SPRING_TARGET_USE > 1 + SPRING_MAX_STEP) and string.format(', capped at +%.0f%% this Build', SPRING_MAX_STEP * 100) or '')
                if it.max and stored > it.max + 1e-6 then
                  table.insert(rangeLimits, string.format('spring %s wants %.0f N/mm, the car stops at its maximum', sec:sub(-2), kTarget / 1000))
                end
              end
            end
          end
          desc = desc or string.format('Spring %s (stiffer 1 click - %s; the rate or the per-%s travel is not known, so the smallest step)', sec:sub(-2), sig, EV_UNIT.one)
          local _, ch = writeAbs(it, sec, 1, clicks, desc, NUDGE_FRACTION.spring)
          if ch then calc.touched[sec] = 'the bottoming chain'; moved = true end
        end
        if not moved then return false, endWord .. ' springs already at their stiffest' end
        springsMovedForTravel = true
        return true, 'moved'
      end

      -- Last: ride height costs grip and aero. One click per Build, in the
      -- direction the pit calibration measured (rideDir); refused when the
      -- ride height already moved this Build (the other end's chain, or the
      -- floor-clearance step) - one change at a time.
      levers['rideRaise' .. e] = function()
        if not settings.writeSuspension then return false, 'module off' end
        if calc.rideMoved then return false, 'ride height already moved this Build - one change at a time, measured next window' end
        local _, sig = signal()
        local up, measured = rideDir(front)
        local secs = {}
        for _, c in ipairs(corners) do
          table.insert(secs, firstPresent('ROD_LENGTH_' .. c, 'RIDE_HEIGHT_' .. c)
            or (rideMap['ROD_LENGTH_' .. c] and ('ROD_LENGTH_' .. c)) or (rideMap['RIDE_HEIGHT_' .. c] and ('RIDE_HEIGHT_' .. c)) or false)
        end
        local ok, why = moveAll(rideMap, secs, endWord .. ' ride height', up, 1, function(sec)
          return string.format('Ride height %s (raise 1 click - %s; ride height is the last bottoming fix - %s)', sec:sub(-2), sig,
            measured and 'direction measured in the pits' or '⚠ verify direction on this car')
        end, NUDGE_FRACTION.ride)
        if ok then calc.rideMoved = true end
        return ok, why
      end
    end
    travelLeversFor('F')
    travelLeversFor('R')

    -- DAMPERS. Slow and fast dampers do genuinely different jobs and, as of
    -- 4.4.0, are no longer both blindly stiffened.
    --
    -- SLOW (bump/rebound) responds to low shaft speeds - the body movements
    -- of weight transfer: roll, pitch, dive, squat. Repeated slow-damper
    -- events mean the platform isn't being controlled, so stiffer is right.
    --
    -- FAST (fast bump / fast rebound) responds to high shaft speeds - sharp
    -- single events: kerbs, bumps, ripples. Direction depends entirely on
    -- WHY the fast damper is being worked, and the previous version had
    -- this backwards. AC's own in-game description says it plainly: lower
    -- fast-bump values let the suspension absorb more energy over bumps and
    -- kerbs, while a very stiff setting means the damper barely moves, so
    -- the car absorbs nothing and gets launched. So:
    --   * fast events WITH bottoming on that end -> the end's bottoming
    --     chain (v2.6.0) owns it: fast bump stiffer when its turn comes,
    --     one change at a time, fast rebound left alone.
    --   * fast events WITHOUT bottoming -> until v2.6.1, SOFTEN for kerbs
    --     (floored at the factory default). Removed in v2.6.1 - see below.
    -- Fast rebound follows fast bump (Suspension Secrets: a soft fast bump
    -- normally wants a soft fast rebound so the damper is extended again
    -- in time for the next bump). Until v2.6.0 bottoming flipped fast
    -- rebound STIFFER too, on the idea that too-soft rebound lets the car
    -- creep down onto the stops. It is the other way round: too MUCH
    -- rebound is what packs a car down over a run of bumps - the wheel
    -- isn't back before the next one compresses it again.
    -- v2.6.1: THE FAST-DAMPER KERB SOFTENER IS GONE. Nik: "it's useless.
    -- abolish it." It softened fast bump AND fast rebound whenever fast
    -- events crossed threshold - which measures "this track has kerbs",
    -- not "these dampers are too stiff" - floored only at the factory
    -- default (v1.9.4), and stood aside on an end whose bottoming chain was
    -- running. Fast dampers are now moved by the bottoming chain's fastBump
    -- lever only (stiffer, one change at a time); nothing softens them for
    -- kerbs any more. A side effect worth having: AC's own fast-rebound
    -- tooltip says too low "can provoke a bouncing of the tyres", and this
    -- writer was the only thing that ever lowered it.

    -- SLOW DAMPERS (bump/rebound), rebuilt 4.6.0. Direction follows the
    -- same balance logic as the advice text: the side with MORE events is
    -- comparatively SOFTER (moves more freely, crosses the velocity
    -- threshold more often), so restoring balance means stiffening that
    -- side OR softening the other side to match. Bottoming on that axle
    -- overrides balance entirely - since v2.6.0 the axle is left to its
    -- bottoming chain (until then both were stiffened). Margin-checked exactly like ARB's
    -- near-the-limit fallback: prefer the "textbook" direction, but switch
    -- to the other side if that one is already near its own limit.
    --
    -- v1.9.3: THE REAR AXLE NO LONGER USES THE HISTOGRAM WHEN THE CAR IS
    -- TELLING US WHAT IT'S DOING. The histogram is a damper-symmetry
    -- heuristic; it knows nothing about handling. And it was structurally
    -- biased: on the rear, rebound events out-number bump events in every
    -- real session logged (216 vs 46, 110 vs 25, 45 vs 20), so the rear
    -- branch almost always resolved to "stiffen rear rebound" - on a car
    -- with 265 oversteer events in one session, it stiffened rear rebound
    -- 24->28. Assetto Corsa's own setup tooltips (captured verbatim in
    -- CLAUDE.md, "In-game damper guidance") say plainly:
    --
    --   REAR REBOUND  higher: "less stable under braking and initial turn
    --                 in, but much more agile on slow turns that need the
    --                 whole car to rotate"
    --                 lower:  "more stable at initial turn in"
    --   REAR BUMP     higher: "more oversteer under acceleration or at the
    --                 moment you release the brakes entering a turn"
    --                 lower:  "more traction and more stability the moment
    --                 you release the brakes"
    --
    -- So: a LOOSE rear (oversteer dominant) wants rear rebound and rear
    -- bump SOFTER; a TIGHT car (understeer dominant) can use rear rebound
    -- STIFFER for rotation. The histogram stays as the fallback for the
    -- rear when neither signal clearly dominates, and is untouched on the
    -- front, where AC's own tooltip describes effects that genuinely vary
    -- by car (out of scope here by design - see the front-rebound note in
    -- the 0.625 branch below). This is the position the driver held for
    -- the entire alpha, backed by Koni's guide, Suspension Secrets and
    -- this project's own v1.0.1 finding; the tooltip settled it. Actioned
    -- only after the user asked, having first held for more tester logs.
    local rearHandling, snapN, pushN, rearNote = rearHandlingSignal(self, th)
    local slowDamperMap = {
      damperBump = schemaWithLive(schema.damperBump),
      damperRebound = schemaWithLive(schema.damperRebound),
    }
    -- marginFraction, when given, is a fraction of the item's FULL range
    -- rather than a step count - more robust across cars with wildly
    -- different step granularities than a fixed number of steps would be.
    -- Falls back to the original tight margin (1.5 steps from the hard
    -- limit) when not given.
    local function nearLimit(section, map, towardMax, marginFraction)
      local cur = getCurVal(parsed, section)
      if not cur then return false end
      local it = map[section]
      if not it then return false end
      local margin = marginFraction and (marginFraction * (it.max - it.min)) or (1.5 * it.step)
      return towardMax and (cur >= it.max - margin) or (cur <= it.min + margin)
    end

    -- v2.3.0: DAMPING-RATIO FLOOR PRE-PASS. A vanilla slow damper whose
    -- ratio (c / 2 sqrt(k m), wheel rates, sprung corner mass) sits below
    -- the floor - bump 0.30, rebound 0.50 (v2.6.1, was 0.40) - is lifted to just above it in
    -- ONE move. The physics gives a sane window, not a point, so this only
    -- ever lifts badly under-damped settings (the Escort mod's front bump
    -- was 0.18; the Huracan's setup allows rear rebound down to 0.18);
    -- it never lowers a stiff one - real race cars run up to ~1.8. Balance
    -- tuning inside the window stays with the lever chain.
    for _, corner in ipairs({'LF', 'RF', 'LR', 'RR'}) do
      local front = (corner == 'LF' or corner == 'RF')
      local enabled
      if front then enabled = settings.writeDampersFront else enabled = settings.writeDampersRear end
      if enabled then
        for _, kind in ipairs({'BUMP', 'REBOUND'}) do
          local sec = 'DAMP_' .. kind .. '_' .. corner
          local cur = getCurVal(parsed, sec)
          local item = calcDamperMap[kind][sec]
          local z = cur and zetaOf(sec, cur)
          local floorZ = (kind == 'BUMP') and ZETA_FLOOR_BUMP or ZETA_FLOOR_REBOUND
          if z and z < floorZ and item and item.raw then
            local cTarget = physicalOf(item, cur) * (floorZ * 1.05 / z)
            local stored = storedOf(item, cTarget)
            if stored then
              local clicks = math.max(1, math.ceil((stored - cur) / (item.step or 1) - 1e-6))
              local _, ch = writeAbs(item, sec, 1, clicks,
                string.format('%s %s (CALCULATED: damping ratio %.2f is under the %.2f floor - lifted in one move)', front and 'Front' or 'Rear', string.lower(kind) .. ' ' .. corner, z, floorZ),
                NUDGE_FRACTION.damper)
              if ch then calc.touched[sec] = true end
            end
          end
        end
      end
    end

    -- SLOW DAMPERS FROM THE HISTOGRAM (engine:damperHistVerdict): the side
    -- of an axle whose wheels move faster (less of the moving time) is the
    -- under-damped side; one click a Build on the slow setting, stiffening
    -- that side unless it is at its limit or its damping-ratio ceiling, else
    -- softening the other. An end running out of travel belongs to its
    -- bottoming chain; the rear with a clear handling verdict belongs to the
    -- balance chain (rearDampers).
    for _, axle in ipairs({
      {e = 'F', corner1 = 'LF', corner2 = 'RF', bottom = travelHitsConsistent(self, 'springsHitsF', self.springsHitsF, th), label = 'Front', enabled = settings.writeDampersFront},
      {e = 'R', corner1 = 'LR', corner2 = 'RR', bottom = travelHitsConsistent(self, 'springsHitsR', self.springsHitsR, th), label = 'Rear', enabled = settings.writeDampersRear},
    }) do
      if axle.enabled then
        local hv = self:damperHistVerdict(axle.e)
        if axle.bottom then
          table.insert(changes, string.format('%s dampers: left to the bottoming chain - this end runs out of travel on most %s (%s)', axle.label, EV_UNIT.many, hv.text))
        elseif axle.e == 'R' and rearHandling then
          table.insert(changes, string.format('Rear dampers: the balance chain decides this Build (rear %s) - %s', rearHandling, hv.text))
        elseif not hv.verdict then
          table.insert(changes, string.format('%s dampers: %s - left alone', axle.label, hv.text))
        else
          for _, corner in ipairs({axle.corner1, axle.corner2}) do
            local bumpSection = damperSection('BUMP', corner)
            local rebSection = damperSection('REBOUND', corner)
            local zb = zetaOf(bumpSection, getCurVal(parsed, bumpSection))
            local zr = zetaOf(rebSection, getCurVal(parsed, rebSection))
            if hv.verdict == 'bumpSoft' then
              if not nearLimit(bumpSection, slowDamperMap.damperBump, true) and not (zb and zb >= hv.ceilBump) then
                writeAbs(slowDamperMap.damperBump[bumpSection], bumpSection, 1, 1,
                  string.format('%s bump %s (stiffer - %s)', axle.label, corner, hv.text), NUDGE_FRACTION.damper)
              else
                writeAbs(slowDamperMap.damperRebound[rebSection], rebSection, -1, 1,
                  string.format('%s rebound %s (softer - bump at its limit%s; %s)', axle.label, corner,
                    zb and string.format(', damping ratio %.2f', zb) or '', hv.text), NUDGE_FRACTION.damper)
              end
            else
              if not nearLimit(rebSection, slowDamperMap.damperRebound, true) and not (zr and zr >= hv.ceilRebound) then
                writeAbs(slowDamperMap.damperRebound[rebSection], rebSection, 1, 1,
                  string.format('%s rebound %s (stiffer - %s)', axle.label, corner, hv.text), NUDGE_FRACTION.damper)
              else
                writeAbs(slowDamperMap.damperBump[bumpSection], bumpSection, -1, 1,
                  string.format('%s bump %s (softer - rebound at its limit%s; %s)', axle.label, corner,
                    zr and string.format(', damping ratio %.2f', zr) or '', hv.text), NUDGE_FRACTION.damper)
              end
            end
          end
        end
      end
    end

    -- v2.1.0: the rear axle's balance lever (v1.9.3 directions, AC's own
    -- tooltips): loose -> rebound AND bump softer; tight -> rebound stiffer
    -- within 30% of its limit. Triggered by the REAR handling signal
    -- (mid+high), which must agree with the chain's direction.
    levers.rearDampers = function(regime, direction, jump)
      if not settings.writeDampersRear then return false, 'module off' end
      -- v2.5.0: say so when the car simply has none (the Sunbeam's log read
      -- "already at their softest" on a car with no damper adjustment).
      local anyRear = false
      for _, corner in ipairs({'LR', 'RR'}) do
        local b, r = damperSection('BUMP', corner), damperSection('REBOUND', corner)
        if getCurVal(parsed, b) or getCurVal(parsed, r) or slowDamperMap.damperBump[b] or slowDamperMap.damperRebound[r] then anyRear = true end
      end
      if not anyRear then return false, 'no adjustable rear dampers on this car' end
      if rearHandling ~= direction then return false, 'rear handling signal is ' .. tostring(rearHandling or rearNote or 'neutral') .. ', not ' .. direction end
      for _, corner in ipairs({'LR', 'RR'}) do
        if calc.touched[damperSection('BUMP', corner)] or calc.touched[damperSection('REBOUND', corner)] then
          return false, 'a rear damper was lifted to the damping-ratio floor this Build - measured next window first'
        end
      end
      local moved = false
      for _, corner in ipairs({'LR', 'RR'}) do
        local bumpSection, rebSection = damperSection('BUMP', corner), damperSection('REBOUND', corner)  -- v2.2.0
        if direction == 'loose' then
          if not nearLimit(rebSection, slowDamperMap.damperRebound, false) then
            local _, ch = writeAbs(slowDamperMap.damperRebound[rebSection], rebSection, -1, jump or steps(snapN),
              'Rear rebound ' .. corner .. ' (SOFTER - rear oversteer; AC: lower rear rebound = more stable at initial turn-in)', NUDGE_FRACTION.damper)
            moved = moved or ch
          end
          if not nearLimit(bumpSection, slowDamperMap.damperBump, false) then
            local _, ch = writeAbs(slowDamperMap.damperBump[bumpSection], bumpSection, -1, jump or steps(snapN),
              'Rear bump ' .. corner .. ' (SOFTER - rear oversteer; AC: lower rear bump = more traction and stability on brake release)', NUDGE_FRACTION.damper)
            moved = moved or ch
          end
        else
          if not nearLimit(rebSection, slowDamperMap.damperRebound, true, 0.30) then
            local _, ch = writeAbs(slowDamperMap.damperRebound[rebSection], rebSection, 1, jump or steps(pushN),
              'Rear rebound ' .. corner .. ' (stiffer - front pushing, rear planted; AC: higher rear rebound = more agile on slow turns needing rotation)', NUDGE_FRACTION.damper)
            moved = moved or ch
          end
        end
      end
      if not moved then
        return false, direction == 'loose' and 'rear bump and rebound already at their softest' or 'rear rebound already within 30% of its stiffest'
      end
      return true, 'moved'
    end


    -- Ride height / rod length - sign convention varies per car so this
    -- carries an explicit warning to sanity-check the direction. The probe
    -- list holds BOTH naming conventions (ROD_LENGTH_* and RIDE_HEIGHT_*)
    -- because cars use one or the other; misses are tracked per corner and
    -- only reported if neither variant existed, instead of logging a
    -- SKIPPED line for whichever convention this car happens not to use.
    --
    -- v1.0.0: RAKE added as a real, coordinated (front-and-rear-together)
    -- lever, prioritised above the old low-speed-only nudge. Direction
    -- confirmed against nine independent sources before writing this:
    -- more rake (front lower relative to rear) reduces understeer; less
    -- rake increases it - unanimous, both through the aero mechanism
    -- (steeper diffuser/floor) and the plain mechanical one (raising one
    -- end shifts weight and CG toward the other). Tied to the HIGH-speed
    -- signal specifically since every source that explained WHY pointed
    -- at cornering speed and load as what makes rake's effect meaningful.
    -- The old low-speed-only, one-end-only nudge is kept as a fallback for
    -- when only the low-speed signal fired - smaller effect, so it keeps
    -- its own smaller fraction, but the "verify direction" caveat is
    -- removed now that the direction has real support behind it rather
    -- than being an untested guess.
   if settings.writeSuspension then
    local rideMap = schemaWithLive(schema.rideHeight)
    -- v1.9.8: both regimes go through balanceVerdict, so a Build can only
    -- ever move the two ends in COMPLEMENTARY directions (or not at all).
    -- The old low-speed branch judged push and snap independently per
    -- end: a real Dacia log shows "LF (more rake for less push) 5 -> 4"
    -- and "LR (less rake for less oversteer) 5 -> 4" in the SAME Build -
    -- both ends down, rake unchanged, the car just 1 click lower. And a
    -- slight oversteer bias is not something rake should be spent on.
    -- v2.1.0: the bottoming RAISE stays here (it's a travel problem, not a
    -- balance lever); the rake moves are levers.rake below, run from the
    -- lever chain. A Build that raised for bottoming does not also rake.
    -- v2.6.0: the bottoming raise is now the LAST lever of each end's
    -- bottoming chain (rideRaiseF/R: one click, one change at a time) -
    -- it no longer raises all four corners 1-2 clicks on top of every
    -- other fix. rideDir (the pit-calibrated direction) moved up to the
    -- levers. A Build whose ride height already moved does not also rake
    -- (calc.rideMoved).

    -- v2.6.0: RIDE HEIGHT TO THE FLOOR (floorClearanceStep). Replaces
    -- v2.3.0's "front to the aero peak", which moved the front toward the
    -- height where its downforce peaks however far that was from the floor
    -- (the Huracan GT3 Evo2: "lower to 22 mm" on a car running 62). Both
    -- ends move by the same millimetres (rake kept), in the calibrated
    -- direction. The aero peak is now only how far down it may go - the
    -- STALL: the splitter's and the diffuser's ground height in fast
    -- corners stays above their own peak heights. Runs before the chains:
    -- a Build that moved ride height here holds rake and the bottoming ride
    -- raise (calc.rideMoved); a raise holds the bottoming chains too
    -- (calc.floorRaised) - one change at a time.
    do
      local bins = windowBins(self)
      local function medianOf(field, upper, positive)
        local v = {}
        for _, b in ipairs(bins) do
          local x = b[field]
          if type(x) == 'number' and (not positive or x > 0) then table.insert(v, x) end
        end
        if #v < 2 then return nil, #v end
        table.sort(v)
        -- an even count takes the cautious middle: the lower clearance, the
        -- higher travel use
        if upper then return v[math.floor(#v / 2) + 1], #v end
        return v[math.floor((#v + 1) / 2)], #v
      end
      local clrF, nF = medianOf('clrF')
      local clrR, nR = medianOf('clrR')
      local useF = medianOf('travelUseF', true, true)
      local useR = medianOf('travelUseR', true, true)
      local slopeF, pairsF, reliableF = self:rideCalSlope('F')
      local slopeR, pairsR, reliableR = self:rideCalSlope('R')
      -- Stall room: the least, over the splitter and the diffuser, of the
      -- fast-corner ground height above that surface's GH_CL peak. The
      -- front falls back to the measured front ride height.
      local peaks = self.aeroPeaks or {}
      local ghAt = {}
      if (self.ghFrontN or 0) >= 30 then ghAt.front = self.ghFrontSum / self.ghFrontN
      elseif (self.hsRhFN or 0) >= 30 then ghAt.front = self.hsRhFSum / self.hsRhFN end
      if (self.ghDiffN or 0) >= 30 then ghAt.diffuser = self.ghDiffSum / self.ghDiffN end
      local stallRoom, stallParts = nil, {}
      for _, role in ipairs({'front', 'diffuser'}) do
        if peaks[role] and ghAt[role] then
          local room = (ghAt[role] - peaks[role]) * 1000
          table.insert(stallParts, string.format('%s %.0f mm above its %.0f mm peak', role == 'front' and 'splitter' or 'diffuser', room, peaks[role] * 1000))
          if not stallRoom or room < stallRoom then stallRoom = room end
        end
      end
      local action, mm, why = floorClearanceStep({clrF = clrF, clrR = clrR, slopeF = slopeF, slopeR = slopeR,
        reliableF = reliableF, reliableR = reliableR, useF = useF, useR = useR,
        bottomingF = (travelSignal(self, 'F', th)) ~= nil, bottomingR = (travelSignal(self, 'R', th)) ~= nil,
        stallRoomMm = stallRoom})
      local result
      if action == 'hold' then
        result = 'HOLD - ' .. why
      else
        local cF, cR, applied = floorClicks(action, mm, slopeF, slopeR, reliableF, reliableR)
        local movedAny, parts = false, {}
        for _, e in ipairs({'F', 'R'}) do
          local front = (e == 'F')
          local clicks, slope, reliable
          if front then clicks, slope, reliable = cF, slopeF, reliableF else clicks, slope, reliable = cR, slopeR, reliableR end
          local up, measured = rideDir(front)
          local dir = (action == 'raise') and up or -up
          local endMoved = false
          for _, c in ipairs(front and {'LF', 'RF'} or {'LR', 'RR'}) do
            local sec = firstPresent('ROD_LENGTH_' .. c, 'RIDE_HEIGHT_' .. c)
            if sec and clicks > 0 then
              local _, ch = writeAbs(rideMap[sec], sec, dir, clicks,
                string.format('Ride height %s (FLOOR CLEARANCE: %s -> %s %d click%s%s; %s)', c, why, action, clicks, clicks == 1 and '' or 's',
                  (reliable and slope) and string.format(', %.1f mm', clicks * math.abs(slope)) or '',
                  measured and 'direction measured in the pits' or '⚠ verify direction on this car'),
                NUDGE_FRACTION.ride, true)
              if ch then
                calc.touched[sec] = 'the floor-clearance target'
                endMoved = true
              else
                local it, cur = rideMap[sec], getCurVal(parsed, sec)
                if it and cur and ((dir < 0 and cur <= it.min + 1e-9) or (dir > 0 and cur >= it.max - 1e-9)) then
                  table.insert(rangeLimits, string.format('ride height %s is at the end of its range - the floor-clearance target wanted it %s',
                    c, action == 'raise' and 'higher' or 'lower'))
                end
              end
            end
          end
          movedAny = movedAny or endMoved
          table.insert(parts, string.format('%s %d click%s%s', e, clicks, clicks == 1 and '' or 's', endMoved and '' or ' (not moved)'))
        end
        if movedAny then
          calc.rideMoved = true
          if action == 'raise' then calc.floorRaised = true end
        end
        result = string.format('%s %.0f mm (%s) - %s', string.upper(action), applied, table.concat(parts, ', '), why)
      end
      local hitF, hitR = 0, 0
      for _, b in ipairs(bins) do hitF, hitR = hitF + (b.floorHitsF or 0), hitR + (b.floorHitsR or 0) end
      local function mmText(v) return v and string.format('%.0f', v) or 'n/a' end
      local function calText(slope, np, reliable)
        if not slope then return 'none' end
        return string.format('%.2f mm/click from %d pair%s%s', slope, np or 0, np == 1 and '' or 's', reliable and '' or ' (not reliable yet)')
      end
      calc.notes.floor = string.format('lowest point on the median %s F %s / R %s mm over %d %s (target %d) · contacts F %.1f / R %.1f per %s · stall room %s · calibration F %s · R %s -> %s',
        EV_UNIT.one, mmText(clrF), mmText(clrR), math.min(nF, nR), EV_UNIT.many, FLOOR_TARGET_MM,
        hitF / math.max(#bins, 1), hitR / math.max(#bins, 1), EV_UNIT.one,
        #stallParts > 0 and table.concat(stallParts, ', ') or 'n/a (no ground-effect data)',
        calText(slopeF, pairsF, reliableF), calText(slopeR, pairsR, reliableR), result)
      calc.notes.ride = result
    end

    -- RAKE lever. Static ride heights are captured in the pits from
    -- car.rideHeight (metres, front [0] / rear [1]), so the app knows the
    -- car's actual rake and can refuse to take it below RAKE_MIN_MM. The
    -- first v2.0.0 night took a Huracan's rake negative - four "less rake"
    -- Builds, front +4 / rear -4 clicks, front ended higher than rear. The
    -- driver: "Front shouldn't be higher than the rear." Correct; a floor.
    local RAKE_MIN_MM = 3
    local function measuredRakeMm()
      if self.rideHeightCaptured and self.staticRideHeightR and self.staticRideHeightR > 0 then
        return (self.staticRideHeightR - self.staticRideHeightF) * 1000
      end
      return nil
    end
    levers.rake = function(regime, direction)
      if not settings.writeSuspension then return false, 'module off' end
      -- v2.6.0: was "raised for bottoming" - that raise is the bottoming
      -- chain's last lever now, and it (or the floor-clearance step) says so.
      if calc.rideMoved then return false, 'ride height already moved this Build (bottoming chain or floor clearance) - rake waits a window' end
      for _, probe in ipairs(SETUP_PROBE.rideHeight) do
        local by = calc.touched[probe.section]
        if by then return false, string.format('%s already set by %s this Build - rake waits a window', probe.section, type(by) == 'string' and by or 'a calculated target') end
      end
      local rake = measuredRakeMm()
      if direction == 'loose' and rake and rake <= RAKE_MIN_MM then
        return false, string.format('rake already %+.0f mm (floor %+d mm) - front must not come up to the rear', rake, RAKE_MIN_MM)
      end
      local moved = false
      for _, probe in ipairs(SETUP_PROBE.rideHeight) do
        local front = (probe.corner == 'LF' or probe.corner == 'RF')
        local schemaItem = rideMap[probe.section]
        if getCurVal(parsed, probe.section) or schemaItem then
          local _, ch
          local up, measured = rideDir(front)  -- v2.5.0: +1 click raises (or lowers, if the pits measured so)
          local dirNote = measured and 'direction measured in the pits' or '⚠ verify direction on this car'
          if direction == 'tight' then
            local dir = (front and -1 or 1) * up  -- lower front, raise rear = more rake
            local stallNote = front and rideHeightStallCaveat(self) or ''
            _, ch = writeAbs(schemaItem, probe.section, dir, 1,
              string.format('Ride height %s (more rake for less %s-speed push - %s%s)%s',
                probe.corner, regime == 'high' and 'high' or 'low', dirNote, rake and string.format('; rake now %+.0f mm', rake) or '', stallNote), NUDGE_FRACTION.rake, true)
          else
            local dir = (front and 1 or -1) * up  -- raise front, lower rear = less rake
            _, ch = writeAbs(schemaItem, probe.section, dir, 1,
              string.format('Ride height %s (less rake for less %s-speed oversteer - %s%s)',
                probe.corner, regime == 'high' and 'high' or 'low', dirNote, rake and string.format('; rake now %+.0f mm, floor %+d', rake, RAKE_MIN_MM) or ''), NUDGE_FRACTION.rake, true)
          end
          moved = moved or (ch == true)
        end
      end
      if not moved then return false, 'no ride height sections on this car (or at their limits)' end
      return true, 'moved'
    end
   end -- settings.writeSuspension (ride height / rake)

    -- Toe, rebuilt v1.9.9. Was a ONE-WAY RATCHET - the fourth found in this
    -- project: any turninPush over threshold added front toe-out, any
    -- rearToeEvents over threshold added rear toe-in, 2 clicks each, every
    -- Build, and nothing ever took either back. Both signals fire in every
    -- real session (turn-in push in 15-35 corners, rear slip asymmetry in
    -- 7-13), so on a real Corvette GT3 log four Builds in 17 minutes walked
    -- front toe 11 -> 19 of 20 (zero toe is 10: +0.1 deg to +0.9 deg
    -- toe-out) and rear 14 -> 6 (+0.4 deg toe-OUT to -0.4 deg toe-IN).
    -- Alignment is the finest lever on the car and it was moving fastest.
    --
    -- Now: toe follows the balance verdict, one click per Build, and can
    -- come BACK toward zero:
    --   front  tight, and turn-in push in >15% of corners -> +1 toe-out
    --          loose, and currently toe-OUT                 -> -1 (calmer
    --          turn-in; never past zero into toe-in)
    --   rear   loose (rear signal), rear instability events -> -1 (toe-in)
    --          tight, and currently toe-IN                  -> +1 (free the
    --          rear; never past zero into toe-out)
    -- "Currently toe-out/in" needs to know where zero sits in this car's
    -- stored units - readSetupItem's `zero`, from the live setup.ini. When
    -- unknown (baked-only car), only the forward moves run, as before.
    local toeMap = schemaWithLive(schema.toe)
    local toeLowVerdict, _, _, toeLowNote = regimeVerdict(self, 'low', th)
    local toeRearVerdict, toeRearSnapN, toeRearPushN, toeRearNote = rearHandlingSignal(self, th)
    local toeCorners = math.max(self.corneringSamples or 0, 20)
    local turninRate = self.turninPush / toeCorners * 100
    -- v2.0.0: the trigger signal for each forward move must show in at
    -- least half the window's clean laps.
    local tinA, tinC, tinOk = lapSupport(self, 'turninPush')
    local rtA, rtC, rtOk = lapSupport(self, 'rearToeEvents')
    -- v2.1.0: two levers, run from the chain. Each writes both corners of
    -- its axle, one click, and reports why it couldn't when it couldn't.
    local function toeSections(front)
      local out = {}
      for _, probe in ipairs(SETUP_PROBE.toe) do
        local isFront = (probe.corner == 'LF' or probe.corner == 'RF')
        if isFront == front then table.insert(out, probe) end
      end
      return out
    end
    levers.toeFront = function(regime, direction)
      if not settings.writeToeFront then return false, 'module off' end
      local moved = false
      for _, probe in ipairs(toeSections(true)) do
        local it = toeMap[probe.section]
        local cur = getCurVal(parsed, probe.section)
        local zero = it and it.zero
        local _, ch = false, false
        if direction == 'tight' then
          if not (self.turninPush > th and turninRate > 15) then
            return false, string.format('turn-in push only in %.0f%% of corners (bar 15%%) - toe-out not the answer', turninRate)
          elseif not tinOk then
            return false, lapSupportNote('turn-in push', tinA, tinC)
          end
          _, ch = writeAbs(it, probe.section, 1, 1,
            string.format('Toe %s (more toe-out, sharper turn-in; car pushing, turn-in push in %.0f%% of corners)', probe.corner, turninRate), NUDGE_FRACTION.toe)
        else
          if not (cur and zero and cur > zero) then return false, 'front toe already at/inside zero - nothing to take back' end
          _, ch = writeAbs(it, probe.section, -1, 1,
            'Toe ' .. probe.corner .. ' (LESS toe-out - car is loose, calmer turn-in; toward zero, never into toe-in)', NUDGE_FRACTION.toe)
        end
        moved = moved or (ch == true)
      end
      if not moved then return false, 'no front toe section on this car (or at its limit)' end
      return true, 'moved'
    end
    levers.toeRear = function(regime, direction)
      if not settings.writeToeRear then return false, 'module off' end
      local moved = false
      for _, probe in ipairs(toeSections(false)) do
        local it = toeMap[probe.section]
        local cur = getCurVal(parsed, probe.section)
        local zero = it and it.zero
        local _, ch = false, false
        if direction == 'loose' then
          if toeRearVerdict ~= 'loose' then return false, 'rear handling signal is not loose' end
          if not (self.rearToeEvents > th) then return false, 'no rear instability events to answer' end
          if not rtOk then return false, lapSupportNote('rear instability', rtA, rtC) end
          _, ch = writeAbs(it, probe.section, -1, 1,
            string.format('Toe %s (more toe-in, more stability; rear loose, %d rear instability events)', probe.corner, self.rearToeEvents), NUDGE_FRACTION.toe)
        else
          if not (cur and zero and cur < zero) then return false, 'rear toe already at/inside zero - nothing to take back' end
          _, ch = writeAbs(it, probe.section, 1, 1,
            'Toe ' .. probe.corner .. ' (LESS toe-in - car pushing, free the rear; toward zero, never into toe-out)', NUDGE_FRACTION.toe)
        end
        moved = moved or (ch == true)
      end
      if not moved then return false, 'no rear toe section on this car (or at its limit)' end
      return true, 'moved'
    end

    -- Brake bias, DIFFERENTIAL and AERO each get their OWN toggle as of
    -- v1.9.0, by request - they were one combined writeDiffAeroBrake switch
    -- from v1.4.0 (which pulled them out of Build's default scope) through
    -- v1.5.0 (which put them back on by default). Three separate levers on
    -- three unrelated subsystems had no reason to share a switch once every
    -- other module had its own; keeping them bundled just meant freezing a
    -- dialled-in brake bias also froze the wings. As everywhere else, only
    -- the WRITE is gated - all three still compute and show in the live
    -- advice panel regardless.
   if settings.writeBrakeBias then

    -- Brake bias: absolute % (46-68 range typical), so schema midpoint ± N%
    -- makes sense here too. Softer signal than others - only writes when a
    -- clear direction shows up. Like ride height, the probe list carries
    -- both naming conventions (FRONT_BIAS / BRAKE_BIAS) and a car has one
    -- or the other, so a miss on the unused name isn't worth reporting -
    -- we stop after the first one that lands.
    --
    -- v2.3.0: ONE CALCULATED WRITE PER CAR, THEN ADVICE ONLY. The driver's
    -- rule: "moving brakes too far forward/backward has a big influence on
    -- understeer/oversteer/stability on entry. Make brake balance advise
    -- only after 1 build." So:
    --   * the target is where both axles reach the limit together - the
    --     front's measured share of tyre load under hard straight-line
    --     braking, corrected for tyre radii - plus a 1% forward stability
    --     margin (engine:biasTarget);
    --   * the single write moves at most BIAS_MAX_JUMP (3%) toward it;
    --   * it is HELD if the move would feed an entry problem the car already
    --     shows consistently: forward (more entry push / stability) is held
    --     if turn-in push or front lockups dominate; rearward (more entry
    --     rotation) is held if lift-off/entry oversteer, rear lockups or a
    --     loose rear dominate;
    --   * once evaluated with enough braking data (written, already there,
    --     or held) the car is marked done - every later Build leaves bias
    --     alone and the BRAKE advice line carries the target and the
    --     lockup trims for the driver to apply in small steps.
    -- The v1.x lockup +-1 writer is retired (its advice lives on).
    local biasMap = schemaWithLive(schema.brakeBias)
    local biasSec = firstPresent('FRONT_BIAS', 'BRAKE_BIAS')
    local tgt, tgtInfo = self:biasTarget()
    self.lastBiasTarget, self.lastBiasInfo = tgt, tgtInfo
    if not biasSec then
      table.insert(changes, 'Brake bias: SKIPPED (no FRONT_BIAS/BRAKE_BIAS on this car)')
    elseif self:biasBaselineDone(carFolder) then
      table.insert(changes, 'Brake bias: advice only on this car (its one calculated write was used by an earlier Build) - '
        .. tostring(tgtInfo) .. ' - see the BRAKE advice line for trims')
    elseif not tgt then
      table.insert(changes, 'Brake bias: calculated target not ready - ' .. tostring(tgtInfo) .. ' (the one-time write waits for it; nothing written)')
    -- v2.5.2: an overridden gate (the test button) is too little evidence to
    -- spend the once-per-car decision on - 30 Sep it was HELD on 11 corners,
    -- 4 Oct written on 5 braking zones of a gravel stage.
    elseif gateOverridden then
      table.insert(changes, string.format('Brake bias: calculated %.1f%% - the one-time write waits for a Build that passes the lap gate (this one was overridden); nothing written - %s', tgt, tostring(tgtInfo)))
    else
      local item = biasMap[biasSec]
      local cur = getCurVal(parsed, biasSec)
      local asFraction = cur and cur <= 1.5
      local curPct = cur and (asFraction and cur * 100 or cur)
      if not curPct then
        table.insert(changes, 'Brake bias: SKIPPED (no current value on the car)')
      else
        self.liveBiasPct = curPct  -- v2.5.0: for the BRAKE line's lockups-vs-calculation check
        -- v2.5.0: a target outside the car's own bias range is worth knowing.
        if item and item.min and item.max then
          local mn, mx = item.min, item.max
          if asFraction then mn, mx = mn * 100, mx * 100 end
          if tgt > mx + 0.25 or tgt < mn - 0.25 then
            table.insert(rangeLimits, string.format('brake bias wants %.1f%% front, the car\'s range is %.0f-%.0f%%', tgt, mn, mx))
          end
        end
        local delta = tgt - curPct
        local lowV = regimeVerdict(self, 'low', th)
        local rearV = rearHandlingSignal(self, th)
        local _, _, tinOkB = lapSupport(self, 'turninPush')
        local _, _, lfOk = lapSupport(self, 'lockF')
        local _, _, lrOk = lapSupport(self, 'lockR')
        local _, _, loOk = lapSupport(self, 'liftOffSnap')
        local hold
        if delta > 0 then
          if self.turninPush > th and tinOkB and (lowV == 'tight') then hold = 'moving forward adds entry push, and the car already pushes on turn-in'
          elseif self.lockF > self.lockR and self.lockF >= th and lfOk then hold = 'the fronts already lock more than the rears - forward would make that worse' end
        elseif delta < 0 then
          if self.liftOffSnap > th and loOk then hold = 'moving rearward adds entry rotation, and the car already steps out on lift-off/entry'
          elseif self.lockR > self.lockF and self.lockR >= th and lrOk then hold = 'the rears already lock more than the fronts - rearward would make that worse'
          elseif rearV == 'loose' then hold = 'moving rearward adds entry rotation to a car whose rear is already loose' end
        end
        local capped = clamp(delta, -BIAS_MAX_JUMP, BIAS_MAX_JUMP)
        local stepPct = (item and item.step and item.step > 0) and (asFraction and item.step * 100 or item.step) or 1
        local clicks = math.floor(math.abs(capped) / stepPct + 0.5)
        if hold then
          table.insert(changes, string.format('Brake bias: calculated %.1f%% vs your %.1f%% - HELD, %s. Advice only from here on this car.', tgt, curPct, hold))
          self:markBiasBaselineDone(carFolder)
        elseif clicks == 0 then
          table.insert(changes, string.format('Brake bias: already at the calculated target (%.1f%% vs %.1f%%) - advice only from here on this car.', curPct, tgt))
          self:markBiasBaselineDone(carFolder)
        else
          local _, ch = writeAbs(item, biasSec, delta > 0 and 1 or -1, clicks,
            string.format('Brake bias (ONE-TIME calculated baseline: %s%s; %s entry)', tgtInfo,
              math.abs(delta) > BIAS_MAX_JUMP and string.format(', capped at %.0f%% this move', BIAS_MAX_JUMP) or '',
              delta > 0 and 'more stable / slightly more push on' or 'more rotation / slightly looser on'), 0.02, true)
          if ch then
            calc.touched[biasSec] = true
            self:markBiasBaselineDone(carFolder)
            table.insert(changes, 'Brake bias: that was its one calculated write on this car - advice only from the next Build on (trim in small steps from the BRAKE line).')
          end
        end
      end
    end
   end -- settings.writeBrakeBias

   if settings.writeDifferential then
    -- DIFFERENTIAL, new in 4.6.0. RWD/FWD only - AWD's centre diff is a
    -- controller chain, not these fields (see the DIFFERENTIAL advice
    -- module notes for why). Only POWER and PRELOAD are touched: both
    -- detection signals are specifically about power-on behaviour (gas >
    -- 0.4 in both), so there's no telemetry-backed basis yet for moving
    -- COAST, which governs off-throttle behaviour - leaving it alone here
    -- rather than guessing.
    --
    -- 4.8.1: these use quietSkip, and report once at the end instead of
    -- per-item. Verified against eight real cars' setup.ini that partial
    -- availability is normal, not an edge case - some expose DIFF_POWER
    -- and DIFF_COAST but no DIFF_PRELOAD, one exposes only DIFF_PRELOAD,
    -- and two expose no diff sections at all. Without quietSkip those
    -- cars get a "SKIPPED - not in your setup file" line for a setting
    -- they simply don't have, which reads like a fault rather than a
    -- normal property of the car.
    if self.driveType ~= 'AWD' and self.driveType ~= '4WD' then
      local powerMap = schemaWithLive(schema.diffPower)
      local preloadMap = schemaWithLive(schema.diffPreload)
      -- Tries DIFF_POWER first, DIFF_RAMP_POWER second - same "probe both
      -- conventions, report skip only if both miss" pattern already used
      -- for ride height (ROD_LENGTH_*/RIDE_HEIGHT_*) and brake bias
      -- (FRONT_BIAS/BRAKE_BIAS) below. Confirmed genuinely necessary, not
      -- theoretical: a scan of 1561 real saved setups found 92 using
      -- DIFF_RAMP_POWER/DIFF_RAMP_COAST, which the writer silently
      -- couldn't reach before v1.3.1 despite SETUP_PROBE already listing
      -- it - this hardcoded the literal 'DIFF_POWER' name directly rather
      -- than iterating SETUP_PROBE.diffPower like the ride-height writer
      -- does, so adding it to the probe list alone hadn't been enough.
      local function writeDiffPower(direction, clicks, desc)
        if writeAbs(powerMap['DIFF_POWER'], 'DIFF_POWER', direction, clicks, desc, NUDGE_FRACTION.diff, true) then return true end
        return writeAbs(powerMap['DIFF_RAMP_POWER'], 'DIFF_RAMP_POWER', direction, clicks, desc, NUDGE_FRACTION.diff, true)
      end
      -- v1.9.9: the two diff signals are OPPOSITE levers, and they were
      -- compared with ">=" on counts as small as 3 vs 4. Real Corvette GT3
      -- log, two Builds five minutes apart: "less lock" (3 rotation vs 2
      -- diverging events) then "more lock" (4 diverging vs 3 rotation) -
      -- power 20 -> 10 -> 30, preload 100 -> 80 -> 100. Flip-flopping on
      -- noise. Now the acting signal needs HISTOGRAM_MIN_EVENTS of its own
      -- AND the same 25% dominance every other balance rule uses.
      local diffTried, diffDone = false, false
      local rotN, divN = self.diffRotationEvents, self.diffEvents
      -- v2.0.0: lap consistency - the acting signal must show in at least
      -- half the window's clean laps.
      local rotA, rotC, rotOk = lapSupport(self, 'diffRotationEvents')
      local divA, divC, divOk = lapSupport(self, 'diffEvents')
      if rotN >= HISTOGRAM_MIN_EVENTS and rotN > divN * 1.25 and not rotOk then
        table.insert(changes, 'Differential: ' .. lapSupportNote('forced-together (too much lock)', rotA, rotC))
      elseif divN >= HISTOGRAM_MIN_EVENTS and divN > rotN * 1.25 and not divOk then
        table.insert(changes, 'Differential: ' .. lapSupportNote('diverging (too little lock)', divA, divC))
      elseif rotN >= HISTOGRAM_MIN_EVENTS and rotN > divN * 1.25 then
        -- Too much lock: both rears forced to near-equal slip under
        -- cornering load - reduce power lock and preload.
        diffTried = true
        if writeDiffPower(-1, steps(rotN),
          string.format('Diff power (less lock, wheels are being forced together under load; %d vs %d diverging)', rotN, divN)) then diffDone = true end
        if writeAbs(preloadMap['DIFF_PRELOAD'], 'DIFF_PRELOAD', -1, steps(rotN),
          'Diff preload (less, to match reduced power lock)', NUDGE_FRACTION.diff, true) then diffDone = true end
      elseif divN >= HISTOGRAM_MIN_EVENTS and divN > rotN * 1.25 then
        -- Too little lock: asymmetric slip with no cornering load to
        -- explain it - increase preload first (cheaper, more direct fix
        -- for an open-diff-like symptom), power lock as a secondary lever.
        diffTried = true
        local preDone, preCh = writeAbs(preloadMap['DIFF_PRELOAD'], 'DIFF_PRELOAD', 1, steps(divN),
          string.format('Diff preload (more, wheels are diverging with no load to explain it; %d vs %d forced-together)', divN, rotN), NUDGE_FRACTION.diff, true)
        if preDone then diffDone = true end
        -- v2.5.2: "backing up the preload increase" only when the preload
        -- actually went up (it can't on a car without DIFF_PRELOAD, or at
        -- its maximum) - the Sunbeam logged it twice with no preload line.
        if writeDiffPower(1, steps(divN),
          preCh and 'Diff power (more lock, to back up the preload increase)'
            or string.format('Diff power (more lock, wheels are diverging with no load to explain it; %d vs %d forced-together)', divN, rotN)) then diffDone = true end
      elseif rotN > th or divN > th then
        table.insert(changes, string.format('Differential: %d forced-together / %d diverging events - %s, left alone',
          rotN, divN, (math.max(rotN, divN) < HISTOGRAM_MIN_EVENTS) and ('not enough evidence yet (needs ' .. HISTOGRAM_MIN_EVENTS .. ')') or 'neither clearly dominant'))
      end
      if diffTried and not diffDone then
        table.insert(changes, 'Differential: SKIPPED (this car exposes no adjustable DIFF_POWER/DIFF_RAMP_POWER/DIFF_PRELOAD in your setup, and no readable schema)')
      end
    end
   end -- settings.writeDifferential

    -- v2.5.0: DIFF COAST as a balance lever - off-throttle balance only.
    -- The writer above deliberately never touches coast (both its signals
    -- are power-on); this lever is the only thing that does, and only for
    -- the phase coast lock governs: more lock steadies lift-off / entry
    -- oversteer, less lock frees entry push. Mid-corner problems are left
    -- to the levers that act there. RWD/FWD only.
    levers.diff = function(regime, direction)
      if not settings.writeDifferential then return false, 'module off' end
      if regime ~= 'low' then return false, 'low-speed only' end
      if self.driveType == 'AWD' or self.driveType == '4WD' then return false, 'AWD - the centre diff is not this lever' end
      local sec = firstPresent('DIFF_COAST', 'DIFF_RAMP_COAST')
      local coastMap = schemaWithLive(schema.diffCoast)
      if not sec and not coastMap.DIFF_COAST then return false, 'no adjustable diff coast on this car' end
      sec = sec or 'DIFF_COAST'
      if calc.touched[sec] then return false, 'diff coast already set this Build' end
      if direction == 'loose' then
        local nEv = self.liftOffSnap or 0
        local _, _, ok = lapSupport(self, 'liftOffSnap')
        if nEv < th or not ok then return false, 'the oversteer is not on lift-off/entry - coast lock only acts there' end
        local _, ch = writeAbs(coastMap[sec], sec, 1, 1,
          string.format('Diff coast (more lock - steadier on lift-off and entry; %d lift-off oversteer events)', nEv), NUDGE_FRACTION.diff)
        if ch then return true, 'moved' end
        return false, 'diff coast at its maximum'
      end
      local nEv = self.turninPush or 0
      local _, _, ok = lapSupport(self, 'turninPush')
      if nEv < th or not ok then return false, 'the push is not on entry - coast lock only acts there' end
      local _, ch = writeAbs(coastMap[sec], sec, -1, 1,
        string.format('Diff coast (less lock - more rotation on entry; %d turn-in push events)', nEv), NUDGE_FRACTION.diff)
      if ch then return true, 'moved' end
      return false, 'diff coast at its minimum'
    end

   if settings.writeAero then
    -- Wings, rebuilt v1.9.4. Previously a one-way ratchet: direction was
    -- hard-coded +1 for both, front wing rose on every high-speed push and
    -- rear wing on every high-speed snap, BOTH fired in the same Build when
    -- both crossed threshold, and nothing could ever bring either down. A
    -- mixed car at high speed therefore walked both wings to maximum and
    -- paid for it in drag on every straight, with no signal that would ever
    -- push back - the same "rule that only resolves one way" defect as the
    -- rear rebound (v1.9.3). Real log: front splitter already pinned at its
    -- max, rear wing 5->6->7 with nothing to stop it.
    --
    -- Aero BALANCE is a ratio, exactly like ARB: high-speed push is cured
    -- by more front wing OR less rear wing, and the two are equivalent for
    -- balance - the second costs less drag. So this now mirrors the ARB
    -- writer precisely: prefer adding to the axle that wants more, but if
    -- that wing is already near its maximum, reduce the OTHER wing instead;
    -- and when both signals fire, act only on the larger and say so, rather
    -- than adding downforce at both ends and calling it balance. Near-max
    -- status is snapshotted once BEFORE either writes, so the second
    -- decision can never be made against the first's own output (the
    -- v1.4.1 ARB self-cancellation bug).
    local wingFMap = schemaWithLive(schema.wingFront)
    local wingRMap = schemaWithLive(schema.wingRear)
    -- v1.9.9: which setup section IS the rear wing on this car. The fixed
    -- WING_1=front / WING_2=rear guess is wrong on a real Corvette Z06 GT3:
    -- its aero.ini is BODY / SPLITTER R / SPLITTER L / REAR WING / DIFFUSER
    -- R / DIFFUSER L, so the rear wing is WING_3 - and setup.ini exposes
    -- exactly [WING_3] "Rear wing". Four Builds logged "Rear wing: SKIPPED
    -- (WING_2 not in your setup file)" on a car with a rear wing spinner
    -- in front of the driver. aero.ini NAMEs are readable since v1.9.6
    -- (aeroWingIndex, role -> index); prefer that index when the car's
    -- live setup actually has that section, else the old guess.
    local function resolveWingSection(role, fallback, map)
      local idx = self.aeroWingIndex and self.aeroWingIndex[role]
      if idx then
        local sec = 'WING_' .. idx
          if (liveSetup and liveSetup[sec]) or getCurVal(parsed, sec) or map[sec] then
          if liveSetup and liveSetup[sec] then
            local it = liveSetup[sec]
            if not map[sec] then
              map[sec] = {section = sec, min = it.min, max = it.max, step = (it.step and it.step > 0) and it.step or 1, label = sec}
            end
            -- Not in MANAGED_SECTIONS (v1.8.1 keeps the general sync to
            -- probed names), so the live value is synced here, for this
            -- one section, right before it's written from.
            if not MANAGED_SECTIONS[sec] and not it.readOnly then
              local looksInteger = math.abs(it.value - math.floor(it.value + 0.5)) < 1e-6
              ensureSectionValue(parsed, sec, string.format(looksInteger and '%.0f' or '%.3f', it.value))
            end
          end
          return sec
        end
      end
      return fallback
    end
    local wingF = resolveWingSection('front', SETUP_PROBE.wingFront[1] and SETUP_PROBE.wingFront[1].section, wingFMap)
    local wingR = resolveWingSection('rear', SETUP_PROBE.wingRear[1] and SETUP_PROBE.wingRear[1].section, wingRMap)
    local function nearMax(section, map)
      local cur = getCurVal(parsed, section)
      local it = map[section]
      if not cur or not it then return false end
      return cur >= it.max - it.step * 1.5
    end
    local function nearMin(section, map)
      local cur = getCurVal(parsed, section)
      local it = map[section]
      if not cur or not it then return false end
      return cur <= it.min + it.step * 1.5
    end

    -- v2.1.0: the wing lever, run from the chain (high-speed regime only -
    -- wings do nothing at low speed, which is exactly why they're the
    -- first lever there and never a lever at low speed). Prefer adding to
    -- the axle that wants more; if that wing is near its maximum, reduce
    -- the OTHER one (same balance shift, less drag). Near-max/min are
    -- snapshotted before the write.
    levers.wings = function(regime, direction, jump)
      if not settings.writeAero then return false, 'module off' end
      if regime ~= 'high' then return false, 'aero lever, high-speed only' end
      local frontNearMax = wingF and nearMax(wingF, wingFMap)
      local rearNearMax = wingR and nearMax(wingR, wingRMap)
      local frontNearMin = wingF and nearMin(wingF, wingFMap)
      local rearNearMin = wingR and nearMin(wingR, wingRMap)
      local w
      if direction == 'tight' then
        if wingF and not frontNearMax then
          w = {sec = wingF, map = wingFMap, dir = 1, n = self.highPush,
            desc = string.format('Front wing (more downforce, less high-speed push; %d push vs %d oversteer)', self.highPush, self.highSnap)}
        elseif wingR and not rearNearMin then
          w = {sec = wingR, map = wingRMap, dir = -1, n = self.highPush,
            desc = 'Rear wing (LESS - front wing already near maximum, so rebalance from the other end; less drag too)'}
        else
          return false, 'front wing at maximum and rear at minimum - nothing left in the wings for push'
        end
      else
        if wingR and not rearNearMax then
          w = {sec = wingR, map = wingRMap, dir = 1, n = self.highSnap,
            desc = string.format('Rear wing (more downforce, less high-speed oversteer; %d oversteer vs %d push)', self.highSnap, self.highPush)}
        elseif wingF and not frontNearMin then
          w = {sec = wingF, map = wingFMap, dir = -1, n = self.highSnap,
            desc = 'Front wing (LESS - rear wing already near maximum, so rebalance from the other end; less drag too)'}
        else
          return false, 'rear wing at maximum and front at minimum - nothing left in the wings for oversteer'
        end
      end
      local _, ch = writeAbs(w.map[w.sec], w.sec, w.dir, jump or steps(w.n),
        w.desc .. (jump and string.format(' [measured-response jump: %d]', jump) or ''), NUDGE_FRACTION.wing)
      if not ch then return false, 'no adjustable wing section on this car' end
      return true, 'moved'
    end
   end -- settings.writeAero

  -----------------------------------------------------------------------------
  -- v2.1.0: THE LEVER CHAIN RUNNER. One balance lever per regime per
  -- Build, in physics priority order, so the next window measures what
  -- that one lever did. See LEVER_CHAINS / leverLedger* for the ledger
  -- that freezes a lever after two moves that didn't reduce the signal.
  -----------------------------------------------------------------------------
  do
    local lowV, lowPush, lowSnap, lowNote, lowRate = regimeVerdict(self, 'low', th)
    local highV, highPush, highSnap, highNote, highRate = regimeVerdict(self, 'high', th)
    local ledger = self:leverLedgerFor(carFolder)
    self.leverPendingThisBuild = {}
    -- Cross-regime conflict: opposite verdicts at low and high speed. A
    -- mechanical lever (ARB, dampers, toe, rake) bleeds into high speed and
    -- would fight the wing; the wing does nothing at low speed. So act on
    -- the HIGH chain only and hold the low one for this Build - the next
    -- window shows whether the aero change alone moved either signal.
    local conflict = lowV and highV and lowV ~= highV
    local function pushRate(regime) local p, s = regimeCounts(self, regime); local c = math.max(self.corneringSamples or 0, 20); return p / c * 100 end
    local function snapRate(regime) local p, s = regimeCounts(self, regime); local c = math.max(self.corneringSamples or 0, 20); return s / c * 100 end
    -- v2.6.0: a key is a balance regime ('low-loose') or an end running
    -- out of travel ('travelF-bottoming'); verdict, rate and noise of both
    -- come from here.
    local function verdictOf(regime)
      local e = regime:match('^travel([FR])$')
      if e then return (travelSignal(self, e, th)) end
      return (regime == 'low') and lowV or highV
    end
    local function rateOf(key)
      local regime, dir = key:match('^(%a+)%-(%a+)$')
      local e = regime:match('^travel([FR])$')
      if e then return select(3, travelSignal(self, e, th)) end
      return (dir == 'loose') and snapRate(regime) or pushRate(regime)
    end
    local function seOf(key)
      local regime, dir = key:match('^(%a+)%-(%a+)$')
      local which = regime:find('^travel') and 'hits' or (dir == 'loose' and 'snap' or 'push')
      local _, se = self:lapRateStats(regime, which)
      return se
    end

    ---------------------------------------------------------------------------
    -- v2.4.0: BRANCH PASSES (see the block above parseBranchStore). Review
    -- every branch of this car at this track BEFORE any lever moves: apply
    -- last window's judgements to the moves, end a pass whose problem is
    -- gone, and settle last Build's put-backs.
    ---------------------------------------------------------------------------
    local branchAll = parseBranchStore(settings.branchState)
    local branchHold = {}   -- key -> why this branch sits this Build out
    local function branchFor(key)
      for _, b in ipairs(branchAll) do
        if b.car == carFolder and b.track == trackFolder and b.key == key then return b end
      end
      return nil
    end
    local function rateText(r, se)
      return string.format('%.1f%s', r or 0, se and string.format(' (±%.1f)', se) or '')
    end
    local function movesText(b)
      local parts = {}
      for _, m in ipairs(b.moves or {}) do
        local s = {}
        for sec, ba in pairs(m.secs or {}) do table.insert(s, string.format('%s %s→%s', sec, fmtNum(ba[1]), fmtNum(ba[2]))) end
        table.sort(s)
        table.insert(parts, string.format('%s %s [%s]', m.lever, m.result, table.concat(s, ', ')))
      end
      return #parts > 0 and table.concat(parts, '; ') or 'none'
    end
    local function snapshotManaged()
      local s = {}
      for section in pairs(MANAGED_SECTIONS) do
        local v = getCurVal(parsed, section)
        if v then s[section] = v end
      end
      return s
    end
    -- Section -> its setup item, so a put-back goes through writeTuned and
    -- every guard still applies (damping floor, LUT curve, calculated
    -- targets set this Build).
    local function itemFor(section)
      if arbMap[section] then return arbMap[section] end
      for _, list in pairs(schema) do
        if type(list) == 'table' then
          local m = schemaWithLive(list)
          if m[section] then return m[section] end
        end
      end
      return nil
    end
    -- Returns ok, note, value now.
    local function setTo(section, want, desc)
      local cur = getCurVal(parsed, section)
      if not cur then return false, 'no current value', nil end
      if math.abs(cur - want) < 1e-6 then return true, 'already there', cur end
      local it = itemFor(section)
      if it and it.step and it.step > 0 then
        local clicks = math.floor(math.abs(want - cur) / it.step + 0.5)
        if clicks < 1 then return true, 'already within one click', cur end
        writeTuned(it, section, want > cur and 1 or -1, clicks, 0.07, desc)
      else
        local looksInteger = math.abs(want - math.floor(want + 0.5)) < 1e-6
        ensureSectionValue(parsed, section, string.format(looksInteger and '%.0f' or '%.2f', want))
        table.insert(changes, string.format('%s: %s → %s', desc, fmtNum(cur), fmtNum(want)))
      end
      local now = getCurVal(parsed, section)
      if now and math.abs(now - cur) > 1e-6 then
        return true, (math.abs(now - want) < 1e-6) and 'set' or ('nearest on the grid: ' .. fmtNum(now)), now
      end
      return false, 'refused by a guard (see the line above)', cur
    end
    -- Put back every section a no-effect move changed (branchKeepValues).
    local function putBack(b)
      local keep, expected, why = branchKeepValues(b.moves)
      local reverted, notes = {}, {}
      local secs = {}
      for sec in pairs(keep) do table.insert(secs, sec) end
      table.sort(secs)
      for _, sec in ipairs(secs) do
        local want, exp = keep[sec], expected[sec]
        if why[sec] ~= '' and exp and math.abs(want - exp) > 1e-6 then
          local cur = getCurVal(parsed, sec)
          local off
          for lever in why[sec]:gmatch('[^+]+') do
            if LEVER_MODULE[lever] and not settings[LEVER_MODULE[lever]] then off = lever end
          end
          if not cur then
            table.insert(notes, sec .. ' is not in the setup any more - left')
          elseif off then
            table.insert(notes, string.format('%s left at %s (the %s module is now off)', sec, fmtNum(cur), off))
          elseif math.abs(cur - exp) > 1e-6 then
            table.insert(notes, string.format('%s left at %s (changed since the pass left it at %s - by you or another module)', sec, fmtNum(cur), fmtNum(exp)))
          else
            local ok, note, now = setTo(sec, want, string.format('Branch %s put-back: %s back to %s (%s had no effect)', b.key, sec, fmtNum(want), why[sec]))
            if ok and now and math.abs(now - cur) > 1e-6 then
              reverted[sec] = {cur, now}
              calc.touched[sec] = 'a branch put-back'
            else
              table.insert(notes, string.format('%s left at %s (%s)', sec, fmtNum(cur), note))
            end
          end
        end
      end
      return reverted, notes
    end
    -- Put-backs that made it worse go back to what they were before.
    local function restore(b)
      local back, notes = {}, {}
      for sec, ft in pairs(b.reverted or {}) do
        local cur = getCurVal(parsed, sec)
        if cur and math.abs(cur - ft[2]) < 1e-6 then
          local ok, note, now = setTo(sec, ft[1], string.format('Branch %s RESTORE: %s back to %s (putting it back made things worse)', b.key, sec, fmtNum(ft[1])))
          if ok and now and math.abs(now - cur) > 1e-6 then
            table.insert(back, sec)
            calc.touched[sec] = 'a branch restore'
          else
            table.insert(notes, sec .. ' (' .. note .. ')')
          end
        else
          table.insert(notes, sec .. ' (changed since)')
        end
      end
      table.sort(back)
      return back, notes
    end
    -- A new pass. reopen = frozen means "for this pass": every lever is
    -- available again, and one that was frozen gets ONE more try before it
    -- freezes again. Pass 1 of a branch keeps the ledger as it stands.
    local function startPass(b, passNo, rate, se, reopen)
      b.state, b.pass, b.baseRate, b.baseSe = 'active', passNo, rate, se
      b.baseBuild = n(settings.buildSerial, 0) + 1
      b.moves, b.reverted, b.outcome, b.verifyRate, b.verifySe = {}, {}, nil, nil, nil
      local reopened = {}
      if reopen then
        for lever, e in pairs(ledger[b.key] or {}) do
          if e.frozen then
            e.frozen, e.ineff = false, LEVER_FREEZE_AFTER - 1
            table.insert(reopened, lever)
          else
            e.ineff = 0
          end
        end
      end
      table.sort(reopened)
      return reopened
    end
    local function afterPass(b, outcome, rate, se)
      if outcome == 'fixed' then
        b.state, b.outcome, b.reverted = 'done', 'fixed', {}
        return 'branch DONE - watching; if the problem comes back, a new pass starts from the top'
      elseif (outcome == 'improved' or (outcome == 'no-gain' and not self.branchStopOnNoGain)) and (b.pass or 1) < BRANCH_MAX_PASSES then
        local nextPass = (b.pass or 1) + 1
        local reopened = startPass(b, nextPass, rate, se, true)
        return string.format('pass %d starts from the top of the branch (%s), baseline %s per 100%s',
          nextPass, table.concat(LEVER_CHAINS[b.key], ' > '), rateText(rate, se),
          #reopened > 0 and ('; one more try each for ' .. table.concat(reopened, ', ')) or '')
      end
      b.state, b.reverted = 'stopped', {}
      b.outcome = (outcome == 'improved') and 'capped' or 'no-gain'
      if b.outcome == 'capped' then
        return string.format('branch STOPPED after %d passes - the rest is advice only (Settings: "Reset lever history" starts it again)', b.pass or 1)
      end
      return 'branch STOPPED - a whole pass made no difference beyond the lap-to-lap noise; advice only (Settings: "Reset lever history" starts it again)'
    end
    -- End of a pass: judge the group, put back no-effect moves.
    local function endPass(b, reason, rate, se, vNow)
      local _, dir = b.key:match('^(%a+)%-(%a+)$')
      local improved, _, noise = branchGroupEffect(b.baseRate, b.baseSe, rate, se)
      local outcome = (vNow ~= dir) and 'fixed' or (improved and 'improved' or 'no-gain')
      local verdictText
      if outcome == 'fixed' then
        verdictText = vNow and ('FIXED - overshot to ' .. vNow .. ', which its own branch now handles') or 'FIXED'
      else
        verdictText = improved and 'IMPROVED as a group' or 'NO GAIN as a group'
      end
      table.insert(changes, string.format('Branch %s pass %d ENDED (%s): %s → %s per 100 corners since Build #%d%s = %s · moves: %s',
        b.key, b.pass or 1, reason, rateText(b.baseRate, b.baseSe), rateText(rate, se), b.baseBuild or 0,
        noise and string.format(' (noise %.1f)', noise) or ' (no lap statistics - 15% rule)', verdictText, movesText(b)))
      local reverted, notes = {}, {}
      if self.branchPutBack then reverted, notes = putBack(b) end
      local nRev = 0
      for _ in pairs(reverted) do nRev = nRev + 1 end
      b.outcome = outcome
      if nRev > 0 then
        b.state, b.reverted, b.verifyRate, b.verifySe = 'verify', reverted, rate, se
        branchHold[b.key] = 'its put-backs were applied this Build; the next window checks them before this branch moves again'
        table.insert(changes, string.format('Branch %s: %d section%s put back to the starting value (moves with no effect)%s; the next window checks nothing got worse - restored if it did',
          b.key, nRev, nRev == 1 and '' or 's', #notes > 0 and (' · not put back: ' .. table.concat(notes, '; ')) or ''))
      else
        if #notes > 0 then table.insert(changes, 'Branch ' .. b.key .. ': nothing put back - ' .. table.concat(notes, '; ')) end
        table.insert(changes, 'Branch ' .. b.key .. ': ' .. afterPass(b, outcome, rate, se))
      end
    end

    -- Last window's judgements -> the moves they belong to.
    for _, j in ipairs(self.leverJudgements or {}) do
      local b = branchFor(j.key)
      if b then
        for i, m in ipairs(b.moves) do
          if m.lever == j.lever and m.result == 'pending' then
            if j.result == 'unloaded' then table.remove(b.moves, i) else m.result = j.result end
            break
          end
        end
      end
    end
    self.leverJudgements = {}
    for _, b in ipairs(branchAll) do
      if b.car == carFolder and b.track == trackFolder then
        -- Anything still pending was never judged (a Build on another car or
        -- track came between) - kept, never put back.
        for _, m in ipairs(b.moves) do if m.result == 'pending' then m.result = 'unjudged' end end
        local regime, dir = b.key:match('^(%a+)%-(%a+)$')
        local vNow = verdictOf(regime)
        local rate, se = rateOf(b.key), seOf(b.key)
        if b.state == 'verify' then
          if lastBuildLoadedVerdict == 'NO' then
            -- The put-backs never reached the car: apply them again.
            for sec, ft in pairs(b.reverted or {}) do
              local cur = getCurVal(parsed, sec)
              if cur and math.abs(cur - ft[1]) < 1e-6 then
                setTo(sec, ft[2], string.format('Branch %s put-back (again - last Build was not loaded): %s', b.key, sec))
                calc.touched[sec] = 'a branch put-back'
              end
            end
            branchHold[b.key] = 'last Build (with its put-backs) was not loaded - applied again, checked next window'
          else
            local worse, up, noise = branchGotWorse(b.verifyRate, b.verifySe, rate, se)
            worse = (worse and vNow == dir) or (b.outcome == 'fixed' and vNow == dir)
            if worse then
              local back, notes = restore(b)
              table.insert(changes, string.format('Branch %s: the put-backs made it WORSE (%s → %s per 100%s) - restored %s%s',
                b.key, rateText(b.verifyRate, b.verifySe), rateText(rate, se), noise and string.format(', noise %.1f', noise) or '',
                #back > 0 and table.concat(back, ', ') or 'nothing (changed since)',
                #notes > 0 and (' · not restored: ' .. table.concat(notes, '; ')) or ''))
              if #back > 0 then branchHold[b.key] = 'restored this Build - measured next window' end
              table.insert(changes, 'Branch ' .. b.key .. ': ' .. afterPass(b, b.outcome, b.verifyRate, b.verifySe))
            else
              table.insert(changes, string.format('Branch %s: put-backs confirmed (%s → %s per 100 - no worse beyond the noise)',
                b.key, rateText(b.verifyRate, b.verifySe), rateText(rate, se)))
              table.insert(changes, 'Branch ' .. b.key .. ': ' .. afterPass(b, (vNow ~= dir) and 'fixed' or b.outcome, rate, se))
            end
          end
        elseif b.state == 'active' and vNow ~= dir then
          if #b.moves > 0 then
            endPass(b, 'the problem is gone', rate, se, vNow)
          else
            b.state, b.outcome = 'done', 'fixed'
          end
        end
      end
    end

    -- v2.6.0: one branch, one lever per Build - shared by the balance
    -- chains (prefix 'Balance', label 'low-speed' / 'high-speed') and the
    -- bottoming chains (prefix 'Bottoming', label 'front' / 'rear').
    local function runBranch(key, verdict, label, prefix)
      local regime = key:match('^(%a+)%-')
      local travel = regime:find('^travel') ~= nil
      local head = travel and (prefix .. ' ' .. label) or string.format('%s %s (%s)', prefix, label, verdict)
      -- v2.4.0: the branch this signal belongs to.
      if branchHold[key] then
        table.insert(changes, string.format('%s: HELD this Build - branch %s: %s', head, key, branchHold[key]))
        return
      end
      local b = branchFor(key)
      if b and b.state == 'stopped' then
        table.insert(changes, string.format('%s: branch %s STOPPED (%s, pass %d, baseline %s per 100 at Build #%d, now %s) - advice only; Settings: "Reset lever history" starts it again',
          head, key, b.outcome == 'capped' and 'pass limit reached' or 'no gain as a group', b.pass or 1,
          rateText(b.baseRate, b.baseSe), b.baseBuild or 0, rateText(rateOf(key), seOf(key))))
        return
      end
      if b and b.state == 'verify' then return end
      if not b then
        b = {car = carFolder, track = trackFolder, key = key, moves = {}, reverted = {}}
        table.insert(branchAll, b)
        startPass(b, 1, rateOf(key), seOf(key), false)
        table.insert(changes, string.format('Branch %s: pass 1 starts - baseline %s per 100 corners (Build #%d)', key, rateText(b.baseRate, b.baseSe), b.baseBuild))
      elseif b.state == 'done' then
        startPass(b, 1, rateOf(key), seOf(key), false)
        table.insert(changes, string.format('Branch %s: the problem is BACK - a new pass starts from the top, baseline %s per 100 corners', key, rateText(b.baseRate, b.baseSe)))
      end
      local chain = LEVER_CHAINS[key]
      local rateWord = travel and 'max-travel hits' or ((verdict == 'loose' and 'oversteer' or 'push') .. ' rate')
      local function tryChain()
        local tried = {}
        for _, lever in ipairs(chain) do
          local entry = ledger[key] and ledger[key][lever]
          if entry and entry.frozen then
            table.insert(tried, lever .. ' (frozen: ' .. entry.ineff .. ' moves without effect)')
          else
            local fn = levers[lever]
            local acted, why = false, 'module off'
            -- v2.3.0: MEASURED-RESPONSE JUMP. If an earlier window measured
            -- this lever's per-click effect on this signal clearly above the
            -- lap-to-lap noise (entry.sens, rate change per click, < 0 =
            -- improves), move the clicks that effect says are needed to reach
            -- the verdict's boundary, capped at LEVER_MAX_JUMP. No measured
            -- effect -> the usual 1-2 click step. Toe and rake always step
            -- (finest lever; peaky), so they never get a jump; nor do the
            -- bottoming levers (v2.6.0: one cautious step at a time).
            local rateNow = rateOf(key)
            local jump, jumpNote = nil, ''
            if not travel and entry and entry.sens and entry.sens < 0 and (lever == 'arb' or lever == 'rearDampers' or lever == 'wings') then
              local otherRate = (verdict == 'loose') and pushRate(regime) or snapRate(regime)
              local mode = self:balanceModeNow()
              local target = otherRate * ((verdict == 'loose') and mode.looseRatio or mode.tightRatio)
              if verdict == 'loose' and regime ~= 'high' then target = math.max(target, mode.slight) end
              local needed = rateNow - target
              if needed > 0 then
                jump = clamp(math.ceil(needed / -entry.sens), 1, LEVER_MAX_JUMP)
                jumpNote = string.format('; measured %.1f per click -> %d click%s to reach ~%.0f per 100', -entry.sens, jump, jump == 1 and '' or 's', target)
              end
            end
            calc.lastClicks = 0
            local before = snapshotManaged()   -- v2.4.0: what this lever changes
            if fn then acted, why = fn(regime, verdict, jump) end
            if acted then
              local rateBefore = rateNow
              local seBefore = seOf(key)
              table.insert(self.leverPendingThisBuild, {key = key, lever = lever, rateBefore = rateBefore,
                clicks = math.max(calc.lastClicks, 1), se = seBefore})
              local secs = {}
              for sec, v0 in pairs(before) do
                local v1 = getCurVal(parsed, sec)
                if v1 and math.abs(v1 - v0) > 1e-9 then secs[sec] = {v0, v1} end
              end
              table.insert(b.moves, {lever = lever, result = 'pending', secs = secs})
              table.insert(changes, string.format('%s: lever %s moved %d click%s (%s in the chain%s%s; branch pass %d); %s %.1f per 100 corners banked to judge it next window',
                head, lever, math.max(calc.lastClicks, 1), math.max(calc.lastClicks, 1) == 1 and '' or 's',
                #tried + 1 == 1 and 'first' or ('#' .. (#tried + 1)),
                #tried > 0 and ('; skipped ' .. table.concat(tried, ', ')) or '', jumpNote, b.pass or 1,
                rateWord, rateBefore))
              return true, tried
            else
              table.insert(tried, lever .. ' (' .. tostring(why) .. ')')
            end
          end
        end
        return false, tried
      end -- tryChain

      local acted, tried = tryChain()
      if acted then return end
      if b.state == 'active' and #b.moves > 0 then
        -- v2.4.0: the branch is worked through - judge it as a group, put
        -- back what did nothing, and (if it improved and nothing was put
        -- back) cycle straight back to the top.
        table.insert(changes, string.format('%s: no lever left to move in pass %d - %s', head, b.pass or 1, table.concat(tried, '; ')))
        endPass(b, 'no lever left in the branch', rateOf(key), seOf(key), verdict)
        if b.state == 'active' and #b.moves == 0 then
          local acted2, tried2 = tryChain()
          if not acted2 then
            table.insert(changes, string.format('%s: pass %d has no lever to move yet either - %s', head, b.pass or 1, table.concat(tried2, '; ')))
          end
        end
        return
      end
      table.insert(changes, string.format('%s: NO lever left to move - %s', head, table.concat(tried, '; ')))
    end

    local function run(regime, verdict, note, push, snap)
      local label = regime == 'low' and 'low-speed' or 'high-speed'
      if not verdict then
        local why = balanceLeftAloneNote(note, push, snap, label)
        if why then table.insert(changes, string.format('Balance %s: %s', label, why)) end
        return
      end
      if conflict and regime == 'low' then
        table.insert(changes, string.format('Balance %s (%s): HELD this Build - high-speed says %s; a mechanical change would fight the aero change, so the aero lever goes first and both are measured next window',
          label, verdict, highV))
        return
      end
      runBranch(regime .. '-' .. verdict, verdict, label, 'Balance')
    end

    -- v2.6.0: BOTTOMING CHAINS, one per end, run before the balance
    -- chains - the platform first. Only on a lap-consistent travel signal
    -- (travelSignal); held when the floor-clearance step raised ride
    -- height this Build (one change at a time).
    local function runTravel(e)
      local label = (e == 'F') and 'front' or 'rear'
      local verdict, hits, _, agree, considered = travelSignal(self, e, th)
      if not verdict then
        if (hits or 0) > th then
          table.insert(changes, string.format('Bottoming %s: %s', label, lapSupportNote('max-travel hits', agree or 0, considered or 0)))
        end
        return
      end
      if calc.floorRaised then
        table.insert(changes, string.format('Bottoming %s: HELD this Build - the floor-clearance step raised ride height; one change at a time, measured next window', label))
        return
      end
      runBranch('travel' .. e .. '-' .. verdict, verdict, label, 'Bottoming')
    end
    -- v2.6.1: REBOUND FOLLOWS THE SPRINGS (anti-bounce). A damper's ratio
    -- is c / 2 sqrt(k m): stiffen the spring and the same rebound setting
    -- damps that corner LESS. v2.6.0's bottoming chain never touches
    -- rebound, so three or four Builds of stiffer springs walked the
    -- rebound ratio down until the car kept oscillating after every bump -
    -- and the next Build couldn't see it, because the floor pre-pass above
    -- runs BEFORE the chains move the springs, and nothing measures bounce.
    -- Each corner's slow rebound (value and ratio) is snapshotted here,
    -- before any chain runs; after them, a corner whose ratio FELL while
    -- its rebound itself was left alone (so a spring move did it) gets its
    -- rebound raised in the same Build, back to where the ratio was and
    -- never under the floor. A lever that moved rebound on purpose is left
    -- alone - it already went through the floor check in writeTuned.
    -- Vanilla DAMP_REBOUND_* only: a CSP LUT damper has no ratio (zetaOf).
    local reboundSnap = {}
    for _, corner in ipairs({'LF', 'RF', 'LR', 'RR'}) do
      local sec = 'DAMP_REBOUND_' .. corner
      local cur = getCurVal(parsed, sec)
      reboundSnap[corner] = {cur = cur, z = cur and zetaOf(sec, cur) or nil}
    end
    runTravel('F')
    runTravel('R')
    run('high', highV, highNote, highPush, highSnap)
    run('low', lowV, lowNote, lowPush, lowSnap)
    for _, corner in ipairs({'LF', 'RF', 'LR', 'RR'}) do
      local front = (corner == 'LF' or corner == 'RF')
      local enabled
      if front then enabled = settings.writeDampersFront else enabled = settings.writeDampersRear end
      local snap = reboundSnap[corner]
      local sec = 'DAMP_REBOUND_' .. corner
      local cur = getCurVal(parsed, sec)
      local rebItem = calcDamperMap.REBOUND[sec]
      local z = cur and zetaOf(sec, cur)
      if enabled and snap.z and z and cur == snap.cur and rebItem and rebItem.raw and z < snap.z - 0.005 then
        local zTarget = math.max(snap.z, ZETA_FLOOR_REBOUND * 1.05)
        local stored = storedOf(rebItem, physicalOf(rebItem, cur) * (zTarget / z))
        if stored then
          local clicks = math.max(1, math.ceil((stored - cur) / (rebItem.step or 1) - 1e-6))
          -- The floor pre-pass may have lifted this rebound earlier in this
          -- Build (touched = true) - against the springs as they were then.
          -- Re-checking it against the new springs is the same job.
          if calc.touched[sec] == true then calc.touched[sec] = nil end
          local _, ch = writeAbs(rebItem, sec, 1, clicks,
            string.format('%s rebound %s (STIFFER - rebound follows the springs: this Build\'s spring change took its damping ratio %.2f -> %.2f, put back to %.2f so the corner does not bounce)',
              front and 'Front' or 'Rear', corner, snap.z, z, zTarget),
            NUDGE_FRACTION.damper)
          if ch then calc.touched[sec] = 'the rebound-follows-springs step' end
        end
      end
    end

    -- v2.4.0: the branches line for the log, and the store to commit if this
    -- Build is written (records used here go last, so the trim drops the
    -- oldest).
    do
      local lines, ordered = {}, {}
      for _, b in ipairs(branchAll) do
        if b.car == carFolder and b.track == trackFolder then
          table.insert(lines, string.format('%s %s pass %d%s: baseline %s at Build #%d, now %s · moves: %s%s',
            b.key, string.upper(b.state or '?'), b.pass or 1, b.outcome and (' (' .. b.outcome .. ')') or '',
            rateText(b.baseRate, b.baseSe), b.baseBuild or 0, rateText(rateOf(b.key), seOf(b.key)), movesText(b),
            next(b.reverted or {}) and (' · put back (from/to): ' .. serialiseSecList(b.reverted)) or ''))
        else
          table.insert(ordered, b)
        end
      end
      for _, b in ipairs(branchAll) do
        if b.car == carFolder and b.track == trackFolder then table.insert(ordered, b) end
      end
      table.sort(lines)
      self.branchLogLine = string.format('branches (v2.4.0, %s at %s): %s', carFolder, trackFolder,
        #lines > 0 and table.concat(lines, ' || ') or 'none yet for this car at this track')
      self.branchStoreNext = serialiseBranchStore(ordered)
    end
  end
  end

  -- v2.5.0: one line for what this car can't adjust, one for calculated
  -- targets its range stopped short - both from what the car has NOW, every
  -- Build, so a car in progress that gains dampers or bars simply stops
  -- listing them.
  local absentLine, rangeLine
  do
    local rules = {
      {'^DAMP_FAST_BUMP_', 'fast bump'}, {'^DAMP_FAST_REBOUND_', 'fast rebound'},
      {'^DAMP_BUMP_', 'bump'}, {'^DAMPER_BUMP_', 'bump'}, {'^DAMP_REBOUND_', 'rebound'}, {'^DAMPER_REBOUND_', 'rebound'},
      {'^TOE_OUT_', 'toe'}, {'^CAMBER_', 'camber'}, {'^SPRING_RATE_', 'spring'},
      {'^ROD_LENGTH_', 'ride height'}, {'^RIDE_HEIGHT_', 'ride height'}, {'^PACKER_RANGE_', 'packer range'},
      {'^BUMP_STOP_RATE_', 'bump stop'}, {'^ARB', 'anti-roll bar'}, {'^WING_', 'wing'},
    }
    local cornerRank = {LF = 1, RF = 2, LR = 3, RR = 4}
    local secs, fam, famOrder = {}, {}, {}
    for sec in pairs(absentSections) do table.insert(secs, sec) end
    table.sort(secs)
    for _, sec in ipairs(secs) do
      local label = sec
      for _, r in ipairs(rules) do if sec:find(r[1]) then label = r[2]; break end end
      if not fam[label] then fam[label] = {}; table.insert(famOrder, label) end
      local corner = sec:match('_(%u%u)$')
      if corner and cornerRank[corner] then table.insert(fam[label], corner) end
    end
    local parts = {}
    for _, label in ipairs(famOrder) do
      local cs = fam[label]
      table.sort(cs, function(a, b) return cornerRank[a] < cornerRank[b] end)
      table.insert(parts, #cs > 0 and (label .. ' ' .. table.concat(cs, '/')) or label)
    end
    if #parts > 0 then
      absentLine = 'Not adjustable on this car, so not written: ' .. table.concat(parts, ', ')
        .. ' (its setup has no such items - if the car gains them they are used automatically)'
    end
    if #rangeLimits > 0 then
      rangeLine = 'Range limits reached - the car\'s own setup range, not the calculation, stopped these: ' .. table.concat(rangeLimits, '; ')
    end
  end

  -- Status note. As of 4.3.0 an unreadable schema is no longer fatal for
  -- anything: with a template setup file (last.ini, found automatically)
  -- every category is still writable, because a real current value is all
  -- that's needed to nudge from. Only the case where BOTH are missing
  -- genuinely limits what can be done.
  local limitedNote = ''
  if not usedBase and schemaLimited then
    limitedNote = ' [no existing setup file found for this car AND its setup.ini isn\'t readable - '
      .. 'run a session so AC writes last.ini (or save any setup for this car), then Build again]'
  elseif schemaLimited then
    limitedNote = ' [this car\'s setup.ini isn\'t readable, so values were nudged from your current setup instead]'
  end

  local logLines = {
    string.format('car=%s track=%s schemaCategories=%d schemaLimited=%s schemaSource=%s (v%s, Build #%d overall, #%d since app load, %d session restart%s seen)',
      carFolder, trackFolder, schemaCategoryCount, tostring(schemaLimited), tostring(self.schemaSource), VERSION,
      n(settings.buildSerial, 0) + 1, self.buildsThisSession + 1, self.sessionRestarts or 0, (self.sessionRestarts or 0) == 1 and '' or 's'),
    string.format('template=%s (%s)', tostring(templateLabel), tostring(usedBase or 'no file')),
    lastBuildLoadedLine,
    -- v1.8.0: proves or kills the live-setup read in one session. If this
    -- says available, the base values every module nudged from came from the
    -- car itself rather than a file written at last session exit - which is
    -- the whole point. A REJECTED/unavailable line means the old template
    -- path silently took over and nothing else here changed behaviour.
    (function()
      if not liveSetup then
        return string.format('liveSetup: UNAVAILABLE (%s) - fell back to the template file, values may be stale',
          tostring(liveNote))
      end
      local sample = {}
      -- v1.9.6: TOE_OUT_LF added to the sample. It's SHOW_CLICKS=1 on the
      -- Ferrari (-100..70 step 10), the one SHOW_CLICKS=1 section whose
      -- stored-unit convention readSetupItem's rule predicts (-10..7) but no
      -- log has yet shown; the spinner's range here settles it.
      -- v2.1.1: TYRES and FINAL_RATIO added - the two the driver found
      -- reverting. Both are unmanaged, so these are the CARRIED values.
      for _, sec in ipairs({'PRESSURE_LF', 'CAMBER_LF', 'TOE_OUT_LF', 'DAMP_REBOUND_LR', 'DAMPER_REBOUND_LR', 'ARB_FRONT', 'ARB_F', 'TYRES', 'FINAL_RATIO'}) do
        local it = liveSetup[sec]
        if it then
          table.insert(sample, string.format('%s=%s[%s..%s step %s%s]', sec, tostring(it.value),
            tostring(it.min), tostring(it.max), tostring(it.step),
            it.displayMultiplier and (' x' .. tostring(it.displayMultiplier)) or ''))
        end
      end
      -- v2.1.1: `carried` = unmanaged sections (gearing, compound, fuel, TC,
      -- limiter, brake power) copied from LIVE into the output so loading it
      -- leaves the driver's own choices alone. No writer may touch them.
      return string.format('liveSetup: %s · %d managed synced, %d unmanaged CARRIED from live (gearing/compound/fuel/TC - never written, now never reverted%s), %d readOnly, %d unmanaged not in template (left out)%s · %s',
        tostring(liveNote), liveSynced, liveCarried,
        #carriedSamples > 0 and ('; template was stale on ' .. table.concat(carriedSamples, ', ')) or '',
        liveSkippedReadOnly, liveUnmanagedAbsent, compoundCheck .. liveFuelNote,
        #sample > 0 and table.concat(sample, ' ') or 'no sample sections present')
    end)(),
    -- Module write toggles, v1.7.4 - so a Build's log is self-explaining
    -- when a category shows SKIPPED/unchanged purely because its checkbox
    -- was off, not because of any detection or write problem.
    string.format('moduleGates: pressures=%s camber=%s suspension=%s springs=%s arb=%s dampersF=%s dampersR=%s fastDampersF=%s fastDampersR=%s toeF=%s toeR=%s brakeBias=%s diff=%s aero=%s',
      tostring(settings.writePressures), tostring(settings.writeCamber), tostring(settings.writeSuspension),
      tostring(settings.writeSprings), tostring(settings.writeARB),
      tostring(settings.writeDampersFront), tostring(settings.writeDampersRear),
      tostring(settings.writeFastDampersFront), tostring(settings.writeFastDampersRear),
      tostring(settings.writeToeFront), tostring(settings.writeToeRear),
      tostring(settings.writeBrakeBias), tostring(settings.writeDifferential), tostring(settings.writeAero)),
    -- Raw event counters AT THE MOMENT BUILD WAS PRESSED, added v1.4.0 so
    -- "did this category's counter actually cross threshold and still not
    -- write" is a fact you can read off the log, not something that has
    -- to be inferred from the advice panel (which is live and can show a
    -- later, higher count than whatever Build actually saw if more
    -- driving happened between the panel screenshot and the Build press).
    string.format('th=%d counters: bottoming=%d springsF=%d springsR=%d midPush=%d midSnap=%d highPush=%d highSnap=%d turninPush=%d rearToeEvents=%d lockF=%d lockR=%d',
      th, self.bottoming, self.springsHitsF, self.springsHitsR, self.midPush, self.midSnap,
      self.highPush, self.highSnap, self.turninPush, self.rearToeEvents, self.lockF, self.lockR),
    string.format('  damper events: bumpF=%d rebF=%d bumpR=%d rebR=%d · fast bumpF=%d rebF=%d bumpR=%d rebR=%d · diffEvents=%d diffRotationEvents=%d',
      self.dampBumpF, self.dampRebF, self.dampBumpR, self.dampRebR,
      self.fastDampBumpF, self.fastDampRebF, self.fastDampBumpR, self.fastDampRebR,
      self.diffEvents, self.diffRotationEvents),
    -- v2.0.0: evidence window, per-lap bins, lap consistency - the same
    -- three lines a DECLINED Build writes, so the two can be compared.
    table.concat(self:evidenceLogLines(th), '\n'),
    -- v2.1.0: what the previous Build's levers did to this window, and the
    -- per-car ledger the chain runner consulted this Build.
    gateOverridden and string.format('GATE OVERRIDDEN (test button) - this Build ran with fewer clean %s than the gate requires; consistency checks pass through with < 2 clean %s', EV_UNIT.many, EV_UNIT.many) or 'gate: passed normally',
    effectLine,
    self:leverLedgerLine(carFolder),
    self.branchLogLine or 'branches: n/a',
    -- v2.6.0: ride height to the floor, and what touched the track.
    'floor (v2.6.0): ' .. (calc.notes.floor or 'not evaluated (suspension module off)'),
    'track contacts (v2.6.0, logged only): ' .. ((self.trackContacts or 0) > 0
      and string.format('%d this window%s', self.trackContacts, (self.trackContactPosN or 0) > 0
        and string.format(', lowest point y %.3f m, mean |x| %.2f m (car space)', self.trackContactMinY or 0, self.trackContactSumAbsX / self.trackContactPosN) or '')
      or 'none this window'),
    (function()  -- v2.6.2
      local okL, line = pcall(self.colliderLogLine, self)
      return okL and line or ('collider floor (v2.6.2): log line failed - ' .. tostring(line))
    end)(),
    -- v2.3.0: every calculated target's inputs and outcome, one line.
    (function()
      local parts = {}
      -- brake bias
      local bt, btInfo = self:biasTarget()
      table.insert(parts, string.format('bias %s%s', bt and string.format('%.1f%% (%s)', bt, btInfo) or ('n/a - ' .. tostring(btInfo)),
        self:biasBaselineDone(carFolder) and ' [one-time write USED - advice only]' or ' [one-time write still available]'))
      -- springs: median lap peak travel use
      local function medianUse(front)
        local u = {}
        for _, b in ipairs(windowBins(self)) do
          local x = front and b.travelUseF or b.travelUseR
          if x and x > 0 then table.insert(u, x) end
        end
        table.sort(u)
        return (#u >= 1) and u[math.floor((#u + 1) / 2)] or nil
      end
      local mF, mR = medianUse(true), medianUse(false)
      -- v2.5.0: of the car's OWN range (see readTravelRef), and where it
      -- sits at rest.
      table.insert(parts, string.format('travel use (median %s) F %s R %s of the car\'s range F %.0f / R %.0f mm (%s)%s (spring target %.0f%%)',
        EV_UNIT.one, mF and string.format('%.0f%%', mF * 100) or 'n/a', mR and string.format('%.0f%%', mR * 100) or 'n/a',
        (self.lastTravelF or 0) * 1000, (self.lastTravelR or 0) * 1000, tostring(self.travelRefSrc),
        (self.staticTravelF and self.staticTravelR) and string.format(', at rest F %.0f%% R %.0f%%', self.staticTravelF / self.lastTravelF * 100, self.staticTravelR / self.lastTravelR * 100) or '',
        SPRING_TARGET_USE * 100) .. string.format(' - v2.6.0: springs are the bottoming chain\'s 4th fix, at most +%.0f%% a Build', SPRING_MAX_STEP * 100))
      -- v2.6.0: ride height to the floor (the floor line has the inputs);
      -- the aero peaks are only the stall limit now.
      local peaks = self.aeroPeaks or {}
      table.insert(parts, string.format('ride height to the floor: %s (front fast-corner avg %s, splitter ground %s, aero peak front %s / diffuser %s)',
        tostring(calc.notes.ride or 'not evaluated'),
        (self.hsRhFN or 0) > 0 and string.format('%.1f mm', self.hsRhFSum / self.hsRhFN * 1000) or 'n/a',
        (self.ghFrontN or 0) > 0 and string.format('%.1f mm', self.ghFrontSum / self.ghFrontN * 1000) or 'n/a',
        peaks.front and string.format('%.0f mm', peaks.front * 1000) or 'n/a',
        peaks.diffuser and string.format('%.0f mm', peaks.diffuser * 1000) or 'n/a'))
      -- damping ratios, as written
      local z = {}
      for _, corner in ipairs({'LF', 'LR'}) do
        for _, kind in ipairs({'BUMP', 'REBOUND'}) do
          local sec = 'DAMP_' .. kind .. '_' .. corner
          local v = getCurVal(parsed, sec)
          local zz = v and zetaOf(sec, v)
          table.insert(z, string.format('%s %s %s', corner, kind == 'BUMP' and 'b' or 'r', zz and string.format('%.2f', zz) or 'n/a'))
        end
      end
      table.insert(parts, 'damping ratio ' .. table.concat(z, ' ') .. string.format(' (floors b %.2f / r %.2f)', ZETA_FLOOR_BUMP, ZETA_FLOOR_REBOUND))
      -- camber gain
      local gF, nF = self:camberGain('F')
      local gR, nR = self:camberGain('R')
      table.insert(parts, string.format('camber gain F %s R %s', gF and string.format('%.2f', gF) or string.format('n/a (%d pts)', nF or 0),
        gR and string.format('%.2f', gR) or string.format('n/a (%d pts)', nR or 0)))
      -- final drive
      local fd = self.finalDriveCalc
      table.insert(parts, fd and string.format('final drive ideal %.3f, fitted %.3f%s', fd.want, fd.cur,
        fd.bestRatio and string.format(', nearest option %.3f (#%d of %d)', fd.bestRatio, (fd.bestIdx or 0) + 1, fd.n or 0) or '') or 'final drive n/a')
      return 'calculated targets (v2.3.0): ' .. table.concat(parts, ' · ')
    end)(),
    string.format('rake: static front %s rear %s = %s (floor +3 mm for "less rake")',
      self.rideHeightCaptured and string.format('%.0f mm', self.staticRideHeightF * 1000) or 'n/a',
      (self.staticRideHeightR or 0) > 0 and string.format('%.0f mm', self.staticRideHeightR * 1000) or 'n/a',
      (self.rideHeightCaptured and (self.staticRideHeightR or 0) > 0) and string.format('%+.0f mm rake', (self.staticRideHeightR - self.staticRideHeightF) * 1000) or 'unknown'),
    -- v1.9.8: the three balance verdicts every push-vs-snap writer used
    -- this Build, so "why didn't ARB/rake/wings/rear dampers move" is
    -- answerable from the log. 'slight' = oversteer present but under the
    -- per-100-corners bar; 'mixed' = both present, neither dominant.
    (function()
      local lowV, _, _, lowN, lowRate = regimeVerdict(self, 'low', th)
      local highV, _, _, highN = regimeVerdict(self, 'high', th)
      local rearV, rearSnapN, rearPushN, rearN = rearHandlingSignal(self, th)
      local mode = self:balanceModeNow()
      return string.format('balance verdicts (%s target: tight if push > %.2f x snap, loose if snap > %.2f x push): low=%s (push %d / snap %d, %.0f snap per 100 corners; slight <= %d) · high=%s (push %d / snap %d) · rear=%s (push %d / snap %d)',
        mode.label, mode.tightRatio, mode.looseRatio,
        lowV or lowN or 'neutral', self.midPush, self.midSnap, lowRate, mode.slight,
        highV or highN or 'neutral', self.highPush, self.highSnap,
        rearV or rearN or 'neutral', rearPushN, rearSnapN)
    end)(),
    -- v2.5.0: what was taken OUT of those snap counts, and why.
    string.format('held slides (v2.5.0): %d this window - deliberate (started with the handbrake, or the throttle held %.0f s+ through the slide), counted apart and never a verdict; handbrake use also kept out of the rear-lockup and brake-bias samples',
      self.heldSlides or 0, HELD_SLIDE_S),
    -- v2.5.0: evidence units and the physics fingerprint, so both can be
    -- verified from the log.
    string.format('evidence units (v2.5.0): %s · physics fingerprint: %s',
      (self.unitsPerLap or 1) > 1 and string.format('%d sections a lap on this %.1f km track (> %.1f km splits into ~%.0f km sections)', self.unitsPerLap, (self.trackLengthM or 0) / 1000, LONG_TRACK_M / 1000, SECTION_M / 1000)
        or string.format('whole laps (%.1f km track)', (self.trackLengthM or 0) / 1000),
      self.physicsChangeNote and 'CHANGED - learned values reset (see the first change line)'
        or (self.physicsFirstSeen and 'first time this car is seen - recorded' or (self.physicsPrint and 'unchanged since this car was last seen' or 'not read'))),
    -- REAR REBOUND EXPERIMENT LINE, v1.6.0 - question ANSWERED in v1.9.1,
    -- logic FIXED in v1.9.3. It was opened because this app stiffened rear
    -- rebound whenever rebound events outnumbered bump events, while real
    -- motorsport sources and this project's own v1.0.1 finding said excess
    -- rear rebound makes a car loose. AC's own setup tooltip then said it
    -- outright ("higher: less stable under braking and initial turn in"),
    -- and the rear axle's slow-damper direction is now driven by the
    -- handling signal instead - see rearHandlingSignal. The line stays,
    -- with a new purpose: it should now show snap rates FALLING across
    -- sessions as rearRebound falls on loose cars. If they don't, that's
    -- the fix not working, and this is where it shows first. Values are
    -- the PRE-write snapshot (v1.9.2) - what was actually driven, not what
    -- Build just wrote. Read it as a trend across sessions; a single row
    -- proves nothing either way.
    (function()
      local cs = math.max(self.corneringSamples, 1)
      local per100 = function(v) return v / cs * 100 end
      -- v1.9.2: reads the PRE-WRITE snapshot captured right after the live
      -- sync, not `parsed` as it stands here (which by this point in
      -- logLines has already been through every writer below - see the
      -- snapshot's own comment for the real session this was caught on).
      local rebLR = rearReboundAsDriven.rebLR
      local rebRR = rearReboundAsDriven.rebRR
      local bumpLR = rearReboundAsDriven.bumpLR
      return string.format(
        'REAR REBOUND EXPERIMENT: rearRebound(as driven)=%s/%s rearBump=%s · per-100-corners: midSnap=%.1f highSnap=%.1f spinR=%.1f liftOffSnap=%.1f · rearDy=%s · corners=%d',
        rebLR and string.format('%.0f', rebLR) or 'n/a',
        rebRR and string.format('%.0f', rebRR) or 'n/a',
        bumpLR and string.format('%.0f', bumpLR) or 'n/a',
        per100(self.midSnap), per100(self.highSnap), per100(self.spinR), per100(self.liftOffSnap),
        self.dyPeakN > 0 and string.format('%.3f', self.dyPeakRSum / self.dyPeakN) or 'n/a',
        self.corneringSamples)
    end)(),
    string.format('staticCamberCaptured=%s corneringSamples=%d peakCamberF=%s peakCamberR=%s peakCamberSrc=%s dy0=%s/%s%s',
      tostring(self.staticCamberCaptured), self.corneringSamples,
      self.peakCamberF and string.format('%.2f°', self.peakCamberF) or 'n/a',
      self.peakCamberR and string.format('%.2f°', self.peakCamberR) or 'n/a',
      tostring(self.peakCamberSrc or 'none'),
      self.dy0F and string.format('%.3f', self.dy0F) or 'n/a',
      self.dy0R and string.format('%.3f', self.dy0R) or 'n/a',
      self.dyRefUsed and ' (DY_REF - DY0 is 0 on this tyre)' or ''),
    string.format('damperCrossover=%s (logged only) · event thresholds %.2f / %.2f m/s, FIXED for every car since v2.2.0',
      self.damperCrossover and string.format('%.3f m/s (live suspensions.ini)', self.damperCrossover) or 'n/a',
      self.velModerate or DAMPER_EVENT_MODERATE, self.velSharp or DAMPER_EVENT_SHARP),
    -- v2.2.0: which suspension model each axle's setup uses, and whether
    -- the curves behind CSP's LUT dampers / LUT anti-roll bars could be
    -- read to verify a move's direction before writing it.
    self:lutSuspensionLine(),
    string.format('driveType=%s aeroLutChecked=%s aeroLutRisk=%s (settles whether ac.DataLUT11 works in app context)',
      tostring(self.driveType), tostring(self.aeroLutChecked), tostring(self.aeroLutRisk)),
    string.format('sectorsAvailable=%s (settles whether ac.getTrackSectorName works on this track)', tostring(self.sectorsAvailable)),
    string.format('topGear=%s topGearRatio=%s secondTopGearRatio=%s (ac.getCarPhysics, v1.5.0 - live per-gear measurement retired, see engine:update\'s comment for why)',
      tostring(self.topGearNum),
      self.topGearRatio and string.format('%.3f', self.topGearRatio) or 'n/a',
      self.secondTopGearRatio and string.format('%.3f', self.secondTopGearRatio) or 'n/a'),
    string.format('gearPhysDiag: %s · maxGearSeen=%d gearAtVmax=%d topSpeed=%.0f rpmAtVmax=%.0f limiterTime=%.2fs (v1.7.3, explains a topGear=nil read above and lets the new too-tall GEARING check be verified against real numbers)',
      tostring(self.gearPhysDiag), self.maxGearSeen, self.gearAtVmax, self.topSpeed, self.rpmAtVmax, self.limiterTime),
    string.format('aeroPeaks front=%s diffuser=%s (mm, from this car\'s own GH_CL curve) · rideHeight captured=%s static front=%s',
      self.aeroPeaks.front and string.format('%.0f', self.aeroPeaks.front * 1000) or 'n/a',
      self.aeroPeaks.diffuser and string.format('%.0f', self.aeroPeaks.diffuser * 1000) or 'n/a',
      tostring(self.rideHeightCaptured),
      self.rideHeightCaptured and string.format('%.0f', self.staticRideHeightF * 1000) or 'n/a'),
    (function()
      if not (self.aeroDynamic and #self.aeroDynamic > 0) then return 'aeroDynamic: none found' end
      local parts = {}
      for _, d in ipairs(self.aeroDynamic) do table.insert(parts, d.wing .. '/' .. d.input) end
      return 'aeroDynamic controllers found: ' .. table.concat(parts, ', ')
    end)(),
    string.format('pressureMethod=%s tyreDataSrc=%s', pressureMethod, tostring(self.targetSrc)),
    -- Explicit, human-readable reasons rather than just raw state - the
    -- point of this log is to answer "why didn't X happen" on its own,
    -- without needing the raw fields above interpreted for you.
    'ARB/springs/dampers/toe/ride height/brake bias/wings/bump stop: '
      .. (usedBase and ('nudged from your current setup (' .. tostring(templateLabel) .. ')')
        or (schemaLimited
          and 'NO template setup file found AND no readable schema - nothing to work from. Run a session so AC writes last.ini, or save any setup for this car.'
          or 'no template found, using car schema midpoints instead')),
    -- v2.3.0: this line said "SKIPPED - sit stationary in the pits" on
    -- Builds that then wrote camber (real Corvette log): the writer has
    -- not needed a static reading since v1.5.0. It now says what happened.
    'camber write: '
      .. (not settings.writeCamber and 'SKIPPED (module unticked)'
        or (self.corneringSamples <= 8 and 'SKIPPED - need more clean corners for a trustworthy loaded-tyre reading'
          or (self.peakCamberF and 'calculated from this tyre\'s own camber curve + measured loaded camber (noise dead-band and per-car gain, v2.3.0)'
            or 'thermal route (tread temperature spread) - this tyre states no camber curve'))),
    'pressure write: always attempted (uses ' .. pressureMethod .. ')',
  }

  if #changes == 0 then
    -- v2.4.0: this Build consumed last window's lever judgements at its
    -- start - keep what the branches learned from them even though
    -- nothing is written (a put-back or a lever move would be a change,
    -- so only judgements and state changes can land here).
    if self.branchStoreNext then settings.branchState = self.branchStoreNext end
    self.branchStoreNext = nil
    self:leverLedgerSave(carFolder)
    self.setupChanges = {}
    if not self.staticCamberCaptured and schemaLimited then
      self.setupMsg = 'Sit stationary in the pits once + drive more laps to trigger telemetry flags' .. limitedNote
    elseif not self.staticCamberCaptured then
      self.setupMsg = 'Sit stationary in the pits once, then press Build again' .. limitedNote
    else
      self.setupMsg = 'No changes triggered yet - drive some more clean laps to build telemetry flags' .. limitedNote
    end
    if absentLine then table.insert(logLines, absentLine) end  -- v2.5.0
    table.insert(logLines, 'result: no changes - ' .. self.setupMsg)
    self:writeDebugLog(logLines)
    return false
  end
  -- v2.5.0: summaries go with the real changes (they are never a reason to
  -- write a file on their own).
  if rangeLine then table.insert(changes, rangeLine) end
  if absentLine then table.insert(changes, absentLine) end

  local outName = 'SetupCoach_Optimized.ini'
  local outPath = dir .. '/' .. outName
  local f, err = io.open(outPath, 'w')

  -- If the track-specific setups folder doesn't exist yet, fall back to the
  -- car's generic setups folder before giving up - it's somewhat more likely
  -- to already exist if you've saved any setup at all for this car before.
  local usedGenericFallback = false
  if not f and err and tostring(err):find('No such file or directory') and trackFolder ~= 'generic' then
    local genericDir = setupsDir(carFolder, 'generic')
    if genericDir then
      outPath = genericDir .. '/' .. outName
      f, err = io.open(outPath, 'w')
      usedGenericFallback = f ~= nil
    end
  end

  if not f then
    if err and tostring(err):find('No such file or directory') then
      self.setupMsg = string.format(
        "ERROR: folder doesn't exist yet - %s. Plain file writes can't create new folders, and CSP doesn't appear to expose a way around that. Save any setup once from the in-game Setup screen for this car (any track) to create the folder, then press Build again.",
        dir)
    else
      self.setupMsg = 'ERROR writing setup file: ' .. tostring(err) .. ' (tried: ' .. outPath .. ')'
    end
    table.insert(logLines, 'result: ERROR - ' .. self.setupMsg)
    self:writeDebugLog(logLines)
    return false
  end
  f:write(table.concat(parsed.lines, '\n'))
  f:close()

  self.setupChanges = changes
  self.setupOutPath = outPath
  self.setupMsg = string.format('Wrote %s (%d change%s)%s - load it from the in-game Setup screen%s',
    outName, #changes, #changes == 1 and '' or 's',
    usedGenericFallback and ' [saved under generic, not this track]' or '', limitedNote)
  pcall(ac.setMessage, 'Setup Coach', 'Optimal setup written: ' .. outName)

  table.insert(logLines, 'result: wrote ' .. outPath)
  for _, c in ipairs(changes) do table.insert(logLines, '  ' .. c) end

  -- v2.0.0: remember what was written (for next Build's lastBuildLoaded
  -- check), then CONSUME the evidence this Build acted on. The next Build
  -- sees only laps driven after this one.
  self.lastBuildWritten = {}
  for section in pairs(MANAGED_SECTIONS) do
    local v = getCurVal(parsed, section)
    if v then self.lastBuildWritten[section] = v end
  end
  self.buildsThisSession = self.buildsThisSession + 1
  local okDate, dateStr = pcall(os.date, '%H:%M:%S')
  self.lastBuildAt = okDate and dateStr or '?'
  -- v2.0.1: persist the record and a running serial (survives app reloads).
  settings.buildSerial = n(settings.buildSerial, 0) + 1
  -- v2.5.0: one record per car + track, "HH:MM:SS;SEC=v,SEC=v,...".
  do
    local pairsOut = {}
    for section, v in pairs(self.lastBuildWritten) do table.insert(pairsOut, section .. '=' .. tostring(v)) end
    table.sort(pairsOut)
    local list = parseKeyedStore(settings.lastBuildRecord)
    keyedPut(list, carFolder, trackFolder, tostring(self.lastBuildAt) .. ';' .. table.concat(pairsOut, ','))
    settings.lastBuildRecord = serialiseKeyedStore(list)
    self.lastBuildKey = carFolder .. '>' .. trackFolder
  end
  -- v2.1.0: the levers this Build moved, for the next window to judge.
  do
    local items = {}
    for _, p in ipairs(self.leverPendingThisBuild or {}) do
      -- v2.3.0: + clicks moved and the window's standard error, so the
      -- next window can measure a per-click effect against the noise.
      table.insert(items, string.format('%s:%s:%.2f:%d:%.2f', p.key, p.lever, p.rateBefore, p.clicks or 1, p.se or -1))
    end
    -- v2.5.0: one record per car + track, "serial#items" - the next Build
    -- at THIS track judges them; other tracks keep their own.
    local list = parseKeyedStore(settings.leverPending)
    keyedPut(list, carFolder, trackFolder, (#items > 0) and (tostring(n(settings.buildSerial, 0)) .. '#' .. table.concat(items, ';')) or nil)
    settings.leverPending = serialiseKeyedStore(list)
    self:leverLedgerSave(carFolder)
    -- v2.4.0: branch passes as this Build left them.
    if self.branchStoreNext then settings.branchState = self.branchStoreNext end
    self.branchStoreNext = nil
  end
  local consumedLabel = string.format('Build #%d', n(settings.buildSerial, 0))
  self.physicsChangeNote = nil  -- v2.5.0: reported by this Build
  self.physicsFirstSeen = false  -- v2.5.2: likewise "first time this car is seen"
  self:consumeWindow(consumedLabel)
  local needUnits = clamp(math.floor(n(settings.buildMinLaps, 2)), 1, 5)
  table.insert(logLines, string.format('evidence consumed: counters, corner samples and pressure peaks reset; next Build needs %d clean %s%s and %d corners driven on THIS setup',
    needUnits, unitWord(needUnits), longTrackNote(self), BUILD_MIN_CORNERS))
  self.setupMsg = self.setupMsg .. string.format(' [telemetry consumed - drive %d+ clean %s on it before the next Build]', needUnits, unitWord(needUnits))
  self:writeDebugLog(logLines)
  return true
end

--------------------------------------------------------------------------------
-- UI
--------------------------------------------------------------------------------

---@param car ac.StateCar?
---@param sim ac.StateSim
local function drawHeader(car, sim)
  local carName = engine.carId
  pcall(function() if car and car.name then carName = car:name() or carName end end)

  ui.pushFont(ui.Font.Title)
  ui.text('SETUP COACH')
  ui.popFont()
  ui.sameLine(0, 12)
  ui.pushFont(ui.Font.Small)
  ui.text('v' .. VERSION .. '  ·  ' .. tostring(engine.samples) .. ' samples')
  ui.popFont()

  if car then
    ui.text(string.format('%s  ·  %s  ·  lap %d  ·  last %s  ·  best %s',
      carName ~= '' and carName or 'car',
      engine.compound ~= '' and engine.compound or '—',
      engine.completedLaps, fmtTime(getLastLap(car)), fmtTime(getBestLap(car))))

    local air = getAirTemp(sim)
    local road = sim and n(sim.roadTemperature, 0) or 0
    ui.text(string.format('%.0f km/h  ·  %.0f rpm  ·  fuel %.1f L  ·  road %.0f°  air %.0f°',
      n(car.speedKmh), n(car.rpm), n(car.fuel), road, air))
  else
    ui.text('Waiting for car...')
  end
end

-- CSP's ui.checkbox does NOT return the new value - it returns whether the
-- box was CLICKED this frame. Straight from CSP's own shipped SDK
-- definition (extension/internal/lua-sdk/ac_apps/lib.lua):
--
--     ---@return boolean @Returns `true` if checkbox was clicked.
--     if ui.checkbox('My checkbox', myFlag) then myFlag = not myFlag end
--
-- So the natural-looking `flag = ui.checkbox(label, flag)` is WRONG in a
-- specific and nasty way: on the frame you click it the call returns true
-- and the flag goes true, and on EVERY frame after that it returns false
-- and the flag goes straight back to false. That is exactly the reported
-- "tick the box, the menu flashes briefly and vanishes" bug (v1.7.6), and
-- it was in all 17 checkbox call sites in this file - including four that
-- predate the module toggles entirely (Show kPa, Hide OK items, Use temp
-- analysis, Sample in replay). Those were never noticed because they live
-- in windowSettings, which as of v1.7.5 appears never to actually render
-- for this app - so their lines never ran and their stored defaults
-- survived untouched. The module toggles were the first checkboxes this
-- app has ever drawn in a window that genuinely displays, which is why
-- the long-standing bug only surfaced now.
--
-- Wrapped once here so no call site has to remember the idiom. Returns the
-- value the flag should now have, so `flag = checkbox(label, flag)` reads
-- naturally AND is correct.
local function checkbox(label, value)
  if ui.checkbox(label, value) then return not value end
  return value
end

-- v1.7.5: shared between windowMain (behind a collapse toggle - see the
-- OPTIMAL SETUP section below) and windowSettings, so the checkbox list
-- lives in exactly one place - defined here specifically BECAUSE relying
-- on windowSettings alone turned out to be a real discoverability failure
-- (reported directly: "dont see any boxes... check debug" - not a code
-- bug, CSP's own settings-gear access for this app couldn't be confirmed
-- working at all, so the toggles are now reachable from the main panel
-- the driver is already looking at, with no dependency on finding it).
local function drawModuleToggleCheckboxes()
  ui.text('Build writes these modules')
  ui.pushFont(ui.Font.Small)
  ui.textWrapped('Untick a module to freeze it at whatever value is already in your setup - Build leaves it completely alone, even while the advice panel keeps flagging it. Use this once a module is dialled in and you want to keep iterating on the rest without it moving.')
  ui.popFont()
  settings.writePressures = checkbox('Pressures', settings.writePressures)
  settings.writeCamber = checkbox('Camber', settings.writeCamber)
  settings.writeSuspension = checkbox('Suspension (ride height / rake)', settings.writeSuspension)
  settings.writeSprings = checkbox('Springs', settings.writeSprings)
  settings.writeARB = checkbox('ARB', settings.writeARB)
  settings.writeDampersFront = checkbox('Front dampers (slow)', settings.writeDampersFront)
  settings.writeDampersRear = checkbox('Rear dampers (slow)', settings.writeDampersRear)
  settings.writeFastDampersFront = checkbox('Fast front dampers', settings.writeFastDampersFront)
  settings.writeFastDampersRear = checkbox('Fast rear dampers', settings.writeFastDampersRear)
  settings.writeToeFront = checkbox('Front toe', settings.writeToeFront)
  settings.writeToeRear = checkbox('Rear toe', settings.writeToeRear)
  settings.writeBrakeBias = checkbox('Brake bias', settings.writeBrakeBias)
  settings.writeDifferential = checkbox('Differential', settings.writeDifferential)
  settings.writeAero = checkbox('Aero (wings)', settings.writeAero)
  -- Starting a new car/track means wanting everything back on before
  -- progressively freezing modules again as each one gets dialled in - that
  -- recurring reset is what this is for. Deliberately a button rather than
  -- anything automatic on upgrade: un-ticks here are real choices and are
  -- never overridden without being asked for.
  ui.offsetCursorY(2)
  if ui.button('All on', vec2(70, 22)) then
    for _, key in ipairs(MODULE_GATE_KEYS) do settings[key] = true end
  end
end

-- v3.1.1 panel: live tyres, this window's balance numbers, then only the
-- checks that want a change (act/warn), top first. Fine and still-measuring
-- checks collapse to one line each; "Show every check" brings the full
-- reasoning back. Info items (evidence, tyres, fuel, lap times, weather)
-- are shown in the summary instead of the list.
local PANEL_COLORS = {
  act = rgbm(1.0, 0.55, 0.2, 1), warn = rgbm(1.0, 0.85, 0.3, 1),
  ok = rgbm(0.45, 0.85, 0.45, 1), wait = rgbm(0.6, 0.6, 0.6, 1),
  info = {['BUILD EVIDENCE'] = true, TYRES = true, FUEL = true, PERFORMANCE = true, WEATHER = true},
}

local function drawAdviceList(compact)
  local fine, measuring, shown = {}, {}, 0
  for i = 1, #engine.lastAdvice do
    local a = engine.lastAdvice[i]
    if not PANEL_COLORS.info[a.id] then
      if a.status == 'act' or a.status == 'warn' or engine.showAllChecks then
        shown = shown + 1
        ui.textColored(a.id, PANEL_COLORS[a.status] or PANEL_COLORS.wait)
        ui.pushFont(ui.Font.Small)
        ui.textWrapped(a.text)
        ui.popFont()
        ui.offsetCursorY(3)
      elseif a.status == 'wait' then
        measuring[#measuring + 1] = string.lower(a.id)
      else
        fine[#fine + 1] = string.lower(a.id)
      end
    end
  end
  if shown == 0 then
    ui.textColored('Nothing to change right now - everything measured is inside the target.', PANEL_COLORS.ok)
  end
  ui.pushFont(ui.Font.Small)
  if #fine > 0 then ui.textWrapped('Fine: ' .. table.concat(fine, ', ')) end
  if #measuring > 0 then ui.textWrapped('Still measuring: ' .. table.concat(measuring, ', ')) end
  ui.popFont()
  engine.showAllChecks = checkbox('Show every check, with the reasoning', engine.showAllChecks)
end

-- Live tyre table: pressure against the hot target, inside/middle/outside
-- and core temperature against the tyre's optimum - read straight from the
-- car every frame.
local function drawLiveTyres(car)
  if not (car and car.wheels) then return end
  local x0 = ui.getCursorX()
  local colX = {x0, x0 + 150, x0 + 280, x0 + 410, x0 + 540}
  local function row(label, vals, colors)
    ui.setCursorX(colX[1])
    ui.text(label)
    for i = 1, 4 do
      ui.sameLine(0, 0)
      ui.setCursorX(colX[i + 1])
      if colors and colors[i] then ui.textColored(vals[i], colors[i]) else ui.text(vals[i]) end
    end
  end
  local press = {engine.livePressFL, engine.livePressFR, engine.livePressRL, engine.livePressRR}
  local pv, pc, tv, cv, cc = {}, {}, {}, {}, {}
  for i = 1, 4 do
    local w = car.wheels[i]
    local tgt = i <= 2 and n(engine.targetF, 0) or n(engine.targetR, 0)
    pv[i] = (press[i] or 0) > 5 and psiStr(press[i]) or '-'
    if (press[i] or 0) > 5 and tgt > 0 then
      local d = math.abs(press[i] - tgt)
      pc[i] = d <= 0.5 and PANEL_COLORS.ok or (d <= 1.2 and PANEL_COLORS.warn or PANEL_COLORS.act)
    end
    tv[i] = string.format('%.0f / %.0f / %.0f', n(w and w.tyreInsideTemperature), n(w and w.tyreMiddleTemperature), n(w and w.tyreOutsideTemperature))
    local core, opt = n(w and w.tyreCoreTemperature), n(w and w.tyreOptimumTemperature)
    cv[i] = opt > 0 and string.format('%.0f° (opt %.0f°)', core, opt) or string.format('%.0f°', core)
    if opt > 0 then
      local d = math.abs(core - opt)
      cc[i] = d <= 5 and PANEL_COLORS.ok or (d <= 12 and PANEL_COLORS.warn or PANEL_COLORS.act)
    end
  end
  ui.pushFont(ui.Font.Small)
  row('', {'FL', 'FR', 'RL', 'RR'})
  row(string.format('Pressure (hot %s / %s)', n(engine.targetF, 0) > 0 and psiStr(engine.targetF) or '-', n(engine.targetR, 0) > 0 and psiStr(engine.targetR) or '-'), pv, pc)
  row('Temp in / mid / out', tv)
  row('Core', cv, cc)
  ui.popFont()
end

-- This window's numbers, the same ones Build decides from.
local function drawWindowSummary()
  local th = math.max(1, math.floor(n(settings.threshold, 2)))
  local passes, clean, _, _, _, minLaps, corners = engine:buildEvidence()
  local mode = balanceMode()
  ui.pushFont(ui.Font.Small)
  ui.text(string.format('%d clean %s · %d corners since %s · %s', clean, unitWord(clean), corners,
    tostring(engine.windowLabel or 'session start'),
    passes and 'ready to Build' or string.format('Build needs %d clean %s and %d corners', minLaps, unitWord(minLaps), BUILD_MIN_CORNERS)))
  local per = corners > 0 and 100 / corners or 0
  for _, r in ipairs({{'Low speed', 'low'}, {'High speed', 'high'}}) do
    local v, push, snap, note = regimeVerdict(engine, r[2], th)
    local word, col = 'balanced', PANEL_COLORS.ok
    if v == 'tight' then word, col = 'UNDERSTEER', PANEL_COLORS.act
    elseif v == 'loose' then word, col = 'OVERSTEER', PANEL_COLORS.act
    elseif note == 'slight' then word = 'slight oversteer - inside the target'
    elseif note then word, col = 'mixed (' .. note .. ')', PANEL_COLORS.wait end
    if corners == 0 then word, col = 'no corners yet', PANEL_COLORS.wait end
    ui.text(string.format('%s: push %.0f / oversteer %.0f per 100 corners ->', r[1], (push or 0) * per, (snap or 0) * per))
    ui.sameLine(0, 6)
    ui.textColored(word, col)
  end
  ui.text(string.format('Balance target: %s · turn-in push %.0f%% of corners · lockups F %d / R %d',
    mode.label, (engine.turninPush or 0) * per, engine.lockF or 0, engine.lockR or 0))
  local function damp(e)
    local h = engine:damperHistVerdict(e)
    if not h.measured then return 'measuring' end
    local s = string.format('bump %.0f%% / reb %.0f%%', h.share * 100, (1 - h.share) * 100)
    if h.verdict == 'bumpSoft' then return s .. ' (bump soft)' elseif h.verdict == 'rebSoft' then return s .. ' (rebound soft)' end
    return s .. ' (even)'
  end
  ui.text(string.format('Travel used F %.0f%% / R %.0f%% · max-travel hits F %d / R %d · dampers F %s · R %s',
    (engine.travelUsePeakF or 0) * 100, (engine.travelUsePeakR or 0) * 100,
    engine.springsHitsF or 0, engine.springsHitsR or 0, damp('F'), damp('R')))
  ui.popFont()
end

-- Balance target picker: one button per BALANCE_MODES entry, the active one
-- marked. Build and the advice lines read settings.balanceMode.
-- Brake bias one-time write: status + re-arm, in the main window (the
-- Settings window is not reachable for this app).
local function drawBiasRearm()
  local carKey = engine.carId or ''
  if carKey == '' then return end
  if engine:biasBaselineDone(carKey) then
    if ui.button('Re-arm brake-bias write (this car)##biasrearm', vec2(260, 22)) then
      settings.biasBaselineCars = tostring(settings.biasBaselineCars or ''):gsub('|' .. carKey:gsub('%p', '%%%0') .. '|', '|')
    end
  else
    ui.pushFont(ui.Font.Small)
    ui.text('Brake bias: the one-time calculated write is armed for this car')
    ui.popFont()
  end
end

local function drawBalanceModePicker()
  ui.text('Balance target:')
  for _, key in ipairs(BALANCE_MODE_ORDER) do
    ui.sameLine(0, 6)
    local active = (balanceMode() == BALANCE_MODES[key])
    local label = active and ('[' .. BALANCE_MODES[key].label .. ']') or BALANCE_MODES[key].label
    if ui.button(label .. '##balmode' .. key, vec2(96, 22)) then
      settings.balanceMode = key
    end
  end
end

function script.windowMain(dt)
  local car = ac.getCar(0)
  local sim = ac.getSim()

  drawHeader(car, sim)
  ui.offsetCursorY(4)
  drawLiveTyres(car)
  ui.offsetCursorY(6)
  ui.separator()
  ui.offsetCursorY(4)
  drawWindowSummary()
  ui.offsetCursorY(6)
  ui.separator()
  ui.offsetCursorY(4)
  ui.text('WHAT TO CHANGE - one at a time, top of the list first')
  ui.offsetCursorY(2)
  drawAdviceList(settings.compact)

  ui.offsetCursorY(10)
  ui.separator()
  ui.offsetCursorY(6)
  ui.text(engine.exportMsg)
  ui.offsetCursorY(6)

  if ui.button('RESET TELEMETRY', vec2(180, 28)) then
    engine:reset()
    engine.exportMsg = 'Telemetry reset'
  end
  ui.sameLine(0, 10)
  if ui.button('SAVE PIT NOTES', vec2(180, 28)) then
    engine:export()
  end
  ui.sameLine(0, 10)
  -- v1.9.2, by direct request: "Some testers are having trouble finding the
  -- folder SetupCoach_Notes where the debug and pitnotes.txt get written."
  -- The path was already auto-detected correctly (findDocsRoot uses CSP's
  -- own ac.FolderID.ACDocuments, which follows a moved/OneDrive-redirected
  -- Documents folder same as the game itself does) - the problem was pure
  -- discoverability, not resolution, so the fix is removing the need to
  -- navigate there by hand at all. io.createDir first and ignore its result
  -- (best-effort) so this also works on a fresh install where nothing has
  -- been saved yet and the folder may not exist.
  if ui.button('OPEN NOTES FOLDER', vec2(180, 28)) then
    local root = findDocsRoot()
    if not root or root == '' then
      engine.exportMsg = 'ERROR: cannot find Documents/Assetto Corsa folder'
    else
      local dir = root .. '/SetupCoach_Notes'
      pcall(io.createDir, dir)
      local okOpen = pcall(os.openInExplorer, dir)
      engine.exportMsg = okOpen and ('Opened: ' .. dir) or ('Could not open - path is: ' .. dir)
    end
  end

  ui.offsetCursorY(10)
  ui.separator()
  ui.offsetCursorY(6)
  ui.pushFont(ui.Font.Small)
  ui.text('OPTIMAL SETUP - writes a new .ini next to your setups, never overwrites yours')
  ui.popFont()
  -- Surfaced explicitly because static-camber-not-captured is the one
  -- remaining precondition (base-file requirement was removed in 4.2.0 -
  -- everything except camber and pressure now works off the car's own
  -- setup.ini schema, no base file needed).
  ui.pushFont(ui.Font.Small)
  ui.text(string.format('Static camber: %s',
    engine.staticCamberCaptured and 'captured' or '(not yet - sit stationary in the pits once)'))
  ui.popFont()
  -- v1.7.5: module write toggles moved here (also, in windowSettings) -
  -- right where you're already looking when you're about to press Build.
  engine.showModuleToggles = checkbox('Which modules does Build write?', engine.showModuleToggles)
  if engine.showModuleToggles then
    ui.offsetCursorY(4)
    drawModuleToggleCheckboxes()
    ui.offsetCursorY(4)
  end
  drawBalanceModePicker()
  drawBiasRearm()
  if ui.button('BUILD OPTIMAL SETUP', vec2(180, 28)) then
    engine:buildOptimalSetup()
  end
  -- v2.1.0: one-shot gate override, for testing. The NEXT Build skips the
  -- clean-laps / corners gate (everything else - consumption, lap
  -- consistency, the lever chain - runs as normal) and the log says so.
  -- One-shot so it can't be left on by accident.
  ui.sameLine(0, 10)
  if ui.button(engine.gateOverrideOnce and 'OVERRIDE ARMED (next Build)' or 'OVERRIDE LAP GATE (test)', vec2(220, 28)) then
    engine.gateOverrideOnce = not engine.gateOverrideOnce
  end
  ui.offsetCursorY(4)
  ui.textWrapped(engine.setupMsg or '')
  if engine.setupChanges and #engine.setupChanges > 0 then
    ui.offsetCursorY(4)
    for i = 1, #engine.setupChanges do
      ui.pushFont(ui.Font.Small)
      ui.textWrapped('- ' .. engine.setupChanges[i])
      ui.popFont()
    end
  end

  ui.offsetCursorY(10)
  ui.separator()
  ui.offsetCursorY(6)
  ui.pushFont(ui.Font.Small)
  ui.text('GRIP TREND - did the last setup change help? compares lateral-G and best lap vs a saved baseline')
  ui.popFont()
  if ui.button('SAVE GRIP BASELINE', vec2(180, 28)) then
    engine:saveGripBaseline(car, sim)
  end
  ui.offsetCursorY(4)
  local gripText = engine:gripCompareText(car, sim)
  if gripText then
    ui.textWrapped(gripText)
  elseif engine.gripMsg ~= '' then
    ui.textWrapped(engine.gripMsg)
  else
    ui.textWrapped('No baseline saved for this car/track yet.')
  end
end

function script.windowHud(dt)
  local car = ac.getCar(0)
  ui.pushFont(ui.Font.Small)
  ui.text(string.format('SETUP COACH  ·  %d smp  ·  lap %d', engine.samples, engine.completedLaps))
  ui.popFont()

  local urgent = engine:urgent()
  for i = 1, math.min(3, #urgent) do
    local a = urgent[i]
    ui.text(a.id .. ': ' .. a.text)
  end

  if car then
    ui.text(string.format('FL:%s FR:%s RL:%s RR:%s  ·  %.0f km/h',
      psiStr(engine.livePressFL), psiStr(engine.livePressFR),
      psiStr(engine.livePressRL), psiStr(engine.livePressRR), n(car.speedKmh)))
  end
end

function script.windowSettings(dt)
  ui.text('Event threshold')
  settings.threshold = ui.slider('##th', n(settings.threshold, 2), 1, 5, '%.0f')
  -- v2.0.0: the Build evidence gate. ui.slider RETURNS the value (unlike
  -- ui.checkbox - see the v1.7.7 note), so plain assignment is right.
  drawBalanceModePicker()
  ui.text('Clean laps required before Build will write')
  settings.buildMinLaps = ui.slider('##minlaps', n(settings.buildMinLaps, 2), 1, 5, '%.0f laps')
  -- v2.3.0: Build writes brake bias ONCE per car (a calculated baseline),
  -- then it is advice only. This re-arms that single write for the current
  -- car - e.g. after a big setup or track change.
  local carKey = engine.carId or ''
  if carKey ~= '' and engine:biasBaselineDone(carKey) then
    if ui.button('Re-arm one-time brake-bias write for this car', vec2(320, 24)) then
      settings.biasBaselineCars = tostring(settings.biasBaselineCars or ''):gsub('|' .. carKey:gsub('%p', '%%%0') .. '|', '|')
    end
  else
    ui.text('Brake bias: one-time calculated write still available for this car')
  end
  -- v2.4.0: forget this car's lever ledger and branch passes (all tracks) -
  -- a STOPPED branch starts again from pass 1.
  if carKey ~= '' and ui.button('Reset lever history for this car', vec2(320, 24)) then
    engine:leverHistoryReset(carKey)
  end
  ui.text('Cold→hot pressure rise')
  settings.psiRise = ui.slider('##rise', n(settings.psiRise, 3), 1, 8, '%.1f psi')
  settings.useKpa = checkbox('Show kPa', settings.useKpa)
  settings.compact = checkbox('Hide OK items', settings.compact)
  settings.diagnoseTemps = checkbox('Use temp analysis', settings.diagnoseTemps)
  settings.sampleReplay = checkbox('Sample in replay', settings.sampleReplay)

  ui.offsetCursorY(8)
  ui.separator()
  ui.offsetCursorY(6)
  drawModuleToggleCheckboxes()

  ui.offsetCursorY(8)
  ui.separator()
  ui.offsetCursorY(6)
  ui.text('Base setup file for "Build Optimal Setup" (optional)')
  ui.pushFont(ui.Font.Small)
  ui.textWrapped('Name only, no .ini, e.g. "quali" - looked for in this track\'s setup folder, then generic. Leave blank: the app already finds last.ini automatically, this is only for naming a specific saved setup instead.')
  ui.popFont()
  -- ui.inputText's exact signature wasn't confirmed against every CSP build,
  -- so this is wrapped in pcall: worst case the field just doesn't update
  -- rather than breaking the rest of the settings window.
  local okInput, res = pcall(ui.inputText, '##baseSetup', settings.baseSetupName or '', 64)
  if okInput and type(res) == 'string' then
    settings.baseSetupName = res
  else
    ui.text('(base setup name: ' .. (settings.baseSetupName ~= '' and settings.baseSetupName or 'none') .. ' - text input unavailable on this CSP build)')
  end
end

function script.onShow() end

function script.onSimUpdate(dt)
  engine:update(dt, ac.getCar(0), ac.getSim())
end

function script.update(dt)
  if not script._simBound then
    engine:update(dt, ac.getCar(0), ac.getSim())
  end
end

local _origSim = script.onSimUpdate
function script.onSimUpdate(dt)
  script._simBound = true
  _origSim(dt)
end
