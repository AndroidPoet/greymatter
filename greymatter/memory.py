"""
Core memory module for ai++ - SQLite + FTS5 based persistent memory
Zero dependencies beyond Python standard library
"""

import sqlite3
import json
import os
import time
import random
import string
from pathlib import Path
from datetime import datetime

DATA_DIR = Path.home() / '.greymatter'
DB_PATH = DATA_DIR / 'memory.db'

# Ensure data directory exists
DATA_DIR.mkdir(parents=True, exist_ok=True)


class Memory:
    def __init__(self, db_path=None):
        self.db_path = db_path or DB_PATH
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        """Initialize database schema with FTS5 for fast search"""
        cursor = self.conn.cursor()

        # Core tables
        cursor.executescript("""
            -- Memories: persistent learnings and facts
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                type TEXT DEFAULT 'learning',
                source TEXT,
                importance INTEGER DEFAULT 5,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            -- FTS5 index for fast full-text search
            CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
                content,
                type,
                source,
                content=memories,
                content_rowid=id
            );

            -- Ledger: structured session state
            CREATE TABLE IF NOT EXISTS ledger (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(session_id, key)
            );

            -- Handoffs: session transition documents
            CREATE TABLE IF NOT EXISTS handoffs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                summary TEXT NOT NULL,
                next_steps TEXT,
                open_questions TEXT,
                artifacts TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            -- FTS for handoffs
            CREATE VIRTUAL TABLE IF NOT EXISTS handoffs_fts USING fts5(
                summary,
                next_steps,
                open_questions,
                content=handoffs,
                content_rowid=id
            );

            -- Sessions: track AI usage
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                ai_type TEXT NOT NULL,
                started_at TEXT DEFAULT CURRENT_TIMESTAMP,
                ended_at TEXT,
                outcome TEXT,
                working_dir TEXT
            );

            -- Artifacts: code, files, decisions
            CREATE TABLE IF NOT EXISTS artifacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                type TEXT NOT NULL,
                name TEXT,
                content TEXT NOT NULL,
                file_path TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS artifacts_fts USING fts5(
                name,
                content,
                type,
                content=artifacts,
                content_rowid=id
            );

            -- Performance indexes
            CREATE INDEX IF NOT EXISTS idx_memories_importance ON memories(importance);
            CREATE INDEX IF NOT EXISTS idx_memories_created_at ON memories(created_at);
            CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(type);
            CREATE INDEX IF NOT EXISTS idx_artifacts_session_id ON artifacts(session_id);
            CREATE INDEX IF NOT EXISTS idx_ledger_session_id ON ledger(session_id);
            CREATE INDEX IF NOT EXISTS idx_handoffs_session_id ON handoffs(session_id);
            CREATE INDEX IF NOT EXISTS idx_handoffs_created_at ON handoffs(created_at);
        """)
        self.conn.commit()

    def _rebuild_fts(self):
        """Rebuild FTS indexes"""
        cursor = self.conn.cursor()
        cursor.execute("INSERT INTO memories_fts(memories_fts) VALUES('rebuild')")
        cursor.execute("INSERT INTO handoffs_fts(handoffs_fts) VALUES('rebuild')")
        cursor.execute("INSERT INTO artifacts_fts(artifacts_fts) VALUES('rebuild')")
        self.conn.commit()

    # === MEMORIES ===

    def save(self, content: str, type: str = 'learning', source: str = None, importance: int = 5) -> int:
        """Save a memory"""
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO memories (content, type, source, importance) VALUES (?, ?, ?, ?)",
            (content, type, source, importance)
        )
        rowid = cursor.lastrowid
        # Update FTS
        cursor.execute(
            "INSERT INTO memories_fts(rowid, content, type, source) VALUES (?, ?, ?, ?)",
            (rowid, content, type, source)
        )
        self.conn.commit()
        return rowid

    def search(self, query: str, limit: int = 10) -> list:
        """Full-text search memories"""
        cursor = self.conn.cursor()
        # Escape special FTS characters and add prefix matching
        safe_query = query.replace('"', '""')
        cursor.execute("""
            SELECT m.*, bm25(memories_fts) as rank
            FROM memories_fts
            JOIN memories m ON memories_fts.rowid = m.id
            WHERE memories_fts MATCH ?
            ORDER BY rank
            LIMIT ?
        """, (f'"{safe_query}"*', limit))
        return [dict(row) for row in cursor.fetchall()]

    def get_recent(self, limit: int = 20) -> list:
        """Get recent memories"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM memories ORDER BY created_at DESC LIMIT ?", (limit,))
        return [dict(row) for row in cursor.fetchall()]

    def get_important(self, min_importance: int = 7) -> list:
        """Get important memories"""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM memories WHERE importance >= ? ORDER BY importance DESC, created_at DESC",
            (min_importance,)
        )
        return [dict(row) for row in cursor.fetchall()]

    def delete(self, memory_id: int):
        """Delete a memory"""
        cursor = self.conn.cursor()
        # Get the memory first for FTS cleanup
        cursor.execute("SELECT * FROM memories WHERE id = ?", (memory_id,))
        row = cursor.fetchone()
        if row:
            cursor.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
            cursor.execute(
                "INSERT INTO memories_fts(memories_fts, rowid, content, type, source) VALUES('delete', ?, ?, ?, ?)",
                (memory_id, row['content'], row['type'], row['source'])
            )
            self.conn.commit()

    # === LEDGER (Session State) ===

    def ledger_set(self, session_id: str, key: str, value) -> None:
        """Set a ledger value"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO ledger (session_id, key, value)
            VALUES (?, ?, ?)
            ON CONFLICT(session_id, key) DO UPDATE SET value = excluded.value
        """, (session_id, key, json.dumps(value)))
        self.conn.commit()

    def ledger_get(self, session_id: str, key: str = None):
        """Get ledger value(s)"""
        cursor = self.conn.cursor()
        if key:
            cursor.execute("SELECT value FROM ledger WHERE session_id = ? AND key = ?", (session_id, key))
            row = cursor.fetchone()
            return json.loads(row['value']) if row else None

        cursor.execute("SELECT key, value FROM ledger WHERE session_id = ?", (session_id,))
        result = {}
        for row in cursor.fetchall():
            result[row['key']] = json.loads(row['value'])
        return result

    def ledger_get_latest(self) -> dict:
        """Get the most recent ledger state"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT session_id FROM ledger
            GROUP BY session_id
            ORDER BY MAX(created_at) DESC
            LIMIT 1
        """)
        row = cursor.fetchone()
        if not row:
            return {}
        return self.ledger_get(row['session_id'])

    # === HANDOFFS ===

    def create_handoff(self, session_id: str, summary: str,
                       next_steps: str = None, open_questions: str = None,
                       artifacts: list = None) -> int:
        """Create a session handoff"""
        cursor = self.conn.cursor()
        artifacts_json = json.dumps(artifacts) if artifacts else None
        cursor.execute("""
            INSERT INTO handoffs (session_id, summary, next_steps, open_questions, artifacts)
            VALUES (?, ?, ?, ?, ?)
        """, (session_id, summary, next_steps, open_questions, artifacts_json))
        rowid = cursor.lastrowid
        # Update FTS
        cursor.execute(
            "INSERT INTO handoffs_fts(rowid, summary, next_steps, open_questions) VALUES (?, ?, ?, ?)",
            (rowid, summary, next_steps, open_questions)
        )
        self.conn.commit()
        return rowid

    def get_last_handoff(self) -> dict:
        """Get the most recent handoff"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM handoffs ORDER BY created_at DESC LIMIT 1")
        row = cursor.fetchone()
        return dict(row) if row else None

    def search_handoffs(self, query: str, limit: int = 5) -> list:
        """Search handoffs"""
        cursor = self.conn.cursor()
        safe_query = query.replace('"', '""')
        cursor.execute("""
            SELECT h.*, bm25(handoffs_fts) as rank
            FROM handoffs_fts
            JOIN handoffs h ON handoffs_fts.rowid = h.id
            WHERE handoffs_fts MATCH ?
            ORDER BY rank
            LIMIT ?
        """, (f'"{safe_query}"*', limit))
        return [dict(row) for row in cursor.fetchall()]

    # === SESSIONS ===

    def start_session(self, ai_type: str, working_dir: str = None) -> str:
        """Start a new session"""
        session_id = f"{ai_type}-{int(time.time())}-{''.join(random.choices(string.ascii_lowercase, k=6))}"
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO sessions (id, ai_type, working_dir) VALUES (?, ?, ?)",
            (session_id, ai_type, working_dir)
        )
        self.conn.commit()
        return session_id

    def end_session(self, session_id: str, outcome: str = 'completed') -> None:
        """End a session"""
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE sessions SET ended_at = CURRENT_TIMESTAMP, outcome = ? WHERE id = ?",
            (outcome, session_id)
        )
        self.conn.commit()

    def get_session(self, session_id: str) -> dict:
        """Get session info"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    # === ARTIFACTS ===

    def save_artifact(self, session_id: str, type: str, name: str,
                      content: str, file_path: str = None) -> int:
        """Save an artifact"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO artifacts (session_id, type, name, content, file_path)
            VALUES (?, ?, ?, ?, ?)
        """, (session_id, type, name, content, file_path))
        rowid = cursor.lastrowid
        cursor.execute(
            "INSERT INTO artifacts_fts(rowid, name, content, type) VALUES (?, ?, ?, ?)",
            (rowid, name, content, type)
        )
        self.conn.commit()
        return rowid

    def search_artifacts(self, query: str, limit: int = 10) -> list:
        """Search artifacts"""
        cursor = self.conn.cursor()
        safe_query = query.replace('"', '""')
        cursor.execute("""
            SELECT a.*, bm25(artifacts_fts) as rank
            FROM artifacts_fts
            JOIN artifacts a ON artifacts_fts.rowid = a.id
            WHERE artifacts_fts MATCH ?
            ORDER BY rank
            LIMIT ?
        """, (f'"{safe_query}"*', limit))
        return [dict(row) for row in cursor.fetchall()]

    # === CONTEXT BUILDING ===

    def build_context(self, query: str = None, include_handoff: bool = True,
                      include_ledger: bool = True, include_memories: bool = True,
                      memory_limit: int = 10) -> str:
        """Build context string to inject into AI prompt"""
        context = []

        # Last handoff (most important for continuity)
        if include_handoff:
            handoff = self.get_last_handoff()
            if handoff:
                context.append(f"## Previous Session\n{handoff['summary']}")
                if handoff['next_steps']:
                    context.append(f"### Next Steps\n{handoff['next_steps']}")
                if handoff['open_questions']:
                    context.append(f"### Open Questions\n{handoff['open_questions']}")

        # Latest ledger state
        if include_ledger:
            ledger = self.ledger_get_latest()
            if ledger:
                context.append(f"## Session State\n```json\n{json.dumps(ledger, indent=2)}\n```")

        # Relevant memories
        if include_memories:
            if query:
                memories = self.search(query, memory_limit)
            else:
                memories = self.get_important(7)
                if len(memories) < 5:
                    # Deduplicate when extending
                    seen_ids = {m['id'] for m in memories}
                    for m in self.get_recent(memory_limit - len(memories)):
                        if m['id'] not in seen_ids:
                            memories.append(m)
                            seen_ids.add(m['id'])

            if memories:
                context.append("## Remembered Context")
                for m in memories:
                    context.append(f"- [{m['type']}] {m['content']}")

        return '\n\n'.join(context)

    # === UTILITIES ===

    def stats(self) -> dict:
        """Get database statistics"""
        cursor = self.conn.cursor()
        stats = {}
        # Use whitelist to avoid SQL injection
        valid_tables = ('memories', 'sessions', 'handoffs', 'artifacts')
        for table in valid_tables:
            cursor.execute("SELECT COUNT(*) as count FROM " + table)
            stats[table] = cursor.fetchone()['count']
        return stats

    def close(self):
        """Close database connection"""
        self.conn.close()


# Singleton with cleanup
_instance = None

def get_memory() -> Memory:
    """Get singleton memory instance"""
    global _instance
    if _instance is None:
        _instance = Memory()
    return _instance


def _cleanup_memory():
    """Cleanup on exit"""
    global _instance
    if _instance is not None:
        try:
            _instance.close()
        except Exception:
            pass


import atexit
atexit.register(_cleanup_memory)
