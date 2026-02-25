#!/bin/bash
# Regia Installer for Linux/macOS
# Run: bash install-linux.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REGIA_DIR="$(dirname "$SCRIPT_DIR")"

echo ""
echo "============================================"
echo "       Regia Installer for Linux/macOS      "
echo "   Intelligent Document Management System   "
echo "============================================"
echo ""

command_exists() { command -v "$1" &> /dev/null; }

# === Check Python ===
echo "[1/6] Checking Python..."
if command_exists python3; then
    echo "  Found: $(python3 --version)"
else
    echo "  Python3 not found. Installing..."
    if command_exists apt-get; then
        sudo apt-get update && sudo apt-get install -y python3 python3-venv python3-pip
    elif command_exists brew; then
        brew install python@3.12
    elif command_exists dnf; then
        sudo dnf install -y python3 python3-pip
    else
        echo "  ERROR: Cannot auto-install Python. Please install Python 3.11+ manually."
        exit 1
    fi
fi

# === Check Node.js ===
echo "[2/6] Checking Node.js..."
if command_exists node; then
    echo "  Found: Node.js $(node --version)"
else
    echo "  Node.js not found. Installing..."
    if command_exists apt-get; then
        curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
        sudo apt-get install -y nodejs
    elif command_exists brew; then
        brew install node
    else
        echo "  ERROR: Cannot auto-install Node.js. Please install Node.js 18+ manually."
        exit 1
    fi
fi

# === Check Ollama (optional) ===
echo "[3/6] Checking Ollama (AI engine)..."
if command_exists ollama; then
    echo "  Found: Ollama installed"
else
    read -p "  Ollama not found. Install for AI features? (Y/n) " answer
    if [[ "$answer" != "n" && "$answer" != "N" ]]; then
        echo "  Installing Ollama..."
        curl -fsSL https://ollama.com/install.sh | sh
        echo "  Pulling lightweight AI model..."
        ollama pull qwen2.5:0.5b
    else
        echo "  Skipped. Regia will use rule-based classification."
    fi
fi

# === Check Tesseract (optional) ===
echo "[3b/6] Checking Tesseract OCR..."
if command_exists tesseract; then
    echo "  Found: Tesseract installed"
else
    echo "  Installing Tesseract OCR..."
    if command_exists apt-get; then
        sudo apt-get install -y tesseract-ocr
    elif command_exists brew; then
        brew install tesseract
    else
        echo "  Skipped. OCR features may be limited."
    fi
fi

# === Setup Backend ===
echo "[4/6] Setting up backend..."
cd "$REGIA_DIR/backend"
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
./venv/bin/pip install -r requirements.txt -q
echo "  Backend dependencies installed"

# === Setup Frontend ===
echo "[5/6] Setting up frontend..."
cd "$REGIA_DIR/frontend"
npm install --silent
echo "  Frontend dependencies installed"

# === Create Start Script ===
echo "[6/6] Creating start script..."
cat > "$REGIA_DIR/start-regia.sh" << 'SCRIPT'
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Starting Regia..."

# Start backend
cd "$SCRIPT_DIR/backend"
./venv/bin/python run.py &
BACKEND_PID=$!

sleep 3

# Start frontend
cd "$SCRIPT_DIR/frontend"
npm run dev &
FRONTEND_PID=$!

sleep 2

echo ""
echo "Regia is running!"
echo "  Backend:  http://localhost:8420"
echo "  Frontend: http://localhost:5173"
echo ""
echo "Press Ctrl+C to stop."

# Open browser
if command -v xdg-open &> /dev/null; then
    xdg-open http://localhost:5173
elif command -v open &> /dev/null; then
    open http://localhost:5173
fi

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT
wait
SCRIPT
chmod +x "$REGIA_DIR/start-regia.sh"

echo ""
echo "============================================"
echo "  Regia installed successfully!             "
echo "============================================"
echo ""
echo "  Run './start-regia.sh' to launch Regia"
echo "  Or run 'npm run tauri:dev' in frontend/ for desktop mode"
echo ""
