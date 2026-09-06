import os
import re
import uuid
from pathlib import Path
from typing import List, Dict, Any

import fitz
import pytesseract
from PIL import Image
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

VECTOR_DB_PATH = BASE_DIR / "vector_store"
VECTOR_DB_PATH.mkdir(parents=True, exist_ok=True)

COLLECTION_NAME = "industrial_documents"

EMBEDDING_MODEL = "all-MiniLM-L6-v2"

TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

if os.path.exists(TESSERACT_PATH):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH


# ============================================================
# MODELS
# ============================================================

_embedding_model = None
_qdrant_client = None


def get_embedding_model():
    global _embedding_model

    if _embedding_model is None:
        _embedding_model = SentenceTransformer(EMBEDDING_MODEL)

    return _embedding_model


def get_vector_db():
    global _qdrant_client

    if _qdrant_client is None:
        _qdrant_client = QdrantClient(
            path=str(VECTOR_DB_PATH)
        )

    return _qdrant_client


def initialize_collection():
    db = get_vector_db()

    collections = db.get_collections().collections

    existing = [c.name for c in collections]

    if COLLECTION_NAME not in existing:

        db.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=384,
                distance=Distance.COSINE
            )
        )

    return COLLECTION_NAME


# ============================================================
# TEXT CLEANING
# ============================================================

def clean_text(text: str) -> str:

    if not text:
        return ""

    text = text.replace("\x00", " ")

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    text = re.sub(
        r"\n\s*\n+",
        "\n\n",
        text
    )

    return text.strip()


# ============================================================
# PDF EXTRACTION
# ============================================================

def extract_pdf_text(file_path: str) -> Dict[str, Any]:

    document = fitz.open(file_path)

    pages = []

    total_text = ""

    for page_number, page in enumerate(document):

        text = page.get_text("text")

        text = clean_text(text)

        # ----------------------------------------------------
        # OCR FALLBACK FOR SCANNED PDF
        # ----------------------------------------------------

        if len(text.strip()) < 30:

            pix = page.get_pixmap(
                matrix=fitz.Matrix(2, 2)
            )

            image_bytes = pix.tobytes("png")

            from io import BytesIO

            image = Image.open(
                BytesIO(image_bytes)
            )

            text = pytesseract.image_to_string(
                image
            )

            text = clean_text(text)

        pages.append(
            {
                "page": page_number + 1,
                "text": text
            }
        )

        total_text += f"\n{text}"

    document.close()

    return {
        "text": clean_text(total_text),
        "pages": pages,
        "page_count": len(pages)
    }


# ============================================================
# IMAGE OCR
# ============================================================

def extract_image_text(file_path: str) -> Dict[str, Any]:

    image = Image.open(file_path)

    text = pytesseract.image_to_string(
        image
    )

    text = clean_text(text)

    return {
        "text": text,
        "pages": [
            {
                "page": 1,
                "text": text
            }
        ],
        "page_count": 1
    }


# ============================================================
# TEXT / CSV / OTHER DOCUMENTS
# ============================================================

def extract_plain_text(file_path: str) -> Dict[str, Any]:

    extensions = {
        ".txt",
        ".csv",
        ".md",
        ".log"
    }

    suffix = Path(file_path).suffix.lower()

    if suffix in extensions:

        text = Path(
            file_path
        ).read_text(
            encoding="utf-8",
            errors="ignore"
        )

        text = clean_text(text)

        return {
            "text": text,
            "pages": [
                {
                    "page": 1,
                    "text": text
                }
            ],
            "page_count": 1
        }

    return {
        "text": "",
        "pages": [],
        "page_count": 0
    }


# ============================================================
# UNIVERSAL DOCUMENT EXTRACTION
# ============================================================

def extract_document(file_path: str) -> Dict[str, Any]:

    path = Path(file_path)

    extension = path.suffix.lower()

    if extension == ".pdf":

        result = extract_pdf_text(
            str(path)
        )

    elif extension in {
        ".png",
        ".jpg",
        ".jpeg",
        ".tiff",
        ".bmp"
    }:

        result = extract_image_text(
            str(path)
        )

    elif extension in {
        ".txt",
        ".csv",
        ".md",
        ".log"
    }:

        result = extract_plain_text(
            str(path)
        )

    else:

        raise ValueError(
            f"Unsupported document type: {extension}"
        )

    return result


# ============================================================
# CHUNKING
# ============================================================

