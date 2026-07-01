"""
Diagnóstico — testa o cruzamento produto x preço para "Two Legends".
Rodar: python debug_inspect.py
"""
import requests, json, time

BASE = "https://tcgcsv.com/tcgplayer"
CATEGORY_ID = 68
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) BanzaiRadar/1.0"}


def fetch(url, retries=3):
    for attempt in range(1, retries + 1):
        resp = requests.get(url, headers=HEADERS, timeout=20)
        if resp.status_code == 200 and resp.text.strip():
            return resp.json()
        print(f"  [tentativa {attempt}] status {resp.status_code}: {resp.text[:200]}")
        time.sleep(2)
    raise SystemExit("Falhou.")


groups = fetch(f"{BASE}/{CATEGORY_ID}/groups")["results"]
target = next(g for g in groups if g["name"] == "Two Legends")
group_id = target["groupId"]
print(f"Two Legends → groupId {group_id}\n")

products = fetch(f"{BASE}/{CATEGORY_ID}/{group_id}/products")["results"]
prices   = fetch(f"{BASE}/{CATEGORY_ID}/{group_id}/prices")["results"]

print(f"Total produtos: {len(products)}")
print(f"Total entradas de preço: {len(prices)}\n")

print("Amostra de 5 entradas RAW de preço:")
for p in prices[:5]:
    print(" ", json.dumps(p, ensure_ascii=False))

# Testa o cruzamento pros mesmos 5 produtos do meio usados antes
meio = len(products) // 2
amostra = products[meio:meio+5]

print("\nCruzamento produto → preço:")
price_by_id = {}
for p in prices:
    pid = p.get("productId")
    price_by_id.setdefault(pid, []).append(p)

for prod in amostra:
    pid = prod["productId"]
    entries = price_by_id.get(pid, [])
    print(f"\n{prod['name']} (productId={pid})")
    if not entries:
        print("  ❌ NENHUMA entrada de preço encontrada para este productId")
    for e in entries:
        print(f"  subTypeName={e.get('subTypeName')!r}  marketPrice={e.get('marketPrice')}  lowPrice={e.get('lowPrice')}")
