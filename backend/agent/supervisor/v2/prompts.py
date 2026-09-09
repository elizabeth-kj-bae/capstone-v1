"""Supervisor graph의 prompt 텍스트.

상수 명명 규칙:
- {DOMAIN}_PROMPT_TEMPLATE: .format()으로 인자 주입하는 prompt
- {AGENT}_AGENT_SYSTEM: sub-agent의 system prompt
- {ROLE}_SYSTEM: 단일 호출의 system message
"""


# ---------------------------------------------------------------------
# Sub-agent system prompts
# ---------------------------------------------------------------------

RESEARCH_AGENT_SYSTEM = (
    "당신은 Research Agent입니다. "
    "주어진 task에 대해 적절한 tool을 호출하여 정보를 수집하세요. "
    "수집된 정보를 명확하게 요약하여 반환하세요."
)


WRITING_AGENT_SYSTEM = (
    "당신은 Writing Agent입니다. "
    "Research Agent가 수집한 정보를 받아 사용자가 이해하기 쉬운 "
    "형태로 통합된 답변을 작성하세요."
)


ANALYSIS_AGENT_SYSTEM = (
    "당신은 Analysis Agent입니다. "
    "Research Agent가 수집한 정보를 분석하는 것이 책임입니다.\n\n"
    "다음 중 적절한 분석 활동을 수행하세요:\n"
    "- 패턴 식별: 데이터에서 반복되는 패턴, 추세 발견\n"
    "- 비교/분류: 정보를 카테고리로 분류하거나 비교\n"
    "- 통합: 여러 source의 정보를 일관된 형태로 통합\n"
    "- 우선순위화: 중요도/긴급도 기반 순위 부여\n\n"
    "Writing Agent와 달리, 사용자에게 직접 전달할 응답이 아닌 "
    "Writing Agent가 활용할 분석 결과를 작성하세요. "
    "구조화된 형태(목록, 표, 카테고리)로 표현하면 좋습니다."
)


# ---------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------

ROUTING_PROMPT_TEMPLATE = """\
다음 사용자 질문을 분석하여 처리 경로를 결정하세요.

사용자 질문: {user_msg}

판단 기준:
- simple: 인사, 메타 질문, 단일 LLM 호출로 답변 가능한 단순 정보 요청
  예: "안녕하세요", "당신은 누구인가요?", "어떻게 사용하나요?"
- complex: 정보 수집(검색), 통합, 분석이 필요한 작업
  예: "DB 다운 시 대응 절차와 incident를 종합해 가이드 작성"

route와 reasoning을 응답하세요.
"""


SIMPLE_RESPONSE_SYSTEM = (
    "당신은 ICT 운영 지원 AI 어시스턴트입니다. "
    "사용자의 질문에 친절하고 정확하게 답변하세요. "
    "복잡한 정보 수집이 필요한 경우 별도 안내가 가능하다고 알려주세요."
)


# ---------------------------------------------------------------------
# Planning
# ---------------------------------------------------------------------

PLANNING_PROMPT_TEMPLATE = """\
사용자 요청을 분석하여 진행 계획(plan), analysis 필요 여부
(needs_analysis), task 목록(tasks)을 작성하세요.

사용자 요청: {user_msg}

[Agent 종류]
- "research": MCP tool로 정보 검색 (운영 매뉴얼, ticket, 시스템 상태 등)
- "analysis": 수집된 정보를 분석/가공 (패턴 식별, 비교/분류, 통합,
  우선순위화, 근본원인)
- "writing": 최종 응답을 사용자 친화적으로 작성 (항상 마지막에 1개)

[needs_analysis 판단 기준]
- False (analysis 불필요): 검색 결과를 필터/나열/요약해 거의 그대로
  전달하면 되는 단순 요청
  예) "critical 등급 incident ticket을 모두 검색해 목록으로 알려주세요"
       → research → writing
  예) "DB 백업 절차 문서를 찾아 알려주세요" → research → writing
- True (analysis 필요): 수집 정보에 대한 가공·추론이 필요한 요청
  예) "최근 incident 3건의 공통 근본원인을 비교 분석해 주세요"
       → research → analysis → writing
  예) "운영 매뉴얼과 과거 incident를 종합해 DB 다운 대응 가이드를 만드세요"
       → research → analysis → writing

[Task 설계 규칙]
- needs_analysis=False이면 tasks에 analysis를 절대 포함하지 마세요.
- needs_analysis=True이면 research 다음, writing 이전에 analysis를
  1개 배치하세요.
- writing task는 항상 마지막에 정확히 1개.
"""


# ---------------------------------------------------------------------
# Replan (Dynamic Planning)
# ---------------------------------------------------------------------

