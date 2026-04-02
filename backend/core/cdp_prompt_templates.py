"""
CDP Prompt Templates
카테고리별 Claude 프롬프트 템플릿 (SK ecoplant 최적화)
"""
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.agents.cdp_auto_answer_module import CDPQuestion, AnswerType


SYSTEM_PROMPT = """You are an expert CDP response consultant for SK ecoplant Co., Ltd.

Company Profile:
- Name: SK ecoplant Co., Ltd.
- Industry: Construction / Environmental Services / Clean Energy
- Headquarters: Republic of Korea
- Key Businesses: Hi-tech (semiconductor EPC), Solution (architecture/engineering),
  Energy (fuel cells, hydrogen), Environment (recycling, ITAD)
- Major Subsidiaries: SK ecoplant Engineering, SK oceanplant, SK tes, Re:NEUS, SK ecoplus
- Net Zero Target: 2040
- SBTi Status: Approved (1.5°C aligned)
- Annual Revenue: approximately 9.3 trillion KRW (2024)

Response Rules:
1. MAXIMIZE CDP score — always select the highest-scoring applicable option
2. For "Select from:" questions → return EXACTLY ONE best-scoring option
3. For "Select all that apply" → return ALL truthful and applicable options
4. For text answers → include: specific initiative names, quantitative metrics,
   dates, frameworks referenced (TCFD, SBTi, GHG Protocol, ISO 14064)
5. NEVER fabricate data — mark uncertain values with [VERIFY_REQUIRED]
6. Strictly observe character limits
7. Write in professional English only"""


# ── 유형별 프롬프트 템플릿 ────────────────────────────────────────────────────

SINGLE_SELECT_TEMPLATE = """\
## Task
Select the SINGLE BEST option to maximize the CDP score.

## Question ({q_no})
{main_question}

## Sub-Question #{sub_q_no}
{sub_q_desc}

## Available Options
{options}

## Scoring Criteria
{scoring_criteria}

## Previous Year Answer
{prev_answer}

## Instructions
Return exactly one option from the list above. Choose the option that scores highest.

## Answer:"""


MULTI_SELECT_TEMPLATE = """\
## Task
Select ALL applicable options to maximize the CDP score.

## Question ({q_no})
{main_question}

## Sub-Question #{sub_q_no}
{sub_q_desc}

## Available Options
{options}

## Scoring Criteria
{scoring_criteria}

## Previous Year Answer
{prev_answer}

## Instructions
- Prefix each selected option with "• "
- Select every option that is truthfully applicable to SK ecoplant
- Flag uncertain items with [VERIFY_REQUIRED]

## Answer:"""


TEXT_SHORT_TEMPLATE = """\
## Task
Write a concise CDP response within {max_chars} characters.

## Question ({q_no})
{main_question}

## Sub-Question #{sub_q_no}
{sub_q_desc}

## Scoring Criteria
{scoring_criteria}

## Previous Year Answer
{prev_answer}

## Company Context
{company_context}

## Instructions
- Be specific: name initiatives, include dates and quantities
- Reference relevant frameworks: TCFD, SBTi, GHG Protocol, ISO 14064
- Structure: Context → Action → Result/Impact
- Stay strictly within {max_chars} characters

## Answer:"""


TEXT_LONG_TEMPLATE = """\
## Task
Write a comprehensive CDP response within {max_chars} characters.

## Question ({q_no})
{main_question}

## Sub-Question #{sub_q_no}
{sub_q_desc}

## Scoring Criteria
{scoring_criteria}

## Previous Year Answer (improve upon this)
{prev_answer}

## Company Context
{company_context}

## Structure Guide
1. Context & Governance (20%): Board/C-suite involvement, strategy integration
2. Process & Methodology (30%): Frameworks (TCFD, SBTi), frequency, scope, tools used
3. Actions & Results (30%): Concrete initiatives, quantitative outcomes, YoY progress
4. Future Plans & Ambition (20%): Short/medium/long-term targets, Net Zero 2040 roadmap

## Instructions
- Maximum {max_chars} characters — do not exceed
- Flag unverifiable data with [VERIFY_REQUIRED]
- Reference specific SK ecoplant programs and metrics where known

## Answer:"""


NUMERICAL_TEMPLATE = """\
## Task
Provide the correct numerical value.

## Question ({q_no})
{main_question}

## Sub-Question #{sub_q_no}
{sub_q_desc}

## Format / Unit
{options}

## Previous Year Answer
{prev_answer}

## Instructions
Return ONLY the number (no text, no units, no commas).
If the value is unknown or needs verification: [DATA_REQUIRED]

## Answer:"""


GROUPED_OPTION_TEMPLATE = """\
## Task
Select appropriate options from each group.

## Question ({q_no})
{main_question}

## Sub-Question #{sub_q_no}
{sub_q_desc}

## Option Groups
{options}

## Scoring Criteria
{scoring_criteria}

## Previous Year Answer
{prev_answer}

## Output Format
Group Name
☑ Selected Option 1
☑ Selected Option 2

## Answer:"""


# ── 특수 고배점 문항 템플릿 ───────────────────────────────────────────────────

