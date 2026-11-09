"""Write the Assetto Corsa data/ folder for the Vauxhall Nova GTE 1989 (Phase 1 skeleton physics).

Every number below is this car's own, from docs/SPEC_SHEET.md, and carries a tag in the generated
ini comments: SOURCED (spec sheet source), ESTIMATE (reasoned, see note) or PLACEHOLDER (to be tuned
with telemetry in Phase 6). The Kunos Escort Mk1 files in the Sunbeam project are used only as a FORMAT
reference (section and key names) and for the generic street-tyre wear/temperature curves, which are
copied verbatim and marked as such. Nothing here is a ported handling value.

Re-running is safe: it rebuilds car/vauxhall_nova_gte_1989/data and never touches the .kn5 files.
Run with:  python tools\\build_car.py
"""
import math
import shutil
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
CAR = PROJECT / "car" / "vauxhall_nova_gte_1989"
DATA = CAR / "data"
FORMAT_REF = Path(r"D:\Claude\talbot_sunbeam_lotus\refs\donor_data\ks_ford_escort_mk1")
CAR_ID = "vauxhall_nova_gte_1989"

# ---------------- numbers ----------------
G = 9.81
WHEELBASE = 2.343                    # SOURCED FIA A-5375 p2
TRACK_F, TRACK_R = 1.320, 1.307      # SOURCED encyCARpedia/auto-data
WIDTH, HEIGHT, LENGTH = 1.535, 1.365, 3.622   # SOURCED FIA / brochure
KERB = 834                           # SOURCED brochure + Haynes
FUEL_TANK = 42                       # SOURCED ultimatespecs/auto-data
DRIVER = 75                          # AC convention: total mass with driver
FUEL_KG = 0.9 * FUEL_TANK * 0.745    # ESTIMATE: kerb weight taken as 90 % fuel
TOTALMASS = round(KERB + DRIVER - FUEL_KG)
CG_LOCATION = 0.62                   # ESTIMATE front weight fraction, FWD hatch with transverse engine (spec GAP)
CG_HEIGHT = 0.50                     # ESTIMATE (spec GAP)
TYRE_R = 0.0254 * 14 / 2 + 0.175 * 0.65    # 175/65 R14 nominal, SOURCED size -> 0.2916 m
RIM_R_AC = 0.0254 * 15 / 2           # AC wants nominal +1 inch (14" rim)
BASEY = -(CG_HEIGHT - TYRE_R)        # same both axles
cg_z = WHEELBASE / 2 - (1 - CG_LOCATION) * WHEELBASE
GRAPHICS_OFFSET = f"0,{-CG_HEIGHT:.3f},{-cg_z:.3f}"

STEER_RATIO = 21.4                   # SOURCED FIA p9, Haynes
STEER_LOCK = round(3.8 / 2 * 360)    # SOURCED Haynes 3.8 turns lock to lock -> 684 deg each way, ~32 deg at the wheel

# ride frequencies 1.45 Hz front / 1.6 Hz rear (ESTIMATE targets in SPEC_SHEET "Chassis derivations")
m_f = TOTALMASS * CG_LOCATION / 2
m_r = TOTALMASS * (1 - CG_LOCATION) / 2
def wheel_rate(f, m): return round((2 * math.pi * f) ** 2 * m, -2)
K_F, K_R = wheel_rate(1.45, m_f), wheel_rate(1.60, m_r)
def damp(k, m, z): return round(2 * math.sqrt(k * m) * z, -1)

GEARS = [3.55, 2.14, 1.43, 1.12, 0.89]   # SOURCED FIA p6, brochure
GEAR_R, FINAL = 3.31, 3.74               # SOURCED FIA p6/p7, Haynes
IDLE, LIMITER = 925, 6200                # SOURCED Haynes idle 900-950; limiter ESTIMATE (brochure curve ends 6000)
# crank torque Nm, read from the brochure graph (SPEC_SHEET torque curve, ESTIMATE of values); peak 135 Nm @ 3400
TORQUE = [(0, 60), (500, 72), (1000, 90), (1500, 103), (2000, 115), (2500, 125), (3000, 132), (3500, 135),
          (4000, 135), (4500, 135), (5000, 135), (5500, 128), (5600, 126),
          (6000, 118), (6200, 110), (6500, 0)]   # 5500/5600 trimmed so peak = 74 kW @ 5600 (SOURCED)
