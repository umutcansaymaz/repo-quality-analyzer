"""User repository — data access layer."""
from src.models.user import User

class UserRepository:
    def __init__(self, db):
        self.db = db
    
    def get_by_id(self, user_id: int) -> User:
        row = self.db.query("SELECT * FROM users WHERE id = ?", user_id)
        return User(**row) if row else None
    
    def save(self, user: User) -> User:
        self.db.execute("INSERT INTO users VALUES (?, ?, ?, ?)", 
                        user.id, user.username, user.email, user.is_active)
        return user
