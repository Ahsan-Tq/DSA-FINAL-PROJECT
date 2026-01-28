import sqlite3
import secrets

from database import DB_NAME


def _connect():
    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def ensure_auth_schema():
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS wallets (
            wallet_address TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL UNIQUE,
            balance REAL NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )
    conn.commit()
    conn.close()

def get_all_usernames():
    conn = _connect()
    cur = conn.cursor()
    cur.execute("SELECT username FROM users")
    rows = cur.fetchall()
    conn.close()
    return [r[0] for r in rows]


def count_users():
    conn = _connect()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users")
    n = int(cur.fetchone()[0])
    conn.close()
    return n


def get_user_by_username(username: str):
    conn = _connect()
    cur = conn.cursor()
    cur.execute("SELECT id, username, password_hash, role FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    conn.close()
    if row is None:
        return None
    return {"id": row[0], "username": row[1], "password_hash": row[2], "role": row[3]}


def get_user_by_id(user_id: int):
    conn = _connect()
    cur = conn.cursor()
    cur.execute("SELECT id, username, password_hash, role FROM users WHERE id = ?", (int(user_id),))
    row = cur.fetchone()
    conn.close()
    if row is None:
        return None
    return {"id": row[0], "username": row[1], "password_hash": row[2], "role": row[3]}


def _wallet_exists(conn, wallet_address: str) -> bool:
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM wallets WHERE wallet_address = ?", (wallet_address,))
    return cur.fetchone() is not None


def _generate_wallet_address(conn) -> str:
    for _ in range(100):
        addr = secrets.token_hex(16)
        if not _wallet_exists(conn, addr):
            return addr
    raise RuntimeError("Could not generate unique wallet address")


def generate_wallet_address() -> str:
    conn = _connect()
    try:
        return _generate_wallet_address(conn)
    finally:
        conn.close()


def create_user_with_wallet(username: str, password_hash: str, role: str, initial_balance: float):
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            (username, password_hash, role),
        )
        user_id = cur.lastrowid
        wallet_address = _generate_wallet_address(conn)
        cur.execute(
            "INSERT INTO wallets (wallet_address, user_id, balance) VALUES (?, ?, ?)",
            (wallet_address, user_id, float(initial_balance)),
        )
        conn.commit()
        return {"id": user_id, "username": username, "role": role, "wallet_address": wallet_address, "balance": float(initial_balance)}
    finally:
        conn.close()


def get_wallet_by_user_id(user_id: int):
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        "SELECT wallet_address, user_id, balance FROM wallets WHERE user_id = ?",
        (int(user_id),),
    )
    row = cur.fetchone()
    conn.close()
    if row is None:
        return None
    return {"wallet_address": row[0], "user_id": row[1], "balance": float(row[2])}


def get_wallet_by_address(wallet_address: str):
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        "SELECT wallet_address, user_id, balance FROM wallets WHERE wallet_address = ?",
        (wallet_address,),
    )
    row = cur.fetchone()
    conn.close()
    if row is None:
        return None
    return {"wallet_address": row[0], "user_id": row[1], "balance": float(row[2])}

