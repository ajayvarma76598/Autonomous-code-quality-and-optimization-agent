import uuid
from datetime import UTC, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    user_id = Column(String(255), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False)
    username = Column(String(100), unique=True, nullable=False)
    role = Column(String(50))
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )

    sessions = relationship(
        "Session", back_populates="user", cascade="all, delete-orphan"
    )
    repositories = relationship(
        "Repository", back_populates="user", cascade="all, delete-orphan"
    )


class Session(Base):
    __tablename__ = "sessions"
    session_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        String(255), ForeignKey("users.user_id", ondelete="CASCADE")
    )
    repository_id = Column(
        UUID(as_uuid=True), ForeignKey("repositories.repository_id", ondelete="CASCADE")
    )
    session_name = Column(String(255))
    status = Column(String(50))
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    last_activity_at = Column(DateTime)
    ended_at = Column(DateTime)

    user = relationship("User", back_populates="sessions")
    repository = relationship("Repository", back_populates="sessions")
    workflow_runs = relationship(
        "WorkflowRun", back_populates="session"
    )
    query_history = relationship(
        "QueryHistory", back_populates="session"
    )


class Repository(Base):
    __tablename__ = "repositories"
    repository_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        String(255), ForeignKey("users.user_id", ondelete="CASCADE")
    )
    name = Column(String(255))
    description = Column(Text)
    git_provider = Column(String(50))
    git_url = Column(Text)
    default_branch = Column(String(100))
    default_language = Column(String(100))
    status = Column(String(50))
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )

    user = relationship("User", back_populates="repositories")
    sessions = relationship(
        "Session", back_populates="repository", cascade="all, delete-orphan"
    )
    snapshots = relationship(
        "RepositorySnapshot", back_populates="repository", cascade="all, delete-orphan"
    )
    performance_logs = relationship(
        "PerformanceLog", back_populates="repository", cascade="all, delete-orphan"
    )


class RepositorySnapshot(Base):
    __tablename__ = "repository_snapshots"
    snapshot_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    repository_id = Column(
        UUID(as_uuid=True), ForeignKey("repositories.repository_id", ondelete="CASCADE")
    )
    commit_hash = Column(String(100))
    branch = Column(String(100))
    commit_message = Column(Text)
    author = Column(String(255))
    indexed_at = Column(DateTime)
    is_latest = Column(Boolean)

    repository = relationship("Repository", back_populates="snapshots")
    metadata_ = relationship(
        "RepositoryMetadata",
        back_populates="snapshot",
        uselist=False,
        cascade="all, delete-orphan",
    )
    files = relationship(
        "RepositoryFile", back_populates="snapshot", cascade="all, delete-orphan"
    )
    dependency_relationships = relationship(
        "DependencyRelationship",
        back_populates="snapshot",
        cascade="all, delete-orphan",
    )
    workflow_runs = relationship(
        "WorkflowRun", back_populates="snapshot", cascade="all, delete-orphan"
    )


class RepositoryFile(Base):
    __tablename__ = "repository_files"
    file_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    snapshot_id = Column(
        UUID(as_uuid=True),
        ForeignKey("repository_snapshots.snapshot_id", ondelete="CASCADE"),
    )
    path = Column(Text)
    filename = Column(String(255))
    extension = Column(String(20))
    language = Column(String(50))
    size_bytes = Column(BigInteger)
    line_count = Column(Integer)
    checksum = Column(String(255))
    metadata_ = Column("metadata", JSONB)

    snapshot = relationship("RepositorySnapshot", back_populates="files")
    code_objects = relationship(
        "CodeObject", back_populates="file", cascade="all, delete-orphan"
    )
    document_chunks = relationship(
        "DocumentChunk", back_populates="file", cascade="all, delete-orphan"
    )
    quality_metrics = relationship(
        "CodeQualityMetric", back_populates="file", cascade="all, delete-orphan"
    )


class RepositoryMetadata(Base):
    __tablename__ = "repository_metadata"
    metadata_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    snapshot_id = Column(
        UUID(as_uuid=True),
        ForeignKey("repository_snapshots.snapshot_id", ondelete="CASCADE"),
    )
    architecture_summary = Column(Text)
    technology_stack = Column(JSONB)
    folder_structure = Column(JSONB)
    entry_points = Column(JSONB)
    readme_summary = Column(Text)
    statistics = Column(JSONB)
    generated_at = Column(DateTime, default=lambda: datetime.now(UTC))

    snapshot = relationship("RepositorySnapshot", back_populates="metadata_")


