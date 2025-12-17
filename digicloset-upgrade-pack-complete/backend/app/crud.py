from sqlalchemy.orm import Session
from . import models, schemas
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

def create_user(db: Session, user: schemas.UserCreate):
    hashed = pwd_context.hash(user.password)
    db_user = models.User(email=user.email, hashed_password=hashed)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def create_upload(db: Session, owner_id: int, filename: str, content_type: str, s3_key: str = None):
    up = models.Upload(filename=filename, content_type=content_type, owner_id=owner_id, s3_key=s3_key)
    db.add(up)
    db.commit()
    db.refresh(up)
    return up
