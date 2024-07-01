# -*- coding: utf-8 -*-
"""
Created on Thu Jun 13 02:23:21 2024

@author: Nimra Noor
"""


from pydantic import BaseModel, UUID4
from fastapi import HTTPException, Depends
import logging
from DbConnection import get_db
from pymongo.errors import ConnectionFailure, PyMongoError, OperationFailure
from fastapi import APIRouter
from session_manager import session_manager



router = APIRouter()


class DeleteSessionRequest(BaseModel):
    user_id: UUID4
    session_id: str

class DeleteSessionResponse(BaseModel):
    session_id: str
    deleted: bool

@router.post("/delete_session", response_model=DeleteSessionResponse)
async def delete_session(request: DeleteSessionRequest, db=Depends(get_db)) -> DeleteSessionResponse:
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
        
        result = await db.users.update_one(
            {"user_id": str(request.user_id)},
            {
                "$pull": {
                    "sessions": {"session_id": request.session_id}
                }
            }
        )

        if result.modified_count == 0:
            logging.error(f"Failed to delete session {request.session_id} for user {request.user_id}.")
            raise ValueError("Failed to delete session.")
            
        if session_manager.get_session(request.session_id):
            session_manager.remove_session(request.session_id)

        return DeleteSessionResponse(
            session_id=request.session_id,
            deleted=True
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
