#!/bin/zsh
# Instala (o reinstala) el vigilante como tarea de launchd en esta Mac: corre
# clientes/navar/herramientas/vigilante.py cada 15 minutos, aunque no haya nadie logueado
# en la sesión (sí tiene que estar la Mac prendida y Google Drive corriendo).
#
#   zsh clientes/navar/herramientas/instalar_vigilante.sh          # instala
#   zsh clientes/navar/herramientas/instalar_vigilante.sh quitar   # desinstala
#
# Para ver qué hizo: tail -50 clientes/navar/privado/vigilante.log

set -e
REPO="$(cd "$(dirname "$0")/../../.." && pwd)"
ETIQUETA="com.finauto.navar.vigilante"
PLIST="$HOME/Library/LaunchAgents/$ETIQUETA.plist"

if [[ "$1" == "quitar" ]]; then
  launchctl bootout "gui/$(id -u)/$ETIQUETA" 2>/dev/null || true
  rm -f "$PLIST"
  echo "vigilante desinstalado"
  exit 0
fi

mkdir -p "$HOME/Library/LaunchAgents" "$REPO/clientes/navar/privado"
cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$ETIQUETA</string>
  <key>ProgramArguments</key>
  <array>
    <string>$REPO/.venv/bin/python</string>
    <string>$REPO/clientes/navar/herramientas/vigilante.py</string>
  </array>
  <key>WorkingDirectory</key><string>$REPO</string>
  <key>StartInterval</key><integer>900</integer>
  <key>RunAtLoad</key><true/>
  <key>StandardOutPath</key><string>$REPO/clientes/navar/privado/vigilante.launchd.log</string>
  <key>StandardErrorPath</key><string>$REPO/clientes/navar/privado/vigilante.launchd.log</string>
  <key>EnvironmentVariables</key>
  <dict><key>PATH</key><string>/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin</string></dict>
</dict>
</plist>
EOF

launchctl bootout "gui/$(id -u)/$ETIQUETA" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
echo "vigilante instalado: corre cada 15 min. Log: clientes/navar/privado/vigilante.log"