CD, FRONTAL_AREA = 0.37, 1.68            # Cd SOURCED brochure; area ESTIMATE 0.8 x width x height


def w(name, text):
    (DATA / name).write_text(text.strip() + "\n", encoding="utf-8")


def car_ini():
    w("car.ini", f"""
[HEADER]
VERSION=1

[INFO]
SCREEN_NAME=Vauxhall Nova GTE 1989

[BASIC]
GRAPHICS_OFFSET={GRAPHICS_OFFSET}		; model origin = ground midway between axles; physics origin = CG
GRAPHICS_PITCH_ROTATION=0
TOTALMASS={TOTALMASS}						; kerb {KERB} kg (SOURCED) + driver {DRIVER} - fuel {FUEL_KG:.0f} kg (ESTIMATE)
INERTIA={WIDTH},{HEIGHT},{LENGTH}			; body width, height, length (SOURCED)

[GRAPHICS]
DRIVEREYES=-0.36,1.13,-0.10			; RHD, from the modelled seat/wheel (ESTIMATE, tune in game)
ONBOARD_EXPOSURE=31
OUTBOARD_EXPOSURE=31
ON_BOARD_PITCH_ANGLE=-3
BUMPER_CAMERA_POS=0.0,0.50,1.80
BONNET_CAMERA_POS=0.0,1.05,0.60
MIRROR_POSITION=0.0,1.15,0.10
VIRTUAL_MIRROR_ENABLED=0
USE_ANIMATED_SUSPENSIONS=0
SHAKE_MUL=3
FUEL_LIGHT_MIN_LITERS=6
BONNET_CAMERA_PITCH=0

[CONTROLS]
FFMULT=2.0						; PLACEHOLDER, no power steering
STEER_ASSIST=1.000
STEER_LOCK={STEER_LOCK}					; SOURCED 3.8 turns lock to lock
STEER_RATIO={STEER_RATIO}				; SOURCED
LINEAR_STEER_ROD_RATIO=0.00244		; ESTIMATE from the front geometry (steering arm ~0.14 m)

[FUEL]
CONSUMPTION=0.0021				; PLACEHOLDER (39 mpg UK combined to be matched in Phase 6)
FUEL=20
MAX_FUEL={FUEL_TANK}				; SOURCED

[FUELTANK]
POSITION=0,-0.25,-0.75				; ESTIMATE under the rear seat

[RIDE]
PICKUP_FRONT_HEIGHT=-0.35
PICKUP_REAR_HEIGHT=-0.35

[PIT_STOP]
TYRE_CHANGE_TIME_SEC=10
FUEL_LITER_TIME_SEC=0.6
BODY_REPAIR_TIME_SEC=20
ENGINE_REPAIR_TIME_SEC=2
SUSP_REPAIR_TIME_SEC=30
""")


