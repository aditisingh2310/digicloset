from pydantic import BaseModel, EmailStr
from typing import Optional, List
import datetime

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: int
    email: EmailStr
    is_active: bool
    created_at: datetime.datetime

    class Config:
        orm_mode = True

class UploadCreate(BaseModel):
    filename: str
    content_type: Optional[str]

class UploadOut(BaseModel):
    id: int
    filename: str
    content_type: Optional[str]
    s3_key: Optional[str]
    created_at: datetime.datetime

    class Config:
        orm_mode = True
