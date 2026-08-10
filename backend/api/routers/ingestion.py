from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from uuid import UUID
import logging
import os
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

from backend.api.dependencies import get_db
from backend.database.session import SessionLocal
from backend.repositories.repository_repository import repository_repo
from backend.ingestion.git import git_service
from backend.ingestion.indexer import indexer
from backend.database.models.models import RepositorySnapshot, RepositoryFile

logger = logging.getLogger(__name__)

class RepositoryIngestionState(str, Enum):
    CLONING = "cloning"
    COVERAGE = "coverage"
    SONAR = "sonar"
    INDEXING = "indexing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

router = APIRouter(prefix="/repositories", tags=["Ingestion"])

def _detect_languages(repo_path: str) -> str:
    try:
        files = os.listdir(repo_path)
        langs = set()
        if any(f in files for f in ["pom.xml", "build.gradle", "build.gradle.kts"]): langs.add("java")
        if any(f in files for f in ["package.json", "yarn.lock"]): langs.add("javascript/typescript")
        if any(f in files for f in ["requirements.txt", "pyproject.toml", "setup.py", "Pipfile"]): langs.add("python")
        if "go.mod" in files: langs.add("go")
        if "Cargo.toml" in files: langs.add("rust")
        if "composer.json" in files: langs.add("php")
        if "Gemfile" in files: langs.add("ruby")
        if any(f.endswith(".sln") or f.endswith(".csproj") for f in files): langs.add("csharp")
        
        if langs:
            return ", ".join(sorted(langs))
            
        # Fallback to counting extensions
        ext_counts = {}
        for root, _, fs in os.walk(repo_path):
            if '.git' in root or 'node_modules' in root or '.venv' in root: continue
            for f in fs:
                ext = os.path.splitext(f)[1].lower()
                if ext in [".py", ".java", ".js", ".ts", ".go", ".rs", ".php", ".rb", ".cs", ".cpp", ".c"]:
                    ext_counts[ext] = ext_counts.get(ext, 0) + 1
        
        if ext_counts:
            ext_map = {".py": "python", ".java": "java", ".js": "javascript", ".ts": "typescript", 
                       ".go": "go", ".rs": "rust", ".php": "php", ".rb": "ruby", ".cs": "csharp", 
                       ".cpp": "c++", ".c": "c"}
            
            # Get top 2 extensions if they are significant (>10% of total code files)
            total = sum(ext_counts.values())
            sorted_exts = sorted(ext_counts.items(), key=lambda x: x[1], reverse=True)
            top_langs = []
            for ext, count in sorted_exts[:2]:
                if count / total >= 0.1:  # Must be at least 10%
                    top_langs.append(ext_map.get(ext, "unknown"))
            
            if top_langs:
                return ", ".join(list(dict.fromkeys(top_langs)))
    except Exception as e:
        logger.warning(f"Language detection failed: {e}")
    return "unknown"

