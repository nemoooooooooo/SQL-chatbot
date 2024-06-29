from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, UUID4
from session_manager import session_manager
from agent_manager import agent_manager
import logging
from datetime import datetime
from DbConnection import get_db
from utilities import ensure_memory_limits
from CONTROL_VAR import MAX_PAIRS_IN_MEMORY, MAX_TOKENS

router = APIRouter()


class MessageRequest(BaseModel):
    session_id: str
    message: str
    user_id: UUID4

class MessageResponse(BaseModel):
    response: str



@router.post("/chat", response_model=MessageResponse)
async def chat(request: MessageRequest, db=Depends(get_db)) -> MessageResponse:
    try:
        session = session_manager.get_session(request.session_id)
        if not session:
            logging.error(f"Session {request.session_id} not found.")
            raise HTTPException(status_code=404, detail="Session not found.")

        agent = agent_manager.get_agent(session["agent_id"])
        if not agent:
            logging.error(f"Agent {session['agent_id']} not found.")
            raise HTTPException(status_code=404, detail="Agent not found.")

        chain = agent["chain"]
        history = session["history"]

        response = chain.invoke({"question": request.message, "messages": history.messages})

        history.add_user_message(request.message)
        history.add_ai_message(response)


        # Update message history in memory and database
        current_time = datetime.utcnow()
        message = {"user_id": str(request.user_id), 
                   "agent_id": session["agent_id"], 
                   "session_id": request.session_id, 
                   "user_message": request.message, 
                   "bot_response": response, 
                   "timestamp": current_time}

        ensure_memory_limits(MAX_PAIRS_IN_MEMORY, MAX_TOKENS, str(request.session_id))

        # Save messages to database
        await db.messages.insert_one(message)
        
        # Update last_used time for session and agent
        session_manager.update_last_used(request.session_id)
        agent_manager.update_last_used(session["agent_id"])
        
        # Update last_used time in the database
        await db.users.update_one(
            {"user_id": str(request.user_id), "sessions.session_id": request.session_id},
            {"$set": {"sessions.$.last_used": current_time}}
        )
        await db.users.update_one(
            {"user_id": str(request.user_id), "agents.agent_id": session["agent_id"]},
            {"$set": {"agents.$.last_used": current_time}}
        )

        return MessageResponse(response=response)
    
    
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        raise HTTPException(status_code=500, detail= f"An unexpected error occurred: {e}")