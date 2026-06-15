from sqlalchemy.future import select
from sqlalchemy.orm import Session
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
import io
import PyPDF2
import uuid

# Import the existing tools
from backend.services.rag_service import chunk_text, get_embeddings
from backend.services.ollama_service import generate_completion_stream
from backend.services.transfer_service import execute_agent_transfer
import backend.models as models
from backend.database import get_db
from backend.routers.auth import get_current_active_user
from backend.services.memory_service import extract_and_update_memory, get_global_context

try:
    import chromadb
    from chromadb.config import Settings
    CHROMA_AVAILABLE = True
    chroma_client = chromadb.PersistentClient(
        path="backend/chroma_db",
        settings=Settings(anonymized_telemetry=False)
    )
    sandbox_collection = chroma_client.get_or_create_collection(name="sandbox_knowledge")
except ImportError:
    CHROMA_AVAILABLE = False
    sandbox_collection = None

router = APIRouter()

SANDBOX_SYSTEM_PROMPT = """You are the Sandbox Agent for the Tata Steel Industrial AI Platform.

Your purpose is to act as the first entry point for all users before they access the Engineering Agent.

The Sandbox Agent is a general-purpose AI assistant powered by Retrieval-Augmented Generation (RAG).

Responsibilities:

1. Knowledge Exploration
* Answer questions using uploaded PDFs.
* Use RAG retrieval before generating responses.
* Prefer retrieved document content over assumptions.
* Cite document sources whenever possible.

2. PDF Knowledge Assistant
Users may upload one or more PDF documents.
For every uploaded document:
* Extract text
* Chunk content
* Generate embeddings
* Store in sandbox_knowledge collection
* Use retrieved content during responses
Support:
* Multiple PDF uploads
* Document replacement
* Document deletion
* Session-specific document retrieval

3. Conversation Assistance
Help users:
* Understand documents
* Summarize content
* Compare documents
* Generate reports
* Extract requirements
* Identify problems
* Brainstorm solutions
Do not perform advanced engineering decision-making.

4. Requirement Discovery
When users discuss a project, collect:
* Project Name
* Objective
* Problem Statement
* Technology Stack
* Constraints
* Expected Outcomes
Store information as a session summary.
Do not generate final engineering solutions if requirements are incomplete.
Ask clarification questions first.

5. Satisfaction Tracking
After responses:
* Allow rating collection
* Track user satisfaction
* Track response usefulness

6. Escalation Detection
Recommend Engineering Agent transfer when:
* User requests architecture design
* User requests implementation plans
* User requests industrial maintenance workflows
* User requests safety-critical procedures
* User requests root cause analysis
* User requests engineering decisions
* User requests compliance guidance
* User requests specialist dispatch logic

7. Engineering Transfer
When escalation occurs:
Generate a structured summary:
* User Objective
* Uploaded Documents
* Key Discussions
* Requirements Collected
* Constraints
* Open Questions
* Recommended Next Actions
Transfer:
* Chat History
* Session Summary
* Uploaded Documents
* User Requirements
to the Engineering Agent.

COMMUNICATION & LANGUAGE RULES
* Be conversational, friendly, and natural. Do NOT repeat your internal rules or capabilities back to the user.
* Do NOT use rigid headers (like "Summary", "Clarification Questions", etc.) unless the user explicitly requests a formal report. Respond directly to what the user said.
* If a "DETECTED LANGUAGE" is provided below, you MUST respond entirely in that same language to maintain a natural conversation.

INVENTORY & WORK ORDER RULE:
* If the user requests an Inventory Part, a Work Order, or requests to Escalate, DO NOT invent or hallucinate a PDF document (e.g. do not say "According to the SOP..."). 
* Instead, directly acknowledge their request and state that you will prepare the context to escalate them to the Engineering Agent for execution.

The Sandbox Agent should act as a knowledge assistant and requirement discovery assistant.
The Sandbox Agent should NOT:
* Dispatch specialists
* Trigger emergency workflows
* Perform safety-critical decisions
* Verify permits
* Execute maintenance procedures
* Perform compliance enforcement
Those responsibilities belong exclusively to the Engineering Agent.

CRITICAL SHARED MEMORY INSTRUCTION:
Do NOT ask the user to repeat any information that is already provided in the SHARED PROJECT MEMORY section above. 
Use the Shared Memory to seamlessly continue previous discussions. If they mention correcting a word, it will be automatically stored."""

