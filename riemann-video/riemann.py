"""
« Pourquoi démontrer l'hypothèse de Riemann serait une dinguerie,
   même pour la vie de tous les jours ? »

Vidéo explicative en 8 scènes, Manim Community Edition (testé avec 0.19.1).
Aucune voix off : tout passe par des sous-titres français incrustés.

Rendu d'une scène (1080p, 30 i/s) :
    manim -qh --fps 30 riemann.py Scene1Atomes
Rendu complet + assemblage : voir build.sh

Palette (3 couleurs) : bleu (BLEU), or (OR), blanc cassé (TXT) sur fond sombre.
Les données numériques (|ζ|, zéros, formule explicite) viennent de
precompute.py -> data.npz, calculées avec mpmath.
"""
from __future__ import annotations

import json
import random
from pathlib import Path

import numpy as np
from manim import *
from scipy.special import expi

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from voix import voix  # voix off (Kokoro, hors ligne)

# --------------------------------------------------------------------------
# Style global
# --------------------------------------------------------------------------
HERE = Path(__file__).resolve().parent
DATA = np.load(HERE / "data.npz")

FOND = "#0E1117"   # fond sombre
BLEU = "#58C4DD"   # couleur 1
OR = "#F2C14E"     # couleur 2
TXT = "#ECECEC"    # couleur 3 (texte / neutre)
GRIS = "#7D838C"   # simple nuance de TXT pour les éléments secondaires
CARTE = "#152029"  # nuance très sombre de BLEU (fond des cartes)

FONT = "Inter"
config.background_color = FOND

MAX_MOTS = 12      # contrainte : 12 mots maximum par ligne de sous-titre


def primes_upto(n: int) -> list[int]:
    """Crible d'Ératosthène."""
    sieve = np.ones(n + 1, dtype=bool)
    sieve[:2] = False
    for i in range(2, int(n ** 0.5) + 1):
        if sieve[i]:
            sieve[i * i:: i] = False
    return [int(p) for p in np.nonzero(sieve)[0]]


def li(x):
    """Logarithme intégral li(x) = Ei(ln x)."""
    return expi(np.log(x))


def T(text, size=32, color=TXT, **kw):
    """Raccourci pour un texte dans la police de la vidéo."""
    return Text(text, font=FONT, font_size=size, color=color, **kw)


# --------------------------------------------------------------------------
# Sous-titres : un mixin partagé par toutes les scènes
# --------------------------------------------------------------------------
class SousTitres:
    """Gère les sous-titres incrustés.

    say(texte) remplace le sous-titre courant. Si le précédent n'a pas eu
    le temps d'être lu, on attend d'abord. Chaque sous-titre est journalisé
    (début, fin, texte) dans subs/<Scene>.json pour fabriquer le .srt.
    """

    def init_subs(self, chapitre: str | None = None):
        self._sub = None
        self._sub_start = 0.0
        self._sub_until = 0.0
        self._log: list[dict] = []
        if chapitre:
            head = T(chapitre, 24, GRIS)
            head = VGroup(BackgroundRectangle(head, color=FOND, fill_opacity=0.9, buff=0.1), head)
            head.to_corner(UL, buff=0.3)
            self.fix(head)
            self.play(FadeIn(head, shift=0.2 * RIGHT), run_time=0.8)
            self.header = head

    # Dans une ThreeDScene, les textes doivent rester collés à l'écran.
    def fix(self, *mobs):
        # z_index élevé : les textes passent toujours devant les objets 3D
        for m in mobs:
            m.set_z_index(100)
        if isinstance(self, ThreeDScene):
            self.add_fixed_in_frame_mobjects(*mobs)
            self.remove(*mobs)

    @staticmethod
    def temps_lecture(text: str) -> float:
        n = len(text.split())
        return max(2.2, 1.2 + 0.32 * n)

    @staticmethod
    def fabrique(text: str) -> VGroup:
        lignes = text.split("\n")
        for l in lignes:
            if len(l.split()) > MAX_MOTS:
                raise ValueError(f"Sous-titre trop long ({len(l.split())} mots) : {l}")
        rows = VGroup(*[T(l, 32, TXT) for l in lignes]).arrange(DOWN, buff=0.14)
        if rows.width > 13.2:
            rows.scale_to_fit_width(13.2)
        bg = BackgroundRectangle(rows, color=FOND, fill_opacity=0.82, buff=0.16)
        return VGroup(bg, rows).to_edge(DOWN, buff=0.28)

    def son(self, wav: str, decalage: float = 0.0):
        # Ajout direct au fichier de sortie : Scene.add_sound() ignore le son
        # si l'animation précédente sortait du cache de Manim.
        self.renderer.file_writer.add_sound(wav, self._now() + decalage)

    def _now(self) -> float:
        return self.renderer.time

    def attendre_lecture(self):
        reste = self._sub_until - self._now()
        if reste > 0.05:
            self.wait(reste)

    def say(self, text: str, extra: float = 0.0):
        self.attendre_lecture()
        new = self.fabrique(text)
        self.fix(new)
        if self._sub is not None:
            self.play(FadeOut(self._sub), run_time=0.25)
            self._log.append(dict(start=self._sub_start, end=self._now(), text=self._sub_text))
        self._sub_start = self._now()
        # voix off : la phrase démarre avec le sous-titre, qui reste affiché
        # au moins le temps de la dire (+ une petite respiration)
        wav, duree = voix(text)
        self.son(wav)
        self.play(FadeIn(new), run_time=0.3)
        self._sub, self._sub_text = new, text
        self._sub_until = self._sub_start + max(0.3 + self.temps_lecture(text), duree + 0.45) + extra

    def end_subs(self, fade_all: bool = True):
        """Fin de scène : laisse lire le dernier sous-titre, puis fondu."""
        self.attendre_lecture()
        if self._sub is not None:
            self._log.append(dict(start=self._sub_start, end=self._now() + 0.5,
                                  text=self._sub_text))
        if fade_all:
            self.play(*[FadeOut(m) for m in self.mobjects], run_time=1.0)
        self.wait(0.3)
        out = HERE / "subs"
        out.mkdir(exist_ok=True)
        (out / f"{type(self).__name__}.json").write_text(
            json.dumps(dict(duration=self._now(), subs=self._log),
                       ensure_ascii=False, indent=1))


# --------------------------------------------------------------------------
# Le paysage |ζ(s)| (scènes 4 et 8)
# --------------------------------------------------------------------------
SIG, T2, Z2 = DATA["sig"], DATA["t2"], DATA["zeta_abs2"]
TC, ZC = DATA["tc"], DATA["zc"]
ZEROS = DATA["zeros"]
H_MAX = 2.6
T_MAX = 36


def h_de(z):
    """Hauteur affichée : |ζ| écrêté en douceur (quasi linéaire près de 0,
    aplati au-delà de ~3 : le pôle en s = 1 et la région Re(s) < 0 sont infinis
    ou très hauts)."""
    return H_MAX * np.tanh(np.asarray(z) / H_MAX)