class CodeObject(Base):
    __tablename__ = "code_objects"
    object_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_id = Column(
        UUID(as_uuid=True), ForeignKey("repository_files.file_id", ondelete="CASCADE")
    )
    parent_object_id = Column(
        UUID(as_uuid=True), ForeignKey("code_objects.object_id", ondelete="CASCADE")
    )
    object_type = Column(String(50))
    name = Column(String(255))
    signature = Column(Text)
    return_type = Column(String(255))
    start_line = Column(Integer)
    end_line = Column(Integer)
    docstring = Column(Text)
    cyclomatic_complexity = Column(Integer)
    metadata_ = Column("metadata", JSONB)

    file = relationship("RepositoryFile", back_populates="code_objects")
    children = relationship(
        "CodeObject", back_populates="parent", cascade="all, delete-orphan"
    )
    parent = relationship(
        "CodeObject", back_populates="children", remote_side=[object_id]
    )
    dependencies_as_source = relationship(
        "DependencyRelationship",
        foreign_keys="[DependencyRelationship.source_object_id]",
        back_populates="source_object",
    )
    dependencies_as_target = relationship(
        "DependencyRelationship",
        foreign_keys="[DependencyRelationship.target_object_id]",
        back_populates="target_object",
    )
    document_chunks = relationship(
        "DocumentChunk", back_populates="object", cascade="all, delete-orphan"
    )


class DependencyRelationship(Base):
    __tablename__ = "dependency_relationships"
    relationship_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    snapshot_id = Column(
        UUID(as_uuid=True),
        ForeignKey("repository_snapshots.snapshot_id", ondelete="CASCADE"),
    )
    source_object_id = Column(
        UUID(as_uuid=True), ForeignKey("code_objects.object_id", ondelete="CASCADE")
    )
    target_object_id = Column(
        UUID(as_uuid=True), ForeignKey("code_objects.object_id", ondelete="CASCADE")
    )
    relationship_type = Column(String(50))
    metadata_ = Column("metadata", JSONB)

    snapshot = relationship(
        "RepositorySnapshot", back_populates="dependency_relationships"
    )
    source_object = relationship(
        "CodeObject",
        foreign_keys=[source_object_id],
        back_populates="dependencies_as_source",
    )
    target_object = relationship(
        "CodeObject",
        foreign_keys=[target_object_id],
        back_populates="dependencies_as_target",
    )


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    chunk_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_id = Column(
        UUID(as_uuid=True), ForeignKey("repository_files.file_id", ondelete="CASCADE")
    )
    object_id = Column(
        UUID(as_uuid=True), ForeignKey("code_objects.object_id", ondelete="CASCADE")
    )
    chunk_index = Column(Integer)
    chunk_type = Column(String(50))
    content = Column(Text)
    start_line = Column(Integer)
    end_line = Column(Integer)
    metadata_ = Column("metadata", JSONB)

    file = relationship("RepositoryFile", back_populates="document_chunks")
    object = relationship("CodeObject", back_populates="document_chunks")
    embeddings = relationship(
        "Embedding", back_populates="chunk", cascade="all, delete-orphan"
    )
    retrieval_logs = relationship(
        "RetrievalLog", back_populates="chunk", cascade="all, delete-orphan"
    )
    query_citations = relationship(
        "QueryCitation", back_populates="chunk", cascade="all, delete-orphan"
    )


class Embedding(Base):
    __tablename__ = "embeddings"
    embedding_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chunk_id = Column(
        UUID(as_uuid=True), ForeignKey("document_chunks.chunk_id", ondelete="CASCADE")
    )
    provider = Column(String(100))
    model_name = Column(String(255))
    embedding_dimension = Column(Integer)
    embedding = Column(Vector(1536))
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

    chunk = relationship("DocumentChunk", back_populates="embeddings")


class RetrievalLog(Base):
    __tablename__ = "retrieval_logs"
    retrieval_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    query_id = Column(
        UUID(as_uuid=True), ForeignKey("query_history.query_id", ondelete="CASCADE")
    )
    chunk_id = Column(
        UUID(as_uuid=True), ForeignKey("document_chunks.chunk_id", ondelete="CASCADE")
    )
    retriever_type = Column(String(50))
    bm25_score = Column(Float)
    vector_score = Column(Float)
    rerank_score = Column(Float)
    rank = Column(Integer)
    latency_ms = Column(Integer)

    query = relationship("QueryHistory", back_populates="retrieval_logs")
    chunk = relationship("DocumentChunk", back_populates="retrieval_logs")


