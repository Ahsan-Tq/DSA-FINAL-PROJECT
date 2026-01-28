from typing import Optional, Dict

from auth_db import ensure_seeded_accounts, get_user_by_username, create_user_with_wallet
from security import hash_password, issue_token, verify_password


def _ensure_seeded():
    def create_user(username: str, role: str, initial_balance: float):
        if username == "demo_user":
            plain = "demo123"
        elif username == "tester":
            plain = "tester123"
        else:
            plain = "change_me"
        ph = hash_password(plain)
        created = create_user_with_wallet(username, ph, role, float(initial_balance))
        created["seed_password"] = plain
        return created

    return ensure_seeded_accounts(create_user)


def check_credentials(username: str, password: str, users: Optional[Dict[str, str]] = None) -> bool:
    if users is not None:
        username = (username or "").strip()
        password = (password or "").strip()
        return username in users and users[username] == password
    _ensure_seeded()
    u = get_user_by_username((username or "").strip())
    if u is None:
        return False
    return verify_password(password or "", u["password_hash"])


def login_token(username: str, password: str) -> dict:
    _ensure_seeded()
    u = get_user_by_username((username or "").strip())
    if u is None:
        return {"ok": False, "error": "Invalid credentials"}
    if not verify_password(password or "", u["password_hash"]):
        return {"ok": False, "error": "Invalid credentials"}
    token = issue_token(u["id"], u["username"], u["role"])
    return {"ok": True, "token": token, "role": u["role"], "username": u["username"]}


def login():
    username = input("Enter username: ").strip()
    password = input("Enter password: ").strip()
    res = login_token(username, password)
    if res.get("ok"):
        print("Login successful!")
        return res.get("token")
    print(res.get("error", "Login failed"))
    return False