def _run_ingestion_pipeline(repository_id: UUID):
    db = SessionLocal()
    try:
        repo = repository_repo.get(db=db, id=repository_id)
        if not repo:
            logger.error(f"Repository {repository_id} not found for ingestion.")
            return

        # 1. Clone locally for indexing and snapshot
        repo.status = RepositoryIngestionState.CLONING.value
        db.commit()
        repo_path = git_service.clone_repository(repo.git_url, branch=repo.default_branch or "main")
        
        # 1b. Check if we already have this commit ingested (skip if no changes)
        commit_info = git_service.get_latest_commit(repo_path)
        latest_snapshot = db.query(RepositorySnapshot).filter_by(
            repository_id=repository_id, is_latest=True
        ).first()
        
        if latest_snapshot and latest_snapshot.commit_hash == commit_info.get("commit_hash", ""):
            logger.info(f"Repository {repository_id} commit {latest_snapshot.commit_hash} is already ingested. Skipping duplication.")
            repo.status = RepositoryIngestionState.SKIPPED.value
            db.commit()
            return
        
        # 2. Remote Analysis (Coverage & SonarQube via EC2 Worker)
        repo.status = RepositoryIngestionState.COVERAGE.value
        db.commit()
        
        import requests
        
        # 2a. Pre-configure SonarQube Quality Gate via Option 3
        try:
            import os
            sonar_host = os.environ.get("SONAR_HOST_URL")
            sonar_token = os.environ.get("SONAR_TOKEN")
            project_key = str(repository_id)
            repo_name = getattr(repo, "name", None) or f"Repo-{project_key[:8]}"
            
            # Step 1: Create project in SonarQube (will just return 400 if it already exists, which is fine)
            requests.post(
                f"{sonar_host}/api/projects/create",
                data={"project": project_key, "name": repo_name},
                auth=(sonar_token, ""),
                timeout=10
            )
            
            # Step 2: Assign the "Sonar way" Quality Gate to the project
            qg_response = requests.post(
                f"{sonar_host}/api/qualitygates/select",
                data={"projectKey": project_key, "gateName": "Sonar way"},
                auth=(sonar_token, ""),
                timeout=10
            )
            if not qg_response.ok:
                logger.warning(f"Failed to assign Quality Gate: {qg_response.text}")
            else:
                logger.info(f"Successfully assigned 'Sonar way' Quality Gate to project {project_key}")
                
        except Exception as e:
            logger.warning(f"Could not reach SonarQube to pre-configure Quality Gate: {e}")

        logger.info(f"Sending repository {repository_id} to EC2 worker for coverage...")
        try:
            cov_response = requests.post(
                "http://32.236.210.75:8001/coverage/run",
                json={
                    "repository_url": repo.git_url,
                    "project_key": str(repository_id)
                },
                timeout=(10, 1800)  # (connect timeout, read timeout)
            )
            cov_response.raise_for_status()
            logger.info(f"EC2 worker coverage finished successfully: {cov_response.json()}")
            
            repo.status = RepositoryIngestionState.SONAR.value
            db.commit()

            logger.info(f"Sending repository {repository_id} to EC2 worker for sonar...")
            sonar_response = requests.post(
                "http://32.236.210.75:8001/sonar/run",
                json={
                    "repository_url": repo.git_url,
                    "project_key": str(repository_id)
                },
                timeout=(10, 1800)
            )
            sonar_response.raise_for_status()
            logger.info(f"EC2 worker sonar finished successfully: {sonar_response.json()}")
        except requests.RequestException as e:
            logger.error(f"EC2 worker analysis failed: {e}")
            repo.status = RepositoryIngestionState.FAILED.value
            
            error_detail = str(e)
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json().get("detail", error_detail)
                except Exception:
                    error_detail = e.response.text or error_detail
            
            if hasattr(repo, "error_message"):
                repo.error_message = error_detail
            db.commit()
            return
            

        
    except Exception as e:
        logger.warning(f"Language detection failed: {e}")
    return "unknown"

