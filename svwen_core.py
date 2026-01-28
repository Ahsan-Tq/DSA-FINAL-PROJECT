import hashlib
import io
from contextlib import redirect_stdout
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Optional, Dict, Any, List

from blockchain import Blockchain
from auth_db import (
    ensure_seeded_accounts,
    get_user_by_id,
    get_user_by_username,
    get_wallet_by_user_id,
    find_wallet_addresses_by_username_query,
    transfer_balance,
    reverse_transfer,
)
from security import hash_password, issue_token, verify_password, verify_token


def _capture(fn, *args, **kwargs):
    buf = io.StringIO()
    with redirect_stdout(buf):
        result = fn(*args, **kwargs)
    return result, buf.getvalue()


def _parse_kv_pipe(data: str) -> dict:
    out = {}
    parts = (data or "").split("|")
    for p in parts:
        p = p.strip()
        if "=" in p:
            k, v = p.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def _amount_to_decimal(amount) -> Decimal:
    if isinstance(amount, Decimal):
        return amount
    if isinstance(amount, (int, float)):
        return Decimal(str(amount))
    return Decimal(str(amount).strip())


def _tx_hash(sender_wallet: str, receiver_wallet: str, amount_str: str, timestamp: str) -> str:
    payload = f"{sender_wallet}|{receiver_wallet}|{amount_str}|{timestamp}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True)
class Session:
    token: str
    username: str
    role: str


