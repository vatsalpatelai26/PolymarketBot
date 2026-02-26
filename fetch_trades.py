import argparse
import json
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from db import get_connection, init_db

BASE_API = "https://data-api.polymarket.com"
DEFAULT_CONFIG = Path(__file__).resolve().parent / "tracked_traders.json"


def load_tracked_traders(config_path: Path) -> List[str]:
    if not config_path.exists():
        raise FileNotFoundError(
            f"Missing {config_path}. Create it with a JSON array of trader wallet addresses."
        )

    data = json.loads(config_path.read_text())
    if not isinstance(data, list):
        raise ValueError("tracked_traders.json must contain a JSON list of wallet addresses")

    return [str(address).strip().lower() for address in data if str(address).strip()]


def http_get_json(path: str, params: Optional[Dict[str, Any]] = None) -> Any:
    query = f"?{urlencode(params)}" if params else ""
    url = f"{BASE_API}{path}{query}"
    request = Request(url, headers={"User-Agent": "PolymarketBot/1.0"})
    with urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def try_profile(address: str) -> Dict[str, Any]:
    endpoints = [
        f"/users/{address}",
        f"/profile/{address}",
        "/users",
    ]

    for endpoint in endpoints:
        try:
            if endpoint == "/users":
                data = http_get_json(endpoint, {"address": address})
            else:
                data = http_get_json(endpoint)

            if isinstance(data, list) and data:
                return data[0]
            if isinstance(data, dict) and data:
                return data
        except Exception:
            continue

    return {"address": address}


def normalize_trade(trade: Dict[str, Any], address: str) -> Optional[Dict[str, Any]]:
    trade_id = str(
        trade.get("id")
        or trade.get("tradeId")
        or trade.get("transactionHash")
        or f"{address}-{trade.get('timestamp')}-{trade.get('tokenID')}"
    )

    if not trade_id:
        return None

    timestamp = (
        trade.get("timestamp")
        or trade.get("createdAt")
        or trade.get("time")
        or datetime.now(timezone.utc).isoformat()
    )

    return {
        "trade_id": trade_id,
        "trader_address": address,
        "market_slug": trade.get("marketSlug") or trade.get("slug"),
        "market_question": trade.get("question") or trade.get("marketQuestion"),
        "outcome": trade.get("outcome") or trade.get("outcomeName"),
        "side": trade.get("side") or trade.get("type"),
        "price": trade.get("price") or trade.get("outcomePrice"),
        "size": trade.get("size") or trade.get("shares"),
        "amount": trade.get("amount") or trade.get("usdcSize") or trade.get("value"),
        "token_id": trade.get("tokenID") or trade.get("tokenId"),
        "tx_hash": trade.get("transactionHash") or trade.get("txHash"),
        "timestamp": str(timestamp),
        "raw_json": json.dumps(trade),
    }


def fetch_trades_for_address(address: str, limit: int = 100) -> List[Dict[str, Any]]:
    candidate_params = [
        {"user": address, "limit": limit},
        {"maker": address, "limit": limit},
        {"taker": address, "limit": limit},
        {"address": address, "limit": limit},
    ]

    trades: List[Dict[str, Any]] = []
    for params in candidate_params:
        try:
            payload = http_get_json("/trades", params)
        except Exception:
            continue

        if isinstance(payload, list):
            trades = payload
        elif isinstance(payload, dict):
            trades = payload.get("data") or payload.get("trades") or []

        if trades:
            break

    normalized = [normalize_trade(t, address) for t in trades]
    return [t for t in normalized if t is not None]


def upsert_profile(conn: sqlite3.Connection, address: str, profile: Dict[str, Any]) -> None:
    conn.execute(
        """
        INSERT INTO traders (
            address, username, display_name, profile_image, bio,
            follower_count, following_count, volume_traded, last_profile_sync
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(address) DO UPDATE SET
            username=excluded.username,
            display_name=excluded.display_name,
            profile_image=excluded.profile_image,
            bio=excluded.bio,
            follower_count=excluded.follower_count,
            following_count=excluded.following_count,
            volume_traded=excluded.volume_traded,
            last_profile_sync=excluded.last_profile_sync
        """,
        (
            address,
            profile.get("username") or profile.get("handle"),
            profile.get("displayName") or profile.get("name"),
            profile.get("profileImage") or profile.get("profilePicture"),
            profile.get("bio"),
            profile.get("followerCount"),
            profile.get("followingCount"),
            profile.get("volumeTraded") or profile.get("volume"),
            datetime.now(timezone.utc).isoformat(),
        ),
    )


def insert_trades(conn: sqlite3.Connection, trades: Iterable[Dict[str, Any]]) -> int:
    count = 0
    for trade in trades:
        cursor = conn.execute(
            """
            INSERT OR IGNORE INTO trades (
                trade_id, trader_address, market_slug, market_question,
                outcome, side, price, size, amount, token_id,
                tx_hash, timestamp, raw_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                trade["trade_id"],
                trade["trader_address"],
                trade["market_slug"],
                trade["market_question"],
                trade["outcome"],
                trade["side"],
                trade["price"],
                trade["size"],
                trade["amount"],
                trade["token_id"],
                trade["tx_hash"],
                trade["timestamp"],
                trade["raw_json"],
            ),
        )
        if cursor.rowcount == 1:
            count += 1
    return count


def run_sync(config_path: Path) -> None:
    addresses = load_tracked_traders(config_path)
    conn = get_connection()

    total_inserted = 0
    for address in addresses:
        profile = try_profile(address)
        upsert_profile(conn, address, profile)

        trades = fetch_trades_for_address(address)
        inserted = insert_trades(conn, trades)
        total_inserted += inserted
        print(f"[{address}] fetched={len(trades)} inserted={inserted}")

    conn.commit()
    conn.close()
    print(f"Sync complete. Inserted {total_inserted} new trades.")


def main():
    parser = argparse.ArgumentParser(description="Fetch and store tracked Polymarket trades")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="Path to tracked_traders.json")
    parser.add_argument(
        "--loop",
        action="store_true",
        help="Run continuously, syncing once per minute",
    )
    args = parser.parse_args()

    config_path = Path(args.config).resolve()
    init_db()

    if args.loop:
        while True:
            try:
                run_sync(config_path)
            except Exception as exc:
                print(f"Sync failed: {exc}")
            time.sleep(60)
    else:
        run_sync(config_path)


if __name__ == "__main__":
    main()
