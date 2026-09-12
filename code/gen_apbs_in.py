#!/usr/bin/env python3
"""
Generate a correctly-enclosing APBS input (.in) for a PQR file.
These proteins are elongated beta-helices (long axis 160-260 A), so a fixed
161^3 @ 0.5 A grid (80 A box) truncates them. This script sizes the fine grid
to enclose the molecule with margin, per-axis, and centers it on the bbox center.

Usage: python3 gen_apbs_in.py <file.pqr> <in_path> <dx_prefix> [spacing]
"""
import sys, math

def main():
    pqr, in_path, dx_prefix = sys.argv[1], sys.argv[2], sys.argv[3]
    spacing = float(sys.argv[4]) if len(sys.argv) > 4 else 1.5
    margin = 20.0
    pts = []
    for line in open(pqr):
        if line.startswith(('ATOM', 'HETATM')):
            parts = line.split()
            try:
                pts.append((float(parts[6]), float(parts[7]), float(parts[8])))
            except (ValueError, IndexError):
                continue
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]; zs = [p[2] for p in pts]
    minx, maxx = min(xs), max(xs); miny, maxy = min(ys), max(ys); minz, maxz = min(zs), max(zs)
    cx, cy, cz = (minx + maxx) / 2, (miny + maxy) / 2, (minz + maxz) / 2
    sx = maxx - minx; sy = maxy - miny; sz = maxz - minz
    fx = sx + 2 * margin; fy = sy + 2 * margin; fz = sz + 2 * margin
    nx = int(math.ceil(fx / spacing)); ny = int(math.ceil(fy / spacing)); nz = int(math.ceil(fz / spacing))
    # coarsen to sizeable, moderate grids (cap ~220 per axis to bound memory)
    cap = 220
    if max(nx, ny, nz) > cap:
        spacing = max(fx, fy, fz) / cap
        nx = int(math.ceil(fx / spacing)); ny = int(math.ceil(fy / spacing)); nz = int(math.ceil(fz / spacing))
    # make fglen exactly dime*spacing so APBS mg-manual is self-consistent
    fx = nx * spacing; fy = ny * spacing; fz = nz * spacing
    cglen = [1.6 * v for v in (fx, fy, fz)]
    content = f"""read
 mol pqr {pqr}
end
elec name mol
 mg-manual
 dime {nx} {ny} {nz}
 grid {spacing:.3f} {spacing:.3f} {spacing:.3f}
 cgcent {cx:.3f} {cy:.3f} {cz:.3f}
 fgcent {cx:.3f} {cy:.3f} {cz:.3f}
 cglen {cglen[0]:.2f} {cglen[1]:.2f} {cglen[2]:.2f}
 fglen {fx:.2f} {fy:.2f} {fz:.2f}
 mol 1
 lpbe
 bcfl sdh
 srfm smol
 chgm spl2
 sdens 10.0
 srad 1.4
 swin 0.3
 temp 298.15
 pdie 2.0
 sdie 78.5
 ion charge 1 conc 0.150 radius 2.0
 ion charge -1 conc 0.150 radius 2.0
 write pot dx {dx_prefix}
end
quit
"""
    with open(in_path, 'w') as f:
        f.write(content)
    print(f"{pqr}: center=({cx:.1f},{cy:.1f},{cz:.1f}) size=({sx:.0f},{sy:.0f},{sz:.0f}) "
          f"grid={nx}x{ny}x{nz} spacing={spacing:.2f} fglen=({fx:.0f},{fy:.0f},{fz:.0f}) -> {in_path}")

if __name__ == '__main__':
    main()