def suspensions_ini():
    fb, fr = damp(K_F, m_f, 0.22), damp(K_F, m_f, 0.45)
    rb, rr = damp(K_R, m_r, 0.22), damp(K_R, m_r, 0.45)
    w("suspensions.ini", f"""
[HEADER]
VERSION=4

[BASIC]
WHEELBASE={WHEELBASE}						; SOURCED FIA
CG_LOCATION={CG_LOCATION}					; ESTIMATE

[ARB]
FRONT=9000							; PLACEHOLDER (20-22 mm bar, ESTIMATE in spec sheet)
REAR=0								; twist beam roll stiffness - PLACEHOLDER until modelled

; Geometry: ESTIMATE from the Corsa A/Nova layout (strut + lower arm front, rack behind the axle;
; twist beam rear modelled as two parallel trailing arms). Castor 1.8 deg, SAI ~8 deg by construction.
[FRONT]
TYPE=STRUT
BASEY={BASEY:.3f}							; CG height {CG_HEIGHT} m ESTIMATE
TRACK={TRACK_F}							; SOURCED
ROD_LENGTH=0.0
HUB_MASS=38							; ESTIMATE
RIM_OFFSET=0.0
STRUT_CAR=0.150, 0.495, -0.019
STRUT_TYRE=0.065, -0.105, 0.0
WBCAR_BOTTOM_FRONT=0.365, -0.105, 0.080
WBCAR_BOTTOM_REAR=0.365, -0.105, -0.330
WBTYRE_BOTTOM=0.065, -0.105, 0.0
; Steering points sit on the +Z side: AC drives the rack one way only, and the arm behind the axle (the
; real Nova has its rack on the bulkhead, Haynes Ch.8) steered backwards in-game (Nik, 2026-10-12).
; Mirrored to the front with the tie-rod end slightly outboard of the balljoint to keep Ackermann.
WBCAR_STEER=0.410, -0.075, 0.150
WBTYRE_STEER=0.055, -0.075, 0.115
TOE_OUT=0.00013							; Haynes 0-2 mm total toe-out laden -> ~1 mm (SOURCED range)
STATIC_CAMBER=-0.3						; Haynes -0.75..+0.75 deg (SOURCED range)
SPRING_RATE={K_F:.0f}						; wheel rate for 1.45 Hz ride (ESTIMATE)
PROGRESSIVE_SPRING_RATE=0
BUMP_STOP_RATE=30000
BUMPSTOP_UP=0.080
BUMPSTOP_DN=0.080
PACKER_RANGE=0.160
DAMP_BUMP={fb:.0f}						; 0.22 critical (ESTIMATE)
DAMP_FAST_BUMP={fb * 0.6:.0f}
DAMP_FAST_BUMPTHRESHOLD=0.100
DAMP_REBOUND={fr:.0f}						; 0.45 critical (ESTIMATE)
DAMP_FAST_REBOUND={fr * 0.6:.0f}
DAMP_FAST_REBOUNDTHRESHOLD=0.100

[REAR]
TYPE=DWB
BASEY={BASEY:.3f}
TRACK={TRACK_R}							; SOURCED
ROD_LENGTH=0.0
HUB_MASS=30							; ESTIMATE
RIM_OFFSET=0.0
WBCAR_TOP_FRONT=0.150, 0.030, 0.480
WBCAR_TOP_REAR=0.350, 0.030, 0.480
WBCAR_BOTTOM_FRONT=0.150, -0.040, 0.480
WBCAR_BOTTOM_REAR=0.350, -0.040, 0.480
WBTYRE_TOP=0.020, 0.030, 0.0
WBTYRE_BOTTOM=0.020, -0.040, 0.0
WBCAR_STEER=0.300, -0.005, 0.120		; toe link on the same side as the front, so TOE_OUT reads the same way
WBTYRE_STEER=0.040, -0.005, 0.120
TOE_OUT=-0.00030						; Haynes 0-4 mm toe-in -> ~2 mm (SOURCED range)
STATIC_CAMBER=-1.1						; Haynes -0.67..-1.58 deg (SOURCED range)
SPRING_RATE={K_R:.0f}						; wheel rate for 1.6 Hz ride (ESTIMATE)
PROGRESSIVE_SPRING_RATE=0
BUMP_STOP_RATE=30000
BUMPSTOP_UP=0.080
BUMPSTOP_DN=0.090
PACKER_RANGE=0.170
DAMP_BUMP={rb:.0f}
DAMP_FAST_BUMP={rb * 0.6:.0f}
DAMP_FAST_BUMPTHRESHOLD=0.100
DAMP_REBOUND={rr:.0f}
DAMP_FAST_REBOUND={rr * 0.6:.0f}
DAMP_FAST_REBOUNDTHRESHOLD=0.100

[GRAPHICS_OFFSETS]
WHEEL_LF=0.0
SUSP_LF=0.0
WHEEL_RF=0.0
SUSP_RF=0.0
WHEEL_LR=0.0
SUSP_LR=0.0
WHEEL_RR=0.0
SUSP_RR=0.0

[DAMAGE]
MIN_VELOCITY=40
GAIN=0.0004
MAX_DAMAGE=0.05
DEBUG_LOG=0
""")


