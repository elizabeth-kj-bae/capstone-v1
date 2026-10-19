"""
본 capstone 시스템의 Layer별 Error Type 정의.

각 Error는 어느 layer에서 발생했고, 어떻게 처리되어야 하는지 명시.
"""
from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional


class ErrorSeverity(str, Enum):
    """Error의 심각도."""
    LOW = "low"        # 부분 기능 손상, 사용자 가치 일부 유지
    MEDIUM = "medium"  # 주요 기능 손상, 사용자 가치 크게 감소
    HIGH = "high"      # 시스템 동작 불가, 사용자 가치 없음


class ErrorLayer(str, Enum):
    """Error가 발생한 layer."""
    DATA = "data_layer"              # Vector DB, External API
    TOOL = "tool_layer"              # MCP server
    ORCHESTRATION = "orchestration"  # Agent, Supervisor
    APPLICATION = "application"      # Backend API
    PRESENTATION = "presentation"    # Frontend


class ErrorRecoverability(str, Enum):
    """Error의 복구 가능성."""
    RECOVERABLE = "recoverable"          # Fallback 또는 partial result 가능
    NON_RECOVERABLE = "non_recoverable"  # 대안 없음, 사용자 통보 필요


class CapstoneError(BaseModel):
    """
    본 capstone 한정으로 표준 Error 표현.
    
    Layer 간 error 전달의 단일 모델.
    각 layer가 이 형식으로 error를 raise하고,
    상위 layer가 이 형식을 받아 결정.
    """
    layer: ErrorLayer = Field(description="Error 발생 layer")
    severity: ErrorSeverity = Field(description="Error 심각도")
    recoverability: ErrorRecoverability = Field(description="복구 가능성")
    
    code: str = Field(description="Error 식별 코드 (예: TOOL_TIMEOUT, LLM_RATE_LIMIT)")
    message: str = Field(description="Internal log용 상세 메시지")
    user_message: Optional[str] = Field(
        default=None,
        description="사용자에게 보일 친화적 메시지 (없으면 generic 안내)"
    )
    
    context: dict = Field(
        default_factory=dict,
        description="Error context (예: tool_name, task_id, retry_count)"
    )


# Layer별 구체 Error type (편의용 factory)

class ToolError(Exception):
    """Tool layer error를 raise할 때 사용."""
    def __init__(self, code: str, message: str, tool_name: str, recoverable: bool = True):
        self.error = CapstoneError(
            layer=ErrorLayer.TOOL,
            severity=ErrorSeverity.MEDIUM if recoverable else ErrorSeverity.HIGH,
            recoverability=ErrorRecoverability.RECOVERABLE if recoverable else ErrorRecoverability.NON_RECOVERABLE,
            code=code,
            message=message,
            user_message=f"'{tool_name}' 도구가 일시적으로 사용 불가합니다." if recoverable else None,
            context={"tool_name": tool_name},
        )
        super().__init__(message)


class OrchestrationError(Exception):
    """Orchestration layer error를 raise할 때 사용."""
    def __init__(self, code: str, message: str, task_id: Optional[str] = None):
        self.error = CapstoneError(
            layer=ErrorLayer.ORCHESTRATION,
            severity=ErrorSeverity.MEDIUM,
            recoverability=ErrorRecoverability.RECOVERABLE,
            code=code,
            message=message,
            context={"task_id": task_id} if task_id else {},
        )
        super().__init__(message)

