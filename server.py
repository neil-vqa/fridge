import logging
import socketserver
import subprocess
import tempfile
from pathlib import Path

HOST, PORT = "0.0.0.0", 8080
EXECUTION_TIMEOUT = 30  # in seconds
MAX_SCRIPT_SIZE = 1024 * 60  # 60 KB

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(threadName)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ThreadingCodeExecutionHandler(socketserver.BaseRequestHandler):
    def handle(self):
        log_extra = {"client_ip": self.client_address[0]}
        logger.info("Accepted connection", extra=log_extra)

        try:
            script_bytes = bytearray()
            while True:
                if len(script_bytes) > MAX_SCRIPT_SIZE:
                    logger.error("Exceeded max script size limit", extra=log_extra)
                    self.request.sendall(b"ERROR: Script size exceeds limit.")
                    return

                chunk = self.request.recv(4096)
                if not chunk:
                    break
                script_bytes.extend(chunk)

            if not script_bytes:
                logger.warning("No data received from client.", extra=log_extra)
                return

            script_code = script_bytes.decode("utf-8")

            with tempfile.TemporaryDirectory() as exec_dir:
                log_extra["exec_dir"] = exec_dir
                logger.info("Created isolated execution directory", extra=log_extra)

                script_path = Path(exec_dir) / "main.py"
                with open(script_path, "w") as script_file:
                    script_file.write(script_code)

                log_extra["script_path"] = script_path
                logger.info("Saved received code to temporary file", extra=log_extra)

                try:
                    process = subprocess.run(
                        ["uv", "run", "main.py"],
                        capture_output=True,
                        text=True,
                        timeout=EXECUTION_TIMEOUT,
                        check=False,
                        cwd=exec_dir,
                    )

                    log_extra["return_code"] = process.returncode
                    logger.info("Execution finished", extra=log_extra)

                    response = (
                        f"--- Execution Result ---\n"
                        f"Return Code: {process.returncode}\n\n"
                        f"--- STDOUT ---\n{process.stdout}\n"
                        f"--- STDERR ---\n{process.stderr}"
                    ).encode("utf-8")

                    self.request.sendall(response)

                except subprocess.TimeoutExpired:
                    logger.exception(
                        f"Script timed out after {EXECUTION_TIMEOUT}s", extra=log_extra
                    )
                    self.request.sendall(f"ERROR: Execution timed out".encode("utf-8"))

        except UnicodeDecodeError:
            logger.error("Failed to decode received data as UTF-8", extra=log_extra)
            self.request.sendall(b"ERROR: Invalid UTF-8 data received.")
        except Exception:
            logger.error(
                "An unexpected error occurred in the handler",
                extra=log_extra,
                exc_info=True,
            )
            self.request.sendall(b"SERVER ERROR: An internal error occurred.")
        finally:
            logger.info("Connection closed", extra=log_extra)


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    """A threaded TCP server."""

    daemon_threads = True
    allow_reuse_address = True


if __name__ == "__main__":
    logger.info(f"Starting threaded server on {HOST}:{PORT}")
    with ThreadedTCPServer((HOST, PORT), ThreadingCodeExecutionHandler) as server:
        server.serve_forever()
