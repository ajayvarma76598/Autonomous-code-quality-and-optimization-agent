import asyncio

from dotenv import load_dotenv

load_dotenv()

from backend.agents.metrics.metrics_agent import MetricsAgent  # noqa: E402

from backend.workflows.state import AgentState  # noqa: E402


async def test_sql_agent():
    print("Initializing MetricsAgent...")
    agent = MetricsAgent()

    if not agent.sql_agent:
        print("Failed to initialize SQL Agent.")
        return

    queries = [
        "List files with cyclomatic complexity above 18.",
        "Which services have error rates above 1%?",
        "What is the average response time for the analytics-engine?",
    ]

    for q in queries:
        print("\n======================================")
        print(f"Testing Query: {q}")
        print("======================================")

        state: AgentState = {
            "query": q,
            "session_id": "test_session",
            "messages": [],
            "context": [],
            "requires_escalation": False,
        }

        result_state = agent.execute(state)
        print("\nAgent Response:")
        print(result_state.get("final_response"))


if __name__ == "__main__":
    asyncio.run(test_sql_agent())
