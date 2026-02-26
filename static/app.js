const traderListEl = document.getElementById("trader-list");
const tradeListEl = document.getElementById("trade-list");
const tradeTitleEl = document.getElementById("trade-title");

let selectedAddress = null;

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json();
}

function traderCard(trader) {
  const name = trader.display_name || trader.username || trader.address;
  const image = trader.profile_image || "";
  return `
    <article class="trader-card ${selectedAddress === trader.address ? "active" : ""}" data-address="${escapeHtml(trader.address)}">
      <div class="profile">
        <img src="${escapeHtml(image)}" alt="${escapeHtml(name)} profile" onerror="this.style.display='none'" />
        <div>
          <strong>${escapeHtml(name)}</strong>
          <div class="meta">@${escapeHtml(trader.username || "unknown")}</div>
        </div>
      </div>
      <p class="meta">${escapeHtml(trader.bio || "No bio")}</p>
      <p class="meta">Trades: ${trader.trade_count || 0} • Followers: ${trader.follower_count || 0}</p>
      <p class="meta">Volume: ${trader.volume_traded || 0} • Last trade: ${escapeHtml(trader.latest_trade || "N/A")}</p>
      <p class="meta">${escapeHtml(trader.address)}</p>
    </article>
  `;
}

function tradeRow(trade) {
  return `
    <article class="trade-row">
      <h4>${escapeHtml(trade.market_question || trade.market_slug || "Unknown market")}</h4>
      <div class="trade-grid">
        <div><strong>Outcome</strong><br/>${escapeHtml(trade.outcome || "N/A")}</div>
        <div><strong>Side</strong><br/>${escapeHtml(trade.side || "N/A")}</div>
        <div><strong>Price</strong><br/>${escapeHtml(trade.price || "N/A")}</div>
        <div><strong>Size</strong><br/>${escapeHtml(trade.size || trade.amount || "N/A")}</div>
        <div><strong>Amount</strong><br/>${escapeHtml(trade.amount || "N/A")}</div>
        <div><strong>Token</strong><br/>${escapeHtml(trade.token_id || "N/A")}</div>
        <div><strong>Time</strong><br/>${escapeHtml(trade.timestamp || "N/A")}</div>
        <div><strong>Tx</strong><br/>${escapeHtml(trade.tx_hash || "N/A")}</div>
      </div>
    </article>
  `;
}

async function loadTraders() {
  const traders = await fetchJson("/api/traders");
  if (traders.length === 0) {
    traderListEl.innerHTML = `<p class="empty">No traders found yet. Run fetch_trades.py first.</p>`;
    tradeListEl.innerHTML = "";
    return;
  }

  if (!selectedAddress) {
    selectedAddress = traders[0].address;
  }

  traderListEl.innerHTML = traders.map(traderCard).join("");

  for (const card of document.querySelectorAll(".trader-card")) {
    card.addEventListener("click", () => {
      selectedAddress = card.dataset.address;
      loadTraders().catch(console.error);
    });
  }

  await loadTrades(selectedAddress, traders);
}

async function loadTrades(address, traders = null) {
  const knownTraders = traders || (await fetchJson("/api/traders"));
  const selected = knownTraders.find((t) => t.address === address);
  const title = selected?.display_name || selected?.username || address;
  tradeTitleEl.textContent = `Trades • ${title}`;

  const trades = await fetchJson(`/api/traders/${address}/trades`);
  if (trades.length === 0) {
    tradeListEl.innerHTML = `<p class="empty">No trades for this trader yet.</p>`;
    return;
  }

  tradeListEl.innerHTML = trades.map(tradeRow).join("");
}

loadTraders().catch((error) => {
  console.error(error);
  traderListEl.innerHTML = `<p class="empty">Failed to load traders.</p>`;
});
