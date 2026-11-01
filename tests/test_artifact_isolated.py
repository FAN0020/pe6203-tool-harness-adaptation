"""Actual Docker execution only. No runtime/image installation and no host fallback.

Run with PE6203_ARTIFACT_IMAGE=<reviewed local image@sha256:...>.
All fixtures are generic, independent of MCPEvol answers/trajectories.
"""

import os

import pytest
from test_artifact_validation import GOOD, TESTS, answer, protocol

from pe6203 import artifact_validation as av

pytestmark = pytest.mark.artifact_isolation


@pytest.fixture
def isolated():
    image = os.environ.get("PE6203_ARTIFACT_IMAGE")
    if not image:
        pytest.skip("Actual isolation untested: no explicitly reviewed pinned image configured")
    config = av.settings(protocol(image=image, max_repairs=0, timeout_seconds=1))
    backend = av.DockerBackend(config)
    if not backend.available():
        pytest.skip("Actual isolation untested: Docker/local pinned image unavailable")
    return config, backend


@pytest.mark.asyncio
async def test_real_exact_artifact_with_benign_negative_tests(isolated, tmp_path):
    config, backend = isolated
    result = await av.validate(answer(GOOD), config, tmp_path / "out", backend=backend)
    assert result["status"] == "passed_finite_tests"
    assert result["attempts"][0]["isolated_execution"] is True
    sha = result["accepted_artifact"]["sha256"]
    assert all(
        t["artifact_sha256_before"] == t["artifact_sha256_after"] == sha and t["normal_completion"]
        for t in result["attempts"][0]["tests"]
    )


@pytest.mark.parametrize(
    "source",
    ["raise SystemExit(0)", "import os; os._exit(0)", "open(__file__, 'w').write('# tampered')"],
)
def test_real_early_exit_and_artifact_mutation_never_pass(isolated, source):
    _, backend = isolated
    result = backend.run(source, TESTS[:1])
    assert result["status"] == "test_failed"
    assert result["tests"][0]["normal_completion"] is False


def test_real_network_filesystem_user_environment_boundaries(isolated, tmp_path, monkeypatch):
    _, backend = isolated
    host_marker = tmp_path / "host-only.txt"
    host_marker.write_text("trusted harmless boundary marker")
    monkeypatch.setenv("PE6203_HOST_SECRET_PROBE", "must-not-enter-container")
    source = f"""import os, socket
assert os.getuid() == 65534
assert 'PE6203_HOST_SECRET_PROBE' not in os.environ
assert not os.path.exists({str(host_marker)!r})
try:
 open('/root-write-probe', 'w').write('forbidden')
except OSError:
 pass
else:
 raise AssertionError('root filesystem writable')
s = socket.socket()
s.settimeout(0.2)
try:
 s.connect(('1.1.1.1', 443))
except OSError:
 pass
else:
 raise AssertionError('network reachable')
"""
    result = backend.run(
        source, [{"id": "boundaries", "kind": "negative", "source": "import artifact"}]
    )
    assert result["status"] == "passed_finite_tests"


def test_real_timeout(isolated):
    _, backend = isolated
    result = backend.run(
        "while True: pass", [{"id": "timeout", "kind": "negative", "source": "import artifact"}]
    )
    assert result["status"] == "timeout"


def test_real_test_processes_cannot_contaminate_next_container(isolated):
    _, backend = isolated
    result = backend.run(
        "value = 1",
        [
            {
                "id": "write",
                "kind": "benign",
                "source": "import artifact\nopen('/work/marker','w').write('x')",
            },
            {
                "id": "fresh",
                "kind": "negative",
                "source": "import artifact, os\nassert not os.path.exists('/work/marker')",
            },
        ],
    )
    assert result["status"] == "passed_finite_tests"
