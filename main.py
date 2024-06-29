# -*- coding: utf-8 -*-
"""
Created on Wed Jun 12 21:06:52 2024

@author: Nimra Noor
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from DbConnection import db
from routes import create_agent, create_session, chat
from dotenv import load_dotenv
import logging
from agent_manager import agent_manager
from session_manager import session_manager
from CONTROL_VAR import llm_api_key


load_dotenv()


app = FastAPI()


# Include routers
app.include_router(create_agent.router)
app.include_router(create_session.router)
app.include_router(chat.router)

# Configure CORS settings
origins = ["*"]  # Allow requests from all origins
methods = ["*"]  # Allow all HTTP methods

# Add CORS middleware to FastAPI application
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=methods,
    allow_headers=["*"],  # Allow all headers
)


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@app.on_event("startup")
async def startup_event():
    logger.info("Application startup: Preparing resources and initializing services")
    collections = await db.list_collection_names()
    
    if "users" not in collections:
        await db.create_collection("users")
        
    
    await db.users.create_index([("user_id", 1)], unique=True)
    await db.users.create_index([("agents.agent_id", 1), ("user_id", 1)], unique=True)
    await db.users.create_index([("sessions.session_id", 1), ("sessions.agent_id", 1), ("user_id", 1)], unique=True)


    # Load agents from MongoDB
    agents = await db.users.find({"agents": {"$exists": True}}).to_list(length=None)
    for user in agents:
        for agent in user["agents"]:
            agent_manager.add_agent(agent["agent_id"], agent["db"], llm_api_key)

    # Load sessions from MongoDB
    sessions = await db.users.find({"sessions": {"$exists": True}}).to_list(length=None)
    for user in sessions:
        for session in user["sessions"]:
            session_manager.add_session(session["session_id"], session["agent_id"])


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application shutdown: Cleaning up resources")
    await db.client.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)















