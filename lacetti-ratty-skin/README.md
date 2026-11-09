# Ratty Racing skin – wtcc_chevrolet_lacetti

Black/purple livery with the Ratty Racing logo, #101, driver Nicklearse101.
Installed as `content/cars/wtcc_chevrolet_lacetti/skins/ratty_racing_101`.

Rebuild:
    python make_skin.py ratty_racing_logo.jpg <out folder>
    python make_windows.py <out folder>

How it works: the 8 stock skins are compared – pixels that differ between them
are the paintable livery area; pixels that match (lights, grilles, interior) are
kept from skin 6. The brightest value per pixel gives baked shading.
The right side's strip (top of the texture) is stored upside down with the front still
at the left: shapes are mirrored vertically, writing is rotated 180 degrees (an earlier
version flipped it, which came out mirrored - found with the generator's 3D preview).
Output: 4096x2048 uncompressed DDS with mipmaps.
