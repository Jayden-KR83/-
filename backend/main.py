from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pathlib import Path
from backend.api.routes import router

app = FastAPI(title="CDP AI Platform", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

_DASHBOARD = Path(__file__).parent.parent / "frontend" / "index.html"

@app.get("/", response_class=HTMLResponse)
def root():
    if _DASHBOARD.exists():
        return HTMLResponse(_DASHBOARD.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>CDP AI Platform</h1><a href='/docs'>API 문서</a>")