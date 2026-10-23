"""
Tjekker hvilke varer der ligger på en stand i Børneloppen og registrerer,
hvilke der er forsvundet (= solgt) siden sidste kørsel.

Kører på GitHub Actions hver 3. time. Data gemmes i docs/data/, som
dashboardet (docs/index.html) læser.
"""

import json
import os
import re
import sys
import time
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

# ---- Indstillinger ---------------------------------------------------------
BUTIK_ID = os.environ.get("BUTIK_ID", "21")      # 21 = Lyngby
STAND = os.environ.get("STAND", "151")
BASE = "https://www.boerneloppen.dk/webshop"
MAX_SIDER = 60                                    # sikkerhedsgrænse
MAKS_FALD = 0.5   # forsvinder mere end 50 % på én gang, er det nok en fejl

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs", "data")
VARER_FIL = os.path.join(DATA_DIR, "varer.json")
KOERSLER_FIL = os.path.join(DATA_DIR, "koersler.json")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36")

PRODUKT_RE = re.compile(r"/webshop/[^?#]+-(\d{6,})/?$")
PRIS_RE = re.compile(r"(\d{1,3}(?:\.\d{3})*|\d+),(\d{2})\s*kr", re.I)
STR_RE = re.compile(r"Str\.?\s*:?\s*([0-9A-Za-zÆØÅæøå/\-\.]+)")
STAND_RE = re.compile(r"Stand\s*(\d+)", re.I)


def nu_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


# ---- Hent og fortolk sider --------------------------------------------------
def kort_for_link(a, produkt_id):
    """Find det mindste element omkring linket, der indeholder prisen."""
    el = a
    for _ in range(8):
        if el.parent is None:
            break
        el = el.parent
        ids = {m.group(1) for x in el.find_all("a", href=True)
               if (m := PRODUKT_RE.search(x["href"].split("?")[0]))}
        if len(ids) > 1:
            return None  # gået for langt op – flere varer i samme element
        if PRIS_RE.search(el.get_text(" ", strip=True)):
            return el
    return None


def fortolk(html):
    """Returnerer {id: vare} for alle varer på en side/fragment."""
    soup = BeautifulSoup(html, "html.parser")
    varer = {}
    for a in soup.find_all("a", href=True):
        href = a["href"].split("?")[0].split("#")[0]
        m = PRODUKT_RE.search(href)
        if not m:
            continue
        pid = m.group(1)
        if pid in varer:
            # flere links til samme vare (billede + titel): udfyld manglende navn
            if not varer[pid]["navn"]:
                varer[pid]["navn"] = navn_fra_link(a)
            continue
        kort = kort_for_link(a, pid)
        if kort is None:
            continue
        tekst = kort.get_text(" ", strip=True)
        pm = PRIS_RE.search(tekst)
        pris = float(pm.group(1).replace(".", "") + "." + pm.group(2)) if pm else None
        sm = STR_RE.search(tekst)
        stm = STAND_RE.search(tekst)
        navn = navn_fra_link(a)
        if not navn:
            for x in kort.find_all("a", href=True):
                if pid in x["href"]:
                    navn = navn_fra_link(x)
                    if navn:
                        break
        url = href if href.startswith("http") else "https://www.boerneloppen.dk" + href
        varer[pid] = {
            "id": pid,
            "navn": navn,
            "str": sm.group(1).rstrip(".") if sm else None,
            "pris": pris,
            "stand": stm.group(1) if stm else None,
            "url": url,
        }
    return varer

def navn_fra_link(a):
    t = re.sub(r"\s+", " ", a.get_text(" ", strip=True)).strip()
    # Linket omslutter hele varekortet: klip "Lyngby - Stand 151 Str. ..." af
    m = re.search(r"\s*\S+\s*-\s*Stand\s*\d+", t)
    if m:
        t = t[:m.start()].strip()
    if t:
        return t
    img = a.find("img")
    if img and img.get("alt"):
        return img["alt"].strip()
    return a.get("title", "").strip()

