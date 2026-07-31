# TripPlanner AI

A multi-agent AI travel planner that generates complete trip itineraries — flights, hotels, and a day-by-day plan — from a single natural language request.

## How it works

A [LangGraph](https://www.langchain.com/langgraph) state graph coordinates five agents in sequence:

1. **Flight agent** — looks up airport/airline data via the Aviationstack MCP server and asks the LLM to produce route, airline, duration, and fare guidance.
2. **Hotel agent** — searches the web for hotel recommendations via the Tavily MCP server.
3. **Weather agent** — extracts the destination from the query and fetches current conditions and a forecast via a custom-built weather MCP server.
4. **Itinerary agent** — turns the flight, hotel, and weather results into a day-by-day plan.
5. **Final agent** — formats everything into a single, user-facing response (trip summary, flights, hotels, weather, itinerary, budget, recommendations).

Conversation state is checkpointed to Postgres per `thread_id`, so a planning session can be resumed across requests.

## MCP servers

All tool access goes through [MCP](https://modelcontextprotocol.io/) (Model Context Protocol) via a single `MultiServerMCPClient` in [mcp_client.py](mcp_client.py), which mixes three different ways of running an MCP server:

| Server | Type | Transport | Notes |
|---|---|---|---|
| `tavily` | Cloud-hosted | `streamable_http` | Tavily runs the MCP server; the client just calls `https://mcp.tavily.com/mcp/` with an API key. Nothing to install or run locally. |
| `Aviationstack MCP` | Local, third-party package | `stdio` | The [`aviationstack-mcp`](https://pypi.org/project/aviationstack-mcp/) package is launched locally via `uvx`, and the client talks to it over stdio. The code isn't ours, but the process runs on our machine. |
| `weather` | Local, custom-built | `stdio` | [custom_weather_mcp_server.py](custom_weather_mcp_server.py) is a `FastMCP` server written for this project (`get_current_weather`, `get_forecast`, backed by the OpenWeather API). It's launched as a subprocess (`sys.executable custom_weather_mcp_server.py`) and spoken to over stdio, same as the third-party one — the difference is we own and can extend this one directly. |

This mix demonstrates the three common integration patterns for MCP tools: consuming a provider-hosted server over HTTP, running someone else's server locally over stdio, and running your own.

## Tech stack

- **Backend:** Python, [FastAPI](https://fastapi.tiangolo.com/) + Uvicorn
- **Agent orchestration:** [LangGraph](https://www.langchain.com/langgraph) (`StateGraph`), [LangChain](https://www.langchain.com/) core
- **LLM:** Groq-hosted `llama-3.3-70b-versatile` via `langchain-groq`
- **Tool integration:** [MCP](https://modelcontextprotocol.io/) (Model Context Protocol) via `langchain-mcp-adapters` / `MultiServerMCPClient`
- **State persistence:** PostgreSQL via `psycopg` + `langgraph-checkpoint-postgres`
- **Frontend:** Server-rendered Jinja2 templates with vanilla HTML/CSS/JS
- **Packaging/deployment:** `uv` for dependency management, Docker
- **Observability:** LangSmith tracing (optional)

## APIs used

- **[Groq API](https://groq.com/)** — LLM inference (`llama-3.3-70b-versatile`)
- **[Tavily API](https://tavily.com/)** — web search for hotel discovery, accessed through Tavily's cloud-hosted MCP server
- **[Aviationstack API](https://aviationstack.com/)** — airport and airline data, accessed through the locally-run `aviationstack-mcp` MCP server (via `uvx`)
- **[OpenWeatherMap API](https://openweathermap.org/api)** — current conditions and forecast, accessed through this project's own `custom_weather_mcp_server.py` MCP server
- **[LangSmith](https://www.langchain.com/langsmith)** — optional tracing/observability for the LangGraph runs

## Project structure

```
app.py                       FastAPI app: routes, templates, static files
backend.py                   LangGraph state graph and agent definitions
mcp_client.py                MCP client setup (Tavily + Aviationstack + weather servers)
custom_weather_mcp_server.py Custom MCP server exposing weather tools (OpenWeatherMap)
templates/                    Jinja2 HTML templates
static/                       CSS and JS for the frontend
tools/                        Standalone tool implementations
```

## Setup

1. Install dependencies with [uv](https://docs.astral.sh/uv/):
   ```
   uv sync
   ```
2. Create a `.env` file with the following variables:
   ```
   GROQ_API_KEY=
   DATABASE_URL=            # Postgres connection string (e.g. Render)
   AVIATIONSTACK_API_KEY=
   TAVILY_API_KEY=
   OPENWEATHER_API_KEY=
   DEFAULT_ORIGIN_IATA=      # optional default departure airport
   LANGSMITH_TRACING=        # optional
   LANGSMITH_ENDPOINT=       # optional
   LANGSMITH_API_KEY=        # optional
   LANGSMITH_PROJECT=        # optional
   ```
3. Run the app:
   ```
   uv run uvicorn app:app --reload
   ```
   The app will be available at `http://127.0.0.1:8000`.

### Running with Docker

```
docker build -t tripplanner .
docker run -p 8000:8000 --env-file .env tripplanner
```

## API endpoints

- `GET /` — web UI
- `POST /api/travel` — submit a travel request (`{ "message": str, "thread_id": Optional[str] }`)
- `GET /health` — health check
