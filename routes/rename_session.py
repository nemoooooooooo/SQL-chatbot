# -*- coding: utf-8 -*-
"""
Created on Thu Jun 13 00:42:56 2024

@author: Nimra Noor
"""

from pydantic import BaseModel, UUID4, validator
from fastapi import HTTPException, Depends
import logging
from DbConnection import get_db
from pymongo.errors import ConnectionFailure, PyMongoError, OperationFailure
from datetime import datetime
from fastapi import APIRouter


router = APIRouter()


class RenameSessionRequest(BaseModel):
    user_id: UUID4
    session_id: str
    new_session_name: str
    
    @validator('new_session_name')
    def name_must_not_be_empty(cls, v):
        if v.strip() == "":
            raise ValueError('Session name must not be an empty string.')
        return v


class RenameSessionResponse(BaseModel):
    session_id: str
    new_session_name: str

@router.post("/rename_session", response_model=RenameSessionResponse)
async def rename_session(request: RenameSessionRequest, db=Depends(get_db)) -> RenameSessionResponse:
    try:
        user = await db.users.find_one({"user_id": str(request.user_id)})
        if not user:
            logging.error(f"User {request.user_id} not found.")
            raise ValueError("User not found.")

        session_found = False
        for session in user.get('sessions', []):
            if session['session_id'] == request.session_id:
                session_found = True
                break

        if not session_found:
            logging.error(f"Session {request.session_id} not found for user {request.user_id}.")
            raise ValueError("Session not found.")
        
        if not request.new_session_name.strip():
            logging.error("Session name must not be empty.")
            raise ValueError("Session name must not be empty.")
        
        result = await db.users.update_one(
            {"user_id": str(request.user_id), "sessions.session_id": request.session_id},
            {
                "$set": {
                    "sessions.$.session_name": request.new_session_name,
                    "sessions.$.last_modified": datetime.utcnow()
                }
            }
        )

        if result.modified_count == 0:
            logging.error(f"Failed to rename session {request.session_id} for user {request.user_id}.")
            raise ValueError("Failed to rename session.")

        return RenameSessionResponse(
            session_id=request.session_id,
            new_session_name=request.new_session_name
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