class QueryCitation(Base):
    __tablename__ = "query_citations"
    citation_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    query_id = Column(
        UUID(as_uuid=True), ForeignKey("query_history.query_id", ondelete="CASCADE")
    )
    chunk_id = Column(
        UUID(as_uuid=True), ForeignKey("document_chunks.chunk_id", ondelete="CASCADE")
    )
    citation_text = Column(Text)
    used_in_answer = Column(Boolean)

    query = relationship("QueryHistory", back_populates="citations")
    chunk = relationship("DocumentChunk", back_populates="query_citations")


class WorkflowRun(Base):
    __tablename__ = "workflow_runs"
    workflow_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(
        UUID(as_uuid=True), ForeignKey("sessions.session_id", ondelete="SET NULL"), nullable=True
    )
    snapshot_id = Column(
        UUID(as_uuid=True),
        ForeignKey("repository_snapshots.snapshot_id", ondelete="CASCADE"),
    )
    workflow_type = Column(String(100))
    status = Column(String(50))
    started_at = Column(DateTime, default=lambda: datetime.now(UTC))
    completed_at = Column(DateTime)
    latency_ms = Column(Integer)

    session = relationship("Session", back_populates="workflow_runs")
    snapshot = relationship("RepositorySnapshot", back_populates="workflow_runs")
    query_history = relationship(
        "QueryHistory", back_populates="workflow"
    )
    evaluation_runs = relationship(
        "EvaluationRun", back_populates="workflow", cascade="all, delete-orphan"
    )


class QueryHistory(Base):
    __tablename__ = "query_history"
    query_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(
        UUID(as_uuid=True), ForeignKey("sessions.session_id", ondelete="SET NULL"), nullable=True
    )
    workflow_id = Column(
        UUID(as_uuid=True), ForeignKey("workflow_runs.workflow_id", ondelete="SET NULL"), nullable=True
    )
    user_query = Column(Text)
    assistant_response = Column(Text)
    intent = Column(String(100))
    confidence = Column(Float)
    latency_ms = Column(Integer)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

    session = relationship("Session", back_populates="query_history")
    workflow = relationship("WorkflowRun", back_populates="query_history")
    retrieval_logs = relationship(
        "RetrievalLog", back_populates="query", cascade="all, delete-orphan"
    )
    citations = relationship(
        "QueryCitation", back_populates="query", cascade="all, delete-orphan"
    )


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"
    evaluation_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id = Column(
        UUID(as_uuid=True), ForeignKey("workflow_runs.workflow_id", ondelete="CASCADE")
    )
    dataset_version = Column(String(50))
    model_version = Column(String(100))
    embedding_version = Column(String(100))
    started_at = Column(DateTime, default=lambda: datetime.now(UTC))
    completed_at = Column(DateTime)

    workflow = relationship("WorkflowRun", back_populates="evaluation_runs")
    results = relationship(
        "EvaluationResult",
        back_populates="evaluation_run",
        cascade="all, delete-orphan",
    )


class EvaluationResult(Base):
    __tablename__ = "evaluation_results"
    result_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evaluation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("evaluation_runs.evaluation_id", ondelete="CASCADE"),
    )

    # Active Enterprise Metrics
    faithfulness = Column(Float)
    answer_relevancy = Column(Float)
    context_precision = Column(Float)
    latency_ms = Column(Integer)
    context_recall = Column(Float)
    llm_confidence = Column(Float)
    task_success_rate = Column(Float)

    # Legacy fields
    groundedness = Column(Float)
    passed = Column(Boolean)

    evaluation_run = relationship("EvaluationRun", back_populates="results")


class CodeQualityMetric(Base):
    __tablename__ = "code_quality_metrics"
    metric_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_id = Column(
        UUID(as_uuid=True), ForeignKey("repository_files.file_id", ondelete="CASCADE")
    )
    cyclomatic_complexity = Column(Float)
    maintainability_index = Column(Float)
    code_smell_count = Column(Integer)
    security_vulnerability_count = Column(Integer)
    bugs_count = Column(Integer, default=0)
    security_hotspots_count = Column(Integer, default=0)
    test_coverage_percentage = Column(Float)
    last_analysis_date = Column(DateTime)

    file = relationship("RepositoryFile", back_populates="quality_metrics")


class PerformanceLog(Base):
    __tablename__ = "performance_logs"
    log_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    repository_id = Column(
        UUID(as_uuid=True), ForeignKey("repositories.repository_id", ondelete="CASCADE")
    )
    service_name = Column(String(150))
    average_response_time_ms = Column(Float)
    peak_response_time_ms = Column(Float)
    error_rate_percentage = Column(Float)
    throughput_requests_per_second = Column(Integer)
    recorded_at = Column(DateTime)

    repository = relationship("Repository", back_populates="performance_logs")
