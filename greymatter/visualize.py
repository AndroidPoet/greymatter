#!/usr/bin/env python3
"""
Memory Visualization - Web UI for memory graph

Features:
- Interactive memory graph
- Node = memory, Edge = relationship
- Search and filter
- Timeline view
- Statistics dashboard

Uses only Python stdlib (http.server + embedded HTML/JS)
No npm, no external dependencies!
"""

import json
import http.server
import socketserver
import webbrowser
import threading
from typing import Dict, List
from pathlib import Path
from urllib.parse import parse_qs, urlparse


def get_memory_graph_data() -> Dict:
    """Get memory data formatted for visualization"""
    from .memory import get_memory
    from .embeddings import get_semantic_search

    memory = get_memory()
    search = get_semantic_search()

    # Get all memories
    memories = memory.get_recent(limit=200)

    # Build nodes
    nodes = []
    for mem in memories:
        nodes.append({
            'id': str(mem['id']),
            'label': mem['content'][:30] + '...',
            'content': mem['content'],
            'type': mem.get('type', 'unknown'),
            'importance': mem.get('importance', 5),
            'created_at': mem.get('created_at', ''),
            'group': mem.get('type', 'unknown'),
        })

    # Build edges (find similar memories)
    edges = []
    if len(memories) > 1:
        search.index_memories(memories)

        for i, mem in enumerate(memories[:50]):  # Limit for performance
            related = search.search(mem['content'], memories, top_k=3, min_score=0.3)
            for rel in related:
                if rel['id'] != mem['id']:
                    edges.append({
                        'from': str(mem['id']),
                        'to': str(rel['id']),
                        'value': rel.get('semantic_score', 0.5),
                    })

    # Stats
    stats = memory.stats()

    return {
        'nodes': nodes,
        'edges': edges,
        'stats': stats,
    }


# Embedded HTML/JS for visualization - Simple card layout, no physics
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Grey Matter - Memory Viewer</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #1a1a2e;
            color: #eee;
            min-height: 100vh;
        }
        .header {
            padding: 20px 30px;
            background: #0f3460;
            display: flex;
            justify-content: space-between;
            align-items: center;
            position: sticky;
            top: 0;
            z-index: 100;
        }
        .header h1 { font-size: 1.5rem; color: #e94560; }
        .stats {
            display: flex;
            gap: 30px;
        }
        .stat { text-align: center; }
        .stat-value { font-size: 1.5rem; font-weight: bold; color: #e94560; }
        .stat-label { font-size: 0.8rem; color: #888; }
        .search-bar {
            padding: 15px 30px;
            background: #16213e;
        }
        .search-box {
            width: 100%;
            max-width: 500px;
            padding: 12px 20px;
            border: none;
            border-radius: 25px;
            background: #0f3460;
            color: #fff;
            font-size: 1rem;
        }
        .search-box::placeholder { color: #666; }
        .container {
            padding: 30px;
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 20px;
        }
        .memory-card {
            background: #16213e;
            border-radius: 12px;
            padding: 20px;
            border-left: 4px solid #e94560;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .memory-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        }
        .memory-card.preference { border-left-color: #e94560; }
        .memory-card.decision { border-left-color: #3498db; }
        .memory-card.learning { border-left-color: #2ecc71; }
        .memory-card.problem { border-left-color: #f39c12; }
        .memory-card.solution { border-left-color: #9b59b6; }
        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }
        .memory-type {
            font-size: 0.75rem;
            text-transform: uppercase;
            padding: 4px 10px;
            border-radius: 12px;
            background: #0f3460;
        }
        .importance {
            font-size: 0.8rem;
            color: #888;
        }
        .memory-content {
            font-size: 1rem;
            line-height: 1.5;
            color: #ddd;
        }
        .memory-date {
            margin-top: 15px;
            font-size: 0.75rem;
            color: #666;
        }
        .empty-state {
            grid-column: 1 / -1;
            text-align: center;
            padding: 60px;
            color: #666;
        }
        .empty-state h2 { margin-bottom: 10px; color: #888; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🧠 Grey Matter</h1>
        <div class="stats">
            <div class="stat">
                <div class="stat-value" id="stat-memories">0</div>
                <div class="stat-label">Memories</div>
            </div>
            <div class="stat">
                <div class="stat-value" id="stat-sessions">0</div>
                <div class="stat-label">Sessions</div>
            </div>
            <div class="stat">
                <div class="stat-value" id="stat-handoffs">0</div>
                <div class="stat-label">Handoffs</div>
            </div>
        </div>
    </div>

    <div class="search-bar">
        <input type="text" class="search-box" placeholder="Search memories..." id="search">
    </div>

    <div class="container" id="memory-list"></div>

    <script>
        let allData = null;

        async function loadData() {
            const response = await fetch('/api/graph');
            allData = await response.json();

            document.getElementById('stat-memories').textContent = allData.nodes.length;
            document.getElementById('stat-sessions').textContent = allData.stats.sessions || 0;
            document.getElementById('stat-handoffs').textContent = allData.stats.handoffs || 0;

            renderMemories(allData.nodes);
        }

        function renderMemories(memories) {
            const container = document.getElementById('memory-list');

            if (!memories || memories.length === 0) {
                container.innerHTML = '<div class="empty-state"><h2>No memories yet</h2><p>Start using Grey Matter and your memories will appear here!</p></div>';
                return;
            }

            container.innerHTML = memories.map(mem => `
                <div class="memory-card ${mem.type}">
                    <div class="card-header">
                        <span class="memory-type">${mem.type}</span>
                        <span class="importance">⭐ ${mem.importance}/10</span>
                    </div>
                    <div class="memory-content">${mem.content}</div>
                    <div class="memory-date">${mem.created_at}</div>
                </div>
            `).join('');
        }

        document.getElementById('search').addEventListener('input', function(e) {
            const query = e.target.value.toLowerCase();
            if (!allData) return;

            const filtered = allData.nodes.filter(n =>
                n.content.toLowerCase().includes(query) ||
                n.type.toLowerCase().includes(query)
            );

            renderMemories(filtered);
        });

        loadData();
    </script>
</body>
</html>
'''


class VisualizationHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP handler for visualization server"""

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == '/' or parsed.path == '/index.html':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode())

        elif parsed.path == '/api/graph':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            data = get_memory_graph_data()
            self.wfile.write(json.dumps(data).encode())

        elif parsed.path == '/api/stats':
            from .memory import get_memory
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            data = get_memory().stats()
            self.wfile.write(json.dumps(data).encode())

        else:
            self.send_error(404)

    def log_message(self, format, *args):
        pass  # Suppress logging


def start_server(port: int = 8765, open_browser: bool = True) -> None:
    """Start the visualization server"""
    with socketserver.TCPServer(("", port), VisualizationHandler) as httpd:
        url = f"http://localhost:{port}"
        print(f"🧠 Memory Visualization running at {url}")

        if open_browser:
            webbrowser.open(url)

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down...")


def start_server_background(port: int = 8765) -> threading.Thread:
    """Start server in background thread"""
    thread = threading.Thread(
        target=lambda: start_server(port, open_browser=True),
        daemon=True
    )
    thread.start()
    return thread


# CLI entry point
def main():
    import argparse
    parser = argparse.ArgumentParser(description='Memory Visualization')
    parser.add_argument('--port', '-p', type=int, default=8765)
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args()

    start_server(port=args.port, open_browser=not args.no_browser)


if __name__ == '__main__':
    main()
