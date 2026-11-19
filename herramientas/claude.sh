#!/bin/bash
# La app cambia de carpeta al actualizarse. Usamos el ejecutable más reciente.
base="$HOME/Library/Application Support/Claude/claude-code"
elegido=""
if [[ -d "$base" ]]; then
    while IFS= read -r -d '' candidato; do
        if [[ -x "$candidato" && ( -z "$elegido" || "$candidato" -nt "$elegido" ) ]]; then
            elegido="$candidato"
        fi
    done < <(find "$base" -type f -path '*/claude.app/Contents/MacOS/claude' -print0)
fi
if [[ -z "$elegido" ]]; then
    echo 'No encontré Claude Code en la app. Abrí o actualizá la app de Claude y probá de nuevo.' >&2
    exit 1
fi
# Las comillas mantienen las preguntas y los argumentos tal como llegaron.
exec "$elegido" "$@"
