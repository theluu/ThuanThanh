#!/usr/bin/env python3
"""PreToolUse guard: stop Claude Code from reading/printing .env secrets or writing API keys into files.

Reads the hook payload on stdin; exit 2 blocks the tool call and the stderr message is shown to Claude.
"""
import json
import re
import sys

KEY_RE = re.compile(r"sk-(?:proj-)?[A-Za-z0-9_\-]{20,}|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{30,}")
# A reader command whose own arguments (same simple command) include a .env file (but not .env.example).
ENV_READ_RE = re.compile(
    r"(?:^|[\s;&|(])(?:cat|less|more|head|tail|bat|grep|rg|awk|sed|strings|xxd|od|base64|cp|scp|curl|source)\b"
    r"[^\n;&|]*?(?:^|[\s/'\"=<])\.env(?:\.(?!example\b)[\w.-]+)?(?=$|[\s'\";|&)>])", re.MULTILINE)
SETUP_COPY_RE = re.compile(r"^\s*cp\s+\S*\.env\.example\s+\S*\.env\s*$")  # README setup step
SECRET_VARS_RE = re.compile(r"(?<![.\w/-])(printenv|env|export -p|set)\b\s*($|\|)|\$\{?(OPENAI_API_KEY|ANTHROPIC_API_KEY|API_TOKEN|MAIN_DB_URL|EXTERNAL_DB_URL)\b")


def block(reason: str) -> None:
    print(f"Blocked by .claude/hooks/guard_secrets.py: {reason}", file=sys.stderr)
    sys.exit(2)


def main() -> None:
    payload = json.load(sys.stdin)
    tool, inp = payload.get("tool_name", ""), payload.get("tool_input", {}) or {}

    if tool == "Bash":
        cmd = inp.get("command", "")
        if ENV_READ_RE.search(cmd) and not SETUP_COPY_RE.match(cmd):
            block("reading or copying a .env file exposes secrets; use .env.example instead.")
        if SECRET_VARS_RE.search(cmd):
            block("printing environment secrets (API keys / DB URLs) is not allowed.")
        if KEY_RE.search(cmd):
            block("the command contains what looks like a live API key.")
    elif tool in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
        text = json.dumps(inp)
        if KEY_RE.search(text):
            block("refusing to write an API key into a file; reference it via environment variables.")


if __name__ == "__main__":
    main()
