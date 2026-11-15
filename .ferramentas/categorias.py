import json, os, re, sys, time, io, html, urllib.parse, urllib.request
from PIL import Image

UA = "MinhaIgrejinhaImagens/1.1 (minhaigrejinha@gmail.com) python-urllib"
alvos = json.load(open(sys.argv[1]))
SAIDA = sys.argv[2]
os.makedirs(SAIDA + "/fotos", exist_ok=True)
EVITAR = re.compile(r"(map|coat|arms|wappen|stemma|church|chiesa|kirche|eglise|église|iglesia|igreja|altar|relic|reliqu|tomb|grave|grab|tomba|sepol|plaque|plaque|lapide|sign|stamp|briefmarke|francobollo|coin|moneta|page|folio|manuscript|codex|interior|exterior|facade|fassade|window|vitrail|street|strasse|via |panorama|view|vista|ansicht|logo|text|inscription|inschrift|signature|firma|\.svg|\.pdf|\.djvu|\.tif)", re.I)

def pedir(url):
    for n in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (429, 503):
                time.sleep(min(int(e.headers.get("Retry-After") or 0) or 20 * (n + 1), 120)); continue
            raise
        except Exception:
            time.sleep(5 * (n + 1))
    raise RuntimeError(url)

def api(base, **p):
    p["format"] = "json"
    return json.loads(pedir(base + "?" + urllib.parse.urlencode(p)))

def limpo(t):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html.unescape(t or ""))).strip()[:200]

qids = {v: k for k, v in alvos.items()}
cat = {}
lista = list(qids)
for i in range(0, len(lista), 50):
    d = api("https://www.wikidata.org/w/api.php", action="wbgetentities", ids="|".join(lista[i:i + 50]), props="claims")
    for q, ent in d.get("entities", {}).items():
        c = (ent.get("claims") or {}).get("P373") or []
        if c and c[0]["mainsnak"].get("datavalue"):
            cat[qids[q]] = c[0]["mainsnak"]["datavalue"]["value"]
    time.sleep(1)
print(len(alvos), "alvos;", len(cat), "com categoria no Commons", flush=True)

creditos, fim = {}, time.time() + 230 * 60
for sid, categoria in cat.items():
    if time.time() > fim: break
    try:
        m = api("https://commons.wikimedia.org/w/api.php", action="query", list="categorymembers", cmtitle="Category:" + categoria, cmtype="file", cmlimit="30")
        time.sleep(1)
        arquivos = [x["title"] for x in m.get("query", {}).get("categorymembers", []) if not EVITAR.search(x["title"]) and re.search(r"\.(jpe?g|png)$", x["title"], re.I)]
        if not arquivos: continue
        titulo = arquivos[0]
        d = api("https://commons.wikimedia.org/w/api.php", action="query", prop="imageinfo", iiprop="url|extmetadata", iiurlwidth="960", titles=titulo)
        time.sleep(1)
        p = next(iter(d["query"]["pages"].values()))
        ii = (p.get("imageinfo") or [None])[0]
        if not ii: continue
        meta = ii.get("extmetadata") or {}
        licenca = limpo((meta.get("LicenseShortName") or {}).get("value"))
        if not re.search(r"CC0|CC BY|Public domain|PD", licenca, re.I): continue
        img = Image.open(io.BytesIO(pedir(ii.get("thumburl") or ii["url"])))
        time.sleep(1)
        img.seek(0); img = img.convert("RGB"); img.thumbnail((600, 800))
        img.save(f"{SAIDA}/fotos/{sid}.webp", "WEBP", quality=72)
        creditos[sid] = {"arquivo": f"{sid}.webp", "autor": limpo((meta.get("Artist") or {}).get("value")) or "Desconhecido", "licenca": licenca, "url": ii.get("descriptionurl", ""), "titulo": titulo}
        if len(creditos) % 25 == 0:
            json.dump(creditos, open(SAIDA + "/creditos.json", "w"), ensure_ascii=False, indent=1)
            print(len(creditos), "fotos", flush=True)
    except Exception as e:
        print("falha", sid, str(e)[:80], flush=True)
json.dump(creditos, open(SAIDA + "/creditos.json", "w"), ensure_ascii=False, indent=1)
print(len(creditos), "fotos no fim")
