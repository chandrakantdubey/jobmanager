import asyncio
import json
import logging
import random
from typing import List, Set, Dict, Any
from concurrent.futures import ThreadPoolExecutor

from sqlmodel import Session, select
from app.db.models import Job
from app.models.job import ScraperInput, JobPost, JobType

# Import Scrapers
from app.scrapers.google import GoogleScraper
from app.scrapers.linkedin import LinkedInScraper
from app.scrapers.indeed import IndeedScraper
from app.scrapers.glassdoor import GlassdoorScraper
from app.scrapers.ziprecruiter import ZipRecruiterScraper
from app.scrapers.bayt import BaytScraper
from app.scrapers.naukri import NaukriScraper
from app.scrapers.adzuna import AdzunaScraper
from app.scrapers.remotive import RemotiveScraper
from app.scrapers.himalayas import HimalayasScraper
from app.scrapers.jobicy import JobicyScraper
from app.scrapers.weworkremotely import WeWorkRemotelyScraper
from app.scrapers.talent import TalentScraper
from app.scrapers.jobspresso import JobspressoScraper
from app.scrapers.jora import JoraScraper
from app.scrapers.remoteco import RemoteCoScraper
from app.scrapers.workingnomads import WorkingNomadsScraper
from app.scrapers.justremote import JustRemoteScraper
from app.scrapers.powertofly import PowerToFlyScraper
from app.scrapers.remoteleaf import RemoteLeafScraper
from app.scrapers.peopleperhour import PeoplePerHourScraper
from app.scrapers.guru import GuruScraper
from app.scrapers.truelancer import TruelancerScraper
from app.scrapers.builtin import BuiltInScraper
from app.scrapers.arc import ArcScraper
# NEW working scrapers (Phase 3)
from app.scrapers.dice import DiceScraper
from app.scrapers.skipthedrive import SkipTheDriveScraper
from app.scrapers.themuse import TheMuseScraper


logger = logging.getLogger("JobService")

def generate_search_queries(resume: dict, user_search_term: str, pass_num: int = 1) -> List[str]:
    """
    Generate search queries based on resume and pass number.
    
    Pass 1: Exact resume titles + top skill combinations
    Pass 2: Broader titles (remove specific tech names)
    Pass 3: Major skills only
    """
    queries = []
    
    if resume:
        parsed_titles = resume.get('parsed_titles', [])
        extracted_skills = resume.get('extracted_skills', [])
        
        if pass_num == 1:
            # Use exact parsed titles
            queries.extend(parsed_titles[:3])  # Top 3 titles
            
            # Combine top 2-3 skills for compound queries
            if len(extracted_skills) >= 2:
                top_skills = extracted_skills[:3]
                queries.append(f"{top_skills[0]} {top_skills[1]} Developer")
                
        elif pass_num == 2:
            # Broader titles - strip specific technologies
            for title in parsed_titles[:2]:
                # Remove specific tech words to broaden search
                broad_title = title
                for tech in ['Python', 'Java', 'JavaScript', 'React', 'Node', 'Angular', 'Vue']:
                    broad_title = broad_title.replace(tech, '').strip()
                if broad_title and broad_title != title:
                    queries.append(broad_title)
            
            # Add generic role titles
            if extracted_skills:
                queries.append("Software Developer")
                queries.append("Software Engineer")
                
        elif pass_num == 3:
            # Fallback: use major skills individually
            queries.extend(extracted_skills[:5])
    
    # Always include user's manual search term if provided
    if user_search_term and user_search_term.strip():
        queries.insert(0, user_search_term)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_queries = []
    for q in queries:
        if q and q.lower() not in seen:
            seen.add(q.lower())
            unique_queries.append(q)
    
    return unique_queries[:5]  # Limit to top 5 queries per pass