class ChatRequest(BaseModel):
    message: str
    session_id: str
    model: str = "mistral:latest"
    message_type: str = "text"
    detected_language: str = None

@router.post("/session")
def create_sandbox_session(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    session_id = str(uuid.uuid4())
    db_session = models.SandboxSession(session_id=session_id, user_id=current_user.id)
    db.add(db_session)
    db.commit()
    return {"status": "success", "session_id": session_id}

@router.post("/voice/transcribe")
async def transcribe_voice(file: UploadFile = File(...)):
    from backend.services.voice_service import process_voice_input
    import shutil
    import os
    
    temp_path = f"temp_voice_{uuid.uuid4()}.webm"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    try:
        transcription, language, metrics = await process_voice_input(temp_path)
        print(f"VOICE METRICS: {metrics}")
        
        return {
            "status": "success",
            "transcription": transcription,
            "detected_language": language,
            "metrics": metrics
        }
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

class EscalateRequest(BaseModel):
    sandbox_session_id: str

@router.post("/escalate")
async def escalate_sandbox(
    request: EscalateRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    sandbox_session = db.query(models.SandboxSession).filter(models.SandboxSession.session_id == request.sandbox_session_id, models.SandboxSession.user_id == current_user.id).first()
    if not sandbox_session:
        raise HTTPException(status_code=404, detail="Sandbox session not found or unauthorized")
        
    sandbox_session.status = 'Escalated'
    
    # Create new engineering session
    new_engineer_session_id = str(uuid.uuid4())
    eng_session = models.EngineeringSession(
        session_id=new_engineer_session_id,
        user_id=current_user.id,
        title=sandbox_session.title,
        status="active"
    )
    db.add(eng_session)
    db.commit()
    
    # Execute transfer to generate summary and initial memory
    transfer = await execute_agent_transfer(request.sandbox_session_id, new_engineer_session_id, db, user_id=current_user.id)
    
    # Find Supervisor
    supervisor = None
    if current_user.supervisor_id:
        supervisor = db.query(models.User).filter(models.User.id == current_user.supervisor_id).first()
    if not supervisor:
        # Fallback: search for any user with the supervisor role
        supervisor = db.query(models.User).filter(models.User.role.ilike("SUPERVISOR")).first()
        
    supervisor_name = supervisor.name if supervisor else "Supervisor 1"
    
    # Create Notification
    if supervisor:
        notification = models.Notification(
            recipient_id=supervisor.id,
            title="Sandbox Escalation Alert",
            body=f"Engineer {current_user.name} has escalated a sandbox session. A new engineering session {new_engineer_session_id} has been created.",
            type="escalation_alert",
            related_session_id=new_engineer_session_id
        )
        db.add(notification)
        db.commit()
        
    return {
        "success": True,
        "status": "PENDING",
        "message": "Issue escalated successfully.",
        "supervisor": supervisor_name,
        "engineer_session_id": new_engineer_session_id,
        "transfer_summary": transfer.transfer_summary
    }

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_active_user)
):
    if not file.filename.lower().endswith((".pdf", ".txt")):
        raise HTTPException(status_code=400, detail="Only .pdf and .txt files are supported")
        
    content = await file.read()
    text = ""
    
    if file.filename.lower().endswith(".pdf"):
        try:
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(content))
            for page in pdf_reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to parse PDF: {str(e)}")
    else:
        # .txt file
        try:
            text = content.decode("utf-8")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to decode TXT: {str(e)}")
            
    if not text.strip():
        raise HTTPException(status_code=400, detail="No text extracted from document")
        
    chunks = chunk_text(text, chunk_size=500, overlap=50)
    
    if CHROMA_AVAILABLE and sandbox_collection is not None:
        doc_id = str(uuid.uuid4())
        for i, chunk in enumerate(chunks):
            embedding = get_embeddings(chunk)
            sandbox_collection.add(
                embeddings=[embedding],
                documents=[chunk],
                metadatas=[{"filename": file.filename, "source": "sandbox"}],
                ids=[f"{doc_id}_chunk_{i}"]
            )
            
    return {"status": "success", "message": f"Processed {len(chunks)} chunks from {file.filename}"}

