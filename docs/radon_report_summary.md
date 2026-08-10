# Radon Report Summary

The `radon_report.txt` file is the output of running **Radon**, a Python tool used to compute various code quality metrics. The report is divided into three sections: **Cyclomatic Complexity**, **Maintainability Index**, and **Raw Metrics**.

## Commands Used to Generate This Report

```bash
uv tool install radon
uv run radon cc backend -a > radon_report.txt
uv run radon mi backend >> radon_report.txt
uv run radon raw backend >> radon_report.txt
```

## 1. Cyclomatic Complexity (CC)
Cyclomatic complexity is a software metric used to indicate the complexity of a program. It quantitatively measures the number of linearly independent paths through a code block (like a function or method). 
* **More paths (e.g., lots of `if/else` statements, loops, or `switch` cases)** = Higher complexity, harder to test, and harder to maintain.
* **Fewer paths** = Lower complexity, easier to read and test.

### How to Read the CC Section
Each line in this section describes a block of code (Class, Method, or Function), where it is located, and its assigned **grade**.
* **M, C, or F:** Identifies whether it's a **M**ethod, **C**lass, or standalone **F**unction.
* **Line numbers and name:** Exactly where the block starts and what it is called.
* **Grade (A through F):** The letter at the end of each line is the complexity score.
    * **A (1-5):** Low complexity (Excellent)
    * **B (6-10):** Moderate complexity
    * **C (11-20):** High complexity 
    * **D, E, F (21+):** Very high to extreme complexity (Severe risk, requires immediate refactoring)

### Key Findings from the CC Report
Below are the most complex areas in the codebase that act as the biggest "code smells" and bottlenecks. These are the worst offenders that likely need immediate refactoring:

#### 🔴 Critical Complexity (Grade F) - Needs Immediate Attention:
* `extract_citations` (in `backend\api\routers\query.py`)
* `execute_query` (in `backend\api\routers\query.py`)
* `run_evaluation`

#### 🟠 Severe Complexity (Grade E):
* `TestCoverageAgent.execute` (in `backend\agents\analysis\coverage_agent.py`)
* `RepositoryAgent.execute` (in `backend\agents\repository\repository_agent.py`)
* `HybridRetriever._rrf_fuse`

#### 🟡 High Complexity (Grade D):
* `PerformanceAgent.execute`
* `_detect_languages` & `_run_ingestion_pipeline` (in `backend\api\routers\ingestion.py`)
* `WorkflowRouter.invoke`
* Data fetching methods like `SonarProvider.fetch` and `SQLProvider.fetch`

---

## 2. Maintainability Index (MI)
This metric measures how maintainable the source code is on a scale of 0 to 100.
* **Higher is better:** A score closer to 100 means the code is highly maintainable, easy to read, and easy to modify.
* **Lower is worse:** A score closer to 0 means the code is convoluted and will be extremely difficult for developers to update without introducing bugs.
* **Grading:** Like Cyclomatic Complexity, Radon assigns a letter grade based on the score:
  * **A (Excellent):** 20 - 100
  * **B (Fair):** 10 - 19
  * **C (Poor):** 0 - 9

---

## 3. RAW Metrics
This section provides a simple breakdown of the physical lines of code for each file. It helps you see where the bulk of the project's logic lives vs. comments. You'll see acronyms like:
* **LOC:** Total Lines of Code
* **LLOC:** Logical Lines of Code (the actual number of statements)
* **SLOC:** Source Lines of Code (code minus comments and blank lines)
* **Comments:** Number of comment lines
* **Multi:** Number of lines used by multi-line strings (like docstrings)
* **Blank:** Number of blank lines

## Conclusion
This report acts as a roadmap for reducing technical debt. Functions scoring D, E, or F in Cyclomatic Complexity have too much logic packed into them and should be broken down into smaller, more modular helper functions to improve the overall Maintainability Index of the project.