def engine_files():
    (DATA / "power.lut").write_text("\n".join(f"{r}|{t}" for r, t in TORQUE) + "\n", encoding="utf-8")
    w("engine.ini", f"""
[HEADER]
VERSION=1
POWER_CURVE=power.lut			; crank torque from the brochure graph (ESTIMATE of values)
COAST_CURVE=FROM_COAST_REF

[ENGINE_DATA]
ALTITUDE_SENSITIVITY=0.1
INERTIA=0.10					; PLACEHOLDER
LIMITER={LIMITER}					; ESTIMATE (fuel cut not sourced)
LIMITER_HZ=20
MINIMUM={IDLE}					; SOURCED Haynes idle 900-950 rpm

[COAST_REF]
RPM=6000
TORQUE=40					; PLACEHOLDER engine braking
NON_LINEARITY=0

[COAST_DATA]
COAST0=0
COAST1=0
COAST=0.0000015

[COAST_CURVE]
FILENAME=coast.lut

[DAMAGE]
TURBO_BOOST_THRESHOLD=10
TURBO_DAMAGE_K=0
RPM_THRESHOLD=6800
RPM_DAMAGE_K=1
""")
    (DATA / "throttle.lut").write_text("\n".join(f"{x}|{x}" for x in range(0, 101, 10)) + "\n", encoding="utf-8")


def drivetrain_ini():
    gears = "\n".join(f"GEAR_{i + 1}={g}" for i, g in enumerate(GEARS))
    w("drivetrain.ini", f"""
[HEADER]
VERSION=3

[TRACTION]
TYPE=FWD					; SOURCED

[GEARS]
COUNT=5
GEAR_R=-{GEAR_R}				; SOURCED FIA p6
{gears}
FINAL={FINAL}				; SOURCED FIA p7, Haynes

[DIFFERENTIAL]
POWER=0				; open differential (road car, no LSD listed)
COAST=0
PRELOAD=0

[GEARBOX]
CHANGE_UP_TIME=300		; "rubbery gearshift" - PLACEHOLDER
CHANGE_DN_TIME=320
AUTO_CUTOFF_TIME=0
SUPPORTS_SHIFTER=1
VALID_SHIFT_RPM_WINDOW=800
CONTROLS_WINDOW_GAIN=0.4
INERTIA=0.02

[CLUTCH]
MAX_TORQUE=250				; 200 mm plate (SOURCED size), torque ESTIMATE

[AUTOCLUTCH]
UPSHIFT_PROFILE=NONE
DOWNSHIFT_PROFILE=DOWNSHIFT_PROFILE
USE_ON_CHANGES=0
MIN_RPM=1100
MAX_RPM=1700
FORCED_ON=0

[DOWNSHIFT_PROFILE]
POINT_0=50
POINT_1=280
POINT_2=900

[AUTOBLIP]
ELECTRONIC=0
POINT_0=20
POINT_1=140
POINT_2=200
LEVEL=0.6

[DAMAGE]
RPM_WINDOW_K=100

[AUTO_SHIFTER]
UP=5900
DOWN=3000
SLIP_THRESHOLD=0.95
GAS_CUTOFF_TIME=0.300
""")
    # final.rto: just the standard ratio until optional ratios are sourced
    (DATA / "final.rto").write_text("19//71|3.74\n", encoding="utf-8")


