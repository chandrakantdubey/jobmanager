
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Field, SQLModel, create_engine, Session, select, col, delete
from typing import List, Optional
from datetime import timedelta
from pydantic import BaseModel
import json

from app.db.session import create_db_and_tables, get_session
from app.db.models import User, Resume, Job, UserJob, JobStatus
from app.core.auth import get_current_user, authenticate_user, create_access_token, get_password_hash, ACCESS_TOKEN_EXPIRE_MINUTES
from app.utils.text import extract_text_from_pdf_bytes, extract_keywords, extract_job_titles
from app.services.job_service import JobService

# Pydantic Schemas for Auth
class Token(BaseModel):
    access_token: str
    token_type: str

class UserCreate(BaseModel):
    username: str
    email: str
    password: str

class UserRead(BaseModel):
    id: int
    username: str
    email: str

app = FastAPI(title="Job Application Manager (Auth)")

# Allow CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    create_db_and_tables()

# AUTHENTICATION
@app.post("/auth/register", response_model=UserRead)
def register(user: UserCreate, session: Session = Depends(get_session)):
    db_user = session.exec(select(User).where(User.username == user.username)).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    db_email = session.exec(select(User).where(User.email == user.email)).first()
    if db_email:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = get_password_hash(user.password)
    new_user = User(username=user.username, email=user.email, hashed_password=hashed_password)
    session.add(new_user)
    session.commit()
    session.refresh(new_user)
    return new_user

