# -*- coding: utf-8 -*-
"""
Created on Sat Jun 29 19:04:46 2024

@author: Nimra Noor
"""

import redis
import tiktoken
import json
import pymysql
from pymongo.errors import PyMongoError
from CONTROL_VAR import mysql_host, mysql_user, mysql_password
from DbConnection import db
import pandas as pd
import sqlparse
from typing import Any, Union
import io
import logging


def num_tokens_from_string(string: str) -> int:
        """
        Returns the number of tokens in a text string.
        Helper method for remove_urls_and_update_ai_dialog()
        """
        encoding_name = "cl100k_base"
        encoding = tiktoken.get_encoding(encoding_name)
        num_tokens = len(encoding.encode(string))
        return num_tokens
    


def ensure_memory_limits(max_pairs, max_tokens, user_memory_key):
        
        # Connect to Redis
        r = redis.Redis()
        """
        Manages memory by keeping it below predefined limits (see control_variables.py)
        """
        
        user_memory_key =f"message_store:{user_memory_key}"


        # Retrieve all dialog pairs from Redis memory
        dialog_pairs = r.lrange(user_memory_key, 0, -1)  
        

        # Calculate the current number of pairs
        current_pairs = len(dialog_pairs) // 2

        # If the number of pairs exceeds the max limit, truncate it
        if current_pairs > max_pairs:
            truncate_count = (current_pairs - max_pairs) * 2  # Multiply by 2 because each pair consists of AI and human dialog
            dialog_pairs = dialog_pairs[:-truncate_count]

        # Count the total number of tokens across all remaining dialog pairs
        total_tokens = sum(num_tokens_from_string(json.loads(message)["data"]["content"]) for message in dialog_pairs)
        print("total tokens: ", total_tokens)

        # If the total number of tokens exceeds the max limit, further truncate dialog pairs
        while total_tokens > max_tokens:
            # Start removing pairs from the end until the total number of tokens is less than the max limit
            for _ in range(2):  # Remove both AI and human dialog from a pair
                if dialog_pairs:
                    pair = dialog_pairs.pop()
                    pair_tokens = num_tokens_from_string(json.loads(pair)["data"]["content"])
                    total_tokens -= pair_tokens
                else:
                    break

        # Reflect the truncation in Redis
        r.ltrim(user_memory_key, 0, len(dialog_pairs) - 1)
        print("Memory successfully limited")
        


# MySQL connection utility
def get_mysql_connection(database: str = None):
    connection = pymysql.connect(
        host=mysql_host,
        user=mysql_user,
        password=mysql_password,
        database=database
    )
    return connection

def create_mysql_database(db_name: str):
    connection = get_mysql_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE `{db_name}`")
        connection.commit()
    finally:
        connection.close()

def drop_mysql_database(db_name: str):
    connection = get_mysql_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(f"DROP DATABASE `{db_name}`")
        connection.commit()
    finally:
        connection.close()

def execute_mysql_query(db_name: str, query: str):
    connection = get_mysql_connection(db_name)
    try:
        with connection.cursor() as cursor:
            cursor.execute(query)
        connection.commit()
    finally:
        connection.close()

def record_db_in_mongo(user_id: str, db_name: str):
    try:
        db.users.update_one(
            {"user_id": user_id},
            {"$push": {"databases": db_name}}
        )
    except PyMongoError as e:
        raise e

def remove_db_from_mongo(user_id: str, db_name: str):
    try:
        db.users.update_one(
            {"user_id": user_id},
            {"$pull": {"databases": db_name}}
        )
    except PyMongoError as e:
        raise e

def create_db_from_csv(user_id: str, db_name: str, csv_file: Any):
    df = pd.read_csv(csv_file)
    create_mysql_database(db_name)
    connection = get_mysql_connection(db_name)
    try:
        df.to_sql(name='table_name', con=connection, index=False, if_exists='replace')
    finally:
        connection.close()
    record_db_in_mongo(user_id, db_name)

def create_db_from_sql(user_id: str, db_name: str, sql_file: Any):
    create_mysql_database(db_name)
    sql_script = sql_file.read().decode()
    connection = get_mysql_connection(db_name)
    try:
        with connection.cursor() as cursor:
            for statement in sqlparse.split(sql_script):
                if statement.strip():
                    cursor.execute(statement)
        connection.commit()
    finally:
        connection.close()
    record_db_in_mongo(user_id, db_name)