def hent_alle():
    s = requests.Session()
    s.headers.update({"User-Agent": UA,
                      "Accept-Language": "da,en;q=0.8"})
    start_url = f"{BASE}?boerneloppen_theme_store_id={BUTIK_ID}&sku={STAND}"

    # 1) Almindelig sidevisning: sætter sessions-cookien og giver side 1
    r = s.get(start_url, timeout=30)
    r.raise_for_status()
    alle = fortolk(r.text)
    print(f"Side 1: {len(alle)} varer")

    # 2) "Hent flere"-kald, som browseren laver når man scroller
    xhr = {"X-Requested-With": "XMLHttpRequest", "Accept": "*/*",
           "Referer": start_url}
    tomme_i_traek = 0
    for side in range(2, MAX_SIDER + 1):
        time.sleep(1.5)  # vær flink ved serveren
        r = s.get(f"{start_url}&page={side}&priority=", headers=xhr, timeout=30)
        r.raise_for_status()
        nye = {k: v for k, v in fortolk(r.text).items() if k not in alle}
        print(f"Side {side}: {len(nye)} nye varer")
        if not nye:
            tomme_i_traek += 1
            if tomme_i_traek >= 2:   # to sider uden nyt = slut
                break
            continue
        tomme_i_traek = 0
        alle.update(nye)

    # Behold kun varer, der faktisk står på standen (hvis standnr. er angivet)
    return {k: v for k, v in alle.items() if v["stand"] in (None, STAND)}


# ---- Sammenlign med sidst ---------------------------------------------------
def indlaes(fil, standard):
    try:
        with open(fil, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return standard


def gem(fil, data):
    os.makedirs(os.path.dirname(fil), exist_ok=True)
    with open(fil, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)


def opdater(gamle, fundne, tid):
    """Returnerer (varer, statistik). gamle/varer: {id: vare med status}."""
    varer = {k: dict(v) for k, v in gamle.items()}
    nye = solgte = tilbage = 0

    for pid, v in fundne.items():
        if pid not in varer:
            varer[pid] = {**v, "status": "paa_stand", "foerst_set": tid,
                          "sidst_set": tid, "solgt": None}
            nye += 1
        else:
            g = varer[pid]
            if g["status"] == "solgt":
                # dukkede op igen: var ikke solgt alligevel
                g["status"] = "paa_stand"
                g["solgt"] = None
                tilbage += 1
            g.update({k: v[k] for k in ("navn", "str", "pris", "url") if v.get(k) is not None})
            g["sidst_set"] = tid

    for pid, g in varer.items():
        if g["status"] == "paa_stand" and pid not in fundne:
            g["status"] = "solgt"
            g["solgt"] = tid
            solgte += 1

    return varer, {"nye": nye, "solgte": solgte, "tilbage": tilbage}


def main():
    tid = nu_iso()
    gamle = indlaes(VARER_FIL, {})
    koersler = indlaes(KOERSLER_FIL, [])

    fundne = hent_alle()
    paa_stand_foer = sum(1 for v in gamle.values() if v["status"] == "paa_stand")

    if not fundne:
        print("FEJL: Fandt ingen varer – gemmer intet. (Er standen tom eller har siden ændret sig?)")
        sys.exit(1)
    if paa_stand_foer >= 10 and len(fundne) < paa_stand_foer * (1 - MAKS_FALD):
        print(f"FEJL: Kun {len(fundne)} af {paa_stand_foer} varer fundet – ligner en fejl, gemmer intet.")
        sys.exit(1)

    varer, stat = opdater(gamle, fundne, tid)
    koersler.append({"tid": tid, "antal": len(fundne), **stat})
    koersler = koersler[-2000:]

    gem(VARER_FIL, varer)
    gem(KOERSLER_FIL, koersler)
    print(f"OK: {len(fundne)} varer på standen, {stat['nye']} nye, "
          f"{stat['solgte']} solgt, {stat['tilbage']} dukket op igen")


if __name__ == "__main__":
    main()
