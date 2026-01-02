from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from sqlalchemy.orm import Session
from datetime import datetime

from ..schemas.analysis import (
    AnalyzeRequest,
    AnalyzeResponse,
    RunStatusResponse,
    AnalysisResultResponse,
)
from ..models import get_db, AnalysisRun, AnalysisResult
from ..models.analysis import AnalysisStatus
from ..services.github import GitHubService
from ..services.analyzer import AnalyzerService

router = APIRouter(prefix="/api", tags=["analysis"])


async def run_analysis(run_id: int, request: AnalyzeRequest, db_url: str):
    """Background task to run the analysis."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    
    # Create new session for background task
    engine = create_engine(db_url, connect_args={"check_same_thread": False} if "sqlite" in db_url else {})
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        run = db.query(AnalysisRun).filter(AnalysisRun.id == run_id).first()
        if not run:
            return
        
        run.status = AnalysisStatus.PROCESSING
        db.commit()
        
        github_service = GitHubService()
        analyzer = AnalyzerService()
        
        # Get analysis payload
        if request.pr_url:
            pr_data = await github_service.fetch_pr_data(request.pr_url)
            payload = analyzer.normalize_payload(
                pr_data,
                language_hint=request.options.language_hint,
                rules_yaml=request.options.rules_yaml,
            )
            
            # Try to fetch repo rules if requested
            if request.options.use_repo_rules and not request.options.rules_yaml:
                rules = await github_service.get_repo_file(
                    pr_data.owner, pr_data.repo, "review_rules.yml"
                ) or await github_service.get_repo_file(
                    pr_data.owner, pr_data.repo, ".review_rules.yml"
                )
                if rules:
                    payload.rules_yaml = rules
        else:
            payload = analyzer.normalize_diff_payload(
                request.diff_text,
                language_hint=request.options.language_hint,
                rules_yaml=request.options.rules_yaml,
            )
        
        # Run analysis
        review = await analyzer.analyze(payload)
        markdown = analyzer.format_as_markdown(review)
        
        # Save result
        result = AnalysisResult(
            run_id=run_id,
            result_json={
                "review": review.model_dump(),
                "markdown": markdown,
            },
            model_version=analyzer.settings.llm_model if analyzer.settings.openai_api_key else "heuristics",
        )
        db.add(result)
        
        run.status = AnalysisStatus.COMPLETED
        run.completed_at = datetime.utcnow()
        db.commit()
        
    except Exception as e:
        run = db.query(AnalysisRun).filter(AnalysisRun.id == run_id).first()
        if run:
            run.status = AnalysisStatus.FAILED
            run.error_message = str(e)
            run.completed_at = datetime.utcnow()
            db.commit()
        raise
    finally:
        db.close()


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_pr(
    request: AnalyzeRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Submit a PR for analysis.
    
    Accepts either a GitHub PR URL (for public repos) or raw diff text.
    Returns a run_id that can be used to check status and retrieve results.
    """
    # Validate request
    if not request.pr_url and not request.diff_text:
        raise HTTPException(
            status_code=400,
            detail="Either pr_url or diff_text must be provided"
        )
    
    # Parse PR URL to get repo info
    repo = None
    pr_number = None
    if request.pr_url:
        try:
            github_service = GitHubService()
            owner, repo_name, pr_number = github_service.parse_pr_url(request.pr_url)
            repo = f"{owner}/{repo_name}"
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    # Create analysis run
    run = AnalysisRun(
        repo=repo,
        pr_number=pr_number,
        pr_url=request.pr_url,
        diff_text=request.diff_text if not request.pr_url else None,
        status=AnalysisStatus.PENDING,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    
    # Start background analysis
    from ..config import get_settings
    settings = get_settings()
    background_tasks.add_task(run_analysis, run.id, request, settings.database_url)
    
    return AnalyzeResponse(
        run_id=run.id,
        status=run.status,
        message="Analysis started. Use GET /api/runs/{run_id} to check status.",
    )


@router.get("/runs/{run_id}", response_model=RunStatusResponse)
async def get_run_status(run_id: int, db: Session = Depends(get_db)):
    """Get the status of an analysis run."""
    run = db.query(AnalysisRun).filter(AnalysisRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    return RunStatusResponse(
        run_id=run.id,
        status=run.status,
        repo=run.repo,
        pr_number=run.pr_number,
        pr_url=run.pr_url,
        created_at=run.created_at,
        completed_at=run.completed_at,
        error_message=run.error_message,
    )


@router.get("/runs/{run_id}/result", response_model=AnalysisResultResponse)
async def get_run_result(run_id: int, db: Session = Depends(get_db)):
    """Get the result of a completed analysis run."""
    run = db.query(AnalysisRun).filter(AnalysisRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    if run.status == AnalysisStatus.PENDING:
        return AnalysisResultResponse(
            run_id=run.id,
            status=run.status,
            result=None,
        )
    
    if run.status == AnalysisStatus.PROCESSING:
        return AnalysisResultResponse(
            run_id=run.id,
            status=run.status,
            result=None,
        )
    
    if run.status == AnalysisStatus.FAILED:
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {run.error_message}"
        )
    
    result = db.query(AnalysisResult).filter(AnalysisResult.run_id == run_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")
    
    from ..schemas.analysis import StructuredReview
    
    return AnalysisResultResponse(
        run_id=run.id,
        status=run.status,
        result=StructuredReview(**result.result_json.get("review", {})),
        model_version=result.model_version,
        markdown_comment=result.result_json.get("markdown"),
    )


@router.get("/runs", response_model=list[RunStatusResponse])
async def list_runs(
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """List recent analysis runs."""
    runs = (
        db.query(AnalysisRun)
        .order_by(AnalysisRun.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    
    return [
        RunStatusResponse(
            run_id=run.id,
            status=run.status,
            repo=run.repo,
            pr_number=run.pr_number,
            pr_url=run.pr_url,
            created_at=run.created_at,
            completed_at=run.completed_at,
            error_message=run.error_message,
        )
        for run in runs
    ]
