import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.routers.trace import router as trace_router

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await init_db()
    except Exception as e:
        print(f"[startup] init_db skipped: {e}")
    yield


app = FastAPI(title="GeneTrace", version="0.1.0", lifespan=lifespan)

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://gene-trace-qcc2r23wz-sidselothcodes-projects.vercel.app",
    "https://gene-trace.vercel.app",
    "https://*.vercel.app",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(trace_router)
