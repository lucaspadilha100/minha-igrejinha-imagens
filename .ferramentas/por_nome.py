import json, os, re, sys, time, io, html, urllib.parse, urllib.request
from PIL import Image

UA = "MinhaIgrejinhaImagens/1.1 (minhaigrejinha@gmail.com) python-urllib"
alvos = json.load(open(sys.argv[1]))
SAIDA = sys.argv[2]
os.makedirs(SAIDA + "/fotos", exist_ok=True)
SANTO = re.compile(r"(saint|santo|santa|san |beato|beata|blessed|venerab|martyr|martire|mártir|bishop|vescovo|bispo|priest|sacerdote|presbítero|monk|monaco|abbot|abate|nun|religios|suora|frate|friar|hermit|eremita|pope|papa|catholic|cattolic|católic)", re.I)

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

creditos, achados, fim = {}, {}, time.time() + 230 * 60
for sid, nomes in alvos.items():
    if time.time() > fim: break
    try:
        ent = None
        for nome, lingua in nomes:
            r = api("https://www.wikidata.org/w/api.php", action="wbsearchentities", search=nome, language=lingua, uselang=lingua, type="item", limit="5")
            time.sleep(1)
            bons = [x for x in r.get("search", []) if SANTO.search(x.get("description", "") or "")]
            if len(bons) >= 1:
                ent = bons[0]; break
        if not ent: continue
        d = api("https://www.wikidata.org/w/api.php", action="wbgetentities", ids=ent["id"], props="claims")
        time.sleep(1)
        claims = d["entities"][ent["id"]].get("claims", {})
        arquivo = None
        if claims.get("P18") and claims["P18"][0]["mainsnak"].get("datavalue"):
            arquivo = "File:" + claims["P18"][0]["mainsnak"]["datavalue"]["value"]
        elif claims.get("P373") and claims["P373"][0]["mainsnak"].get("datavalue"):
            m = api("https://commons.wikimedia.org/w/api.php", action="query", list="categorymembers", cmtitle="Category:" + claims["P373"][0]["mainsnak"]["datavalue"]["value"], cmtype="file", cmlimit="20")
            time.sleep(1)
            fs = [x["title"] for x in m.get("query", {}).get("categorymembers", []) if re.search(r"\.(jpe?g|png)$", x["title"], re.I) and not re.search(r"(map|coat|arms|church|chiesa|kirche|altar|relic|tomb|grave|plaque|stamp|coin|page|interior|facade|window|street|view|logo)", x["title"], re.I)]
            arquivo = fs[0] if fs else None
        if not arquivo: continue
        d = api("https://commons.wikimedia.org/w/api.php", action="query", prop="imageinfo", iiprop="url|extmetadata", iiurlwidth="960", titles=arquivo)
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
        creditos[sid] = {"arquivo": f"{sid}.webp", "autor": limpo((meta.get("Artist") or {}).get("value")) or "Desconhecido", "licenca": licenca, "url": ii.get("descriptionurl", ""), "qid": ent["id"], "descricao": ent.get("description", ""), "rotulo": ent.get("label", "")}
        if len(creditos) % 25 == 0:
            json.dump(creditos, open(SAIDA + "/creditos.json", "w"), ensure_ascii=False, indent=1)
            print(len(creditos), "fotos", flush=True)
    except Exception as e:
        print("falha", sid, str(e)[:80], flush=True)
json.dump(creditos, open(SAIDA + "/creditos.json", "w"), ensure_ascii=False, indent=1)
print(len(creditos), "fotos no fim")
