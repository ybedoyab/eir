"""Vertex AI Veo adapter, with a deterministic "unavailable" fallback.

The clip is never handed to the browser as a raw gs:// or public URL — it is written to our
own storage (GCS if configured, else local disk) and served back through a backend route
(`GET /api/v1/recovery/{episode_id}/video/{filename}`), so the storage stays private.

Cheapest-tier-first for the MVP: defaults to the Veo "fast" tier, which is also the only tier
in the current Veo generation with native synchronized audio narration — that narration is the
"captions" for this feature (see plan §7); no separate TTS/captioning pipeline.

**Storage is content-addressed** (plan §15.3). The object key is a hash of the model and the
prompt, so every episode seeded from the same care-plan task list shares one stored clip and
one Veo call, no matter how many episodes exist or how often the page is reloaded. Cost and
bytes scale with the number of *distinct task lists*, not with the number of clicks.

The exception is a deliberate "Regenerate" (``force=True``), which must actually call Veo — it
is the live demo control. Those land under a per-episode ``clips/adhoc/`` prefix that is pruned
to a single object on write and swept by a short bucket lifecycle rule, so forcing cannot
accumulate either.
"""

from __future__ import annotations

import hashlib
import logging
import re
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from app.repositories.video_budget import utc_day

logger = logging.getLogger("eir.recovery_video")

CACHED_PREFIX = "clips/"
ADHOC_PREFIX = "clips/adhoc/"

# Filenames are minted by _target() below, never by a caller. The route re-derives the storage
# key from an untrusted URL path, so both halves are matched against these before they are
# joined into a path — no traversal reaches the filesystem or the bucket.
_FILENAME_RE = re.compile(r"(adhoc-)?[0-9a-f]{16,64}\.mp4")
_EPISODE_ID_RE = re.compile(r"[A-Za-z0-9._:-]{1,128}")


def storage_key(episode_id: str, filename: str) -> str | None:
    """Map an untrusted ``{episode_id}/video/{filename}`` URL pair to a storage key.

    Returns None when either half is not something this module minted.
    """
    if not _FILENAME_RE.fullmatch(filename):
        return None
    if not filename.startswith("adhoc-"):
        # Cached clips are shared across episodes by design — the key carries no episode.
        return f"{CACHED_PREFIX}{filename}"
    if not _EPISODE_ID_RE.fullmatch(episode_id):
        return None
    return f"{ADHOC_PREFIX}{episode_id}/{filename}"


@dataclass
class VideoResult:
    ok: bool
    video_url: str = ""
    storage_key: str = ""
    duration_seconds: float = 0.0
    model: str = ""
    cached: bool = False
    error: str | None = None


class VideoStorage(Protocol):
    def exists(self, key: str) -> bool: ...

    def save(self, key: str, data: bytes) -> None: ...

    def read(self, key: str) -> bytes | None: ...

    def prune(self, prefix: str, *, keep: str) -> int: ...

    def describe(self) -> dict[str, Any]: ...


class LocalVideoStorage:
    """Local-disk storage, same shape as the file-store adapters used elsewhere.

    Laptop-only. On Cloud Run the filesystem is RAM *and* the worker that generates a clip is
    a different container from the API that serves it, so a deployed environment must set
    ``RECOVERY_VIDEO_BUCKET`` (plan §15.1).
    """

    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        return self._base_dir / key

    def exists(self, key: str) -> bool:
        return self._path(key).exists()

    def save(self, key: str, data: bytes) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def read(self, key: str) -> bytes | None:
        path = self._path(key)
        return path.read_bytes() if path.is_file() else None

    def prune(self, prefix: str, *, keep: str) -> int:
        directory = self._base_dir / prefix
        if not directory.is_dir():
            return 0
        removed = 0
        for path in directory.iterdir():
            if path.is_file() and str(path.relative_to(self._base_dir).as_posix()) != keep:
                path.unlink()
                removed += 1
        return removed

    def describe(self) -> dict[str, Any]:
        return {"backend": "local", "path": str(self._base_dir)}


class GcsVideoStorage:
    """Private GCS bucket. Bytes are always proxied back through our own backend route."""

    def __init__(self, bucket_name: str) -> None:
        self._bucket_name = bucket_name
        self._client: Any | None = None

    def _bucket(self) -> Any:
        if self._client is None:
            from google.cloud import storage

            self._client = storage.Client()
        return self._client.bucket(self._bucket_name)

    def exists(self, key: str) -> bool:
        return bool(self._bucket().blob(key).exists())

    def save(self, key: str, data: bytes) -> None:
        self._bucket().blob(key).upload_from_string(data, content_type="video/mp4")

    def read(self, key: str) -> bytes | None:
        blob = self._bucket().blob(key)
        if not blob.exists():
            return None
        return blob.download_as_bytes()

    def prune(self, prefix: str, *, keep: str) -> int:
        removed = 0
        for blob in self._bucket().list_blobs(prefix=prefix):
            if blob.name != keep:
                blob.delete()
                removed += 1
        return removed

    def describe(self) -> dict[str, Any]:
        return {"backend": "gcs", "bucket": self._bucket_name}


