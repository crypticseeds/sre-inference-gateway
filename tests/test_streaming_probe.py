"""End-to-end integration with the llm-slo-bench Go probe."""

import json
from io import BytesIO
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tarfile
import tempfile
import time

import pytest

pytestmark = pytest.mark.integration


def benchmark_checkout() -> Path:
    """Locate the benchmark from an override or beside the primary gateway repo."""
    override = os.environ.get("LLM_SLO_BENCH_DIR")
    if override:
        return Path(override)
    gateway_dir = Path(__file__).resolve().parents[1]
    git_common_dir = subprocess.run(
        ["git", "rev-parse", "--git-common-dir"],
        cwd=gateway_dir,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    if git_common_dir.returncode != 0:
        return Path("llm-slo-bench")
    common_dir = Path(git_common_dir.stdout.strip())
    if not common_dir.is_absolute():
        common_dir = gateway_dir / common_dir
    return common_dir.resolve().parent.parent / "llm-slo-bench"


def test_go_probe_against_mock_streaming_gateway():
    """Run the reference Go probe against a local no-key mock gateway."""
    go = shutil.which("go")
    if go is None:
        pytest.skip("Go is unavailable")

    bench_dir = benchmark_checkout()
    if not (bench_dir / "go.mod").is_file():
        pytest.skip(f"llm-slo-bench checkout is unavailable at {bench_dir}")

    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]

    with tempfile.TemporaryDirectory() as temp_dir:
        source_dir = Path(temp_dir) / "llm-slo-bench-source"
        archive = subprocess.run(
            ["git", "archive", "HEAD"],
            cwd=bench_dir,
            capture_output=True,
            timeout=30,
            check=False,
        )
        assert archive.returncode == 0, archive.stderr.decode()
        source_dir.mkdir()
        with tarfile.open(fileobj=BytesIO(archive.stdout)) as source_archive:
            source_archive.extractall(source_dir, filter="data")

        binary = Path(temp_dir) / "llm-slo-bench"
        build = subprocess.run(
            [go, "build", "-o", binary, "./cmd/llm-slo-bench"],
            cwd=source_dir,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        assert build.returncode == 0, build.stderr

        environment = os.environ.copy()
        for name in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY"):
            environment.pop(name, None)

        log_path = Path(temp_dir) / "gateway.log"
        with log_path.open("w", encoding="utf-8") as gateway_log:
            gateway = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "app.main:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(port),
                ],
                cwd=Path(__file__).parents[1],
                env=environment,
                stdout=gateway_log,
                stderr=subprocess.STDOUT,
                text=True,
            )
            try:
                deadline = time.monotonic() + 30
                while time.monotonic() < deadline:
                    if gateway.poll() is not None:
                        break
                    try:
                        with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                            break
                    except OSError:
                        time.sleep(0.1)
                else:
                    pytest.fail(f"gateway did not start:\n{log_path.read_text()}")

                assert gateway.poll() is None, log_path.read_text()
                probe = subprocess.run(
                    [
                        binary,
                        "probe",
                        "--endpoint",
                        f"http://127.0.0.1:{port}/v1/chat/completions",
                        "--model",
                        "mock-model",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    check=False,
                )
                assert probe.returncode == 0, (
                    f"probe stderr:\n{probe.stderr}\ngateway log:\n{log_path.read_text()}"
                )
                print(probe.stdout, end="")
                result = json.loads(probe.stdout)
                assert result["status_code"] == 200
                assert result["ttft_ms"] > 0
                assert result["content_events"] > 1
                assert result["usage"] is not None
            finally:
                gateway.terminate()
                try:
                    gateway.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    gateway.kill()
                    gateway.wait(timeout=5)
