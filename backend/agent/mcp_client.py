"""
MCP server와의 연결을 관리하는 client.

- MCP server를 subprocess로 실행
- stdio transport로 통신
- LangChain의 BaseTool 형식으로 변환하여 LangGraph agent가 사용 가능하게 함
"""
import os
from pathlib import Path
from langchain_mcp_adapters.client import MultiServerMCPClient


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


async def get_mcp_tools() -> list:
    """
    MCP server에 연결하여 Tool 목록을 LangChain BaseTool 형식으로 반환.

    LangGraph agent에 직접 전달 가능.
    """
    client = MultiServerMCPClient(get_mcp_server_config())
    tools = await client.get_tools()
    return tools