def calculate_match_score(job: JobPost, resume: dict) -> float:
    """
    Calculate how well a job matches the resume (0-100 score).
    
    Scoring:
    - Skill match: +10 per matching skill
    - Title match: +20 if job title contains resume title
    - Description match: +5 per skill found in description
    """
    if not resume:
        return 50.0  # Neutral score if no resume
    
    score = 0.0
    job_text = f"{job.title} {job.description}".lower()
    
    # Check skill matches
    extracted_skills = resume.get('extracted_skills', [])
    skill_matches = 0
    for skill in extracted_skills:
        if skill.lower() in job_text:
            skill_matches += 1
            score += 10
    
    # Check title matches
    parsed_titles = resume.get('parsed_titles', [])
    for title in parsed_titles:
        if title.lower() in job.title.lower():
            score += 20
            break
    
    # Description detailed skill match (bonus)
    if job.description:
        desc_lower = job.description.lower()
        for skill in extracted_skills:
            if skill.lower() in desc_lower:
                score += 5
    
    # Cap at 100
    return min(score, 100.0)


class JobService:
    @staticmethod
    async def stream_search_jobs(
        search_term: str,
        location: str,
        results_wanted: int = 15,
        sites: List[str] = ["linkedin", "indeed"],
        is_remote: bool = False,
        country: str = "usa",
        resume: dict = None,  # Changed from resume_skills to full resume dict
        min_experience: int = None,
        max_experience: int = None,
        hours_old: int = None,
        job_type: List[str] = None,
        offset: int = 0,
        session: Session = None
    ):
        """
        Stream job results with multi-pass search strategy and resume-based matching.
        
        Pass 1: Exact resume titles + top skills (if resume exists)
        Pass 2: Broader queries if results < results_wanted
        Pass 3: Fallback to major skills/user term
        """
        
        # Normalize sites to lowercase
        sites = [s.lower() for s in sites]
        
        # Initialize scrapers
        scrapers = []
        if "google" in sites: scrapers.append(GoogleScraper())
        if "linkedin" in sites: scrapers.append(LinkedInScraper())
        if "indeed" in sites: scrapers.append(IndeedScraper())
        if "glassdoor" in sites: scrapers.append(GlassdoorScraper())
        if "ziprecruiter" in sites: scrapers.append(ZipRecruiterScraper())
        if "bayt" in sites: scrapers.append(BaytScraper())
        if "naukri" in sites: scrapers.append(NaukriScraper())
        if "adzuna" in sites: scrapers.append(AdzunaScraper())
        if "remotive" in sites: scrapers.append(RemotiveScraper())
        if "himalayas" in sites: scrapers.append(HimalayasScraper())
        if "jobicy" in sites: scrapers.append(JobicyScraper())
        if "weworkremotely" in sites: scrapers.append(WeWorkRemotelyScraper())
        if "talent.com" in sites: scrapers.append(TalentScraper())
        if "jobspresso" in sites: scrapers.append(JobspressoScraper())
        if "jora" in sites: scrapers.append(JoraScraper())
        if "remote.co" in sites: scrapers.append(RemoteCoScraper())
        if "workingnomads" in sites: scrapers.append(WorkingNomadsScraper())
        if "justremote" in sites: scrapers.append(JustRemoteScraper())
        if "powertofly" in sites: scrapers.append(PowerToFlyScraper())
        if "remoteleaf" in sites: scrapers.append(RemoteLeafScraper())
        if "peopleperhour" in sites: scrapers.append(PeoplePerHourScraper())
        if "guru" in sites: scrapers.append(GuruScraper())
        if "truelancer" in sites: scrapers.append(TruelancerScraper())
        if "builtin" in sites: scrapers.append(BuiltInScraper())
        if "arc" in sites: scrapers.append(ArcScraper())
        # NEW working scrapers (Phase 3)
        if "dice" in sites: scrapers.append(DiceScraper())
        if "skipthedrive" in sites: scrapers.append(SkipTheDriveScraper())
        if "themuse" in sites or "muse" in sites: scrapers.append(TheMuseScraper())
        
        if not scrapers:
            yield json.dumps({"type": "error", "message": "No valid sites selected"}) + "\n"
            return

        # Multi-pass search strategy
        max_passes = 3
        all_collected_jobs = []
        match_score_threshold = 20.0  # Minimum score to include job
        
        for pass_num in range(1, max_passes + 1):
            # Generate queries for this pass
            queries = generate_search_queries(resume, search_term, pass_num)
            
            if not queries:
                queries = [search_term]  # Fallback to user term
            
            yield json.dumps({
                "type": "info", 
                "message": f"Pass {pass_num}: Searching with {len(queries)} queries: {', '.join(queries[:3])}"
            }) + "\n"
            
            pass_jobs = []
            
            # Try each query in this pass
            for query in queries:
                input_data = ScraperInput(
                    search_term=query,
                    location=location,
                    results_wanted=results_wanted // len(queries) if len(queries) > 1 else results_wanted,
                    country=country,
                    is_remote=is_remote,
                    min_experience=min_experience,
                    max_experience=max_experience,
                    hours_old=hours_old,
                    job_type=[JobType(jt) for jt in job_type] if job_type else None,
                    offset=offset
                )

                queue = asyncio.Queue()
                tasks = []

                # Start scrapers for this query
                for scraper in scrapers:
                    tasks.append(asyncio.create_task(
                        JobService._run_scraper(scraper, input_data, queue)
                    ))

                # Consume results
                completed_scrapers = 0
                while completed_scrapers < len(scrapers):
                    item = await queue.get()
                    
                    if isinstance(item, list):
                        # Score and filter jobs
                        for job in item:
                            score = calculate_match_score(job, resume) if resume else 50.0
                            if score >= match_score_threshold:
                                job.match_score = int(score)
                                pass_jobs.append(job)
                        completed_scrapers += 1
                        
                    elif isinstance(item, str):
                        # Stream log message
                        yield json.dumps({"type": "update", "message": item}) + "\n"
                    
                    queue.task_done()

                await asyncio.gather(*tasks)
            
            # Add jobs from this pass
            all_collected_jobs.extend(pass_jobs)
            
            # Save to database
            if session and pass_jobs:
                JobService._save_jobs_to_db(pass_jobs, session)
            
            # Stream results from this pass
            data = [j.model_dump() if hasattr(j, "model_dump") else j.dict() for j in pass_jobs]
            yield json.dumps({"type": "result_batch", "data": data}, default=str) + "\n"
            
            yield json.dumps({
                "type": "success",
                "message": f"Pass {pass_num} complete: {len(pass_jobs)} jobs (Total: {len(all_collected_jobs)})"
            }) + "\n"
            
            # Stop if we have enough results
            if len(all_collected_jobs) >= results_wanted:
                yield json.dumps({
                    "type": "info",
                    "message": f"Target reached ({len(all_collected_jobs)} >= {results_wanted}). Stopping search."
                }) + "\n"
                break
        
        # Final summary
        yield json.dumps({
            "type": "complete",
            "message": f"Search complete! Found {len(all_collected_jobs)} matching jobs across {pass_num} pass(es)."
        }) + "\n"


    @staticmethod
    async def _run_scraper(scraper, input_data, queue):
        try:
            site_name = scraper.site_name
            await queue.put(f"Starting scrape on {site_name}...")
            
            # Blocking call in thread
            jobs = await asyncio.to_thread(scraper.scrape, input_data)
            
            await queue.put(f"Found {len(jobs)} jobs on {site_name}")
            await queue.put(jobs) # Put raw JobPost objects
            
        except Exception as e:
            await queue.put(f"Error on {scraper.site_name}: {e}")
            await queue.put([]) # Signal done with empty list

    @staticmethod
    def _save_jobs_to_db(jobs: List[JobPost], session: Session):
        """Save JobPost objects to database, avoiding duplicates."""
        if not session:
            return
        
        for post in jobs:
            try:
                # Check if job already exists by URL
                existing = session.exec(select(Job).where(Job.job_url == post.job_url)).first()
                
                if not existing:
                    # Convert JobPost to DB Job model
                    db_job = Job(
                        title=post.title,
                        company=post.company,
                        location=post.location or "N/A",
                        job_url=post.job_url,
                        site=post.site,
                        description=post.description or "",
                        description_snippet=(post.description[:200] + "...") if post.description else "",
                        match_score=getattr(post, 'match_score', 50),
                        date_posted=str(post.date_posted) if post.date_posted else None
                    )
                    session.add(db_job)
                    session.commit()
                    session.refresh(db_job)
            except Exception as e:
                logger.error(f"DB Error saving job: {e}")
                session.rollback()

