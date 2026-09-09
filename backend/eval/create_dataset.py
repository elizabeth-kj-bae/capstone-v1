"""
본 capstone 도메인의 ICT 운영 질문 Eval Dataset 생성.
"""
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

from langsmith import Client

client = Client()

# Dataset 생성
DATASET_NAME = "capstone-ict-operations"

dataset = client.create_dataset(
    dataset_name=DATASET_NAME,
    description="ICT 운영 지원 agent 평가용 dataset. 본 capstone hands-on용."
)

# 예시 추가
examples = [
    {
        "inputs": {
            "message": "데이터베이스 다운 시 대응 절차를 알려주세요."
        },
        "outputs": {
            "expected_topics": ["DB 진단", "복구 절차", "에스컬레이션"],
            "expected_tools_used": ["search_operations_manual"],
            "should_include_steps": True,
        }
    },
    {
        "inputs": {
            "message": "auth-service 시스템 상태와 관련 ticket을 알려주세요."
        },
        "outputs": {
            "expected_topics": ["시스템 상태", "ticket 목록"],
            "expected_tools_used": ["check_system_status", "search_tickets"],
            "should_include_steps": False,
        }
    },
    {
        "inputs": {
            "message": "운영 매뉴얼과 최근 incident를 종합해 장애 대응 가이드를 만들어 주세요."
        },
        "outputs": {
            "expected_topics": ["매뉴얼", "incident", "통합 가이드"],
            "expected_tools_used": ["search_operations_manual", "search_tickets"],
            "should_include_steps": True,
        }
    },
    {
        "inputs": {
            "message": "네트워크 장애 시 첫 단계는?"
        },
        "outputs": {
            "expected_topics": ["네트워크 진단", "첫 단계"],
            "expected_tools_used": ["search_operations_manual"],
            "should_include_steps": True,
        }
    },
    {
        "inputs": {
            "message": "안녕하세요."
        },
        "outputs": {
            "expected_topics": ["인사"],
            "expected_tools_used": [],
            "should_include_steps": False,
        }
    },
]

client.create_examples(
    inputs=[ex["inputs"] for ex in examples],
    outputs=[ex["outputs"] for ex in examples],
    dataset_id=dataset.id,
)

print(f"Dataset '{DATASET_NAME}' created with {len(examples)} examples.")
print(f"View at: https://smith.langchain.com/datasets/{dataset.id}")
