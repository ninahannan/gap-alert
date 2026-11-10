"""
Alert harga GAP Public Gold ke Telegram channel, siap graf 30 hari.
- Hantar bila harga berubah (semakan setiap 10 minit)
- Hantar UPDATE HARIAN sekali sehari selepas PG kemas kini harga jam 12:00 malam
Perlu 2 env var: BOT_TOKEN dan CHANNEL_ID (cth: @nurhasninahannan)
"""
import os
import re
import random
import html
import csv
from datetime import datetime, timezone, timedelta

import requests

URL = "https://publicgold.com.my"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120 Safari/537.36"}
FAIL_SIMPAN = "last_price.txt"
FAIL_SEJARAH = "history.csv"
FAIL_HARIAN = "last_daily.txt"   # tarikh update harian terakhir dihantar
MYT = timezone(timedelta(hours=8))


def ambil_teks():
    r = requests.get(URL, headers=HEADERS, timeout=30)
    r.raise_for_status()
    teks = re.sub(r"<script.*?</script>|<style.*?</style>", " ", r.text, flags=re.S | re.I)
    teks = re.sub(r"<[^>]+>", " ", teks)
    teks = html.unescape(teks)
    return re.sub(r"\s+", " ", teks)


def cari_harga(teks, nama_program, gram):
    """Cari 'RM xxx = <gram> gram' selepas tajuk program (GAP / SAP)."""
    i = teks.upper().find(nama_program)
    if i == -1:
        return None
    bahagian = teks[i:i + 1500]
    harga = re.search(r"RM\s*([\d,\.]+)\s*=\s*" + re.escape(gram) + r"\s*gram", bahagian)
    return float(harga.group(1).replace(",", "")) if harga else None


def baca_terakhir():
    try:
        with open(FAIL_SIMPAN) as f:
            emas, perak = f.read().strip().split(",")
            return float(emas), (float(perak) if perak else None)
    except Exception:
        return None, None


def simpan(emas, perak):
    with open(FAIL_SIMPAN, "w") as f:
        f.write(f"{emas},{perak if perak else ''}")


def tambah_sejarah(masa_iso, emas, perak):
    baru = not os.path.exists(FAIL_SEJARAH)
    with open(FAIL_SEJARAH, "a") as f:
        if baru:
            f.write("masa,emas,perak\n")
        f.write(f"{masa_iso},{emas},{perak if perak else ''}\n")


def hantar_telegram(mesej, gambar=None):
    asas = f"https://api.telegram.org/bot{os.environ['BOT_TOKEN']}"
    data = {"chat_id": os.environ["CHANNEL_ID"], "parse_mode": "HTML"}
    if gambar:
        with open(gambar, "rb") as g:
            r = requests.post(f"{asas}/sendPhoto", data={**data, "caption": mesej},
                              files={"photo": g}, timeout=60)
    else:
        r = requests.post(f"{asas}/sendMessage", data={**data, "text": mesej}, timeout=30)
    r.raise_for_status()


def baris_perubahan(baru, lama):
    if lama is None or baru == lama:
        return ""
    beza = baru - lama
    return f"  📈 naik RM {beza:,.0f}" if beza > 0 else f"  📉 turun RM {abs(beza):,.0f}"


def ayat_banding(baru, lama, label_lama, label_baru):
    """Cth: Harga emas GAP TURUN sebanyak RM5 daripada RM577 (semalam) kepada RM572 (hari ini)."""
    if baru > lama:
        return (f"📈 Harga emas GAP <b>NAIK</b> sebanyak <b>RM{baru - lama:,.0f}</b> daripada "
                f"RM{lama:,.0f} ({label_lama}) kepada <b>RM{baru:,.0f}</b> ({label_baru}).")
    if baru < lama:
        return (f"📉 Harga emas GAP <b>TURUN</b> sebanyak <b>RM{lama - baru:,.0f}</b> daripada "
                f"RM{lama:,.0f} ({label_lama}) kepada <b>RM{baru:,.0f}</b> ({label_baru}).")
    return f"➖ Harga emas GAP <b>KEKAL</b> pada <b>RM{baru:,.0f}</b>, sama seperti {label_lama}."


