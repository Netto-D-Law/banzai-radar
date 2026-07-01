"""Banzai Radar — Analisador: top movers automático"""
from dataclasses import dataclass
from typing import Optional
from db.models import get_conn


@dataclass
class CardAnalysis:
    card_id: int
    name: str
    set_code: str
    game: str
    rarity: Optional[str]
    tcg_url: str
    price_now: float
    price_24h: float
    price_7d: float
    change_24h: float
    change_7d: float
    momentum: int
    status: str


def _pct(now, before):
    if not before or before <= 0:
        return 0.0
    return round((now - before) / before * 100, 1)

def _momentum(ch24, ch7d):
    n24 = max(0, min(100, (ch24 + 50)))
    n7d = max(0, min(100, (ch7d / 3 + 50)))
    return round(max(0, min(100, n24 * 0.70 + n7d * 0.30)))

def _status(ch24):
    if ch24 >= 20:  return "spike"
    if ch24 >= 8:   return "rising"
    if ch24 <= -8:  return "falling"
    return "stable"


def get_top_movers(n: int = 20, min_price: float = 1.0, game: str = None, set_code: str = None) -> list[CardAnalysis]:
    """
    Retorna as top N cartas com maior variação de preço em 24h.
    min_price: ignora cartas abaixo deste valor (elimina ruído)
    game: filtra por 'OPTCG' ou 'GCG' (None = todos)
    set_code: filtra por coleção específica (ex: 'Emperors in the New World')
    """
    conn = get_conn()

    filters = []
    params_base = []
    if game:
        filters.append("c.game = ?")
        params_base.append(game)
    if set_code:
        filters.append("c.set_code = ?")
        params_base.append(set_code)
    extra_filter = ("AND " + " AND ".join(filters)) if filters else ""

    # Busca preço atual (snapshot mais recente por carta)
    cards = conn.execute(f"""
        SELECT
            c.id, c.name, c.set_code, c.game, c.rarity, c.tcg_url,
            ps.market_price AS price_now
        FROM cards c
        JOIN price_snapshots ps ON ps.id = (
            SELECT id FROM price_snapshots
            WHERE card_id = c.id ORDER BY captured_at DESC LIMIT 1
        )
        WHERE c.active = 1
          AND ps.market_price >= ?
          {extra_filter}
    """, [min_price] + params_base).fetchall()

    results = []
    for card in cards:
        price_now = card["price_now"]

        # Preço 24h atrás (snapshot mais próximo de 24h)
        row_24h = conn.execute("""
            SELECT market_price FROM price_snapshots
            WHERE card_id = ? AND captured_at <= datetime('now', '-20 hours')
            ORDER BY captured_at DESC LIMIT 1
        """, (card["id"],)).fetchone()

        # Preço 7d atrás
        row_7d = conn.execute("""
            SELECT market_price FROM price_snapshots
            WHERE card_id = ? AND captured_at <= datetime('now', '-6 days')
            ORDER BY captured_at DESC LIMIT 1
        """, (card["id"],)).fetchone()

        price_24h = row_24h["market_price"] if row_24h else price_now
        price_7d  = row_7d["market_price"]  if row_7d  else price_now

        ch24 = _pct(price_now, price_24h)
        ch7d = _pct(price_now, price_7d)

        results.append(CardAnalysis(
            card_id   = card["id"],
            name      = card["name"],
            set_code  = card["set_code"],
            game      = card["game"],
            rarity    = card["rarity"],
            tcg_url   = card["tcg_url"],
            price_now = price_now,
            price_24h = price_24h,
            price_7d  = price_7d,
            change_24h= ch24,
            change_7d = ch7d,
            momentum  = _momentum(ch24, ch7d),
            status    = _status(ch24),
        ))

    conn.close()

    # Ordena: spikes primeiro, depois por variação 24h desc
    results.sort(key=lambda x: (x.status != "spike", -x.change_24h))
    return results[:n]


def get_opportunities(min_discount_pct: float = 15.0) -> list[dict]:
    """Cartas onde low_price está X% abaixo do market_price."""
    conn = get_conn()
    rows = conn.execute("""
        SELECT c.id, c.name, c.set_code, c.game, c.tcg_url,
               ps.market_price, ps.low_price, ps.captured_at,
               ROUND((ps.market_price - ps.low_price) / ps.market_price * 100, 1) AS discount_pct
        FROM cards c
        JOIN price_snapshots ps ON ps.id = (
            SELECT id FROM price_snapshots WHERE card_id = c.id
            ORDER BY captured_at DESC LIMIT 1
        )
        WHERE c.active = 1
          AND ps.market_price > 0
          AND ps.low_price > 0
          AND (ps.market_price - ps.low_price) / ps.market_price * 100 >= ?
        ORDER BY (ps.market_price - ps.low_price) DESC
    """, (min_discount_pct,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]
