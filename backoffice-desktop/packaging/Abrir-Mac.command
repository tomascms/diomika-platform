#!/bin/bash
# Diomika Backoffice — desbloqueia (quarentena Gatekeeper) e abre a app.
# Mac: 1.ª vez → botão direito neste ficheiro → Abrir → Abrir.
set -e
cd "$(dirname "$0")"

echo ""
echo " Diomika Backoffice"
echo " -------------------"

APP_DIR=".diomika"
APP="$APP_DIR/Diomika Backoffice.app"

echo " - A remover quarentena (ficheiros descarregados)..."
xattr -dr com.apple.quarantine . 2>/dev/null || true

if [ -d "$APP" ]; then
  xattr -cr "$APP" 2>/dev/null || true
  codesign --force --deep --sign - "$APP" 2>/dev/null || true
  echo " - A abrir Diomika Backoffice..."
  open "$APP"
  exit 0
fi

ZIP=$(ls Diomika-Backoffice-*-mac.zip 2>/dev/null | head -1)
if [ -n "$ZIP" ]; then
  echo " - A extrair $ZIP..."
  mkdir -p "$APP_DIR"
  ditto -x -k "$ZIP" "$APP_DIR"
  if [ ! -d "$APP" ]; then
    FOUND=$(find "$APP_DIR" -maxdepth 3 -name "Diomika Backoffice.app" -type d | head -1)
    [ -n "$FOUND" ] && APP="$FOUND"
  fi
fi

if [ ! -d "$APP" ]; then
  DMG=$(ls Diomika-Backoffice-*-mac.dmg 2>/dev/null | head -1)
  if [ -n "$DMG" ]; then
    echo " - A montar $DMG..."
    MOUNT=$(hdiutil attach "$DMG" -nobrowse -noverify -quiet | awk 'END {print $NF}')
    SRC=$(find "$MOUNT" -maxdepth 2 -name "Diomika Backoffice.app" -type d 2>/dev/null | head -1)
    if [ -z "$SRC" ]; then
      SRC=$(find "$MOUNT" -maxdepth 2 -name "*.app" -type d 2>/dev/null | head -1)
    fi
    if [ -n "$SRC" ]; then
      mkdir -p "$APP_DIR"
      echo " - A copiar a app (só na 1.ª vez)..."
      ditto "$SRC" "$APP"
    fi
    hdiutil detach "$MOUNT" -quiet 2>/dev/null || hdiutil detach "$MOUNT" -force -quiet 2>/dev/null || true
  fi
fi

if [ ! -d "$APP" ]; then
  echo ""
  echo " ERRO: falta Diomika-Backoffice-*-mac.dmg nesta pasta."
  echo " Mac (1.ª vez): botão direito em Abrir-Mac.command → Abrir."
  echo ""
  read -r -p "Enter para fechar..."
  exit 1
fi

xattr -cr "$APP" 2>/dev/null || true
codesign --force --deep --sign - "$APP" 2>/dev/null || true
echo " - A abrir Diomika Backoffice..."
open "$APP"
