"""
Banzai Radar — Scraper via tcgcsv.com
API pública que espelha o TCGPlayer diariamente.
Zero scraping, zero autenticação, cobre One Piece e Gundam completos.
"""
import time
import logging
import requests

log = logging.getLogger(__name__)

BASE = "https://tcgcsv.com"
HEADERS = {"User-Agent": "BanzaiRadar/1.0 (internal market tool)"}

# Nomes dos jogos conforme TCGPlayer/tcgcsv
GAME_NAMES = {
    "OPTCG": "one piece card game",
    "GCG":   "gundam card game",
}


def _get(url: str) -> dict:
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    return resp.json()


def get_category_ids() -> dict[str, int]:
    """Descobre os categoryIds de OPTCG e GCG dinamicamente."""
    data = _get(f"{BASE}/tcgplayer/categories")
    result = {}
    for cat in data.get("results", []):
        name_lower = cat["name"].lower()
        for game_key, game_name in GAME_NAMES.items():
            if game_name in name_lower:
                result[game_key] = cat["categoryId"]
                log.info("  %s → categoryId %s", game_key, cat["categoryId"])
    return result


def get_groups(category_id: int) -> list[dict]:
    """Retorna todos os sets de um jogo."""
    data = _get(f"{BASE}/tcgplayer/{category_id}/groups")
    return data.get("results", [])


def get_products_and_prices(category_id: int, group_id: int, group_name: str = "") -> list[dict]:
    """
    Busca produtos + preços de um set e os une por productId.
    Filtra apenas cartas individuais (exclui sealed boxes, etc).
    """
    try:
        prod_data  = _get(f"{BASE}/tcgplayer/{category_id}/{group_id}/products")
        price_data = _get(f"{BASE}/tcgplayer/{category_id}/{group_id}/prices")
    except Exception as e:
        log.warning("    Falha no grupo %s: %s", group_id, e)
        return []

    # Indexa preços por productId — considera TODAS as variantes
    # (Normal, Foil, Reverse Holofoil, etc). Cartas raras/paralelas
    # costumam ter preço APENAS em Foil, então restringir a "Normal"
    # descartava justamente as cartas de maior valor.
    prices = {}
    for p in price_data.get("results", []):
        pid = p.get("productId")
        mkt = p.get("marketPrice") or 0.0
        current = prices.get(pid)
        # Mantém a variante de maior preço de mercado por carta
        if current is None or mkt > current["market_price"]:
            prices[pid] = {
                "market_price": mkt,
                "low_price":    p.get("lowPrice") or 0.0,
                "mid_price":    p.get("midPrice") or 0.0,
                "sub_type":     p.get("subTypeName"),
            }

    cards = []
    for prod in prod_data.get("results", []):
        pid   = prod["productId"]
        price = prices.get(pid, {})
        mkt   = price.get("market_price", 0.0)

        # Ignora produtos sem preço de mercado válido
        if mkt < 0.50:
            continue

        # Extrai rarity e set number do extendedData
        rarity = set_number = None
        for ext in prod.get("extendedData", []):
            if ext.get("name") in ("Rarity",):
                rarity = ext.get("value")
            elif ext.get("name") in ("Number", "CardNumber"):
                set_number = ext.get("value")

        # productTypeName vem sempre None nesse mirror (confirmado via teste).
        # Sinal confiável: cartas têm Rarity no extendedData, sealed não têm.
        is_card = bool(rarity)

        # Cinto de segurança: exclui por nome mesmo que rarity venha errado
        name_lower = prod.get("name", "").lower()
        SEALED_KEYWORDS = ("starter deck", "booster box", "booster pack",
                           "premium booster", "collection set", "demo deck",
                           "ultra deck", "case", "display")
        if any(kw in name_lower for kw in SEALED_KEYWORDS):
            is_card = False

        if not is_card:
            continue

        cards.append({
            "product_id":   pid,
            "name":         prod.get("name", ""),
            "set_name":     group_name,
            "rarity":       rarity,
            "set_number":   set_number,
            "market_price": mkt,
            "low_price":    price.get("low_price", 0.0),
            "mid_price":    price.get("mid_price", mkt),
            "tcg_url":      f"https://www.tcgplayer.com/product/{pid}",
        })

    if prod_data.get("results") and not cards:
        sample = prod_data["results"][0]
        log.warning("    ⚠️  %d produtos mas 0 passaram no filtro. Amostra bruta:", len(prod_data["results"]))
        log.warning("        productTypeName=%r  extendedData=%r",
                    sample.get("productTypeName"), sample.get("extendedData"))

    return cards


def scrape_all(games: list[str] = None) -> dict[str, list[dict]]:
    """
    Ponto de entrada principal.
    Retorna {game_key: [lista de cartas com preços]}.
    games: ['OPTCG', 'GCG'] ou None para ambos.
    """
    games = games or list(GAME_NAMES.keys())
    log.info("Descobrindo categoryIds...")
    cat_ids = get_category_ids()

    all_results = {}
    for game in games:
        cat_id = cat_ids.get(game)
        if not cat_id:
            log.warning("categoryId não encontrado para %s", game)
            continue

        log.info("Coletando %s (categoryId=%s)...", game, cat_id)
        groups = get_groups(cat_id)
        log.info("  %d sets encontrados", len(groups))

        cards = []
        for i, group in enumerate(groups, 1):
            gid   = group["groupId"]
            gname = group.get("name", gid)
            log.info("  [%d/%d] %s", i, len(groups), gname)
            batch = get_products_and_prices(cat_id, gid, gname)
            cards.extend(batch)
            time.sleep(0.4)  # respeita rate limit do tcgcsv.com

        log.info("  Total %s: %d cartas com preço", game, len(cards))
        all_results[game] = cards

    return all_results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
    results = scrape_all()
    for game, cards in results.items():
        print(f"\n{game}: {len(cards)} cartas")
        for c in sorted(cards, key=lambda x: -x["market_price"])[:5]:
            print(f"  {c['name']:<40} ${c['market_price']:.2f}")
