# -*- coding: utf-8 -*-
"""
Created on Wed Jun 12 21:06:52 2024

@author: Nimra Noor
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from DbConnection import db
from routes import api_keys
from dotenv import load_dotenv
import logging


load_dotenv()

app = FastAPI()


# Include routers
app.include_router(api_keys.router)


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
    if "API_keys" not in collections:
        await db.create_collection("API_keys")
        
    
    await db.users.create_index([("user_id", 1)], unique=True)
    await db.API_keys.create_index([("user_id", 1)], unique=True)
    


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application shutdown: Cleaning up resources")
    await db.client.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