def tyres_ini():
    def axle(pressure, fz0):
        return f"""NAME=Road 175/65 R14
SHORT_NAME=R
WIDTH=0.175					; SOURCED size
RADIUS={TYRE_R:.4f}				; 175/65 R14 nominal (SOURCED size)
RIM_RADIUS={RIM_R_AC:.4f}			; 14" rim, AC convention nominal +1"
ANGULAR_INERTIA=0.85				; ESTIMATE rim+tyre+brake
DAMP=500
RATE=235000					; ESTIMATE vertical rate for a 175 section
DY0=1.08					; PLACEHOLDER road-tyre grip, tune with telemetry
DY1=-0.05
DX0=1.10
DX1=-0.05
WEAR_CURVE=street_wear.lut		; generic Kunos street curve (format reference copy)
SPEED_SENSITIVITY=0.0035
RELAXATION_LENGTH=0.07
ROLLING_RESISTANCE_0=10
ROLLING_RESISTANCE_1=0.0005
ROLLING_RESISTANCE_SLIP=4000
FLEX=0.0009
CAMBER_GAIN=0.12
DCAMBER_0=1.1
DCAMBER_1=-13
FRICTION_LIMIT_ANGLE=8.0
XMU=0.27
PRESSURE_STATIC={pressure}				; SOURCED Haynes cold pressure (psi)
PRESSURE_SPRING_GAIN=5400
PRESSURE_FLEX_GAIN=0.5
PRESSURE_RR_GAIN=0.6
PRESSURE_D_GAIN=0.006
PRESSURE_IDEAL=30
FZ0={fz0:.0f}					; static corner load (ESTIMATE from mass and CG)
LS_EXPY=0.75
LS_EXPX=0.76
DX_REF=1.10
DY_REF=1.08
FLEX_GAIN=0.04
FALLOFF_LEVEL=0.90
FALLOFF_SPEED=1
CX_MULT=1.0
RADIUS_ANGULAR_K=0.02
BRAKE_DX_MOD=0.02"""

    thermal = """SURFACE_TRANSFER=0.0200
PATCH_TRANSFER=0.00027
CORE_TRANSFER=0.000290
INTERNAL_CORE_TRANSFER=0.00055
FRICTION_K=0.058
ROLLING_K=0.26
PERFORMANCE_CURVE=tcurve_street.lut
GRAIN_GAMMA=1
GRAIN_GAIN=0.3
BLISTER_GAMMA=1
BLISTER_GAIN=0.2
COOL_FACTOR=1.6
SURFACE_ROLLING_K=0.85"""
    w("tyres.ini", f"""
[HEADER]
VERSION=10

[VIRTUALKM]
USE_LOAD=1

[COMPOUND_DEFAULT]
INDEX=0

[FRONT]
{axle(26, m_f * G)}

[REAR]
{axle(23, m_r * G)}

[THERMAL_FRONT]
{thermal}

[THERMAL_REAR]
{thermal}
""")
    # generic Kunos street curves, copied verbatim as format/behaviour references
    shutil.copy(FORMAT_REF / "street_front.lut", DATA / "street_wear.lut")
    shutil.copy(FORMAT_REF / "tcurve_street.lut", DATA / "tcurve_street.lut")


def brakes_ini():
    w("brakes.ini", """
[HEADER]
VERSION=1

[DATA]
MAX_TORQUE=1500			; PLACEHOLDER, tune to period stopping distance in Phase 6
FRONT_SHARE=0.70			; ESTIMATE: 236 mm vented discs front (SOURCED), drums rear
HANDBRAKE_TORQUE=800		; PLACEHOLDER
COCKPIT_ADJUSTABLE=0
ADJUST_STEP=0.5

[DISCS_GRAPHICS]
DISC_LF=DISK_LF
DISC_RF=DISK_RF
DISC_LR=DISK_LR
DISC_RR=DISK_RR
FRONT_MAX_GLOW=0.0
REAR_MAX_GLOW=0.0
LAG_HOT=0.995
LAG_COOL=0.98

[TEMPS_FRONT]
COOL_TRANSFER=0.008
TORQUE_K=0.9
PERF_CURVE=(|0=0.85|300=0.95|450=1.0|550=0.9|700=0.6|)
COOL_SPEED_FACTOR=0.018

[TEMPS_REAR]
COOL_TRANSFER=0.006
TORQUE_K=0.9
PERF_CURVE=(|0=0.85|300=0.95|450=1.0|550=0.9|700=0.6|)
COOL_SPEED_FACTOR=0.010
""")


