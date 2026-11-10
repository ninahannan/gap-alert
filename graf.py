"""
Lukis graf harga GAP 30 hari - Versi 2 (landskap + panel ringkasan tahunan).
Style Nina Hannan: maroon & emas + watermark.
"""
import csv
import json
import os
from datetime import datetime, timedelta, timezone, date

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import FancyBboxPatch
import numpy as np

# ---------- Tetapan jenama ----------
NAMA = "Nina Hannan"
SUBTAJUK = "Public Gold Dealer"
TELEFON = "011-3316 2410"   # kosongkan "" kalau tak nak tunjuk
PGCODE = "PG00256918"               # cth "PG00123456" - isi kalau nak tunjuk kod dealer

FAIL_TAHUNAN = "ytd.json"   # simpan tertinggi/terendah tahun semasa

BG = "#4A0A10"
PANEL = "#5E1018"
EMAS = "#F2C14E"
EMAS_CERAH = "#FFE08A"
KRIM = "#E9CFA8"
HIJAU = "#7CF0B0"
MERAH = "#FF9A8A"

BULAN = ["Jan", "Feb", "Mac", "Apr", "Mei", "Jun", "Jul", "Ogo", "Sep", "Okt", "Nov", "Dis"]


def tarikh_my(d, tahun=True):
    s = f"{d.day} {BULAN[d.month - 1]}"
    return f"{s} {d.year}" if tahun else s


def harga_harian(fail_sejarah, hari=30):
    harian = {}
    with open(fail_sejarah) as f:
        for row in csv.DictReader(f):
            t = datetime.fromisoformat(row["masa"])
            harian[t.date()] = float(row["emas"])
    tarikh = sorted(harian)[-hari:]
    return tarikh, [harian[d] for d in tarikh]


def kemas_kini_tahunan(harga, hari_ini):
    """Baca ytd.json, kemas kini kalau harga hari ini pecah rekod. Reset bila tahun baru."""
    data = {}
    if os.path.exists(FAIL_TAHUNAN):
        with open(FAIL_TAHUNAN) as f:
            data = json.load(f)
    if data.get("tahun") != hari_ini.year:
        data = {"tahun": hari_ini.year,
                "terendah": {"harga": harga, "tarikh": hari_ini.isoformat()},
                "tertinggi": {"harga": harga, "tarikh": hari_ini.isoformat()}}
    if harga < data["terendah"]["harga"]:
        data["terendah"] = {"harga": harga, "tarikh": hari_ini.isoformat()}
    if harga > data["tertinggi"]["harga"]:
        data["tertinggi"] = {"harga": harga, "tarikh": hari_ini.isoformat()}
    with open(FAIL_TAHUNAN, "w") as f:
        json.dump(data, f, indent=2)
    return data


def kad(fig, x, y, w, h, tajuk, nilai, bawah, warna):
    fig.add_artist(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.015",
                                  transform=fig.transFigure, facecolor="#2A0508",
                                  edgecolor=warna, lw=1.6, alpha=0.9))
    fig.text(x + 0.02, y + h - 0.045, tajuk, color=warna, fontsize=13, weight="bold")
    fig.text(x + 0.02, y + h - 0.125, nilai, color="white", fontsize=30, weight="bold")
    fig.text(x + 0.02, y + 0.03, bawah, color=KRIM, fontsize=13)


