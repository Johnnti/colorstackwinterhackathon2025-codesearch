import json
import re
from typing import Optional
from dataclasses import dataclass
from ..schemas.analysis import (
    StructuredReview,
    PRSummary,
    Finding,
    RiskMatrix,
    TestPlan,
    MergeReadiness,
    Severity,
    RiskLevel,
)
from ..services.github import PRData
from ..config import get_settings


@dataclass
class AnalysisPayload:
    """Normalized analysis payload."""
    title: str
    body: str
    diff: str
    files: list[dict]
    file_names: list[str]
    commits: list[str]
    language_hint: Optional[str] = None
    rules_yaml: Optional[str] = None


class AnalyzerService:
    """Service for analyzing PRs and generating structured reviews."""
    
    # Heuristic patterns for fallback analysis
    SECURITY_PATTERNS = [
        (r"password|secret|api_key|apikey|token|credential", "Potential hardcoded secret"),
        (r"eval\s*\(", "Dangerous eval() usage"),
        (r"exec\s*\(", "Dangerous exec() usage"),
        (r"SELECT.*FROM.*WHERE.*=.*\+", "Potential SQL injection"),
        (r"innerHTML\s*=", "Potential XSS vulnerability"),
        (r"dangerouslySetInnerHTML", "React XSS risk"),
        (r"subprocess\.call.*shell\s*=\s*True", "Shell injection risk"),
        (r"pickle\.load", "Insecure deserialization"),
        (r"yaml\.load\((?!.*Loader)", "Insecure YAML loading"),
    ]
    
    PERF_PATTERNS = [
        (r"SELECT\s+\*", "SELECT * may fetch unnecessary data"),
        (r"\.findAll\(|\.find_all\(", "May need pagination for large datasets"),
        (r"for.*in.*for.*in", "Nested loops - potential O(n²)"),
        (r"time\.sleep", "Blocking sleep in code"),
        (r"console\.log|print\(", "Debug statements in production code"),
    ]
    
    AUTH_PATTERNS = [
        (r"@login_required|@authenticated|@auth", "Auth decorator change"),
        (r"middleware.*auth|auth.*middleware", "Auth middleware change"),
        (r"jwt|JWT|token.*verify", "JWT/token handling change"),
        (r"permission|role|access.*control", "Permission/role change"),
    ]
    
    def __init__(self):
        self.settings = get_settings()
    
    def normalize_payload(self, pr_data: PRData, language_hint: Optional[str] = None, rules_yaml: Optional[str] = None) -> AnalysisPayload:
        """Normalize PR data into analysis payload."""
        file_names = [f.get("filename", "") for f in pr_data.files]
        commit_messages = [c.get("commit", {}).get("message", "") for c in pr_data.commits]
        
        return AnalysisPayload(
            title=pr_data.title,
            body=pr_data.body,
            diff=pr_data.diff,
            files=pr_data.files,
            file_names=file_names,
            commits=commit_messages,
            language_hint=language_hint,
            rules_yaml=rules_yaml,
        )
    
    def normalize_diff_payload(self, diff_text: str, language_hint: Optional[str] = None, rules_yaml: Optional[str] = None) -> AnalysisPayload:
        """Normalize raw diff text into analysis payload."""
        # Extract file names from diff
        file_names = re.findall(r"^\+\+\+ b/(.+)$", diff_text, re.MULTILINE)
        
        return AnalysisPayload(
            title="Uploaded Diff",
            body="",
            diff=diff_text,
            files=[{"filename": f} for f in file_names],
            file_names=file_names,
            commits=[],
            language_hint=language_hint,
            rules_yaml=rules_yaml,
        )
    
    async def analyze(self, payload: AnalysisPayload) -> StructuredReview:
        """Run analysis on the payload."""
        # Try LLM analysis first, fall back to heuristics
        if self.settings.openai_api_key:
            try:
                return await self._analyze_with_llm(payload)
            except Exception as e:
                print(f"LLM analysis failed, falling back to heuristics: {e}")
        
        return self._analyze_with_heuristics(payload)
    
    async def _analyze_with_llm(self, payload: AnalysisPayload) -> StructuredReview:
        """Analyze using LLM (OpenAI)."""
        import openai
        
        client = openai.AsyncOpenAI(api_key=self.settings.openai_api_key)
        
        # Truncate diff if too large
        max_diff_chars = 15000
        diff_text = payload.diff[:max_diff_chars]
        if len(payload.diff) > max_diff_chars:
            diff_text += "\n\n[Diff truncated due to size...]"
        
        prompt = self._build_llm_prompt(payload, diff_text)
        
        response = await client.chat.completions.create(
            model=self.settings.llm_model,
            messages=[
                {"role": "system", "content": self._get_system_prompt()},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=4000,
        )
        
        result_json = json.loads(response.choices[0].message.content)
        return self._parse_llm_response(result_json)
    
    def _get_system_prompt(self) -> str:
        return """You are an expert code reviewer. Analyze the provided PR/diff and output a structured JSON review.

Your review should be actionable, specific, and prioritized. Focus on:
1. Security vulnerabilities
2. Performance issues
3. Breaking changes
4. Code quality and maintainability
5. Missing tests

Be direct and specific. Reference exact files and patterns when possible.

Output format (JSON):
{
  "pr_summary": {
    "what_changed": "Brief description of changes",
    "why_it_changed": "Inferred purpose/motivation",
    "key_files": ["file1.py", "file2.js"]
  },
  "findings": [
    {
      "title": "Issue title",
      "severity": "low|medium|high|critical",
      "confidence": 0.0-1.0,
      "file": "path/to/file.py",
      "evidence": "Code snippet or pattern found",
      "recommendation": "What to do about it"
    }
  ],
  "risk_matrix": {
    "security": "low|medium|high",
    "performance": "low|medium|high",
    "breaking_change": "low|medium|high",
    "maintainability": "low|medium|high"
  },
  "test_plan": {
    "unit_tests": ["Test suggestion 1"],
    "integration_tests": ["Test suggestion 1"],
    "edge_cases": ["Edge case to consider"]
  },
  "merge_readiness": {
    "score": 0-100,
    "blockers": ["Critical issue that must be fixed"],
    "notes": "Overall assessment"
  }
}"""
    
    def _build_llm_prompt(self, payload: AnalysisPayload, diff_text: str) -> str:
        prompt_parts = [
            f"# PR Title: {payload.title}",
            f"\n## Description:\n{payload.body}" if payload.body else "",
            f"\n## Files Changed ({len(payload.file_names)}):",
            "\n".join(f"- {f}" for f in payload.file_names[:50]),
            f"\n## Commit Messages:",
            "\n".join(f"- {c}" for c in payload.commits[:10]) if payload.commits else "No commit messages available",
            f"\n## Diff:\n```\n{diff_text}\n```",
        ]
        
        if payload.rules_yaml:
            prompt_parts.append(f"\n## Custom Review Rules:\n```yaml\n{payload.rules_yaml}\n```")
        
        if payload.language_hint:
            prompt_parts.append(f"\n## Language Hint: {payload.language_hint}")
        
        return "\n".join(prompt_parts)
    
    def _parse_llm_response(self, result: dict) -> StructuredReview:
        """Parse and validate LLM response into StructuredReview."""
        try:
            return StructuredReview(
                pr_summary=PRSummary(**result.get("pr_summary", {
                    "what_changed": "Unable to parse",
                    "why_it_changed": "Unable to parse",
                    "key_files": []
                })),
                findings=[
                    Finding(
                        title=f.get("title", "Unknown"),
                        severity=Severity(f.get("severity", "low")),
                        confidence=float(f.get("confidence", 0.5)),
                        file=f.get("file", "unknown"),
                        line_number=f.get("line_number"),
                        evidence=f.get("evidence", ""),
                        recommendation=f.get("recommendation", "")
                    )
                    for f in result.get("findings", [])
                ],
                risk_matrix=RiskMatrix(
                    security=RiskLevel(result.get("risk_matrix", {}).get("security", "low")),
                    performance=RiskLevel(result.get("risk_matrix", {}).get("performance", "low")),
                    breaking_change=RiskLevel(result.get("risk_matrix", {}).get("breaking_change", "low")),
                    maintainability=RiskLevel(result.get("risk_matrix", {}).get("maintainability", "low")),
                ),
                test_plan=TestPlan(
                    unit_tests=result.get("test_plan", {}).get("unit_tests", []),
                    integration_tests=result.get("test_plan", {}).get("integration_tests", []),
                    edge_cases=result.get("test_plan", {}).get("edge_cases", []),
                ),
                merge_readiness=MergeReadiness(
                    score=int(result.get("merge_readiness", {}).get("score", 50)),
                    blockers=result.get("merge_readiness", {}).get("blockers", []),
                    notes=result.get("merge_readiness", {}).get("notes", ""),
                ),
            )
        except Exception as e:
            print(f"Error parsing LLM response: {e}")
            # Return heuristics-based analysis as fallback
            raise
    
    def _analyze_with_heuristics(self, payload: AnalysisPayload) -> StructuredReview:
        """Fallback heuristics-based analysis."""
        findings = []
        security_risk = RiskLevel.LOW
        perf_risk = RiskLevel.LOW
        
        # Check security patterns
        for pattern, description in self.SECURITY_PATTERNS:
            matches = re.finditer(pattern, payload.diff, re.IGNORECASE)
            for match in matches:
                # Find which file this is in
                file_name = self._find_file_for_match(payload.diff, match.start())
                findings.append(Finding(
                    title=description,
                    severity=Severity.HIGH,
                    confidence=0.7,
                    file=file_name or "unknown",
                    evidence=match.group(0),
                    recommendation=f"Review and verify this is not a security issue: {description}",
                ))
                security_risk = RiskLevel.HIGH
        
        # Check performance patterns
        for pattern, description in self.PERF_PATTERNS:
            matches = re.finditer(pattern, payload.diff, re.IGNORECASE)
            for match in matches:
                file_name = self._find_file_for_match(payload.diff, match.start())
                findings.append(Finding(
                    title=description,
                    severity=Severity.MEDIUM,
                    confidence=0.6,
                    file=file_name or "unknown",
                    evidence=match.group(0),
                    recommendation=f"Consider performance implications: {description}",
                ))
                perf_risk = RiskLevel.MEDIUM
        
        # Check auth patterns
        auth_changes = False
        for pattern, description in self.AUTH_PATTERNS:
            if re.search(pattern, payload.diff, re.IGNORECASE):
                auth_changes = True
                findings.append(Finding(
                    title=description,
                    severity=Severity.MEDIUM,
                    confidence=0.8,
                    file="multiple",
                    evidence=f"Pattern matched: {pattern}",
                    recommendation="Ensure auth changes are thoroughly tested",
                ))
        
        # Determine key files (most changed)
        key_files = sorted(
            payload.files,
            key=lambda f: f.get("changes", 0),
            reverse=True
        )[:5]
        key_file_names = [f.get("filename", "") for f in key_files]
        
        # Calculate merge readiness
        critical_count = len([f for f in findings if f.severity == Severity.CRITICAL])
        high_count = len([f for f in findings if f.severity == Severity.HIGH])
        score = max(0, 100 - (critical_count * 30) - (high_count * 15) - (len(findings) * 2))
        
        blockers = [f.title for f in findings if f.severity in [Severity.CRITICAL, Severity.HIGH]]
        
        # Generate test suggestions
        test_suggestions = self._generate_test_suggestions(payload, findings, auth_changes)
        
        return StructuredReview(
            pr_summary=PRSummary(
                what_changed=f"Changes to {len(payload.file_names)} file(s): {', '.join(payload.file_names[:5])}{'...' if len(payload.file_names) > 5 else ''}",
                why_it_changed=payload.body[:200] if payload.body else "No description provided",
                key_files=key_file_names,
            ),
            findings=findings[:20],  # Limit findings
            risk_matrix=RiskMatrix(
                security=security_risk,
                performance=perf_risk,
                breaking_change=RiskLevel.LOW,
                maintainability=RiskLevel.MEDIUM if len(payload.file_names) > 10 else RiskLevel.LOW,
            ),
            test_plan=test_suggestions,
            merge_readiness=MergeReadiness(
                score=score,
                blockers=blockers[:5],
                notes=f"Heuristic analysis found {len(findings)} potential issues." if findings else "No major issues detected by heuristic analysis.",
            ),
        )
    
    def _find_file_for_match(self, diff: str, match_pos: int) -> Optional[str]:
        """Find which file a diff match belongs to."""
        # Look backwards from match position for file header
        before_match = diff[:match_pos]
        file_headers = list(re.finditer(r"^\+\+\+ b/(.+)$", before_match, re.MULTILINE))
        if file_headers:
            return file_headers[-1].group(1)
        return None
    
    def _generate_test_suggestions(self, payload: AnalysisPayload, findings: list[Finding], auth_changes: bool) -> TestPlan:
        """Generate test suggestions based on analysis."""
        unit_tests = []
        integration_tests = []
        edge_cases = []
        
        # Based on file types
        for file_name in payload.file_names:
            if "auth" in file_name.lower() or "login" in file_name.lower():
                unit_tests.append(f"Test authentication logic in {file_name}")
                integration_tests.append("Test complete login/logout flow")
                edge_cases.append("Test with invalid/expired tokens")
            
            if "api" in file_name.lower() or "route" in file_name.lower():
                unit_tests.append(f"Test endpoint handlers in {file_name}")
                integration_tests.append("Test API endpoints with various inputs")
                edge_cases.append("Test rate limiting and error responses")
            
            if "model" in file_name.lower() or "schema" in file_name.lower():
                unit_tests.append(f"Test data validation in {file_name}")
                edge_cases.append("Test with null/empty values")
        
        # Based on findings
        for finding in findings:
            if finding.severity in [Severity.HIGH, Severity.CRITICAL]:
                integration_tests.append(f"Verify fix for: {finding.title}")
        
        if auth_changes:
            integration_tests.append("Test authentication flows end-to-end")
            edge_cases.append("Test session handling and token refresh")
        
        return TestPlan(
            unit_tests=list(set(unit_tests))[:5],
            integration_tests=list(set(integration_tests))[:5],
            edge_cases=list(set(edge_cases))[:5],
        )
    
    def format_as_markdown(self, review: StructuredReview) -> str:
        """Format the review as a GitHub-style markdown comment."""
        lines = [
            "# 🤖 AI Code Review",
            "",
            "## 📝 Summary",
            f"**What changed:** {review.pr_summary.what_changed}",
            f"**Why:** {review.pr_summary.why_it_changed}",
            f"**Key files:** {', '.join(review.pr_summary.key_files) if review.pr_summary.key_files else 'N/A'}",
            "",
        ]
        
        # Findings
        if review.findings:
            lines.extend([
                "## 🔍 Findings",
                "",
            ])
            
            # Sort by severity
            severity_order = {Severity.CRITICAL: 0, Severity.HIGH: 1, Severity.MEDIUM: 2, Severity.LOW: 3}
            sorted_findings = sorted(review.findings, key=lambda f: severity_order.get(f.severity, 4))
            
            for f in sorted_findings[:10]:
                emoji = {"critical": "🚨", "high": "⚠️", "medium": "📋", "low": "💡"}.get(f.severity, "📋")
                lines.append(f"{emoji} **{f.title}** ({f.severity})")
                lines.append(f"- File: `{f.file}`")
                lines.append(f"- {f.recommendation}")
                lines.append("")
        
        # Risk Matrix
        lines.extend([
            "## ⚡ Risk Matrix",
            "",
            "| Category | Level |",
            "|----------|-------|",
            f"| Security | {review.risk_matrix.security} |",
            f"| Performance | {review.risk_matrix.performance} |",
            f"| Breaking Change | {review.risk_matrix.breaking_change} |",
            f"| Maintainability | {review.risk_matrix.maintainability} |",
            "",
        ])
        
        # Test Plan
        lines.extend([
            "## 🧪 Suggested Tests",
            "",
        ])
        
        if review.test_plan.unit_tests:
            lines.append("**Unit Tests:**")
            for t in review.test_plan.unit_tests:
                lines.append(f"- [ ] {t}")
            lines.append("")
        
        if review.test_plan.integration_tests:
            lines.append("**Integration Tests:**")
            for t in review.test_plan.integration_tests:
                lines.append(f"- [ ] {t}")
            lines.append("")
        
        if review.test_plan.edge_cases:
            lines.append("**Edge Cases:**")
            for t in review.test_plan.edge_cases:
                lines.append(f"- [ ] {t}")
            lines.append("")
        
        # Merge Readiness
        score = review.merge_readiness.score
        score_emoji = "✅" if score >= 80 else "⚠️" if score >= 50 else "❌"
        
        lines.extend([
            "## 🎯 Merge Readiness",
            "",
            f"{score_emoji} **Score: {score}/100**",
            "",
        ])
        
        if review.merge_readiness.blockers:
            lines.append("**Blockers:**")
            for b in review.merge_readiness.blockers:
                lines.append(f"- ❌ {b}")
            lines.append("")
        
        if review.merge_readiness.notes:
            lines.append(f"*{review.merge_readiness.notes}*")
        
        lines.extend([
            "",
            "---",
            "*Generated by AI PR Code Reviewer*",
        ])
        
        return "\n".join(lines)
