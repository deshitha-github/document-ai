# Architecture Issue - numpy x86_64 vs ARM64

## Problem
You're on Apple Silicon (ARM64/M series chip) with Python 3.13, but numpy 1.26.4 is building with x86_64 architecture due to build toolchain issues.

## Quick Solution

### Option 1: Use Python 3.11 or 3.12 (Recommended)

Python 3.13 is very new and doesn't have pre-built ARM64 wheels for numpy 1.26.x. Use Python 3.11 or 3.12 instead:

```bash
# Install Python 3.12
brew install python@3.12

# Remove old venv
cd /Users/desh/document-ai
rm -rf .venv

# Create new venv with Python 3.12
python3.12 -m venv .venv

# Activate and install
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Test
python main.py
```

###Option 2: Try Without Virtual Environment (Quick Test Only)

If you just want to test quickly, you can use your system Python packages:

```bash
cd /Users/desh/document-ai
python3 main.py
```

**Note**: This isn't recommended for long-term use as it can cause conflicts with other projects.

### Option 3: Wait and Restart Terminal

Sometimes the issue is just cached environment variables:

1. Close your current terminal completely
2. Open a fresh terminal
3. Try the venv installation again:

```bash
cd /Users/desh/document-ai
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## Why This Happens

- Python 3.13 is brand new (released Oct 2024)
- Many packages don't have pre-built ARM64 wheels for it yet
- When building from source, the build tools sometimes default to x86_64
- Your Mac is ARM64 but can run x86_64 through Rosetta translation
- Python can't load mixed architecture libraries

## Recommended: Use Python 3.12

Python 3.12 has mature ARM64 support and all packages have pre-built wheels for it.

```bash
# Check Python versions
ls -la /opt/homebrew/bin/python*

# If you don't have Python 3.12:
brew install python@3.12

# Then recreate your venv with it
```

This will solve the problem permanently!

