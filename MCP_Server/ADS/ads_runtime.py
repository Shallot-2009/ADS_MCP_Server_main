from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import sys
import time
import xmlrpc.client
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_LIVE_HOST = "127.0.0.1"
DEFAULT_LIVE_PORT = 8765


def discover_ads_root(explicit: str | os.PathLike[str] | None = None) -> Path:
    """Find ADS without embedding a machine-specific filesystem path."""
    candidates: list[Path] = []

    for value in (explicit, os.environ.get("ADS_INSTALL_ROOT"), os.environ.get("HPEESOF_DIR")):
        if value:
            path = Path(value).expanduser()
            candidates.append(path if path.is_absolute() else PROJECT_ROOT / path)

    if os.name == "nt":
        with contextlib.suppress(ImportError, OSError):
            import winreg

            for base_key in (r"SOFTWARE\Keysight\ADS", r"SOFTWARE\WOW6432Node\Keysight\ADS"):
                with contextlib.suppress(OSError):
                    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, base_key) as ads_key:
                        versions: list[str] = []
                        index = 0
                        while True:
                            try:
                                versions.append(winreg.EnumKey(ads_key, index))
                                index += 1
                            except OSError:
                                break
                        for version in sorted(versions, reverse=True):
                            with contextlib.suppress(OSError):
                                with winreg.OpenKey(ads_key, version + r"\eeenv") as env_key:
                                    value, _ = winreg.QueryValueEx(env_key, "HPEESOF_DIR")
                                    if value:
                                        candidates.append(Path(value))

    for variable in ("ProgramFiles", "ProgramW6432"):
        if os.environ.get(variable):
            candidates.append(Path(os.environ[variable]) / "Keysight" / "ADS2026")

    checked: set[Path] = set()
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved in checked:
            continue
        checked.add(resolved)
        if (resolved / "bin" / "ads.exe").is_file():
            return resolved

    raise FileNotFoundError(
        "ADS 2026 was not found. Set ADS_INSTALL_ROOT once, or repair the Keysight ADS registry entry."
    )


class TimeoutTransport(xmlrpc.client.Transport):
    """XML-RPC transport with a finite socket timeout."""

    def __init__(self, timeout_seconds: float) -> None:
        super().__init__()
        self.timeout_seconds = timeout_seconds

    def make_connection(self, host: str) -> Any:
        connection = super().make_connection(host)
        connection.timeout = self.timeout_seconds
        return connection


def jsonable(value: Any, *, max_items: int = 5000) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        items = list(value.items())[:max_items]
        return {str(k): jsonable(v, max_items=max_items) for k, v in items}
    if isinstance(value, (list, tuple, set)):
        return [jsonable(v, max_items=max_items) for v in list(value)[:max_items]]
    if hasattr(value, "tolist"):
        with contextlib.suppress(Exception):
            return jsonable(value.tolist(), max_items=max_items)
    return repr(value)


