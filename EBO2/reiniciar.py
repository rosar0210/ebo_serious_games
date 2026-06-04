import os
import subprocess

# Lista de nombres de procesos a rastrear
nombres_procesos = ['app_juegos', 'ebo_gpt', 'pasapalabra', 'simonSay', 'storytelling', 'ebo_app','encuesta', 'therapistPanel', 'mirror' ]

def matar_procesos():
    # Usar el comando ps para listar los procesos en ejecución
    procesos = subprocess.check_output(['ps', 'aux']).decode('utf-8').splitlines()

    # Iterar sobre cada proceso
    for proceso in procesos:
        for nombre in nombres_procesos:
            if nombre in proceso:
                # Obtener el PID (el segundo campo en la salida de ps)
                pid = proceso.split()[1]
                try:
                    # Matar el proceso usando el PID
                    print(f"Matando el proceso: {proceso} (PID: {pid})")
                    os.kill(int(pid), 9)  # 9 es la señal SIGKILL
                except ProcessLookupError:
                    pass  # El proceso ya no existe
                except PermissionError:
                    print(f"No tienes permisos para matar el proceso con PID: {pid}")

# Ejecutar la función
matar_procesos()
print("TODO REINICIADO, INICIANDO PROGRAMA")