@app.post("/auth/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_session)):
    user = authenticate_user(session, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/auth/users/me", response_model=UserRead)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

# RESUMES
@app.post("/resumes/", response_model=Resume)
async def upload_resume(
    file: UploadFile = File(...), 
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    content = await file.read()
    text = extract_text_from_pdf_bytes(content)
    skills = extract_keywords(text)
    titulo = extract_job_titles(text)

    resume = Resume(
        user_id=current_user.id,
        filename=file.filename,
        content_text=text,
        extracted_skills=list(skills),
        parsed_titles=titulo,
        is_active=True
    )
    
    # Deactivate others
    existing = session.exec(select(Resume).where(Resume.user_id == current_user.id)).all()
    for r in existing:
        r.is_active = False
        session.add(r)
        
    session.add(resume)
    session.commit()
    session.refresh(resume)
    return resume

@app.get("/resumes/", response_model=List[Resume])
def get_resumes(current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    return session.exec(select(Resume).where(Resume.user_id == current_user.id).order_by(Resume.upload_date.desc())).all()

@app.delete("/resumes/{resume_id}")
def delete_resume(resume_id: int, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    resume = session.get(Resume, resume_id)
    if not resume or resume.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Resume not found")
    session.delete(resume)
    session.commit()
    return {"ok": True}

# JOBS & SEARCH
@app.post("/search/jobs")
async def search_jobs(
    search_term: str = Query(..., description="Job title or keywords"),
    location: str = Query(..., description="Location"),
    results_wanted: int = Query(20, description="Number of results"),
    # Filters
    country: str = Query("usa", description="Country"),
    job_type: Optional[str] = Query(None),
    is_remote: bool = Query(False),
    easy_apply: bool = Query(None),
    date_posted: Optional[str] = Query(None),
    min_experience: Optional[int] = Query(None, description="Min years experience"),
    max_experience: Optional[int] = Query(None, description="Max years experience"),
    sites: str = Query("linkedin,indeed", description="Comma separated sites"),
    current_user: Optional[User] = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    if not current_user:
         raise HTTPException(status_code=401, detail="Authentication required")
         
    resume = session.exec(select(Resume).where(Resume.user_id == current_user.id, Resume.is_active == True)).first()
    if not resume:
        resume = session.exec(select(Resume).where(Resume.user_id == current_user.id).order_by(Resume.upload_date.desc())).first()
    
    resume_skills = set(resume.extracted_skills) if resume else set()
    site_list = [s.strip() for s in sites.split(",")]
    
    # Use streaming service but collect all for sync endpoint
    jobs = []
    async for msg in JobService.stream_search_jobs(
        search_term=search_term,
        location=location,
        results_wanted=results_wanted,
        sites=site_list,
        is_remote=is_remote,
        country=country,
        min_experience=min_experience,
        max_experience=max_experience,
        resume_skills=resume_skills,
        session=session
    ):
        try:
            data = json.loads(msg)
            if data["type"] == "result_batch":
                jobs.extend(data["data"])
        except: pass
            
    return jobs

@app.get("/search/stream")
async def stream_search_jobs(
    search_term: str = Query(..., description="Job title"),
    location: str = Query(..., description="Location"),
    results_wanted: int = Query(20),
    sites: str = Query("linkedin,indeed"),
    is_remote: bool = Query(False),
    country: str = Query("india"),
    min_experience: int = Query(None),
    max_experience: int = Query(None),
    offset: int = Query(0),
    token: str = Query(...),
    session: Session = Depends(get_session)
):
    # Validate token
    credentials_exception = HTTPException(
         status_code=status.HTTP_401_UNAUTHORIZED,
         detail="Could not validate credentials",
         headers={"WWW-Authenticate": "Bearer"},
    )
    try:
         # Use auth logic
         from app.core.auth import verify_password, SECRET_KEY, ALGORITHM
         from jose import jwt, JWTError
         payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
         username: str = payload.get("sub")
         if username is None: raise credentials_exception
    except Exception:
         raise credentials_exception
         
    user = session.exec(select(User).where(User.username == username)).first()
    if not user: raise credentials_exception

    # Get ACTIVE user resume
    resume = session.exec(select(Resume).where(Resume.user_id == user.id, Resume.is_active == True)).first()
    if not resume:
        resume = session.exec(select(Resume).where(Resume.user_id == user.id).order_by(Resume.upload_date.desc())).first()
    
    # Prepare resume data for service
    resume_data = None
    if resume:
        resume_data = {
            'extracted_skills': resume.extracted_skills or [],
            'parsed_titles': resume.parsed_titles or []
        }
    
    site_list = [s.strip() for s in sites.split(",")]
    
    return StreamingResponse(
        JobService.stream_search_jobs(
            search_term=search_term,
            location=location,
            resume=resume_data,  # Changed from resume_skills to resume dict
            results_wanted=results_wanted,
            sites=site_list,
            is_remote=is_remote,
            country=country,
            min_experience=min_experience,
            max_experience=max_experience,
            offset=offset,
            session=session
        ),
        media_type="text/event-stream"
    )


# TRACKING (UserJobs)
class UserJobUpdate(BaseModel):
    status: JobStatus
    notes: Optional[str] = None

class JobCreateDTO(BaseModel):
    title: str
    company: str
    location: str
    job_url: str
    description: str = ""
    site: str = "unknown"
    date_posted: Optional[str] = None
    match_score: int = 0

@app.post("/jobs/track", response_model=UserJob)
def track_job(job_data: JobCreateDTO, status: JobStatus = JobStatus.SAVED, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    # 1. Check if Job exists by URL (deduplication)
    job = session.exec(select(Job).where(Job.job_url == job_data.job_url)).first()
    
    if not job:
        # Create new Job
        job = Job(
            title=job_data.title,
            company=job_data.company,
            location=job_data.location,
            job_url=job_data.job_url,
            description=job_data.description,
            site=job_data.site,
            date_posted=job_data.date_posted,
            match_score=job_data.match_score
        )
        session.add(job)
        session.commit()
        session.refresh(job)
    
    # 2. Check if already tracked
    existing = session.exec(select(UserJob).where(UserJob.user_id == current_user.id, UserJob.job_id == job.id)).first()
    if existing:
        existing.status = status
        session.add(existing)
        session.commit()
        session.refresh(existing)
        return existing
        
    # 3. Create Tracking
    user_job = UserJob(user_id=current_user.id, job_id=job.id, status=status)
    session.add(user_job)
    session.commit()
    session.refresh(user_job)
    return user_job

@app.get("/tracking", response_model=List[dict])
def get_tracked_jobs(current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    statement = select(UserJob, Job).where(UserJob.user_id == current_user.id).where(UserJob.job_id == Job.id)
    results = session.exec(statement).all()
    
    output = []
    for uj, job in results:
        data = uj.model_dump()
        data["job"] = job.model_dump()
        output.append(data)
    return output

@app.delete("/tracking/{user_job_id}")
def delete_tracked_job(user_job_id: int, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    uj = session.get(UserJob, user_job_id)
    if not uj or uj.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Tracked job not found")
    session.delete(uj)
    session.commit()
    return {"ok": True}

# RESUME MANAGEMENT
@app.get("/resumes", response_model=List[Resume])
def get_resumes_managed(current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    return session.exec(select(Resume).where(Resume.user_id == current_user.id).order_by(Resume.upload_date.desc())).all()

@app.delete("/resumes/{resume_id}")
def delete_resume_managed(resume_id: int, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    resume = session.get(Resume, resume_id)
    if not resume or resume.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Resume not found")
    session.delete(resume)
    session.commit()
    return {"ok": True}

@app.get("/resumes/active", response_model=Resume)
def get_active_resume(current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    resume = session.exec(select(Resume).where(Resume.user_id == current_user.id, Resume.is_active == True)).first()
    if not resume:
        resume = session.exec(select(Resume).where(Resume.user_id == current_user.id).order_by(Resume.upload_date.desc())).first()
        
    if not resume:
        raise HTTPException(status_code=404, detail="No resume found")
    return resume

@app.post("/resumes/{resume_id}/activate")
def activate_resume(resume_id: int, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    resume = session.get(Resume, resume_id)
    if not resume or resume.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Resume not found")
    
    # Deactivate all others
    other_resumes = session.exec(select(Resume).where(Resume.user_id == current_user.id)).all()
    for r in other_resumes:
        r.is_active = False
        session.add(r)
    
    resume.is_active = True
    session.add(resume)
    session.commit()
    return {"ok": True}

class ResumeUpdate(BaseModel):
    extracted_skills: Optional[List[str]] = None
    parsed_titles: Optional[List[str]] = None
    search_preferences: Optional[dict] = None

@app.put("/resumes/{resume_id}")
def update_resume(resume_id: int, update: ResumeUpdate, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    resume = session.get(Resume, resume_id)
    if not resume or resume.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Resume not found")
    
    if update.extracted_skills is not None:
        resume.extracted_skills = update.extracted_skills
    if update.parsed_titles is not None:
        resume.parsed_titles = update.parsed_titles
    if update.search_preferences is not None:
        resume.search_preferences = update.search_preferences
    
    session.add(resume)
    session.commit()
    session.refresh(resume)
    return resume

@app.post("/resumes/upload", response_model=Resume)
async def upload_resume_managed(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    # 1. Read file
    content = await file.read()
    
    # 2. Extract Text
    text = extract_text_from_pdf_bytes(content)
    if not text:
        raise HTTPException(status_code=400, detail="Could not extract text from PDF")
        
    # 3. Extract Skills & Titles
    skills = extract_keywords(text)
    titles = extract_job_titles(text)
    
    # 4. Save to DB
    resume = Resume(
        user_id=current_user.id,
        filename=file.filename,
        content_text=text,
        extracted_skills=list(skills),
        parsed_titles=titles,
        is_active=True # Auto-activate new upload
    )
    
    # Deactivate others
    existing = session.exec(select(Resume).where(Resume.user_id == current_user.id)).all()
    for r in existing:
        r.is_active = False
        session.add(r)
        
    session.add(resume)
    session.commit()
    session.refresh(resume)
    return resume

# GLOBAL SCRAPED JOBS VIEW
class PaginatedJobs(BaseModel):
    items: List[Job]
    total: int

@app.get("/jobs", response_model=PaginatedJobs)
def get_all_scraped_jobs(
    current_user: User = Depends(get_current_user), 
    session: Session = Depends(get_session),
    limit: int = 50, 
    offset: int = 0,
    search: str = None,
    location: str = None
):
    query = select(Job)
    if search:
        query = query.where(col(Job.title).contains(search) | col(Job.description).contains(search) | col(Job.company).contains(search))
    if location:
        query = query.where(col(Job.location).contains(location))
    
    # Get total count (inefficient but simple for now)
    total = len(session.exec(query).all())
    
    # Get items
    items = session.exec(query.order_by(Job.created_at.desc()).offset(offset).limit(limit)).all()
    
    return PaginatedJobs(items=items, total=total)

@app.delete("/jobs/{job_id}")
def delete_scraped_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    # Delete associated UserJob records first (manual cascade)
    user_jobs = session.exec(select(UserJob).where(UserJob.job_id == job_id)).all()
    for uj in user_jobs:
        session.delete(uj)
        
    session.delete(job)
    session.commit()
    return {"ok": True}

@app.delete("/jobs/all/delete")
def delete_all_scraped_jobs(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    session.exec(delete(UserJob))
    session.exec(delete(Job))
    session.commit()
    return {"ok": True}

@app.delete("/tracking/all/delete")
def delete_all_tracked_jobs(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    statement = delete(UserJob).where(UserJob.user_id == current_user.id)
    session.exec(statement)
    session.commit()
    return {"ok": True}
