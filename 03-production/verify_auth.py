"""Test allowed and denied access to the authentication demo on a spare port."""
import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import create_mcp_http_client, streamable_http_client

BASE = Path(__file__).resolve().parent
URL = "http://localhost:8010/mcp"


async def allowed():
    token = os.getenv("MCP_AUTH_TOKEN", "dev-token-abc123")
    async with create_mcp_http_client(headers={"Authorization": f"Bearer {token}"}) as client:
        async with streamable_http_client(URL, http_client=client) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                assert "get_weather" in {tool.name for tool in (await session.list_tools()).tools}
                result = await session.call_tool("get_weather", {"city": "Hanoi"})
                text = result.content[0].text
                assert not result.is_error and "Hanoi: 29" in text
                return text


def main():
    output = BASE.parent / "reports/auth-verification.json"
    output.parent.mkdir(exist_ok=True)
    env = dict(os.environ, MCP_AUTH_PORT="8010", PYTHONIOENCODING="utf-8")
    with (BASE.parent / ".lab-runtime/auth-test.log").open("w", encoding="utf-8") as log:
        server = subprocess.Popen([sys.executable, str(BASE / "auth_server.py")], env=env, stdout=log, stderr=log)
        report = {"passed": False}
        try:
            for _ in range(60):
                if server.poll() is not None:
                    raise RuntimeError("Authentication demo failed to start; check port 8010")
                try:
                    response = httpx.post(URL, json={}, timeout=1)
                    break
                except httpx.ConnectError:
                    time.sleep(0.25)
            else:
                raise TimeoutError("Auth demo did not start")
            report["missing_token_status"] = response.status_code
            assert response.status_code in (401, 403)
            response = httpx.post(URL, json={}, headers={"Authorization": "Bearer invalid-lab-token"}, timeout=5)
            report["invalid_token_status"] = response.status_code
            assert response.status_code in (401, 403)
            report["valid_token_result"] = asyncio.run(allowed())
            report["passed"] = True
            print("PASS auth: missing/invalid token rejected; valid token calls get_weather")
        finally:
            server.terminate()
            server.wait(timeout=10)
            output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
