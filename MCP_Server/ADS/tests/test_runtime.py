from pathlib import Path

from ads_runtime import ADSLiveClient, ADSRuntime, discover_ads_root, jsonable


def test_default_paths() -> None:
    runtime = ADSRuntime()
    assert runtime.ads_root == discover_ads_root()
    assert runtime.ads_exe.name == "ads.exe"
    assert runtime.simulator_exe.name == "hpeesofsim.exe"
    assert runtime.ads_python.name == "python.exe"


def test_jsonable() -> None:
    assert jsonable({"path": Path("a"), "items": {1, 2}})["path"] == "a"


def test_live_url() -> None:
    assert ADSLiveClient("127.0.0.1", 8765).url == "http://127.0.0.1:8765"


def test_addon_paths(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("ADS_MCP_ROOT", str(tmp_path))
    _, plugin = ADSLiveClient.addon_paths()
    assert plugin == tmp_path / "ads_live_bridge" / "__init__.py"
