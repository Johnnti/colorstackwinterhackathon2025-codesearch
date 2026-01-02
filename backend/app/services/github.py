import httpx
import re
from typing import Optional
from dataclasses import dataclass
from ..config import get_settings


@dataclass
class PRData:
    """Data structure for PR information."""
    owner: str
    repo: str
    pr_number: int
    title: str
    body: str
    state: str
    head_sha: str
    base_branch: str
    head_branch: str
    diff: str
    files: list[dict]
    commits: list[dict]
    author: str
    created_at: str
    updated_at: str


class GitHubService:
    """Service for interacting with GitHub API."""
    
    BASE_URL = "https://api.github.com"
    
    def __init__(self, token: Optional[str] = None):
        settings = get_settings()
        self.token = token or settings.github_token
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "AI-PR-Code-Reviewer",
        }
        if self.token:
            self.headers["Authorization"] = f"Bearer {self.token}"
    
    @staticmethod
    def parse_pr_url(pr_url: str) -> tuple[str, str, int]:
        """
        Parse a GitHub PR URL to extract owner, repo, and PR number.
        
        Supports formats:
        - https://github.com/owner/repo/pull/123
        - github.com/owner/repo/pull/123
        """
        pattern = r"(?:https?://)?github\.com/([^/]+)/([^/]+)/pull/(\d+)"
        match = re.match(pattern, pr_url)
        if not match:
            raise ValueError(f"Invalid GitHub PR URL: {pr_url}")
        return match.group(1), match.group(2), int(match.group(3))
    
    async def get_pr(self, owner: str, repo: str, pr_number: int) -> dict:
        """Fetch PR metadata."""
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/pulls/{pr_number}"
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            return response.json()
    
    async def get_pr_diff(self, owner: str, repo: str, pr_number: int) -> str:
        """Fetch the PR diff."""
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/pulls/{pr_number}"
        headers = {**self.headers, "Accept": "application/vnd.github.v3.diff"}
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=60)
            response.raise_for_status()
            return response.text
    
    async def get_pr_files(self, owner: str, repo: str, pr_number: int) -> list[dict]:
        """Fetch list of files changed in the PR."""
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/pulls/{pr_number}/files"
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            return response.json()
    
    async def get_pr_commits(self, owner: str, repo: str, pr_number: int) -> list[dict]:
        """Fetch commits in the PR."""
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/pulls/{pr_number}/commits"
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            return response.json()
    
    async def get_file_content(self, owner: str, repo: str, path: str, ref: str) -> str:
        """Fetch content of a specific file at a given ref."""
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/contents/{path}"
        params = {"ref": ref}
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            if data.get("encoding") == "base64":
                import base64
                return base64.b64decode(data["content"]).decode("utf-8")
            return data.get("content", "")
    
    async def fetch_pr_data(self, pr_url: str) -> PRData:
        """Fetch all relevant PR data in one call."""
        owner, repo, pr_number = self.parse_pr_url(pr_url)
        
        # Fetch all data concurrently
        import asyncio
        pr_info, diff, files, commits = await asyncio.gather(
            self.get_pr(owner, repo, pr_number),
            self.get_pr_diff(owner, repo, pr_number),
            self.get_pr_files(owner, repo, pr_number),
            self.get_pr_commits(owner, repo, pr_number),
        )
        
        return PRData(
            owner=owner,
            repo=repo,
            pr_number=pr_number,
            title=pr_info.get("title", ""),
            body=pr_info.get("body") or "",
            state=pr_info.get("state", ""),
            head_sha=pr_info.get("head", {}).get("sha", ""),
            base_branch=pr_info.get("base", {}).get("ref", ""),
            head_branch=pr_info.get("head", {}).get("ref", ""),
            diff=diff,
            files=files,
            commits=commits,
            author=pr_info.get("user", {}).get("login", ""),
            created_at=pr_info.get("created_at", ""),
            updated_at=pr_info.get("updated_at", ""),
        )
    
    async def post_comment(self, owner: str, repo: str, pr_number: int, body: str) -> dict:
        """Post a comment to a PR."""
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/issues/{pr_number}/comments"
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers=self.headers,
                json={"body": body},
                timeout=30
            )
            response.raise_for_status()
            return response.json()
    
    async def get_repo_file(self, owner: str, repo: str, path: str, ref: str = "main") -> Optional[str]:
        """Try to fetch a file from the repo (e.g., review_rules.yml)."""
        try:
            return await self.get_file_content(owner, repo, path, ref)
        except httpx.HTTPStatusError:
            return None
