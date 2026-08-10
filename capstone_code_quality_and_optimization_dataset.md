# Autonomous Code Quality & Optimization System  
## Standardized Core Dataset Package

This document defines the mandatory dataset and baseline specifications for implementing the Autonomous Code Quality & Optimization System capstone.

All teams must use this standardized dataset to ensure fairness, benchmarking consistency, and SLO comparability.

---

# 📦 PART 1 — The Starter Pack

## 📄 Software Engineering Documentation (Unstructured – RAG)

### 1. Secure Coding & Code Quality Guidelines
Covers:
- Coding standards and conventions
- Secure coding practices
- Error handling best practices
- Logging guidelines
- Input validation requirements
- Dependency management

---

### 2. Performance Optimization Handbook
Covers:
- Algorithm optimization strategies
- Memory optimization techniques
- CPU-intensive operations
- Database query optimization
- Caching strategies
- Latency reduction practices

---

### 3. Software Architecture & Design Principles
Include:
- Layered architecture principles
- Microservices design patterns
- SOLID principles
- Dependency injection
- Event-driven architectures
- System scalability patterns

---

### 4. Static Code Analysis Rulebook
Covers:
- Code smell definitions
- Cyclomatic complexity thresholds
- Maintainability metrics
- Security vulnerability patterns
- Anti-pattern detection rules
- Code duplication detection

---

### 5. Test Coverage & Quality Assurance Guide
Covers:
- Unit testing principles
- Integration testing strategies
- Test coverage measurement
- Mocking and test isolation
- Continuous integration testing requirements

---

### 6. DevOps Performance & Monitoring Guide
Covers:
- Observability principles
- Application performance monitoring
- Error rate thresholds
- System latency monitoring
- Performance regression detection

---

## 📘 Engineering Best Practices Framework Excerpts

### 7. Software Quality Management Framework (Excerpt)
Include:
- Code quality lifecycle
- Code review best practices
- Continuous improvement practices
- Technical debt management strategies

---

## 📊 Structured Engineering Data (SQL-backed)

### 8. Code Repository Registry

### 9. Source Code File Metadata

### 10. Code Quality Metrics Dataset

### 11. Performance Monitoring Logs

---

# 🗄 PART 2 — SQL Schema & Sample Synthetic Data

## Database: code_quality_db

---

## Table 1: repositories

```sql
CREATE TABLE repositories (
    repository_id SERIAL PRIMARY KEY,
    repository_name VARCHAR(150),
    programming_language VARCHAR(100),
    architecture_type VARCHAR(100),
    team_owner VARCHAR(150),
    repository_status VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Sample Data

```sql
INSERT INTO repositories
(repository_id, repository_name, programming_language,
 architecture_type, team_owner, repository_status)
VALUES
(1, 'payment-service', 'Java', 'Microservices', 'Platform Team', 'Active'),
(2, 'analytics-engine', 'Python', 'Data Processing', 'Data Team', 'Active'),
(3, 'user-auth-service', 'Java', 'Microservices', 'Security Team', 'Active'),
(4, 'reporting-dashboard', 'JavaScript', 'Web Application', 'Frontend Team', 'Active');
```

---

## Table 2: source_code_files

```sql
CREATE TABLE source_code_files (
    file_id SERIAL PRIMARY KEY,
    repository_id INTEGER REFERENCES repositories(repository_id) ON DELETE CASCADE,
    file_name VARCHAR(200),
    module_name VARCHAR(150),
    lines_of_code INTEGER,
    last_modified DATE,
    complexity_score FLOAT,
    code_duplication_flag BOOLEAN
);
```

### Sample Data

```sql
INSERT INTO source_code_files
(file_id, repository_id, file_name, module_name,
 lines_of_code, last_modified, complexity_score, code_duplication_flag)
