from __future__ import annotations

import contextlib
import io
import os
import socketserver
import threading
from pathlib import Path
from typing import Any, TYPE_CHECKING
from xmlrpc.server import SimpleXMLRPCServer

if TYPE_CHECKING:
    from keysight.ads.de.app import Addon


HOST = os.environ.get("ADS_LIVE_HOST", "127.0.0.1")
PORT = int(os.environ.get("ADS_LIVE_PORT", "8765"))
_server: "ThreadedXMLRPCServer | None" = None
_thread: "threading.Thread | None" = None


def _jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(v) for v in value]
    if hasattr(value, "tolist"):
        with contextlib.suppress(Exception):
            return _jsonable(value.tolist())
    return repr(value)


def _main_thread_call(function: Any, *args: Any, **kwargs: Any) -> Any:
    import _pde_app

    state: dict[str, Any] = {}
    done = threading.Event()

    def runner() -> None:
        try:
            state["result"] = function(*args, **kwargs)
        except Exception as exc:
            state["error"] = f"{type(exc).__name__}: {exc}"
        finally:
            done.set()

    _pde_app.ui.execute_in_main_thread(runner)
    if not done.wait(timeout=300):
        raise TimeoutError("ADS main-thread operation timed out after 300 seconds")
    if "error" in state:
        raise RuntimeError(state["error"])
    return _jsonable(state.get("result"))


def _workspace_info() -> dict[str, Any]:
    from keysight.ads import de

    if not de.workspace_is_open():
        return {"workspace_open": False}
    wrk = de.active_workspace()
    return {
        "workspace_open": True,
        "path": str(wrk.path),
        "library_names": sorted(str(x) for x in wrk.library_names),
        "writable_library_names": sorted(str(x) for x in wrk.writable_library_names),
    }


def _list_designs() -> dict[str, Any]:
    from keysight.ads import de

    if not de.workspace_is_open():
        raise RuntimeError("No workspace is open in ADS")
    wrk = de.active_workspace()
    designs: list[dict[str, str]] = []
    for lib_name in sorted(wrk.writable_library_names):
        with contextlib.suppress(Exception):
            lib = wrk.open_library(lib_name)
            for cell in lib.cells:
                for view in cell.views:
                    designs.append(
                        {
                            "library": str(lib_name),
                            "cell": str(cell.name),
                            "view": str(view.name),
                            "lcv": str(view.lcv_name),
                        }
                    )
    return {"count": len(designs), "designs": designs}


def _execute_python(code: str) -> dict[str, Any]:
    from keysight.ads import ael, de
    from keysight.ads.de import app

    stdout = io.StringIO()
    stderr = io.StringIO()
    namespace: dict[str, Any] = {
        "de": de,
        "ael": ael,
        "app": app,
        "Path": Path,
        "result": None,
    }
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        exec(compile(code, "<ads-live-mcp>", "exec"), namespace, namespace)
    return {
        "result": _jsonable(namespace.get("result")),
        "stdout": stdout.getvalue(),
        "stderr": stderr.getvalue(),
    }


class BridgeService:
    def ping(self) -> dict[str, Any]:
        from keysight.ads import de

        return {
            "ok": True,
            "bridge": "ADS Codex MCP Live Bridge",
            "product_version": de.product_version(),
            "host": HOST,
            "port": PORT,
            "inside_ads_gui": bool(de.is_pde_app()),
        }

    def workspace_info(self) -> dict[str, Any]:
        return _main_thread_call(_workspace_info)

    def list_designs(self) -> dict[str, Any]:
        return _main_thread_call(_list_designs)

    def open_workspace(self, path: str, force: bool = False) -> dict[str, Any]:
        def operation() -> dict[str, Any]:
            from keysight.ads import de

            de.open_workspace(str(Path(path).expanduser().resolve()), force=force)
            return _workspace_info()

        return _main_thread_call(operation)

    def execute_python(self, code: str) -> dict[str, Any]:
        return _main_thread_call(_execute_python, code)

    def zoom_all(self) -> dict[str, Any]:
        def operation() -> dict[str, Any]:
            from keysight.ads import ael

            ael.call.de_view_all()
            return {"ok": True}

        return _main_thread_call(operation)


class ThreadedXMLRPCServer(socketserver.ThreadingMixIn, SimpleXMLRPCServer):
    daemon_threads = True
    allow_reuse_address = True


def _start_server() -> None:
    global _server, _thread
    if _server is not None:
        return
    _server = ThreadedXMLRPCServer((HOST, PORT), allow_none=True, logRequests=False)
    _server.register_introspection_functions()
    _server.register_instance(BridgeService())
    _thread = threading.Thread(target=_server.serve_forever, name="ads-codex-mcp-live-bridge", daemon=True)
    _thread.start()
    print(f"ADS Codex MCP Live Bridge listening on http://{HOST}:{PORT}")


def _stop_server() -> None:
    global _server, _thread
    server = _server
    _server = None
    if server is not None:
        server.shutdown()
        server.server_close()
    _thread = None


def setup_addon(addon: "Addon") -> None:
    _start_server()


def shutdown_addon(addon: "Addon") -> None:
    _stop_server()


def identify() -> None:
    print("ADS Codex MCP Live Bridge")
