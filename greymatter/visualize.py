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


# Embedded HTML/JS for visualization
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Grey Matter Memory Visualization</title>
    <script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #1a1a2e;
            color: #eee;
        }
        .container {
            display: flex;
            height: 100vh;
        }
        .sidebar {
            width: 300px;
            background: #16213e;
            padding: 20px;
            overflow-y: auto;
        }
        .main {
            flex: 1;
            display: flex;
            flex-direction: column;
        }
        .header {
            padding: 15px 20px;
            background: #0f3460;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .header h1 {
            font-size: 1.5rem;
            color: #e94560;
        }
        #graph {
            flex: 1;
            background: #1a1a2e;
        }
        .stat-card {
            background: #0f3460;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 15px;
        }
        .stat-card h3 {
            color: #e94560;
            margin-bottom: 10px;
        }
        .stat-value {
            font-size: 2rem;
            font-weight: bold;
        }
        .search-box {
            width: 100%;
            padding: 10px;
            border: none;
            border-radius: 5px;
            background: #0f3460;
            color: #fff;
            margin-bottom: 15px;
        }
        .memory-item {
            background: #0f3460;
            padding: 10px;
            border-radius: 5px;
            margin-bottom: 10px;
            cursor: pointer;
            transition: all 0.2s;
        }
        .memory-item:hover {
            background: #e94560;
        }
        .memory-type {
            font-size: 0.8rem;
            color: #888;
            text-transform: uppercase;
        }
        .memory-content {
            font-size: 0.9rem;
            margin-top: 5px;
        }
        .importance {
            display: inline-block;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            margin-right: 5px;
        }
        .importance-high { background: #e94560; }
        .importance-med { background: #f39c12; }
        .importance-low { background: #3498db; }
        .legend {
            display: flex;
            gap: 15px;
            font-size: 0.8rem;
        }
        .legend-item {
            display: flex;
            align-items: center;
            gap: 5px;
        }
        .legend-dot {
            width: 12px;
            height: 12px;
            border-radius: 50%;
        }
        .detail-panel {
            position: fixed;
            right: 0;
            top: 0;
            width: 350px;
            height: 100%;
            background: #16213e;
            padding: 20px;
            transform: translateX(100%);
            transition: transform 0.3s;
            overflow-y: auto;
        }
        .detail-panel.open {
            transform: translateX(0);
        }
        .close-btn {
            float: right;
            background: none;
            border: none;
            color: #e94560;
            font-size: 1.5rem;
            cursor: pointer;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="sidebar">
            <input type="text" class="search-box" placeholder="Search memories..." id="search">

            <div class="stat-card">
                <h3>Memories</h3>
                <div class="stat-value" id="stat-memories">0</div>
            </div>

            <div class="stat-card">
                <h3>Sessions</h3>
                <div class="stat-value" id="stat-sessions">0</div>
            </div>

            <div class="stat-card">
                <h3>Connections</h3>
                <div class="stat-value" id="stat-edges">0</div>
            </div>

            <h3 style="margin: 20px 0 10px;">Recent Memories</h3>
            <div id="memory-list"></div>
        </div>

        <div class="main">
            <div class="header">
                <h1>🧠 Grey Matter Memory Graph</h1>
                <div class="legend">
                    <div class="legend-item">
                        <div class="legend-dot" style="background: #e94560;"></div>
                        preference
                    </div>
                    <div class="legend-item">
                        <div class="legend-dot" style="background: #3498db;"></div>
                        decision
                    </div>
                    <div class="legend-item">
                        <div class="legend-dot" style="background: #2ecc71;"></div>
                        learning
                    </div>
                    <div class="legend-item">
                        <div class="legend-dot" style="background: #f39c12;"></div>
                        problem
                    </div>
                </div>
            </div>
            <div id="graph"></div>
        </div>
    </div>

    <div class="detail-panel" id="detail-panel">
        <button class="close-btn" onclick="closeDetail()">×</button>
        <h2 id="detail-title">Memory Details</h2>
        <div id="detail-content"></div>
    </div>

    <script>
        let network = null;
        let allData = null;

        // Color mapping for types
        const typeColors = {
            'preference': '#e94560',
            'decision': '#3498db',
            'learning': '#2ecc71',
            'problem': '#f39c12',
            'solution': '#9b59b6',
            'instruction': '#1abc9c',
            'inform': '#95a5a6',
            'unknown': '#7f8c8d'
        };

        async function loadData() {
            const response = await fetch('/api/graph');
            allData = await response.json();

            // Update stats
            document.getElementById('stat-memories').textContent = allData.nodes.length;
            document.getElementById('stat-sessions').textContent = allData.stats.sessions || 0;
            document.getElementById('stat-edges').textContent = allData.edges.length;

            // Update memory list
            const listEl = document.getElementById('memory-list');
            listEl.innerHTML = allData.nodes.slice(0, 20).map(node => `
                <div class="memory-item" onclick="focusNode('${node.id}')">
                    <span class="importance importance-${node.importance >= 7 ? 'high' : node.importance >= 4 ? 'med' : 'low'}"></span>
                    <span class="memory-type">${node.type}</span>
                    <div class="memory-content">${node.label}</div>
                </div>
            `).join('');

            // Create graph
            renderGraph(allData);
        }

        function renderGraph(data) {
            const container = document.getElementById('graph');

            // Destroy existing network to prevent memory leaks
            if (network) {
                network.destroy();
                network = null;
            }

            // Skip if no data
            if (!data.nodes || data.nodes.length === 0) {
                container.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100%;color:#888;font-size:1.2rem;">No memories yet. Start using Grey Matter!</div>';
                return;
            }

            const nodes = new vis.DataSet(data.nodes.map(n => ({
                ...n,
                color: {
                    background: typeColors[n.type] || typeColors['unknown'],
                    border: '#fff',
                    highlight: { background: '#fff', border: typeColors[n.type] }
                },
                size: 10 + n.importance * 2,
                font: { color: '#fff', size: 10 }
            })));

            const edges = new vis.DataSet(data.edges.map(e => ({
                ...e,
                color: { color: 'rgba(255,255,255,0.2)', highlight: '#e94560' },
                width: e.value * 3
            })));

            const options = {
                nodes: {
                    shape: 'dot',
                    borderWidth: 2,
                },
                edges: {
                    smooth: { type: 'continuous' }
                },
                physics: data.nodes.length > 2 ? {
                    stabilization: {
                        enabled: true,
                        iterations: 100,
                        updateInterval: 50
                    },
                    barnesHut: {
                        gravitationalConstant: -2000,
                        springConstant: 0.04,
                        damping: 0.5
                    },
                    minVelocity: 1.0,
                    maxVelocity: 30
                } : false,  // Disable physics for small graphs
                interaction: {
                    hover: true,
                    tooltipDelay: 100
                }
            };

            network = new vis.Network(container, { nodes, edges }, options);

            network.on('click', function(params) {
                if (params.nodes.length > 0) {
                    showDetail(params.nodes[0]);
                }
            });

            // Stop physics after stabilization
            network.on('stabilizationIterationsDone', function() {
                network.setOptions({ physics: false });
            });
        }

        function focusNode(nodeId) {
            if (network) {
                network.focus(nodeId, { scale: 1.5, animation: true });
                network.selectNodes([nodeId]);
                showDetail(nodeId);
            }
        }

        function showDetail(nodeId) {
            const node = allData.nodes.find(n => n.id === nodeId);
            if (!node) return;

            document.getElementById('detail-title').textContent = node.type;
            document.getElementById('detail-content').innerHTML = `
                <p style="margin: 15px 0;"><strong>Content:</strong></p>
                <p>${node.content}</p>
                <p style="margin: 15px 0;"><strong>Importance:</strong> ${node.importance}/10</p>
                <p><strong>Created:</strong> ${node.created_at}</p>
            `;
            document.getElementById('detail-panel').classList.add('open');
        }

        function closeDetail() {
            document.getElementById('detail-panel').classList.remove('open');
        }

        // Search
        document.getElementById('search').addEventListener('input', function(e) {
            const query = e.target.value.toLowerCase();
            if (!allData) return;

            const filtered = {
                nodes: allData.nodes.filter(n =>
                    n.content.toLowerCase().includes(query) ||
                    n.type.toLowerCase().includes(query)
                ),
                edges: allData.edges,
                stats: allData.stats
            };

            renderGraph(filtered);
        });

        // Load on start
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
