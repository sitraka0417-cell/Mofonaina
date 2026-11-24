#!/usr/bin/env python3
"""Mofonaina : maka ny donné avy amin'ny API Jasem, manova azy ho format h2/h3/h4/h5
ary manoratra ny fichier JJ_MM_AAAA.txt eo amin'ny fototry ny repo.

Fampiasana:
  python convert_fiambenana.py                    # maka avy amin'ny API, manoratra ao amin'ny "."
  python convert_fiambenana.py --input x.json     # fitiliana amin'ny json eo an-toerana
  python convert_fiambenana.py --out dossier/     # hanoratra any amin'ny dossier hafa
Ny token (raha ilaina) dia azo apetraka amin'ny variable API_TOKEN.
"""
import argparse, datetime, json, os, re, sys, time, urllib.request

DEFAULT_URL = "https://jasemsoftware.site/api/v1/fiambenana"
JIRO = ['Alatsinainy', 'Talata', 'Alarobia', 'Alakamisy', 'Zoma', 'Sabata', 'Alahady']
VOLANA = ['Janoary', 'Febroary', 'Marsa', 'Avrily', 'Mey', 'Jona', 'Jolay', 'Aogôsitra',
          'Septambra', 'Oktôbra', 'Nôvambra', 'Desambra']
REF = r"(?:\d\s)?[A-ZÀ-Ý][A-Za-zÀ-ÿ'’]*\.?\s*\d+:\d+"


# ---------- maka ny donné ----------
def http_json(url):
    headers = {"User-Agent": "Mozilla/5.0 (compatible; MofonainaBot/1.0)",
               "Accept": "application/json"}
    if os.environ.get("API_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["API_TOKEN"]
    last = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as exc:  # noqa
            last = exc
            time.sleep(3 * (attempt + 1))
    raise SystemExit(f"Tsy afaka naka ny API ({url}): {last}")


def entries_from(payload):
    """Manaiky lisitra mivantana na dict misy lisitra (data/items/results...)."""
    if isinstance(payload, list):
        return payload, None
    if isinstance(payload, dict):
        nxt = payload.get("next_page_url") or (payload.get("links") or {}).get("next") \
            if isinstance(payload.get("links"), dict) or payload.get("next_page_url") else None
        for k in ("data", "items", "results", "fiambenana"):
            if isinstance(payload.get(k), list):
                return payload[k], nxt
        for v in payload.values():
            if isinstance(v, list) and v and isinstance(v[0], dict):
                return v, nxt
    raise SystemExit("Tsy fantatra ny firafitry ny valin'ny API.")


def load(args):
    if args.input:
        return entries_from(json.load(open(args.input, encoding="utf-8")))[0]
    out, url, seen = [], args.url, set()
    while url and url not in seen:
        seen.add(url)
        items, url = entries_from(http_json(url))
        out.extend(items)
    return out


# ---------- fanovana format ----------
def typo(s):
    s = s.replace('\r\n', '\n').replace('\r', '\n').replace('\xa0', ' ')
    return s.replace('’', "'").replace('‘', "'").replace('“', '"').replace('”', '"')


def fix_nums(s):
    s = re.sub(r'(?<=\d):[ \t]+(?=\d)', ':', s)
    prev = None
    while prev != s:
        prev = s
        s = re.sub(r'(\d+:\d+(?:-\d+)?(?:,\d+(?:-\d+)?)*),[ \t]+(\d+)', r'\1,\2', s)
    return s


def fix_dash(s):
    return re.sub(r'(["\.!?\)])[ \t]*[-–—][ \t]*(?=' + REF + ')', r'\1 - ', s)


def norm_ref(r):
    r = fix_nums(typo(r).strip())
    r = re.sub(r'\s+', ' ', r)
    r = re.sub(r'[,\s]+\.?$', '', r)
    r = re.sub(r"^((?:\d )?[A-Za-zÀ-ÿ']+\.)(?=\d)", r'\1 ', r)
    return r if r.endswith('.') else r + '.'


def convert(e):
    dt = datetime.date.fromisoformat(str(e['daty'])[:10])
    h2 = f"{JIRO[dt.weekday()]} {dt.day} {VOLANA[dt.month - 1]} {dt.year}"
    fname = f"{dt.day:02d}_{dt.month:02d}_{dt.year}.txt"
    h3 = typo(e['lohateny_andro']).strip()

    verse = typo(e['andininy_soratra_masina']).strip()
    ref = e.get('toerana_soratra_masina')
    if not ref:
        m = re.search(r'["]?[ \t]*[-–—][ \t]*(' + REF + r'(?:[,\-]\s*\d+)*)\.?\s*$', verse)
        if m:
            ref, verse = m.group(1), verse[:m.start()].strip()
    verse = verse.strip().strip('"').strip()
    h4 = f'"{verse}"' + (f' - {norm_ref(ref)}' if ref else '')

    body = typo(e['mofon_aina'])
    body = re.sub(r'[ \t]*\n(?:[ \t]*\n)*[ \t]*', '\n\n', body).strip()
    body = fix_dash(fix_nums(body))
    body = re.sub(r'(?m)(?<=[\.!?\)"])[ \t]*[—–-][ \t]*(?=[^\n]{0,70}\b\d{4}\b[^\n]*\.$)(?=[A-Z])',
                  ' – ', body)
    src = typo(e.get('loharano') or '').strip()
    if src and not src.endswith('.'):
        src += '.'
    if src and not body.endswith(src):
        body = body.rstrip() + ' – ' + src

    return fname, f"<h2>{h2}</h2>\n\n<h3>{h3}</h3>\n\n<h4>{h4}</h4>\n\n<h5>{body}</h5>\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=DEFAULT_URL)
    ap.add_argument("--input")
    ap.add_argument("--out", default=".")
    args = ap.parse_args()

    entries = [e for e in load(args) if e.get('publish', True)]
    if not entries:
        raise SystemExit("Foana ny donné : tsy misy nosoratana (tsy nisy nofafana).")
    os.makedirs(args.out, exist_ok=True)
    new = changed = 0
    for e in entries:
        try:
            fname, txt = convert(e)
        except Exception as exc:  # entrée tsy feno : lavina, tsy manakana ny hafa
            print("Nolavina:", e.get('daty'), exc, file=sys.stderr)
            continue
        path = os.path.join(args.out, fname)
        old = open(path, encoding="utf-8").read() if os.path.exists(path) else None
        if old != txt:
            open(path, "w", encoding="utf-8").write(txt)
            new, changed = (new + 1, changed) if old is None else (new, changed + 1)
    print(f"{len(entries)} entrée(s) : {new} vaovao, {changed} nanavao, "
          f"{len(entries) - new - changed} tsy niova.")


if __name__ == "__main__":
    main()
