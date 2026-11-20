"""Shared test setup: the first-start tour and the background car warm-up stay off in the tests (test_tour.py and
test_warm_app.py switch them on for themselves)."""
import os

os.environ['R4S_NO_TOUR'] = '1'
os.environ['R4S_NO_WARM'] = '1'     # no car got ready in the background (test_warm_app.py switches it on)
