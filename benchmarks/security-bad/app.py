"""Security vulnerabilities — hardcoded password, SQL injection, weak hashing."""

class InsecureApp:
    DB_PASSWORD = "super_secret_123"  # Hardcoded secret
    API_KEY = "sk-1234567890abcdef"  # Hardcoded API key
    
    def __init__(self, db):
        self.db = db
    
    def login(self, username, password):
        # SQL injection vulnerability — string concatenation
        query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
        return self.db.execute(query)
    
    def hash_password(self, password):
        # Weak hashing — MD5
        import hashlib
        return hashlib.md5(password.encode()).hexdigest()
    
    def eval_user_input(self, user_input):
        # Code injection — eval
        return eval(user_input)
    
    def get_config(self):
        # Exposes secrets in config
        return {
            "db_password": self.DB_PASSWORD,
            "api_key": self.API_KEY,
            "debug": True
        }
