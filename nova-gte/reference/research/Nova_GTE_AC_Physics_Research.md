# 1989 Vauxhall Nova GTE — Assetto Corsa Physics Research & Tuning Plan

**Target:** UK-market, right-hand-drive 1989 Vauxhall Nova GTE, standard road trim  
**Purpose:** A research-backed specification and practical workflow for building a believable Assetto Corsa car in Blender/Claude Code.  
**Status:** Research and tuning brief — **not a validated physics pack**. Exact factory alignment, spring/damper data, gear ratios and tyre test data were not all publicly verifiable from the sources available.

---

## 1. Conclusions at a glance

The Nova GTE should feel like a light, front-wheel-drive hot hatch from the late 1980s, not a modern track car:

- Naturally aspirated 1.6-litre, 8-valve, fuel-injected inline-four.
- About **99 bhp at 5,600 rpm** and **135 Nm (100 lb-ft) at 3,400 rpm** in commonly published specifications.
- Transverse front engine, five-speed manual gearbox, front-wheel drive.
- MacPherson struts at the front and a torsion-beam rear axle with separate springs/dampers.
- Front ventilated discs and rear drums are reported for this model.
- Period road tyres, commonly listed as **175/65 R14**; confirm the exact wheel/tyre package against the target car or original brochure.
- Modest aerodynamic grip: handling should come from tyre grip, weight transfer and chassis balance, not large downforce.
- Expect front-tyre saturation under power and a safe, generally understeering balance at the limit. A lift-off or trail-braking response can help the car rotate, but it should not behave like a rear-drive drift car.

