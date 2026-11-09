"""Generate with microsoft/TRELLIS.2 (single image).  usage: trellis2_gen.py <out_dir> <tag> <seed> <img> [res] [decim]"""
import os, shutil, sys, time
from PIL import Image
from gradio_client import Client, handle_file
from huggingface_hub import get_token

out, tag, seed, img = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
res = sys.argv[5] if len(sys.argv) > 5 else "1536"
decim = int(sys.argv[6]) if len(sys.argv) > 6 else 500000
os.makedirs(out, exist_ok=True)
im = Image.open(img).convert("RGB"); im.thumbnail((1536, 1536))
q = os.path.join(out, f"in_{tag}.png"); im.save(q)
t0 = time.time()
c = Client("microsoft/TRELLIS.2", token=get_token(), verbose=False)
c.predict(api_name="/start_session")
pre = c.predict(handle_file(q), api_name="/preprocess_image")
shutil.copy(pre, os.path.join(out, f"pre_{tag}.png"))
print("preprocessed", round(time.time() - t0), "s", flush=True)
c.predict(handle_file(pre), seed, res, 7.5, 0.7, 12, 5.0, 7.5, 0.5, 12, 3.0, 1.0, 0.0, 12, 3.0, api_name="/image_to_3d")
print("generated", round(time.time() - t0), "s", flush=True)
glb, dl = c.predict(decim, 2048, api_name="/extract_glb")
shutil.copy(dl or glb, os.path.join(out, f"trellis2_{tag}.glb"))
print("done", round(time.time() - t0), "s ->", os.path.join(out, f"trellis2_{tag}.glb"))
