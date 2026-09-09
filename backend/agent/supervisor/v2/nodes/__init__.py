"""Supervisor v2 node 함수들.

각 노드를 도메인별 파일로 분리하되, 본 __init__.py에서 모두
re-export 하여 호출자(graph.py)는 `from . import nodes`로
동일하게 사용할 수 있음.

도메인별 분리:
- routing:   질문 복잡도 분기 (simple/complex)
- planning:  Task 분해
- research:  MCP tool로 정보 수집 (병렬)
- replan:    Dynamic Planning (평가 + plan 재수립)
- analysis:  정보 분석/가공
- writing:   응답 작성 (재시도 포함)
- validator: 응답 품질 검증
- finalize:  최종 응답 + graceful degradation
"""

from .analysis import execute_analysis_tasks_node
from .finalize import finalize_node
from .planning import planning_node
from .replan import replan_check_node, replan_node
from .research import execute_all_research_tasks_node
from .routing import routing_node, simple_response_node
from .validator import validator_node
from .writing import execute_writing_task_node

__all__ = [
    # graph 실행 순서로 정렬 
    "routing_node",
    "simple_response_node",
    "planning_node",
    "execute_all_research_tasks_node",
    "replan_check_node",
    "replan_node",
    "execute_analysis_tasks_node",
    "execute_writing_task_node",
    "validator_node",
    "finalize_node",
]
