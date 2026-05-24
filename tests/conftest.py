"""Shared pytest fixtures."""
from __future__ import annotations

from pathlib import Path

import pytest

from provectus_analytics import db as _db, ingest, reconcile, partition, milestones


REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def synthetic_data_dir() -> Path:
    return REPO_ROOT


@pytest.fixture
def pipeline_db(tmp_path, synthetic_data_dir):
    """Fully populated in-memory pipeline DB seeded from synthetic CSVs."""
    db_path = tmp_path / "test.db"
    conn = _db.init_db(db_path)
    ingest.ingest_all(
        conn,
        synthetic_data_dir / "synthetic_fsp_clients.csv",
        synthetic_data_dir / "synthetic_fsp_reservations.csv",
        synthetic_data_dir / "synthetic_fsp_invoices.csv",
        synthetic_data_dir / "synthetic_alumni_survey.csv",
    )
    reconcile.reconcile(conn)
    partition.build_enrollments(conn)
    partition.partition_flights(conn)
    milestones.compute_milestones(conn)
    yield conn
    conn.close()
