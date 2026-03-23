# CDP AI Platform

## Phase Status
- Phase 1: PDF Parsing + Excel Output (COMPLETE)
- Phase 2: Auto-scoring Agent (PLANNED)
- Phase 3: Answer Draft Agent / RAG (PLANNED)

## Key Files
- backend/agents/pdf_parser_agent.py  <- Phase 1 core parser
- backend/api/routes.py               <- API endpoints
- backend/core/llm_client.py          <- Claude API client
- data/outputs/                       <- Excel output folder

## PDF Parser Rules (Phase 1)
Color constants:
  CC_TITLE   = "je-mok"  # dark gray  avg<=0.80
  CC_HEADER  = "he-do"   # light gray avg<=0.96
  CC_CONTENT = "nae-yong" # white     avg>0.96

Table types:
  numbered     -> extract number/Sub/Options
  tags         -> extract Tags rows (CDP 3 categories only)
  skip         -> "Requested content" or "Explanation of terms" header
  continuation -> no number header, append options to previous col_ranges

CDP tag filter: authority type, environmental issue, questionnaire sector

Excel output: single sheet "吏덈Ц_援ъ“?? only
Output folder: C:/Project/CDP-AI-Platform/data/outputs/

## Server
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
Dashboard: http://localhost:8000
API docs:  http://localhost:8000/docs
Health:    http://localhost:8000/api/v1/health

## Dev Rules
1. Read skills/*.skill.md before coding
2. All LLM calls via backend/core/llm_client.py ClaudeClient
3. Agent functions must return AgentResult type
4. Run tests before next step: python -m pytest backend/tests/

## Security
- API Key in .env only - never hardcode
- .env excluded from git