# FIXED
def is_casual_message(message: str) -> bool:
    message = message.lower().strip()
    casual_words = [
        "hello", "hi", "hey", "good morning", "good evening",
        "good afternoon", "how are you", "thanks", "thank you",
        "ok", "okay", "bye", "goodbye", "yes", "no", "sure",
        "great", "nice", "cool", "got it", "understood"
    ]
    return (
        len(message.split()) <= 4
        or any(message.startswith(w) for w in casual_words)
        or message in casual_words
    )

@router.post("/chat")
async def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    # Verify session
    sandbox_session = db.query(models.SandboxSession).filter(models.SandboxSession.session_id == request.session_id, models.SandboxSession.user_id == current_user.id).first()
    if not sandbox_session:
        raise HTTPException(status_code=404, detail="Sandbox session not found or unauthorized")
        
    # Retrieve RAG context
    context_text = ""
    if CHROMA_AVAILABLE and sandbox_collection is not None:
        try:
            query_embedding = await get_embeddings(request.message)
            results = sandbox_collection.query(
                query_embeddings=[query_embedding],
                n_results=3
            )
            if results and results.get('documents') and results['documents'][0]:
                context_text = "\n".join(results['documents'][0])
        except Exception as e:
            print(f"Sandbox RAG retrieval failed: {e}")
            
    
    # Update model for session removed to prevent crash

    # Save user message
    user_msg = models.SandboxMessage(
        session_id=request.session_id, 
        sender="user", 
        content=request.message,
        message_type=request.message_type,
        detected_language=request.detected_language
    )
    db.add(user_msg)
    db.commit()

    # FIXED
    if is_casual_message(request.message):
        global_context = ""
    else:
        # Casual filter
        msg_lower = request.message.lower().strip()
        casual_words = msg_lower.split()
        is_casual = len(casual_words) <= 4 or any(msg_lower.startswith(g) for g in ["hello", "hi", "hey", "thanks", "ok", "bye", "good morning", "good evening"])
        
        if is_casual:
            global_context = ""
        else:
            global_context = get_global_context(request.session_id, db) + "\n\n"

    lang_directive = ""
    if request.detected_language and request.detected_language != "en":
        lang_map = {
            'hi': 'Hindi', 'te': 'Telugu', 'ta': 'Tamil', 'kn': 'Kannada', 
            'ml': 'Malayalam', 'mr': 'Marathi', 'gu': 'Gujarati', 
            'bn': 'Bengali', 'pa': 'Punjabi'
        }
        full_lang = lang_map.get(request.detected_language, request.detected_language)
        lang_directive = f"\n\n[CRITICAL RULE: The user is speaking {full_lang}. YOU MUST REPLY ENTIRELY IN {full_lang.upper()}! DO NOT REPLY IN ENGLISH OR HINDI.]"
        
    full_prompt = f"{global_context}{SANDBOX_SYSTEM_PROMPT}{lang_directive}\n\nRETRIEVED KNOWLEDGE:\n{context_text}\n\nUSER QUERY:\n{request.message}"
    user_id = current_user.id

    async def on_stream_complete(full_agent_response: str):
        import asyncio
        from backend.database import SessionLocal
        async def db_work():
            bg_db = SessionLocal()
            try:
                agent_msg = models.SandboxMessage(
                    session_id=request.session_id, 
                    sender="agent", 
                    content=full_agent_response,
                    message_type=request.message_type,
                    detected_language=request.detected_language
                )
                bg_db.add(agent_msg)
                
                # Auto-title logic
                msg_count = bg_db.query(models.SandboxMessage).filter(models.SandboxMessage.session_id == request.session_id).count()
                if msg_count == 2: # user msg + this agent msg
                    session = bg_db.query(models.SandboxSession).filter(models.SandboxSession.session_id == request.session_id).first()
                    if session and not session.title:
                        import re
                        clean_msg = re.sub(r'[^a-zA-Z0-9\s]', '', request.message)
                        words = clean_msg.split()
                        title = ' '.join([w.capitalize() for w in words[:10]])
                        if len(title) > 50:
                            title = title[:47] + '...'
                        if not title.strip():
                            title = 'Sandbox Session'
                        session.title = title
    
                bg_db.commit()
                
                await extract_and_update_memory(
                    user_id=user_id, 
                    session_id=request.session_id, 
                    user_message=request.message, 
                    agent_message=full_agent_response, 
                    db=bg_db
                )
            except Exception as e:
                import traceback
                print("Failed saving sandbox msg to db:", e)
                traceback.print_exc()
            finally:
                bg_db.close()
        await db_work()

    return StreamingResponse(
        generate_completion_stream(full_prompt, model=request.model, on_complete=on_stream_complete),
        media_type="text/event-stream"
    )