class RunClaimStore(Protocol):
    """Structural view of ``SchedulerIdempotencyStore`` — kept local so this adapter does not
    depend on the repositories package (the composition root wires the concrete one)."""

    def claim_run(self, key: str) -> bool: ...


class DailyCounter(Protocol):
    def increment(self, day: str, *, limit: int) -> bool: ...

    def used(self, day: str) -> int: ...


class VideoQuota(Protocol):
    def claim(self, episode_id: str) -> str | None:
        """Return None when generation may proceed, else a machine-readable refusal reason."""

    def describe(self) -> dict[str, Any]: ...


@dataclass
class StoreBackedVideoQuota:
    """Per-episode cooldown plus a global daily ceiling.

    The frontend's disabled button is not a control — a second tab or a curl loop defeats it —
    so the limit that actually protects the bill lives here, behind durable stores shared by
    the API and the worker.
    """

    claims: RunClaimStore
    counter: DailyCounter
    cooldown_seconds: int
    daily_limit: int

    def claim(self, episode_id: str) -> str | None:
        if self.cooldown_seconds > 0:
            window = int(time.time()) // self.cooldown_seconds
            if not self.claims.claim_run(f"recovery-video:{episode_id}:{window}"):
                return "cooldown"
        if self.daily_limit > 0 and not self.counter.increment(utc_day(), limit=self.daily_limit):
            return "daily_limit_reached"
        return None

    def describe(self) -> dict[str, Any]:
        return {
            "cooldown_seconds": self.cooldown_seconds,
            "daily_limit": self.daily_limit,
            "used_today": self.counter.used(utc_day()),
        }


class UnlimitedVideoQuota:
    """No-op quota for fakes and tests."""

    def claim(self, episode_id: str) -> str | None:
        return None

    def describe(self) -> dict[str, Any]:
        return {"cooldown_seconds": 0, "daily_limit": 0, "used_today": 0}


class VideoGenerationClient(Protocol):
    adapter_name: str
    available: bool
    # Read by the prompt builder: narration has to fit inside the clip, so the word budget is
    # derived from the configured length rather than hardcoded a second time.
    duration_seconds: int

    def generate(self, *, prompt: str, episode_id: str, force: bool = False) -> VideoResult: ...

    def read(self, *, episode_id: str, filename: str) -> bytes | None: ...

    def status(self) -> dict[str, Any]: ...


class UnavailableVideoClient:
    """Deterministic fallback: no video generated, honestly reported. Never fails silently by
    pretending to have produced something."""

    adapter_name = "video_unavailable"
    available = False
    duration_seconds = 8

    def generate(self, *, prompt: str, episode_id: str, force: bool = False) -> VideoResult:
        return VideoResult(ok=False, error="recovery_video_disabled")

    def read(self, *, episode_id: str, filename: str) -> bytes | None:
        return None

    def status(self) -> dict[str, Any]:
        return {"configured": False, "mode": "fallback", "adapter": self.adapter_name}


