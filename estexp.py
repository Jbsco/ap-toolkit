#!/usr/bin/env python3
"""
estexp: recommend the next exposure from one or two frames.

  estexp.py light_540.fits                       # exposure from the FITS header
  estexp.py 200ms light_540.fits                 # override the current exposure
  estexp.py 5ms light_040.fits light_052.fits    # two frames: fit the light trend
  estexp.py light.fits --dark master_dark.fits   # pedestal from a master dark
  estexp.py light.fits --pedestal 200 --target 0.65 --lead 60

Method:
  level    = robust bright-content level (99.9th percentile after a 3x3 median
             on a 2x subsample, so isolated hot pixels do not set it)
  signal   = level - pedestal            (exposure scales signal, not pedestal)
  factor   = (target - pedestal) / signal
  next_exp = exp * factor, then projected forward by the light trend (two frames)

Target defaults to 65% of the ADC range (42.6k ADU on 16-bit), the usual
"bright content well up the histogram, headroom for a hot edge" point. If the
frame already clips, the true level is unknown and it recommends halving.
"""
import sys, os, re, glob, argparse, datetime
import numpy as np
import cv2
from astropy.io import fits

ADC_MAX = 65535.0


def parse_exp(s):
    """'10s' '200ms' '500us' '0.005' '1/250' -> seconds, or None if not an exposure."""
    m = re.fullmatch(r"\s*(\d+(?:\.\d*)?|\.\d+)\s*(s|sec|ms|us|µs)?\s*", s, re.I)
    if m:
        v = float(m.group(1)); u = (m.group(2) or "s").lower()
        return v * {"s": 1, "sec": 1, "ms": 1e-3, "us": 1e-6, "µs": 1e-6}[u]
    m = re.fullmatch(r"\s*1/(\d+(?:\.\d*)?)\s*", s)
    return 1.0 / float(m.group(1)) if m else None


def fmt_exp(sec):
    if sec >= 1:      return f"{sec:.3g} s"
    if sec >= 1e-3:   return f"{sec*1e3:.3g} ms"
    return f"{sec*1e6:.3g} us"


def to_adu(x):
    """Siril writes 32-bit output normalised to [0,1]; bring it back to ADU."""
    return x * ADC_MAX if x.dtype.kind == "f" and float(x.max()) <= 1.5 else x


