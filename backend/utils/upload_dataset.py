import argparse
import re

from dotenv import load_dotenv

# Load environment variables (from backend/.env if needed)
load_dotenv()


def parse_golden_dataset(filepath: str):
    """
    Parses the golden_dataset.md file and extracts questions and expected answers.
    """
    with open(filepath, encoding="utf-8") as f:
        content = f.read()

    dataset_items = []

    # Regex to find "**QXX. [Question]**" and "**Expected Answer:** [Answer]"
    # It accounts for possible line breaks in the answer
    pattern = (
        r"\*\*Q\d+\.\s+(.*?)\*\*\n\*\*Expected Answer:\*\*\s+(.*?)(?=\n\n\*\*Q|\Z)"
    )

    matches = re.finditer(pattern, content, re.DOTALL)
    for match in matches:
        question = match.group(1).strip()
        expected_answer = match.group(2).strip()

        # Skip N/A questions if we want, or keep them to test refusal.
        # We'll keep them to test refusal capability!
        dataset_items.append(
            {
                "input": {"query": question},
                "expected_output": {"response": expected_answer},
            }
        )

    return dataset_items


def upload_to_langfuse(dataset_items: list, dataset_name: str = "golden-eval-v1"):
    try:
        from langfuse import Langfuse
    except ImportError:
        print("Error: langfuse python package not installed.")
        return

    # Initialize Langfuse client
    langfuse = Langfuse()

    # Check if langfuse is properly configured
    if not langfuse.auth_check():
        print(
            "Error: Langfuse authentication failed. Check your environment variables."
        )
        return

    print(f"Creating dataset: {dataset_name}")
    try:
        langfuse.create_dataset(name=dataset_name)
    except Exception:
        # Ignore error if dataset already exists
        pass

    print(f"Uploading {len(dataset_items)} items to {dataset_name}...")
    for item in dataset_items:
        langfuse.create_dataset_item(
            dataset_name=dataset_name,
            input=item["input"],
            expected_output=item["expected_output"],
        )

    print("Upload complete!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upload Golden Dataset to Langfuse")
    parser.add_argument(
        "--file", type=str, required=True, help="Path to golden_dataset.md"
    )
    parser.add_argument(
        "--name",
        type=str,
        default="golden-eval-v1",
        help="Name of the dataset in Langfuse",
    )
    args = parser.parse_args()

    items = parse_golden_dataset(args.file)
    if not items:
        print("No items found in dataset. Check the regex parser.")
    else:
        upload_to_langfuse(items, args.name)