class VeoVideoAdapter:
    """Generates a short recovery clip with Vertex AI Veo."""

    adapter_name = "veo"
    available = True

    def __init__(
        self,
        *,
        client_kwargs: dict[str, Any],
        model: str,
        max_wait_seconds: int,
        storage: VideoStorage,
        quota: VideoQuota | None = None,
        duration_seconds: int = 8,
    ) -> None:
        self._client_kwargs = client_kwargs
        self._model = model
        self._max_wait_seconds = max_wait_seconds
        self._storage = storage
        self._quota = quota or UnlimitedVideoQuota()
        self.duration_seconds = duration_seconds
        self._client: Any | None = None
        self._last_success: bool | None = None
        self._last_error: str | None = None

    def status(self) -> dict[str, Any]:
        return {
            "configured": True,
            "mode": "managed",
            "adapter": self.adapter_name,
            "model": self._model,
            "duration_seconds": self.duration_seconds,
            "max_wait_seconds": self._max_wait_seconds,
            "storage": self._storage.describe(),
            "quota": self._quota.describe(),
            "last_success": self._last_success,
            "last_error": self._last_error,
        }

    def read(self, *, episode_id: str, filename: str) -> bytes | None:
        key = storage_key(episode_id, filename)
        if key is None:
            return None
        return self._storage.read(key)

    def _client_instance(self) -> Any:
        if self._client is None:
            from google import genai

            self._client = genai.Client(**self._client_kwargs)
        return self._client

    def _target(self, prompt: str, episode_id: str, force: bool) -> tuple[str, str]:
        """Returns ``(filename, storage_key)``.

        Cached path: the key is a digest of model + prompt, so identical instructions reuse one
        object. Forced path: a nonce, scoped to the episode's own ad-hoc prefix.
        """
        if force:
            filename = f"adhoc-{uuid.uuid4().hex}.mp4"
            return filename, f"{ADHOC_PREFIX}{episode_id}/{filename}"
        digest = hashlib.sha256(f"{self._model}\n{prompt}".encode()).hexdigest()[:32]
        filename = f"{digest}.mp4"
        return filename, f"{CACHED_PREFIX}{filename}"

    def _result(self, *, episode_id: str, filename: str, key: str, cached: bool) -> VideoResult:
        return VideoResult(
            ok=True,
            video_url=f"/api/v1/recovery/{episode_id}/video/{filename}",
            storage_key=key,
            duration_seconds=float(self.duration_seconds),
            model=self._model,
            cached=cached,
        )

    def generate(self, *, prompt: str, episode_id: str, force: bool = False) -> VideoResult:
        filename, key = self._target(prompt, episode_id, force)

        if not force:
            try:
                if self._storage.exists(key):
                    self._record(True, None)
                    return self._result(
                        episode_id=episode_id, filename=filename, key=key, cached=True
                    )
            except Exception:  # noqa: BLE001 - a cache probe must never block generation
                logger.warning("Recovery video cache probe failed for %s", key, exc_info=True)

        # Quota is charged only for work that actually reaches Veo — a cache hit is free.
        refusal = self._quota.claim(episode_id)
        if refusal is not None:
            self._record(False, refusal)
            return VideoResult(ok=False, error=refusal)

        try:
            video_bytes = self._invoke_veo(prompt)
        except _VeoFailure as failure:
            self._record(False, failure.reason)
            return VideoResult(ok=False, error=failure.reason)
        except Exception as exc:  # noqa: BLE001 - always degrade, never raise into the workflow
            logger.exception("Veo generation failed")
            self._record(False, type(exc).__name__)
            return VideoResult(ok=False, error=type(exc).__name__)

        self._storage.save(key, video_bytes)
        if force:
            # At most one ad-hoc clip per episode; repeated regeneration replaces rather than
            # accumulates. Best-effort — a failed sweep is covered by the bucket lifecycle rule.
            try:
                self._storage.prune(f"{ADHOC_PREFIX}{episode_id}/", keep=key)
            except Exception:  # noqa: BLE001
                logger.warning("Could not prune ad-hoc clips for episode %s", episode_id)
        self._record(True, None)
        return self._result(episode_id=episode_id, filename=filename, key=key, cached=False)

    def _invoke_veo(self, prompt: str) -> bytes:
        from google.genai import types

        client = self._client_instance()
        operation = client.models.generate_videos(
            model=self._model,
            prompt=prompt,
            config=types.GenerateVideosConfig(
                number_of_videos=1,
                duration_seconds=self.duration_seconds,
                aspect_ratio="9:16",
            ),
        )
        deadline = time.monotonic() + self._max_wait_seconds
        while not operation.done:
            if time.monotonic() > deadline:
                raise _VeoFailure("timeout")
            time.sleep(3)
            operation = client.operations.get(operation)

        if getattr(operation, "error", None):
            raise _VeoFailure(str(operation.error))

        generated = getattr(operation.result, "generated_videos", None) or []
        if not generated:
            raise _VeoFailure("no_video_returned")

        video = generated[0].video
        data = getattr(video, "video_bytes", None)
        if data:
            return bytes(data)
        # Vertex can answer with a GCS URI instead of inline bytes when the request carried an
        # output_gcs_uri. Phase 2's poller takes that path deliberately; until then, refuse
        # with a label rather than crashing on a None.
        if getattr(video, "uri", None):
            raise _VeoFailure("vertex_returned_gcs_uri")
        raise _VeoFailure("no_video_bytes")

    def _record(self, success: bool, error: str | None) -> None:
        self._last_success = success
        self._last_error = error


class _VeoFailure(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def build_video_client(
    *,
    enabled: bool,
    client_kwargs: dict[str, Any],
    model: str,
    max_wait_seconds: int,
    bucket_name: str,
    local_dir: Path,
    quota: VideoQuota | None = None,
    duration_seconds: int = 8,
) -> VideoGenerationClient:
    if not enabled:
        return UnavailableVideoClient()
    storage: VideoStorage = (
        GcsVideoStorage(bucket_name) if bucket_name else LocalVideoStorage(local_dir)
    )
    return VeoVideoAdapter(
        client_kwargs=client_kwargs,
        model=model,
        max_wait_seconds=max_wait_seconds,
        storage=storage,
        quota=quota,
        duration_seconds=duration_seconds,
    )
