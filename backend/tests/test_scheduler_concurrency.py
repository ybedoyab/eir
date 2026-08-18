import threading
from datetime import UTC, datetime, timedelta

from app.domain.recovery.models import EpisodeStatus, RecoveryEpisode
from app.repositories.recovery_repository import InMemoryRecoveryEpisodeRepository


def test_concurrent_claim_due_follow_up_is_atomic() -> None:
    repo = InMemoryRecoveryEpisodeRepository()
    now = datetime.now(UTC)
    episode = RecoveryEpisode(
        id="ep-concurrent",
        patient_id="patient-synthetic-001",
        status=EpisodeStatus.WAITING_FOR_NEXT_FOLLOWUP,
        started_at=now,
        next_follow_up_at=now - timedelta(minutes=1),
    )
    repo.save(episode)
    results: list = []
    lock = threading.Lock()

    def worker() -> None:
        claimed = repo.claim_due_follow_up(episode.id, now=now, interval_days=7)
        with lock:
            results.append(claimed)

    threads = [threading.Thread(target=worker) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sum(1 for item in results if item is not None) == 1
    assert len(repo.list_events(episode.id)) == 1
