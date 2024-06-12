# -*- coding: utf-8 -*-
"""
Created on Sat Oct  7 23:35:51 2023

@author: Nimra Noor
"""

from pydantic import BaseModel, UUID4
from typing import Optional
from fastapi import HTTPException, Depends
import logging
from DbConnection import get_db
from pymongo.errors import ConnectionFailure, PyMongoError, OperationFailure
from fastapi import APIRouter
import re

router = APIRouter()




class UpdateKeyRequest(BaseModel):
    openai_key: Optional[str] = None  
    fireworks_key: Optional[str] = None
    user_id: UUID4


class UpdateKeyResponse(BaseModel):
    key_updated: bool

logging.basicConfig(filename='error.log', level=logging.ERROR)


@router.post("/update_api_key", response_model=UpdateKeyResponse)
async def update_api_key(request: UpdateKeyRequest, db=Depends(get_db)) -> UpdateKeyResponse:
    try:
 
        user_exists = await db.users.find_one({"user_id": str(request.user_id)})
        if not user_exists:
            logging.error(f"{request.user_id} not found.")
            raise ValueError("User not found.")

        if request.openai_key is None and request.fireworks_key is None:
            logging.error("At least one API key must be provided.")
            raise ValueError("No API key provided.")

        if request.openai_key and not re.match("^sk-[a-zA-Z0-9]{48}$", request.openai_key):
            logging.error(f"Invalid OpenAI key format for user {request.user_id}.")
            raise ValueError("Invalid OpenAI key format.")
            
        # Validate Fireworks key format
        if request.fireworks_key and not re.match("^[a-zA-Z0-9]{48}$", request.fireworks_key):
            logging.error(f"Invalid Fireworks key format for user {request.user_id}.")
            raise ValueError("Invalid Fireworks key format.")
                
            
        # Attempt to update the database
        result = await db.API_keys.update_one(
            {"user_id": str(request.user_id)},
            {
                "$set": {
                    "openai_key": request.openai_key,
                    "fireworks_key": request.fireworks_key
                }
            },
            upsert=True
        )

        # Check the update/insert result
        if not result.modified_count and not result.upserted_id:
            error_message = f"Duplicate key error for user {request.user_id}."
            logging.error(error_message)
            raise ValueError(error_message)


        return UpdateKeyResponse(key_updated=bool(result.modified_count or result.upserted_id))

            
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








