import re
import pandas as pd
import json
import asyncio
from pypdf import PdfReader
from io import BytesIO
from typing import List, Set, Generator
import random
from models import Job
from jobspy import scrape_jobs, Country
from sqlmodel import Session, select

# Common tech keywords to look for
TECH_KEYWORDS = {
    "python", "java", "javascript", "typescript", "c++", "c#", "go", "rust", "php", "ruby", "swift", "kotlin",
    "html", "css", "react", "angular", "vue", "node.js", "node", "django", "flask", "fastapi", "spring",
    "sql", "mysql", "postgresql", "mongodb", "redis", "elasticsearch",
    "aws", "azure", "gcp", "docker", "kubernetes", "jenkins", "git", "linux",
    "machine learning", "ai", "data science", "nlp", "computer vision",
    "frontend", "backend", "fullstack", "devops", "sre", "api", "rest", "graphql"
}

def extract_text_from_pdf_bytes(file_bytes: bytes) -> str:
    try:
        reader = PdfReader(BytesIO(file_bytes))
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return ""

def extract_keywords(text: str) -> Set[str]:
    text_lower = text.lower()
    found_keywords = set()
    for keyword in TECH_KEYWORDS:
        pattern = r'\b' + re.escape(keyword) + r'\b'
        if re.search(pattern, text_lower):
            found_keywords.add(keyword)
    return found_keywords

def score_job(job_keywords: Set[str], resume_keywords: Set[str]) -> int:
    return len(job_keywords.intersection(resume_keywords))

# Heuristic list of common job titles
COMMON_JOB_TITLES = {
    "software engineer", "frontend developer", "backend developer", "fullstack developer",
    "devops engineer", "data scientist", "machine learning engineer", "product manager",
    "project manager", "business analyst", "qa engineer", "mobile developer", 
    "android developer", "ios developer", "ui/ux designer", "web developer",
    "systems administrator", "cloud architect", "data analyst", "technical lead",
    "engineering manager", "cto", "vp of engineering", "python developer", 
    "java developer", "react developer", "node.js developer", "go developer"
}

def extract_job_titles(text: str) -> List[str]:
    """
    Extracts likely job titles from text using a predefined list.
    """
    text_lower = text.lower()
    found_titles = set()
    
    # Check for direct matches
    for title in COMMON_JOB_TITLES:
        # Use simple word boundary check
        pattern = r'\b' + re.escape(title) + r'\b'
        if re.search(pattern, text_lower):
            found_titles.add(title.title()) # Capitalize for display
            
    return list(found_titles)


# Refactored to yield progress updates with Parallel Execution and Pagination
async def scrape_single_site(
    site: str,
    search_term: str,
    location: str,
    results_wanted: int,
    is_remote: bool,
    job_type: str,
    easy_apply: bool,
    country: str,
    offset: int,
    hours_old: int,
    linkedin_company_ids: List[int],
    resume_skills: Set[str],
    session: Session,
    queue: asyncio.Queue
):
    """
    Helper to scrape a single site and push updates/results to a shared queue.
    """
    try:
        await queue.put(json.dumps({"type": "update", "message": f"Scraping {site} (Offset: {offset})..."}) + "\n")
        
        # Rate Limiting per site
        sleep_time = random.uniform(2, 5)
        await asyncio.sleep(sleep_time)

        # Run blocking scrape in thread
        jobs_df = await asyncio.to_thread(
            scrape_jobs,
            site_name=[site],
            search_term=search_term,
            location=location,
            results_wanted=results_wanted, 
            is_remote=is_remote,
            job_type=job_type,
            easy_apply=easy_apply,
            country_indeed=country,
            offset=offset,
            hours_old=hours_old,
            linkedin_fetch_description=True,
            linkedin_company_ids=linkedin_company_ids,
            enforce_annual_salary=False,
            verbose=0
        )
        
        count = len(jobs_df)
        await queue.put(json.dumps({"type": "update", "message": f"Found {count} jobs on {site}"}) + "\n")
        
        current_scored = []
        for _, row in jobs_df.iterrows():
            title = str(row.get('title', ''))
            description = str(row.get('description', ''))
            job_text = title + " " + description
            job_skills = extract_keywords(job_text)
            score = score_job(job_skills, resume_skills)
            
            job = Job(
                title=title,
                company=str(row.get('company', 'N/A')),
                location=str(row.get('location', 'N/A')),
                job_url=str(row.get('job_url', '#')),
                description=description,
                description_snippet=description[:200] + "...",
                site=str(row.get('site', site)),
                date_posted=str(row.get('date_posted', '')),
                match_score=score,
                matching_skills=list(job_skills.intersection(resume_skills))
            )

            # Auto-Save / Upsert logic if session provided
            if session:
                try:
                    # Check exist by URL
                    existing = session.exec(select(Job).where(Job.job_url == job.job_url)).first()
                    if not existing:
                        session.add(job)
                        session.commit()
                        session.refresh(job)
                    else:
                        job.id = existing.id # Link ID
                except Exception as db_err:
                    print(f"DB Error saving job: {db_err}")

            current_scored.append(job)
        
        # Push results to queue
        await queue.put(current_scored)

    except Exception as e:
        error_msg = str(e)
        if "Invalid country string" in error_msg:
             await queue.put(json.dumps({"type": "error", "message": f"Error scraping {site}: Invalid country. Please check supported countries."}) + "\n")
        else:
             await queue.put(json.dumps({"type": "error", "message": f"Error scraping {site}: {error_msg}"}) + "\n")
        # Push empty list to signal done
        await queue.put([])


