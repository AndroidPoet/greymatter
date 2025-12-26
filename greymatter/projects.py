#!/usr/bin/env python3
"""
Projects - Per-Project Memory Management

Each project/folder gets its own brain that auto-switches.

Features:
- Auto-detect project root (git, package.json, etc.)
- Separate memory per project
- Shared global memory for common knowledge
- Memory inheritance (project can access global)
- Project context awareness
"""

import os
import hashlib
from pathlib import Path
from typing import Dict, Optional, List
from dataclasses import dataclass

from .memory import Memory, DATA_DIR


@dataclass
class Project:
    """Project information"""
    name: str
    root: Path
    id: str
    db_path: Path
    is_git: bool = False
    is_npm: bool = False
    is_python: bool = False


class ProjectDetector:
    """Detect project root and type"""

    # Files that indicate project root
    ROOT_MARKERS = [
        '.git',
        'package.json',
        'pyproject.toml',
        'setup.py',
        'Cargo.toml',
        'go.mod',
        'pom.xml',
        'build.gradle',
        '.project',
        'Makefile',
        'CMakeLists.txt',
    ]

    # Type indicators
    TYPE_MARKERS = {
        'git': ['.git'],
        'npm': ['package.json', 'yarn.lock', 'pnpm-lock.yaml'],
        'python': ['pyproject.toml', 'setup.py', 'requirements.txt', 'Pipfile'],
        'rust': ['Cargo.toml'],
        'go': ['go.mod'],
        'java': ['pom.xml', 'build.gradle'],
    }

    @staticmethod
    def find_root(start_path: Path = None) -> Optional[Path]:
        """Find project root by looking for marker files"""
        path = Path(start_path or os.getcwd()).resolve()

        while path != path.parent:
            for marker in ProjectDetector.ROOT_MARKERS:
                if (path / marker).exists():
                    return path
            path = path.parent

        return None

    @staticmethod
    def detect_type(root: Path) -> Dict[str, bool]:
        """Detect project type(s)"""
        types = {}
        for type_name, markers in ProjectDetector.TYPE_MARKERS.items():
            types[type_name] = any((root / m).exists() for m in markers)
        return types

    @staticmethod
    def get_project_id(root: Path) -> str:
        """Generate unique project ID"""
        # Use path hash for uniqueness
        path_str = str(root.resolve())
        return hashlib.md5(path_str.encode()).hexdigest()[:12]

    @staticmethod
    def detect(path: Path = None) -> Optional[Project]:
        """Detect project from path"""
        root = ProjectDetector.find_root(path)

        if not root:
            return None

        types = ProjectDetector.detect_type(root)
        project_id = ProjectDetector.get_project_id(root)

        # Create project-specific DB path
        db_path = DATA_DIR / 'projects' / f'{project_id}.db'
        db_path.parent.mkdir(parents=True, exist_ok=True)

        return Project(
            name=root.name,
            root=root,
            id=project_id,
            db_path=db_path,
            is_git=types.get('git', False),
            is_npm=types.get('npm', False),
            is_python=types.get('python', False),
        )


