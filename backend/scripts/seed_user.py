import os
import sys
import uuid

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from backend.database.models.models import Repository, RepositorySnapshot, Session, User
from backend.database.session import SessionLocal


def seed_test_data():
    db = SessionLocal()
    try:
        user_uuid = uuid.UUID("11111111-1111-1111-1111-111111111111")
        session_uuid = uuid.UUID("22222222-2222-2222-2222-222222222222")
        repo_uuid = uuid.UUID("33333333-3333-3333-3333-333333333333")
        snapshot_uuid = uuid.UUID("44444444-4444-4444-4444-444444444444")

        # 1. Add User
        user = db.query(User).filter_by(user_id=user_uuid).first()
        if not user:
            user = User(
                user_id=user_uuid,
                email="admin@example.com",
                username="admin",
                role="admin",
            )
            db.add(user)
            db.commit()

        # 2. Add Repository
        repo = db.query(Repository).filter_by(repository_id=repo_uuid).first()
        if not repo:
            repo = Repository(
                repository_id=repo_uuid,
                user_id=user_uuid,
                name="test-repo",
                git_url="https://github.com/example/test-repo",
                status="ingested",
            )
            db.add(repo)
            db.commit()

        # 3. Add Snapshot
        snap = db.query(RepositorySnapshot).filter_by(snapshot_id=snapshot_uuid).first()
        if not snap:
            snap = RepositorySnapshot(
                snapshot_id=snapshot_uuid, repository_id=repo_uuid, is_latest=True
            )
            db.add(snap)
            db.commit()

        # 4. Add Session
        sess = db.query(Session).filter_by(session_id=session_uuid).first()
        if not sess:
            sess = Session(
                session_id=session_uuid,
                user_id=user_uuid,
                repository_id=repo_uuid,
                session_name="Test Session",
            )
            db.add(sess)
            db.commit()

        print("Successfully seeded database with hardcoded 1111... UUIDs!")
        print(f"User ID: {user_uuid}")
        print(f"Repo ID: {repo_uuid}")
        print(f"Snapshot ID: {snapshot_uuid}")
        print(f"Session ID: {session_uuid}")

    finally:
        db.close()


if __name__ == "__main__":
    seed_test_data()
