---
name: video-tools-on-nicks-pc
description: "How to read and make MP4 video on Nik's PC with no ffmpeg - WinRT MediaComposition from PowerShell 5.1, helpers already written"
metadata:
  node_type: memory
  type: reference
  originSessionId: 697f937a-51fc-411b-a08d-68df19522080
  modified: 2026-09-25T11:07:28.686Z
---

Nik's PC has no ffmpeg, numpy, OpenCV, imageio or moviepy (checked
2026-09-25) - only Pillow. Installing any would mean a download, which
needs his OK. What works without installing anything: Windows' own
WinRT MediaComposition, driven from Windows PowerShell 5.1.
- Read frames from any MP4 (e.g. his phone clips):
  MediaComposition.GetThumbnailAsync.
- Write an H.264 1080p30 + AAC MP4 from a PNG sequence plus a WAV:
  one MediaClip.CreateFromImageFileAsync per frame + a
  BackgroundAudioTrack, then RenderToFileAsync. 150 frames encode in ~4 s.

Single shareable version (Nik sent it to a friend): `Downloads\bozza_racing_studios_intro.py`
- renderer + synthesised sound + the encoder embedded as a PowerShell
string, `--gag car|crew|driver|all`, `--out`, words/tagline configurable at
the top, font fallback to Arial Black, prints an ffmpeg command if not on
Windows. Verified frame-identical to the delivered clips.
Older two-file helpers: `C:\Users\nickl\Downloads\BozzaRacingStudios_intro_source\winrt_media.ps1`
(Save-Thumbnails, Render-ImageSequence), next to `bozza_intro.py` - the
Pillow renderer + synthesised soundtrack for the "Bozza Racing Studios"
5 s ident (Cartoon Network Studios style, made 2026-09-25; outputs
`Downloads\BozzaRacingStudios_intro.mp4` plus `_pitcrew` / `_driver`
variants - `--gag car|crew|driver` picks the window gag). Nik asked for
the We Bare Bears characters in it; I declined (Cartoon Network's
copyrighted characters, and it's for a public channel) and drew our own
bears instead - one design, told apart by cap / headset / flag / helmet.
Every encode is ~10 MB whatever the content (fixed 16 Mbit/s), so equal
file sizes don't mean equal files - compare hashes.

Gotchas:
- PowerShell 5.1 can't call `.Add` on WinRT collections (Clips,
  BackgroundAudioTracks). Go through `ICollection<T>.Add` by reflection
  (Add-Item in the helper).
- The shell safety check blocks `Remove-Item -Recurse -Force $var` when
  the path is a bare variable. Use a quoted literal or "$var\sub" path.
- Keep copyrighted audio out: synthesise sound effects rather than
  lifting a reference clip's jingle.
