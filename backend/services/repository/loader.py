import os
from typing import Any

from backend.services.base_service import BaseService


class RepositoryLoader(BaseService):
    def __init__(self):
        super().__init__("RepositoryLoader")

    def load_metadata(self, local_path: str) -> dict[str, Any]:
        def _load():
            entry_points = []
            languages = set()
            frameworks = set()

            if local_path and os.path.exists(str(local_path)):
                for root, _, files in os.walk(local_path):
                    for f in files:
                        f_lower = f.lower()
                        ext = os.path.splitext(f)[1].lower()
                        if ext in [".py", ".java", ".ts", ".js", ".go"]:
                            languages.add(ext.replace(".", ""))
                        if f_lower in [
                            "main.py",
                            "app.py",
                            "routes.py",
                            "server.js",
                            "index.js",
                            "index.ts",
                            "main.go",
                            "program.cs",
                            "application.java",
                            "main.java",
                        ]:
                            entry_points.append(f)
                        if f_lower in ["requirements.txt", "pyproject.toml", "pipfile"]:
                            frameworks.add("python-backend")
                        if f_lower in ["package.json"]:
                            frameworks.add("nodejs")
                        if f_lower in ["pom.xml", "build.gradle"]:
                            frameworks.add("jvm-backend")

            return {
                "entry_points": list(set(entry_points)),
                "frameworks": list(frameworks),
                "primary_language": list(languages)[0] if languages else "unknown",
            }

        return self.execute(_load).data
