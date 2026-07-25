class UserService:
    """God Object — does everything: user CRUD, auth, notifications, settings, DB access."""
    def __init__(self, db):
        self.db = db
    
    def create_user(self, username, email, password):
        user = {"username": username, "email": email, "password": self._hash(password)}
        self.db.save("users", user)
        self._send_welcome_email(email)
        self._create_default_settings(user["id"])
        return user
    
    def authenticate(self, username, password):
        user = self.db.find("users", username=username)
        if user and user["password"] == self._hash(password):
            return self._generate_token(user)
        return None
    
    def update_profile(self, user_id, **kwargs):
        user = self.db.get("users", user_id)
        user.update(kwargs)
        self.db.save("users", user)
        self._notify_profile_change(user)
        return user
    
    def delete_user(self, user_id):
        self.db.delete("users", user_id)
        self._cleanup_settings(user_id)
        self._send_farewell_email(user_id)
    
    def change_password(self, user_id, old_pw, new_pw):
        user = self.db.get("users", user_id)
        if user["password"] != self._hash(old_pw):
            raise ValueError("Invalid password")
        user["password"] = self._hash(new_pw)
        self.db.save("users", user)
        self._notify_password_change(user)
    
    def get_settings(self, user_id):
        return self.db.find("settings", user_id=user_id)
    
    def update_settings(self, user_id, **kwargs):
        settings = self.get_settings(user_id)
        settings.update(kwargs)
        self.db.save("settings", settings)
    
    def _hash(self, text):
        import hashlib
        return hashlib.sha256(text.encode()).hexdigest()
    
    def _send_welcome_email(self, email):
        pass
    
    def _create_default_settings(self, user_id):
        self.db.save("settings", {"user_id": user_id, "theme": "light"})
    
    def _generate_token(self, user):
        import jwt
        return jwt.encode({"user_id": user["id"]}, "secret", algorithm="HS256")
    
    def _notify_profile_change(self, user):
        pass
    
    def _cleanup_settings(self, user_id):
        self.db.delete("settings", user_id)
    
    def _send_farewell_email(self, user_id):
        pass
    
    def _notify_password_change(self, user):
        pass
