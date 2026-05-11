from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, farms, fields, predictions
from app.routers.imagery import router as imagery_router
from app.routers.ml import router as ml_router
from app.services.gee_auth import init_gee

app = FastAPI(
    title="AgroSense API",
    description="Satellite-Based AI Crop Monitoring System for Pakistan",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(farms.router)
app.include_router(fields.router)
app.include_router(predictions.router)
app.include_router(imagery_router)
app.include_router(ml_router)

@app.on_event("startup")
def startup_event():
    init_gee()

@app.get("/health", tags=["System"])
def health():
    return {"status": "ok", "app": "AgroSense", "version": "1.0.0"}

@app.get("/", tags=["System"])
def root():
    return {
        "message": "AgroSense API is running",
        "docs": "/docs",
        "health": "/health",
    }
