# -*- coding: utf-8 -*-
"""
Created on Thu Jun 20 00:15:00 2024

@author: Nimra Noor
"""

from typing import Dict, Any
from langchain.memory import RedisChatMessageHistory
import threading
from CONTROL_VAR import redis_url
from datetime import datetime

class SessionManager:
    def __init__(self,  redis_url: str):
        self.sessions: Dict[str, Any] = {}
        self.lock = threading.Lock()
        self.redis_url = redis_url

    def add_session(self, session_id: str, agent_id: str):
        with self.lock:
            if session_id in self.sessions:
                return  # Skip if session already exists
            
            history = RedisChatMessageHistory(session_id, url=self.redis_url)
            
            self.sessions[session_id] = {
                "agent_id": agent_id,
                "history": history,
                "last_used": datetime.utcnow()
            }
            
            
    def get_session(self, session_id: str):
        with self.lock:
            return self.sessions.get(session_id)
        
    def update_last_used(self, session_id: str):
        with self.lock:
            if session_id in self.sessions:
                self.sessions[session_id]["last_used"] = datetime.utcnow()

    def remove_session(self, session_id: str):
        with self.lock:
            if session_id in self.sessions:
                del self.sessions[session_id]
                
    def remove_sessions_by_agent(self, agent_id: str):
        with self.lock:
            sessions_to_remove = [session_id for session_id, session in self.sessions.items() if session["agent_id"] == agent_id]
            for session_id in sessions_to_remove:
                del self.sessions[session_id]


session_manager = SessionManager(redis_url)