def _run_ingestion_pipeline(repository_id: UUID):
    db = SessionLocal()
    try:
        repo = repository_repo.get(db=db, id=repository_id)
        if not repo:
            logger.error(f"Repository {repository_id} not found for ingestion.")
            return

        # 1. Clone locally for indexing and snapshot
        repo.status = RepositoryIngestionState.CLONING.value
        db.commit()
        repo_path = git_service.clone_repository(repo.git_url, branch=repo.default_branch or "main")
        
        # 1b. Check if we already have this commit ingested (skip if no changes)
        commit_info = git_service.get_latest_commit(repo_path)
        latest_snapshot = db.query(RepositorySnapshot).filter_by(
            repository_id=repository_id, is_latest=True
        ).first()
        
        if latest_snapshot and latest_snapshot.commit_hash == commit_info.get("commit_hash", ""):
            logger.info(f"Repository {repository_id} commit {latest_snapshot.commit_hash} is already ingested. Skipping duplication.")
            repo.status = RepositoryIngestionState.SKIPPED.value
            db.commit()
            return
        
        # 2. Remote Analysis (Coverage & SonarQube via EC2 Worker)
        repo.status = RepositoryIngestionState.COVERAGE.value
        db.commit()
        
        import requests
        
        # 2a. Pre-configure SonarQube Quality Gate via Option 3
        try:
            import os
            sonar_host = os.environ.get("SONAR_HOST_URL")
            sonar_token = os.environ.get("SONAR_TOKEN")
            project_key = str(repository_id)
            repo_name = getattr(repo, "name", None) or f"Repo-{project_key[:8]}"
            
            # Step 1: Create project in SonarQube (will just return 400 if it already exists, which is fine)
            requests.post(
                f"{sonar_host}/api/projects/create",
                data={"project": project_key, "name": repo_name},
                auth=(sonar_token, ""),
                timeout=10
            )
            
            # Step 2: Assign the "Sonar way" Quality Gate to the project
            qg_response = requests.post(
                f"{sonar_host}/api/qualitygates/select",
                data={"projectKey": project_key, "gateName": "Sonar way"},
                auth=(sonar_token, ""),
                timeout=10
            )
            if not qg_response.ok:
                logger.warning(f"Failed to assign Quality Gate: {qg_response.text}")
            else:
                logger.info(f"Successfully assigned 'Sonar way' Quality Gate to project {project_key}")
                
        except Exception as e:
            logger.warning(f"Could not reach SonarQube to pre-configure Quality Gate: {e}")

        logger.info(f"Sending repository {repository_id} to EC2 worker for coverage...")
        try:
            cov_response = requests.post(
                "http://32.236.210.75:8001/coverage/run",
                json={
                    "repository_url": repo.git_url,
                    "project_key": str(repository_id)
                },
                timeout=(10, 1800)  # (connect timeout, read timeout)
            )
            cov_response.raise_for_status()
            logger.info(f"EC2 worker coverage finished successfully: {cov_response.json()}")
            
            repo.status = RepositoryIngestionState.SONAR.value
            db.commit()

            logger.info(f"Sending repository {repository_id} to EC2 worker for sonar...")
            sonar_response = requests.post(
                "http://32.236.210.75:8001/sonar/run",
                json={
                    "repository_url": repo.git_url,
                    "project_key": str(repository_id)
                },
                timeout=(10, 1800)
            )
            sonar_response.raise_for_status()
            logger.info(f"EC2 worker sonar finished successfully: {sonar_response.json()}")
        except requests.RequestException as e:
            logger.error(f"EC2 worker analysis failed: {e}")
            repo.status = RepositoryIngestionState.FAILED.value
            
            error_detail = str(e)
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json().get("detail", error_detail)
                except Exception:
                    error_detail = e.response.text or error_detail
            
            if hasattr(repo, "error_message"):
                repo.error_message = error_detail
            db.commit()
            return
            

        
        # 4. Create Snapshot
        snapshot = RepositorySnapshot(
            repository_id=repository_id,
            commit_hash=commit_info.get("commit_hash", ""),
            branch=repo.default_branch or "main",
            commit_message=commit_info.get("message", ""),
            author=commit_info.get("author", ""),
            indexed_at=datetime.now(timezone.utc),
            is_latest=True
        )
        # Set previous snapshots to is_latest = False
        db.query(RepositorySnapshot).filter(
            RepositorySnapshot.repository_id == repository_id
        ).update({"is_latest": False})
        
        db.add(snapshot)
        db.commit()
        db.refresh(snapshot)

        # 5-12. Run full production indexing pipeline locally
        repo.status = RepositoryIngestionState.INDEXING.value
        db.commit()
        
        from backend.services.repository.indexer import RepositoryIndexer
        from backend.services.llm import llm_service
        repo_indexer = RepositoryIndexer()
        llm = llm_service.get_llm() if hasattr(llm_service, "get_llm") else None
        repo_indexer.index(
            local_path=repo_path,
            snapshot_id=str(snapshot.snapshot_id),
            llm=llm,
        )



    except Exception as e:
        logger.warning(f"Language detection failed: {e}")
    return "unknown"

