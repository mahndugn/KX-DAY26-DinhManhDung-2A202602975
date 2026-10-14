"""Weather agent using tools discovered from an HTTP MCP server."""
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from google.adk import Agent
from google.adk.models.google_llm import Gemini
from google.genai import types
from google.adk.tools.mcp_tool.mcp_toolset import (
    McpToolset,
    StreamableHTTPConnectionParams,
)

load_dotenv(Path(__file__).resolve().parent.parent / ".env")
load_dotenv(Path(__file__).with_name(".env"))
logging.getLogger("httpx").setLevel(logging.WARNING)

MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8085/mcp")
weather_tools = McpToolset(
    connection_params=StreamableHTTPConnectionParams(
        url=MCP_SERVER_URL,
        timeout=30.0,
    ),
)

root_agent = Agent(
    name="weather_agent",
    model=Gemini(
        model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        retry_options=types.HttpRetryOptions(attempts=3, initial_delay=2,
                                            http_status_codes=[500, 502, 503, 504]),
    ),
    instruction=(
        "Bạn là trợ lý thời tiết. Trả lời bằng tiếng Việt. "
        "Các tool hỗ trợ thành phố trên toàn thế giới, bao gồm Tokyo. "
        "Tên thành phố trong mô tả tool chỉ là ví dụ, không phải danh sách giới hạn. "
        "Luôn dùng get_current_weather cho thời tiết hiện tại và get_forecast "
        "cho dự báo; không tự bịa dữ liệu. Dự báo hỗ trợ 1 đến 3 ngày. "
        "Dùng health_check khi người dùng yêu cầu kiểm tra server. "
        "Nếu tool báo lỗi, giải thích lỗi thay vì đưa ra số liệu giả."
    ),
    generate_content_config=types.GenerateContentConfig(temperature=0.2),
    tools=[weather_tools],
)
