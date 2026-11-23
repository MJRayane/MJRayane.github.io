"""
Pré-calcul des données mathématiques utilisées par les scènes Manim.
Tout est calculé une seule fois (mpmath, haute précision) et stocké dans data.npz.

  - zeta_abs   : |ζ(σ + i t)| sur une grille du plan complexe (scènes 4 et 8)
  - zeros      : parties imaginaires des 100 premiers zéros non triviaux
  - explicit_* : formule explicite de Riemann, pour reconstruire π(x)
                 avec 1, 2, ..., 100 paires de zéros (scène 5)
"""
import numpy as np
import mpmath as mp

mp.mp.dps = 20

# ---------------------------------------------------------------- 1. |ζ(s)|
SIG = np.round(np.arange(-1.0, 2.0001, 0.1), 3)      # partie réelle σ (contient 0.5)
T = np.round(np.arange(0.0, 36.0001, 0.2), 3)          # partie imaginaire t
Z = np.zeros((len(SIG), len(T)))
for i, s in enumerate(SIG):
    for j, t in enumerate(T):
        if abs(s - 1) < 1e-9 and t == 0:
            Z[i, j] = 1e6                               # pôle en s = 1
        else:
            Z[i, j] = float(abs(mp.zeta(mp.mpc(s, t))))

# ---------------------------------------------------------------- 2. zéros
N_ZEROS = 100
zeros = np.array([float(mp.zetazero(k).imag) for k in range(1, N_ZEROS + 1)])

# ---------------------------------------------------------------- 3. formule explicite
# Riemann : J(y) = li(y) - Σ_ρ li(y^ρ) - ln 2 + ∫_y^∞ dt / (t (t²-1) ln t)
# puis π(x) = Σ_n μ(n)/n · J(x^(1/n)).
# On sépare la partie "lisse" (sans zéros) et la contribution de chaque paire de zéros,
# pour pouvoir les additionner une par une dans l'animation.
MU = {1: 1, 2: -1, 3: -1, 4: 0, 5: -1, 6: 1, 7: -1}
X = np.linspace(1.5, 60.0, 900)

def tail_integral(y):
    return float(mp.quad(lambda t: 1 / (t * (t * t - 1) * mp.log(t)), [y, mp.inf]))

smooth = np.zeros_like(X)
contrib = np.zeros((N_ZEROS, len(X)))
rhos = [mp.mpc(0.5, g) for g in zeros]
for ix, x in enumerate(X):
    for n, mu in MU.items():
        if mu == 0:
            continue
        y = mp.mpf(x) ** (mp.mpf(1) / n)
        if y <= 2:            # J(y) = 0 pour y < 2 (aucune puissance de premier)
            continue
        ly = mp.log(y)
        smooth[ix] += mu / n * float(mp.li(y) - mp.log(2) + tail_integral(y))
        for k, r in enumerate(rhos):
            # ρ et son conjugué : li(y^ρ) + li(y^ρ̄) = 2 Re Ei(ρ ln y)
            contrib[k, ix] += mu / n * float(-2 * mp.re(mp.ei(r * ly)))

# ---------------------------------------------------------------- 4. grille du paysage
# Pas de 0,4 en t, mais le nœud le plus proche de chaque zéro est déplacé
# EXACTEMENT sur le zéro : la surface touche alors vraiment le sol.
T2 = np.arange(0.0, 36.0001, 0.4)
for g in zeros[zeros < 36]:
    T2[np.argmin(abs(T2 - g))] = g
Z2 = np.zeros((len(SIG), len(T2)))
for i, s in enumerate(SIG):
    for j, t in enumerate(T2):
        Z2[i, j] = 1e6 if (abs(s - 1) < 1e-9 and t == 0) else float(abs(mp.zeta(mp.mpc(s, t))))
# |ζ(1/2 + i t)| finement, pour tracer la droite critique sur le relief
TC = np.arange(0.0, 36.0001, 0.05)
ZC = np.array([float(abs(mp.zeta(mp.mpc(0.5, t)))) for t in TC])

np.savez("data.npz", sig=SIG, t=T, zeta_abs=Z, zeros=zeros, x=X,
         smooth=smooth, contrib=contrib, t2=T2, zeta_abs2=Z2, tc=TC, zc=ZC)
print("zéros :", zeros[:5], "...")
print("π(59.5) reconstruit avec 100 zéros :", smooth[-10] + contrib[:, -10].sum())
