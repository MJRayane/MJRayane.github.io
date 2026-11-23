"""
Voix off française, synthétisée hors ligne avec Kokoro (voix « ff_siwis »).

  - oral(texte)  : transforme le texte affiché (sous-titre) en texte « à prononcer »
                   (symboles, grands nombres, noms propres...)
  - voix(texte)  : renvoie (chemin du .wav, durée en s), avec un cache dans voix/

Les fichiers du modèle (≈ 350 Mo) ne sont pas versionnés : build.sh les
télécharge dans modeles/ depuis les releases GitHub de kokoro-onnx.
Voix : corpus SIWIS (Université d'Édimbourg), licence CC-BY 4.0.
"""
from __future__ import annotations

import hashlib
import re
import wave
from pathlib import Path

from num2words import num2words

HERE = Path(__file__).resolve().parent
MODELES = HERE / "modeles"
CACHE = HERE / "voix"
VOIX, VITESSE = "ff_siwis", 0.95

# Remplacements appliqués AVANT la conversion des nombres (ordre important).
REMPLACEMENTS = [
    ("Re(s) = 1/2", "partie réelle de s égale un demi"),
    ("π(x)", "pi de x"), ("li(x)", "li de x"), ("ζ(s)", "zêta de s"), ("ζ", "zêta"),
    ("√x", "racine de x"), ("1/2", "un demi"),
    ("…", ", "), ("«", ""), ("»", ""), ("(", ""), (")", ""),
    ("RSA", "R.S.A."), ("WhatsApp", "ouatsape"), ("site web", "site ouèbe"),
    ("Miller-Rabin", "Milère-Rabine"), ("Miller", "Milère"), ("algorithmes", "algoritmes"),
    ("Bernhard", "Bernard"), ("Euler", "Eulère"), ("Wiles", "Ouaïlze"), ("Clay", "Clé"),
    ("TOUS", "tous"), ("PAS", "pas"), ("1 million", "un million"), ("1 onde", "une onde"),
]
# Ajustements phonétiques mot à mot, appliqués APRÈS (sur le texte en minuscules ou non)
APRES = [
    (r"\bGauss\b", "Gausse"),
]


def _nombres(txt: str) -> str:
    # "50 847 534" ou "10 000" (espaces de milliers) -> un seul nombre
    txt = re.sub(r"\d{1,3}(?: \d{3})+", lambda m: m.group(0).replace(" ", ""), txt)
    # "1." en début de phrase (énumération) -> "Un."
    txt = re.sub(r"^(\d)\. ", lambda m: num2words(int(m.group(1)), lang="fr").capitalize() + ". ", txt)
    return re.sub(r"\d+", lambda m: num2words(int(m.group(0)), lang="fr"), txt)


def oral(texte: str) -> str:
    t = texte.replace("\n", " ")
    for a, b in REMPLACEMENTS:
        t = t.replace(a, b)
    t = _nombres(t)
    for a, b in APRES:
        t = re.sub(a, b, t)
    t = re.sub(r"\s+", " ", t).strip()
    t = re.sub(r"\s+([,.?!:;])", r"\1", t)
    t = re.sub(r",\s*,", ",", t)
    t = t.lstrip(",;: ")
    return t[:1].upper() + t[1:]


_kokoro = None


def _moteur():
    global _kokoro
    if _kokoro is None:
        from kokoro_onnx import Kokoro
        _kokoro = Kokoro(str(MODELES / "kokoro-v1.0.onnx"), str(MODELES / "voices-v1.0.bin"))
    return _kokoro


def voix(texte: str) -> tuple[str, float]:
    """Synthétise (ou relit en cache) la phrase ; renvoie (chemin wav, durée)."""
    o = oral(texte)
    CACHE.mkdir(exist_ok=True)
    f = CACHE / (hashlib.sha1(f"{VOIX}|{VITESSE}|{o}".encode()).hexdigest()[:16] + ".wav")
    if not f.exists():
        import numpy as np
        samples, sr = _moteur().create(o, voice=VOIX, speed=VITESSE, lang="fr-fr")
        pcm = (np.clip(samples, -1, 1) * 32767).astype("<i2")
        with wave.open(str(f), "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
            w.writeframes(pcm.tobytes())
    with wave.open(str(f)) as w:
        return str(f), w.getnframes() / w.getframerate()
