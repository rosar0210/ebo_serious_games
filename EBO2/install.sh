#!/bin/bash
set -euo pipefail

# Script de instalación automática de EBO2 (usa Python 3.10 para el venv)

PROJECT_PATH="$(pwd)"
VENV_DIR="$PROJECT_PATH/games_venv"
PY_CMD="python3.11"
REQUIREMENTS="$PROJECT_PATH/requirements.txt"

echo "Ruta del proyecto: $PROJECT_PATH"

# Función para comprobar si un comando existe
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Comprueba si python3.10 está instalado; si no, intenta instalarlo
ensure_python310() {
    if command_exists "$PY_CMD"; then
        echo "Encontrado $PY_CMD: $($PY_CMD --version 2>&1)"
        return 0
    fi

    echo "Python 3.10 no encontrado. Intentando instalar desde repositorios..."

    # intentar instalación directa
    sudo apt-get update -y
    # instalar paquetes básicos necesarios
    sudo apt-get install -y software-properties-common apt-transport-https ca-certificates gnupg

    # Intento 1: instalar paquetes directamente
    if sudo DEBIAN_FRONTEND=noninteractive apt-get install -y python3.10 python3.10-venv python3.10-distutils; then
        echo "python3.10 instalado desde repositorios."
        return 0
    fi

    echo "Instalación directa falló. Añadiendo PPA deadsnakes y reintentando..."

    # Añadir deadsnakes PPA e instalar (fallback)
    sudo add-apt-repository -y ppa:deadsnakes/ppa
    sudo apt-get update -y
    sudo DEBIAN_FRONTEND=noninteractive apt-get install -y python3.10 python3.10-venv python3.10-distutils

    if command_exists "$PY_CMD"; then
        echo "python3.10 instalado correctamente (vía deadsnakes)."
        return 0
    else
        echo "Error: No se pudo instalar python3.10 automáticamente."
        echo "Por favor instala Python 3.10 manualmente (ej: sudo apt install python3.10 python3.10-venv) y vuelve a ejecutar este script."
        exit 1
    fi
}

# Obtener versión de python en formato major.minor (ej: 3.10)
get_major_minor() {
    "$1" -c 'import sys; v = sys.version_info; print(f"{v.major}.{v.minor}")'
}

# Comprueba si el venv existente usa Python 3.10; si no, lo recrea
ensure_venv() {
    if [ -d "$VENV_DIR" ]; then
        if [ -x "$VENV_DIR/bin/python" ]; then
            VENV_VER="$(get_major_minor "$VENV_PY" 2>/dev/null || true)"
   	 	if [ "$VENV_VER" = "3.10" ] || [ "$VENV_VER" = "3.11" ]; then
        		echo "El venv ya existe y usa Python $VENV_VER (se reutilizará)."
        		return 0
    		else
        		echo "El venv existente usa Python $VENV_VER. Se recreará para ajustarse."
        		rm -rf "$VENV_DIR"
   		 fi
        else
            echo "El venv existe pero no tiene $VENV_DIR/bin/python ejecutable. Se recreará."
            rm -rf "$VENV_DIR"
        fi
    fi

    # Crear el entorno virtual con python3.10
    echo "Creando entorno virtual con $PY_CMD..."
    "$PY_CMD" -m venv "$VENV_DIR"
    echo "Entorno virtual games_venv creado con $PY_CMD."
}

# --------------------------
# Inicio del script
# --------------------------

# Asegúrate de tener python3.10
ensure_python310

# Crear/recrear venv si procede
ensure_venv

# Activar venv
# shellcheck disable=SC1090
source "$VENV_DIR/bin/activate"

# Actualizar pip y setuptools y wheel dentro del venv (usa el pip del propio venv)
python -m pip install --upgrade pip setuptools wheel

# Instalar dependencias si existe requirements.txt
if [ -f "$REQUIREMENTS" ]; then
    echo "Instalando dependencias desde $REQUIREMENTS ..."
    python -m pip install -r "$REQUIREMENTS"
    echo "Dependencias instaladas."
else
    echo "No se encontró $REQUIREMENTS — omitiendo instalación de dependencias."
fi

# Desactivar venv
deactivate

# --------------------------
# Resto del instalador (.desktop, icono, permisos...)
# --------------------------

echo "Configurando el archivo .desktop..."

DESKTOP_FILE="EBO2.desktop"
ICON_FILE="happy_sinfondo.png"

if [ ! -f "$DESKTOP_FILE" ]; then
    echo "Error: $DESKTOP_FILE no encontrado en $PROJECT_PATH"
    exit 1
fi

if [ ! -f "$PROJECT_PATH/$ICON_FILE" ]; then
    echo "Error: Icono $ICON_FILE no encontrado en $PROJECT_PATH"
    exit 1
fi

# Reemplazar Exec e Icon en el .desktop con la ruta absoluta
sed -i "s|^Exec=.*|Exec=$PROJECT_PATH/iniciar_juegos.sh|" "$DESKTOP_FILE"
sed -i "s|^Icon=.*|Icon=$PROJECT_PATH/$ICON_FILE|" "$DESKTOP_FILE"

# Copiar al escritorio (compatibilidad Español/Inglés)
for DIR in "$HOME/Desktop" "$HOME/Escritorio"; do
    mkdir -p "$DIR"
    cp "$DESKTOP_FILE" "$DIR/"
    chmod +x "$DIR/$DESKTOP_FILE"
    # marcar como confiable (GIO)
    if command_exists gio; then
        gio set "$DIR/$DESKTOP_FILE" "metadata::trusted" yes || true
    fi
done

# Copiar al menú de aplicaciones
APP_DIR="$HOME/.local/share/applications"
mkdir -p "$APP_DIR"
cp "$DESKTOP_FILE" "$APP_DIR/"
chmod +x "$APP_DIR/$DESKTOP_FILE"

# Ajustar permisos del icono
chmod 644 "$PROJECT_PATH/$ICON_FILE"

# Actualizar caché del menú de aplicaciones (si existe la herramienta)
if command_exists update-desktop-database; then
    update-desktop-database "$APP_DIR" || true
fi

# Permitir ejecutar iniciar_juegos.sh
chmod +x "$PROJECT_PATH/iniciar_juegos.sh"

# Refrescar Nautilus (si está instalado) para que el escritorio muestre el nuevo .desktop
if command_exists nautilus; then
    nautilus -q || true
fi

echo "Instalación completada. Ahora puedes ejecutar EBO2 desde el escritorio o el menú de aplicaciones."

