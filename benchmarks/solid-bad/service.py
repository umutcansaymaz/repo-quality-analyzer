"""SOLID violations — multiple responsibilities, no abstraction, tight coupling."""

class UserService:
    """Violates SRP, OCP, DIP — does everything itself."""
    def __init__(self):
        import sqlite3
        self.db = sqlite3.connect(":memory:")
        self.db.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT, email TEXT)")
        self.db.commit()
    
    def register(self, username, email):
        # Validation logic (should be separate)
        if len(username) < 3:
            raise ValueError("Username too short")
        if "@" not in email:
            raise ValueError("Invalid email")
        
        # DB access (should use repository)
        cursor = self.db.execute("INSERT INTO users (username, email) VALUES (?, ?)", username, email)
        self.db.commit()
        
        # Email sending (should use abstraction)
        import smtplib
        try:
            server = smtplib.SMTP("localhost", 25)
            server.sendmail("noreply@example.com", email, "Welcome!")
            server.quit()
        except:
            pass
        
        # Logging (should use logger abstraction)
        print(f"User registered: {username}")
        
        return cursor.lastrowid
    
    def send_notification(self, user_id, message):
        # Notification logic in user service (violates SRP)
        user = self.db.execute("SELECT * FROM users WHERE id = ?", user_id).fetchone()
        if user:
            print(f"Notification to {user[1]}: {message}")
    
    def delete_user(self, user_id):
        self.db.execute("DELETE FROM users WHERE id = ?", user_id)
        self.db.commit()
        print(f"User {user_id} deleted")
