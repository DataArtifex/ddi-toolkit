"""BaseX REST client for database management, document loading, and XQuery execution."""

from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import httpx
except ImportError:
    httpx = None  # type: ignore[assignment]

_RequestError: tuple[type[Exception], ...]
if httpx is not None:
    _RequestError = (httpx.RequestError,)
else:
    _RequestError = (Exception,)


class BaseXError(Exception):
    """Base exception for all BaseX operations."""


class BaseXConnectionError(BaseXError):
    """Raised when unable to connect to the BaseX server."""


class BaseXQueryError(BaseXError):
    """Raised when an XQuery or command fails on BaseX."""


class BaseXNotFoundError(BaseXError):
    """Raised when a requested database or resource is not found."""


class BaseXAuthError(BaseXError):
    """Raised on authentication or permission failure."""


@dataclass
class BaseXConfig:
    """Configuration for BaseX REST connection."""

    url: str = "http://localhost:8080/rest"
    username: str = "admin"
    password: str = "admin"
    timeout: float = 60.0
    ssl_verify: bool = True

    @classmethod
    def from_env(cls, env_file: str | Path | None = None) -> BaseXConfig:
        """Creates a configuration object from environment variables and optional .env file."""
        try:
            from dotenv import load_dotenv

            if env_file:
                load_dotenv(dotenv_path=env_file)
            else:
                load_dotenv()
        except ImportError:
            pass

        url = os.getenv("BASEX_URL") or os.getenv("BASEX_REST_URL")
        if not url:
            host = os.getenv("BASEX_HOST", "localhost")
            port = os.getenv("BASEX_PORT", "8080")
            base_path = os.getenv("BASEX_PATH", "/rest").strip("/")
            url = f"http://{host}:{port}/{base_path}"

        username = os.getenv("BASEX_USER") or os.getenv("BASEX_USERNAME") or "admin"
        password = os.getenv("BASEX_PASSWORD") or os.getenv("BASEX_PASS") or "admin"
        timeout_str = os.getenv("BASEX_TIMEOUT", "60.0")
        try:
            timeout = float(timeout_str)
        except ValueError:
            timeout = 60.0

        ssl_verify = os.getenv("BASEX_SSL_VERIFY", "true").lower() in ("true", "1", "yes")

        return cls(
            url=url.rstrip("/"),
            username=username,
            password=password,
            timeout=timeout,
            ssl_verify=ssl_verify,
        )


