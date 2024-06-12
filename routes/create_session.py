from pydantic import BaseModel, UUID4, validator
from typing import Optional
from fastapi import HTTPException, Depends
import logging
from DbConnection import get_db
from pymongo.errors import ConnectionFailure, PyMongoError, OperationFailure
from fastapi import APIRouter
from datetime import datetime
import uuid

router = APIRouter()

class CreateSessionRequest(BaseModel):
    user_id: UUID4
    session_name: Optional[str] = "New Chat"

    @validator('session_name')
    def name_must_not_be_empty(cls, v):
        if v.strip() == "":
            raise ValueError('Session name must not be an empty string.')
        return v

class CreateSessionResponse(BaseModel):
    session_id: str
    session_name: str
    created_at: datetime
    last_modified: datetime

logging.basicConfig(filename='error.log', level=logging.ERROR)

@router.post("/create_session", response_model=CreateSessionResponse)
async def create_session(request: CreateSessionRequest, db=Depends(get_db)) -> CreateSessionResponse:
    try:
        user = await db.users.find_one({"user_id": str(request.user_id)})
        if not user:
            logging.error(f"User {request.user_id} not found.")
            raise HTTPException(status_code=400, detail="User not found.")

        session_id = str(uuid.uuid4())
        session_name = request.session_name
        current_time = datetime.utcnow()

        new_session = {
            "session_id": session_id,
            "session_name": session_name,
            "created_at": current_time,
            "last_modified": current_time  # Initialize with the creation time
        }

        result = await db.users.update_one(
            {"user_id": str(request.user_id)},
            {
                "$push": {
                    "sessions": new_session
                }
            }
        )

        if result.modified_count == 0:
            logging.error(f"Failed to create session for user {request.user_id}.")
            raise HTTPException(status_code=500, detail="Failed to create session.")

        return CreateSessionResponse(
            session_id=session_id,
            session_name=session_name,
            created_at=current_time,
            last_modified=current_time  # Return the initial value
        )
        
    except ConnectionFailure:
        logging.error(f"Database connection error for user {request.user_id}.")
        raise HTTPException(status_code=500, detail="Database connection error.")
    except PyMongoError as pe:
        logging.error(f"Database error for user {request.user_id}: {pe}")
        raise HTTPException(status_code=500, detail=f"Database error: {pe}")
    except OperationFailure as ofe:
        logging.error(f"Database operation error for user {request.user_id}: {ofe}")
        raise HTTPException(status_code=500, detail=f"Database operation error: {ofe}")
    except ValueError as ve:
        logging.error(f"Value error for user {request.user_id}: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logging.error(f"An unexpected error occurred for user {request.user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")

