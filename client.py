import socket

SERVER_HOST = "localhost"
SERVER_PORT = 8080

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


def send_code_for_execution(host, port, script_content):
    """Connects to the server, sends the script, and prints the response."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((host, port))
            print("--- Sending script to server ---")
            sock.sendall(script_content.encode("utf-8"))

            sock.shutdown(socket.SHUT_WR)

            print("--- Waiting for response ---")
            response = b""
            while True:
                data = sock.recv(1024)
                if not data:
                    break
                response += data

            print("\n--- Server Response ---")
            print(response.decode("utf-8"))

    except ConnectionRefusedError:
        print(f"Error: Connection refused. Is the server running on {host}:{port}?")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    send_code_for_execution(SERVER_HOST, SERVER_PORT, SCRIPT_TO_EXECUTE)
