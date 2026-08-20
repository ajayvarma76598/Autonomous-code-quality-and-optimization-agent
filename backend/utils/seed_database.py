import random
import uuid
from datetime import UTC, datetime, timedelta

from backend.database.models.models import (
    CodeObject,
    CodeQualityMetric,
    EvaluationResult,
    EvaluationRun,
    PerformanceLog,
    Repository,
    RepositoryFile,
    RepositorySnapshot,
    User,
    WorkflowRun,
)
from backend.database.models.models import Session as DbSession
from backend.database.session import SessionLocal, init_db

# -----------------------------
# CONFIGURATION
# -----------------------------

NUM_USERS = 5
NUM_REPOSITORIES = 15
NUM_FILES_PER_REPO = 10
NUM_OBJECTS_PER_FILE = 3
NUM_WORKFLOWS = 30

# -----------------------------
# DATA POOLS
# -----------------------------

repo_names = [
    "payment-service",
    "user-auth-service",
    "analytics-engine",
    "inventory-service",
    "notification-service",
    "recommendation-engine",
    "reporting-dashboard",
    "order-management",
    "search-service",
    "fraud-detection-engine",
]

languages = ["Java", "Python", "JavaScript", "Go", "TypeScript"]
architectures = ["Microservices", "Monolith", "Serverless", "Event-Driven"]
teams = [
    "Platform Team",
    "Backend Team",
    "Data Engineering",
    "Security Team",
    "Frontend Team",
    "Infrastructure Team",
]
repo_status = ["Active", "Maintenance", "Deprecated"]

modules = [
    "authentication",
    "payment-core",
    "data-pipeline",
    "api-controller",
    "reporting-engine",
    "user-management",
    "order-processing",
]
file_types = ["Service", "Controller", "Manager", "Repository", "Processor", "Handler"]


def random_date():
    start = datetime(2024, 1, 1, tzinfo=UTC)
    end = datetime(2025, 3, 1, tzinfo=UTC)
    delta = end - start
    return start + timedelta(seconds=random.randint(0, int(delta.total_seconds())))


