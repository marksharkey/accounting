#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate

# Set up WeasyPrint dependencies
export DYLD_LIBRARY_PATH="/opt/homebrew/lib"
export PKG_CONFIG_PATH="/opt/homebrew/lib/pkgconfig"
export LDFLAGS="-L/opt/homebrew/opt/libffi/lib"
export CPPFLAGS="-I/opt/homebrew/opt/libffi/include"

# Start uvicorn
uvicorn main:app --port 8010 --reload
