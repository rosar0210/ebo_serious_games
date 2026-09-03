# ebo_serious_games

## Instalación y configuración de EBO2

Todo el proceso de preparación de la aplicación está automatizado mediante el script `install.sh`. Este script comprueba tu versión de Python, crea un entorno virtual aislado, instala las dependencias necesarias y configura los accesos directos del sistema.

---

### 1) Configuración previa (dependencias del sistema)

Antes de ejecutar el script de instalación, asegúrate de tener instaladas las librerías base del sistema. 
Estas librerías permiten que la interfaz gráfica (PySide6/Qt y Tkinter) y las herramientas de visión artificial funcionen correctamente.

En **Ubuntu / Debian**, instálalas ejecutando:

```sh
sudo apt-get update
sudo apt-get install -y python3.11-venv python3-tk libxcb-xinerama0 libxcb-cursor0 \
     libxkbcommon-x11-0 libxcb-randr0 libxcb-icccm4 libxcb-image0 \
     libxcb-keysyms1 libxcb-render-util0 libglu1-mesa
```
**Nota:** En algunas distribuciones el paquete puede llamarse `python3-venv` (sin la versión). Si `python3.11-venv` no está disponible, prueba con:
> ```sh
> sudo apt-get install -y python3-venv
> ```

---

### 2) Clonar el repositorio

Clona el repo y entra en la carpeta `EBO2`:


  ```sh
  git clone https://github.com/rosar0210/ebo_serious_games.git
  cd ebo_serious_games/EBO2
  ```

---

### 3) Instalación

Ejecuta el script de instalación:
```sh
./install.sh
```
Este script, de forma automática:
- Crea el entorno virtual `games_venv` si no existe.
- Instala todas las dependencias desde `requirements.txt`.
- Configura el lanzador `.desktop` en el menú de aplicaciones y el escritorio.

> Si el script no tiene permisos de ejecución, concédeselos con:
> ```sh
> chmod +x install.sh
> ```

---

### 4) Ejecutar la aplicación

- **Desde el escritorio**: haz doble click en el icono de **EBO2** (la primera vez puede que tengas que hacer clic derecho → *Allow launching* o *Permitir lanzar*).
- **Desde el menú de aplicaciones**: busca **EBO2** y ejecútalo directamente.

---

## Configuración de `ebo_gpt`

Para que `ebo_gpt` funcione correctamente, es necesario crear un archivo `.env` y agregar tu clave de OpenAI.

### Pasos para crear el archivo `.env`
1. Navega a la carpeta `ebo_gpt` en tu terminal (elige la versión que corresponda):
   ```sh
   cd EBO1/ebo_gpt
   ```
   o
   ```sh
   cd EBO2/ebo_gpt
   ```
2. Crea el archivo `.env`:
   ```sh
   touch .env
   ```
3. Abre el archivo `.env` con tu editor de texto preferido y agrega la siguiente línea:
   ```env
   OPENAI_API_KEY="tu_clave_aqui"
   ```
4. Guarda los cambios y cierra el archivo.

Ahora `ebo_gpt` estará configurado correctamente para utilizar la API de OpenAI.
