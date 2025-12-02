import logging

from code_exec_client import (
    CodeExecutionClient,
    ExecutionResult,
    ServerConnectionError,
    ServerResponseError,
)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

HOST, PORT = "localhost", 8080


SCRIPT_TO_EXECUTE = """
#!/usr/bin/env python
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "youtube-transcript-api"
# ]
# ///

from youtube_transcript_api import YouTubeTranscriptApi

def fetch_transcript(url):
    video_id = url.split("v=")[1].split("&")[0] if "v=" in url else url.split("/")[-1]
    api = YouTubeTranscriptApi()
    transcript = api.get_transcript(video_id)
    return " ".join([f"{t['text']}" for t in transcript])

url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
print(fetch_transcript(url))

"""


def main():
    # --- Example 1: Basic usage with a `with` statement ---
    logger.info("--- Running Example 1: Basic execution ---")

    try:
        with CodeExecutionClient(HOST, PORT) as client:
            result = client.execute(SCRIPT_TO_EXECUTE)
            print_result(result)
    except (ServerConnectionError, ServerResponseError):
        logger.exception("Execution failed: %s")

    # --- Example 2: Handling a script with an error ---
    logger.info("\n--- Running Example 2: Script with an error and stderr output ---")
    error_script = (
        "import sys\n"
        "print('This will go to stdout.')\n"
        "print('This is an error message.', file=sys.stderr)\n"
        "sys.exit(42)"
    )

    try:
        # You can also manage the connection manually
        client = CodeExecutionClient(HOST, PORT, timeout=10)
        client.connect()
        result = client.execute(error_script)
        print_result(result)
        client.close()
    except ServerConnectionError:
        logger.exception("Could not connect to the server: %s")
    except ServerResponseError:
        logger.exception("Server returned an error: %s")
    except Exception:
        logger.exception(
            "An unexpected error occurred",
        )

    # --- Example 3: Executing from a file (optional) ---
    # This example requires a file named 'my_script.py' to exist.
    # from pathlib import Path
    # if Path("my_script.py").exists():
    #     logger.info("\n--- Running Example 3: Executing from a file ---")
    #     with CodeExecutionClient(HOST, PORT) as client:
    #         result = client.execute_from_file("my_script.py")
    #         print_result(result)


def print_result(result: ExecutionResult):
    """A helper function to neatly print the execution result."""
    print("\n" + "=" * 20 + " Execution Result " + "=" * 20)
    print(f"Return Code: {result.return_code}")
    print("--- STDOUT ---")
    print(result.stdout if result.stdout else "[No stdout]")
    print("--- STDERR ---")
    print(result.stderr if result.stderr else "[No stderr]")
    print("=" * 58 + "\n")


if __name__ == "__main__":
    main()
