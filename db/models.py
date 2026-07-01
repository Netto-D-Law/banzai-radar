"""Banzai Radar — Database (updated: added product_id to cards)"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "radar.db"

def get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS cards (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id  INTEGER UNIQUE,          -- ID do TCGPlayer/tcgcsv
            name        TEXT NOT NULL,
            set_code    TEXT NOT NULL,
            game        TEXT NOT NULL CHECK(game IN ('OPTCG','GCG')),
            rarity      TEXT,
            tcg_url     TEXT,
            active      INTEGER DEFAULT 1,
            created_at  TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS price_snapshots (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            card_id      INTEGER NOT NULL REFERENCES cards(id),
            price        REAL NOT NULL,
            market_price REAL,
            low_price    REAL,
            source       TEXT DEFAULT 'tcgcsv',
            captured_at  TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS watchlist (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            card_id     INTEGER NOT NULL REFERENCES cards(id) UNIQUE,
            alert_price REAL,
            notes       TEXT,
            added_at    TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS events (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            event_date  TEXT NOT NULL,
            title       TEXT NOT NULL,
            description TEXT,
            game        TEXT,
            impact      TEXT CHECK(impact IN ('high','med','low')) DEFAULT 'med',
            created_at  TEXT DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_snapshots_card_date
            ON price_snapshots(card_id, captured_at DESC);
        CREATE INDEX IF NOT EXISTS idx_events_date
            ON events(event_date);
    """)
    conn.commit()
    conn.close()
    print("✅ Banco inicializado em:", DB_PATH)

if __name__ == "__main__":
    init_db()
