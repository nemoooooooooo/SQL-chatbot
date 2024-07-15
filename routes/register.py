from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr, Field
from uuid import uuid4
from passlib.context import CryptContext
from DbConnection import get_db
import logging

router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=20)
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)

class RegisterResponse(BaseModel):
    user_id: str
    username: str
    email: str

@router.post("/register", response_model=RegisterResponse)
async def register_user(request: RegisterRequest, db=Depends(get_db)):
    try:
        existing_user = await db.users.find_one({"$or": [{"username": request.username}, {"email": request.email}]})
        if existing_user:
            raise HTTPException(status_code=400, detail="Username or email already exists.")
        
        user_id = str(uuid4())
        hashed_password = pwd_context.hash(request.password)
        user = {
            "user_id": user_id,
            "username": request.username,
            "first_name": request.first_name,
            "last_name": request.last_name,
            "email": request.email,
            "password": hashed_password
        }
        await db.users.insert_one(user)
        return RegisterResponse(user_id=user_id, username=request.username, email=request.email)
    except Exception as e:
        logging.error(f"Error registering user: {e}")
        raise HTTPException(status_code=500, detail=f"An error occurred: {e}")
