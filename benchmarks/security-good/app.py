"""Security best practices — no hardcoded secrets, parameterized queries, input validation."""
import os
import hashlib
import secrets

class SecureApp:
    def __init__(self, db):
        self.db = db
        self.secret_key = os.environ.get("SECRET_KEY")  # From env, not hardcoded
    
    def hash_password(self, password: str) -> str:
        salt = secrets.token_bytes(32)
        return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000).hex() + salt.hex()
    
    def verify_password(self, password: str, stored: str) -> bool:
        salt = bytes.fromhex(stored[64:])
        hash_val = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000).hex()
        return hash_val == stored[:64]
    
    def get_user(self, user_id: int):
        # Parameterized query — prevents SQL injection
        return self.db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    
    def validate_input(self, data: dict) -> bool:
        required = ["username", "email"]
        return all(k in data and isinstance(data[k], str) and len(data[k]) < 255 for k in required)