def _run_ingestion_pipeline(repository_id: UUID):
    db = SessionLocal()
    try:
        repo = repository_repo.get(db=db, id=repository_id)
        if not repo:
            logger.error(f"Repository {repository_id} not found for ingestion.")
            return

        # 1. Clone locally for indexing and snapshot
        repo.status = RepositoryIngestionState.CLONING.value
        db.commit()
        repo_path = git_service.clone_repository(repo.git_url, branch=repo.default_branch or "main")
        
        # 1b. Check if we already have this commit ingested (skip if no changes)
        commit_info = git_service.get_latest_commit(repo_path)
        latest_snapshot = db.query(RepositorySnapshot).filter_by(
            repository_id=repository_id, is_latest=True
        ).first()
        
        if latest_snapshot and latest_snapshot.commit_hash == commit_info.get("commit_hash", ""):
            logger.info(f"Repository {repository_id} commit {latest_snapshot.commit_hash} is already ingested. Skipping duplication.")
            repo.status = RepositoryIngestionState.SKIPPED.value
            db.commit()
            return
        
        # 4. Create Snapshot
        snapshot = RepositorySnapshot(
            repository_id=repository_id,
            commit_hash=commit_info.get("commit_hash", ""),
            branch=repo.default_branch or "main",
            commit_message=commit_info.get("message", ""),
            author=commit_info.get("author", ""),
            indexed_at=datetime.now(timezone.utc),
            is_latest=True
        )
        # Set previous snapshots to is_latest = False
        db.query(RepositorySnapshot).filter(
            RepositorySnapshot.repository_id == repository_id
        ).update({"is_latest": False})
        
        db.add(snapshot)
        db.commit()
        db.refresh(snapshot)

        # 5-12. Run full production indexing pipeline locally
        repo.status = RepositoryIngestionState.INDEXING.value
        db.commit()
        
        from backend.services.repository.indexer import RepositoryIndexer
        from backend.services.llm import llm_service
        repo_indexer = RepositoryIndexer()
        llm = llm_service.get_llm() if hasattr(llm_service, "get_llm") else None
        repo_indexer.index(
            local_path=repo_path,
            snapshot_id=str(snapshot.snapshot_id),
            llm=llm,
        )

        # 2. Remote Analysis (Coverage & SonarQube via EC2 Worker)
        repo.status = RepositoryIngestionState.COVERAGE.value
        db.commit()
        
        import requests
        
        # 2a. Pre-configure SonarQube Quality Gate via Option 3
        try:
            import os
            sonar_host = os.environ.get("SONAR_HOST_URL")
            sonar_token = os.environ.get("SONAR_TOKEN")
            project_key = str(repository_id)
            repo_name = getattr(repo, "name", None) or f"Repo-{project_key[:8]}"
            
            # Step 1: Create project in SonarQube (will just return 400 if it already exists, which is fine)
            requests.post(
                f"{sonar_host}/api/projects/create",
                data={"project": project_key, "name": repo_name},
                auth=(sonar_token, ""),
                timeout=10
            )
            
            # Step 2: Assign the "Sonar way" Quality Gate to the project
            qg_response = requests.post(
                f"{sonar_host}/api/qualitygates/select",
                data={"projectKey": project_key, "gateName": "Sonar way"},
                auth=(sonar_token, ""),
                timeout=10
            )
            if not qg_response.ok:
                logger.warning(f"Failed to assign Quality Gate: {qg_response.text}")
            else:
                logger.info(f"Successfully assigned 'Sonar way' Quality Gate to project {project_key}")
                
        except Exception as e:
            logger.warning(f"Could not reach SonarQube to pre-configure Quality Gate: {e}")

        logger.info(f"Sending repository {repository_id} to EC2 worker for coverage...")
        try:
            cov_response = requests.post(
                "http://32.236.210.75:8001/coverage/run",
                json={
                    "repository_url": repo.git_url,
                    "project_key": str(repository_id)
                },
                timeout=(10, 1800)  # (connect timeout, read timeout)
            )
            cov_response.raise_for_status()
            logger.info(f"EC2 worker coverage finished successfully: {cov_response.json()}")
            
            repo.status = RepositoryIngestionState.SONAR.value
            db.commit()

            logger.info(f"Sending repository {repository_id} to EC2 worker for sonar...")
            sonar_response = requests.post(
                "http://32.236.210.75:8001/sonar/run",
                json={
                    "repository_url": repo.git_url,
                    "project_key": str(repository_id)
                },
                timeout=(10, 1800)
            )
            sonar_response.raise_for_status()
            logger.info(f"EC2 worker sonar finished successfully: {sonar_response.json()}")
        except requests.RequestException as e:
            logger.error(f"EC2 worker analysis failed: {e}")
            repo.status = RepositoryIngestionState.FAILED.value
            
            error_detail = str(e)
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json().get("detail", error_detail)
                except Exception:
                    error_detail = e.response.text or error_detail
            
            if hasattr(repo, "error_message"):
                repo.error_message = error_detail
            db.commit()
            return
            

        
    except Exception as e:
        logger.warning(f"Language detection failed: {e}")
    return "unknown"

