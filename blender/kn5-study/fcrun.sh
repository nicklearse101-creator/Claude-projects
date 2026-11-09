#!/usr/bin/env bash
# Run a FreeCAD script headless with everything on D: (temp files, FreeCAD user data, Python cache).
export TEMP='D:\ClaudeData\tmp' TMP='D:\ClaudeData\tmp' TMPDIR='D:\ClaudeData\tmp'
export FREECAD_USER_HOME='D:\ClaudeData\FreeCAD' FREECAD_USER_DATA='D:\ClaudeData\FreeCAD' FREECAD_USER_TEMP='D:\ClaudeData\tmp'
export PYTHONPYCACHEPREFIX='D:\ClaudeData\tmp\pycache'
export CURVESWB='D:\ClaudeData\FreeCAD\Mod\CurvesWB\freecad'
exec /d/FreeCAD/bin/freecadcmd.exe "$@"
