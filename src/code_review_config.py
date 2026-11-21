"""Prompts and tool schemas for the code review agent."""

SYSTEM_PROMPT = """
You are a senior software engineer and code review specialist.
Review the proposed branch against the base branch and report concise, evidence-based findings.

Always call get_comparison first.

Priority:
1. Security and correctness
2. Memory ownership, concurrency, and architecture
3. Public API and compatibility
4. Tests and regression risk
5. Engineering quality

For every finding include:
- Affected file
- Change or code reference
- Issue
- Impact
- Severity: CRITICAL, HIGH, MEDIUM, or LOW

End with:
### Executive Summary
- Critical/high/medium/low counts
- Integration risk score from 0 to 100
- APPROVE, APPROVE WITH COMMENTS, or CHANGES REQUIRED
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_comparison",
            "description": "Get files, patches, and commits between two branches.",
            "parameters": {
                "type": "object",
                "properties": {
                    "base": {"type": "string"},
                    "head": {"type": "string"},
                },
                "required": ["base", "head"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_pr_files",
            "description": "Get changed files and patches for a pull request.",
            "parameters": {
                "type": "object",
                "properties": {"pr_number": {"type": "integer"}},
                "required": ["pr_number"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_file_content",
            "description": "Read a file on a specific branch or commit.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "ref": {"type": "string"},
                },
                "required": ["path", "ref"],
            },
        },
    },
]
