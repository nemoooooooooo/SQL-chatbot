from pydantic import BaseModel, UUID4, validator
from typing import Optional
from fastapi import HTTPException, Depends
import logging
from DbConnection import get_db
from pymongo.errors import ConnectionFailure, PyMongoError, OperationFailure
from fastapi import APIRouter
from datetime import datetime
import uuid
import re
from agent_manager import agent_manager
from CONTROL_VAR import llm_api_key


router = APIRouter()

class CreateAgentRequest(BaseModel):
    user_id: UUID4
    agent_name: Optional[str] = "New Agent"
    db_connection_str: str

    @validator('agent_name')
    def name_must_not_be_empty(cls, v):
        if v.strip() == "":
            raise ValueError('Agent name must not be an empty string.')
        return v
    
    @validator('db_connection_str')
    def validate_db_connection_str(cls, v):
        # Define a simple regex for MySQL connection string validation
        regex = r"mysql\+pymysql:\/\/\w+:\w+@[\w\.]+\/\w+"
        if not re.match(regex, v):
            raise ValueError('Invalid database connection string format.')
        return v


class CreateAgentResponse(BaseModel):
    agent_id: str
    agent_name: str
    created_at: datetime
    last_used: datetime

logging.basicConfig(filename='error.log', level=logging.ERROR)

@router.post("/create_agent", response_model=CreateAgentResponse)
async def create_agent(request: CreateAgentRequest, db=Depends(get_db)) -> CreateAgentResponse:
    try:
        user = await db.users.find_one({"user_id": str(request.user_id)})
        if not user:
            logging.error(f"User {request.user_id} not found.")
            raise HTTPException(status_code=400, detail="User not found.")
            
        
        # Ensure no duplicate agent ID for the user
        existing_agents = user.get("agents", [])
        if any(agent["agent_name"] == request.agent_name for agent in existing_agents):
            logging.error(f"Agent name {request.agent_name} already exists for user {request.user_id}.")
            raise HTTPException(status_code=400, detail="Agent name already exists for user.")


        agent_id = str(uuid.uuid4())
        agent_name = request.agent_name
        current_time = datetime.utcnow()
        

        new_agent = {
            "agent_id": agent_id,
            "agent_name": agent_name,
            "created_at": current_time,
            "last_used": current_time,  # Initialize with the creation time
            "db": request.db_connection_str
        }

        result = await db.users.update_one(
            {"user_id": str(request.user_id)},
            {
                "$push": {
                    "agents": new_agent
                }
            }
        )

        if result.modified_count == 0:
            logging.error(f"Failed to create agent for user {request.user_id}.")
            raise HTTPException(status_code=500, detail="Failed to create agent.")

        
        # Store the agent in an in-memory dictionary or cache
        agent_manager.add_agent(agent_id, request.db_connection_str, llm_api_key)


        return CreateAgentResponse(
            agent_id=agent_id,
            agent_name=agent_name,
            created_at=current_time,
            last_used=current_time  # Return the initial value
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

