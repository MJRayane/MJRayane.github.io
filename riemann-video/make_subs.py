"""Assemble les journaux de sous-titres (subs/<Scene>.json, écrits pendant le rendu)
en deux fichiers :
  - sous-titres.txt : tous les sous-titres, scène par scène
  - riemann.srt     : sous-titres synchronisés avec riemann.mp4
"""
import json, subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCENES = [("Scene1Atomes", "1 · Les atomes des nombres"), ("Scene2Chaos", "2 · Le chaos apparent"),
          ("Scene3Escalier", "3 · L'escalier des nombres premiers"), ("Scene4Paysage", "4 · Le paysage de Riemann"),
          ("Scene5Musique", "5 · La musique des nombres premiers"),
          ("Scene6Quotidien", "6 · Et dans la vie de tous les jours ?"),
          ("Scene7Dominos", "7 · L'effet domino"), ("Scene8Conclusion", "8 · Conclusion")]
VID = HERE / "media/videos/riemann/1080p30"


def duree(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True).stdout
    return float(out)


def ts(t):
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


txt = ["« Pourquoi démontrer l'hypothèse de Riemann serait une dinguerie,",
       "   même pour la vie de tous les jours ? »", "", "Sous-titres complets (dans l'ordre d'apparition)", ""]
srt, n, offset = [], 1, 0.0
for scene, titre in SCENES:
    log = json.loads((HERE / "subs" / f"{scene}.json").read_text())
    f = VID / f"{scene}.mp4"
    d = duree(f) if f.exists() else log["duration"]
    txt += ["=" * 60, titre, "=" * 60]
    for s in log["subs"]:
        txt.append(s["text"].replace("\n", " / "))
        srt += [str(n), f"{ts(offset + s['start'])} --> {ts(offset + s['end'])}", s["text"], ""]
        n += 1
    txt.append("")
    offset += d
(HERE / "sous-titres.txt").write_text("\n".join(txt), encoding="utf-8")
(HERE / "riemann.srt").write_text("\n".join(srt), encoding="utf-8")
print(f"{n - 1} sous-titres, durée totale {offset / 60:.1f} min")
