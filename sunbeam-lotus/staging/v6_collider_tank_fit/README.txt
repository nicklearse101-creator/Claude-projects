Fix for talbot_sunbeam_lotus_81_works_backup_v6 - measured in game at Ascari, 6 Oct (car standing in the pits).

1) Copy colliders.ini from this folder over
   D:\SteamLibrary\steamapps\common\assettocorsa\content\cars\talbot_sunbeam_lotus_81_works_backup_v6\data\colliders.ini

2) Open that car's data\car.ini in Notepad and change three lines:
     GRAPHICS_OFFSET=0.000,-0.414,-0.174          ->  GRAPHICS_OFFSET=0.000,-0.403,-0.174
     GRAPHICS_PITCH_ROTATION=-1.85                ->  GRAPHICS_PITCH_ROTATION=-1.80
     POSITION=0,-0.15,-1.85   (under [FUELTANK])  ->  POSITION=0.000,0.006,-1.625

3) Content Manager -> the car -> Pack data (data.acd is what AC loads), then restart the session.

What it does
 * body sits 11 mm higher and 0.05 deg flatter on its wheels: the v5/v6 springs settle differently from the 28 Sep fit
 * collider: 4 boxes hugging the shell (nose / front body / rear body / tail) instead of the stock mod's 3 thin slabs
   that sat ~7 cm off and stopped 0.2 m short of the nose and 0.5 m short of the tail
 * fuel tank: on the boot floor (~0.24 m behind the rear axle) instead of in the rear bumper
To undo: put the old lines back (shown on the left) - nothing else in the car changes.
