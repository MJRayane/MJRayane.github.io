"""Vérifie que chaque ligne de sous-titre fait au plus 12 mots (tokens séparés par des espaces)."""
import ast, sys
tree = ast.parse(open("riemann.py").read())
bad = 0
for node in ast.walk(tree):
    if isinstance(node, ast.Call) and getattr(node.func, "attr", "") == "say":
        txt = node.args[0].value
        for l in txt.split("\n"):
            n = len(l.split())
            if n > 12:
                bad += 1
                print(f"ligne {node.lineno}: {n} mots : {l}")
print("OK" if not bad else f"{bad} ligne(s) trop longue(s)")
sys.exit(bool(bad))
