# Radon and Scalene Tools Setup and Usage Guide

This document provides a step-by-step guide on how to install and run the **Radon** and **Scalene** tools, along with a description of their purposes and capabilities.

## 1. Tool Descriptions

### Radon
**Radon** is a Python tool used to compute various code metrics, which help in assessing code complexity and maintainability. It analyzes Python source code and provides insightful data that can be used to refactor and improve code quality.

Key metrics computed by Radon include:
- **Cyclomatic Complexity (CC):** Measures the number of linearly independent paths through the source code. A lower number indicates simpler, easier-to-understand code.
- **Maintainability Index (MI):** A metric that calculates how maintainable the source code is on a scale. A higher score means the code is easier to maintain.
- **Raw Metrics:** Provides basic statistics such as Lines of Code (LOC), Logical Lines of Code (LLOC), Source Lines of Code (SLOC), comments, and blank lines.
- **Halstead Metrics:** Measures code complexity based on the number of operators and operands used.

### Scalene
**Scalene** is a high-performance, low-overhead CPU, GPU, and memory profiler for Python. It provides detailed insights into resource consumption, helping developers identify performance bottlenecks.

Key features of Scalene include:
- **Comprehensive Profiling:** It profiles CPU execution time (distinguishing between Python and C code), memory usage (including tracking memory leaks), and GPU utilization.
- **Line-Level and Function-Level Profiling:** It shows precisely which lines of code or functions are consuming the most resources.
- **AI-Powered Suggestions:** Scalene can use AI models to suggest potential optimizations for problematic code snippets.
- **Low Overhead:** It is designed to run with minimal impact on the execution time of the program being profiled.

---

## 2. Step-by-Step Installation

Since this project uses `uv` for fast dependency management, we will use it to install the tools. The tools are typically added to the `dev` dependency group.

### Step 2.1: Open your terminal
Navigate to the root directory of your project:
```bash
cd path/to/your/project
```

### Step 2.2: Install Radon and Scalene using `uv`
Run the following command to add `radon` and `scalene` to your development dependencies:
```bash
uv add --dev radon scalene
```
*Note: If you already have a `pyproject.toml` file, this command will automatically update your `[dependency-groups]` to include them.*

### Step 2.3: Verify Installation
Ensure the tools are installed correctly by checking their versions:
```bash
uv run radon --version
uv run scalene --version
```

---

## 3. How to Run Radon

You can run Radon using the `uv run radon` prefix. Here are the most common commands:

### Analyze Cyclomatic Complexity (CC)
To compute the cyclomatic complexity of all Python files in the current directory (excluding tests and virtual environments):
```bash
uv run radon cc . -a
```
- The `.` specifies the current directory.
- The `-a` flag computes the average complexity at the end of the report.

### Analyze Maintainability Index (MI)
To calculate the maintainability index:
```bash
uv run radon mi .
```

### Analyze Raw Metrics
To get raw statistics (Lines of Code, comments, etc.):
```bash
uv run radon raw .
```

*Tip: You can configure Radon in your `pyproject.toml` to automatically exclude certain directories (like `.venv` or `tests`).*

---

## 4. How to Run Scalene

Scalene requires you to run your Python script through it to profile its execution.

### Profile a Python Script
To profile a script (e.g., `main.py`), use the following command:
```bash
uv run scalene main.py
```

### Important Flags for Scalene
- `--cpu-only`: Profile only CPU usage (disables memory and GPU profiling).
- `--profile-all`: Profile all code, including external libraries (by default, Scalene only profiles your project code).
- `--cli`: Output the profiling report to the terminal instead of opening a web-based interface.
- `--outfile report.html`: Save the profiling results to an HTML file.

**Example Command with Flags:**
```bash
uv run scalene --cli --cpu-only main.py
```
