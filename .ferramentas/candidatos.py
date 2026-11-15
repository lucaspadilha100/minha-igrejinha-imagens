import json, os, re, sys, time, io, html, urllib.parse, urllib.request
from PIL import Image

UA = "MinhaIgrejinhaImagens/1.2 (minhaigrejinha@gmail.com) python-urllib"
alvos = json.load(open(sys.argv[1]))
SAIDA, PARTE, PARTES = sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
os.makedirs(SAIDA + "/fotos", exist_ok=True)
EVITAR = re.compile(r"(map|coat|arms|wappen|stemma|church|chiesa|kirche|eglise|église|iglesia|igreja|kerk|kościół|altar|relic|reliqu|tomb|grave|grab|tomba|sepol|sarcoph|plaque|lapide|stamp|briefmarke|francobollo|coin|moneta|page|folio|manuscript|codex|interior|exterior|facade|fassade|street|strasse|panorama|view|vista|ansicht|logo|inscription|inschrift|signature|firma|bulle|letter|lettera|book|libro|cover|\.svg|\.pdf|\.djvu|\.tif)", re.I)
BOM = re.compile(r"(portrait|ritratto|retrato|bildnis|painting|dipinto|pintura|icon|icona|ikon|santino|holy card|statue|statua|estatua|figure|vitrail|stained|fresco|affresco|photo|foto)", re.I)
IMG = re.compile(r"\.(jpe?g|png|webp)$", re.I)

def pedir(url):
    for n in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (429, 503):
                time.sleep(min(int(e.headers.get("Retry-After") or 0) or 20 * (n + 1), 120)); continue
            if e.code == 404: return b"{}"
            raise
        except Exception:
            time.sleep(5 * (n + 1))
    raise RuntimeError(url)

def api(base, **p):
    p["format"] = "json"
    time.sleep(0.3)
    return json.loads(pedir(base + "?" + urllib.parse.urlencode(p)))

C = "https://commons.wikimedia.org/w/api.php"
def limpo(t):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html.unescape(t or ""))).strip()[:200]

def membros(cat, tipo, n):
    m = api(C, action="query", list="categorymembers", cmtitle="Category:" + cat, cmtype=tipo, cmlimit=str(n))
    return [x["title"] for x in m.get("query", {}).get("categorymembers", [])]

def candidatos(alvo):
    nomes, achados = list(alvo.get("nomes") or []), []
    cat = None
    if alvo.get("qid"):
        d = api("https://www.wikidata.org/w/api.php", action="wbgetentities", ids=alvo["qid"], props="claims|labels", languages="en|it|es|fr|de|pt")
        ent = d.get("entities", {}).get(alvo["qid"], {})
        c = (ent.get("claims") or {}).get("P373") or []
        if c and c[0]["mainsnak"].get("datavalue"): cat = c[0]["mainsnak"]["datavalue"]["value"]
        for l in ("it", "en", "es", "fr", "de"):
            v = (ent.get("labels") or {}).get(l, {}).get("value")
            if v and v not in nomes: nomes.append(v)
    if cat:
        achados += [t for t in membros(cat, "file", 100) if IMG.search(t) and not EVITAR.search(t)]
        if len(achados) < 3:
            for sub in [s for s in membros(cat, "subcat", 30) if not EVITAR.search(s)][:8]:
                achados += [t for t in membros(sub.split(":", 1)[1], "file", 30) if IMG.search(t) and not EVITAR.search(t)]
                if len(achados) >= 6: break
    if len(achados) < 2:
        buscas = [f'"{n}"' for n in nomes[:4]] + ([f"{n} filetype:bitmap" for n in nomes[:3]] if alvo.get("solto") else [])
        for b in buscas:
            r = api(C, action="query", list="search", srsearch=b, srnamespace="6", srlimit="10")
            achados += [x["title"] for x in r.get("query", {}).get("search", []) if IMG.search(x["title"]) and not EVITAR.search(x["title"])]
            if len(achados) >= 3: break
    vistos, lista = set(), []
    for t in sorted(achados, key=lambda t: 0 if BOM.search(t) else 1):
        if t not in vistos: vistos.add(t); lista.append(t)
    return lista[:3], cat

creditos, fim = {}, time.time() + 220 * 60
itens = sorted(alvos.items())[PARTE::PARTES]
for i, (sid, alvo) in enumerate(itens):
    if time.time() > fim: break
    try:
        lista, cat = candidatos(alvo)
        for k, titulo in enumerate(lista):
            d = api(C, action="query", prop="imageinfo", iiprop="url|extmetadata", iiurlwidth="960", titles=titulo)
            p = next(iter(d["query"]["pages"].values()))
            ii = (p.get("imageinfo") or [None])[0]
            if not ii: continue
            meta = ii.get("extmetadata") or {}
            licenca = limpo((meta.get("LicenseShortName") or {}).get("value"))
            if not re.search(r"CC0|CC BY|Public domain|PD", licenca, re.I): continue
            img = Image.open(io.BytesIO(pedir(ii.get("thumburl") or ii["url"])))
            img.seek(0); img = img.convert("RGB"); img.thumbnail((600, 800))
            if min(img.size) < 120: continue
            nome = f"{sid}__{k + 1}.webp"
            img.save(f"{SAIDA}/fotos/{nome}", "WEBP", quality=72)
            creditos.setdefault(sid, []).append({"arquivo": nome, "autor": limpo((meta.get("Artist") or {}).get("value")) or "Desconhecido", "licenca": licenca, "url": ii.get("descriptionurl", ""), "titulo": titulo, "categoria": cat or ""})
    except Exception as e:
        print("falha", sid, str(e)[:80], flush=True)
    if i % 25 == 0:
        json.dump(creditos, open(SAIDA + "/creditos.json", "w"), ensure_ascii=False, indent=1)
        print(i, "de", len(itens), ";", len(creditos), "com candidato", flush=True)
json.dump(creditos, open(SAIDA + "/creditos.json", "w"), ensure_ascii=False, indent=1)
print(len(creditos), "com candidato no fim")
