#!/bin/bash
pkill -f "python3 generated/therapistPanel.py"
pkill -f "python3 generated/app_juegos.py" # También limpiamos la app por si acaso

export ROBOCOMP=$HOME/robocomp/core

# Obtener la ruta del directorio
BASE_DIR="$(dirname "$(realpath "$0")")"

# Ejecutar reiniciar.py
python3 "$BASE_DIR/reiniciar.py"
sleep 1

# Definir las rutas
declare -A rutas
declare -A scripts

rutas["GPT"]="$BASE_DIR/ebo_gpt"
scripts["GPT"]="ebo_gpt.py"

rutas["Pasapalabra"]="$BASE_DIR/pasapalabra"
scripts["Pasapalabra"]="pasapalabra.py"

rutas["SimonSay"]="$BASE_DIR/simonSay"
scripts["SimonSay"]="simonSay.py"

rutas["Storytelling"]="$BASE_DIR/storytelling"
scripts["Storytelling"]="storytelling.py"

# CAMBIO: Ahora APP_JUEGOS está en la lista de los que se lanzan desde generated
rutas["APP_JUEGOS"]="$BASE_DIR/app_juegos"
scripts["APP_JUEGOS"]="app_juegos.py"

rutas["EBO_APP"]="$BASE_DIR/ebo_app"
scripts["EBO_APP"]="ebo_app.py"

rutas["therapistPanel"]="$BASE_DIR/therapistPanel"
scripts["therapistPanel"]="therapistPanel.py"

rutas["encuesta"]="$BASE_DIR/encuesta"
scripts["encuesta"]="encuesta.py"

rutas["mirror"]="$BASE_DIR/mirror"
scripts["mirror"]="mirror.py"

rutas["trivial"]="$BASE_DIR/trivial"
scripts["trivial"]="trivial.py"

rutas["veoveo"]="$BASE_DIR/veoveo"
scripts["veoveo"]="veoveo.py"

# Función mejorada
function abrir_pestana {
    local ruta="$1"
    local nombre="$2"
    local script="$3"
    local subcarpeta="src"

    # Si son componentes recientes, usamos 'generated'
    if [[ "$nombre" == "therapistPanel" || "$nombre" == "mirror" || "$nombre" == "encuesta" || "$nombre" == "trivial" || "$nombre" == "veoveo" || "$nombre" == "APP_JUEGOS" ]]; then subcarpeta="generated"
    fi

    gnome-terminal --tab -- bash -c "
        cd '$ruta' &&
        echo 'Activando games_venv...' &&
        source '$BASE_DIR/games_venv/bin/activate' &&
        echo 'Iniciando $nombre desde $subcarpeta...' &&
        python3 $subcarpeta/$script etc/config;
        exec bash
    "
}

# Iterar sobre las rutas
for nombre in "${!rutas[@]}"; do
    abrir_pestana "${rutas[$nombre]}" "$nombre" "${scripts[$nombre]}"
    sleep 0.00001
done
