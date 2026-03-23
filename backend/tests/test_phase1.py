"""
Phase 1 자동화 테스트
실행: python backend/tests/test_phase1.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


def test_skill_loader():
    from backend.core.skill_loader import load_skill, list_available_skills
    skills = list_available_skills()
    required = {"pdf_extraction", "scoring_criteria", "crawling_guide", "validator"}
    for s in required:
        assert s in skills, f"SKILL 파일 없음: {s}.skill.md"
    content = load_skill("pdf_extraction")
    assert "pdfplumber" in content
    print(f"  PASS: skill_loader ({len(skills)}개 SKILL 확인)")


def test_config_loads():
    from backend.core.config import settings
    # API Key 미설정 상태에서도 settings 객체는 생성돼야 함
    assert hasattr(settings, "CLAUDE_MODEL")
    assert hasattr(settings, "ANTHROPIC_API_KEY")
    assert settings.CLAUDE_MODEL  # 기본값 존재
    print(f"  PASS: config (model={settings.CLAUDE_MODEL})")


def test_config_validation():
    from backend.core.config import Settings
    s = Settings()
    s.ANTHROPIC_API_KEY = ""
    errors = s.validate()
    assert any("ANTHROPIC_API_KEY" in e for e in errors)

    s.ANTHROPIC_API_KEY = "wrong-format-key"
    errors = s.validate()
    assert any("형식 오류" in e for e in errors)

    s.ANTHROPIC_API_KEY = "sk-ant-valid-key"
    errors = s.validate()
    assert len(errors) == 0
    print("  PASS: config_validation")


def test_claude_client_init_no_key():
    from backend.core.llm_client import ClaudeClient
    try:
        ClaudeClient(api_key="")
        assert False, "빈 키로 생성 시 오류가 발생해야 함"
    except ValueError as e:
        assert "ANTHROPIC_API_KEY" in str(e)
    print("  PASS: claude_client_no_key")


def test_models():
    from backend.core.models import AgentResult, AgentStatus, QuestionItem, CrawlResult
    q = QuestionItem(question_id="C1.1", question_text="Test question")
    assert q.question_id == "C1.1"
    r = AgentResult(agent_name="TestAgent", status=AgentStatus.SUCCESS)
    assert r.status == "success"
    cr = CrawlResult(url="http://example.com", content="test content", success=True)
    assert cr.success
    print("  PASS: models")


def test_question_id_pattern():
    from backend.agents.pdf_parser_agent import _extract_questions_from_text
    sample = """
C1.1 Provide your company current strategy and targets.
C1.2 Describe the highest level of responsibility.
W2.3a What is the total water withdrawal?
S1.1 Describe your approach to identifying employees.
"""
    qs = _extract_questions_from_text(sample, page_num=1)
    ids = {q.question_id for q in qs}
    for expected in ["C1.1", "C1.2", "W2.3a", "S1.1"]:
        assert expected in ids, f"{expected} 미인식. 실제: {ids}"
    print(f"  PASS: question_id_pattern ({len(qs)}개 인식)")


def test_cell_cleaning():
    from backend.agents.pdf_parser_agent import _clean_cell
    assert _clean_cell(None) == ""
    assert _clean_cell("nan") == ""
    assert _clean_cell("  text  ") == "text"
    assert _clean_cell("line1\nline2") == "line1 line2"
    assert _clean_cell("N/A") == ""
    print("  PASS: cell_cleaning")


def test_deduplicate():
    from backend.agents.pdf_parser_agent import _deduplicate_questions
    from backend.core.models import QuestionItem
    qs = [
        QuestionItem(question_id="C1.1", question_text="Short"),
        QuestionItem(question_id="C1.1", question_text="Much longer and detailed question text"),
        QuestionItem(question_id="C1.2", question_text="Another"),
    ]
    result = _deduplicate_questions(qs)
    assert len(result) == 2
    c11 = next(q for q in result if q.question_id == "C1.1")
    assert "longer" in c11.question_text
    print("  PASS: deduplicate_questions")


def test_crawler_rate_limit():
    from backend.core.crawler import WebCrawler
    import time
    crawler = WebCrawler(delay=0.1)
    t0 = time.time()
    crawler._rate_limit()
    crawler._rate_limit()
    elapsed = time.time() - t0
    assert elapsed >= 0.08, f"Rate limit 미작동: {elapsed:.3f}s"
    print(f"  PASS: crawler_rate_limit ({elapsed:.2f}s)")


def test_crawl_agent_domain_filter():
    from backend.agents.crawl_agent import _is_allowed_url
    assert _is_allowed_url("https://cdp.net/en/guidance") is True
    assert _is_allowed_url("https://ghgprotocol.org/standards") is True
    assert _is_allowed_url("https://random-site.com/data") is False
    assert _is_allowed_url("https://internal.company.com") is False
    print("  PASS: crawl_domain_filter")


if __name__ == "__main__":
    tests = [
        test_skill_loader,
        test_config_loads,
        test_config_validation,
        test_claude_client_init_no_key,
        test_models,
        test_question_id_pattern,
        test_cell_cleaning,
        test_deduplicate,
        test_crawler_rate_limit,
        test_crawl_agent_domain_filter,
    ]
    passed = failed = 0
    print("\n[ CDP AI Platform — Phase 1 자동화 테스트 ]\n")
    for fn in tests:
        try:
            fn()
            passed += 1
        except Exception as e:
            print(f"  FAIL: {fn.__name__} → {e}")
            failed += 1
    print(f"\n결과: {passed}개 통과 / {failed}개 실패")
    if failed > 0:
        sys.exit(1)