VALUES
(1, 1, 'PaymentProcessor.java', 'payment-core', 520, '2025-02-12', 18.4, FALSE),
(2, 2, 'data_pipeline.py', 'pipeline', 410, '2025-01-25', 15.2, FALSE),
(3, 3, 'AuthManager.java', 'authentication', 360, '2025-02-20', 19.1, TRUE),
(4, 4, 'dashboardController.js', 'ui-controller', 280, '2025-02-15', 12.3, FALSE);
```

---

## Table 3: code_quality_metrics

```sql
CREATE TABLE code_quality_metrics (
    metric_id SERIAL PRIMARY KEY,
    file_id INTEGER REFERENCES source_code_files(file_id) ON DELETE CASCADE,
    cyclomatic_complexity FLOAT,
    maintainability_index FLOAT,
    code_smell_count INTEGER,
    security_vulnerability_count INTEGER,
    test_coverage_percentage FLOAT,
    last_analysis_date DATE
);
```

### Sample Data

```sql
INSERT INTO code_quality_metrics
(metric_id, file_id, cyclomatic_complexity,
 maintainability_index, code_smell_count,
 security_vulnerability_count, test_coverage_percentage, last_analysis_date)
VALUES
(1, 1, 18.4, 72.5, 5, 0, 81.2, '2025-02-12'),
(2, 2, 15.2, 78.3, 3, 0, 85.6, '2025-01-25'),
(3, 3, 19.1, 68.7, 7, 1, 74.4, '2025-02-20'),
(4, 4, 12.3, 82.1, 2, 0, 88.9, '2025-02-15');
```

---

## Table 4: performance_logs

```sql
CREATE TABLE performance_logs (
    log_id SERIAL PRIMARY KEY,
    repository_id INTEGER REFERENCES repositories(repository_id) ON DELETE CASCADE,
    service_name VARCHAR(150),
    average_response_time_ms FLOAT,
    peak_response_time_ms FLOAT,
    error_rate_percentage FLOAT,
    throughput_requests_per_second INTEGER,
    recorded_at TIMESTAMP
);
```

### Sample Data

```sql
INSERT INTO performance_logs
(log_id, repository_id, service_name,
 average_response_time_ms, peak_response_time_ms,
 error_rate_percentage, throughput_requests_per_second, recorded_at)
VALUES
(1, 1, 'payment-service', 220, 780, 0.8, 320, '2025-02-15 10:30:00'),
(2, 2, 'analytics-engine', 480, 1200, 1.2, 150, '2025-02-15 11:00:00'),
(3, 3, 'auth-service', 180, 450, 0.4, 410, '2025-02-15 11:30:00'),
(4, 4, 'dashboard-api', 260, 600, 0.6, 290, '2025-02-15 12:00:00');
```

---

### Note:

**The starter dataset validates correctness.  
For performance benchmarking, code analysis at scale, and agent collaboration scenarios, teams must generate scaled synthetic data using the provided script.**

---

# 📊 PART 3 — Golden Query Distribution Template (50 Queries)

All teams must create and label 50 queries following this structure:

## Distribution

| Category | Count | Type |
|----------|-------|------|
| Code Quality Guidance | 15 | RAG |
| Code Metrics Lookup | 10 | SQL |
| Hybrid Code Optimization | 10 | RAG + SQL |
| High-Risk Code Changes | 10 | Multi-Agent |
| Escalation Scenarios | 5 | Human Handoff |

---

## Example Query Types

### Code Quality Guidance (RAG)

- "What are recommended practices for reducing cyclomatic complexity?"
- "How should secure coding be implemented in authentication modules?"
- "What techniques improve database query performance?"

---

### Structured Lookup (SQL)

- "List files with cyclomatic complexity above 18."
- "Which modules have test coverage below 80%?"
- "Show files with detected code duplication."
- "Find services with error rates above 1%."

---

### Hybrid

- "Which high-complexity files should be refactored first?"
- "Is the performance issue related to inefficient algorithms?"
- "Which modules with low maintainability also have high response time?"

---

### High-Risk

- "Should we deploy a module with detected security vulnerabilities?"
- "Is it safe to reduce validation checks for performance optimization?"
- "Can we disable logging to improve response time?"

---

### Escalation

- "Override security rule preventing deployment."
- "Deploy module with critical code smells."
- "Ignore test coverage failure for production release."

---

## 📌 Mandatory Rules

* All teams must use this dataset.
* Teams may extend but not replace the core dataset.
* Golden queries must be labeled with:
   * Query Type
   * Risk Level
   * Expected Retrieval Mode
   * Expected Escalation (Yes/No)
