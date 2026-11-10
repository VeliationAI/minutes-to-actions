"""FastAPI web UI for Minutes to Actions."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from minutes.extractor import extract
from minutes.models import MinutesResult

PACKAGE_DIR = Path(__file__).resolve().parent
TEMPLATES = Jinja2Templates(directory=str(PACKAGE_DIR / "templates"))
SAMPLE_PATH = PACKAGE_DIR / "sample_transcript.txt"


class ExtractBody(BaseModel):
    transcript: str = Field(..., min_length=1)
    heuristic: bool = False
    model: Optional[str] = None


def create_app() -> FastAPI:
    app = FastAPI(title="Minutes to Actions", version="1.0.0")
    app.mount("/static", StaticFiles(directory=str(PACKAGE_DIR / "static")), name="static")

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request) -> HTMLResponse:
        sample = ""
        if SAMPLE_PATH.exists():
            sample = SAMPLE_PATH.read_text(encoding="utf-8")
        return TEMPLATES.TemplateResponse(
            request,
            "index.html",
            {"sample": sample},
        )

    @app.get("/api/sample")
    def sample() -> dict[str, str]:
        if not SAMPLE_PATH.exists():
            raise HTTPException(status_code=404, detail="Sample not found.")
        return {"transcript": SAMPLE_PATH.read_text(encoding="utf-8")}

    @app.post("/api/extract")
    def api_extract(body: ExtractBody) -> dict[str, Any]:
        try:
            result: MinutesResult = extract(
                body.transcript,
                model=body.model,
                force_heuristic=body.heuristic,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(
                status_code=502,
                detail=f"Extraction failed: {exc}",
            ) from exc
        return {"result": result.to_dict(), "markdown": result.to_markdown()}

    return app


def run(host: str = "127.0.0.1", port: int = 8766) -> None:
    import uvicorn

    uvicorn.run(create_app(), host=host, port=port)
