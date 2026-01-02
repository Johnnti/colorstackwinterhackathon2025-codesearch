from pydantic import BaseModel
from typing import Optional


class PostCommentRequest(BaseModel):
    """Request body for posting a comment to GitHub."""
    run_id: int
    pr_url: str


class PostCommentResponse(BaseModel):
    """Response from posting a comment."""
    success: bool
    comment_url: Optional[str] = None
    message: str