def find_wallet_addresses_by_username_query(query: str):
    q = (query or "").strip().lower()
    if not q:
        return []
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT w.wallet_address
        FROM users u
        JOIN wallets w ON w.user_id = u.id
        WHERE lower(u.username) LIKE ?
        """,
        ("%" + q + "%",),
    )
    rows = cur.fetchall()
    conn.close()
    return [r[0] for r in rows]


def transfer_balance(sender_user_id: int, receiver_wallet_address: str, amount: float) -> dict:
    conn = _connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        cur = conn.cursor()
        cur.execute("SELECT wallet_address, balance FROM wallets WHERE user_id = ?", (int(sender_user_id),))
        sender_row = cur.fetchone()
        if sender_row is None:
            conn.rollback()
            return {"ok": False, "error": "Sender wallet not found"}
        sender_wallet, sender_balance = sender_row[0], float(sender_row[1])

        cur.execute("SELECT user_id, balance FROM wallets WHERE wallet_address = ?", (receiver_wallet_address,))
        receiver_row = cur.fetchone()
        if receiver_row is None:
            conn.rollback()
            return {"ok": False, "error": "Receiver wallet not found"}
        receiver_user_id, receiver_balance = int(receiver_row[0]), float(receiver_row[1])

        if amount <= 0:
            conn.rollback()
            return {"ok": False, "error": "Amount must be positive"}
        if sender_balance < amount:
            conn.rollback()
            return {"ok": False, "error": "Insufficient balance"}
        if receiver_user_id == int(sender_user_id):
            conn.rollback()
            return {"ok": False, "error": "Cannot send to your own wallet"}

        new_sender_balance = sender_balance - float(amount)
        new_receiver_balance = receiver_balance + float(amount)

        cur.execute("UPDATE wallets SET balance = ? WHERE user_id = ?", (new_sender_balance, int(sender_user_id)))
        cur.execute("UPDATE wallets SET balance = ? WHERE wallet_address = ?", (new_receiver_balance, receiver_wallet_address))
        conn.commit()
        return {
            "ok": True,
            "sender_wallet_address": sender_wallet,
            "receiver_wallet_address": receiver_wallet_address,
            "sender_balance": float(new_sender_balance),
            "receiver_balance": float(new_receiver_balance),
        }
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()


def reverse_transfer(sender_user_id: int, receiver_wallet_address: str, amount: float):
    conn = _connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        cur = conn.cursor()
        cur.execute("SELECT balance FROM wallets WHERE user_id = ?", (int(sender_user_id),))
        s = cur.fetchone()
        cur.execute("SELECT balance FROM wallets WHERE wallet_address = ?", (receiver_wallet_address,))
        r = cur.fetchone()
        if s is None or r is None:
            conn.rollback()
            return
        sender_balance = float(s[0])
        receiver_balance = float(r[0])
        cur.execute("UPDATE wallets SET balance = ? WHERE user_id = ?", (sender_balance + float(amount), int(sender_user_id)))
        cur.execute("UPDATE wallets SET balance = ? WHERE wallet_address = ?", (receiver_balance - float(amount), receiver_wallet_address))
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
    finally:
        conn.close()


def ensure_seeded_accounts(create_user_fn, extra_users: int = 10, extra_balance: float = 100_000.0, extra_password_plain: str = "password123"):
    ensure_auth_schema()
    demo = get_user_by_username("demo_user")
    tester = get_user_by_username("tester")
    created = {}
    if demo is None:
        created["demo_user"] = create_user_fn("demo_user", "user", 1_000_000.0)
    if tester is None:
        created["tester"] = create_user_fn("tester", "tester", 0.0)
    existing = set(get_all_usernames())
    existing.discard("demo_user")
    existing.discard("tester")
    need = int(extra_users) - len(existing)
    if need > 0:
        from security import hash_password

        first_names = [
            "Ali",
            "Ahmed",
            "Hassan",
            "Hussain",
            "Usman",
            "Bilal",
            "Hamza",
            "Imran",
            "Ayesha",
            "Fatima",
            "Zainab",
            "Maryam",
            "Sana",
            "Hira",
            "Sara",
            "Umar",
            "Saad",
            "Fahad",
            "Asad",
            "Arslan",
        ]
        last_names = [
            "Khan",
            "Malik",
            "Sheikh",
            "Butt",
            "Raza",
            "Iqbal",
            "Javed",
            "Chaudhry",
            "Syed",
            "Nawaz",
            "Abbasi",
            "Qureshi",
            "Mirza",
            "Siddiqui",
        ]
        all_usernames = set(get_all_usernames())
        for _ in range(need):
            base = (secrets.choice(first_names) + "_" + secrets.choice(last_names)).lower()
            candidate = base
            suffix = 1
            while candidate in all_usernames:
                suffix += 1
                candidate = f"{base}{suffix}"
            ph = hash_password(extra_password_plain)
            u = create_user_with_wallet(candidate, ph, "user", float(extra_balance))
            u["seed_password"] = extra_password_plain
            created[candidate] = u
            all_usernames.add(candidate)
    return created

