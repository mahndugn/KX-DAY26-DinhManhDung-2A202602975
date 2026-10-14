"""Verify real MCP tool calls; optionally verify the Gemini/ADK loop."""
import argparse
import asyncio
from datetime import datetime, timezone
import importlib
import json
import logging
import os
from pathlib import Path
import sys

BASE = Path(__file__).resolve().parent
logging.basicConfig(level=logging.WARNING)


def safe_error(exc):
    message = f"{type(exc).__name__}: {exc}"
    for key in ("GOOGLE_API_KEY", "GEMINI_API_KEY", "WEATHERAPI_KEY"):
        value = os.getenv(key)
        if value:
            message = message.replace(value, "[REDACTED]")
    return message


def tool_text(result):
    return "\n".join(part.text for part in result.content if getattr(part, "text", None))


async def verify_mcp(report):
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client

    url = os.getenv("MCP_SERVER_URL", "http://localhost:8085/mcp")
    async with streamablehttp_client(url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            names = {tool.name for tool in (await session.list_tools()).tools}
            expected = {"health_check", "get_current_weather", "get_forecast"}
            assert expected <= names, f"Missing tools: {expected - names}"
            report["discovered_tools"] = sorted(names)
            for name, args, marker in (
                ("health_check", {}, "running"),
                ("get_current_weather", {"city": "Hanoi"}, "Temperature:"),
                ("get_forecast", {"city": "Tokyo", "days": 3}, "Chance of Rain:"),
            ):
                result = await session.call_tool(name, args)
                body = tool_text(result)
                assert not result.isError and marker in body, f"{name} returned no valid data: {body}"
                if name == "get_forecast":
                    assert body.count("Chance of Rain:") == 3, "Expected three forecast days"
                report["mcp_calls"].append({"tool": name, "arguments": args, "result": body})
                print(f"PASS MCP {name}")


async def verify_agent(report):
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types
    from weather_agent import root_agent

    sessions = InMemorySessionService()
    runner = Runner(agent=root_agent, app_name="weather_agent", session_service=sessions)
    try:
        for index, (prompt, expected_tool, marker) in enumerate((
            ("Hãy gọi health_check để kiểm tra server.", "health_check", "running"),
            ("Dùng tool lấy thời tiết hiện tại ở Hanoi, trả lời tiếng Việt.", "get_current_weather", "Temperature:"),
            ("Dùng tool lấy dự báo thời tiết Tokyo trong 3 ngày, kèm khả năng mưa.", "get_forecast", "Chance of Rain:"),
        )):
            if index:
                # Each tool interaction uses at least two model requests.
                # Space cases to stay within the observed free-tier quota.
                print("Waiting 35 seconds before the next Gemini case...", flush=True)
                await asyncio.sleep(35)
            session = await sessions.create_session(app_name="weather_agent", user_id="lab_verification")
            trace = {"prompt": prompt, "calls": [], "responses": [], "answer": ""}
            async for event in runner.run_async(
                user_id=session.user_id, session_id=session.id,
                new_message=types.Content(role="user", parts=[types.Part(text=prompt)]),
            ):
                for part in (event.content.parts if event.content else []):
                    if part.function_call:
                        trace["calls"].append({"name": part.function_call.name, "args": part.function_call.args})
                    if part.function_response:
                        trace["responses"].append({"name": part.function_response.name, "response": part.function_response.response})
                if event.is_final_response() and event.content:
                    trace["answer"] += "".join(part.text or "" for part in event.content.parts)
            report["agent_traces"].append(trace)
            assert any(call["name"] == expected_tool for call in trace["calls"]), f"Agent did not call {expected_tool}"
            assert any(response["name"] == expected_tool for response in trace["responses"]), "Missing tool response"
            assert any(marker in json.dumps(response["response"], ensure_ascii=False)
                       for response in trace["responses"] if response["name"] == expected_tool), "Tool returned no weather data"
            assert trace["answer"].strip(), "Missing final answer"
            print(f"PASS ADK/Gemini {expected_tool}")
    finally:
        await runner.close()


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent", action="store_true", help="Also call Gemini through ADK (uses API quota)")
    parser.add_argument("--output", type=Path, help="Save JSON evidence without API keys")
    args = parser.parse_args()
    report = {"timestamp_utc": datetime.now(timezone.utc).isoformat(), "passed": False,
              "mcp_calls": [], "agent_traces": []}
    try:
        from dotenv import load_dotenv
        load_dotenv(BASE / ".env")
        load_dotenv(BASE / "weather_agent" / ".env")
        if not os.getenv("GOOGLE_API_KEY"):
            raise ValueError("GOOGLE_API_KEY is missing")
        for module in ("google.adk", "google.genai", "mcp", "dotenv", "httpx"):
            importlib.import_module(module)
        print("PASS configuration and dependencies (keys hidden)")
        from weather_agent import root_agent
        assert root_agent.tools, "Agent has no tools"
        report["model"] = root_agent.model.model
        await asyncio.wait_for(verify_mcp(report), timeout=120)
        if args.agent:
            await asyncio.wait_for(verify_agent(report), timeout=240)
        report["passed"] = True
    except Exception as exc:
        report["error"] = safe_error(exc)
        print("FAIL " + report["error"])
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Evidence saved: {args.output}")
    print("All requested checks passed." if report["passed"] else "Verification failed.")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
