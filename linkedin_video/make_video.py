"""Build the LinkedIn WAF/DDoS/SASE animation (square MP4 + GIF) from frames.py.

    python linkedin_video/make_video.py            # 4.5s hold, 1.2s dissolve
    python linkedin_video/make_video.py --hold 6   # slower still

Transitions are deliberately SLOW: LinkedIn autoplays muted and silent, so every
frame must be readable in the feed without the viewer scrubbing.
Requires ffmpeg on PATH (Windows: winget install Gyan.FFmpeg).
"""
import argparse, os, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "frames"


def run(cmd):
    print("+", " ".join(str(c) for c in cmd[:6]), "...")
    subprocess.run(cmd, check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hold", type=float, default=4.5, help="seconds each frame is fully visible")
    ap.add_argument("--fade", type=float, default=1.2, help="crossfade duration in seconds")
    ap.add_argument("--fps", type=int, default=25)
    ap.add_argument("--out", default=str(ROOT.parent / "linkedin_sase_waf_ddos.mp4"))
    ap.add_argument("--gif", action="store_true", help="also emit a GIF (bigger, worse — MP4 is preferred)")
    a = ap.parse_args()

    if not shutil.which("ffmpeg"):
        sys.exit("ffmpeg not found on PATH. Windows: winget install Gyan.FFmpeg")

    # 1. render the PNGs
    OUT.mkdir(exist_ok=True)
    run([sys.executable, str(ROOT / "frames.py"), "--out", str(OUT)])
    pngs = sorted(OUT.glob("s*.png"))
    if not pngs:
        sys.exit("frames.py produced no PNGs")
    print("[i] %d frames" % len(pngs))

    # 2. chain them with xfade. Each clip must be long enough to hold AND overlap the
    #    next dissolve, else ffmpeg silently drops frames off the end.
    seg = a.hold + a.fade
    ins, filt, prev = [], [], None
    for i, p in enumerate(pngs):
        ins += ["-loop", "1", "-t", "%.3f" % (seg if i < len(pngs) - 1 else a.hold), "-i", str(p)]
    for i in range(1, len(pngs)):
        off = a.hold + (i - 1) * seg          # start of THIS dissolve on the merged timeline
        src = prev or "[0:v]"
        lbl = "[v%d]" % i
        filt.append("%s[%d:v]xfade=transition=fade:duration=%.3f:offset=%.3f%s"
                    % (src, i, a.fade, off, lbl))
        prev = lbl
    chain = ";".join(filt) + ("," if not filt else "")
    fc = (";".join(filt) + ";" + prev + "format=yuv420p[out]") if filt else "[0:v]format=yuv420p[out]"

    run(["ffmpeg", "-y", *ins, "-filter_complex", fc, "-map", "[out]",
         "-r", str(a.fps), "-c:v", "libx264", "-preset", "slow", "-crf", "18",
         "-pix_fmt", "yuv420p", "-movflags", "+faststart", a.out])

    total = a.hold * len(pngs) + a.fade * (len(pngs) - 1)
    print("[ok] %s  (~%.0fs, %.1f MB)" % (a.out, total, os.path.getsize(a.out) / 1e6))

    if a.gif:
        g = str(Path(a.out).with_suffix(".gif"))
        pal = str(ROOT / "pal.png")
        run(["ffmpeg", "-y", "-i", a.out, "-vf", "fps=12,scale=720:-1:flags=lanczos,palettegen", pal])
        run(["ffmpeg", "-y", "-i", a.out, "-i", pal, "-lavfi",
             "fps=12,scale=720:-1:flags=lanczos[x];[x][1:v]paletteuse", g])
        os.remove(pal)
        print("[ok] %s (%.1f MB)" % (g, os.path.getsize(g) / 1e6))


if __name__ == "__main__":
    main()
