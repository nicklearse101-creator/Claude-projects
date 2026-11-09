"""Build the rally car into staging/<car id> (never touches the installed car), ready for install_staged.py.
build_rally_on_stock loads its own copy of build_car (b.bc), so BOTH must be pointed at staging."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import build_rally_on_stock as b

STAGE = b.bc.PROJECT / "staging" / b.bc.CAR_ID
if __name__ == "__main__":
    STAGE.mkdir(parents=True, exist_ok=True)
    b.bc.CAR = b.CAR = STAGE
    assert b.bc.CAR == STAGE and b.CAR == STAGE and "staging" in str(STAGE), "refusing: not pointed at staging"
    off = b.build()
    print(f"staged {STAGE}\nGRAPHICS_OFFSET={off}")
