#!/usr/bin/env python3
"""
Git Integration - Save reasoning history per commit

This module tracks AI reasoning and decisions alongside git commits,
allowing you to understand WHY changes were made, not just WHAT changed.

Features:
- Save reasoning notes per commit
- Link AI sessions to commits
- Search reasoning history
- Annotate commits with AI insights
"""

import subprocess
import os
import json
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime


class GitIntegration:
    """Git integration for reasoning history"""

    def __init__(self, repo_path: str = None):
        self.repo_path = Path(repo_path or os.getcwd())
        self.reasoning_dir = self.repo_path / '.git' / 'ai-reasoning'
        self._ensure_dirs()

    def _ensure_dirs(self):
        """Ensure reasoning directory exists"""
        if self.is_git_repo():
            self.reasoning_dir.mkdir(parents=True, exist_ok=True)

    def is_git_repo(self) -> bool:
        """Check if current directory is a git repo"""
        return (self.repo_path / '.git').exists()

    def get_current_commit(self) -> Optional[str]:
        """Get current commit hash"""
        try:
            result = subprocess.run(
                ['git', 'rev-parse', 'HEAD'],
                capture_output=True, text=True, cwd=self.repo_path
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass
        return None

    def get_current_branch(self) -> Optional[str]:
        """Get current branch name"""
        try:
            result = subprocess.run(
                ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                capture_output=True, text=True, cwd=self.repo_path
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass
        return None

    def save_reasoning(self, commit_hash: str, reasoning: Dict) -> bool:
        """Save reasoning for a commit"""
        if not self.is_git_repo():
            return False

        reasoning_file = self.reasoning_dir / f"{commit_hash[:8]}.json"

        # Load existing or create new
        if reasoning_file.exists():
            data = json.loads(reasoning_file.read_text())
        else:
            data = {
                'commit': commit_hash,
                'entries': []
            }

        # Add new entry
        data['entries'].append({
            'timestamp': datetime.now().isoformat(),
            **reasoning
        })

        reasoning_file.write_text(json.dumps(data, indent=2))
        return True

    def get_reasoning(self, commit_hash: str) -> Optional[Dict]:
        """Get reasoning for a commit"""
        if not self.is_git_repo():
            return None

        reasoning_file = self.reasoning_dir / f"{commit_hash[:8]}.json"
        if reasoning_file.exists():
            return json.loads(reasoning_file.read_text())
        return None

    def annotate_commit(self, message: str, session_id: str = None,
                        decisions: List[str] = None, learnings: List[str] = None) -> bool:
        """Annotate the current commit with AI reasoning"""
        commit_hash = self.get_current_commit()
        if not commit_hash:
            return False

        reasoning = {
            'message': message,
            'session_id': session_id,
            'decisions': decisions or [],
            'learnings': learnings or [],
            'branch': self.get_current_branch(),
        }

        return self.save_reasoning(commit_hash, reasoning)

    def get_commit_history_with_reasoning(self, limit: int = 10) -> List[Dict]:
        """Get recent commits with their reasoning"""
        if not self.is_git_repo():
            return []

        try:
            result = subprocess.run(
                ['git', 'log', f'-{limit}', '--format=%H|%s|%ai'],
                capture_output=True, text=True, cwd=self.repo_path
            )

            if result.returncode != 0:
                return []

            commits = []
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                parts = line.split('|')
                if len(parts) >= 3:
                    commit_hash = parts[0]
                    commits.append({
                        'hash': commit_hash,
                        'message': parts[1],
                        'date': parts[2],
                        'reasoning': self.get_reasoning(commit_hash)
                    })

            return commits

        except:
            return []

    def search_reasoning(self, query: str) -> List[Dict]:
        """Search through reasoning history"""
        if not self.is_git_repo() or not self.reasoning_dir.exists():
            return []

        results = []
        query_lower = query.lower()

        for file in self.reasoning_dir.glob('*.json'):
            try:
                data = json.loads(file.read_text())
                for entry in data.get('entries', []):
                    # Search in message, decisions, learnings
                    searchable = ' '.join([
                        entry.get('message', ''),
                        ' '.join(entry.get('decisions', [])),
                        ' '.join(entry.get('learnings', []))
                    ]).lower()

                    if query_lower in searchable:
                        results.append({
                            'commit': data['commit'],
                            'entry': entry
                        })
            except:
                continue

        return results

    def link_session(self, session_id: str, commit_hash: str = None) -> bool:
        """Link an AI session to a commit"""
        commit_hash = commit_hash or self.get_current_commit()
        if not commit_hash:
            return False

        return self.save_reasoning(commit_hash, {
            'type': 'session_link',
            'session_id': session_id
        })

    def get_uncommitted_reasoning(self) -> List[Dict]:
        """Get reasoning entries that haven't been committed yet"""
        if not self.is_git_repo():
            return []

        uncommitted_file = self.reasoning_dir / 'uncommitted.json'
        if uncommitted_file.exists():
            data = json.loads(uncommitted_file.read_text())
            return data.get('entries', [])
        return []

    def add_uncommitted_reasoning(self, reasoning: Dict) -> bool:
        """Add reasoning for work not yet committed"""
        if not self.is_git_repo():
            return False

        uncommitted_file = self.reasoning_dir / 'uncommitted.json'

        if uncommitted_file.exists():
            data = json.loads(uncommitted_file.read_text())
        else:
            data = {'entries': []}

        data['entries'].append({
            'timestamp': datetime.now().isoformat(),
            **reasoning
        })

        uncommitted_file.write_text(json.dumps(data, indent=2))
        return True

    def commit_uncommitted_reasoning(self) -> bool:
        """Move uncommitted reasoning to current commit"""
        uncommitted = self.get_uncommitted_reasoning()
        if not uncommitted:
            return False

        commit_hash = self.get_current_commit()
        if not commit_hash:
            return False

        for entry in uncommitted:
            self.save_reasoning(commit_hash, entry)

        # Clear uncommitted
        uncommitted_file = self.reasoning_dir / 'uncommitted.json'
        if uncommitted_file.exists():
            uncommitted_file.unlink()

        return True


# Singleton
_instance = None

def get_git_integration(repo_path: str = None) -> GitIntegration:
    global _instance
    if _instance is None or (repo_path and str(_instance.repo_path) != repo_path):
        _instance = GitIntegration(repo_path)
    return _instance
