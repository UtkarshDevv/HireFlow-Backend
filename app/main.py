from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import get_settings
from app.database import init_db
from app.routers import auth, profiles, jobs, resumes, applications, cloudprep, course

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create all DB tables on startup."""
    init_db()
    print("[OK] Database initialized")
    yield


app = FastAPI(
    title="AI Job Applied API",
    description="Tailors resumes to job descriptions and tracks every application.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list if "*" not in settings.cors_origins_list else ["*"],
    allow_origin_regex=r"^https:\/\/.*\.vercel\.app$|^http:\/\/localhost(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(profiles.router)
app.include_router(jobs.router)
app.include_router(resumes.router)
app.include_router(applications.router)
app.include_router(cloudprep.router)
app.include_router(course.router)


@app.get("/", tags=["health"])
def root():
    return {"status": "ok", "message": "AI Job Applied API is running 🚀"}


@app.get("/health", tags=["health"])
def health():
    return {"status": "healthy"}
