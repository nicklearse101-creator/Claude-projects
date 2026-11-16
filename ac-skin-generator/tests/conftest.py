"""Shared test setup: the first-start tour stays off in the tests (test_tour.py switches it on for itself)."""
import os

os.environ['R4S_NO_TOUR'] = '1'
