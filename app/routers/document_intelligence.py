from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.document_intelligence import (
    store_document,
    search_documents,
    build_rag_context,
)


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/document-intelligence",
    tags=["Document Intelligence"],
)


# ============================================================
# REQUEST SCHEMAS
# ============================================================

class ProcessDocumentRequest(BaseModel):
    document_id: int
    filename: str
    file_path: str


class SearchRequest(BaseModel):
    query: str
    limit: int = 5
    document_id: int | None = None


class RAGRequest(BaseModel):
    query: str
    limit: int = 5
    document_id: int | None = None


# ============================================================
# PROCESS DOCUMENT
# ============================================================

@router.post("/process")
def process_document(request: ProcessDocumentRequest):

    try:

        result = store_document(
            document_id=request.document_id,
            filename=request.filename,
            file_path=request.file_path,
        )

        return result

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )


# ============================================================
# SEMANTIC SEARCH
# ============================================================

@router.post("/search")
def semantic_search(request: SearchRequest):

    try:

        results = search_documents(
            query=request.query,
            limit=request.limit,
            document_id=request.document_id,
        )

        return {
            "success": True,
            "query": request.query,
            "results": results,
            "result_count": len(results),
        }

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )


# ============================================================
# RAG CONTEXT
# ============================================================

@router.post("/rag-context")
def get_rag_context(request: RAGRequest):

    try:

        result = build_rag_context(
            query=request.query,
            limit=request.limit,
            document_id=request.document_id,
        )

        return {
            "success": True,
            "query": request.query,
            **result,
        }

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )