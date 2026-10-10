from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import auth_router, team_router, hackathon_router, submission_router, analysis_router, evaluation_router, tasks_router

# Schema is owned by Alembic migrations (see backend/alembic/) - run
# `alembic upgrade head` before starting the app (the "migrate" service in
# docker-compose.yml does this automatically).

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="HackEval Backend API Engine"
)

# CORS Middleware
# Auth is bearer-token (Authorization header), not cookie-based, so credentials
# are never needed cross-origin - allow_credentials stays off so the origin
# list below can be explicit without hitting the wildcard+credentials conflict.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth_router.router)
app.include_router(team_router.router)
app.include_router(hackathon_router.router)
app.include_router(submission_router.router)
app.include_router(analysis_router.router)
app.include_router(evaluation_router.router)
app.include_router(tasks_router.router)

@app.get("/")
def root():
    return {
        "status": "online",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs": "/docs"
    }
