"""SOLID-compliant code — each class has single responsibility."""
from abc import ABC, abstractmethod

class NotificationSender(ABC):
    @abstractmethod
    def send(self, message: str, recipient: str): pass

class EmailSender(NotificationSender):
    def send(self, message: str, recipient: str):
        print(f"Email to {recipient}: {message}")

class UserValidator:
    @staticmethod
    def validate_email(email: str) -> bool:
        return "@" in email and "." in email
    
    @staticmethod
    def validate_username(username: str) -> bool:
        return len(username) >= 3

class UserRepository:
    def __init__(self, db):
        self.db = db
    def save(self, user_data: dict):
        self.db.save("users", user_data)

class UserRegistrationService:
    """Depends on abstractions (open/closed), injectable (dependency inversion)."""
    def __init__(self, repo: UserRepository, notifier: NotificationSender):
        self.repo = repo
        self.notifier = notifier
    
    def register(self, username: str, email: str):
        if not UserValidator.validate_username(username):
            raise ValueError("Invalid username")
        if not UserValidator.validate_email(email):
            raise ValueError("Invalid email")
        user = {"username": username, "email": email}
        self.repo.save(user)
        self.notifier.send("Welcome!", email)
        return user
