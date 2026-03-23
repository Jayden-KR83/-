"""
CDP PDF Parser 테스트 스크립트
사용법:
    python test_parser.py                    # 기본 (페이지 12-16, 질문 1.1~1.4 영역)
    python test_parser.py 20 25              # 페이지 20~25 테스트
    python test_parser.py 12 16 --open       # 테스트 후 엑셀 파일 자동 열기
"""
import sys, os, time

sys.path.insert(0, os.path.dirname(__file__))

def main():
    page_start = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 12
    page_end = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 16
    auto_open = "--open" in sys.argv

    print("=" * 70)
    print("  CDP PDF Parser Test  |  pages %d ~ %d" % (page_start, page_end))
    print("=" * 70)

    from backend.agents.pdf_parser_agent import run_pdf_parser

    pdf_path = None
    upload_dir = "data/uploads"
    for f in os.listdir(upload_dir):
        if f.endswith(".pdf") and "Questionnaire" in f:
            pdf_path = os.path.join(upload_dir, f)
            break

    if not pdf_path:
        print("[ERROR] data/uploads/ 에 Questionnaire PDF 없음")
        return

    print("[PDF] %s" % pdf_path)
    print("[범위] %d ~ %d 페이지" % (page_start, page_end))
    print()

    t0 = time.time()
    result = run_pdf_parser(
        pdf_path=pdf_path,
        output_dir="data/outputs",
        save_excel=True,
        page_start=page_start,
        page_end=page_end,
    )
    elapsed = time.time() - t0

    print("-" * 70)
    print("[결과] status=%s  time=%.1fs" % (result.status, elapsed))

    if result.error_message:
        print("[오류] %s" % result.error_message)
        return

    data = result.data or {}
    stats = data.get("excel_stats", {})
    print("[통계] 텍스트 행: %s  |  테이블: %s개 (%s행)" % (
        stats.get("text_rows", "?"),
        stats.get("table_count", "?"),
        stats.get("table_rows", "?"),
    ))
    print("[파일] %s" % data.get("excel_filename", "없음"))

    # Show sample of structured questions
    questions = data.get("questions", [])
    if questions:
        print()
        print("=" * 70)
        print("  질문 구조화 결과 (처음 5개)")
        print("=" * 70)
        for q in questions[:5]:
            print()
            print("  번호: %s" % q.get("question_id", "?"))
            text = q.get("question_text", "")
            print("  질문: %s" % (text[:80] + "..." if len(text) > 80 else text))
            print("  페이지: %s" % q.get("page", "?"))

    # Show Excel preview
    excel_path = data.get("excel_path", "")
    if excel_path and os.path.exists(excel_path):
        print()
        print("=" * 70)
        print("  엑셀 미리보기")
        print("=" * 70)
        try:
            import pandas as pd
            xls = pd.ExcelFile(excel_path)
            for sheet in xls.sheet_names:
                df = pd.read_excel(xls, sheet_name=sheet)
                print()
                print("  [시트: %s]  %d행 x %d열" % (sheet, len(df), len(df.columns)))
                print("  컬럼: %s" % list(df.columns))
                # Show first 5 rows
                for i, row in df.head(5).iterrows():
                    vals = []
                    for c in df.columns:
                        v = str(row[c]) if str(row[c]) != "nan" else ""
                        vals.append(v[:40])
                    print("    %s" % " | ".join(vals))
                if len(df) > 5:
                    print("    ... (%d행 더)" % (len(df) - 5))
        except Exception as e:
            print("  [미리보기 오류] %s" % e)

        if auto_open:
            print()
            print("[열기] %s" % excel_path)
            os.startfile(excel_path)

    print()
    print("=" * 70)
    print("  완료!")
    print("=" * 70)


if __name__ == "__main__":
    main()
