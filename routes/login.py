from fastapi import APIRouter, HTTPException, Depends, Response
from pydantic import BaseModel, Field
from passlib.context import CryptContext
from DbConnection import get_db
from starlette.status import HTTP_200_OK
import logging

router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class LoginRequest(BaseModel):
    username_or_email: str
    password: str = Field(..., min_length=8)

class LoginResponse(BaseModel):
    user_id: str
    username: str

@router.post("/login", response_model=LoginResponse, status_code=HTTP_200_OK)
async def login_user(request: LoginRequest, response: Response, db=Depends(get_db)):
    try:
        user = await db.users.find_one({"$or": [{"username": request.username_or_email}, {"email": request.username_or_email}]})
        if not user or not pwd_context.verify(request.password, user["password"]):
            raise HTTPException(status_code=400, detail="Invalid credentials.")
        
        response.set_cookie(key="user_id", value=user["user_id"], httponly=True, secure=True)
        return LoginResponse(user_id=user["user_id"], username=user["username"])
    except Exception as e:
        logging.error(f"Error logging in user: {e}")
        raise HTTPException(status_code=500, detail="An internal server error occurred")
