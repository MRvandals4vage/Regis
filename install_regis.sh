#!/bin/bash
# install_regis.sh — Build and install Regis as a native macOS App

set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
UI="$ROOT/assistant-ui"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'

printf "${YELLOW}🚀 Starting Regis build process...${NC}\n"

# 1. Ensure launcher script is executable
printf "🔧 Setting permissions...\n"
chmod +x "$UI/resources/backend_launcher.sh"

# 2. Install dependencies if needed
if [ ! -d "$UI/node_modules" ]; then
    printf "📦 Installing Node dependencies...\n"
    cd "$UI" && npm install
fi

# 3. Build the app
printf "🏗️ Building Regis.app (this may take a minute)...\n"
cd "$UI"
npm run build:mac

# 4. Move to Applications
printf "🚚 Installing to /Applications...\n"
APP_NAME="Regis.app"
# Find the actual build directory (handles mac/ or mac-arm64/)
BUILD_DIR=$(find "$UI/dist" -name "$APP_NAME" -maxdepth 3 | head -n 1 | xargs dirname)

if [ -n "$BUILD_DIR" ] && [ -d "$BUILD_DIR/$APP_NAME" ]; then
    # Remove old version if exists
    rm -rf "/Applications/$APP_NAME"
    cp -R "$BUILD_DIR/$APP_NAME" "/Applications/"
    printf "${GREEN}✅ Regis has been installed to /Applications!${NC}\n"
else
    printf "${RED}❌ Build failed: Could not find $APP_NAME in $UI/dist${NC}\n"
    exit 1
fi

# 5. Launch it
printf "✨ Launching Regis...\n"
open "/Applications/$APP_NAME"

printf "\n${GREEN}🎉 All done! Regis is now running from your menu bar.${NC}\n"
printf "${YELLOW}Tip: You can find it in your Applications folder and it's set to start at login.${NC}\n"