Sources for the basic specification and chassis layout are listed in [Sources](#10-sources-and-confidence).

## 2. What is known, and what is estimated?

| Parameter | Working value | Confidence / treatment |
|---|---:|---|
| Engine | E16SE, 1,598 cc, inline-4, SOHC, 8-valve, naturally aspirated, fuel injected | High; repeatedly listed |
| Peak power | 99 bhp / about 74 kW at 5,600 rpm | High for published catalogue-style specs |
| Peak torque | 135 Nm at 3,400 rpm | High for published catalogue-style specs; some secondary listings differ |
| Driven wheels | Front | High |
| Gearbox | 5-speed manual | High |
| Front suspension | MacPherson strut | High |
| Rear suspension | Torsion beam / trailing-arm arrangement, separate coil springs and dampers | High at layout level |
| Brakes | Front ventilated discs; rear drums | Supported by model references; verify exact disc size |
| Tyres | 175/65 R14 commonly listed | Medium; confirm exact factory fitment |
| Wheelbase | About 2,343 mm | Commonly listed; verify against the model year/body |
| Curb mass | Do not hard-code a single value without confirming trim, market and measurement convention | Uncertain in available sources |
| Gear ratios / final drive | Obtain from workshop manual or measured reference | Not set here |
| Spring rates, damper curves, anti-roll bar rates | Tune from road behaviour or find factory data | No trustworthy exact values confirmed |
| Alignment, steering ratio, brake bias | Start from period factory values if available; otherwise tune conservatively | Exact values not established here |
| Centre of gravity / inertia | Estimate from dimensions and mass distribution, then tune against transient behaviour | Requires validation |

**Important:** Avoid false precision. A believable mod is not achieved by filling every `.ini` value with plausible-looking numbers. The confirmed facts should anchor a controlled tuning process; estimates should be labelled as estimates.

## 3. Translate the real car into Assetto Corsa

The original AC car physics are primarily configured through files in the car's `data` directory (or packed into `data.acd`). The key files include:

| AC file | What to use it for |
|---|---|
| `car.ini` | Mass, inertia, fuel, wheelbase-related/basic vehicle data, steering and general configuration |
| `engine.ini` + power lookup table(s) | Engine speed range, torque/power curve, engine inertia, engine braking |
| `drivetrain.ini` | Front-wheel-drive layout, gear ratios, final drive, differential behaviour |
| `suspensions.ini` | Suspension type and geometry, wheel rates, dampers, anti-roll bars, ride height and alignment |
| `tyres.ini` and tyre LUTs | Tyre dimensions, load sensitivity, longitudinal/lateral grip, slip response, pressure and thermal behaviour |
| `brakes.ini` | Brake torque/capacity and front/rear balance |
| `aero.ini` | Drag and lift/downforce behaviour |
| `setup.ini` | What the player can adjust; keep a road car's adjustment range realistic |
| `collider.ini` | Collision shape; important for kerbs and grounding, but not a substitute for physics tuning |

The community [Physics Pipeline guide](https://github.com/archibaldmilton/Girellu/wiki/Physics-Pipeline/56dedad42b52516db68b5edab4ceb7329b899f15) discusses the core AC physics files and a methodical development process. The [Assetto Corsa Japan LABS data-folder guide](https://labs.assettocorsa.jp/documents/tutorial/car_data_build) also recommends working with unpacked `data` during development and matching mass, dimensions and tyre radius before tuning other systems.

### Vanilla AC or Custom Shaders Patch?

Build and validate a **vanilla-compatible baseline first**. CSP extended physics features require explicit configuration and a compatible CSP setup; do not use extended-only keys unless the car is intentionally CSP-dependent. See the [extended physics documentation](https://docs.assetto.cn/en/car/physics/enabling.html).

## 4. Engine and drivetrain

### Engine curve

Use a smooth naturally aspirated curve that reaches approximately 99 bhp at 5,600 rpm and approximately 135 Nm at 3,400 rpm. Do not use a flat torque plateau or a turbo-like boost surge. Power should fall off progressively beyond peak power, with the limiter based on verified engine data rather than guesswork.

The relation between torque and power is:

\[
P_{\mathrm{kW}} = \frac{T_{\mathrm{Nm}}\times \mathrm{rpm}}{9549}
\]

At 135 Nm and 3,400 rpm, this gives about 48.1 kW (64.5 bhp), which is consistent with torque peaking well before the published power peak. At 5,600 rpm, 99 bhp corresponds to about 126 Nm. These points are useful checks for a generated power curve; they do not define every intermediate point.

**Implementation:**
1. Create a torque-versus-RPM table using the two known anchor points.
2. Use workshop/manual data for intermediate values if available.
3. If it is not available, use a conservative smooth curve and clearly mark the intermediate values as estimated.
4. Check that the power curve implied by torque does not exceed the published peak.
5. Tune engine braking, inertia and throttle response to feel like a small naturally aspirated 1980s engine.

### Gearing and differential

Use the correct five forward gears and final-drive ratio from reliable workshop data if possible. Gear ratios strongly affect acceleration and top speed, so **do not copy ratios from a different Nova engine or a modified rally car**. If ratios cannot be verified, record them as provisional and tune them against published acceleration/top-speed figures and observed engine RPM at road speed.

Use a period-appropriate open differential as the default unless a particular car is documented to have a limited-slip unit. Avoid aggressive locking that makes the front axle pull the car around corners unrealistically. Under hard acceleration, the front tyres should have to share cornering and drive forces, producing realistic power-on understeer and inside-wheel traction limits.

### How to validate

- Check acceleration in each gear against period road-test figures if available.
- Confirm RPM versus road speed in top gear using tyre rolling circumference and the chosen gear/final-drive ratios.
- Verify that the car does not accelerate like a modern turbo hot hatch.
- Check wheelspin at low speed and on corner exit; do not solve bad gearing by artificially reducing tyre grip.

## 5. Suspension, weight transfer and steering

The Nova's basic layout is MacPherson struts at the front and a torsion-beam rear. That architecture should be represented accurately before detailed tuning.

### Front axle

- Use a MacPherson-strut geometry, not a double-wishbone substitute.
- Recreate plausible steering axis, caster, camber gain, scrub radius and toe change as closely as the available measurements allow.
- The front tyres carry steering and drive loads. Their combined-force limit should be central to the car's feel.
- Avoid excessive front roll stiffness or overly stiff front springs that make the car skip over bumps.

### Rear axle

- Represent the torsion-beam/trailing-arm arrangement with separate coil springs and dampers.
- The rear axle should contribute to roll stiffness and transient balance without behaving like an independent modern multi-link setup.
- Tune lift-off response carefully. A little rotation under lift or trail braking can feel period-correct; sudden snap oversteer is not the default target.

### Springs and dampers

No reliable exact factory spring rates or damper force curves were established in this research. Start with measured wheel positions and ride height, then tune to reference behaviour rather than guessing a single “correct” number.

Recommended order:
1. Match static ride height and wheel location.
2. Set spring rates to achieve plausible static sag and body movement.
3. Tune low-speed damping for pitch/roll control and high-speed damping for sharp bumps.
4. Add bump-stop behaviour only when the geometry and ride travel justify it.
5. Tune anti-roll bars after spring/damper behaviour is stable.
6. Check kerb response, braking dive, acceleration squat and one-wheel bumps.

A useful AC suspension reference is the [Assetto Corsa Dev Docs suspension page](https://docs.assetto.cn/en/car/physics/suspension.html). Its parameters and extension features vary by AC/CSP version, so check the exact version used by the mod.

### Steering

Use the real steering lock/ratio if documented. Do not set excessive steering lock merely to make the car nimble. Ensure the visual steering wheel rotation, steering rack behaviour and front-wheel angle are consistent. Keep the right-hand-drive cockpit and physical steering components on the right, but remember RHD does not itself determine the physics values.

## 6. Tyres, grip and road feel

Tyres are among the biggest sources of handling errors. A road tyre is not just a grip multiplier.

### Target character

The standard GTE should have useful grip for its era but less lateral capacity and less forgiving load sensitivity than a modern performance tyre. It should respond progressively near the limit. Avoid slick-like grip, excessive curb grip or a tyre that keeps full grip at unrealistic slip angles.

### Tyre setup process

1. Use the correct tyre size and rolling radius. For 175/65 R14, nominal unloaded diameter is approximately **583 mm**:
   - rim diameter: 14 × 25.4 = 355.6 mm
   - nominal sidewall: 175 × 0.65 = 113.75 mm each side
   - nominal diameter: 355.6 + 2 × 113.75 = 583.1 mm
   This is a nominal size calculation; the loaded rolling radius is smaller and varies with tyre, pressure and load.
2. Start with road-tyre parameters from a suitable AC road-car tyre as a *shape/reference*, not a direct copy of a modern tyre.
3. Tune longitudinal and lateral grip together. Power-on understeer should arise naturally from front tyre force demand rather than an arbitrary steering penalty.
4. Check load sensitivity, slip-angle response, combined braking/cornering and grip fall-off.
5. Validate cold and warm pressures/temperatures, but do not invent a detailed thermal model without evidence about the period tyre compound.
6. Test on smooth asphalt first, then bumps and kerbs.

The [AC Dev Docs tyre-physics reference](https://docs.assetto.cn/en/car/physics/tyre-physics.html) describes the tyre configuration and optional CSP extensions. For a standard-compatible car, begin with the parameters supported by the intended AC version and add extensions only if needed.

## 7. Brakes, mass and aerodynamics

### Brakes

Model the reported front ventilated discs and rear drums. The front axle should do most of the braking because weight transfers forward under deceleration, but the rear brakes still need to contribute. Set brake torque and bias to avoid premature rear lock-up while retaining a period road-car pedal feel. Verify actual disc/drum dimensions and master-cylinder details from factory data if possible.

Do not use a modern racing brake package, excessive brake torque or ABS unless the target specification actually has it. A road car from this period should not have modern electronic stability control.

### Mass and inertia

Use a documented kerb mass only after confirming whether the source includes fuel, fluids, driver or optional equipment. Add driver mass consistently. Set the centre of gravity and inertia based on a sensible estimate and then validate the car's pitch, roll and yaw response. Do not use inertia values as a shortcut to mask poor suspension or tyre settings.

The real car is light. It should change direction more readily than a heavy modern car, but it should still have believable body movement and not feel weightless. Mass distribution should reflect a transverse front engine and front-wheel-drive gearbox.

### Aerodynamics

At road-car speeds, aero should be a secondary influence. Use modest drag and do not add meaningful racing downforce without evidence. Avoid tuning high-speed cornering grip by adding arbitrary downforce. Top speed should emerge from power, gearing, drag and rolling resistance; compare against reliable period road-test data where possible.

## 8. Test plan: how to tell whether the physics are right

Record every run with the same fuel load, tyres, track, weather and assists. Change one parameter group at a time.

| Test | What to observe | Likely area to adjust |
|---|---|---|
| Straight-line acceleration | Time, RPM, shift points, wheelspin | Engine curve, gear ratios, final drive, mass |
| Top speed | RPM in top gear, speed plateau | Gearing, power, drag, rolling resistance |
| Steady-state circle / constant-radius corner | Understeer gradient, steering angle, speed at limit | Tyres, alignment, roll stiffness, CG |
| Slalom / quick left-right | Delay, roll response, rear follow-through | Damping, inertia, roll stiffness, steering |
| Lift-off mid-corner | Whether rear helps rotate progressively or snaps | Rear toe/compliance approximation, rear roll balance, tyres |
| Braking in a straight line | Stability, stopping distance, lock-up order | Brake torque, bias, tyre grip, weight transfer |
| Braking while turning | Combined grip and stability | Tyres, brake bias, suspension geometry |
| One-wheel bump / kerb | Whether body and axle react plausibly | Suspension geometry, damping, bump stops, collider |
| Wet surface | Grip reduction and transition | Surface/tyre interaction, not dry setup alone |

### Suggested tuning sequence

1. **Dimensions and static setup:** wheelbase, track widths, tyre radius, ride height, wheel alignment.
2. **Mass:** total mass, driver, fuel, CG, inertia.
3. **Drivetrain:** engine curve, gearbox and final drive.
4. **Tyres:** grip and slip response.
5. **Suspension:** geometry, springs, dampers, anti-roll bars.
6. **Brakes:** torque and bias.
7. **Aero:** only after the mechanical model is stable.
8. **Final validation:** compare acceleration, top speed, braking and cornering against real test data.

Keep a changelog. Do not tune multiple systems at once, or it becomes impossible to know which change improved the result.

## 9. Practical instructions for Claude Code

Give Claude Code the research data and ask it to generate **editable AC physics files with a clear assumptions register**, not to claim exact factory values where none were found.

Suggested instruction:

> Build a standard 1989 UK RHD Vauxhall Nova GTE Assetto Corsa physics baseline. Use the E16SE 1.6-litre naturally aspirated engine with approximately 99 bhp at 5,600 rpm and 135 Nm at 3,400 rpm. Use FWD, five-speed manual, MacPherson front suspension and torsion-beam rear suspension. Treat 175/65 R14 as a provisional tyre size pending confirmation. Keep the car road-going, with period-appropriate grip, no modern electronic aids, no racing downforce and no aftermarket LSD unless documented. Separate verified specifications from estimates in comments and `ASSUMPTIONS.md`. Validate INI syntax against the target AC version. Do not invent exact factory spring rates, damper curves, gearbox ratios, CG coordinates or tyre data. Start with a vanilla-compatible baseline and document any CSP-only features.

Ask Claude to:
- keep all editable data under `content/cars/<car_id>/data/`;
- preserve source values and add comments instead of silently overwriting them;
- create a test log template;
- check file references and lookup-table formats;
- provide a diff for each tuning iteration;
- test in game and report observed failures rather than claiming a simulation has been validated when it has not.

## 10. Sources and confidence

1. **EncyCARpedia — Vauxhall Nova GTE specs (1988–1989)**  
   https://www.encycarpedia.com/vauxhall/88-nova-gte-hatch  
   Useful for engine displacement, 99 bhp at 5,600 rpm, 135 Nm at 3,400 rpm, FWD, five-speed manual, tyre size and suspension/brake layout. Secondary specification source.

2. **Classics World — Vauxhall Nova buyer's guide**  
   https://classicsworld.co.uk/guides/vauxhall-nova-buyers-guide/  
   Supports the basic MacPherson-front/torsion-beam-rear layout and period handling character. General Nova guide rather than a full GTE factory data sheet.

3. **Classics World — Vauxhall Nova road test / history**  
   https://classicsworld.co.uk/cars/vauxhall-nova-saloon-road-test/  
   Supports the broad chassis architecture and model history. Some details concern other Nova variants; use it for architecture, not exact GTE calibration.

4. **Assetto Corsa Physics Pipeline (community guide)**  
   https://github.com/archibaldmilton/Girellu/wiki/Physics-Pipeline/56dedad42b52516db68b5edab4ceb7329b899f15  
   Practical guide to AC physics files and workflow; community-authored rather than official Kunos documentation.

5. **Assetto Corsa Japan LABS — data folder / car data build**  
   https://labs.assettocorsa.jp/documents/tutorial/car_data_build  
   Explains the data directory, core physics files and the importance of matching dimensions, mass and tyre radius early.

6. **Assetto Corsa Dev Docs — suspension**  
   https://docs.assetto.cn/en/car/physics/suspension.html  
   Parameter and suspension-extension reference; extension availability depends on AC/CSP version.

7. **Assetto Corsa Dev Docs — tyre physics**  
   https://docs.assetto.cn/en/car/physics/tyre-physics.html  
   Tyre configuration and optional extension reference.

8. **Assetto Corsa Dev Docs — enabling extended physics**  
   https://docs.assetto.cn/en/car/physics/enabling.html  
   Explains that extended physics requires explicit configuration and compatible Custom Shaders Patch support.

9. **1988–1992 Vauxhall Nova workshop manual listing**  
   https://cdn-4.onlymanuals.com/vauxhall/nova/vauxhall_nova_workshop_manual_1988_1992pdf  
   Potential source for exact service data, gear ratios, alignment and mechanical specifications. The available indexed extract was not sufficient to confirm all GTE-specific figures, so those values are deliberately not asserted here.

### Confidence summary

- **High confidence:** engine family, approximate peak power/torque, FWD, five-speed manual and broad suspension architecture.
- **Medium confidence:** exact standard tyre size and brake configuration; confirm against the 1989 UK GTE brochure or workshop manual.
- **Low / not yet established:** exact curb mass convention, gear ratios/final drive, CG and inertia, spring/damper rates, detailed alignment, steering ratio, brake torque and tyre force curves.

The key conclusion is to make the car feel right by matching the known powertrain and chassis architecture, then validating the dynamics with repeatable tests. A photo-realistic model and a convincing physics model are separate tasks; both need their own measurements and checks.