def penutup_semalam(hari_ini):
    """Harga terakhir yang direkod sebelum hari ini."""
    akhir = None
    try:
        with open(FAIL_SEJARAH) as f:
            for row in csv.DictReader(f):
                if datetime.fromisoformat(row["masa"]).date() < hari_ini:
                    akhir = float(row["emas"])
    except FileNotFoundError:
        pass
    return akhir


BULAN = ["Jan", "Feb", "Mac", "Apr", "Mei", "Jun", "Jul", "Ogo", "Sep", "Okt", "Nov", "Dis"]


def tarikh_pendek(iso):
    d = datetime.fromisoformat(iso).date()
    return f"{d.day} {BULAN[d.month - 1]}"


HEADLINE_TURUN = [
    ("📉 <b>HARGA EMAS TURUN RM {beza}!</b>", "Peluang kumpul lebih banyak gram hari ini 💛"),
    ("🛒 <b>EMAS 'DISKAUN' RM {beza} HARI INI!</b>", "RM100 kini dapat {gram} g emas"),
    ("⏰ <b>HARGA EMAS TURUN RM {beza}</b>", "Masa yang baik untuk tambah simpanan emas anda"),
    ("💛 <b>EMAS LEBIH MURAH HARI INI!</b>", "Turun RM {beza}/g. Yang rajin simpan, tahu nilainya"),
]
HEADLINE_NAIK = [
    ("📈 <b>HARGA EMAS NAIK RM {beza}!</b>", "Simpanan emas anda makin bernilai ✨"),
    ("🚀 <b>EMAS NAIK RM {beza}</b>", "Yang mula simpan awal, sedang tersenyum 😊"),
    ("📈 <b>NAIK RM {beza} HARI INI</b>", "Setiap hari tangguh, gram yang dapat makin sikit"),
    ("✨ <b>NILAI EMAS MENINGKAT!</b>", "Naik RM {beza}/g. Emas kekal pilihan simpanan jangka panjang"),
]
HEADLINE_KEKAL = [
    ("🔔 <b>HARGA EMAS GAP HARI INI</b>", "Harga kekal stabil. Konsisten simpan, gram terus bertambah"),
    ("🔔 <b>HARGA EMAS GAP HARI INI</b>", "RM100 hari ini dapat {gram} g emas"),
]


def pilih_headline(emas, banding, gram_rm100):
    if banding is None or emas == banding:
        senarai, beza = HEADLINE_KEKAL, 0
    elif emas < banding:
        senarai, beza = HEADLINE_TURUN, banding - emas
    else:
        senarai, beza = HEADLINE_NAIK, emas - banding
    tajuk, sub = random.choice(senarai)
    isi = {"beza": f"{beza:,.0f}", "gram": f"{gram_rm100:.4f}" if gram_rm100 else "-"}
    return tajuk.format(**isi), sub.format(**isi)


def buat_caption(sekarang, emas, emas_lama, semalam, perak, perak_lama, gram_rm100, harian):
    tarikh = f"{sekarang.day} {BULAN[sekarang.month - 1]} {sekarang.year}"
    jam = sekarang.strftime("%I:%M %p").lstrip("0")

    # Update harian banding dengan semalam; alert biasa banding dengan harga sebelum
    banding = semalam if harian else emas_lama
    tajuk, sub = pilih_headline(emas, banding, gram_rm100)

    c = f"🌙 <b>UPDATE HARGA HARIAN</b> • {tarikh}\n\n" if harian else ""
    c += f"{tajuk}\n<i>{sub}</i>\n\n"
    c += f"📅 {tarikh}  •  🕒 {jam}\n\n"

    if harian:
        if semalam is not None:
            c += ayat_banding(emas, semalam, "semalam", "hari ini") + "\n"
    else:
        if emas_lama is not None:
            c += ayat_banding(emas, emas_lama, "harga sebelum", "terkini") + "\n"
        if semalam is not None and semalam != emas_lama:
            c += "\n" + ayat_banding(emas, semalam, "penutup semalam", "terkini") + "\n"

    c += f"\n✨ Emas 999.9 : <b>RM {emas:,.0f}/g</b>\n"
    if perak:
        c += f"⚪ Perak 999 : <b>RM {perak:,.0f}/100g</b>{baris_perubahan(perak, perak_lama)}\n"
    if gram_rm100:
        c += f"💰 Simpan RM100 = <b>{gram_rm100:.4f} g</b> emas\n"

    try:
        import json
        with open("ytd.json") as f:
            ytd = json.load(f)
        c += (f"\n📊 <b>Ringkasan {ytd['tahun']}</b>\n"
              f"▲ Tertinggi: RM {ytd['tertinggi']['harga']:,.0f} ({tarikh_pendek(ytd['tertinggi']['tarikh'])})\n"
              f"▼ Terendah: RM {ytd['terendah']['harga']:,.0f} ({tarikh_pendek(ytd['terendah']['tarikh'])})\n")
    except Exception:
        pass

    c += (
        "\nNak mula simpan emas dengan GAP? Buka akaun Public Gold "
        "dan mula serendah RM100 sahaja.\n"
        "👉 Daftar di sini: https://goldofficial.me/ninahannan/cara-bermula\n\n"
        "👩‍💼 Nina Hannan (<b>PG00256918</b>) &amp; Ahmad Azim\n"
        "📱 WhatsApp: wa.me/601133162410\n\n"
        "#HargaEmas #PublicGold #GAP #SimpanEmas"
    )
    return c


