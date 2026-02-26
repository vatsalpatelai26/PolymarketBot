from flask import Flask, jsonify, render_template

from db import get_connection, init_db

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/traders")
def api_traders():
    conn = get_connection()
    traders = conn.execute(
        """
        SELECT
            t.address,
            COALESCE(t.username, t.display_name, t.address) as title,
            t.username,
            t.display_name,
            t.profile_image,
            t.bio,
            t.follower_count,
            t.following_count,
            t.volume_traded,
            t.last_profile_sync,
            COUNT(tr.trade_id) as trade_count,
            MAX(tr.timestamp) as latest_trade
        FROM traders t
        LEFT JOIN trades tr ON tr.trader_address = t.address
        GROUP BY t.address
        ORDER BY latest_trade DESC
        """
    ).fetchall()
    conn.close()
    return jsonify([dict(row) for row in traders])


@app.route("/api/traders/<address>/trades")
def api_trader_trades(address: str):
    conn = get_connection()
    trades = conn.execute(
        """
        SELECT
            trade_id,
            trader_address,
            market_slug,
            market_question,
            outcome,
            side,
            price,
            size,
            amount,
            token_id,
            tx_hash,
            timestamp
        FROM trades
        WHERE trader_address = ?
        ORDER BY timestamp DESC
        LIMIT 200
        """,
        (address.lower(),),
    ).fetchall()
    conn.close()
    return jsonify([dict(row) for row in trades])


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