def measure(path):
    """Return dict: level, clip_frac, exptime, date, layers."""
    with fits.open(path, memmap=False) as h:
        d = h[0].data; hd = h[0].header
    x = to_adu(np.asarray(d, dtype=np.float32))
    if x.ndim == 3:                      # debayered: brightest channel, 2x subsample
        sub = x.max(axis=0)[::2, ::2]
    else:                                # raw CFA: max of each 2x2 Bayer block, so the
        H, W = (x.shape[0] // 2) * 2, (x.shape[1] // 2) * 2   # brightest plane (G) counts
        sub = x[:H, :W].reshape(H // 2, 2, W // 2, 2).max(axis=(1, 3))
    clean = cv2.medianBlur(sub, 3)       # kill isolated hot pixels
    return dict(
        level=float(np.percentile(clean, 99.9)),
        peak=float(sub.max()),
        clip_frac=float((sub >= ADC_MAX * 0.99).mean()),
        exptime=hd.get("EXPTIME"),
        gain=hd.get("GAIN"),
        date=hd.get("DATE-OBS"),
        layers=1 if np.asarray(d).ndim == 2 else np.asarray(d).shape[0],
    )


def pedestal_from_dark(path):
    with fits.open(path, memmap=False) as h:
        d = to_adu(np.asarray(h[0].data, dtype=np.float32))
    if d.ndim == 3:
        d = d.max(axis=0)
    return float(np.median(d[::4, ::4]))


def find_dark(light_path, gain):
    """Locate a master dark relative to the light: <session>/.../Light/x.fits ->
    a sibling Dark/ directory (one or two levels up). Prefer a stacked master
    whose GAIN matches; the pedestal is gain-dependent, exposure barely matters
    at sub-second lengths. Returns (path, note) or (None, reason)."""
    here = os.path.dirname(os.path.abspath(light_path))
    roots = [here, os.path.dirname(here), os.path.dirname(os.path.dirname(here))]
    cands = []
    for r in roots:
        for name in ("Dark", "Darks", "dark", "darks"):
            p = os.path.join(r, name)
            if os.path.isdir(p):
                cands += sorted(glob.glob(os.path.join(p, "*.fit*")))
    if not cands:
        return None, "no Dark/ directory beside the light frame"
    masters = [c for c in cands if re.search(r"stack|master", os.path.basename(c), re.I)]
    pool = masters or cands
    same_gain = []
    for c in pool:
        try:
            if fits.getheader(c).get("GAIN") == gain:
                same_gain.append(c)
        except Exception:
            pass
    if same_gain:
        return same_gain[0], "auto: " + os.path.relpath(same_gain[0], here)
    return None, f"Dark/ found but no {'master' if masters else 'frame'} at gain {gain}"


def main():
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("args", nargs="+")
    ap.add_argument("--target", type=float, default=0.65,
                    help="target for bright content, fraction of ADC (default 0.65)")
    ap.add_argument("--clip", type=float, default=ADC_MAX,
                    help="ADU where this gain actually clips (default 65535)")
    ap.add_argument("--pedestal", type=float, default=None, help="bias pedestal, ADU")
    ap.add_argument("--dark", help="master dark/bias FITS; its median is the pedestal")
    ap.add_argument("--lead", type=float, default=60.0,
                    help="seconds until the new exposure takes effect (trend projection)")
    ap.add_argument("-h", "--help", action="store_true")
    a = ap.parse_args()
    if a.help:
        sys.exit(__doc__)

    exp_override = None; files = []
    for s in a.args:
        e = parse_exp(s)
        if e is None:
            files.append(s)
        else:
            exp_override = e
    if not files or len(files) > 2:
        sys.exit("need one or two FITS files (and optionally a current exposure)")

    frames = [measure(f) for f in files]
    cur = frames[-1]
    exp = exp_override if exp_override is not None else cur["exptime"]
    if exp is None:
        sys.exit("no exposure given and no EXPTIME in header")

    ped = a.pedestal
    ped_note = f"{ped:.0f} ADU (--pedestal)" if ped is not None else None
    if a.dark:
        ped = pedestal_from_dark(a.dark); ped_note = f"{ped:.0f} ADU (--dark)"
    elif ped is None:
        found, why = find_dark(files[-1], cur["gain"])
        if found:
            ped = pedestal_from_dark(found); ped_note = f"{ped:.0f} ADU ({why})"
        else:
            ped = 0.0
            ped_note = f"none ({why}); pass --pedestal or --dark, matters most when the frame is dark"

    target = a.target * a.clip
    level = cur["level"]

    print(f"frame      {files[-1]}")
    print(f"exposure   {fmt_exp(exp)}   gain {cur['gain']}   layers {cur['layers']}")
    print(f"level      p99.9 = {level:.0f} ADU  ({100*level/a.clip:.1f}% of clip)   peak {cur['peak']:.0f}")
    print(f"clipped    {100*cur['clip_frac']:.3f}% of pixels at/above 99% of clip")
    print(f"pedestal   {ped_note}")

    if cur["clip_frac"] > 0.001:
        print(f"\nRECOMMEND  {fmt_exp(exp/2)}   (frame is clipping: true level unknown, halve and re-measure)")
        return

    signal = level - ped
    if signal <= 0:
        sys.exit("no signal above the pedestal; frame is at the dark floor")
    factor = (target - ped) / signal
    rec = exp * factor
    print(f"factor     x{factor:.2f}  -> {fmt_exp(rec)} to put bright content at {100*a.target:.0f}% of clip")

    # trend from two frames: signal changes multiplicatively; project by --lead seconds
    if len(frames) == 2 and frames[0]["date"] and cur["date"]:
        t0 = datetime.datetime.fromisoformat(str(frames[0]["date"]))
        t1 = datetime.datetime.fromisoformat(str(cur["date"]))
        dt = (t1 - t0).total_seconds()
        s0 = frames[0]["level"] - ped
        if dt > 0 and s0 > 0 and signal > 0:
            rate = (signal / s0) ** (60.0 / dt)          # multiplicative change per minute
            proj = rec / (rate ** (a.lead / 60.0))
            print(f"trend      signal x{rate:.2f} per minute over {dt:.0f}s "
                  f"({'brightening' if rate > 1 else 'dimming'}); projected {a.lead:.0f}s ahead")
            rec = proj
    print(f"\nRECOMMEND  {fmt_exp(rec)}   ({rec:.4g} s for the Ekos exposure field)")


if __name__ == "__main__":
    main()
