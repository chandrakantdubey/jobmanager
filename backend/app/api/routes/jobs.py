from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
from typing import List, Optional
from sqlmodel import Session

from app.services.job_service import JobService
from app.db.models import Job, User
# Assuming get_session dependency exists or needs to be created. 
# For now, simplistic session handling or None as the service handles None session.

router = APIRouter()

@router.get("/stream")
async def stream_jobs(
    search_term: str,
    location: str,
    results_wanted: int = 20,
    sites: List[str] = Query(default=["linkedin", "indeed"]),
    is_remote: bool = False,
    country: str = "usa",
    offset: int = 0,
    job_type: Optional[List[str]] = Query(default=None),
    hours_old: Optional[int] = None
):
    """
    Stream job search results (SSE style JSON objects).
    """
    return StreamingResponse(
        JobService.stream_search_jobs(
            search_term=search_term,
            location=location,
            results_wanted=results_wanted,
            sites=sites,
            is_remote=is_remote,
            country=country,
            offset=offset,
            job_type=job_type,
            hours_old=hours_old
        ),
        media_type="application/x-ndjson"
    )
