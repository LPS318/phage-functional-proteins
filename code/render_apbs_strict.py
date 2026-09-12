#!/usr/bin/env python3
"""
D4 finish: render strict APBS electrostatic surface (local PyMOL).
Read .pqr + .dx from the cloud node, map APBS potential onto the
molecular surface, output a publication-grade figure.
Red = negative, blue = positive (replaces the approximate figure).

Usage:
  conda activate pymol
  python render_apbs_strict.py --pqr /path/d4strict --dx /path/d4strict/apbs_out \
                               --out /path/work/figs/apbs_strict \
                               --ids KLEO13gp10,KP24gp300,FKANgp232,184_43,S2-2
"""
import argparse, glob, os, sys

def load_pymol_modules():
    sys.path.insert(0, "/Users/zhangwei/miniconda3/envs/pymol/lib/python3.12/site-packages")
    import pymol
    from pymol import cmd
    return cmd

def render_one(cmd, pqr, dx, outpng, name, lo, hi):
    cmd.reinitialize()
    cmd.bg_color("white")
    cmd.load(pqr, name)
    try:
        cmd.load(dx, "pot_" + name)
    except Exception:
        print("[warn] load dx fail: " + dx)
    cmd.hide("everything", name)
    cmd.show("surface", name)
    cmd.set("surface_quality", 1, name)
    cmd.set("transparency", 0.0, name)
    cmd.set("ambient", 0.3)
    cmd.set("specular", 0.5)
    try:
        cmd.ramp_new("pot_ramp_" + name, "pot_" + name, [lo, 0.0, hi], ["red", "white", "blue"])
        cmd.set("surface_color", "pot_ramp_" + name, name)
    except Exception as e:
        print("[warn] ramp fail, default color: %s" % e)
    cmd.orient(name)
    cmd.zoom(name, 1.6)
    cmd.ray(1600, 1100, antialias=1)
    cmd.png(outpng, dpi=300)
    print("saved " + outpng)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pqr", required=True, help="dir with *.pqr")
    ap.add_argument("--dx", required=True, help="dir with *.dx")
    ap.add_argument("--out", default="/Users/zhangwei/Documents/Codex/2026-08-30/ni-h/work/figs/apbs_strict")
    ap.add_argument("--ids", default="KLEO13gp10,KP24gp300,FKANgp232,184_43,S2-2")
    ap.add_argument("--all", action="store_true", help="render all dx")
    ap.add_argument("--lo", type=float, default=-10.0, help="ramp low (kT/e)")
    ap.add_argument("--hi", type=float, default=10.0, help="ramp high (kT/e)")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    cmd = load_pymol_modules()
    ids = [i.strip() for i in a.ids.split(",") if i.strip()]
    if a.all:
        ids = sorted(os.path.splitext(os.path.basename(p))[0] for p in glob.glob(os.path.join(a.dx, "*.dx")))
    for i in ids:
        pqr = os.path.join(a.pqr, i + ".pqr")
        dx = os.path.join(a.dx, i + ".dx")
        if not os.path.exists(pqr) or not os.path.exists(dx):
            print("[skip] missing %s: pqr=%s dx=%s" % (i, os.path.exists(pqr), os.path.exists(dx)))
            continue
        render_one(cmd, pqr, dx, os.path.join(a.out, i + "_apbs.png"), i, a.lo, a.hi)
    print("done -> " + a.out)

if __name__ == "__main__":
    main()