def paysage():
    axes = ThreeDAxes(
        x_range=[-1, 2, 0.5], y_range=[0, T_MAX, 6], z_range=[0, H_MAX, 1],
        x_length=6, y_length=14, z_length=2.2,
        axis_config=dict(color=GRIS, stroke_width=2, include_tip=False),
    )
    nj = len(T2) - 1
    # u = indice en σ (0..30), v = indice en t (0..nj) : la surface passe
    # exactement par les points de grille pré-calculés (dont les zéros).
    surf = Surface(
        lambda u, v: axes.c2p(SIG[int(round(u))], np.interp(v, np.arange(len(T2)), T2),
                              h_de(Z2[int(round(u)), int(round(v))])),
        u_range=[0, len(SIG) - 1], v_range=[0, nj], resolution=(len(SIG) - 1, nj),
        fill_opacity=0.95, stroke_width=0.25, stroke_color=FOND, checkerboard_colors=False,
    )
    surf.set_fill_by_value(axes=axes, axis=2, colorscale=[
        (ManimColor("#10232E"), 0.0), (ManimColor("#2D6F86"), 0.6), (ManimColor(BLEU), 1.5), (ManimColor(TXT), H_MAX)])
    # la droite critique Re(s) = 1/2, tracée SUR le relief (elle touche le sol à chaque zéro)
    critique = VMobject(stroke_color=OR, stroke_width=4).set_points_as_corners(
        [axes.c2p(0.5, t, h_de(z) + 0.03) for t, z in zip(TC, ZC)])
    # un repère doré au-dessus de chaque zéro
    reperes = VGroup()
    for g in ZEROS[ZEROS < T_MAX]:
        base, haut = axes.c2p(0.5, g, 0), axes.c2p(0.5, g, H_MAX + 0.9)
        reperes.add(VGroup(DashedLine(base, haut, color=OR, stroke_width=2.5, dash_length=0.08),
                           Dot(haut, radius=0.08, color=OR)))
    ticks = VGroup(*[T(s, 26, GRIS).rotate(PI / 2, axis=RIGHT).move_to(axes.c2p(x, -1.6, 0))
                     for x, s in ((0, "0"), (0.5, "1/2"), (1, "1"))])
    return axes, surf, critique, reperes, ticks