def aero_files():
    cd_lut = [(-10, 1.0), (-2, 0.375), (0, CD), (2, 0.372), (5, 0.382), (8, 0.41), (10, 0.43), (14, 0.47), (20, 0.50), (30, 0.82)]
    (DATA / "wing_body_AOA_CD.lut").write_text("\n".join(f"{a}|{c}" for a, c in cd_lut) + "\n", encoding="utf-8")
    (DATA / "wing_body_AOA_CL.lut").write_text("-10|0\n0|0\n10|0\n", encoding="utf-8")
    w("aero.ini", f"""
[HEADER]
VERSION=2

[WING_0]
NAME=BODY
CHORD=1
SPAN={FRONTAL_AREA}				; frontal area ESTIMATE (chord x span)
POSITION=0,0.10,0.0
LUT_AOA_CL=wing_body_AOA_CL.lut
LUT_GH_CL=
CL_GAIN=0
LUT_AOA_CD=wing_body_AOA_CD.lut		; Cd {CD} at 0 deg (SOURCED brochure)
LUT_GH_CD=
CD_GAIN=1
ANGLE=0
ZONE_FRONT_CL=0
ZONE_FRONT_CD=0.005
ZONE_REAR_CL=0
ZONE_REAR_CD=0.005
ZONE_LEFT_CL=0
ZONE_LEFT_CD=0.01
ZONE_RIGHT_CL=0
ZONE_RIGHT_CD=0.01
""")


