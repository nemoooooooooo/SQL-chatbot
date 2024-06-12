# -*- coding: utf-8 -*-
"""
Created on Sun Oct  8 00:07:36 2023

@author: Nimra Noor
"""

from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv()


DATABASE_URL = os.getenv("DATABASE_URL", "mongodb://localhost:27017/")
MAX_POOL_SIZE = int(os.getenv("MAX_POOL_SIZE", 10))
MIN_POOL_SIZE = int(os.getenv("MIN_POOL_SIZE", 10))



client = AsyncIOMotorClient(DATABASE_URL, uuidRepresentation="standard", 
                            maxPoolSize=MAX_POOL_SIZE, minPoolSize=MIN_POOL_SIZE)



db = client.neuralyai

async def get_db():
    return db

