"""Supervisor v2 (modular).

v1(legacy 단일 파일)과 동일한 public API를 노출하여 호출자가
변경 없이 두 버전 사이를 전환할 수 있도록 함.

Liskov 원칙:
- v1.__init__.py와 동일한 시그니처
- main.py의 환경변수 분기에서 어느 버전이든 같은 코드로 사용 가능

Refactoring guide의 "두 버전의 공통 인터페이스" 패턴 적용.
"""

from .graph import build_supervisor_graph
from .state import SupervisorState

__all__ = ["build_supervisor_graph", "SupervisorState"]
