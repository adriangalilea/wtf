#!/bin/bash --norc --noprofile
# Preview script for wtf

# Get command and path from arguments
cmd="$1"
path="$2"

# Remove quotes if present
cmd="${cmd#\'}"
cmd="${cmd%\'}"
path="${path#\'}"
path="${path%\'}"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📦 Command: $cmd"
echo "📍 Path: $path"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Documentation first - this is what matters
if command -v tldr >/dev/null 2>&1 && tldr "$cmd" >/dev/null 2>&1; then
    # tldr exists and has entry for this command
    tldr "$cmd" 2>/dev/null | head -40
elif man "$cmd" >/dev/null 2>&1; then
    # Use man page
    echo "📖 From man page:"
    echo ""
    man "$cmd" 2>/dev/null | col -b | head -30
else
    # No docs available
    echo "No documentation found"
    echo ""
    echo "Try running:"
    echo "  $cmd --help"
    echo "  $cmd -h"
fi

# File details at the bottom - nicely formatted
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📄 File Details:"
echo ""

if [ -f "$path" ]; then
    # Permissions and size
    echo "• Permissions: $(ls -lah "$path" 2>/dev/null | awk '{print $1}')"
    echo "• Size: $(ls -lah "$path" 2>/dev/null | awk '{print $5}')"
    echo "• Modified: $(ls -lah "$path" 2>/dev/null | awk '{print $7, $8, $9}')"
    echo ""
    
    # File type
    echo "• Type: $(file -b "$path" 2>/dev/null | head -1)"
    
    # If it's a symlink, show where it points
    if [ -L "$path" ]; then
        echo "• Links to: $(readlink "$path")"
    fi
fi