def create_chunks(
    text: str,
    chunk_size: int = 700,
    overlap: int = 120
) -> List[str]:

    text = clean_text(text)

    if not text:
        return []

    chunks = []

    start = 0

    while start < len(text):

        end = start + chunk_size

        chunk = text[start:end]

        if end < len(text):

            last_break = max(
                chunk.rfind(". "),
                chunk.rfind("\n"),
                chunk.rfind(" ")
            )

            if last_break > chunk_size * 0.5:

                end = start + last_break + 1

                chunk = text[start:end]

        chunk = chunk.strip()

        if chunk:
            chunks.append(chunk)

        next_start = end - overlap

        if next_start <= start:
            next_start = end

        start = next_start

    return chunks


# ============================================================
# EMBEDDINGS
# ============================================================

def generate_embeddings(
    chunks: List[str]
):

    if not chunks:
        return []

    model = get_embedding_model()

    embeddings = model.encode(
        chunks,
        normalize_embeddings=True
    )

    return embeddings.tolist()


# ============================================================
# STORE DOCUMENT IN VECTOR DATABASE
# ============================================================

def store_document(
    document_id: int,
    filename: str,
    file_path: str
) -> Dict[str, Any]:

    initialize_collection()

    extracted = extract_document(
        file_path
    )

    text = extracted["text"]

    chunks = create_chunks(
        text
    )

    if not chunks:

        return {
            "success": False,
            "message": "No readable text found",
            "document_id": document_id
        }

    embeddings = generate_embeddings(
        chunks
    )

    db = get_vector_db()

    points = []

    for index, (
        chunk,
        embedding
    ) in enumerate(
        zip(chunks, embeddings)
    ):

        point_id = str(
            uuid.uuid4()
        )

        points.append(
            PointStruct(
                id=point_id,
                vector=embedding,
                payload={
                    "document_id": document_id,
                    "filename": filename,
                    "chunk_index": index,
                    "text": chunk,
                    "source": filename
                }
            )
        )

    db.upsert(
        collection_name=COLLECTION_NAME,
        points=points
    )

    return {
        "success": True,
        "document_id": document_id,
        "filename": filename,
        "pages": extracted["page_count"],
        "characters": len(text),
        "chunks": len(chunks),
        "vector_database": "Qdrant Local",
        "embedding_model": EMBEDDING_MODEL
    }


# ============================================================
# SEMANTIC SEARCH
# ============================================================

def search_documents(
    query: str,
    limit: int = 5,
    document_id: int | None = None
) -> List[Dict[str, Any]]:

    initialize_collection()

    model = get_embedding_model()

    query_embedding = model.encode(
        query,
        normalize_embeddings=True
    ).tolist()

    db = get_vector_db()

    query_filter = None

    if document_id is not None:

        from qdrant_client.models import Filter, FieldCondition, MatchValue

        query_filter = Filter(
            must=[
                FieldCondition(
                    key="document_id",
                    match=MatchValue(
                        value=document_id
                    )
                )
            ]
        )

    results = db.query_points(
        collection_name=COLLECTION_NAME,
        query=query_embedding,
        query_filter=query_filter,
        limit=limit,
        with_payload=True
    ).points

    output = []

    for result in results:

        payload = result.payload or {}

        output.append(
            {
                "score": float(
                    result.score
                ),
                "document_id": payload.get(
                    "document_id"
                ),
                "filename": payload.get(
                    "filename"
                ),
                "chunk_index": payload.get(
                    "chunk_index"
                ),
                "text": payload.get(
                    "text"
                ),
                "source": payload.get(
                    "source"
                )
            }
        )

    return output


# ============================================================
# RAG CONTEXT BUILDER
# ============================================================

def build_rag_context(
    query: str,
    limit: int = 5,
    document_id: int | None = None
):

    results = search_documents(
        query=query,
        limit=limit,
        document_id=document_id
    )

    if not results:

        return {
            "context": "",
            "sources": [],
            "results": []
        }

    context_parts = []
    sources = []

    for index, result in enumerate(
        results,
        start=1
    ):

        context_parts.append(
            f"""
SOURCE {index}
FILE: {result['filename']}
CHUNK: {result['chunk_index']}
RELEVANCE: {result['score']:.4f}

{result['text']}
"""
        )

        sources.append(
            {
                "filename": result[
                    "filename"
                ],
                "chunk_index": result[
                    "chunk_index"
                ],
                "score": result[
                    "score"
                ]
            }
        )

    return {
        "context": "\n".join(
            context_parts
        ),
        "sources": sources,
        "results": results
    }