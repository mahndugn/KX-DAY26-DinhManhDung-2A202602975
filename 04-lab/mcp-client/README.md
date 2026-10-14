# Weather Agent - Google ADK with MCP Server

AI agent built with **Google Agent Development Kit (ADK)** that uses tools from a local **MCP server** via Streamable HTTP transport.

## Architecture

```
┌─────────────────┐      ┌──────────────────┐      ┌─────────────────────┐
│   User Browser  │ ───> │  ADK Web UI      │ ───> │  Weather Agent      │
│   localhost:8000│      │  (Google ADK)    │      │  (Agent with MCP)   │
└─────────────────┘      └──────────────────┘      └─────────────────────┘
                                                             │
                                                             │ Streamable HTTP
                                                             ▼
                                                   ┌─────────────────────┐
                                                   │  MCP Server         │
                                                   │  localhost:8085/mcp │
                                                   │  FastMCP + Tools    │
                                                   └─────────────────────┘
                                                             │
                                                             ▼
                                                   ┌─────────────────────┐
                                                   │  WeatherAPI.com     │
                                                   └─────────────────────┘
```

## Features

- **Remote MCP Tools**: Connects to MCP server via Streamable HTTP
- **3 Weather Tools**:
  - `get_current_weather(city)` - Real-time weather conditions
  - `get_forecast(city, days)` - Weather forecast up to 3 days
  - `health_check()` - Server health verification
- **Web Interface**: UI via ADK web
- **Streaming Responses**: Real-time AI responses

## Quick Start

### 1. Start the MCP Server

```bash
cd ../mcp-server
export WEATHERAPI_KEY="your_weatherapi_key"
uv run python weather.py
```

### 2. Setup Environment

```bash
cd ../mcp-client

# Create .env file with your Google API key
# Get free key from: https://aistudio.google.com/apikey
echo "GOOGLE_API_KEY=your_google_api_key_here" > .env
```

### 3. Install Dependencies

```bash
uv sync
```

### 4. Run the Agent

```bash
uv run adk web
```

### 5. Use the Agent

1. Open browser: http://localhost:8000
2. Select `weather_agent` from dropdown
3. Ask questions like:
   - "What's the weather in Brisbane?"
   - "Give me a 3-day forecast for Tokyo"
   - "How's the weather in New York?"

## Project Structure

```
mcp-client/
├── weather_agent/
│   ├── agent.py           # Main agent with MCP connection
│   └── __init__.py
├── pyproject.toml
├── .env                   # Environment variables (create this)
└── README.md
```

## Configuration

### Agent Configuration

In `weather_agent/agent.py`:

```python
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8085/mcp")

connection_params = StreamableHTTPConnectionParams(
    url=MCP_SERVER_URL,
    timeout=30.0,
)

root_agent = Agent(
    name="weather_agent",
    model="gemini-2.5-flash",
    tools=[weather_tools],
)
```

## Troubleshooting

### Agent won't connect to MCP server

1. **404 errors**: MCP server is not running or wrong port
   - Ensure the MCP server is running on port 8085
   - Check `MCP_SERVER_URL` (env var / `.env`, default `http://localhost:8085/mcp`)

2. **400/405/406 on a browser GET**: the MCP endpoint expects protocol headers and messages.
   - Use `uv run python verify_setup.py` to initialize MCP and call real tools.
   - A plain GET response does not verify the tools or WeatherAPI key.

3. **Timeout errors**: Server not started
   - Start the MCP server first, then the ADK client

### Connection failures and model limits

Connection failures are reported rather than creating an agent without tools.
The agent retries temporary model errors up to three attempts. A Gemini 429 means
the project's quota is exhausted; wait for the retry interval or check your quota.
`verify_setup.py --agent` spaces its three prompts by 35 seconds to avoid the
observed five-requests-per-minute free-tier limit (each tool turn needs at least
two model requests). This check consumes API quota.

## Environment Variables

Create `.env` file:
```bash
GOOGLE_API_KEY=your_gemini_api_key
GOOGLE_GENAI_USE_VERTEXAI=FALSE
MCP_SERVER_URL=http://localhost:8085/mcp
# Optional: GEMINI_MODEL=gemini-2.5-flash
```

`agent.py` explicitly loads `mcp-client/.env`, with an optional
`weather_agent/.env` as a secondary source. Existing process variables take precedence.

## Verify

```bash
uv run python verify_setup.py
uv run python verify_setup.py --agent --output ../../reports/lab04-verification.json
```

The first command tests MCP discovery, health, current Hanoi weather, and a
three-day Tokyo forecast. The second also asserts Gemini emits the expected
function call, receives real tool data, and produces a final answer.

## Resources

- [Google ADK Documentation](https://google.github.io/adk-docs/)
- [MCP Specification](https://modelcontextprotocol.io/)
- [FastMCP GitHub](https://github.com/jlowin/fastmcp)
- [WeatherAPI](https://www.weatherapi.com/)