REPLAN_CHECK_PROMPT_TEMPLATE = """\
Research 결과가 사용자 질문에 답하기에 충분한지 판단하세요.

[사용자 질문]
{user_msg}

[수립된 Plan]
{plan}

[현재까지 실행된 Task]
{existing_tasks}

[Research 결과 종합]
{research_summary}{failed_research_context}

[Research의 책임 — 핵심 전제]
Research는 'raw material(원자료)'을 수집하는 단계입니다.
사용자가 요청하는 가이드/요약/답변/보고서/분석/제안 등 **최종 산출물**은
이후 Writing/Analysis 단계가 만듭니다.
따라서 is_sufficient는 "raw material이 충분히 모였는가"만 봅니다.
최종 산출물이 결과에 들어있는지는 판단 기준이 아닙니다.

[판단 절차]
1. 사용자 질문에서 Research가 수집해야 할 'raw material 항목'만 추출하세요.
   (가이드/요약/답변/보고서/분석/제안 같은 합성·가공 산출물은 Research
   항목에서 제외)
2. 각 raw material 항목이 위 Research 결과로 실제로 다뤄지는지 항목별로
   확인하세요.
3. raw material 항목 중 하나라도 결과에서 다뤄지지 않으면
   is_sufficient=False.
   모든 raw material 항목이 다뤄지면 is_sufficient=True.

[유의]
- 추가 Research(replan)는 지연·비용을 유발합니다. "더 자세할 수 있다 /
  사례가 더 있을 수 있다" 같은 한계적·미관상 사유로는 False로 판단하지
  마세요. 구체적으로 요청된 raw material이 빠졌을 때만 False.
- 답변 분량·형식 제약(예: '50자 이내')은 Research 충분성과 무관합니다.
  판단에서 제외하세요.
- "DB 다운 가이드", "incident 종합 보고서" 같은 최종 산출물 표현은
  Writing이 합성할 것이므로 Research 항목으로 카운트하지 마세요.
- 실패한 Research로 특정 raw material이 비었다면, 다른 키워드/source로
  재시도할 가치가 있는지 고려하세요.

[예시]
- 질문 "운영 매뉴얼과 incident를 검색해 DB 다운 가이드를 만드세요" /
  결과에 매뉴얼·incident 모두 존재
  → raw material = [매뉴얼, incident] ('가이드'는 writing의 산출물이라 제외).
    두 항목 모두 충족 → is_sufficient=True
- 질문 "장애 사례 3건을 비교 분석해 주세요" / 결과에 장애 사례 5건 존재
  → raw material = [장애 사례] ('비교 분석'은 analysis의 작업이라 제외).
    충족 → is_sufficient=True
- 질문 "DB 백업 절차와 복구 절차를 알려줘" / 결과에 백업 절차만 있고
  복구 절차 없음
  → raw material = [백업 절차, 복구 절차]. '복구 절차' 누락
    → is_sufficient=False
"""


REPLAN_PLAN_PROMPT_TEMPLATE = """\
직전 plan을 보강하여 갱신된 plan과 추가 research task를 작성하세요.

[사용자 요청]
{user_msg}

[직전 Plan]
{previous_plan}

[완료된 Research 결과 요약]
{research_summary}

[기존 task description (중복 방지)]
{existing_tasks}

[부족 판정 사유 (replan_check)]
{insufficient_reason}

[작성 지침]
- 새 plan은 직전 plan을 보강한 형태로 작성하세요.
  (이미 수집된 raw material은 다시 수집하지 말고, 부족한 부분만
   명시적으로 보강)
- additional_research_tasks에는 추가로 필요한 research task만 포함하세요.
  (analysis/writing은 이후 단계에서 별도 처리되므로 포함 금지)
- 각 task는 기존 task description과 중복되지 않는 새 키워드 또는 새
  source를 사용하세요.
"""


# ---------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------

VALIDATION_PROMPT_TEMPLATE = """\
다음 AI 응답을 평가하세요.

[사용자 질문]
{user_question}

[수립된 Plan]
{plan}

[수집된 정보 (Research 결과 요약)]
{task_summary}

[AI 응답 (검증 대상)]
{draft}

[평가 기준]
1. Relevance: 응답이 사용자 질문에 답하는가
2. Completeness: 수집된 정보(Research 결과)를 충분히 활용했는가
3. Clarity: 응답이 구조적이고 명확한가
4. Domain Appropriateness: ICT 운영 도메인의 전문성을 보이는가

[판단]
- 위 4가지 기준을 모두 충분히 만족하면 is_acceptable=True
- 하나라도 명확히 부족하면 is_acceptable=False
- is_acceptable=False인 경우 feedback에 구체적 개선 지시를 작성
  (예: "X에 대한 정보가 응답에 빠져 있음. 추가 필요" 또는 "응답
   구조가 모호함. 단계별로 정리 필요")
"""
