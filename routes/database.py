from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from pydantic import BaseModel, UUID4, Field
from utilities import (
    create_mysql_database, drop_mysql_database, execute_mysql_query,
    record_db_in_mongo, remove_db_from_mongo, create_db_from_csv, 
    create_db_from_sql
)
from DbConnection import get_db
import logging
from agent_manager import agent_manager

router = APIRouter()

class CreateDatabaseRequest(BaseModel):
    user_id: UUID4
    db_name: str = Field(..., pattern=r'^[a-zA-Z0-9_]+$')

class DropDatabaseRequest(BaseModel):
    user_id: UUID4
    db_name: str

class ExecuteQueryRequest(BaseModel):
    user_id: UUID4
    db_name: str
    query: str

@router.post("/create_database")
async def create_database(request: CreateDatabaseRequest, db=Depends(get_db)):

    try:
        
        user = await db.users.find_one({"user_id": str(request.user_id), "databases": request.db_name})
        if not user:
            logging.error(f"User {request.user_id} does not have database {request.db_name}.")
            raise HTTPException(status_code=404, detail="Database record not found for user.")

        create_mysql_database(request.db_name)
        record_db_in_mongo(str(request.user_id), request.db_name)
        return {"message": "Database created successfully"}
    except Exception as e:
        logging.error(f"An error occurred while creating the database: {e}")
        raise HTTPException(status_code=500, detail=f"An error occurred while creating the database: {e}")


@router.post("/drop_database")
async def drop_database(request: DropDatabaseRequest, db=Depends(get_db)):
    try:
        user = await db.users.find_one({"user_id": str(request.user_id), "databases": request.db_name})
        if not user:
            logging.error(f"User {request.user_id} does not have database {request.db_name}.")
            raise HTTPException(status_code=404, detail="Database record not found for user.")
        
                
        drop_mysql_database(request.db_name)
        remove_db_from_mongo(str(request.user_id), request.db_name)

        # Remove agent and sessions
        user = await db.users.find_one({"user_id": str(request.user_id)})
        if user:
            agent_to_remove = None
            for agent in user.get("agents", []):
                if agent["db"].endswith(f"/{request.db_name}"):
                    agent_to_remove = agent
                    break

            if agent_to_remove:
                agent_manager.remove_agent(agent_to_remove["agent_id"])
                await db.users.update_one(
                    {"user_id": str(request.user_id)},
                    {"$pull": {"agents": {"agent_id": agent_to_remove["agent_id"]}}}
                )

                # Remove all sessions associated with this agent
                await db.users.update_one(
                    {"user_id": str(request.user_id)},
                    {"$pull": {"sessions": {"agent_id": agent_to_remove["agent_id"]}}}
                )

        return {"message": "Database and associated agent/sessions dropped successfully"}
    except Exception as e:
        logging.error(f"An error occurred while dropping the database: {e}")
        raise HTTPException(status_code=500, detail=f"An error occurred while dropping the database: {e}")


@router.post("/execute_query")
async def execute_query(request: ExecuteQueryRequest, db=Depends(get_db)):
    try:
        
        user = await db.users.find_one({"user_id": str(request.user_id), "databases": request.db_name})
        if not user:
            logging.error(f"User {request.user_id} does not have database {request.db_name}.")
            raise HTTPException(status_code=404, detail="Database record not found for user.")

        
        execute_mysql_query(request.db_name, request.query)
        return {"message": "Query executed successfully"}
    except Exception as e:
        logging.error(f"An error occurred while executing the query: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while executing the query")


@router.post("/create_database_from_csv")
async def create_database_from_csv(
    user_id: UUID4,
    db_name: str = Field(..., regex=r'^[a-zA-Z0-9_]+$'),
    file: UploadFile = File(...)
):
    try:
        create_db_from_csv(str(user_id), db_name, file.file)
        return {"message": "Database created from CSV file successfully"}
    except Exception as e:
        logging.error(f"An error occurred while creating the database from CSV: {e}")
        raise HTTPException(status_code=500, detail=f"An error occurred while creating the database from CSV: {e}")


@router.post("/create_database_from_sql")
async def create_database_from_sql(
    user_id: UUID4,
    db_name: str = Field(..., regex=r'^[a-zA-Z0-9_]+$'),
    file: UploadFile = File(...)
):
    try:
        create_db_from_sql(str(user_id), db_name, file.file)
        return {"message": "Database created from SQL file successfully"}
    except Exception as e:
        logging.error(f"An error occurred while creating the database from SQL: {e}")
        raise HTTPException(status_code=500, detail=f"An error occurred while creating the database from SQL: {e}")