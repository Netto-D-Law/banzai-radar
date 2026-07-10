"""
Banzai Radar — Export estático
Gera docs/data.json a cada coleta, para publicação via GitHub Pages.
O dashboard público lê esse arquivo direto — sem depender de servidor rodando.
"""
import json
from pathlib import Path
from datetime import datetime, timezone

from db.models import get_conn
from analyzer.momentum import get_top_movers, get_opportunities

DOCS_DIR = Path(__file__).parent.parent / "docs"


def export():
    DOCS_DIR.mkdir(exist_ok=True)

    conn = get_conn()
    total = conn.execute("SELECT COUNT(*) as n FROM cards WHERE active=1").fetchone()["n"]
    last_run = conn.execute("SELECT MAX(captured_at) as t FROM price_snapshots").fetchone()["t"]
    conn.close()

    # Radar amplo (200 cartas, piso $1) — o dashboard filtra por jogo/preço no navegador
    radar = get_top_movers(n=200, min_price=1.0)
    opportunities = get_opportunities(min_discount_pct=15.0)
    spikes = sum(1 for c in radar if c.status == "spike")

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "last_collection": last_run,
        "stats": {
            "monitored": total,
            "spikes_today": spikes,
            "opportunities": len(opportunities),
        },
        "radar": [
            {
                "card_id": c.card_id, "name": c.name, "set_code": c.set_code,
                "game": c.game, "rarity": c.rarity, "tcg_url": c.tcg_url,
                "price_now": c.price_now, "price_24h": c.price_24h, "price_7d": c.price_7d,
                "change_24h": c.change_24h, "change_7d": c.change_7d,
                "momentum": c.momentum, "status": c.status, "low_price": c.low_price, "high_price": c.high_price,
            } for c in radar
        ],
        "opportunities": opportunities,
        "events": [],  # reservado para uso futuro
    }

    out_path = DOCS_DIR / "data.json"
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ Export estático salvo em: {out_path} ({len(radar)} cartas)")


if __name__ == "__main__":
    export()