class ADSRuntime:
    """Stateful ADS automation controller.

    This class runs in ADS's bundled Python. In that mode the ADS database API
    works headlessly and does not require GUI click automation.
    """

    def __init__(self, ads_root: str | os.PathLike[str] | None = None) -> None:
        self.ads_root = discover_ads_root(ads_root)
        self._de_module: Any | None = None

    @property
    def ads_exe(self) -> Path:
        return self.ads_root / "bin" / "ads.exe"

    @property
    def simulator_exe(self) -> Path:
        return self.ads_root / "bin" / "hpeesofsim.exe"

    @property
    def ads_python(self) -> Path:
        return self.ads_root / "tools" / "python" / "python.exe"

    def _prepare_environment(self) -> None:
        os.environ.setdefault("HPEESOF_DIR", str(self.ads_root))
        os.environ.setdefault("ADS_INSTALL_ROOT", str(self.ads_root))
        bin_dir = str(self.ads_root / "bin")
        parts = os.environ.get("PATH", "").split(os.pathsep)
        if bin_dir not in parts:
            os.environ["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")
        packages = self.ads_root / "tools" / "python" / "packages"
        if packages.exists() and str(packages) not in sys.path:
            sys.path.insert(0, str(packages))
        add_dll_directory = getattr(os, "add_dll_directory", None)
        if add_dll_directory and (self.ads_root / "bin").exists():
            with contextlib.suppress(Exception):
                add_dll_directory(str(self.ads_root / "bin"))

    def _de(self) -> Any:
        if self._de_module is not None:
            return self._de_module
        self._prepare_environment()
        from keysight.ads import de

        self._de_module = de
        return self._de_module

    def preload(self) -> None:
        """Load the native ADS automation module before an async MCP loop starts."""
        self._de()

    def detect(self) -> dict[str, Any]:
        info: dict[str, Any] = {
            "ads_root": str(self.ads_root),
            "ads_root_exists": self.ads_root.exists(),
            "ads_exe": str(self.ads_exe),
            "ads_exe_exists": self.ads_exe.exists(),
            "simulator_exe": str(self.simulator_exe),
            "simulator_exe_exists": self.simulator_exe.exists(),
            "ads_python": str(self.ads_python),
            "ads_python_exists": self.ads_python.exists(),
            "current_python": sys.executable,
            "python_version": sys.version,
            "hpeesof_dir": os.environ.get("HPEESOF_DIR"),
        }
        try:
            de = self._de()
            info.update(
                {
                    "keysight_ads_importable": True,
                    "product_version": de.product_version(),
                    "running_automation": bool(de.running_automation()),
                    "inside_ads_gui": bool(de.is_pde_app()),
                    "workspace_open": bool(de.workspace_is_open()),
                }
            )
        except Exception as exc:
            info["keysight_ads_importable"] = False
            info["import_error"] = f"{type(exc).__name__}: {exc}"
        return info

    def launch_gui(self, workspace_path: str | None = None, extra_args: list[str] | None = None) -> dict[str, Any]:
        if not self.ads_exe.exists():
            raise FileNotFoundError(str(self.ads_exe))
        args = [str(self.ads_exe)]
        if workspace_path:
            args.append(str(Path(workspace_path).expanduser().resolve()))
        args.extend(extra_args or [])
        proc = subprocess.Popen(
            args,
            cwd=str(self.ads_root / "bin"),
            env=os.environ.copy(),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
        )
        return {"started": True, "pid": proc.pid, "command": args}

    def workspace_info(self) -> dict[str, Any]:
        de = self._de()
        if not de.workspace_is_open():
            return {"workspace_open": False}
        wrk = de.active_workspace()
        return {
            "workspace_open": True,
            "path": str(wrk.path),
            "lib_defs_file": str(wrk.lib_defs_file),
            "library_names": sorted(str(x) for x in wrk.library_names),
            "writable_library_names": sorted(str(x) for x in wrk.writable_library_names),
        }

    def open_workspace(self, path: str, force: bool = False) -> dict[str, Any]:
        target = Path(path).expanduser().resolve()
        if not target.exists():
            raise FileNotFoundError(str(target))
        de = self._de()
        de.open_workspace(target, force=force)
        return self.workspace_info()

    def create_workspace(self, path: str, open_after_create: bool = True) -> dict[str, Any]:
        target = Path(path).expanduser().resolve()
        if target.exists():
            raise FileExistsError(str(target))
        de = self._de()
        de.create_workspace(target)
        if open_after_create:
            de.open_workspace(target)
        return self.workspace_info() if open_after_create else {"created": True, "path": str(target)}

    def close_workspace(self) -> dict[str, Any]:
        de = self._de()
        if de.workspace_is_open():
            de.close_workspace()
        return {"workspace_open": False}

    def list_designs(self, include_read_only: bool = False) -> dict[str, Any]:
        de = self._de()
        if not de.workspace_is_open():
            raise RuntimeError("No ADS workspace is open in the headless automation session.")
        wrk = de.active_workspace()
        names = sorted(wrk.library_names if include_read_only else wrk.writable_library_names)
        designs: list[dict[str, Any]] = []
        for lib_name in names:
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

    def design_summary(self, design_name: str, max_instances: int = 500) -> dict[str, Any]:
        de = self._de()
        design = de.db_uu.open_design(design_name, de.db.DesignMode.READ_ONLY)
        instances = []
        for inst in list(design.instances)[:max_instances]:
            instances.append(
                {
                    "name": getattr(inst, "name", None),
                    "component_name": getattr(inst, "component_name", None),
                    "angle": getattr(inst, "angle", None),
                    "origin": jsonable(getattr(inst, "origin", None)),
                }
            )
        return {
            "design": design_name,
            "is_schematic": bool(design.is_schematic),
            "instance_count": len(design.instances),
            "instances": jsonable(instances),
            "net_count": len(design.nets),
            "term_count": len(design.terms),
        }

    def generate_netlist(self, design_name: str, output_path: str | None = None) -> dict[str, Any]:
        de = self._de()
        design = de.db_uu.open_design(design_name, de.db.DesignMode.READ_ONLY)
        netlist = design.generate_netlist()
        result: dict[str, Any] = {"design": design_name, "netlist": netlist}
        if output_path:
            target = Path(output_path).expanduser().resolve()
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(netlist, encoding="utf-8")
            result["output_path"] = str(target)
        return result

    def run_python(self, code: str) -> dict[str, Any]:
        de = self._de()
        stdout = io.StringIO()
        stderr = io.StringIO()
        namespace: dict[str, Any] = {
            "de": de,
            "runtime": self,
            "Path": Path,
            "result": None,
        }
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            exec(compile(code, "<ads-mcp>", "exec"), namespace, namespace)
        return {
            "result": jsonable(namespace.get("result")),
            "stdout": stdout.getvalue(),
            "stderr": stderr.getvalue(),
        }

    def run_simulation(
        self,
        netlist_path: str,
        cwd: str | None = None,
        extra_args: list[str] | None = None,
        timeout_seconds: float = 600.0,
    ) -> dict[str, Any]:
        netlist = Path(netlist_path).expanduser().resolve()
        if not netlist.exists():
            raise FileNotFoundError(str(netlist))
        command = [str(self.simulator_exe), str(netlist), *(extra_args or [])]
        started = time.time()
        completed = subprocess.run(
            command,
            cwd=str(Path(cwd).expanduser().resolve()) if cwd else str(netlist.parent),
            env=os.environ.copy(),
            capture_output=True,
            text=True,
            errors="replace",
            timeout=timeout_seconds,
            check=False,
        )
        return {
            "command": command,
            "returncode": completed.returncode,
            "elapsed_seconds": round(time.time() - started, 3),
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "success": completed.returncode == 0,
        }


