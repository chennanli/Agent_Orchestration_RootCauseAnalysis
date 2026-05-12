#!/bin/bash

# ==============================================================================
# TEP Unified Control System - Startup Script
# ==============================================================================
# Follows best practices:
# - Uses hidden virtual environment (.venv/)
# - Single consolidated requirements.txt
# - Auto-creates venv if missing
#
# Behavior: Only starts Unified Console
# Backend and Frontend require manual button clicks (matches original TE system)
# ==============================================================================

cd "$(dirname "$0")"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 TEP Unified Control System - Starting..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Determine Python executable to use (require Python 3.12)
# Prefer an existing project virtualenv, then system python3.12, then python3 if it's 3.12
PYTHON_EXEC=""
if [ -x ".venv/bin/python" ]; then
    VENV_VER=$(.venv/bin/python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || echo "")
    if [ "$VENV_VER" = "3.12" ]; then
        PYTHON_EXEC=".venv/bin/python"
        PYTHON_VERSION=$($PYTHON_EXEC --version 2>&1)
        echo "🐍 Using project venv: $PYTHON_VERSION ✅"
    fi
fi

if [ -z "$PYTHON_EXEC" ]; then
    if command -v python3.12 &> /dev/null; then
        PYTHON_EXEC=python3.12
        PYTHON_VERSION=$($PYTHON_EXEC --version 2>&1)
        echo "🐍 $PYTHON_VERSION ✅"
    else
        # Fallback: check python3 and require it to be 3.12
        if command -v python3 &> /dev/null; then
            P3VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || echo "")
            if [ "$P3VER" = "3.12" ]; then
                PYTHON_EXEC=python3
                PYTHON_VERSION=$($PYTHON_EXEC --version 2>&1)
                echo "🐍 $PYTHON_VERSION ✅"
            fi
        fi
    fi
fi

if [ -z "$PYTHON_EXEC" ]; then
    echo "❌ Python 3.12 not found!"
    echo "   Please install: brew install python@3.12"
    echo "   Then run: ./SETUP_NEW_LAPTOP.sh"
    echo ""
    echo "Press any key to close..."
    read -n 1
    exit 1
fi

# Check for virtual environment (.venv is best practice - hidden directory)
if [ ! -d ".venv" ]; then
    echo ""
    echo "📦 Virtual environment not found. Creating .venv/ with Python 3.12..."
    echo "   (Using hidden directory .venv/ as per Python best practices)"

    $PYTHON_EXEC -m venv .venv

    if [ $? -ne 0 ]; then
        echo "❌ Failed to create virtual environment"
        echo "   Please run: ./SETUP_NEW_LAPTOP.sh for complete setup"
        echo ""
        echo "Press any key to close..."
        read -n 1
        exit 1
    fi

    echo "✅ Virtual environment created: .venv/"
    echo ""
    echo "📥 Installing Python dependencies from requirements.txt..."
    echo "   This may take a few minutes on first run..."

    source .venv/bin/activate

    # Ensure we prefer the newly-created venv python
    PYTHON_EXEC=".venv/bin/python"

    # Upgrade pip first
    pip install --upgrade pip --quiet

    # Install from requirements.txt
    pip install -r requirements.txt

    if [ $? -ne 0 ]; then
        echo "❌ Failed to install dependencies"
        echo "   Please run: ./SETUP_FIRST_TIME.command for complete setup"
        echo ""
        echo "Press any key to close..."
        read -n 1
        exit 1
    fi

    echo "✅ All dependencies installed successfully"
    echo ""
else
    echo "✅ Virtual environment found: .venv/"
    source .venv/bin/activate

    # Prefer the venv python for running commands
    PYTHON_EXEC=".venv/bin/python"

    # Verify Python in venv
    VENV_PYTHON_VERSION=$($PYTHON_EXEC --version)
    echo "   Using: $VENV_PYTHON_VERSION"
    echo ""
fi

# Verify critical packages are installed
echo "🔍 Verifying critical packages..."
"$PYTHON_EXEC" -c "import fastapi, flask, anthropic, openai, genai" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠️  Warning: Some packages may be missing"
    echo "   Installing/updating requirements..."
    .venv/bin/pip install -r requirements.txt --quiet
    echo "✅ Packages updated"
    echo ""
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Starting Unified Console..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📍 Control Panel URL: http://127.0.0.1:9002"
echo ""
echo "💡 Note: Backend and Frontend will NOT auto-start."
echo "   Use the control panel buttons to start them manually:"
echo "   • Click '🚀 Ultra Start' for one-click startup (recommended)"
echo "   • Or start components individually"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Start Unified Console (only this - matches original TE system behavior)
# IMPORTANT: Use selected python executable to ensure packages are found
"$PYTHON_EXEC" unified_console.py

# Keep terminal open on error
if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Error occurred while running unified_console.py"
    echo "   Check logs above for details"
    echo ""
    echo "Press any key to close..."
    read -n 1
fi