def lukis(fail_sejarah, fail_output="graf.png", gram_rm100=None):
    tarikh, harga = harga_harian(fail_sejarah)
    x = np.arange(len(harga))
    y = np.array(harga)
    semasa = y[-1]
    if not gram_rm100:
        gram_rm100 = 100 / semasa
    ytd = kemas_kini_tahunan(float(semasa), tarikh[-1])

    plt.rcParams["font.family"] = "DejaVu Sans"
    fig = plt.figure(figsize=(16, 10), dpi=100)

    # latar maroon gradient + jalur emas
    bg = fig.add_axes([0, 0, 1, 1], zorder=-10)
    bg.imshow(np.linspace(0, 1, 256).reshape(-1, 1), aspect="auto", extent=[0, 1, 0, 1],
              cmap=LinearSegmentedColormap.from_list("bg", ["#2A0508", "#6B111B"]), origin="lower")
    bg.axis("off")
    for yb in (0.99, 0.0):
        fig.add_artist(plt.Rectangle((0, yb), 1, 0.01, color=EMAS, transform=fig.transFigure))

    # ---- Header ----
    fig.text(0.04, 0.905, "HARGA EMAS GAP", color=EMAS, fontsize=40, weight="bold")
    fig.text(0.04, 0.862,
             f"Public Gold 999.9  •  Harga {len(harga)} hari terakhir",
             color=KRIM, fontsize=16)

    # ---- Graf (kiri) ----
    ax = fig.add_axes([0.065, 0.2, 0.655, 0.62], facecolor=PANEL)
    ax.patch.set_alpha(0.55)
    pad = max((y.max() - y.min()) * 0.3, 6)
    lo, hi = y.min() - pad, y.max() + pad
    ax.set_xlim(-0.6, len(x) - 0.4)
    ax.set_ylim(lo, hi)

    grad = LinearSegmentedColormap.from_list("g", [(0.95, 0.76, 0.31, 0.0), (0.95, 0.76, 0.31, 0.55)])
    img = ax.imshow(np.linspace(0, 1, 256).reshape(-1, 1), aspect="auto", cmap=grad,
                    extent=[-0.6, len(x) - 0.4, lo, hi], origin="lower", zorder=1)
    poly = ax.fill_between(x, y, lo, color="none")
    img.set_clip_path(poly.get_paths()[0], transform=ax.transData)

    ax.plot(x, y, color=EMAS, lw=3.2, zorder=3, solid_capstyle="round",
            path_effects=[pe.Stroke(linewidth=8, foreground=EMAS, alpha=0.15), pe.Normal()])

    # harga pada setiap titik
    ax.scatter(x, y, s=34, color=EMAS_CERAH, edgecolor=BG, lw=1.5, zorder=4)
    arah = []
    for i in range(len(y)):
        kiri = y[i - 1] if i > 0 else y[i]
        kanan = y[i + 1] if i < len(y) - 1 else y[i]
        b = y[i] < (kiri + kanan) / 2
        if i > 0 and y[i] == y[i - 1] and b == arah[-1]:
            b = not b
        arah.append(b)
    for i in range(len(y)):
        ax.annotate(f"{y[i]:,.0f}", (x[i], y[i]), xytext=(0, -12 if arah[i] else 9),
                    textcoords="offset points", ha="center",
                    va="top" if arah[i] else "bottom", color="white",
                    fontsize=10.5, weight="bold", zorder=6,
                    path_effects=[pe.withStroke(linewidth=3, foreground=PANEL)])

    ax.scatter(x[-1], y[-1], s=260, color=EMAS_CERAH, alpha=0.25, zorder=4)
    ax.scatter(x[-1], y[-1], s=90, color=EMAS_CERAH, edgecolor=BG, lw=2, zorder=5)

    # tarikh penuh setiap hari di paksi bawah
    for s in ax.spines.values():
        s.set_visible(False)
    ax.grid(axis="y", color=EMAS, alpha=0.12, lw=1)
    ax.tick_params(colors=KRIM, labelsize=11, length=0, pad=8)
    ax.set_xticks(x)
    ax.set_xticklabels([tarikh_my(d, tahun=False) for d in tarikh], rotation=60,
                       ha="right", rotation_mode="anchor", fontsize=10.5)
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"RM {v:,.0f}"))

    ax.text(0.5, 0.5, NAMA.upper(), transform=ax.transAxes, ha="center", va="center",
            fontsize=80, weight="bold", color=EMAS, alpha=0.07, rotation=15, zorder=2)

    # ---- Panel ringkasan (kanan) ----
    px, pw = 0.755, 0.205
    beza = y[-1] - y[-2] if len(y) > 1 else 0
    warna_beza = HIJAU if beza > 0 else MERAH if beza < 0 else KRIM
    simbol = "▲" if beza > 0 else "▼" if beza < 0 else "■"

    fig.text(px, 0.905, f"RM {semasa:,.0f}", color=EMAS_CERAH, fontsize=40, weight="bold")
    fig.text(px, 0.862, "/gram", color=KRIM, fontsize=16)
    fig.text(px + 0.05, 0.862, f"{simbol} RM {abs(beza):,.0f} dari semalam", color=warna_beza,
             fontsize=16, weight="bold")

    fig.text(px, 0.79, f"RINGKASAN {ytd['tahun']}", color=EMAS, fontsize=15, weight="bold")
    t_hi = date.fromisoformat(ytd["tertinggi"]["tarikh"])
    t_lo = date.fromisoformat(ytd["terendah"]["tarikh"])
    kad(fig, px, 0.585, pw, 0.185, "▲ TERTINGGI", f"RM {ytd['tertinggi']['harga']:,.0f}",
        tarikh_my(t_hi), HIJAU)
    kad(fig, px, 0.38, pw, 0.185, "▼ TERENDAH", f"RM {ytd['terendah']['harga']:,.0f}",
        tarikh_my(t_lo), MERAH)
    kad(fig, px, 0.175, pw, 0.185, "SIMPAN RM100 DAPAT", f"{gram_rm100:.4f} g",
        "emas 999.9 melalui GAP", EMAS)

    # ---- Footer ----
    fig.add_artist(plt.Line2D([0.04, 0.96], [0.115, 0.115], color=EMAS, alpha=0.4, lw=1))
    r = fig.canvas.get_renderer()
    t_nama = fig.text(0.04, 0.06, NAMA, color=EMAS, fontsize=26, weight="bold")
    hujung = fig.transFigure.inverted().transform(t_nama.get_window_extent(r))[1][0]
    if PGCODE:
        t_kod = fig.text(hujung + 0.008, 0.06, f"({PGCODE})", color=EMAS_CERAH,
                         fontsize=22, weight="bold")
        hujung = fig.transFigure.inverted().transform(t_kod.get_window_extent(r))[1][0]
    fig.text(hujung + 0.018, 0.066, SUBTAJUK, color=KRIM, fontsize=14)
    hubungi = "   •   ".join(v for v in [
        f"WhatsApp {TELEFON}" if TELEFON else "",
    ] if v)
    fig.text(0.96, 0.066, hubungi, color="white", fontsize=18, ha="right", weight="bold")
    kini = datetime.now(timezone(timedelta(hours=8)))
    fig.text(0.04, 0.022,
             f"Dikemaskini {kini.strftime('%d/%m/%Y %I:%M %p')}  •  Harga rujukan dari publicgold.com.my. "
             "Harga boleh berubah pada bila-bila masa.",
             color=KRIM, alpha=0.7, fontsize=11)

    fig.savefig(fail_output)
    plt.close(fig)
    return fail_output


if __name__ == "__main__":
    print(lukis("history.csv", gram_rm100=0.1748))
