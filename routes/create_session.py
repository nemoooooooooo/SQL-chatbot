from pydantic import BaseModel, UUID4, validator
from typing import Optional
from fastapi import HTTPException, Depends, APIRouter
import logging
from DbConnection import get_db
from pymongo.errors import ConnectionFailure, PyMongoError, OperationFailure
from datetime import datetime
import uuid
from session_manager import session_manager
from agent_manager import agent_manager

router = APIRouter()

class CreateSessionRequest(BaseModel):
    user_id: UUID4
    session_name: Optional[str] = "New Chat"
    agent_id: str

    @validator('session_name')
    def name_must_not_be_empty(cls, v):
        if v.strip() == "":
            raise ValueError('Session name must not be an empty string.')
        return v

class CreateSessionResponse(BaseModel):
    session_id: str
    session_name: str
    created_at: datetime
    last_used: datetime

logging.basicConfig(filename='error.log', level=logging.ERROR)

@router.post("/create_session", response_model=CreateSessionResponse)
async def create_session(request: CreateSessionRequest, db=Depends(get_db)) -> CreateSessionResponse:
    try:
        user = await db.users.find_one({"user_id": str(request.user_id)})
        if not user:
            logging.error(f"User {request.user_id} not found.")
            raise HTTPException(status_code=400, detail="User not found.")

        agent = agent_manager.get_agent(request.agent_id)
        if not agent:
            logging.error(f"Agent {request.agent_id} not found.")
            raise HTTPException(status_code=400, detail="Agent not found.")

        session_id = str(uuid.uuid4())
        
        # Ensure no duplicate session ID for the agent of the user
        existing_sessions = user.get("sessions", [])
        if any(session["session_id"] == session_id and session["agent_id"] == request.agent_id for session in existing_sessions):
            logging.error(f"Session ID {session_id} already exists for agent {request.agent_id} and user {request.user_id}.")
            raise HTTPException(status_code=400, detail="Session ID already exists for agent and user.")

        session_name = request.session_name
        current_time = datetime.utcnow()

        new_session = {
            "session_id": session_id,
            "session_name": session_name,
            "created_at": current_time,
            "last_used": current_time,
            "agent_id": request.agent_id
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

        # Store the session in an in-memory dictionary or cache
        session_manager.add_session(session_id, request.agent_id)

        return CreateSessionResponse(
            session_id=session_id,
            session_name=session_name,
            created_at=current_time,
            last_used=current_time
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
