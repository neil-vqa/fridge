"""
A client library for interacting with a TCP-based remote code execution server.

This module provides a `CodeExecutionClient` class that simplifies the process
of connecting to the server, sending Python code, and receiving the execution
results.
"""

import logging
import socket
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ExecutionResult:
    """
    Represents the result of a remote code execution.

    This is a structured representation of the output received from the server,
    making it easy to access stdout, stderr, and the return code.
    """

    return_code: int
    stdout: str
    stderr: str


class CodeExecutionError(Exception):
    """Base exception for client-side errors."""


class ServerConnectionError(CodeExecutionError):
    """Raised when the client cannot connect to the server."""


class ServerResponseError(CodeExecutionError):
    """Raised when the server returns an error message or invalid response."""


class CodeExecutionClient:
    """
    A client for sending Python code to a remote execution server.

    This class handles the socket connection, data transmission, and response
    parsing, providing a simple interface for remote code execution. It is
    recommended to use this class as a context manager to ensure that
    network resources are properly managed.

    Attributes:
        host (str): The server's hostname or IP address.
        port (int): The port number the server is listening on.
        timeout (int): The socket timeout in seconds for all network operations.

    """

    def __init__(self, host: str, port: int, timeout: int = 60):
        """
        Initializes the CodeExecutionClient.

        Args:
            host: The hostname or IP address of the execution server.
            port: The port number of the server.
            timeout: The timeout in seconds for socket operations.

        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self._socket: Optional[socket.socket] = None
        self._log_extra = {"server_host": self.host, "server_port": self.port}

    def __enter__(self):
        """
        Enters the runtime context and establishes a connection.

        Returns:
            The client instance.

        Raises:
            ServerConnectionError: If the connection to the server fails.

        """
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exits the runtime context, ensuring the connection is closed."""
        self.close()

    def connect(self) -> None:
        """
        Establishes a connection to the remote execution server.

        Raises:
            ServerConnectionError: If a connection cannot be established.

        """
        if self._socket is not None:
            logger.warning(
                "Already connected. Ignoring connect() call.", extra=self._log_extra
            )
            return

        try:
            logger.info("Connecting to server", extra=self._log_extra)
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.settimeout(self.timeout)
            self._socket.connect((self.host, self.port))
            logger.info("Connection established successfully", extra=self._log_extra)
        except (ConnectionRefusedError, socket.timeout, OSError) as e:
            self._socket = None
            msg = f"Failed to connect to {self.host}:{self.port}: {e}"
            raise ServerConnectionError(msg) from e

    def close(self) -> None:
        """Closes the connection to the server if it is open."""
        if self._socket:
            logger.info("Closing connection", extra=self._log_extra)
            try:
                self._socket.close()
            except OSError as e:
                logger.exception(
                    "Error while closing socket", extra=self._log_extra, exc_info=e
                )
            finally:
                self._socket = None

    def execute(self, code: str) -> ExecutionResult:
        """
        Sends Python code to the server for execution and returns the result.

        Args:
            code: A string containing the Python code to execute.

        Returns:
            An ExecutionResult object containing the return code, stdout, and stderr.

        Raises:
            ServerConnectionError: If the client is not connected.
            ServerResponseError: If the server returns a known error message
                                 or an unparsable response.
            CodeExecutionError: For other communication-related errors.

        """
        if self._socket is None:
            msg = "Client is not connected. Call connect() first."
            raise ServerConnectionError(msg)

        try:
            logger.info("Sending script for execution", extra=self._log_extra)
            self._socket.sendall(code.encode("utf-8"))
            self._socket.shutdown(socket.SHUT_WR)

            response = self._receive_all()
            logger.info("Received full response from server", extra=self._log_extra)

            return self._parse_response(response)

        except (socket.timeout, OSError) as e:
            msg = f"A network error occurred: {e}"
            raise CodeExecutionError(msg) from e

    def execute_from_file(self, file_path: Union[str, Path]) -> ExecutionResult:
        """
        Reads code from a file and sends it to the server for execution.

        Args:
            file_path: The path to the Python script file.

        Returns:
            An ExecutionResult object.

        """
        try:
            script_content = Path(file_path).read_text(encoding="utf-8")
            return self.execute(script_content)
        except FileNotFoundError as e:
            msg = f"Script file not found at: {file_path}"
            raise CodeExecutionError(msg) from e
        except OSError as e:
            msg = f"Failed to read script file: {e}"
            raise CodeExecutionError(msg) from e

    def _receive_all(self) -> str:
        """Receives all data from the socket until it's closed by the peer."""
        if not self._socket:
            msg = "Socket is not available for receiving."
            raise ServerConnectionError(msg)

        buffer = bytearray()
        while True:
            try:
                chunk = self._socket.recv(4096)
                if not chunk:
                    break  # Connection closed by the server
                buffer.extend(chunk)
            except socket.timeout:
                msg = "Timed out while waiting for server response."
                raise ServerResponseError(msg) from None

        return buffer.decode("utf-8")

    @staticmethod
    def _parse_response(response: str) -> ExecutionResult:
        """Parses the raw string response from the server into an ExecutionResult."""
        if response.startswith(("ERROR:", "SERVER ERROR:")):
            msg = f"Server returned an error: {response}"
            raise ServerResponseError(msg)

        try:
            header, rest = response.split("\n\n", 1)
            return_code_line = header.splitlines()[1]
            stdout_part, stderr_part = rest.split("\n--- STDERR ---\n")

            return_code_str = return_code_line.replace("Return Code: ", "").strip()
            stdout = stdout_part.replace("--- STDOUT ---\n", "", 1)

            return ExecutionResult(
                return_code=int(return_code_str),
                stdout=stdout,
                stderr=stderr_part,
            )
        except (ValueError, IndexError) as e:
            msg = f"Failed to parse server response: {response}"
            raise ServerResponseError(msg) from e
