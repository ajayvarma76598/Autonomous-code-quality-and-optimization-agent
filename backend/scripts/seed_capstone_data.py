from datetime import datetime

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from backend.database.models.models import (  # noqa: E402
    CodeQualityMetric,
    PerformanceLog,
    Repository,
    RepositoryFile,
    RepositorySnapshot,
    User,
)
from backend.database.session import SessionLocal, init_db  # noqa: E402


def seed_data():
    db = SessionLocal()
    try:
        # Create a dummy user
        user = db.query(User).filter_by(email="capstone@example.com").first()
        if not user:
            user = User(
                email="capstone@example.com", username="capstone_tester", role="admin"
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        # Repositories
        repos = [
            Repository(
                user_id=user.user_id,
                name="payment-service",
                git_provider="github",
                git_url="https://github.com/example/payment-service",
                default_language="Java",
                description="Microservices - Platform Team",
                status="Active",
            ),
            Repository(
                user_id=user.user_id,
                name="analytics-engine",
                git_provider="github",
                git_url="https://github.com/example/analytics-engine",
                default_language="Python",
                description="Data Processing - Data Team",
                status="Active",
            ),
            Repository(
                user_id=user.user_id,
                name="user-auth-service",
                git_provider="github",
                git_url="https://github.com/example/user-auth-service",
                default_language="Java",
                description="Microservices - Security Team",
                status="Active",
            ),
            Repository(
                user_id=user.user_id,
                name="reporting-dashboard",
                git_provider="github",
                git_url="https://github.com/example/reporting-dashboard",
                default_language="JavaScript",
                description="Web Application - Frontend Team",
                status="Active",
            ),
        ]

        for repo in repos:
            db.add(repo)
        db.commit()

        # We need snapshots to attach files to
        snapshots = []
        for repo in repos:
            snapshot = RepositorySnapshot(
                repository_id=repo.repository_id,
                commit_hash="dummy_hash",
                branch="main",
                is_latest=True,
            )
            db.add(snapshot)
            snapshots.append(snapshot)

        db.commit()

        # Files and Code Quality Metrics
        files_data = [
            {
                "repo_idx": 0,
                "name": "PaymentProcessor.java",
                "lines": 520,
                "complexity": 18.4,
                "maintain": 72.5,
                "smells": 5,
                "vuln": 0,
                "cov": 81.2,
            },
            {
                "repo_idx": 1,
                "name": "data_pipeline.py",
                "lines": 410,
                "complexity": 15.2,
                "maintain": 78.3,
                "smells": 3,
                "vuln": 0,
                "cov": 85.6,
            },
            {
                "repo_idx": 2,
                "name": "AuthManager.java",
                "lines": 360,
                "complexity": 19.1,
                "maintain": 68.7,
                "smells": 7,
                "vuln": 1,
                "cov": 74.4,
            },
            {
                "repo_idx": 3,
                "name": "dashboardController.js",
                "lines": 280,
                "complexity": 12.3,
                "maintain": 82.1,
                "smells": 2,
                "vuln": 0,
                "cov": 88.9,
            },
        ]

        for fd in files_data:
            snapshot = snapshots[fd["repo_idx"]]
            repo_file = RepositoryFile(
                snapshot_id=snapshot.snapshot_id,
                path=fd["name"],
                filename=fd["name"],
                extension="." + fd["name"].split(".")[-1],
                language=fd["name"].split(".")[-1],
                line_count=fd["lines"],
            )
            db.add(repo_file)
            db.commit()

            metric = CodeQualityMetric(
                file_id=repo_file.file_id,
                cyclomatic_complexity=fd["complexity"],
                maintainability_index=fd["maintain"],
                code_smell_count=fd["smells"],
                security_vulnerability_count=fd["vuln"],
                test_coverage_percentage=fd["cov"],
                last_analysis_date=datetime.now(),
            )
            db.add(metric)

        db.commit()

        # Performance Logs
        perf_data = [
            {
                "repo_idx": 0,
                "svc": "payment-service",
                "avg": 220,
                "peak": 780,
                "err": 0.8,
                "tps": 320,
            },
            {
                "repo_idx": 1,
                "svc": "analytics-engine",
                "avg": 480,
                "peak": 1200,
                "err": 1.2,
                "tps": 150,
            },
            {
                "repo_idx": 2,
                "svc": "auth-service",
                "avg": 180,
                "peak": 450,
                "err": 0.4,
                "tps": 410,
            },
            {
                "repo_idx": 3,
                "svc": "dashboard-api",
                "avg": 260,
                "peak": 600,
                "err": 0.6,
                "tps": 290,
            },
        ]

        for pd in perf_data:
            repo = repos[pd["repo_idx"]]
            log = PerformanceLog(
                repository_id=repo.repository_id,
                service_name=pd["svc"],
                average_response_time_ms=pd["avg"],
                peak_response_time_ms=pd["peak"],
                error_rate_percentage=pd["err"],
                throughput_requests_per_second=pd["tps"],
                recorded_at=datetime.now(),
            )
            db.add(log)

        db.commit()
        print("Successfully seeded Capstone dataset!")

    except Exception as e:
        print(f"Error seeding data: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    init_db()  # Make sure tables are created
    seed_data()
