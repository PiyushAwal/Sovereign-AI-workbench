import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

from app.database.connection import Base, engine

# Routers
from app.routers.users import router as users_router
from app.routers.projects import router as projects_router
from app.routers.documents import router as documents_router
from app.routers.tasks import router as tasks_router
from app.routers.reports import router as reports_router
from app.routers.document_intelligence import router as document_intelligence_router
from app.routers.ai import router as ai_router

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Sovereign AI Workbench API",
    description="Backend API for Sovereign On-Premise Agentic AI Workbench",
    version="1.0.0",
)

# 1. Enable CORS for all local development tooling
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Add performance logging middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(round(process_time, 4))
    return response

# Include all core routes
app.include_router(users_router)
app.include_router(projects_router)
app.include_router(documents_router)
app.include_router(tasks_router)
app.include_router(reports_router)
app.include_router(document_intelligence_router)
app.include_router(ai_router)

# Mount Dashboard UI
app.mount("/dashboard", StaticFiles(directory="app/static", html=True), name="static")

@app.get("/")
def root():
    return RedirectResponse(url="/dashboard")

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "Sovereign AI Workbench"}
