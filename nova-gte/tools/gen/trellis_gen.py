"""Generate a Nova GTE mesh with TRELLIS (trellis-community/TRELLIS Space) from reference photos.
usage: trellis_gen.py <out_dir> <tag> <seed> <img> [<img> ...]   (1 image = single mode, more = multi-image)"""
import os, shutil, sys, time
from PIL import Image
from gradio_client import Client, handle_file
from huggingface_hub import get_token

out, tag, seed, imgs = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4:]
os.makedirs(out, exist_ok=True)
small = []
for i, p in enumerate(imgs):                      # ~1280 px is plenty; keeps uploads small
    im = Image.open(p).convert("RGB"); im.thumbnail((1280, 1280))
    q = os.path.join(out, f"in_{tag}_{i}.png"); im.save(q); small.append(q)

t0 = time.time()
c = Client("trellis-community/TRELLIS", token=get_token(), verbose=False)
c.predict(api_name="/start_session")
if len(small) == 1:
    c.predict(api_name="/lambda")                 # single-image tab
    pre = c.predict(handle_file(small[0]), api_name="/preprocess_image")
    image, multi = handle_file(pre), []
else:
    c.predict(api_name="/lambda_1")               # multi-image tab
    gal = c.predict([{"image": handle_file(p), "caption": None} for p in small], api_name="/preprocess_images")
    multi = [{"image": handle_file(g["image"]), "caption": None} for g in gal]
    image = handle_file(gal[0]["image"])
    for k, g in enumerate(gal):
        shutil.copy(g["image"], os.path.join(out, f"pre_{tag}_{k}.png"))
print("preprocessed", round(time.time() - t0), "s", flush=True)
res = c.predict(image, multi, seed, 7.5, 12, 3.0, 12, "stochastic", 0.90, 2048, api_name="/generate_and_extract_glb")
vid, glb, dl = res
shutil.copy(dl or glb, os.path.join(out, f"trellis_{tag}.glb"))
if vid and vid.get("video"):
    shutil.copy(vid["video"], os.path.join(out, f"trellis_{tag}.mp4"))
print("done", round(time.time() - t0), "s ->", os.path.join(out, f"trellis_{tag}.glb"))
