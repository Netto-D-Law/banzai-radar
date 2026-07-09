"""
Banzai Radar â Job de Coleta (auto-discovery)
Roda via GitHub Actions 3x/dia.
NÃ£o precisa cadastrar cartas manualmente â descobre tudo automaticamente.
"""
import sys, logging
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from db.models import init_db, get_conn
from scraper.tcgplayer import scrape_all
from analyzer.export_static import export as export_static

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger(__name__)


def upsert_card(conn, game: str, card: dict) -> int:
    """Insere carta nova ou retorna o id existente."""
    row = conn.execute(
        "SELECT id FROM cards WHERE product_id = ?", (card["product_id"],)
    ).fetchone()
    if row:
        conn.execute(
            "UPDATE cards SET set_code=?, name=?, rarity=? WHERE id=?",
            (card["set_name"], card["name"], card.get("rarity"), row["id"]),
        )
        return row["id"]
    cur = conn.execute(
        """INSERT INTO cards (name, set_code, game, rarity, tcg_url, product_id)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (card["name"], card["set_name"], game, card.get("rarity"), card["tcg_url"], card["product_id"])
    )
    return cur.lastrowid


def save_price(conn, card_id: int, card: dict):
    conn.execute(
        """INSERT INTO price_snapshots (card_id, price, market_price, low_price, source)
           VALUES (?, ?, ?, ?, 'tcgcsv')""",
        (card_id, card["mid_price"], card["market_price"], card["low_price"])
    )
    # MantÃ©m 90 dias de histÃ³rico
    conn.execute(
        "DELETE FROM price_snapshots WHERE card_id=? AND captured_at < datetime('now','-90 days')",
        (card_id,)
    )


def run():
    log.info("=== Banzai Radar â Coleta automÃ¡tica ===")
    init_db()

    results = scrape_all()  # coleta OPTCG + GCG completos

    conn = get_conn()
    total_saved = 0
    for game, cards in results.items():
        log.info("Salvando %d cartas de %s...", len(cards), game)
        for card in cards:
            card_id = upsert_card(conn, game, card)
            save_price(conn, card_id, card)
            total_saved += 1
        conn.commit()

    conn.close()
    log.info("=== Coleta concluÃ­da: %d snapshots salvos ===", total_saved)

    export_static()


if __name__ == "__main__":
    run()
