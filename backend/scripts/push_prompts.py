import os
import asyncio
from dotenv import load_dotenv

load_dotenv()

from backend.services.observability.langfuse import langfuse_service
from backend.prompts.registry import FALLBACK_PROMPTS

# The manager prompt is dynamically generated in the code, but we can register it here to keep it centralized in Langfuse
MANAGER_PROMPT = """You are an expert routing agent. Your job is to classify the user's query and route it to the appropriate specialized agent.
Available agents:
- quality: For code quality, code smells, complexity, refactoring, AND Hybrid queries (e.g. correlating SQL maintainability metrics with vector code retrieval).
- performance: For performance optimization, memory profiling, latency improvements, AND Hybrid queries (e.g. correlating SQL error rates with algorithmic complexity).
- architecture: For SOLID principles, design patterns, and system architecture.
- coverage: For unit tests, edge cases, and test coverage.
- metrics: For quantitative code metrics (TSR, cyclomatic complexity score, line counts).
- documentation: For explaining code or generating documentation.
- evaluation: For final scoring or evaluating the overall system.
- repository: For general questions about the codebase, finding files, or if you are unsure.

Route the following query accurately."""

def push_prompts():
    if not langfuse_service.langfuse:
        print("Error: Langfuse is not configured or reachable.")
        return

    langfuse = langfuse_service.langfuse

    print("Pushing prompts to Langfuse Cloud...")

    # Push all fallback prompts
    for prompt_name, prompt_content in FALLBACK_PROMPTS.items():
        print(f"Pushing {prompt_name}...")
        try:
            langfuse.create_prompt(
                name=prompt_name,
                prompt=prompt_content,
                type="text",
                labels=["production"]
            )
            print(f"✅ Successfully pushed {prompt_name}")
        except Exception as e:
            print(f"❌ Failed to push {prompt_name}: {e}")

    # Push the Manager Routing Prompt
    print(f"Pushing manager_routing_prompt...")
    try:
        langfuse.create_prompt(
            name="manager_routing_prompt",
            prompt=MANAGER_PROMPT,
            type="text",
            labels=["production"]
        )
        print(f"✅ Successfully pushed manager_routing_prompt")
    except Exception as e:
        print(f"❌ Failed to push manager_routing_prompt: {e}")

    print("\nAll prompts pushed! They are now centrally managed in your Langfuse Dashboard.")

if __name__ == "__main__":
    push_prompts()