# ==========================================================================
# SCÈNE 1 — Les atomes des nombres
# ==========================================================================
class Scene1Atomes(SousTitres, ThreeDScene):
    def cube(self, pos, color=BLEU):
        c = Cube(side_length=0.56, fill_color=color, fill_opacity=0.9,
                 stroke_color=FOND, stroke_width=1.5)
        return c.move_to(pos)

    def construct(self):
        # --- Carte de titre -------------------------------------------------
        titre = VGroup(
            T("Pourquoi démontrer", 50),
            T("l'hypothèse de Riemann", 58, OR),
            T("serait une dinguerie…", 50),
            T("…même pour la vie de tous les jours ?", 38, BLEU),
        ).arrange(DOWN, buff=0.3)
        self.fix(titre)
        wav, duree = voix("Pourquoi démontrer l'hypothèse de Riemann serait une dinguerie, "
                          "même pour la vie de tous les jours ?")
        self.son(wav, 0.4)
        self.play(LaggedStart(*[FadeIn(l, shift=0.2 * UP) for l in titre], lag_ratio=0.35), run_time=3)
        self.wait(max(2.5, duree + 0.4 + 0.8 - 3))
        self.play(FadeOut(titre), run_time=1)

        self.init_subs("1 · Les atomes des nombres")
        self.set_camera_orientation(phi=68 * DEGREES, theta=-50 * DEGREES, zoom=1.35)

        self.say("Commençons simplement : de quoi sont faits les nombres ?")
        # --- 12 cubes rangés en bloc 3 x 2 x 2 -----------------------------
        d = 0.7
        cubes = {}
        for i in range(3):
            for j in range(2):
                for k in range(2):
                    cubes[i, j, k] = self.cube(np.array([(i - 1) * d, (j - 0.5) * d, (k - 0.5) * d]))
        bloc = VGroup(*cubes.values())
        eq = MathTex("12", font_size=72, color=TXT).to_edge(UP, buff=0.95)
        self.fix(eq)
        self.begin_ambient_camera_rotation(rate=0.06)
        self.play(LaggedStart(*[GrowFromCenter(c) for c in bloc], lag_ratio=0.08), FadeIn(eq), run_time=2.5)
        self.say("Voici 12 petits cubes : c'est le nombre 12.")

        # --- 1re coupure : 12 = 2 x 6 ---------------------------------------
        self.say("On peut le couper en 2 parts égales de 6.")
        haut = VGroup(*[c for (i, j, k), c in cubes.items() if k == 1])
        bas = VGroup(*[c for (i, j, k), c in cubes.items() if k == 0])
        eq2 = MathTex("12", "=", "2", r"\times", "6", font_size=72, color=TXT).to_edge(UP, buff=0.95)
        self.fix(eq2)
        self.play(FadeOut(eq), run_time=0.4)
        self.play(haut.animate.shift(0.4 * OUT), bas.animate.shift(0.4 * IN), FadeIn(eq2), run_time=2)

        # --- 2e coupure : 6 = 2 x 3 ------------------------------------------
        self.say("Chaque 6 se coupe encore : 2 parts de 3.")
        avant = VGroup(*[c for (i, j, k), c in cubes.items() if j == 1])
        arriere = VGroup(*[c for (i, j, k), c in cubes.items() if j == 0])
        eq3 = MathTex("12", "=", "2", r"\times", "2", r"\times", "3", font_size=72, color=TXT).to_edge(UP, buff=0.95)
        eq3[2].set_color(OR); eq3[4].set_color(OR); eq3[6].set_color(OR)
        self.fix(eq3)
        self.play(FadeOut(eq2), run_time=0.4)
        self.play(avant.animate.shift(0.4 * UP), arriere.animate.shift(0.4 * DOWN), FadeIn(eq3), run_time=2)

        self.say("Et 3 ? Impossible de le couper en parts égales.")
        self.play(*[c.animate.set_fill(OR) for c in bloc], run_time=1.5)
        self.say("2 et 3 sont des nombres premiers :\non ne peut les diviser que par 1 et eux-mêmes.")
        self.attendre_lecture()

        # --- Le cas de 7 -------------------------------------------------------
        self.stop_ambient_camera_rotation()
        self.play(FadeOut(bloc), FadeOut(eq3), run_time=1)
        self.move_camera(phi=60 * DEGREES, theta=-80 * DEGREES, zoom=1.35, run_time=1)
        sept = VGroup(*[self.cube(np.array([(i - 3) * d, 0, 0])) for i in range(7)])
        eq7 = MathTex("7", font_size=72, color=TXT).to_edge(UP, buff=0.95)
        self.fix(eq7)
        self.say("Essayons avec 7 cubes.")
        self.play(LaggedStart(*[GrowFromCenter(c) for c in sept], lag_ratio=0.1), FadeIn(eq7), run_time=1.5)

        self.say("En 2 rangées ? Il reste toujours un cube tout seul.")
        pos2 = [np.array([(i % 3 - 1) * d, (0.5 - i // 3) * d * 1.6, 0]) for i in range(6)] + [np.array([2.6, 0, 0])]
        self.play(*[c.animate.move_to(p) for c, p in zip(sept, pos2)], run_time=1.8)
        self.play(sept[6].animate.set_fill(OR), run_time=0.6)
        self.play(sept[6].animate.set_fill(BLEU), run_time=0.6)

        self.say("En 3 rangées ? Encore un cube de trop.")
        pos3 = [np.array([(i % 2 - 0.5) * d, (1 - i // 2) * d * 1.5, 0]) for i in range(6)] + [np.array([2.2, 0, 0])]
        self.play(*[c.animate.move_to(p) for c, p in zip(sept, pos3)], run_time=1.8)
        self.play(sept[6].animate.set_fill(OR), run_time=0.6)
        self.play(sept[6].animate.set_fill(BLEU), run_time=0.6)

        self.say("7 ne se casse pas : c'est un nombre premier.")
        self.play(*[c.animate.move_to(np.array([(i - 3) * d, 0, 0])).set_fill(OR) for i, c in enumerate(sept)],
                  run_time=1.8)

        # --- Les briques ---------------------------------------------------------
        self.play(FadeOut(sept), FadeOut(eq7), run_time=1)
        premiers = T("2   3   5   7   11   13   17   19   23   29   31   …", 44, OR).shift(1.9 * UP)
        self.fix(premiers)
        self.say("Les nombres premiers : 2, 3, 5, 7, 11, 13…\nIl y en a une infinité.")
        self.play(Write(premiers), run_time=2.5)

        exemples = VGroup(
            MathTex(r"30 = 2 \times 3 \times 5", font_size=56),
            MathTex(r"84 = 2 \times 2 \times 3 \times 7", font_size=56),
            MathTex(r"1001 = 7 \times 11 \times 13", font_size=56),
        ).arrange(DOWN, buff=0.4, aligned_edge=LEFT).shift(0.2 * DOWN)
        for e in exemples:
            e.set_color(TXT)
        self.fix(exemples)
        self.say("Tout entier à partir de 2 s'obtient en multipliant des premiers.")
        self.play(LaggedStart(*[FadeIn(e, shift=0.2 * UP) for e in exemples], lag_ratio=0.5), run_time=3)
        self.say("Et d'une seule façon : c'est comme une recette unique.")
        self.say("Les premiers sont les briques, les « atomes »,\nde tous les nombres.")
        self.play(Indicate(premiers, color=OR, scale_factor=1.08), run_time=1.5)
        self.end_subs()


# ==========================================================================
# SCÈNE 2 — Le chaos apparent
# ==========================================================================
class Scene2Chaos(SousTitres, Scene):
    def construct(self):
        self.init_subs("2 · Le chaos apparent")
        P = primes_upto(200)

        ligne = NumberLine(x_range=[0, 200, 10], length=13, color=GRIS, stroke_width=2,
                           include_numbers=False, tick_size=0.06).shift(1.9 * UP)
        nums = VGroup(*[T(str(v), 26, GRIS).next_to(ligne.n2p(v), DOWN, buff=0.45) for v in range(0, 201, 50)])
        self.say("Plaçons tous les nombres premiers jusqu'à 200\nsur une ligne.")
        self.play(Create(ligne), FadeIn(nums), run_time=1.5)
        marques = VGroup(*[Line(ligne.n2p(p) + 0.26 * DOWN, ligne.n2p(p) + 0.26 * UP,
                                color=OR, stroke_width=3) for p in P])
        self.play(LaggedStart(*[GrowFromCenter(m) for m in marques], lag_ratio=0.15), run_time=6)

        self.say("Au début, ils sont serrés. Plus loin, ils s'espacent.")
        self.say("Mais les écarts entre eux sautent dans tous les sens.")

        # --- Loupe sur 87..133 ------------------------------------------------------
        a, b = 87, 133
        zoom = NumberLine(x_range=[a, b, 1], length=13, color=GRIS, stroke_width=2,
                          tick_size=0.05).shift(1.0 * DOWN)
        cadre = Rectangle(width=ligne.n2p(b)[0] - ligne.n2p(a)[0], height=0.62,
                          stroke_color=BLEU, stroke_width=2).move_to((ligne.n2p(a) + ligne.n2p(b)) / 2)
        guides = VGroup(
            DashedLine(cadre.get_corner(DL), zoom.n2p(a), color=BLEU, stroke_width=1.5),
            DashedLine(cadre.get_corner(DR), zoom.n2p(b), color=BLEU, stroke_width=1.5),
        )
        self.play(Create(cadre), run_time=0.8)
        self.play(Create(guides), Create(zoom), run_time=1.5)
        Pz = [p for p in P if a <= p <= b]
        mz = VGroup(*[Line(zoom.n2p(p) + 0.25 * DOWN, zoom.n2p(p) + 0.25 * UP, color=OR, stroke_width=4) for p in Pz])
        # 103 et 109 (jumeaux de 101 et 107) sont décalés vers le bas pour rester lisibles
        lz = VGroup(*[T(str(p), 26, TXT).next_to(zoom.n2p(p), DOWN, buff=0.75 if p in (103, 109) else 0.35)
                      for p in Pz])
        self.say("Regardons de plus près, entre 87 et 133.")
        self.play(LaggedStart(*[GrowFromCenter(m) for m in mz], lag_ratio=0.2), FadeIn(lz), run_time=2.5)

        arcs, gaps = VGroup(), VGroup()
        for p, q in zip(Pz, Pz[1:]):
            arc = ArcBetweenPoints(zoom.n2p(p) + 0.3 * UP, zoom.n2p(q) + 0.3 * UP, angle=-PI / 2.2,
                                   color=BLEU, stroke_width=2.5)
            arcs.add(arc)
            gaps.add(T(str(q - p), 30, BLEU).next_to(arc, UP, buff=0.08))
        self.say("Les écarts : 8, 4, 2, 4, 2, 4… puis 14 !")
        self.play(LaggedStart(*[AnimationGroup(Create(c), FadeIn(g)) for c, g in zip(arcs, gaps)],
                              lag_ratio=0.4), run_time=4)
        i14 = [q - p for p, q in zip(Pz, Pz[1:])].index(14)
        self.say("Entre 113 et 127 : un grand trou, aucun premier.")
        self.play(arcs[i14].animate.set_color(OR).set_stroke(width=5), gaps[i14].animate.set_color(OR).scale(1.4),
                  run_time=1.2)
        i2 = 2  # 101 -> 103
        self.say("Juste avant, 101 et 103 se collent presque.")
        self.play(arcs[i2].animate.set_color(OR).set_stroke(width=5), gaps[i2].animate.set_color(OR).scale(1.4),
                  run_time=1.2)
        self.say("Aucune formule simple ne donne le premier suivant.")
        self.say("On ne sait pas prédire le prochain nombre premier.")
        self.say("Ils semblent tomber au hasard… Et pourtant !")
        self.end_subs()


# ==========================================================================
# SCÈNE 3 — L'escalier π(x) et la courbe li(x)
# ==========================================================================
def axes_2d(x_max, x_step, y_min, y_max, y_step, x_len=11, y_len=4.6, x_labels=None, y_labels=None, x_lab_y=None):
    ax = Axes(x_range=[0, x_max, x_step], y_range=[y_min, y_max, y_step], x_length=x_len, y_length=y_len,
              axis_config=dict(color=GRIS, stroke_width=2, include_tip=False, tick_size=0.05))
    labs = VGroup()
    for v, s in (x_labels or {}).items():
        labs.add(T(s, 20, GRIS).next_to(ax.c2p(v, y_min if x_lab_y is None else x_lab_y), DOWN, buff=0.15))
    for v, s in (y_labels or {}).items():
        labs.add(T(s, 20, GRIS).next_to(ax.c2p(0, v), LEFT, buff=0.15))
    return ax, labs


def escalier(ax, primes, x_max, color=OR, width=3):
    pts, c = [ax.c2p(0, 0)], 0
    for p in primes:
        if p > x_max:
            break
        pts += [ax.c2p(p, c), ax.c2p(p, c + 1)]
        c += 1
    pts.append(ax.c2p(x_max, c))
    return VMobject(stroke_color=color, stroke_width=width).set_points_as_corners(pts)


class Scene3Escalier(SousTitres, Scene):
    def construct(self):
        self.init_subs("3 · L'escalier des nombres premiers")
        P = primes_upto(10000)

        # --- Escalier jusqu'à 100 ----------------------------------------------
        ax, labs = axes_2d(100, 10, 0, 32, 5, x_labels={v: str(v) for v in range(0, 101, 20)},
                           y_labels={v: str(v) for v in range(0, 31, 10)})
        VGroup(ax, labs).scale(0.92).shift(0.35 * UP + 0.7 * LEFT)
        tit_y = T("nombre de premiers jusqu'à x", 22, GRIS).next_to(ax.c2p(0, 32), RIGHT, buff=0.2)
        tit_x = T("x", 24, GRIS).next_to(ax.c2p(100, 0), RIGHT, buff=0.15)
        self.say("Comptons les premiers jusqu'à x. On note ce nombre π(x).")
        self.play(Create(ax), FadeIn(labs), FadeIn(tit_y), FadeIn(tit_x), run_time=1.5)
        stair = escalier(ax, P, 100)
        self.say("Chaque nouveau premier ajoute une marche : c'est un escalier.")
        self.play(Create(stair), run_time=6, rate_func=linear)
        lab_pi = T("π(x)", 30, OR).next_to(ax.c2p(100, 25), UP + LEFT, buff=0.12)
        self.play(FadeIn(lab_pi))

        courbe = ax.plot(lambda x: li(x), x_range=[2, 100], color=BLEU, stroke_width=4)
        lab_li = T("li(x)", 30, BLEU).next_to(ax.c2p(80, li(80)), UP + LEFT, buff=0.15)
        self.say("Gauss avait deviné une courbe lisse qui le suit : li(x).")
        self.play(Create(courbe), FadeIn(lab_li), run_time=3)

        # zoom sur l'écart à x = 100
        p1, p2 = ax.c2p(100, 25), ax.c2p(100, li(100))
        brace = BraceBetweenPoints(p1, p2, direction=RIGHT, color=TXT)
        lab_e = T("écart ≈ 5", 26, TXT).next_to(brace, RIGHT, buff=0.1)
        self.say("Mais il reste un écart entre l'escalier et la courbe.")
        self.play(GrowFromCenter(brace), FadeIn(lab_e), run_time=1.5)
        self.say("Toute la question : jusqu'où cet écart peut-il grandir ?")
        grp1 = VGroup(ax, labs, tit_y, tit_x, stair, courbe, lab_pi, lab_li, brace, lab_e)

        # --- Vue de loin : jusqu'à 10 000 ------------------------------------------
        ax2, labs2 = axes_2d(10000, 1000, 0, 1300, 250,
                             x_labels={v: f"{v:,}".replace(",", " ") for v in range(0, 10001, 2500)},
                             y_labels={v: str(v) for v in range(0, 1251, 500)})
        VGroup(ax2, labs2).shift(0.35 * UP)
        stair2 = escalier(ax2, P, 10000, width=2.5)
        courbe2 = ax2.plot(lambda x: li(x), x_range=[2, 10000], color=BLEU, stroke_width=3)
        tit_y2 = tit_y.copy().next_to(ax2.c2p(0, 1300), RIGHT, buff=0.2)
        self.say("Prenons du recul : jusqu'à 10 000.")
        self.play(FadeOut(grp1, scale=0.6), run_time=1.2)
        self.play(Create(ax2), FadeIn(labs2), FadeIn(tit_y2), run_time=1.2)
        self.play(Create(stair2), Create(courbe2), run_time=4)
        self.say("De loin, l'escalier et la courbe se confondent presque.")
        grp2 = VGroup(ax2, labs2, stair2, courbe2, tit_y2)

        # --- L'écart lui-même ----------------------------------------------------------
        xs = np.arange(2, 10001)
        pi_x = np.searchsorted(np.array(P), xs, side="right")
        ecart = li(xs) - pi_x
        ax3, labs3 = axes_2d(10000, 1000, -110, 110, 50,
                             x_labels={v: f"{v:,}".replace(",", " ") for v in range(0, 10001, 2500)},
                             y_labels={-100: "-100", 100: "100"}, x_lab_y=0)
        VGroup(ax3, labs3).shift(0.35 * UP)
        haut = ax3.plot(lambda x: np.sqrt(x), x_range=[0, 10000], color=BLEU, stroke_width=0)
        bas = ax3.plot(lambda x: -np.sqrt(x), x_range=[0, 10000], color=BLEU, stroke_width=0)
        zone = VMobject(fill_color=BLEU, fill_opacity=0.14, stroke_width=0)
        zone.set_points_as_corners([*haut.get_anchors(), *bas.get_anchors()[::-1]])
        bord = VGroup(DashedVMobject(ax3.plot(lambda x: np.sqrt(x), x_range=[1, 10000]), num_dashes=50),
                      DashedVMobject(ax3.plot(lambda x: -np.sqrt(x), x_range=[1, 10000]), num_dashes=50)
                      ).set_color(BLEU).set_stroke(width=2)
        lab_zone = T("zone de taille √x", 24, BLEU).next_to(ax3.c2p(7600, 92), UP, buff=0.05)
        courbe_e = VMobject(stroke_color=OR, stroke_width=2.5).set_points_as_corners(
            [ax3.c2p(x, e) for x, e in zip(xs[::3], ecart[::3])])
        lab_ce = T("écart = li(x) − π(x)", 24, OR).next_to(ax3.c2p(5000, 25), UP, buff=0.3)
        self.say("Zoomons maintenant sur l'écart lui-même.")
        self.play(FadeOut(grp2), run_time=1)
        self.play(Create(ax3), FadeIn(labs3), run_time=1)
        self.play(Create(courbe_e), FadeIn(lab_ce), run_time=3)
        self.say("Il hésite et zigzague, mais reste dans une zone étroite.")
        self.play(FadeIn(zone), Create(bord), FadeIn(lab_zone), run_time=2)
        self.say("L'hypothèse de Riemann revient exactement à dire ceci :")
        self.say("l'écart ne grandit jamais beaucoup plus vite que √x.")
        self.say("Et on sait qu'il ne peut pas rester beaucoup plus petit.")
        self.say("Bref : les premiers seraient aussi réguliers que possible.")
        self.attendre_lecture()

        # --- Un chiffre concret -----------------------------------------------------------
        self.play(FadeOut(VGroup(ax3, labs3, zone, bord, lab_zone, courbe_e, lab_ce)), run_time=1)
        fait = VGroup(
            T("Jusqu'à 1 milliard :", 40, TXT),
            T("50 847 534 nombres premiers", 52, OR),
            T("li(x) se trompe d'environ 1 700 seulement", 36, BLEU),
        ).arrange(DOWN, buff=0.4).shift(0.5 * UP)
        self.say("Exemple : jusqu'à 1 milliard, il y a\n50 847 534 nombres premiers.")
        self.play(LaggedStart(*[FadeIn(f, shift=0.2 * UP) for f in fait], lag_ratio=0.5), run_time=2.5)
        self.say("La courbe li(x) ne se trompe que d'environ 1 700.")
        self.end_subs()


# ==========================================================================
# SCÈNE 4 — Le paysage de Riemann
# ==========================================================================
class Scene4Paysage(SousTitres, ThreeDScene):
    def construct(self):
        self.init_subs("4 · Le paysage de Riemann")

        # --- La fonction zêta ------------------------------------------------------
        self.say("1859 : Bernhard Riemann publie un court article.")
        an = T("1859", 96, OR).shift(0.6 * UP)
        nom = T("Bernhard Riemann", 40, TXT).next_to(an, DOWN, buff=0.3)
        self.fix(an, nom)
        self.play(FadeIn(an, shift=0.3 * UP), FadeIn(nom), run_time=1.5)
        self.say("Il y étudie une drôle de machine : la fonction zêta, ζ.")
        self.play(FadeOut(an), FadeOut(nom), run_time=0.8)
        f1 = MathTex(r"\zeta(s) = 1 + \frac{1}{2^s} + \frac{1}{3^s} + \frac{1}{4^s} + \cdots",
                     font_size=60, color=TXT).shift(1.3 * UP)
        f2 = MathTex(r"= \frac{1}{1-2^{-s}} \times \frac{1}{1-3^{-s}} \times \frac{1}{1-5^{-s}} \times \cdots",
                     font_size=56, color=OR).next_to(f1, DOWN, buff=0.5)
        c2 = T("(un facteur pour chaque nombre premier)", 26, GRIS).next_to(f2, DOWN, buff=0.3)
        self.fix(f1, f2, c2)
        self.play(Write(f1), run_time=2.5)
        self.say("Euler l'avait vu : on peut l'écrire avec tous les premiers.")
        self.play(Write(f2), FadeIn(c2), run_time=2.5)
        self.say("Riemann l'étend à tout le plan des nombres « complexes ».")
        self.play(FadeOut(VGroup(f1, f2, c2)), run_time=1)

        # --- Le paysage ---------------------------------------------------------------
        axes, surf, critique, reperes, ticks = paysage()
        self.set_camera_orientation(phi=62 * DEGREES, theta=-35 * DEGREES, zoom=0.6,
                                    frame_center=axes.c2p(0.5, 18, 2.2))
        plat = surf.copy().apply_function(lambda p: np.array([p[0], p[1], axes.c2p(0, 0, 0)[2]]))
        legende = T("Au sol : les nombres s   ·   En hauteur : la taille de ζ(s)", 26, TXT)
        legende = VGroup(BackgroundRectangle(legende, color=FOND, fill_opacity=0.9, buff=0.15), legende)
        legende.to_edge(UP, buff=0.85)
        self.fix(legende)
        self.say("Chaque point du sol est un nombre s.\nLa hauteur montre la taille de ζ(s).")
        self.play(Create(axes), FadeIn(ticks), FadeIn(legende), run_time=1.5)
        self.play(ReplacementTransform(plat, surf), run_time=4)
        self.begin_ambient_camera_rotation(rate=0.02)
        self.say("(Les sommets trop hauts sont aplatis, pour la lisibilité.)")
        self.say("Regardez ces creux, où le paysage touche le sol…")
        self.attendre_lecture()
        self.stop_ambient_camera_rotation()
        # vue de côté, rapprochée, sur les premiers creux
        self.move_camera(phi=64 * DEGREES, theta=-14 * DEGREES, zoom=0.78,
                         frame_center=axes.c2p(0.5, 13, 2.0), run_time=5)
        self.say("Là, ζ vaut exactement zéro.\nCe sont les « zéros » de ζ.")
        self.play(LaggedStart(*[Create(r) for r in reperes], lag_ratio=0.3), run_time=2.5)

        self.say("Survolons-les. Où sont-ils placés ?")
        # survol : la caméra glisse le long de la bande critique
        self.move_camera(phi=62 * DEGREES, theta=-8 * DEGREES, zoom=0.78,
                         frame_center=axes.c2p(0.5, 25, 2.0), run_time=8, rate_func=smooth)
        self.say("Tous exactement sur la même droite : Re(s) = 1/2.")
        leg2 = T("En doré : la droite Re(s) = 1/2", 28, OR)
        leg2 = VGroup(BackgroundRectangle(leg2, color=FOND, fill_opacity=0.9, buff=0.15), leg2).move_to(legende)
        self.fix(leg2)
        self.play(FadeOut(legende), run_time=0.4)
        self.play(Create(critique), FadeIn(leg2), run_time=3)
        self.attendre_lecture()
        self.move_camera(phi=62 * DEGREES, theta=-32 * DEGREES, zoom=0.5,
                         frame_center=axes.c2p(0.5, 18, 3.6), run_time=5)
        self.begin_ambient_camera_rotation(rate=0.012)
        enonce = VGroup(T("L'hypothèse de Riemann", 34, OR),
                        T("Tous les zéros « non triviaux » de ζ", 30, TXT),
                        T("sont sur la droite Re(s) = 1/2.", 30, TXT)).arrange(DOWN, buff=0.12)
        bg = BackgroundRectangle(enonce, color=FOND, fill_opacity=0.92, buff=0.2)
        carton = VGroup(bg, enonce).to_edge(UP, buff=0.75)
        self.fix(carton)
        self.say("L'hypothèse : TOUS les zéros « non triviaux »\nsont sur cette droite.")
        self.play(FadeOut(leg2), run_time=0.5)
        self.play(FadeIn(carton), run_time=1.2)
        self.say("(Il existe aussi des zéros « triviaux », faciles, ailleurs.)")
        self.say("On a vérifié plus de 10 000 milliards de zéros par ordinateur.")
        cpt = T("> 10 000 000 000 000 zéros vérifiés : tous sur la droite", 28, OR)
        cpt_bg = BackgroundRectangle(cpt, color=FOND, fill_opacity=0.92, buff=0.15)
        cpt_g = VGroup(cpt_bg, cpt).next_to(carton, DOWN, buff=0.2)
        self.fix(cpt_g)
        self.play(FadeIn(cpt_g), run_time=1)
        self.say("Tous sur la droite ! Mais il y en a une infinité.")
        self.say("Vérifier des milliards de cas, ce n'est pas démontrer.")
        self.end_subs()


# ==========================================================================
# SCÈNE 5 — La musique des nombres premiers
# ==========================================================================
X5 = DATA["x"]
SMOOTH = DATA["smooth"]
CONTRIB = DATA["contrib"]
CUM = np.vstack([np.zeros_like(X5), np.cumsum(CONTRIB, axis=0)])  # CUM[N] = somme des N premières ondes


class Scene5Musique(SousTitres, Scene):
    def construct(self):
        self.init_subs("5 · La musique des nombres premiers")
        self.say("Riemann découvre un lien stupéfiant entre ces zéros\net les premiers.")
        self.say("Chaque zéro produit une onde, comme une note de musique.")

        # --- trois ondes individuelles ------------------------------------------------
        ondes = VGroup()
        for k in range(3):
            ax = Axes(x_range=[0, 60, 10], y_range=[-0.6, 0.6, 0.6], x_length=9, y_length=1.15,
                      axis_config=dict(color=GRIS, stroke_width=1.5, include_tip=False, tick_size=0.03))
            y = CONTRIB[k] * (0.45 / np.abs(CONTRIB[k][X5 > 3]).max())  # amplitude normalisée pour l'affichage
            m = X5 > 2
            g = VMobject(stroke_color=BLEU, stroke_width=3).set_points_smoothly(
                [ax.c2p(x, v) for x, v in zip(X5[m][::3], y[m][::3])])
            lab = T(f"zéro n° {k + 1} : 1/2 + {ZEROS[k]:.2f} i".replace(".", ","), 22, OR)
            lab.next_to(ax, LEFT, buff=0.3)
            ondes.add(VGroup(ax, g, lab))
        ondes.arrange(DOWN, buff=0.35).shift(0.4 * UP)
        for o in ondes:
            self.play(Create(o[0]), FadeIn(o[2]), run_time=0.6)
            self.play(Create(o[1]), run_time=1.6)
        self.say("Plus le zéro est haut sur la droite,\nplus sa note est aiguë.")
        self.play(*[Indicate(o[1], color=OR, scale_factor=1.03) for o in ondes], run_time=1.5)
        self.say("Additionnons ces notes, et écoutons ce qu'elles jouent.")
        self.attendre_lecture()
        self.play(FadeOut(ondes), run_time=1)

        # --- reconstruction de π(x) ---------------------------------------------------
        ax, labs = axes_2d(60, 10, -2, 19, 5, x_len=11.5, y_len=4.8,
                           x_labels={v: str(v) for v in range(0, 61, 10)},
                           y_labels={v: str(v) for v in range(0, 16, 5)})
        VGroup(ax, labs).shift(0.25 * UP)
        P = primes_upto(60)
        vrai = escalier(ax, P, 60, color=GRIS, width=2)
        vrai.set_stroke(opacity=0.6)
        N = ValueTracker(0)

        def courbe():
            n = int(N.get_value())
            y = np.clip(SMOOTH + CUM[n], -1.9, 18.9)
            return VMobject(stroke_color=BLEU, stroke_width=3.5).set_points_as_corners(
                [ax.c2p(x, v) for x, v in zip(X5, y)])

        c = always_redraw(courbe)
        compteur_n = Integer(0, font_size=44, color=OR)
        compteur_t = T("ondes ajoutées :", 30, TXT)
        compteur = VGroup(compteur_t, compteur_n).arrange(RIGHT, buff=0.2).to_corner(UR, buff=0.5).shift(0.25 * DOWN + 0.4 * LEFT)
        compteur_n.add_updater(lambda m: m.set_value(int(N.get_value())))
        lab_v = T("en gris : le vrai escalier π(x)", 24, GRIS).next_to(ax.c2p(3, 17.5), RIGHT, buff=0)

        self.play(Create(ax), FadeIn(labs), run_time=1.2)
        self.say("En gris : le vrai escalier π(x) qu'on veut retrouver.")
        self.play(Create(vrai), FadeIn(lab_v), run_time=2)
        self.say("En bleu : la courbe lisse, sans aucune onde.")
        self.play(Create(c), FadeIn(compteur), run_time=2)

        self.say("Ajoutons 1 onde…")
        self.play(N.animate.set_value(1), run_time=1.5)
        self.say("Puis 5 ondes…")
        self.play(N.animate.set_value(5), run_time=3, rate_func=linear)
        self.say("Puis 20 ondes : les marches se dessinent.")
        self.play(N.animate.set_value(20), run_time=4, rate_func=linear)
        self.say("Et 100 ondes : l'escalier des premiers réapparaît !")
        self.play(N.animate.set_value(100), run_time=6, rate_func=linear)
        self.wait(1)
        marques = VGroup(*[Dot(ax.c2p(p, 0), radius=0.05, color=OR) for p in P])
        noms = VGroup(*[T(str(p), 16, OR).next_to(ax.c2p(p, 0), DOWN, buff=0.12) for p in P[:6]])
        self.say("Chaque marche tombe pile sur un nombre premier.")
        self.play(LaggedStart(*[GrowFromCenter(m) for m in marques], lag_ratio=0.1), FadeIn(noms), run_time=2.5)
        self.say("Les zéros sont la « partition » cachée des nombres premiers.")
        self.say("C'est pour ça que leur position compte autant.")

        # --- si un zéro quittait la droite (illustration) --------------------------------
        y_faux = np.clip(SMOOTH + CUM[100] + CONTRIB[0] * (X5 ** 0.3 - 1) * 2.0, -1.9, 18.9)
        faux = DashedVMobject(VMobject().set_points_as_corners([ax.c2p(x, v) for x, v in zip(X5, y_faux)]),
                              num_dashes=160).set_stroke(OR, width=2.5)
        lab_f = T("pointillés : un zéro hors de la droite (illustration)", 24, OR).next_to(lab_v, DOWN, aligned_edge=LEFT, buff=0.15)
        self.say("Si un seul zéro quittait la droite, sa note serait trop forte…")
        self.play(Create(faux), FadeIn(lab_f), run_time=3)
        self.say("…et l'escalier s'écarterait bien plus de la courbe lisse.")
        self.say("Sur la droite, toutes les notes restent les plus douces possibles.")
        self.end_subs()


# ==========================================================================
# SCÈNE 6 — La vie de tous les jours
# ==========================================================================
def icone_carte():
    corps = RoundedRectangle(width=2.4, height=1.5, corner_radius=0.15, stroke_color=BLEU, stroke_width=3,
                             fill_color=CARTE, fill_opacity=1)
    puce = RoundedRectangle(width=0.45, height=0.35, corner_radius=0.06, stroke_width=0, fill_color=OR,
                            fill_opacity=1).move_to(corps.get_corner(UL) + np.array([0.5, -0.5, 0]))
    num = VGroup(*[Line(ORIGIN, 0.38 * RIGHT, stroke_color=TXT, stroke_width=3) for _ in range(4)]).arrange(
        RIGHT, buff=0.12).move_to(corps.get_center() + 0.25 * DOWN)
    return VGroup(corps, puce, num)


def icone_tel():
    corps = RoundedRectangle(width=1.1, height=2.0, corner_radius=0.18, stroke_color=BLEU, stroke_width=3,
                             fill_color=CARTE, fill_opacity=1)
    b1 = RoundedRectangle(width=0.65, height=0.28, corner_radius=0.1, stroke_width=0, fill_color=BLEU,
                          fill_opacity=0.9).move_to(corps.get_center() + np.array([-0.12, 0.45, 0]))
    b2 = RoundedRectangle(width=0.6, height=0.28, corner_radius=0.1, stroke_width=0, fill_color=TXT,
                          fill_opacity=0.85).move_to(corps.get_center() + np.array([0.12, 0.0, 0]))
    b3 = RoundedRectangle(width=0.5, height=0.28, corner_radius=0.1, stroke_width=0, fill_color=BLEU,
                          fill_opacity=0.9).move_to(corps.get_center() + np.array([-0.17, -0.45, 0]))
    return VGroup(corps, b1, b2, b3)


def icone_cadenas(color=OR):
    corps = RoundedRectangle(width=1.1, height=0.85, corner_radius=0.1, stroke_width=0, fill_color=color,
                             fill_opacity=1)
    anse = Arc(radius=0.33, start_angle=0, angle=PI, stroke_color=color, stroke_width=10).next_to(corps, UP, buff=0)
    trou = Dot(corps.get_center(), radius=0.09, color=FOND)
    return VGroup(anse, corps, trou)


class Scene6Quotidien(SousTitres, Scene):
    def construct(self):
        self.init_subs("6 · Et dans la vie de tous les jours ?")
        carte = icone_carte()
        tel = icone_tel()
        sources = VGroup(carte, tel).arrange(DOWN, buff=0.4).scale(1.05).move_to(5.2 * LEFT + 0.2 * UP)
        cad = icone_cadenas().scale(1.3).move_to(1.4 * LEFT + 0.2 * UP)
        lab_cad = T("chiffrement", 26, OR).next_to(cad, DOWN, buff=0.2)
        f1 = Arrow(sources.get_right(), cad.get_left(), buff=0.3, color=GRIS, stroke_width=3)

        self.say("Un paiement par carte, un site web, un message WhatsApp…")
        self.play(FadeIn(carte, shift=0.3 * RIGHT), FadeIn(tel, shift=0.3 * RIGHT), run_time=1.5)
        self.say("Tout cela est protégé par du chiffrement.")
        self.play(GrowArrow(f1), FadeIn(cad, scale=0.6), FadeIn(lab_cad), run_time=1.5)
        self.say("Beaucoup de ces systèmes reposent sur de grands nombres premiers.")

        # un vrai nombre (probablement) premier de 309 chiffres, comme dans RSA-2048
        from sympy import nextprime
        rng = random.Random(1859)
        p = nextprime(rng.getrandbits(1024) | (1 << 1023))
        s = str(p)
        lignes = [s[i:i + 22] for i in range(0, 66, 22)]
        grand = VGroup(*[Text(l, font="JetBrains Mono", font_size=24, color=TXT) for l in lignes],
                       T(f"…  ({len(s)} chiffres)", 22, GRIS)).arrange(DOWN, buff=0.12, aligned_edge=LEFT)
        boite = SurroundingRectangle(grand, color=BLEU, buff=0.25, corner_radius=0.1)
        bloc_p = VGroup(boite, grand).scale(1.05).move_to(3.75 * RIGHT + 0.2 * UP)
        f2 = Arrow(cad.get_right(), bloc_p.get_left(), buff=0.3, color=GRIS, stroke_width=3)
        self.say("Exemple : une clé RSA cache deux premiers\nd'environ 300 chiffres chacun.")
        self.play(GrowArrow(f2), FadeIn(bloc_p), run_time=2)
        self.say("Pour en fabriquer, l'ordinateur tire un grand nombre au hasard…")
        self.play(Indicate(grand, color=BLEU, scale_factor=1.04), run_time=1.5)
        self.say("…puis il teste s'il est premier. C'est très rapide.")

        test = VGroup(*[T(f"témoin {a} ✓", 24, BLEU) for a in (2, 3, 5, 7)], T("…", 24, BLEU)).arrange(RIGHT, buff=0.4)
        test.scale(0.85).next_to(bloc_p, DOWN, buff=0.85, aligned_edge=RIGHT)
        self.say("Le test de Miller-Rabin répond « premier »\navec une chance d'erreur infime.")
        self.play(LaggedStart(*[FadeIn(t, shift=0.2 * UP) for t in test], lag_ratio=0.4), run_time=2.5)
        self.say("Ça fonctionne très bien, depuis des décennies. Aucun souci.")
        self.say("Mais la réponse est « très probable », pas « certaine ».")
        self.attendre_lecture()

        # --- très probable -> certain -----------------------------------------------
        self.play(FadeOut(VGroup(sources, cad, lab_cad, f1, f2, bloc_p, test)), run_time=1)
        avant = VGroup(T("Aujourd'hui", 28, GRIS), T("« très probablement premier »", 38, BLEU)).arrange(DOWN, buff=0.25)
        apres = VGroup(T("Si l'hypothèse de Riemann généralisée est vraie", 26, GRIS),
                       T("« premier : c'est garanti »", 38, OR)).arrange(DOWN, buff=0.25)
        VGroup(avant, apres).arrange(DOWN, buff=1.1).scale(1.2).shift(0.5 * UP)
        fl = Arrow(avant.get_bottom(), apres.get_top(), buff=0.15, color=TXT, stroke_width=3)
        self.say("Avec l'hypothèse de Riemann (version « généralisée »)…")
        self.play(FadeIn(avant, shift=0.2 * DOWN), run_time=1.2)
        self.say("…le test de Miller devient une preuve, rapide et garantie.")
        self.play(GrowArrow(fl), FadeIn(apres, shift=0.2 * DOWN), run_time=1.8)
        self.say("(D'autres tests certains existent, mais ils sont souvent plus lents.)")
        self.attendre_lecture()

        # --- mise au point honnête ----------------------------------------------------
        self.play(FadeOut(VGroup(avant, apres, fl)), run_time=1)
        cad2 = icone_cadenas().scale(1.4).shift(1.2 * UP)
        msg = VGroup(T("Une preuve ne casserait PAS le chiffrement.", 36, TXT),
                     T("Sa sécurité repose sur d'autres problèmes difficiles,", 28, GRIS),
                     T("comme décomposer un nombre géant en facteurs premiers.", 28, GRIS)
                     ).arrange(DOWN, buff=0.22).next_to(cad2, DOWN, buff=0.5)
        self.say("Attention, idée reçue : une preuve ne casserait PAS\nle chiffrement.")
        self.play(FadeIn(cad2, scale=0.7), FadeIn(msg[0]), run_time=1.5)
        self.say("Sa sécurité repose sur d'autres problèmes, comme factoriser.\nPas sur Riemann.")
        self.play(FadeIn(msg[1:]), run_time=1.2)
        self.say("Ce qui changerait : certaines garanties passeraient\nde « très probable » à « certain ».")
        self.play(Indicate(cad2, color=OR), run_time=1.5)
        self.end_subs()


# ==========================================================================
# SCÈNE 7 — L'effet domino
# ==========================================================================
class Flip(Animation):
    """Retourne une carte (face bleue « Si RH… » -> face dorée « VRAI ✓ »)
    autour de son axe vertical."""

    def __init__(self, card, **kw):
        self.front0 = card[0].copy()
        self.back0 = card.back.copy()
        self.etat = None
        super().__init__(card, **kw)

    def interpolate_mobject(self, alpha):
        a = self.rate_func(alpha)
        if a <= 0 and self.etat == "debut":
            return
        if a >= 1 and self.etat == "fin":
            return
        self.etat = "debut" if a <= 0 else ("fin" if a >= 1 else None)
        front, back = self.mobject[0], self.mobject[1]
        c = self.front0.get_center()
        front.become(self.front0)
        back.become(self.back0)
        if a < 0.5:
            front.rotate(a * PI, axis=OUT, about_point=c)
            back.set_opacity(0)
        else:
            front.set_opacity(0)
            back.rotate((a - 1) * PI, axis=OUT, about_point=c)


# Quatre vrais résultats conditionnels (RH = hypothèse de Riemann) :
#  - Miller (1976) / Bach (1990) : test de primalité déterministe, sous RH généralisée
#  - Schoenfeld (1976) : |π(x) - li(x)| < √x ln x / 8π pour x ≥ 2657
#  - Cramér (1920) : écart entre premiers consécutifs = O(√p ln p)
#  - Robin (1984) : σ(n) < e^γ n ln ln n pour n > 5040
EXEMPLES = [
    "Si RH (généralisée) :\ntest de Miller\ngaranti",
    "Si RH :\n|π(x) − li(x)|\n< √x · ln x / 8π",
    "Si RH :\nécart entre premiers\nvoisins ≲ √p · ln p",
    "Si RH :\nσ(n) < e^γ · n · ln ln n\n(n > 5040)",
]


class Scene7Dominos(SousTitres, ThreeDScene):
    W, H, DX, DZ = 1.3, 0.85, 1.45, 1.0
    COLS, ROWS = 30, 16

    def carte(self, x, z, texte=None, lignes=True, size=13, echelle=None):
        def face(color_stroke, color_fill, contenu):
            r = RoundedRectangle(width=self.W, height=self.H, corner_radius=0.06, stroke_color=color_stroke,
                                 stroke_width=1.6, fill_color=color_fill, fill_opacity=1)
            g = VGroup(r)
            if contenu is not None:
                g.add(contenu.move_to(r))
            return g

        if texte is not None:
            rows = VGroup(*[T(l, size, TXT) for l in texte.split("\n")]).arrange(DOWN, buff=0.04)
            rows.scale(echelle if echelle else min(1, self.W * 0.9 / rows.width))
            contenu = rows
        elif lignes:
            contenu = VGroup(Line(ORIGIN, 0.8 * RIGHT), Line(ORIGIN, 0.55 * RIGHT)).arrange(
                DOWN, buff=0.15, aligned_edge=LEFT).set_stroke(BLEU, 2.5, opacity=0.7)
        else:
            contenu = None
        front = face(BLEU, CARTE, contenu)
        back = face(OR, "#2A2414", T("VRAI ✓", 24 if texte else 22, OR, weight=BOLD))
        for f in (front, back):
            f.rotate(PI / 2, axis=RIGHT).move_to(np.array([x, 0, z]))
        card = VGroup(front, back.copy().set_opacity(0))
        card.back = back
        return card

    def construct(self):
        self.init_subs("7 · L'effet domino")
        self.set_camera_orientation(phi=90 * DEGREES, theta=-90 * DEGREES, zoom=2.5, frame_center=ORIGIN)

        # échelle commune pour que les 4 exemples aient la même taille de texte
        ex_rows = [VGroup(*[T(l, 12, TXT) for l in e.split("\n")]).arrange(DOWN, buff=0.04) for e in EXEMPLES]
        ech = min(1, min(self.W * 0.88 / r.width for r in ex_rows))
        cartes = []
        cx, cz = (self.COLS - 1) / 2, (self.ROWS - 1) / 2
        ex_pos = {(14, 7): 0, (15, 7): 1, (14, 8): 2, (15, 8): 3}
        for i in range(self.COLS):
            for k in range(self.ROWS):
                x, z = (i - cx) * self.DX, (cz - k) * self.DZ
                if (i, k) in ex_pos:
                    c = self.carte(x, z, EXEMPLES[ex_pos[i, k]], size=12, echelle=ech)
                elif abs(i - cx) < 5 and abs(k - cz) < 4:
                    c = self.carte(x, z, "Si Riemann\nest vrai, alors…", size=13)
                else:
                    c = self.carte(x, z)
                c.dist = np.hypot(x, z)
                cartes.append(c)
        centre = VGroup(*[c for c in cartes if c.dist < 1.0])
        self.say("Des mathématiciens ont écrit des milliers de résultats\nqui commencent ainsi :")
        self.play(FadeIn(centre), run_time=1.5)
        self.say("« Si l'hypothèse de Riemann est vraie, alors… »")
        self.say("Par exemple : un test de primalité garanti…")
        self.say("…une borne précise sur l'écart de l'escalier π(x)…")
        self.say("…des écarts entre premiers jamais trop grands…")
        self.say("…ou une inégalité sur les diviseurs des entiers.")
        self.play(FadeIn(VGroup(*[c for c in cartes if 1.0 <= c.dist < 9])), run_time=0.5)
        self.move_camera(zoom=0.95, run_time=4)
        self.add(*[c for c in cartes if c.dist >= 9])
        self.say("Tous ces résultats attendent, suspendus à une seule question.")
        self.move_camera(phi=74 * DEGREES, theta=-68 * DEGREES, zoom=0.42, run_time=5)
        self.say("Un mur entier de « si ».\nEt si quelqu'un démontrait Riemann ?")
        self.wait(0.5)
        ordre = sorted(cartes, key=lambda c: c.dist)
        self.begin_ambient_camera_rotation(rate=0.012)
        self.play(LaggedStart(*[Flip(c, run_time=1) for c in ordre], lag_ratio=0.012), run_time=9)
        self.say("Tous basculeraient d'un coup : « VRAI ».")
        self.say("Un seul théorème en débloquerait des milliers.")
        self.attendre_lecture()
        self.stop_ambient_camera_rotation()
        # le mur s'efface pour laisser place au point (4) : les outils
        self.play(*[c[1].animate.set_opacity(0.12) for c in cartes], run_time=2)
        fermat = VGroup(T("Le précédent de Fermat", 40, OR),
                        T("énoncé vers 1637  ·  démontré par Andrew Wiles en 1994", 30, TXT),
                        T("en chemin : des outils nouveaux pour toutes les mathématiques", 26, GRIS)
                        ).arrange(DOWN, buff=0.3)
        fermat = VGroup(BackgroundRectangle(fermat, color=FOND, fill_opacity=0.9, buff=0.35), fermat)
        self.fix(fermat)
        self.say("Et la méthode de preuve serait sans doute un trésor en soi.")
        self.say("Pour Fermat, la preuve de Wiles, en 1994,\na créé des outils tout neufs.")
        self.play(FadeIn(fermat, shift=0.2 * UP), run_time=1.5)
        self.say("Une preuve de Riemann ouvrirait sûrement des chemins inconnus.")
        self.end_subs()


# ==========================================================================
# SCÈNE 8 — Conclusion
# ==========================================================================
class Scene8Conclusion(SousTitres, ThreeDScene):
    def construct(self):
        axes, surf, critique, reperes, ticks = paysage()
        self.set_camera_orientation(phi=62 * DEGREES, theta=-38 * DEGREES, zoom=0.6,
                                    frame_center=axes.c2p(0.5, 18, 2.0))
        self.init_subs("8 · Conclusion")
        self.play(FadeIn(surf), FadeIn(axes), FadeIn(critique), FadeIn(reperes), FadeIn(ticks), run_time=2)
        self.begin_ambient_camera_rotation(rate=0.012)
        self.say("Résumons ce qu'apporterait une preuve.")
        self.say("1. Les premiers sont aussi réguliers que possible : c'est sûr.")
        self.say("2. Des milliers de théorèmes « si Riemann… » deviennent vrais.")
        self.say("3. Des algorithmes passent\nde « très probable » à « garanti ».")
        self.say("4. Et sans doute de nouveaux outils mathématiques.")

        l1 = T("1859  →  aujourd'hui : toujours ouvert", 44, TXT)
        l2 = T("1 000 000 $", 72, OR)
        l3 = T("Prix du millénaire · Institut Clay", 28, GRIS)
        carton = VGroup(l1, l2, l3).arrange(DOWN, buff=0.3)
        bg = BackgroundRectangle(carton, color=FOND, fill_opacity=0.92, buff=0.3)
        bloc = VGroup(bg, carton).to_edge(UP, buff=0.7)
        self.fix(bloc)
        self.say("Posée en 1859, l'hypothèse n'est toujours pas démontrée.")
        self.stop_ambient_camera_rotation()
        self.move_camera(zoom=0.5, frame_center=axes.c2p(0.5, 18, 3.8), run_time=2,
                         added_anims=[FadeIn(bg), FadeIn(l1, shift=0.2 * DOWN)])
        self.begin_ambient_camera_rotation(rate=0.012)
        self.say("L'Institut Clay offre 1 million de dollars\nà qui la démontrera.")
        self.play(FadeIn(l2, scale=1.3), FadeIn(l3), run_time=1.5)
        self.say("Une dinguerie ? Oui : percer l'ordre caché des nombres premiers.")
        self.say("La partition est là, sous nos yeux. Reste à la comprendre.")
        self.attendre_lecture()
        self.stop_ambient_camera_rotation()
        self.end_subs(fade_all=True)
