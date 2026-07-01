"""Banzai Radar — API v1.1 (auto-discovery)"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from db.models import init_db, get_conn
from analyzer.momentum import get_top_movers, get_opportunities

app = FastAPI(title="Banzai Radar API", version="1.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
def startup():
    init_db()
    print("🚀 Banzai Radar API rodando")

@app.get("/api/radar")
def radar(game: str = None, set_code: str = None, top: int = 20, min_price: float = 1.0):
    """Top N cartas por variação de preço. ?game=OPTCG|GCG &set_code=OP-11 &top=20 &min_price=1"""
    data = get_top_movers(n=top, min_price=min_price, game=game.upper() if game else None, set_code=set_code)
    return [vars(c) for c in data]

@app.get("/api/opportunities")
def opportunities(min_discount: float = 15.0):
    """Cartas onde low_price está X% abaixo do market_price."""
    return get_opportunities(min_discount_pct=min_discount)

@app.get("/api/stats")
def stats():
    conn = get_conn()
    total    = conn.execute("SELECT COUNT(*) as n FROM cards WHERE active=1").fetchone()["n"]
    total_ps = conn.execute("SELECT COUNT(*) as n FROM price_snapshots").fetchone()["n"]
    last_run = conn.execute("SELECT MAX(captured_at) as t FROM price_snapshots").fetchone()["t"]
    conn.close()
    movers = get_top_movers(n=100, min_price=1.0)
    spikes = sum(1 for c in movers if c.status == "spike")
    return {"monitored": total, "snapshots": total_ps, "spikes_today": spikes,
            "opportunities": len(get_opportunities()), "last_collection": last_run}

@app.get("/api/watchlist")
def get_watchlist():
    conn = get_conn()
    rows = conn.execute("""
        SELECT w.id, w.alert_price, c.id AS card_id, c.name, c.set_code, c.game, c.rarity, c.tcg_url,
               ps.market_price AS price_now
        FROM watchlist w JOIN cards c ON c.id=w.card_id
        LEFT JOIN price_snapshots ps ON ps.id=(
            SELECT id FROM price_snapshots WHERE card_id=c.id ORDER BY captured_at DESC LIMIT 1)
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/watchlist/{card_id}")
def add_watchlist(card_id: int, alert_price: float = None):
    conn = get_conn()
    conn.execute("INSERT OR IGNORE INTO watchlist (card_id, alert_price) VALUES (?,?)", (card_id, alert_price))
    conn.commit(); conn.close()
    return {"ok": True}

@app.delete("/api/watchlist/{card_id}")
def del_watchlist(card_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM watchlist WHERE card_id=?", (card_id,))
    conn.commit(); conn.close()
    return {"ok": True}

@app.get("/api/events")
def events(game: str = None):
    conn = get_conn()
    if game:
        rows = conn.execute("SELECT * FROM events WHERE event_date>=date('now') AND (game=? OR game IS NULL) ORDER BY event_date", (game.upper(),)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM events WHERE event_date>=date('now') ORDER BY event_date").fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.get("/api/cards")
def list_cards(game: str = None, set_code: str = None):
    conn = get_conn()
    query = "SELECT * FROM cards WHERE active=1"
    params = []
    if game:
        query += " AND game=?"
        params.append(game.upper())
    if set_code:
        query += " AND set_code=?"
        params.append(set_code)
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.get("/api/sets")
def list_sets(game: str = None):
    """Lista as coleções (sets) com quantidade de cartas cadastradas."""
    conn = get_conn()
    query = """
        SELECT set_code, game, COUNT(*) as card_count
        FROM cards WHERE active=1
    """
    params = []
    if game:
        query += " AND game=?"
        params.append(game.upper())
    query += " GROUP BY set_code, game ORDER BY card_count DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]
