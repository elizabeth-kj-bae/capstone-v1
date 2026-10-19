"""
MCP server와의 연결을 관리하는 client.

- MCP server를 subprocess로 실행
- stdio transport로 통신
- LangChain의 BaseTool 형식으로 변환하여 LangGraph agent가 사용 가능하게 함
"""
import os
from pathlib import Path
from langchain_mcp_adapters.client import MultiServerMCPClient
from schemas.error import ToolError


# MCP server 위치 (capstone/mcp-server/server.py)
MCP_SERVER_PATH = Path(__file__).parent.parent.parent / "mcp-server" / "server.py"


def get_mcp_server_config() -> dict:
    """
    MCP server 연결 설정.
    
    단일 MCP server를 subprocess로 실행.
    여러 MCP server를 사용하려면 dict에 추가 항목을 넣으면 됨.
    """
    return {
        "ict-operations": {
            "command": "python",
            "args": [str(MCP_SERVER_PATH)],
            "transport": "stdio",
        }
    }


def _wrap_with_tool_error(tool):
    """
    MCP tool의 coroutine을 감싸 어떤 예외든 ToolError로 변환.
    
    LangChain create_agent의 default 동작은 tool 예외를 잡아 LLM에 message로
    전달하지만, handle_tool_error=False + ToolError raise를 통해 supervisor의
    except ToolError 블록까지 전파시킴.
    """
    original_coroutine = tool.coroutine
    
    async def wrapped(**kwargs):
        try:
            return await original_coroutine(**kwargs)
        except Exception as e:
            raise ToolError(
                code="MCP_UNAVAILABLE",
                message=f"MCP tool '{tool.name}' 호출 실패: {e}",
                tool_name=tool.name,
                recoverable=True,
            )
    
    tool.coroutine = wrapped
    tool.handle_tool_error = False

    return tool


async def get_mcp_tools() -> list:
    """
    MCP server에 연결하여 Tool 목록을 LangChain BaseTool 형식으로 반환.
    
    LangGraph agent에 직접 전달 가능.
    """
    client = MultiServerMCPClient(get_mcp_server_config())
    tools = await client.get_tools()

    return [_wrap_with_tool_error(t) for t in tools]   # 수정 