@router.delete("/reset")
def reset_sandbox(current_user: models.User = Depends(get_current_active_user)):
    if CHROMA_AVAILABLE and sandbox_collection is not None:
        try:
            # Delete all documents in the sandbox collection
            results = sandbox_collection.get()
            if results and results.get('ids'):
                sandbox_collection.delete(ids=results['ids'])
            return {"status": "success", "message": "Sandbox knowledge base cleared"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to reset sandbox: {str(e)}")
    return {"status": "error", "message": "ChromaDB not available"}

@router.get("/history/list")
def get_sandbox_history(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    sessions = db.query(models.SandboxSession).filter(
        models.SandboxSession.user_id == current_user.id
    ).order_by(models.SandboxSession.created_at.desc()).all()
    
    result = []
    for s in sessions:
        msg_count = db.query(models.SandboxMessage).filter(models.SandboxMessage.session_id == s.session_id).count()
        last_msg = db.query(models.SandboxMessage).filter(models.SandboxMessage.session_id == s.session_id).order_by(models.SandboxMessage.created_at.desc()).first()
        preview = last_msg.content[:50] + "..." if last_msg and last_msg.content else ""
        title = s.title or "Sandbox Session"
        
        result.append({
            "session_id": s.session_id,
            "status": "Escalated" if s.status == 'Escalated' else "Active",
            "started_at": s.created_at,
            "title": title,
            "message_count": msg_count,
            "last_message_preview": preview
        })
    return result

@router.delete("/session/{session_id}")
def delete_sandbox_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    session = (db.execute(select(models.SandboxSession).where(
        models.SandboxSession.session_id == session_id,
        models.SandboxSession.user_id == current_user.id
    ))).scalars().first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    from sqlalchemy import delete
    db.execute(delete(models.SandboxMessage).where(models.SandboxMessage.session_id == session_id))
    db.execute(delete(models.SandboxMemory).where(models.SandboxMemory.session_id == session_id))
    db.execute(delete(models.AgentFeedback).where(models.AgentFeedback.session_id == session_id))
    db.execute(delete(models.EscalationHistory).where(models.EscalationHistory.sandbox_session_id == session_id))
        
    db.delete(session)
    db.commit()
    return {"status": "success"}

@router.get("/history/chat/{session_id}")
def get_sandbox_chat_history(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    session = (db.execute(select(models.SandboxSession).where(
        models.SandboxSession.session_id == session_id,
        models.SandboxSession.user_id == current_user.id
    ))).scalars().first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    messages = db.query(models.SandboxMessage).filter(models.SandboxMessage.session_id == session_id).order_by(models.SandboxMessage.created_at.asc()).all()
    
    result = []
    for m in messages:
        result.append({
            "sender": m.sender,
            "content": m.content,
            "created_at": m.created_at,
            "message_type": m.message_type,
            "detected_language": m.detected_language
        })
    return result