class ADSLiveClient:
    """Client for the small XML-RPC addon running inside the ADS GUI."""

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        timeout_seconds: float = 3.0,
    ) -> None:
        self.host = host or os.environ.get("ADS_LIVE_HOST", DEFAULT_LIVE_HOST)
        self.port = int(port or os.environ.get("ADS_LIVE_PORT", DEFAULT_LIVE_PORT))
        self.timeout_seconds = timeout_seconds

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"

    def _proxy(self) -> xmlrpc.client.ServerProxy:
        return xmlrpc.client.ServerProxy(
            self.url,
            allow_none=True,
            use_builtin_types=True,
            transport=TimeoutTransport(self.timeout_seconds),
        )

    @staticmethod
    def ads_gui_running() -> bool:
        completed = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq hpeesofde.exe", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            errors="replace",
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return "hpeesofde.exe" in completed.stdout.lower()

    @staticmethod
    def addon_paths() -> tuple[Path, Path]:
        home = Path.home()
        config = home / "hpeesof" / "config" / "eesof_addons.xml"
        configured_project = Path(os.environ.get("ADS_MCP_ROOT", PROJECT_ROOT)).expanduser()
        if not configured_project.is_absolute():
            configured_project = PROJECT_ROOT / configured_project
        plugin = configured_project / "ads_live_bridge" / "__init__.py"
        return config, plugin

    def status(self) -> dict[str, Any]:
        config, plugin = self.addon_paths()
        status: dict[str, Any] = {
            "connected": False,
            "url": self.url,
            "ads_gui_running": self.ads_gui_running(),
            "addon_config": str(config),
            "addon_config_exists": config.exists(),
            "plugin_file": str(plugin),
            "plugin_file_exists": plugin.exists(),
        }
        if config.exists():
            with contextlib.suppress(Exception):
                text = config.read_text(encoding="utf-8")
                status["addon_enabled_in_config"] = (
                    "ADS Codex MCP Live Bridge" in text and 'Enabled="1"' in text
                )
        try:
            status["ping"] = self.ping()
            status["connected"] = True
        except Exception as exc:
            status["error"] = f"{type(exc).__name__}: {exc}"
        return status

    def ensure_ready(
        self,
        runtime: ADSRuntime,
        launch_if_needed: bool = True,
        wait_seconds: float = 60.0,
        poll_seconds: float = 1.0,
    ) -> dict[str, Any]:
        initial = self.status()
        if initial["connected"]:
            return {"connected": True, "launched": False, "status": initial}

        launched = False
        launch_result: dict[str, Any] | None = None
        if launch_if_needed and not initial["ads_gui_running"]:
            launch_result = runtime.launch_gui()
            launched = True

        deadline = time.monotonic() + max(0.0, wait_seconds)
        last = initial
        while time.monotonic() < deadline:
            time.sleep(max(0.1, poll_seconds))
            last = self.status()
            if last["connected"]:
                return {
                    "connected": True,
                    "launched": launched,
                    "launch_result": launch_result,
                    "status": last,
                }

        return {
            "connected": False,
            "launched": launched,
            "launch_result": launch_result,
            "status": last,
            "guidance": (
                "ADS started but the live bridge did not become ready. Check for the ADS product "
                "license selection window, then verify the user addon is enabled in Tools > App Manager."
            ),
        }

    def call(self, method: str, *args: Any) -> Any:
        proxy = self._proxy()
        try:
            return getattr(proxy, method)(*args)
        except OSError as exc:
            raise ConnectionError(
                f"Cannot reach the ADS live bridge at {self.url}. Open ADS and enable "
                "the 'ADS Codex MCP Live Bridge' addon in Tools > App Manager."
            ) from exc

    def ping(self) -> dict[str, Any]:
        return self.call("ping")

    def workspace_info(self) -> dict[str, Any]:
        return self.call("workspace_info")

    def list_designs(self) -> dict[str, Any]:
        return self.call("list_designs")

    def open_workspace(self, path: str, force: bool = False) -> dict[str, Any]:
        return self.call("open_workspace", path, force)

    def execute_python(self, code: str) -> dict[str, Any]:
        return self.call("execute_python", code)

    def zoom_all(self) -> dict[str, Any]:
        return self.call("zoom_all")