def tarikh_update_pg(teks):
    """Tarikh 'Last updated' di bahagian GAP website PG."""
    i = teks.upper().find("GOLD ACCUMULATION PROGRAM")
    if i == -1:
        return None
    m = re.search(r"Last updated\s*([0-9]{1,2}-[A-Za-z]{3}-[0-9]{4})", teks[i:i + 1500])
    try:
        return datetime.strptime(m.group(1), "%d-%b-%Y").date() if m else None
    except ValueError:
        return None


def perlu_update_harian(sekarang, teks):
    """Hantar update harian sekali sehari, sebaik PG kemas kini harga selepas 12:00 malam."""
    try:
        with open(FAIL_HARIAN) as f:
            if f.read().strip() == sekarang.date().isoformat():
                return False      # dah hantar hari ini
    except FileNotFoundError:
        pass
    if tarikh_update_pg(teks) == sekarang.date():
        return True               # PG dah update untuk hari ini
    return sekarang.hour >= 1     # fallback: kalau tarikh PG tak jelas, hantar lepas 1 pagi


def main():
    teks = ambil_teks()
    emas = cari_harga(teks, "GOLD ACCUMULATION PROGRAM", "1.0000")
    perak = cari_harga(teks, "SILVER ACCUMULATION PROGRAM", "100.0000")
    i = teks.upper().find("GOLD ACCUMULATION PROGRAM")
    m = re.search(r"RM\s*100\s*=\s*([\d\.]+)\s*gram", teks[i:i + 1500]) if i != -1 else None
    gram_rm100 = float(m.group(1)) if m else None
    if not emas:
        raise SystemExit("Harga GAP tak jumpa - mungkin layout website berubah.")

    sekarang = datetime.now(MYT)
    emas_lama, perak_lama = baca_terakhir()
    harian = perlu_update_harian(sekarang, teks)
    berubah = not (emas == emas_lama and perak == perak_lama)

    if not harian and not berubah:
        print("Harga sama, tak hantar:", emas)
        return

    semalam = penutup_semalam(sekarang.date())   # baca SEBELUM rekod harga baru
    tambah_sejarah(sekarang.isoformat(timespec="seconds"), emas, perak)

    try:  # lukis graf dulu (ia juga kemas kini ytd.json)
        from graf import lukis
        gambar = lukis(FAIL_SEJARAH, gram_rm100=gram_rm100)
    except Exception as e:  # kalau graf gagal, tetap hantar teks
        print("Graf gagal:", e)
        gambar = None

    mesej = buat_caption(sekarang, emas, emas_lama, semalam, perak, perak_lama, gram_rm100, harian)
    hantar_telegram(mesej, gambar)
    simpan(emas, perak)
    if harian:
        with open(FAIL_HARIAN, "w") as f:
            f.write(sekarang.date().isoformat())
    print("Berjaya hantar:", emas, "(harian)" if harian else "(perubahan)")


if __name__ == "__main__":
    main()
