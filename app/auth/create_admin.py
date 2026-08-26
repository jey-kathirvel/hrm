import getpass, os
from app.config.database import SessionLocal
from app.auth.models import User
from app.auth.service import hash_password

def main():
    email=(os.getenv("ADMIN_EMAIL") or input("Admin email: ")).strip().lower()
    password=os.getenv("ADMIN_PASSWORD") or getpass.getpass("Admin password: ")
    if len(password)<10: raise SystemExit("Password must be at least 10 characters")
    db=SessionLocal()
    try:
        if db.query(User).filter(User.email==email).first(): raise SystemExit("Admin already exists")
        db.add(User(email=email,password_hash=hash_password(password))); db.commit(); print(f"Created admin: {email}")
    finally: db.close()
if __name__=="__main__": main()
