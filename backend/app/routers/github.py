from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from ..schemas.github import PostCommentRequest, PostCommentResponse
from ..models import get_db, AnalysisRun, AnalysisResult
from ..models.analysis import AnalysisStatus
from ..services.github import GitHubService

router = APIRouter(prefix="/api/github", tags=["github"])


@router.post("/post-comment", response_model=PostCommentResponse)
async def post_github_comment(
    request: PostCommentRequest,
    db: Session = Depends(get_db),
):
    """
    Post the analysis result as a comment on the GitHub PR.
    
    Requires a valid GitHub token to be configured.
    """
    # Get the analysis run
    run = db.query(AnalysisRun).filter(AnalysisRun.id == request.run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    if run.status != AnalysisStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=f"Analysis is not completed. Current status: {run.status}"
        )
    
    # Get the result
    result = db.query(AnalysisResult).filter(AnalysisResult.run_id == request.run_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")
    
    markdown_comment = result.result_json.get("markdown")
    if not markdown_comment:
        raise HTTPException(status_code=500, detail="No markdown comment available")
    
    # Parse PR URL
    github_service = GitHubService()
    try:
        owner, repo, pr_number = github_service.parse_pr_url(request.pr_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Check if we have a token
    from ..config import get_settings
    settings = get_settings()
    if not settings.github_token:
        raise HTTPException(
            status_code=400,
            detail="GitHub token not configured. Cannot post comments."
        )
    
    # Post the comment
    try:
        comment = await github_service.post_comment(owner, repo, pr_number, markdown_comment)
        return PostCommentResponse(
            success=True,
            comment_url=comment.get("html_url"),
            message="Comment posted successfully",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to post comment: {str(e)}")


@router.get("/validate-url")
async def validate_pr_url(url: str):
    """Validate a GitHub PR URL and return parsed info."""
    github_service = GitHubService()
    try:
        owner, repo, pr_number = github_service.parse_pr_url(url)
        return {
            "valid": True,
            "owner": owner,
            "repo": repo,
            "pr_number": pr_number,
        }
    except ValueError as e:
        return {
            "valid": False,
            "error": str(e),
        }