CLIMATE_RISK_TABLE_PROMPT = """\
## CDP Q3.1.1 — Climate Risk/Opportunity Details (Table Format)

For EACH identified risk/opportunity, provide ALL required fields:
Identifier | Value chain location | Risk/Opportunity type |
Financial impact description | Time horizon | Likelihood | Magnitude |
Financial figures (short/medium/long, min/max) |
Response description | Management cost | Additional explanation

## Scoring Criteria
{scoring_criteria}

## Previous Year Answer
{prev_answer}

## Instructions
- Every completed row cell contributes proportionally to the score
- Fill ALL 30 fields for each item
- Do not leave any mandatory field blank
- Flag data gaps with [VERIFY_REQUIRED]

## Answer:"""


EMISSIONS_TARGET_PROMPT = """\
## CDP Q7.53.1 — Absolute Emissions Reduction Target

## Maximum Score Path
- SBTi approved + 1.5°C aligned → Leadership (3/3 L points)
- Organization-wide + ≥95% base year coverage → Management (4/4 M points)
- Progress: % achieved ≥ % time elapsed → Management credit
- Quantitative targets with base/target year → Disclosure + Awareness

## SK ecoplant Facts
- SBTi: Approved, 1.5°C aligned
- Net Zero Target Year: 2040
- Base Year: 2021
- Scope: Organization-wide

## Scoring Criteria
{scoring_criteria}

## Previous Year Answer
{prev_answer}

## Answer:"""


# ── 프롬프트 빌더 함수 ────────────────────────────────────────────────────────

def build_prompt_for_question(
    question: "CDPQuestion",
    company_context: str = "",
    template_override: str = None,
) -> str:
    """
    문항 유형에 맞는 템플릿 선택 후 SYSTEM_PROMPT와 결합하여 반환.
    """
    from backend.agents.cdp_auto_answer_module import AnswerType

    # 특수 문항 처리
    if template_override:
        template = template_override
    elif question.q_no in ("[3.1.1]", "3.1.1"):
        template = CLIMATE_RISK_TABLE_PROMPT
    elif question.q_no in ("[7.53.1]", "7.53.1"):
        template = EMISSIONS_TARGET_PROMPT
    else:
        _tmap = {
            AnswerType.SINGLE_SELECT:  SINGLE_SELECT_TEMPLATE,
            AnswerType.MULTI_SELECT:   MULTI_SELECT_TEMPLATE,
            AnswerType.TEXT_SHORT:     TEXT_SHORT_TEMPLATE,
            AnswerType.TEXT_LONG:      TEXT_LONG_TEMPLATE,
            AnswerType.NUMERICAL:      NUMERICAL_TEMPLATE,
            AnswerType.PERCENTAGE:     NUMERICAL_TEMPLATE,
            AnswerType.DATE:           NUMERICAL_TEMPLATE,
            AnswerType.GROUPED_OPTION: GROUPED_OPTION_TEMPLATE,
        }
        template = _tmap.get(question.answer_type, TEXT_SHORT_TEMPLATE)

    # 채점 기준 조립
    sc_parts = []
    for label, val in [
        ("D", question.scoring_dc),
        ("A", question.scoring_ac),
        ("M", question.scoring_mc),
        ("L", question.scoring_lc),
    ]:
        if val and val.strip() and val.strip() != "Not scored.":
            sc_parts.append(f"[{label}] {val.strip()}")
    scoring_text = "\n".join(sc_parts) if sc_parts else "Not scored."

    # 글자 수 제한 추출
    mc_match = re.search(r"maximum ([\d,]+) characters?", question.sub_q_options or "", re.IGNORECASE)
    max_chars = int(mc_match.group(1).replace(",", "")) if mc_match else 2500

    prompt_body = template.format(
        q_no            = question.q_no,
        main_question   = question.main_question   or "",
        sub_q_no        = question.sub_q_no        or "",
        sub_q_desc      = question.sub_q_desc      or "",
        options         = question.sub_q_options   or "",
        scoring_criteria= scoring_text,
        prev_answer     = question.prev_year_answer or "No previous answer available",
        company_context = company_context,
        max_chars       = max_chars,
    )
    return f"{SYSTEM_PROMPT}\n\n---\n\n{prompt_body}"


def build_batch_prompt(
    questions: list,
    company_context: str = "",
    max_per_batch: int = 5,
) -> list:
    """
    같은 q_no의 서브 문항들을 배치 처리 — API 호출 횟수 절감.
    단순 선택형/단일 서브 문항에 적합. 긴 서술형은 개별 호출 권장.
    """
    groups: dict = {}
    for q in questions:
        groups.setdefault(q.q_no, []).append(q)

    prompts = []
    for qno, gqs in groups.items():
        for i in range(0, len(gqs), max_per_batch):
            batch = gqs[i:i + max_per_batch]
            parts = [
                SYSTEM_PROMPT,
                f"\n## Batch Processing: {qno} "
                f"(Sub #{batch[0].sub_q_no} – #{batch[-1].sub_q_no})\n",
                "Answer each sub-question below. Format your response as:\n"
                "###SUB_Q_{number}###\n{answer}\n",
            ]
            for q in batch:
                parts.append(
                    f"### Sub #{q.sub_q_no}: {q.sub_q_desc}\n"
                    f"Options: {q.sub_q_options}\n"
                    f"Previous: {q.prev_year_answer or 'None'}\n"
                )
            prompts.append("\n".join(parts))
    return prompts


def parse_batch_response(response_text: str) -> dict:
    """배치 응답에서 SUB_Q 번호별 답변 파싱"""
    return {
        m[0].strip(): m[1].strip()
        for m in re.findall(
            r"###SUB_Q_(\d+)###\s*\n(.*?)(?=###SUB_Q_|\Z)",
            response_text,
            re.DOTALL,
        )
    }
