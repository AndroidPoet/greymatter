#!/bin/bash
# Grey Matter Installer
# Makes claude++, gemini++, ollama++, mem available globally

set -e

echo "🧠 Installing Grey Matter - Human-Like Memory for AI CLIs"
echo "=========================================================="

# Find Python
PYTHON=""
for cmd in python3 python; do
    if command -v $cmd &> /dev/null; then
        PYTHON=$cmd
        break
    fi
done

if [ -z "$PYTHON" ]; then
    echo "❌ Python not found. Please install Python 3.8+"
    exit 1
fi

PYTHON_VERSION=$($PYTHON -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "✓ Found Python $PYTHON_VERSION"

# Install location
INSTALL_DIR="$HOME/.greymatter"
BIN_DIR="$HOME/.local/bin"

mkdir -p "$INSTALL_DIR"
mkdir -p "$BIN_DIR"

# Copy package
echo "→ Installing to $INSTALL_DIR"
cp -r "$(dirname "$0")/greymatter" "$INSTALL_DIR/"

# Create wrapper scripts
echo "→ Creating commands..."

# claude++
cat > "$BIN_DIR/claude++" << 'EOF'
#!/usr/bin/env python3
import sys
sys.path.insert(0, "$INSTALL_DIR")
from greymatter.wrapper import main
sys.exit(main())
EOF
sed -i.bak "s|\$INSTALL_DIR|$INSTALL_DIR|g" "$BIN_DIR/claude++"
rm -f "$BIN_DIR/claude++.bak"
chmod +x "$BIN_DIR/claude++"

# gemini++
cat > "$BIN_DIR/gemini++" << 'EOF'
#!/usr/bin/env python3
import sys
sys.path.insert(0, "$INSTALL_DIR")
from greymatter.wrapper import main
sys.exit(main())
EOF
sed -i.bak "s|\$INSTALL_DIR|$INSTALL_DIR|g" "$BIN_DIR/gemini++"
rm -f "$BIN_DIR/gemini++.bak"
chmod +x "$BIN_DIR/gemini++"

# ollama++
cat > "$BIN_DIR/ollama++" << 'EOF'
#!/usr/bin/env python3
import sys
sys.path.insert(0, "$INSTALL_DIR")
from greymatter.wrapper import main
sys.exit(main())
EOF
sed -i.bak "s|\$INSTALL_DIR|$INSTALL_DIR|g" "$BIN_DIR/ollama++"
rm -f "$BIN_DIR/ollama++.bak"
chmod +x "$BIN_DIR/ollama++"

# gm (shortcut)
cat > "$BIN_DIR/gm" << 'EOF'
#!/usr/bin/env python3
import sys
sys.path.insert(0, "$INSTALL_DIR")
from greymatter.wrapper import main
sys.exit(main())
EOF
sed -i.bak "s|\$INSTALL_DIR|$INSTALL_DIR|g" "$BIN_DIR/gm"
rm -f "$BIN_DIR/gm.bak"
chmod +x "$BIN_DIR/gm"

# mem
cat > "$BIN_DIR/mem" << 'EOF'
#!/usr/bin/env python3
import sys
sys.path.insert(0, "$INSTALL_DIR")
from greymatter.cli import main
sys.exit(main())
EOF
sed -i.bak "s|\$INSTALL_DIR|$INSTALL_DIR|g" "$BIN_DIR/mem"
rm -f "$BIN_DIR/mem.bak"
chmod +x "$BIN_DIR/mem"

# mem-viz
cat > "$BIN_DIR/mem-viz" << 'EOF'
#!/usr/bin/env python3
import sys
sys.path.insert(0, "$INSTALL_DIR")
from greymatter.visualize import main
sys.exit(main())
EOF
sed -i.bak "s|\$INSTALL_DIR|$INSTALL_DIR|g" "$BIN_DIR/mem-viz"
rm -f "$BIN_DIR/mem-viz.bak"
chmod +x "$BIN_DIR/mem-viz"

echo ""
echo "✅ Installation complete!"
echo ""
echo "Commands installed:"
echo "  • claude++   - Claude with human-like memory"
echo "  • gemini++   - Gemini with human-like memory"
echo "  • ollama++   - Ollama with human-like memory"
echo "  • gm         - Grey Matter (auto-detects AI)"
echo "  • mem        - Memory management CLI"
echo "  • mem-viz    - Memory visualization (web UI)"
echo ""

# Check PATH
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    echo "⚠️  Add to your ~/.zshrc or ~/.bashrc:"
    echo ""
    echo "    export PATH=\"\$HOME/.local/bin:\$PATH\""
    echo ""
    echo "Then run: source ~/.zshrc"
    echo ""
fi

echo "Quick start:"
echo "  claude++     # Just run - everything is automatic!"
echo ""