class SVWENLedger:
    """
    Local-library facade for the app.

    - No web server, no HTTP.
    - Uses SQLite for persistence (blockchain + users/wallets).
    """

    def __init__(self):
        self.blockchain = Blockchain()
        if self.blockchain.head is None:
            _capture(self.blockchain.create_genesis_block)
        self._seed_info = self._ensure_seeded()

    # --- auth / session ---

    def _ensure_seeded(self) -> dict:
        def create_user(username: str, role: str, initial_balance: float):
            if username == "demo_user":
                plain = "demo123"
            elif username == "tester":
                plain = "tester123"
            else:
                plain = "change_me"
            ph = hash_password(plain)
            from auth_db import create_user_with_wallet

            created = create_user_with_wallet(username, ph, role, float(initial_balance))
            created["seed_password"] = plain
            return created

        created = ensure_seeded_accounts(create_user)
        return created

    def seed_info(self) -> dict:
        return {"created": self._seed_info}

    def login(self, username: str, password: str) -> dict:
        user = get_user_by_username((username or "").strip())
        if user is None:
            return {"ok": False, "error": "Invalid credentials"}
        if not verify_password(password or "", user["password_hash"]):
            return {"ok": False, "error": "Invalid credentials"}
        token = issue_token(user["id"], user["username"], user["role"])
        return {"ok": True, "token": token, "role": user["role"], "username": user["username"]}

    def _require_token(self, token: str) -> Optional[Dict[str, Any]]:
        payload = verify_token(token or "")
        if payload is None:
            return None
        user = get_user_by_id(int(payload.get("uid", 0)))
        if user is None:
            return None
        if user["username"] != payload.get("usr") or user["role"] != payload.get("role"):
            return None
        wallet = get_wallet_by_user_id(user["id"])
        if wallet is None:
            return None
        return {"user": user, "wallet": wallet}

    def me(self, token: str) -> dict:
        ctx = self._require_token(token)
        if ctx is None:
            return {"ok": False, "error": "Unauthorized"}
        u = ctx["user"]
        w = ctx["wallet"]
        return {
            "ok": True,
            "id": u["id"],
            "username": u["username"],
            "role": u["role"],
            "wallet_address": w["wallet_address"],
            "balance": w["balance"],
        }

    # --- ledger operations ---

    def send_sol(self, token: str, receiver_wallet_address: str, amount) -> dict:
        ctx = self._require_token(token)
        if ctx is None:
            return {"ok": False, "error": "Unauthorized"}

        sender_user = ctx["user"]
        sender_wallet = ctx["wallet"]["wallet_address"]

        try:
            dec = _amount_to_decimal(amount)
        except (InvalidOperation, ValueError):
            return {"ok": False, "error": "Invalid amount"}

        if dec <= 0:
            return {"ok": False, "error": "Amount must be positive"}

        amount_str = format(dec.normalize(), "f")

        valid, _ = _capture(self.blockchain.verify_chain)
        if not valid:
            return {"ok": False, "error": "Blockchain integrity check failed"}

        t = transfer_balance(sender_user["id"], (receiver_wallet_address or "").strip(), float(dec))
        if not t.get("ok"):
            return {"ok": False, "error": t.get("error", "Transfer failed")}

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        txh = _tx_hash(sender_wallet, t["receiver_wallet_address"], amount_str, timestamp)
        data = (
            f"TxHash={txh} | From={sender_wallet} | To={t['receiver_wallet_address']} | "
            f"Amount={amount_str} | Type=TRANSFER | Time={timestamp}"
        )

        ok, out = _capture(self.blockchain.add_block, data)
        if not ok:
            reverse_transfer(sender_user["id"], t["receiver_wallet_address"], float(dec))
            return {"ok": False, "error": "Blockchain rejected transaction"}

        return {
            "ok": True,
            "tx_hash": txh,
            "sender_wallet_address": sender_wallet,
            "receiver_wallet_address": t["receiver_wallet_address"],
            "amount": float(dec),
            "timestamp": timestamp,
            "blockchain_output": out.strip(),
            "sender_balance": t["sender_balance"],
        }

    def send_sol_to_username(self, token: str, receiver_username: str, amount) -> dict:
        ctx = self._require_token(token)
        if ctx is None:
            return {"ok": False, "error": "Unauthorized"}
        ru = (receiver_username or "").strip()
        if not ru:
            return {"ok": False, "error": "Receiver username is required"}
        receiver_user = get_user_by_username(ru)
        if receiver_user is None:
            return {"ok": False, "error": "Receiver username not found"}
        receiver_wallet = get_wallet_by_user_id(receiver_user["id"])
        if receiver_wallet is None:
            return {"ok": False, "error": "Receiver wallet not found"}
        res = self.send_sol(token, receiver_wallet["wallet_address"], amount)
        if res.get("ok"):
            res["receiver_username"] = ru
        return res

    def my_transactions(self, token: str) -> dict:
        ctx = self._require_token(token)
        if ctx is None:
            return {"ok": False, "error": "Unauthorized"}
        wallet = ctx["wallet"]["wallet_address"]
        txs = []
        cur = self.blockchain.head
        while cur is not None:
            if cur.index != 0:
                parsed = _parse_kv_pipe(cur.data)
                if parsed.get("From") == wallet or parsed.get("To") == wallet:
                    txs.append(
                        {
                            "block_index": cur.index,
                            "block_hash": cur.current_hash,
                            "timestamp": cur.timestamp,
                            "tx": parsed,
                        }
                    )
            cur = cur.next
        return {"ok": True, "wallet_address": wallet, "transactions": txs}

    def search_transactions(self, token: str, query: str) -> dict:
        ctx = self._require_token(token)
        if ctx is None:
            return {"ok": False, "error": "Unauthorized"}
        q = (query or "").strip().lower()
        if not q:
            return {"ok": False, "error": "Query cannot be empty"}
        wallet = ctx["wallet"]["wallet_address"]
        matched_wallets = set(find_wallet_addresses_by_username_query(q))
        txs = []
        cur = self.blockchain.head
        while cur is not None:
            if cur.index != 0:
                parsed = _parse_kv_pipe(cur.data)
                if parsed.get("From") == wallet or parsed.get("To") == wallet:
                    hay = " ".join(
                        [
                            str(parsed.get("TxHash", "")),
                            str(parsed.get("From", "")),
                            str(parsed.get("To", "")),
                            str(parsed.get("Amount", "")),
                            str(parsed.get("Time", "")),
                            str(parsed.get("Type", "")),
                        ]
                    ).lower()
                    if q in hay or parsed.get("From") in matched_wallets or parsed.get("To") in matched_wallets:
                        txs.append(
                            {
                                "block_index": cur.index,
                                "block_hash": cur.current_hash,
                                "timestamp": cur.timestamp,
                                "tx": parsed,
                            }
                        )
            cur = cur.next
        return {"ok": True, "query": query, "transactions": txs}

    # --- tester tools ---

    def verify_blockchain(self, token: str) -> dict:
        ctx = self._require_token(token)
        if ctx is None:
            return {"ok": False, "error": "Unauthorized"}
        if ctx["user"]["role"] != "tester":
            return {"ok": False, "error": "Forbidden"}
        valid, out = _capture(self.blockchain.verify_chain)
        return {"ok": True, "valid": bool(valid), "output": out.strip()}

    def tamper_blockchain(self, token: str, index: int, new_data: str) -> dict:
        ctx = self._require_token(token)
        if ctx is None:
            return {"ok": False, "error": "Unauthorized"}
        if ctx["user"]["role"] != "tester":
            return {"ok": False, "error": "Forbidden"}
        try:
            idx = int(index)
        except Exception:
            return {"ok": False, "error": "Invalid index"}
        if idx == 0:
            return {"ok": False, "error": "Cannot tamper Genesis block"}
        nd = (new_data or "").strip()
        if not nd:
            return {"ok": False, "error": "Data cannot be empty"}
        block = self.blockchain.get_block_by_index(idx)
        if block is None:
            return {"ok": False, "error": "Block not found"}
        block.data = nd
        self.blockchain.is_valid = False
        return {"ok": True, "message": f"Block {idx} tampered. Run verify to see effect."}

    def integrity_status(self, token: str) -> dict:
        ctx = self._require_token(token)
        if ctx is None:
            return {"ok": False, "error": "Unauthorized"}
        if ctx["user"]["role"] != "tester":
            return {"ok": False, "error": "Forbidden"}
        return {"ok": True, "is_valid": bool(self.blockchain.is_valid)}


def activity_series_from_transactions(wallet_address: str, transactions: List[dict], limit: int = 18) -> List[float]:
    """
    Convert tx list from `my_transactions()` / `search_transactions()` into a
    small numeric series for the dashboard chart.
    """
    w = (wallet_address or "").strip()
    series: List[float] = []
    for t in (transactions or [])[-int(limit) :]:
        tx = (t or {}).get("tx") or {}
        try:
            amt = float(tx.get("Amount") or 0.0)
        except Exception:
            amt = 0.0
        direction = 1.0 if tx.get("To") == w else -1.0
        series.append(direction * amt)
    return series

