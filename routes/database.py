from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Query
from pydantic import BaseModel, UUID4, Field
from utilities import (
    create_mysql_database, drop_mysql_database, execute_mysql_query,
    record_db_in_mongo, remove_db_from_mongo, create_db_from_csv, 
    create_db_from_sql, create_table, add_column, get_mysql_connection
)
from DbConnection import get_db
import logging
from agent_manager import agent_manager
from typing import Any, Dict
import re


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

class CreateTableRequest(BaseModel):
    user_id: UUID4
    db_name: str
    table_name: str
    columns: str
    
class AddColumnRequest(BaseModel):
    user_id: UUID4
    db_name: str
    table_name: str
    column_definition: str

class AddEntryRequest(BaseModel):
    user_id: UUID4
    db_name: str
    table_name: str
    entry: Dict[str, Any]  # Dictionary with column names as keys and values as values
    
    
    
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
        
@router.post("/create_table")
async def create_table_endpoint(request: CreateTableRequest, db=Depends(get_db)):
    try:
        # Check if the user exists and has the database record
        user = await db.users.find_one({"user_id": str(request.user_id), "databases": request.db_name})
        if not user:
            logging.error(f"User {request.user_id} does not have database {request.db_name}.")
            raise HTTPException(status_code=404, detail="Database record not found for user.")

        # Ensure the table name is valid
        if not re.match(r"^[a-zA-Z0-9_]+$", request.table_name):
            logging.error(f"Invalid table name: {request.table_name}.")
            raise HTTPException(status_code=400, detail="Invalid table name. Only alphanumeric characters and underscores are allowed.")

        # Ensure the columns string is not empty and has valid format
        if not request.columns.strip():
            logging.error("Columns definition is empty.")
            raise HTTPException(status_code=400, detail="Columns definition cannot be empty.")

        # Validate column definitions
        columns = request.columns.split(',')
        for column in columns:
            column = column.strip()
            if not re.match(r"^[a-zA-Z0-9_]+\s+[a-zA-Z0-9()]+(\s+.+)?$", column):
                logging.error(f"Invalid column definition: {column}.")
                raise HTTPException(status_code=400, detail=f"Invalid column definition: {column}. Ensure it follows 'column_name data_type [constraints]' format.")

        # Check if table already exists
        connection = get_mysql_connection(request.db_name)
        with connection.cursor() as cursor:
            cursor.execute(f"SHOW TABLES LIKE '{request.table_name}'")
            if cursor.fetchone():
                logging.error(f"Table {request.table_name} already exists in database {request.db_name}.")
                raise HTTPException(status_code=400, detail=f"Table {request.table_name} already exists in the database.")

        # Create the table
        create_table(request.db_name, request.table_name, request.columns)
        return {"message": "Table created successfully"}
    except HTTPException as e:
        raise e
    except Exception as e:
        logging.error(f"An error occurred while creating the table: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while creating the table")
    finally:
        connection.close()

        
@router.post("/add_column")
async def add_column_endpoint(request: AddColumnRequest, db=Depends(get_db)):
    try:
        user = await db.users.find_one({"user_id": str(request.user_id), "databases": request.db_name})
        if not user:
            logging.error(f"User {request.user_id} does not have database {request.db_name}.")
            raise HTTPException(status_code=404, detail="Database record not found for user.")

        add_column(request.db_name, request.table_name, request.column_definition)
        return {"message": "Column added successfully"}
    except Exception as e:
        logging.error(f"An error occurred while adding the column: {e}")
        raise HTTPException(status_code=500, detail=f"An error occurred while adding the column: {e}")
        
        
@router.post("/add_entry")
async def add_entry_endpoint(request: AddEntryRequest, db=Depends(get_db)):
    connection = None
    try:
        # Check if the user exists and has the database record
        user = await db.users.find_one({"user_id": str(request.user_id), "databases": request.db_name})
        if not user:
            logging.error(f"User {request.user_id} does not have database {request.db_name}.")
            raise HTTPException(status_code=404, detail="Database record not found for user.")

        connection = get_mysql_connection(request.db_name)
        with connection.cursor() as cursor:
            # Check if the table exists
            cursor.execute(f"SHOW TABLES LIKE '{request.table_name}'")
            if not cursor.fetchone():
                logging.error(f"Table {request.table_name} does not exist in database {request.db_name}.")
                raise HTTPException(status_code=404, detail="Table not found in the database.")

            # Fetch table schema to validate columns
            cursor.execute(f"DESCRIBE `{request.table_name}`")
            table_schema = cursor.fetchall()
            table_columns = {column[0] for column in table_schema}

            # Parse and validate columns
            entry_columns = set(request.entry.keys())
            if not entry_columns.issubset(table_columns):
                logging.error(f"One or more columns do not exist in table {request.table_name}.")
                raise HTTPException(status_code=400, detail="Invalid column(s) for the table.")

            # Prepare and execute the insert statement
            columns_str = ', '.join(entry_columns)
            placeholders_str = ', '.join(['%s'] * len(entry_columns))
            values = [request.entry[col] for col in entry_columns]

            insert_query = f"INSERT INTO `{request.table_name}` ({columns_str}) VALUES ({placeholders_str})"
            cursor.execute(insert_query, values)
        connection.commit()

        return {"message": "Entry added successfully"}
    except HTTPException as e:
        raise e
    except Exception as e:
        logging.error(f"An error occurred while adding the entry: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while adding the entry")
    finally:
        if connection:
            connection.close()



@router.post("/create_database_from_csv")
async def create_database_from_csv(
    user_id: UUID4,
    db_name: str = Query(..., pattern=r'^[a-zA-Z0-9_]+$'),
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
    db_name: str = Query(..., pattern=r'^[a-zA-Z0-9_]+$'),
    file: UploadFile = File(...)
):
    try:
        create_db_from_sql(str(user_id), db_name, file.file)
        return {"message": "Database created from SQL file successfully"}
    except Exception as e:
        logging.error(f"An error occurred while creating the database from SQL: {e}")
        raise HTTPException(status_code=500, detail=f"An error occurred while creating the database from SQL: {e}")