#!/usr/bin/env python3
"""
Polymarket Exit Monitor

Monitors selected Polymarket outcome combinations and sends a Telegram
alert when the sum of executable BID prices exceeds a threshold,
indicating a favorable opportunity to SELL existing positions.

Designed for traders who already hold positions.

Author: Ivan Hojman
"""

import os
import requests
from dotenv import load_dotenv

# Load .env locally (GitHub Actions will ignore this)
load_dotenv()

# ================= CONFIG =================

ORDERBOOK_URL = "https://clob.polymarket.com/book"

# Alert when bid_A + bid_B >= THRESHOLD
THRESHOLD = 1.01

# Telegram (from environment / GitHub secrets)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# ================= MARKETS =================

TOKENS = {
    "CUT25": {
        "YES": "92703761682322480664976766247614127878023988651992837287050266308961660624165",
        "NO":  "48193521645113703700467246669338225849301704920590102230072263970163239985027",
    },
    "CUTCUTCUT": {
        "YES": "95417221270011105499568468828531867453865533932484364685389046548264041887861",
        "NO":  "101322769768415942646735830228475566436146317671120615766292718518675772773223",
    },
    "NOCHANGE": {
        "YES": "112838095111461683880944516726938163688341306245473734071798778736646352193304",
        "NO":  "7321318078891059430231591636389479745928915782241484131001985601124919020061",
    },
    "CUTCUTPAUSE": {
        "YES": "113401754986342384261044700457165882158632153698445535217371023842472815025478",
        "NO":  "81906419701908530974011339985097627770048267181648886108185004759027261509242",
    }
}

# ===== CHOOSE POSITIONS YOU WANT TO SELL =====
# (marketA, legA, marketB, legB)
MONITORED_COMBOS = [
    ("CUT25", "YES", "CUTCUTPAUSE", "YES"),
    ("NOCHANGE", "YES", "CUTCUTCUT", "YES"),
]

# ================= HELPERS =================

def safe_float(x):
    try:
        return float(x)
    except Exception:
        return None

def telegram_send(msg):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Telegram not configured")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": msg,
        "parse_mode": "HTML"
    }

    try:
        requests.post(url, json=payload, timeout=6)
    except Exception as e:
        print("Telegram error:", e)

def fetch_orderbook(token_id):
    try:
        r = requests.get(
            ORDERBOOK_URL,
            params={"token_id": token_id},
            timeout=6
        )
        r.raise_for_status()
        return r.json()
    except Exception:
        return None

def best_bid(token_id):
    raw = fetch_orderbook(token_id)
    if not raw or "bids" not in raw:
        return None

    best = None
    for b in raw["bids"]:
        p = safe_float(b.get("price"))
        if p is not None and (best is None or p > best):
            best = p

    return best

# ================= CORE LOGIC =================

def scan_exit_opportunities():
    print("\n🔍 Polymarket EXIT monitor (using bids)\n")

    for mktA, legA, mktB, legB in MONITORED_COMBOS:
        tA = TOKENS[mktA][legA]
        tB = TOKENS[mktB][legB]

        bidA = best_bid(tA)
        bidB = best_bid(tB)

        if bidA is None or bidB is None:
            print(f"{mktA} {legA} / {mktB} {legB} → missing bids")
            continue

        total = bidA + bidB

        print(
            f"{mktA} {legA} + {mktB} {legB} "
            f"→ {bidA:.4f} + {bidB:.4f} = {total:.4f}"
        )

        if total >= THRESHOLD:
            msg = (
                f"💰 <b>EXIT OPPORTUNITY</b>\n\n"
                f"{mktA} {legA} + {mktB} {legB}\n"
                f"Bid sum: <b>{total:.4f}</b>\n"
                f"Threshold: {THRESHOLD:.2f}\n\n"
                f"Consider selling both positions."
            )
            telegram_send(msg)
            print("🚨 Alert sent")

# ================= MAIN =================

if __name__ == "__main__":
    try:
        scan_exit_opportunities()
    except Exception as e:
        telegram_send(f"❌ Exit monitor crashed:\n{e}")
        raise