def _run_ingestion_pipeline(repository_id: UUID):
    db = SessionLocal()
    try:
        repo = repository_repo.get(db=db, id=repository_id)
        if not repo:
            logger.error(f"Repository {repository_id} not found for ingestion.")
            return

        # 1. Clone locally for indexing and snapshot
        repo.status = RepositoryIngestionState.CLONING.value
        db.commit()
        repo_path = git_service.clone_repository(repo.git_url, branch=repo.default_branch or "main")
        
        # 1b. Check if we already have this commit ingested (skip if no changes)
        commit_info = git_service.get_latest_commit(repo_path)
        latest_snapshot = db.query(RepositorySnapshot).filter_by(
            repository_id=repository_id, is_latest=True
        ).first()
        
        if latest_snapshot and latest_snapshot.commit_hash == commit_info.get("commit_hash", ""):
            logger.info(f"Repository {repository_id} commit {latest_snapshot.commit_hash} is already ingested. Skipping duplication.")
            repo.status = RepositoryIngestionState.SKIPPED.value
            db.commit()
            return
        
        # 2. Remote Analysis (Coverage & SonarQube via EC2 Worker)
        repo.status = RepositoryIngestionState.COVERAGE.value
        db.commit()
        
        import requests
        
        # 2a. Pre-configure SonarQube Quality Gate via Option 3
        try:
            import os
            sonar_host = os.environ.get("SONAR_HOST_URL")
            sonar_token = os.environ.get("SONAR_TOKEN")
            project_key = str(repository_id)
            repo_name = getattr(repo, "name", None) or f"Repo-{project_key[:8]}"
            
            # Step 1: Create project in SonarQube (will just return 400 if it already exists, which is fine)
            requests.post(
                f"{sonar_host}/api/projects/create",
                data={"project": project_key, "name": repo_name},
                auth=(sonar_token, ""),
                timeout=10
            )
            
            # Step 2: Assign the "Sonar way" Quality Gate to the project
            qg_response = requests.post(
                f"{sonar_host}/api/qualitygates/select",
                data={"projectKey": project_key, "gateName": "Sonar way"},
                auth=(sonar_token, ""),
                timeout=10
            )
            if not qg_response.ok:
                logger.warning(f"Failed to assign Quality Gate: {qg_response.text}")
            else:
                logger.info(f"Successfully assigned 'Sonar way' Quality Gate to project {project_key}")
                
        except Exception as e:
            logger.warning(f"Could not reach SonarQube to pre-configure Quality Gate: {e}")

        logger.info(f"Sending repository {repository_id} to EC2 worker for coverage...")
        try:
            cov_response = requests.post(
                "http://32.236.210.75:8001/coverage/run",
                json={
                    "repository_url": repo.git_url,
                    "project_key": str(repository_id)
                },
                timeout=(10, 1800)  # (connect timeout, read timeout)
            )
            cov_response.raise_for_status()
            logger.info(f"EC2 worker coverage finished successfully: {cov_response.json()}")
            
            repo.status = RepositoryIngestionState.SONAR.value
            db.commit()

            logger.info(f"Sending repository {repository_id} to EC2 worker for sonar...")
            sonar_response = requests.post(
                "http://32.236.210.75:8001/sonar/run",
                json={
                    "repository_url": repo.git_url,
                    "project_key": str(repository_id)
                },
                timeout=(10, 1800)
            )
            sonar_response.raise_for_status()
            logger.info(f"EC2 worker sonar finished successfully: {sonar_response.json()}")
        except requests.RequestException as e:
            logger.error(f"EC2 worker analysis failed: {e}")
            repo.status = RepositoryIngestionState.FAILED.value
            
            error_detail = str(e)
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json().get("detail", error_detail)
                except Exception:
                    error_detail = e.response.text or error_detail
            
            if hasattr(repo, "error_message"):
                repo.error_message = error_detail
            db.commit()
            return
            

        
        # 4. Create Snapshot
        snapshot = RepositorySnapshot(
            repository_id=repository_id,
            commit_hash=commit_info.get("commit_hash", ""),
            branch=repo.default_branch or "main",
            commit_message=commit_info.get("message", ""),
            author=commit_info.get("author", ""),
            indexed_at=datetime.now(timezone.utc),
            is_latest=True
        )
        # Set previous snapshots to is_latest = False
        db.query(RepositorySnapshot).filter(
            RepositorySnapshot.repository_id == repository_id
        ).update({"is_latest": False})
        
        db.add(snapshot)
        db.commit()
        db.refresh(snapshot)

        # 5-12. Run full production indexing pipeline locally
        repo.status = RepositoryIngestionState.INDEXING.value
        db.commit()
        
        from backend.services.repository.indexer import RepositoryIndexer
        from backend.services.llm import llm_service
        repo_indexer = RepositoryIndexer()
        llm = llm_service.get_llm() if hasattr(llm_service, "get_llm") else None
        repo_indexer.index(
            local_path=repo_path,
            snapshot_id=str(snapshot.snapshot_id),
            llm=llm,
        )

        # 13. Fetch SonarQube metrics and save to DB
        try:
            import os
            import requests
            sonar_host = os.environ.get("SONAR_HOST_URL")
            sonar_token = os.environ.get("SONAR_TOKEN")
            
            logger.info("Fetching project-level SonarQube metrics...")
            metrics_url = f"{sonar_host}/api/measures/component?component={str(repository_id)}&metricKeys=bugs,vulnerabilities,code_smells,complexity,sqale_index,coverage"
            resp = requests.get(metrics_url, auth=(sonar_token, ""), timeout=10)
            if resp.status_code == 200:
                measures = resp.json().get("component", {}).get("measures", [])
                m_dict = {m["metric"]: float(m["value"]) for m in measures if "value" in m}
                
                # We attach the project-level metrics to the first file in the snapshot to satisfy SonarProvider
                from backend.database.models.models import RepositoryFile, CodeQualityMetric
                first_file = db.query(RepositoryFile).filter_by(snapshot_id=snapshot.snapshot_id).first()
                if first_file:
                    new_metric = CodeQualityMetric(
                        file_id=first_file.file_id,
                        cyclomatic_complexity=m_dict.get("complexity", 0),
                        maintainability_index=m_dict.get("sqale_index", 0),
                        code_smell_count=int(m_dict.get("code_smells", 0)),
                        security_vulnerability_count=int(m_dict.get("vulnerabilities", 0)),
                        bugs_count=int(m_dict.get("bugs", 0)),
                        test_coverage_percentage=m_dict.get("coverage", 0),
                        last_analysis_date=datetime.now(timezone.utc)
                    )
                    db.add(new_metric)
                    db.commit()
                    logger.info("Successfully persisted SonarQube metrics to CodeQualityMetric table.")
            else:
                logger.warning(f"Failed to fetch SonarQube metrics: {resp.status_code} {resp.text}")
        except Exception as e:
            logger.error(f"Error fetching/saving Sonar metrics: {e}")

        # 14. Update Status
        repo.status = RepositoryIngestionState.COMPLETED.value
        if hasattr(repo, "coverage_available"):
            repo.coverage_available = True
        db.commit()
        logger.info(f"Ingestion complete for repository {repository_id}")

    except Exception as e:
        import traceback
        logger.error(f"Ingestion failed: {e}\n{traceback.format_exc()}")
        db.rollback()
        repo = repository_repo.get(db=db, id=repository_id)
        if repo:
            repo.status = RepositoryIngestionState.FAILED.value
            db.commit()
    finally:
        db.close()


