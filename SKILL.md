---
name: notebooklm
description: Use when the user mentions NotebookLM, shares a NotebookLM URL, asks to query uploaded documents, wants source-grounded answers from a notebook, or wants to manage a local NotebookLM library from Codex.
---

# NotebookLM for Codex

This skill queries Google NotebookLM notebooks from local Codex. NotebookLM supplies source-grounded answers from documents the user has uploaded; Codex uses those answers as research material, not as a replacement for judgment.

This is a Codex adaptation of `PleasePrompto/notebooklm-skill`. It runs browser automation scripts from this skill directory and stores local state under `~/.agents/skills/notebooklm/data/`.

## When to Use

Use this skill when the user:

- Mentions NotebookLM.
- Shares a `https://notebooklm.google.com/notebook/...` URL.
- Asks to query uploaded docs, research notes, papers, manuals, or knowledge bases.
- Wants to add, list, search, activate, or remove NotebookLM notebooks from a local library.
- Needs source-grounded material before writing, coding, analysis, or synthesis.

Do not use this skill for general web search, ordinary local file search, or writing tasks that do not require NotebookLM sources.

## Codex Operating Rules

- Always run from this skill directory: `~/.agents/skills/notebooklm`.
- Always use `python scripts/run.py ...`; never call scripts directly.
- Commands that install dependencies, open browsers, access NotebookLM, or use Google auth require `sandbox_permissions: "require_escalated"`.
- Google login requires the user. When authentication is needed, tell the user a browser window will open and they must complete Google login manually.
- Do not claim a NotebookLM answer supports something unless NotebookLM actually returned it.
- Treat NotebookLM output as source-grounded notes. Separate document facts from Codex synthesis and user-facing recommendations.

## Core Commands

```bash
# Check authentication
python scripts/run.py auth_manager.py status

# One-time setup or reauth: opens a visible browser for user login
python scripts/run.py auth_manager.py setup
python scripts/run.py auth_manager.py reauth

# List, search, activate, and remove notebooks
python scripts/run.py notebook_manager.py list
python scripts/run.py notebook_manager.py search --query "keyword"
python scripts/run.py notebook_manager.py activate --id notebook-id
python scripts/run.py notebook_manager.py remove --id notebook-id

# Ask a question
python scripts/run.py ask_question.py --question "Your question"
python scripts/run.py ask_question.py --question "..." --notebook-id notebook-id
python scripts/run.py ask_question.py --question "..." --notebook-url "https://notebooklm.google.com/notebook/..."
```

The `run.py` wrapper creates `.venv`, installs dependencies, installs Patchright Chrome support, and executes the chosen script.

## Add a Notebook

If the user provides a NotebookLM URL and asks to add it, prefer smart discovery:

```bash
python scripts/run.py ask_question.py \
  --question "What is the content of this notebook? What topics are covered? Provide a brief but complete overview." \
  --notebook-url "https://notebooklm.google.com/notebook/..."
```

Then add it with discovered or user-provided metadata:

```bash
python scripts/run.py notebook_manager.py add \
  --url "https://notebooklm.google.com/notebook/..." \
  --name "Descriptive Name" \
  --description "What this notebook contains" \
  --topics "topic1,topic2,topic3"
```

Never guess generic notebook metadata. If discovery fails, ask the user for the notebook name, description, and topics.

## Query Workflow

1. Check auth: `python scripts/run.py auth_manager.py status`.
2. If not authenticated, run setup and wait for the user to finish login.
3. Identify notebook by URL, active notebook, or library search.
4. Ask a specific question with enough context.
5. Read the result for the marker: `EXTREMELY IMPORTANT: Is that ALL you need to know?`
6. If the answer has gaps, ask follow-up questions before responding.
7. Watch for summary loops. If 2-3 different follow-up questions return essentially the same high-level summary instead of the requested source details, stop querying NotebookLM for that task.
8. Synthesize the NotebookLM answers and cite boundaries clearly.

## Follow-Up Rule

Every query is independent. If NotebookLM returns a partial answer, immediately ask follow-ups with context from the previous answer. Continue until the user's original request is adequately answered or NotebookLM says the source material does not contain the needed information.

## Summary Loop Rule

NotebookLM sometimes keeps returning the same second-level summary even when asked for source titles, transcript details, examples, or exact scenes. Treat this as a source-access limitation, not as enough material for a deep article.

When a summary loop happens:

- Stop spending more NotebookLM queries on the same extraction path.
- Tell the user clearly that NotebookLM is only yielding a summary layer.
- Switch to one of these next actions:
  - ask the user for the original transcript/video notes,
  - search local Obsidian for the source material,
  - use user-provided excerpts as the primary material,
  - mark the output as directional analysis rather than source-rich longform.
- Do not claim you have the full source or quote-like details if NotebookLM did not return them.

## Data and Security

All local state is stored in `~/.agents/skills/notebooklm/data/`:

- `library.json`: notebook metadata.
- `auth_info.json`: auth status metadata.
- `browser_state/`: cookies and browser profile.

Never commit `data/`, `.venv/`, `.env`, auth files, cookies, or browser state.

## References

- `references/api_reference.md`: script commands and options.
- `references/usage_patterns.md`: research workflows and follow-up patterns.
- `references/troubleshooting.md`: authentication, browser, rate-limit, and recovery guidance.

## Limits

- NotebookLM still requires the user to create notebooks and upload/share sources.
- Google or NotebookLM may rate-limit queries.
- Browser automation may fail if Google changes UI selectors.
- Authentication and live querying cannot be fully verified without the user's Google login.