class BaseXClient:
    """Client for interacting with BaseX via its REST API."""

    def __init__(
        self,
        config: BaseXConfig | None = None,
        *,
        url: str | None = None,
        username: str | None = None,
        password: str | None = None,
        timeout: float | None = None,
        ssl_verify: bool | None = None,
        http_client: Any | None = None,
    ) -> None:
        if config is None:
            config = BaseXConfig.from_env()

        self.config = BaseXConfig(
            url=(url or config.url).rstrip("/"),
            username=username if username is not None else config.username,
            password=password if password is not None else config.password,
            timeout=timeout if timeout is not None else config.timeout,
            ssl_verify=ssl_verify if ssl_verify is not None else config.ssl_verify,
        )

        self._auth: Any | None = None
        if http_client is None:
            if httpx is None:
                raise ImportError(
                    "The BaseX client requires the 'httpx' library. "
                    "Install it directly or install the optional feature: pip install 'dartfx-ddi[basex]'"
                )
            self._auth = httpx.BasicAuth(self.config.username, self.config.password)
            self._client = httpx.Client(
                auth=self._auth,
                timeout=self.config.timeout,
                verify=self.config.ssl_verify,
            )
        else:
            self._client = http_client
            self._auth = getattr(http_client, "auth", None)

        self._owns_client = http_client is None

    def __enter__(self) -> BaseXClient:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def close(self) -> None:
        """Closes the underlying HTTP client session."""
        if self._owns_client and not self._client.is_closed:
            self._client.close()

    def _build_url(self, db_name: str | None = None, path: str | None = None) -> str:
        """Builds a URL for a REST endpoint."""
        url = self.config.url
        if db_name:
            clean_db = db_name.strip("/")
            url = f"{url}/{clean_db}"
            if path:
                clean_path = path.strip("/")
                url = f"{url}/{clean_path}"
        return url

    def _handle_response_error(self, response: Any) -> None:
        """Checks for error status codes and raises appropriate BaseX exceptions."""
        if response.is_success:
            return

        status = response.status_code
        text = response.text

        if status in (401, 403):
            raise BaseXAuthError(f"Authentication failed ({status}): {text}")
        if status == 404:
            raise BaseXNotFoundError(f"Resource not found (404): {text}")
        if status in (400, 409):
            raise BaseXQueryError(f"BaseX operation failed ({status}): {text}")

        raise BaseXError(f"BaseX server error ({status}): {text}")

    def ping(self) -> bool:
        """Checks if the BaseX REST server is reachable and credentials are valid."""
        try:
            response = self._client.get(self.config.url)
            return response.is_success
        except Exception:
            return False

    def list_databases(self) -> list[dict[str, Any]]:
        """Lists all databases available on the BaseX server."""
        try:
            response = self._client.get(self.config.url)
            self._handle_response_error(response)
        except _RequestError as exc:
            raise BaseXConnectionError(f"Failed to connect to BaseX: {exc}") from exc

        # Response XML format: <rest:databases><rest:database resources="X" size="Y">name</rest:database>...
        result: list[dict[str, Any]] = []
        try:
            root = ET.fromstring(response.text)
            for child in root:
                tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                if tag == "database":
                    name = child.text.strip() if child.text else ""
                    resources = int(child.attrib.get("resources", 0))
                    size = int(child.attrib.get("size", 0))
                    result.append(
                        {
                            "name": name,
                            "resources": resources,
                            "size": size,
                        }
                    )
        except ET.ParseError:
            # If server returned empty or non-XML text
            pass

        return result

    def create_db(
        self,
        db_name: str,
        content: bytes | str | Path | None = None,
    ) -> bool:
        """Creates a new database, optionally populating it with initial XML content."""
        url = self._build_url(db_name)
        data: bytes | None = None
        headers: dict[str, str] = {}

        if content is not None:
            if isinstance(content, Path) or (isinstance(content, str) and Path(content).is_file()):
                data = Path(content).read_bytes()
            elif isinstance(content, str):
                data = content.encode("utf-8")
            elif isinstance(content, bytes):
                data = content
            headers["Content-Type"] = "application/xml"

        try:
            response = self._client.put(url, content=data, headers=headers)
            self._handle_response_error(response)
            return response.is_success
        except _RequestError as exc:
            raise BaseXConnectionError(f"Failed to create database '{db_name}': {exc}") from exc

    def drop_db(self, db_name: str) -> bool:
        """Deletes a database from the BaseX server."""
        url = self._build_url(db_name)
        try:
            response = self._client.delete(url)
            self._handle_response_error(response)
            return response.is_success
        except _RequestError as exc:
            raise BaseXConnectionError(f"Failed to drop database '{db_name}': {exc}") from exc

    def list_resources(self, db_name: str) -> list[dict[str, Any]]:
        """Lists all resources stored in the specified database."""
        url = self._build_url(db_name)
        try:
            response = self._client.get(url)
            self._handle_response_error(response)
        except _RequestError as exc:
            raise BaseXConnectionError(f"Failed to list resources in database '{db_name}': {exc}") from exc

        result: list[dict[str, Any]] = []
        try:
            root = ET.fromstring(response.text)
            for child in root:
                tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                if tag in ("resource", "document"):
                    path = child.text.strip() if child.text else ""
                    res_type = child.attrib.get("type", "xml")
                    content_type = child.attrib.get("content-type", "application/xml")
                    size = int(child.attrib.get("size", 0)) if "size" in child.attrib else None
                    result.append(
                        {
                            "path": path,
                            "type": res_type,
                            "content_type": content_type,
                            "size": size,
                        }
                    )
        except ET.ParseError:
            pass

        return result

    def get_db_info(self, db_name: str) -> str:
        """Retrieves info / statistics for the specified database."""
        return self.execute_command(f"OPEN {db_name}\nINFO DB", db_name=db_name)

    def put_document(
        self,
        db_name: str,
        path: str,
        content: bytes | str | Path,
        content_type: str = "application/xml",
    ) -> bool:
        """Stores or replaces a document in the database at the specified path."""
        url = self._build_url(db_name, path)
        data: bytes

        if isinstance(content, Path) or (isinstance(content, str) and Path(content).is_file()):
            data = Path(content).read_bytes()
        elif isinstance(content, str):
            data = content.encode("utf-8")
        elif isinstance(content, bytes):
            data = content
        else:
            raise ValueError(f"Unsupported content type: {type(content)}")

        headers = {"Content-Type": content_type}

        try:
            response = self._client.put(url, content=data, headers=headers)
            self._handle_response_error(response)
            return response.is_success
        except _RequestError as exc:
            raise BaseXConnectionError(f"Failed to put document at '{path}': {exc}") from exc

    def get_document(self, db_name: str, path: str) -> str:
        """Retrieves a document from the database."""
        url = self._build_url(db_name, path)
        try:
            response = self._client.get(url)
            self._handle_response_error(response)
            return response.text
        except _RequestError as exc:
            raise BaseXConnectionError(f"Failed to get document '{path}': {exc}") from exc

    def delete_document(self, db_name: str, path: str) -> bool:
        """Deletes a document from the database."""
        url = self._build_url(db_name, path)
        try:
            response = self._client.delete(url)
            self._handle_response_error(response)
            return response.is_success
        except _RequestError as exc:
            raise BaseXConnectionError(f"Failed to delete document '{path}': {exc}") from exc

    def load_file(
        self,
        db_name: str,
        file_path: str | Path,
        target_path: str | None = None,
    ) -> str:
        """Loads a local file into the specified database.

        Returns the stored document path in BaseX.
        """
        p = Path(file_path)
        if not p.is_file():
            raise FileNotFoundError(f"File not found: {file_path}")

        doc_path = target_path if target_path is not None else p.name
        self.put_document(db_name, doc_path, p)
        return doc_path

    def load_directory(
        self,
        db_name: str,
        dir_path: str | Path,
        pattern: str = "*.xml",
        recursive: bool = True,
    ) -> dict[str, bool]:
        """Loads all matching files in a directory into the database.

        Returns a dictionary mapping document path to success boolean.
        """
        p = Path(dir_path)
        if not p.is_dir():
            raise NotADirectoryError(f"Directory not found: {dir_path}")

        files = p.rglob(pattern) if recursive else p.glob(pattern)
        results: dict[str, bool] = {}

        for f in files:
            if f.is_file():
                rel_path = str(f.relative_to(p)).replace("\\", "/")
                try:
                    ok = self.put_document(db_name, rel_path, f)
                    results[rel_path] = ok
                except Exception as exc:
                    results[rel_path] = False
                    raise BaseXError(f"Failed to upload '{f}': {exc}") from exc

        return results

    def query(
        self,
        xquery: str,
        db_name: str | None = None,
        variables: dict[str, Any] | None = None,
        parameters: dict[str, str] | None = None,
        wrap: bool = False,
    ) -> str:
        """Executes an XQuery against the BaseX server or a specific database.

        Args:
            xquery: The XQuery expression to execute.
            db_name: Optional database context.
            variables: Optional external variable bindings.
            parameters: Optional query serialization parameters.
            wrap: Whether to wrap query results in a <rest:response> element.

        Returns:
            The raw text result from the query execution.
        """
        url = self._build_url(db_name)

        # Build <query xmlns="http://basex.org/rest"> XML payload
        root = ET.Element("query", xmlns="http://basex.org/rest")
        text_el = ET.SubElement(root, "text")
        text_el.text = xquery

        if parameters:
            for name, val in parameters.items():
                ET.SubElement(root, "parameter", name=str(name), value=str(val))

        if wrap:
            ET.SubElement(root, "parameter", name="wrap", value="yes")

        if variables:
            for name, val in variables.items():
                if val is not None:
                    ET.SubElement(root, "variable", name=str(name), value=str(val))

        payload = ET.tostring(root, encoding="utf-8")
        headers = {"Content-Type": "application/xml"}

        try:
            response = self._client.post(url, content=payload, headers=headers)
            self._handle_response_error(response)
            return response.text
        except _RequestError as exc:
            raise BaseXConnectionError(f"Query execution failed: {exc}") from exc

    def execute_command(self, command: str, db_name: str | None = None) -> str:
        """Executes a BaseX command (e.g., 'INFO DB', 'OPTIMIZE')."""
        url = self._build_url(db_name)

        root = ET.Element("command", xmlns="http://basex.org/rest")
        text_el = ET.SubElement(root, "text")
        text_el.text = command

        payload = ET.tostring(root, encoding="utf-8")
        headers = {"Content-Type": "application/xml"}

        try:
            response = self._client.post(url, content=payload, headers=headers)
            self._handle_response_error(response)
            return response.text
        except _RequestError as exc:
            raise BaseXConnectionError(f"Command execution failed: {exc}") from exc

    def run_script(
        self,
        script_path: str,
        db_name: str | None = None,
        variables: dict[str, Any] | None = None,
    ) -> str:
        """Runs a stored XQuery script on the BaseX server."""
        url = self._build_url(db_name)

        root = ET.Element("run", xmlns="http://basex.org/rest")
        text_el = ET.SubElement(root, "text")
        text_el.text = script_path

        if variables:
            for name, val in variables.items():
                ET.SubElement(root, "variable", name=str(name), value=str(val))

        payload = ET.tostring(root, encoding="utf-8")
        headers = {"Content-Type": "application/xml"}

        try:
            response = self._client.post(url, content=payload, headers=headers)
            self._handle_response_error(response)
            return response.text
        except _RequestError as exc:
            raise BaseXConnectionError(f"Run script '{script_path}' failed: {exc}") from exc
