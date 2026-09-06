import os
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.models import AgentTask, Document
from app.ai.ollama_service import generate, health_check
from app.ai.model_router import select_model

router = APIRouter(
    prefix="/ai",
    tags=["AI Agent & RAG"]
)

class AskRequest(BaseModel):
    query: str
    project_id: Optional[int] = None
    use_rag: bool = True
    model: Optional[str] = None
    temperature: Optional[float] = 0.2

class AskResponse(BaseModel):
    model: str
    response: str
    sources: List[str] = []
    rag_used: bool = False
    status: str = "success"

class RunTaskRequest(BaseModel):
    model: Optional[str] = None

@router.get("/health")
def check_ai_health():
    return health_check()

@router.post("/ask", response_model=AskResponse)
def ask_ai(payload: AskRequest, db: Session = Depends(get_db)):
    try:
        active_model = payload.model if payload.model else select_model()
        retrieved_context = []
        sources = []

        if payload.use_rag:
            try:
                query_filter = db.query(Document)
                if payload.project_id:
                    query_filter = query_filter.filter(Document.project_id == payload.project_id)
                docs = query_filter.all()

                keywords = [k.lower() for k in payload.query.split() if len(k) > 3]

                for doc in docs:
                    if doc.file_path and os.path.exists(doc.file_path):
                        with open(doc.file_path, "r", encoding="utf-8", errors="ignore") as f:
                            text_content = f.read()

                        if any(k in text_content.lower() for k in keywords) or not keywords:
                            retrieved_context.append(f"Document: {doc.filename}\nContent:\n{text_content[:1500]}")
                            if doc.filename not in sources:
                                sources.append(doc.filename)
            except Exception:
                pass

        if retrieved_context:
            context_block = "\n---\n".join(retrieved_context)
            final_prompt = (
                "You are an on-premise industrial AI engineering assistant.\n"
                "Use the following authoritative document context to answer the user query accurately.\n\n"
                f"CONTEXT:\n{context_block}\n\n"
                f"QUERY: {payload.query}\n\n"
                "ENGINEERING ASSESSMENT:"
            )
            rag_flag = True
        else:
            final_prompt = (
                "You are an on-premise industrial AI engineering assistant.\n"
                f"QUERY: {payload.query}\n\n"
                "ENGINEERING ASSESSMENT:"
            )
            rag_flag = False

        result = generate(prompt=final_prompt, model=active_model, temperature=payload.temperature)

        return AskResponse(
            model=active_model,
            response=result,
            sources=sources,
            rag_used=rag_flag,
            status="success"
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.post("/tasks/{task_id}/run")
def run_agent_task(task_id: int, payload: Optional[RunTaskRequest] = None, db: Session = Depends(get_db)):
    task = db.query(AgentTask).filter(AgentTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    try:
        task_title = getattr(task, "task_type", "Industrial Task")
        task_desc = getattr(task, "description", "") or "Analyze anomaly telemetry."

        task.status = "in_progress"
        db.commit()

        active_model = (payload.model if payload and payload.model else None) or select_model()
        prompt = (
            "Autonomous Industrial AI Agent executing operational task:\n"
            f"Task Type: {task_title}\n"
            f"Details: {task_desc}\n\n"
            "Produce an actionable, structured industrial analysis and remediation report:"
        )

        task_output = generate(prompt=prompt, model=active_model, temperature=0.3)

        task.status = "completed"
        task.result = task_output
        task.completed_at = datetime.utcnow()

        db.commit()
        db.refresh(task)

        return {
            "status": "success",
            "task_id": task.id,
            "title": task_title,
            "state": "completed",
            "output": task_output
        }
    except Exception as exc:
        task.status = "failed"
        task.error_message = str(exc)
        db.commit()
        raise HTTPException(status_code=500, detail=f"Task execution failed: {str(exc)}")
