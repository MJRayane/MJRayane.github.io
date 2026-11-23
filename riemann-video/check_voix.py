"""Vérifie que chaque sous-titre de chaque scène est bien accompagné de voix
(énergie audio > seuil dans les 0,1 à 0,8 s qui suivent son apparition)."""
import json, subprocess, sys
import numpy as np
from pathlib import Path

HERE = Path(__file__).resolve().parent
VID = HERE / "media/videos/riemann/1080p30"
ok = True
for scene in sys.argv[1:]:
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(VID / f"{scene}.mp4"), "-vn", "-ac", "1",
                          "-ar", "8000", "-f", "s16le", "-"], capture_output=True).stdout
    a = np.frombuffer(raw, "<i2") / 32768
    subs = json.loads((HERE / "subs" / f"{scene}.json").read_text())["subs"]
    muets = [s["text"][:40] for s in subs
             if np.sqrt((a[int((s["start"] + .1) * 8000):int((s["start"] + .8) * 8000)] ** 2).mean()) < 0.01]
    print(f"{scene}: {len(subs) - len(muets)}/{len(subs)} sous-titres avec voix", muets or "")
    ok &= not muets
sys.exit(0 if ok else 1)
