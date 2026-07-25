"""Adapter — concrete implementation of port."""
from src.ports.user_repository import UserRepositoryPort
from src.domain.user import User

class DbUserRepository(UserRepositoryPort):
    def __init__(self, db):
        self.db = db
    
    def get_by_id(self, user_id: int) -> User:
        row = self.db.query("SELECT * FROM users WHERE id=?", user_id)
        return User(**row) if row else None
    
    def save(self, user: User) -> User:
        self.db.execute("INSERT INTO users VALUES(?,?)", user.id, user.email)
        return user
