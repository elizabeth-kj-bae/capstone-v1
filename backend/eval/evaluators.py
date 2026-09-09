from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

# Heuristic
def has_expected_topics(run, example) -> dict:
    """
    응답이 기대 토픽을 포함하는지 검증 (heuristic).
    
    expected_topics 중 절반 이상이 응답에 등장하면 통과.
    """
    response = run.outputs.get("response", "").lower()
    expected = example.outputs.get("expected_topics", [])
    
    if not expected:
        return {"key": "has_expected_topics", "score": 1.0, "comment": "No expected topics."}
    
    found = sum(1 for topic in expected if topic.lower() in response)
    score = found / len(expected)
    
    return {
        "key": "has_expected_topics",
        "score": score,
        "comment": f"Found {found}/{len(expected)} expected topics.",
    }


# LLM-as-a-Judge
judge_llm = ChatOpenAI(model="gpt-4o", temperature=0)


async def response_quality_judge(run, example) -> dict:
    """
    LLM-as-Judge: 응답이 사용자 질문에 적절한가?
    """
    user_question = example.inputs.get("message", "")
    response = run.outputs.get("response", "")
    
    judge_prompt = f"""\
다음은 사용자 질문과 AI agent의 응답입니다.

사용자 질문: {user_question}

AI 응답: {response}

다음 기준으로 응답을 평가하세요:
1. 응답이 사용자 질문에 답하는가?
2. 응답이 명확하고 구조적인가?
3. ICT 운영 도메인의 전문성을 보이는가?

다음 JSON 형식으로 답하세요:
{{
  "score": 0.0-1.0 사이의 숫자,
  "reasoning": "평가 근거 한 문장"
}}
"""
    judge_response = await judge_llm.ainvoke([
        SystemMessage(content="You are an expert evaluator of AI agent responses."),
        HumanMessage(content=judge_prompt),
    ])
    
    import json
    import re
    json_match = re.search(r'\{.*\}', judge_response.content, re.DOTALL)
    parsed = json.loads(json_match.group())
    
    return {
        "key": "response_quality",
        "score": parsed["score"],
        "comment": parsed["reasoning"],
    }
