# -*- coding: utf-8 -*-
"""
Created on Wed Jun 19 22:13:41 2024

@author: Nimra Noor
"""

llm_name = "openai"
llm_api_key = "sk-proj-AV2B55YBepz3MroBLW4QT3BlbkFJRGjEKHtfBcmm5XecCdKk"


system_message = """
        You are a {dialect} expert. Given an input question, creat a syntactically correct {dialect} query to run.
        Unless the user specifies in the question a specific number of examples to obtain, query for at most {top_k} results using the LIMIT clause as per {dialect}. You can order the results to return the most informative data in the database.
        Pay attention to use date('now') function to get the current date, if the question involves "today".
        
        Only use the following tables:
        {table_info}
        
        """
        
answer_prompt_template = """
        Given the following user question, corresponding SQL query, and SQL result, rephrase the answer to the user question in a conversational style without SQL related technical details.

        Question: {question}
        SQL Query: {query}
        SQL Result: {result}
        Answer: """
        
        
redis_url = "redis://localhost:6379"

MAX_PAIRS_IN_MEMORY = 5

MAX_TOKENS = 800