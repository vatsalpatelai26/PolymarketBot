import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "polymarket.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS traders (
            address TEXT PRIMARY KEY,
            username TEXT,
            display_name TEXT,
            profile_image TEXT,
            bio TEXT,
            follower_count INTEGER,
            following_count INTEGER,
            volume_traded REAL,
            last_profile_sync TEXT
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS trades (
            trade_id TEXT PRIMARY KEY,
            trader_address TEXT NOT NULL,
            market_slug TEXT,
            market_question TEXT,
            outcome TEXT,
            side TEXT,
            price REAL,
            size REAL,
            amount REAL,
            token_id TEXT,
            tx_hash TEXT,
            timestamp TEXT,
            raw_json TEXT,
            FOREIGN KEY(trader_address) REFERENCES traders(address)
        )
        """
    )

    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_trades_trader_timestamp
        ON trades(trader_address, timestamp DESC)
        """
    )

    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print(f"Initialized database at {DB_PATH}")
