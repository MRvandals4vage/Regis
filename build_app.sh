#!/bin/bash
# Builds the pure macOS .app bundle using PyInstaller

# Exit if any command fails
set -e

echo "🧹 Cleaning old builds..."
rm -rf build dist "Regis Assistant.spec"

echo "📦 Packaging with PyInstaller..."
# --windowed creates a Mac .app bundle and hides the terminal console
# --noconfirm overwrites output dir without asking
# --name defines the App name
pyinstaller --windowed --noconfirm --name "Regis Assistant" \
            --hidden-import PyQt6 \
            app.py

echo "✅ Build complete!"
echo "You can find your app here: dist/Regis Assistant.app"
echo "You can drag this to your /Applications folder!"