class ProjectMemory:
    """
    Project-aware memory management.

    Each project has its own memory, with fallback to global.
    """

    def __init__(self, project: Project = None, use_global: bool = True):
        self.project = project or ProjectDetector.detect()
        self.use_global = use_global

        # Project-specific memory
        if self.project:
            self.project_memory = Memory(db_path=self.project.db_path)
        else:
            self.project_memory = None

        # Global memory (shared across projects)
        if use_global:
            from .memory import get_memory
            self.global_memory = get_memory()
        else:
            self.global_memory = None

    def save(self, content: str, type: str = 'learning',
             importance: int = 5, scope: str = 'project') -> int:
        """
        Save memory to project or global scope.

        Args:
            scope: 'project' (default), 'global', or 'both'
        """
        mem_id = None

        if scope in ('project', 'both') and self.project_memory:
            mem_id = self.project_memory.save(content, type=type, importance=importance)

        if scope in ('global', 'both') and self.global_memory:
            # Add project context to global
            if self.project:
                content = f"[{self.project.name}] {content}"
            mem_id = self.global_memory.save(content, type=type, importance=importance)

        return mem_id

    def search(self, query: str, limit: int = 10,
               include_global: bool = True) -> List[Dict]:
        """Search memories, combining project and global"""
        results = []

        # Search project memory
        if self.project_memory:
            project_results = self.project_memory.search(query, limit=limit)
            for r in project_results:
                r['scope'] = 'project'
            results.extend(project_results)

        # Search global memory
        if include_global and self.global_memory:
            global_results = self.global_memory.search(query, limit=limit)
            for r in global_results:
                r['scope'] = 'global'
            results.extend(global_results)

        # Sort by importance and return top
        results.sort(key=lambda x: -x.get('importance', 0))
        return results[:limit]

    def get_recent(self, limit: int = 20, include_global: bool = True) -> List[Dict]:
        """Get recent memories from project and optionally global"""
        results = []

        if self.project_memory:
            project_results = self.project_memory.get_recent(limit=limit)
            for r in project_results:
                r['scope'] = 'project'
            results.extend(project_results)

        if include_global and self.global_memory:
            global_results = self.global_memory.get_recent(limit=limit // 2)
            for r in global_results:
                r['scope'] = 'global'
            results.extend(global_results)

        # Sort by timestamp and return
        results.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return results[:limit]

    def build_context(self, query: str = None) -> str:
        """Build context including project info"""
        parts = []

        # Add project info
        if self.project:
            parts.append(f"## Current Project: {self.project.name}")
            parts.append(f"Path: {self.project.root}")
            types = []
            if self.project.is_git:
                types.append("Git")
            if self.project.is_npm:
                types.append("Node.js")
            if self.project.is_python:
                types.append("Python")
            if types:
                parts.append(f"Type: {', '.join(types)}")

        # Project memories
        if self.project_memory:
            from .smart import get_optimizer
            # Create optimizer for project memory
            optimizer = get_optimizer()
            optimizer.memory = self.project_memory
            context, _ = optimizer.get_optimized_context(query=query)
            if context:
                parts.append(f"\n## Project Memory\n{context}")

        # Global memories (limited)
        if self.global_memory:
            important = self.global_memory.get_important(min_importance=8)
            if important:
                parts.append("\n## Global Knowledge")
                for m in important[:5]:
                    parts.append(f"- {m['content'][:80]}")

        return '\n'.join(parts)

    def stats(self) -> Dict:
        """Get stats for project and global"""
        stats = {'project': None, 'global': None}

        if self.project_memory:
            stats['project'] = {
                'name': self.project.name,
                **self.project_memory.stats()
            }

        if self.global_memory:
            stats['global'] = self.global_memory.stats()

        return stats


class ProjectManager:
    """Manage multiple projects"""

    def __init__(self):
        self.projects_dir = DATA_DIR / 'projects'
        self.projects_dir.mkdir(parents=True, exist_ok=True)
        self.current: Optional[ProjectMemory] = None

    def switch_to(self, path: Path = None) -> ProjectMemory:
        """Switch to project at path (or current directory)"""
        project = ProjectDetector.detect(path)
        self.current = ProjectMemory(project=project)
        return self.current

    def list_projects(self) -> List[Dict]:
        """List all known projects"""
        projects = []

        for db_file in self.projects_dir.glob('*.db'):
            project_id = db_file.stem
            mem = Memory(db_path=db_file)
            stats = mem.stats()
            projects.append({
                'id': project_id,
                'db_path': str(db_file),
                **stats
            })

        return projects

    def cleanup_old(self, days: int = 90) -> int:
        """Clean up old project databases"""
        import time
        now = time.time()
        deleted = 0

        for db_file in self.projects_dir.glob('*.db'):
            age_days = (now - db_file.stat().st_mtime) / 86400
            if age_days > days:
                db_file.unlink()
                deleted += 1

        return deleted


# Singleton
_project_memory = None

def get_project_memory() -> ProjectMemory:
    """Get project memory for current directory"""
    global _project_memory
    if _project_memory is None:
        _project_memory = ProjectMemory()
    return _project_memory