async def stream_search_and_score_jobs(
    search_term: str, 
    location: str, 
    resume_skills: Set[str], 
    results_wanted: int = 20,
    sites: List[str] = ["linkedin", "indeed"], 
    is_remote: bool = False,
    country: str = "india",
    job_type: str = None,
    easy_apply: bool = None,
    date_posted: str = None, 
    offset: int = 0,
    linkedin_company_ids: List[int] = None,
    experience: str = None,
    session: Session = None
):
    # 1. Prepare Parameters
    if experience:
        if experience == "entry": search_term += " entry level"
        elif experience == "mid": search_term += " mid level"
        elif experience == "senior": search_term += " senior"
    
    hours_old = None
    if date_posted:
        if date_posted == "today": hours_old = 24
        elif date_posted == "3days": hours_old = 72
        elif date_posted == "week": hours_old = 168
        elif date_posted == "month": hours_old = 720
        
    # Validate Country
    try:
         if country:
             Country.from_string(country)
    except ValueError as e:
         yield json.dumps({"type": "error", "message": f"Invalid country '{country}'. Using default 'india'."}) + "\n"
         country = "india"

    # 2. Main Pagination Loop
    all_scored_jobs = []
    MAX_PAGINATION = 3 # Avoid infinite loops
    current_iteration = 0
    
    # We divide results_wanted by number of sites to ask a fair amount from each.
    # Actually, it's safer to ask `results_wanted` from EACH site to ensure we get enough total.
    # JobSpy handles this reasonably.
    
    while len(all_scored_jobs) < results_wanted and current_iteration < MAX_PAGINATION:
        if current_iteration > 0:
            yield json.dumps({"type": "update", "message": f"Results check: Found {len(all_scored_jobs)}/{results_wanted}. Fetching more (Page {current_iteration + 1})..."}) + "\n"
            offset += 20 # Increment offset for next batch
            
        queue = asyncio.Queue()
        tasks = []
        
        for site in sites:
            task = asyncio.create_task(scrape_single_site(
                site=site,
                search_term=search_term,
                location=location,
                results_wanted=results_wanted, # Request desired from each site
                is_remote=is_remote,
                job_type=job_type,
                easy_apply=easy_apply,
                country=country,
                offset=offset,
                hours_old=hours_old,
                linkedin_company_ids=linkedin_company_ids,
                resume_skills=resume_skills,
                session=session,
                queue=queue
            ))
            tasks.append(task)

        # Consumer Loop
        completed_sites = 0
        while completed_sites < len(sites):
            item = await queue.get()
            
            if isinstance(item, list):
                # It's a result list (job objects)
                all_scored_jobs.extend(item)
                completed_sites += 1
            else:
                # It's a text message (log)
                yield item
            
            queue.task_done()

        # Wait for all tasks to strictly finish (they should be done if they sent results)
        await asyncio.gather(*tasks)
        
        current_iteration += 1
        
        # If we have enough, break early
        if len(all_scored_jobs) >= results_wanted:
            break

    # 3. Finalize
    # Deduplicate by URL
    unique_jobs = {job.job_url: job for job in all_scored_jobs}.values()
    final_list = list(unique_jobs)
    
    # Sort
    final_list.sort(key=lambda x: x.match_score, reverse=True)
    
    count = len(final_list)
    yield json.dumps({"type": "update", "message": f"Search Complete. Total unique jobs found: {count}"}) + "\n"
    
    final_data = [j.model_dump() for j in final_list]
    yield json.dumps({"type": "result", "data": final_data}, default=str) + "\n"

# Legacy Sync wrapper (kept for safety, though unused by stream endpoint)
def search_and_score_jobs(*args, **kwargs):
    print("Warning: Synchronous `search_and_score_jobs` called. Use `stream_search_and_score_jobs` for best results.")
    return []