def misc_files():
    w("electronics.ini", """
[ABS]
SLIP_RATIO_LIMIT=0.12
CURVE=
PRESENT=0			; no ABS on the 1989 GTE (SOURCED brochure)
ACTIVE=0
RATE_HZ=240

[TRACTION_CONTROL]
SLIP_RATIO_LIMIT=0.10
CURVE=
PRESENT=0
ACTIVE=0
RATE_HZ=220
MIN_SPEED_KMH=50
""")
    w("ai.ini", """
[HEADER]
VERSION=3

[GEARS]
UP=5900
DOWN=3000
SLIP_THRESHOLD=0.95
GAS_CUTOFF_TIME=0.300

[PEDALS]
GASGAIN=4.0
BRAKE_HINT=0.92
TRAIL_HINT=1

[STEER]
STEER_GAIN=1.95

[LOOKAHEAD]
BASE=20
GAS_BRAKE_LOOKAHEAD=0

[ULTRA_GRIP]
VALUE=1.2

[PHYSICS_HINTS]
AERO_HINT=1
""")
    w("lods.ini", f"""
[COCKPIT_HR]
DISTANCE_SWITCH=7

[LOD_0]
FILE={CAR_ID}.kn5
IN=0
OUT=2000
""")
    w("colliders.ini", f"""
[COLLIDER_0]
CENTRE=0,{-CG_HEIGHT + 0.25:.3f},{cg_z * -1 + 0.0:.3f}
SIZE={WIDTH - 0.05:.3f},0.10,{LENGTH - 0.30:.3f}
GROUND_ENABLE=1
""")
    w("fuel_cons.ini", "[FUEL_EVAL]\nKM_PER_LITER=13.9\t\t; 39 mpg UK combined (SOURCED ultimatespecs)")
    w("sounds.ini", """
[SKIDS]
ENTRY_POINT=0.45
MIX_VOLUME=0.6
PITCH_BASE=0.6
PITCH_GAIN=0.18

[WIND]
SPEED_GAIN_0=0
SPEED_GAIN_1=0.0003
VOLUME_GAIN=0.7
PITCH_REFERENCE=50
PITCH_GAIN=0.3

[TYRE_ROLLING]
SPEED_GAIN_0=0.0015
SPEED_GAIN_1=0.0001
VOLUME_GAIN=0.8
PITCH_REFERENCE=45
PITCH_GAIN=0.2

[BACKFIRE]
MAXGAS=0.0
MINRPM=6000
MAXRPM=7000
TRIGGERGAS=0.8
VOLUME_IN=1.0
VOLUME_OUT=0.5
VOLUME_SCALE_OUT=2

[BODY_WORK]
MIN=0.2
GAIN=1

[ENGINE]
POSITION=front
""")
    w("setup.ini", """
[FUEL]
SHOW_CLICKS=0
TAB=GENERIC
NAME=Fuel
MIN=1
MAX=42
STEP=1
POS_X=0.5
POS_Y=0
HELP=HELP_FUEL

[PRESSURE_LF]
SHOW_CLICKS=0
TAB=TYRES
NAME=Pressure LF
MIN=18
MAX=40
STEP=1
POS_X=0
POS_Y=0
HELP=HELP_PRESSURE

[PRESSURE_RF]
SHOW_CLICKS=0
TAB=TYRES
NAME=Pressure RF
MIN=18
MAX=40
STEP=1
POS_X=1
POS_Y=0
HELP=HELP_PRESSURE

[PRESSURE_LR]
SHOW_CLICKS=0
TAB=TYRES
NAME=Pressure LR
MIN=18
MAX=40
STEP=1
POS_X=0
POS_Y=1
HELP=HELP_PRESSURE

[PRESSURE_RR]
SHOW_CLICKS=0
TAB=TYRES
NAME=Pressure RR
MIN=18
MAX=40
STEP=1
POS_X=1
POS_Y=1
HELP=HELP_PRESSURE
""")
    for name in ("cameras.ini", "dash_cam.ini", "damage.ini", "driver3d.ini"):
        shutil.copy(FORMAT_REF / name, DATA / name)   # format templates, positions refined once the cockpit exists
    for name in ("lights.ini", "mirrors.ini", "blurred_objects.ini", "wing_animations.ini"):
        w(name, "; filled in once the model has these nodes")
    # Needles rest pointing straight up; dials sweep 270 deg (7:30 -> 4:30), small gauges ~90 deg.
    # Speedo 20-120 mph over 270 deg (photo redgte_10), tacho 0-7000 over 270 deg. Sign of rotation to be
    # confirmed in game (flip STEP/ZERO signs if a needle runs backwards).
    kmh_per_deg = (100 * 1.609344) / 270.0
    w("analog_instruments.ini", f"""
[RPM_INDICATOR]
OBJECT_NAME=ARROW_RPM
ZERO=-135
MIN_VALUE=0
STEP={270.0 / 7000:.6f}
OBJECT_NAME_MAX=

[SPEED_INDICATOR]
OBJECT_NAME=ARROW_SPEED
ZERO={-135 - 20 * 1.609344 / kmh_per_deg:.3f}
STEP={1 / kmh_per_deg:.6f}

[FUEL_INDICATOR]
OBJECT_NAME=ARROW_FUEL
ZERO=-45
MIN_VALUE=0
STEP={90.0 / FUEL_TANK:.4f}

[WATER_TEMP]
OBJECT_NAME=ARROW_WATER
ZERO=0
STEP=1
MIN_VALUE=40
LUT=(40=-45|90=0|130=45)
""")


def main():
    if DATA.exists():
        shutil.rmtree(DATA)
    DATA.mkdir(parents=True)
    car_ini(); suspensions_ini(); engine_files(); drivetrain_ini(); tyres_ini(); brakes_ini(); aero_files(); misc_files()
    peak = max(t * r * 2 * math.pi / 60 / 1000 for r, t in TORQUE)
    print(f"data written: {len(list(DATA.iterdir()))} files")
    print(f"TOTALMASS {TOTALMASS} kg, CG {CG_LOCATION}, offset {GRAPHICS_OFFSET}, tyre R {TYRE_R:.4f}")
    print(f"wheel rates F {K_F:.0f} R {K_R:.0f} N/m, peak power from lut {peak:.1f} kW")


if __name__ == "__main__":
    main()
