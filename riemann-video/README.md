# Pourquoi démontrer l'hypothèse de Riemann serait une dinguerie… même pour la vie de tous les jours ?

Vidéo explicative (≈ 10 min, 1080p, 30 i/s, MP4, sous-titres français incrustés, sans voix off)
réalisée avec **Manim Community Edition 0.19.1**.

| Fichier | Rôle |
|---|---|
| `riemann.mp4` | la vidéo finale |
| `riemann.py` | code source commenté des 8 scènes |
| `precompute.py` | calculs mathématiques (mpmath) → `data.npz` |
| `sous-titres.txt` | tous les sous-titres, scène par scène |
| `riemann.srt` | les mêmes sous-titres, synchronisés (fichier séparé, optionnel) |
| `build.sh` | rendu des 8 scènes puis assemblage avec ffmpeg |
| `make_subs.py`, `lint_subs.py` | export des sous-titres / vérification « 12 mots max par ligne » |

## Les 8 scènes
1. **Les atomes des nombres** : 12 cubes qui se cassent en 2 × 2 × 3 ; 7 qui ne se casse pas.
2. **Le chaos apparent** : les premiers jusqu'à 200, loupe sur les écarts (8, 4, 2, 4, 2, 4, 14, 4).
3. **L'escalier** : π(x) en escalier, la courbe li(x), puis l'écart li(x) − π(x) jusqu'à 10 000.
4. **Le paysage de Riemann** : la surface |ζ(s)| (vraies valeurs, mpmath) ; chaque zéro est un nœud
   exact du maillage, la droite Re(s) = 1/2 est tracée en or sur le relief.
5. **La musique des premiers** : vraie formule explicite de Riemann, π(x) reconstruit avec 1, 5, 20, 100 paires de zéros.
6. **La vie de tous les jours** : chiffrement → grands premiers (vrai premier de 309 chiffres) → test de Miller-Rabin ;
   « très probable » → « garanti » sous l'hypothèse de Riemann généralisée. Rappel explicite :
   une preuve ne casserait **pas** le chiffrement.
7. **L'effet domino** : un mur de 480 cartes « Si Riemann est vrai, alors… » qui basculent en « VRAI ».
8. **Conclusion** : 1859 → aujourd'hui, toujours ouvert ; prix d'1 000 000 $ de l'Institut Clay.

## Refaire la vidéo
```bash
pip install manim==0.19.1 mpmath sympy scipy   # + ffmpeg et LaTeX (texlive)
./build.sh
```

## Points d'exactitude (sources classiques)
- Hypothèse ⇔ |π(x) − li(x)| = O(√x · ln x) (von Koch, 1901) ; borne explicite √x ln x / 8π pour x ≥ 2657 (Schoenfeld, 1976).
- Plus de 10¹³ zéros vérifiés sur la droite critique (Gourdon 2004 ; Platt & Trudgian 2021).
- Test de Miller déterministe sous l'hypothèse de Riemann **généralisée** (Miller 1976, Bach 1990).
  Des tests certains sans hypothèse existent (AKS 2002, ECPP) mais sont plus lents en pratique.
- Écarts entre premiers O(√p ln p) sous RH (Cramér 1920) ; critère de Robin (1984).
- La sécurité de RSA repose sur la difficulté de factoriser : une preuve de RH ne la remettrait pas en cause.