def seed_data():
    db = SessionLocal()

    try:
        print("Initializing Database tables if not exist...")
        init_db()

        print("Clearing old synthetic data (preserving capstone data)...")
        db.query(User).filter(User.email != "capstone@example.com").delete()
        db.commit()

        print("Seeding Users...")
        users = []
        for i in range(NUM_USERS):
            user = User(
                email=f"user{i}@example.com",
                username=f"dev_user_{i}",
                role="developer",
                created_at=random_date(),
            )
            db.add(user)
            users.append(user)
        db.commit()

        print("Seeding Repositories and Snapshots...")
        repositories = []
        snapshots = []
        for i in range(NUM_REPOSITORIES):
            user = random.choice(users)
            repo = Repository(
                user_id=user.user_id,
                name=f"{random.choice(repo_names)}-{i}",
                description="Synthetic repository for benchmarking",
                git_provider="github",
                git_url=f"https://github.com/org/{random.choice(repo_names)}-{i}",
                default_branch="main",
                default_language=random.choice(languages),
                status=random.choice(repo_status),
                created_at=random_date(),
            )
            db.add(repo)
            repositories.append(repo)

        db.commit()

        for repo in repositories:
            snapshot = RepositorySnapshot(
                repository_id=repo.repository_id,
                commit_hash=uuid.uuid4().hex[:12],
                branch="main",
                commit_message="Initial import",
                author="System",
                indexed_at=random_date(),
                is_latest=True,
            )
            db.add(snapshot)
            snapshots.append(snapshot)
        db.commit()

        print("Seeding Files, Code Objects & Quality Metrics...")
        file_ids = []
        for snapshot in snapshots:
            for _ in range(NUM_FILES_PER_REPO):
                module = random.choice(modules)
                ext = snapshot.repository.default_language.lower()[:2]
                file_name = f"{module}_{random.choice(file_types)}.{ext}"

                repo_file = RepositoryFile(
                    snapshot_id=snapshot.snapshot_id,
                    path=f"src/{module}/{file_name}",
                    filename=file_name,
                    extension=ext,
                    language=snapshot.repository.default_language,
                    size_bytes=random.randint(1000, 50000),
                    line_count=random.randint(50, 800),
                    checksum=uuid.uuid4().hex,
                )
                db.add(repo_file)
                db.flush()
                file_ids.append(repo_file.file_id)

                # Seed CodeQualityMetric
                metric = CodeQualityMetric(
                    file_id=repo_file.file_id,
                    cyclomatic_complexity=round(random.uniform(5.0, 30.0), 2),
                    maintainability_index=round(random.uniform(60.0, 95.0), 2),
                    code_smell_count=random.randint(0, 10),
                    security_vulnerability_count=random.randint(0, 3),
                    test_coverage_percentage=round(random.uniform(50.0, 99.0), 2),
                    last_analysis_date=random_date(),
                )
                db.add(metric)
        db.commit()

        print("Seeding Code Objects...")
        for fid in file_ids:
            for i in range(NUM_OBJECTS_PER_FILE):
                obj = CodeObject(
                    file_id=fid,
                    object_type=random.choice(["class", "function", "method"]),
                    name=f"{random.choice(file_types)}Element{i}",
                    signature="def example(): pass",
                    return_type="void",
                    start_line=random.randint(1, 50),
                    end_line=random.randint(51, 200),
                    cyclomatic_complexity=random.randint(1, 20),
                )
                db.add(obj)
        db.commit()

        print("Seeding Performance Logs...")
        for repo in repositories:
            log = PerformanceLog(
                repository_id=repo.repository_id,
                service_name=repo.name,
                average_response_time_ms=round(random.uniform(50.0, 500.0), 2),
                peak_response_time_ms=round(random.uniform(600.0, 2000.0), 2),
                error_rate_percentage=round(random.uniform(0.1, 2.5), 2),
                throughput_requests_per_second=random.randint(50, 1000),
                recorded_at=random_date(),
            )
            db.add(log)
        db.commit()

        print("Seeding Workflow & Evaluation Runs...")
        for _ in range(NUM_WORKFLOWS):
            snapshot = random.choice(snapshots)
            user = snapshot.repository.user

            session = DbSession(
                user_id=user.user_id,
                repository_id=snapshot.repository.repository_id,
                session_name=f"Benchmarking Session-{uuid.uuid4().hex[:6]}",
                status="ACTIVE",
                created_at=random_date(),
            )
            db.add(session)
            db.flush()

            start_t = random_date()
            duration_ms = random.randint(100, 2000)
            end_t = start_t + timedelta(milliseconds=duration_ms)

            run = WorkflowRun(
                session_id=session.session_id,
                snapshot_id=snapshot.snapshot_id,
                workflow_type=random.choice(
                    ["code_review", "optimization", "documentation"]
                ),
                status=random.choice(["COMPLETED", "FAILED"]),
                started_at=start_t,
                completed_at=end_t,
                latency_ms=duration_ms,
            )
            db.add(run)
            db.flush()

            # Seed EvaluationRun & EvaluationResult
            eval_run = EvaluationRun(
                workflow_id=run.workflow_id,
                dataset_version="v1.0",
                model_version="gpt-4o",
                embedding_version="text-embedding-3-small",
                started_at=start_t,
                completed_at=end_t,
            )
            db.add(eval_run)
            db.flush()

            eval_result = EvaluationResult(
                evaluation_id=eval_run.evaluation_id,
                faithfulness=round(random.uniform(0.8, 1.0), 2),
                answer_relevancy=round(random.uniform(0.85, 1.0), 2),
                context_precision=round(random.uniform(0.75, 1.0), 2),
                latency_ms=duration_ms,
                context_recall=round(random.uniform(0.7, 1.0), 2),
                llm_confidence=round(random.uniform(0.85, 0.99), 2),
                task_success_rate=round(random.uniform(0.8, 1.0), 2),
                groundedness=round(random.uniform(0.85, 1.0), 2),
                passed=True,
            )
            db.add(eval_result)

        db.commit()
        print("Database seeding completed successfully!")

    except Exception as e:
        print(f"Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed_data()
