from typing import Dict, Any
from langchain_community.utilities import SQLDatabase
from langchain.llms import OpenAI
from langchain.chains import create_sql_query_chain
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder, PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from operator import itemgetter
from langchain_community.tools.sql_database.tool import QuerySQLDataBaseTool
import threading
import re
import logging
from CONTROL_VAR import system_message, answer_prompt_template
from datetime import datetime
from session_manager import session_manager



class AgentManager:
    def __init__(self):
        self.agents: Dict[str, Any] = {}
        self.lock = threading.Lock()

    def add_agent(self, agent_id: str, db_connection_str: str, llm_api_key: str):
        with self.lock:
            if agent_id in self.agents:
                return  # Skip if agent already exists
            
            if llm_api_key and not re.match("^sk-proj-[a-zA-Z0-9]{48}$", llm_api_key):
                logging.error(f"Invalid OpenAI key format for user {llm_api_key}.")
                raise ValueError("Invalid OpenAI key format.")
                
                
            db = SQLDatabase.from_uri(db_connection_str)
            
            llm = OpenAI(api_key=llm_api_key)

            execute_query = QuerySQLDataBaseTool(db=db)
            
            answer_prompt = PromptTemplate.from_template(answer_prompt_template)

            rephrase_answer = answer_prompt | llm | StrOutputParser()

            final_prompt = ChatPromptTemplate.from_messages(
                [
                    ("system", system_message),
                    MessagesPlaceholder(variable_name="messages"),
                    ("human", "{input}"),
                ]
            ).partial(dialect=db.dialect)

            generate_query = create_sql_query_chain(llm, db, final_prompt)

            chain = (
                RunnablePassthrough.assign(query=generate_query).assign(
                    result=itemgetter("query") | execute_query
                )
                | rephrase_answer
            )

            self.agents[agent_id] = {
                "chain": chain,
                "last_used": datetime.utcnow()
            }


    def get_agent(self, agent_id: str):
        with self.lock:
            return self.agents.get(agent_id)
        
    def update_last_used(self, agent_id: str):
        with self.lock:
            if agent_id in self.agents:
                self.agents[agent_id]["last_used"] = datetime.utcnow()

    def remove_agent(self, agent_id: str):
        with self.lock:
            if agent_id in self.agents:
                del self.agents[agent_id]
                session_manager.remove_sessions_by_agent(agent_id)

agent_manager = AgentManager()
