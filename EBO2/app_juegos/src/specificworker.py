#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
#    Copyright (C) 2025 by YOUR NAME HERE
#
#    This file is part of RoboComp
#
#    RoboComp is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    RoboComp is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with RoboComp.  If not, see <http://www.gnu.org/licenses/>.
#

from PySide6 import QtCore, QtUiTools
from PySide6.QtCore import QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication, QFrame, QMessageBox
from rich.console import Console
from genericworker import GenericWorker
import os
import subprocess
import sys
from pathlib import Path

ruta_src = Path(__file__).resolve().parent.parent / 'src'
print(ruta_src)
sys.path.append(str(ruta_src))

from config_ips import lanzar_gui_configuracion

sys.path.append('/opt/robocomp/lib')
console = Console(highlight=False)


# If RoboComp was compiled with Python bindings you can use InnerModel in Python
# import librobocomp_qmat
# import librobocomp_osgviewer
# import librobocomp_innermodel


class SpecificWorker(GenericWorker):
    def __init__(self, proxy_map, configData, startup_check=False):
        super(SpecificWorker, self).__init__(proxy_map, configData)
        print(f"DEBUG - Atributos actuales: {[a for a in dir(self) if '_proxy' in a]}")
        self.hide()
        self.Period = 100
        if startup_check:
            self.startup_check()
        else:
            self.timer.timeout.connect(self.compute)
            self.timer.start(self.Period)

        self.juego_seleccionado = False
        self.ultimo_estado = None
        self.ebo_listo = False
        self.gameName = "Selecciona Juego"
        self.userName = "Usuario"


    def __del__(self):
        """Destructor"""

    def setParams(self, params):
        self.ip = params["ip"]
        self.ui = self.v_principal()
        self.GestorSG_LanzarApp()
        return True


    @QtCore.Slot()
    def compute(self):
        estado_para_terapeuta = "Seleccionando Juego"
        if self.juego_seleccionado is False and self.ui.isVisible() is False:
            estado_actual = "Relanzando APP"
        elif self.juego_seleccionado is True and self.ui.isVisible() is False:
            estado_actual = "Juego en Curso"
            estado_para_terapeuta = f"Jugando a: {self.gameName}"
        else:
            estado_actual = "Juego en selección"
            estado_para_terapeuta = "Seleccionando Juego"

        # Si el estado actual es diferente al último impreso, imprimimos
        if estado_actual != self.ultimo_estado:
            if self.ultimo_estado is not None:  # No imprimir línea si es el primer estado
                print("------------------------------")
            print(estado_actual)
            self.ultimo_estado = estado_actual  # Actualizamos el último estado

            try:
                # Enviamos: 1. El juego, 2. Un string vacío (ya que no hay usuario), 3. El estado
                self.therapistpanel_proxy.updateGameStatus(self.gameName, "", estado_para_terapeuta)
            except Exception:
                # Si el panel no está abierto, ignoramos para no saturar la consola
                pass

        return True

    def startup_check(self):
        QTimer.singleShot(200, QApplication.instance().quit)

    ######## INTERFAZ GRÁFICA ################

    def v_principal (self):
        #Cargar interfaz
        loader = QtUiTools.QUiLoader()
        file = QtCore.QFile("../../igs/app_juegos.ui")
        file.open(QtCore.QFile.ReadOnly)
        ui = loader.load(file)
        file.close()

	    # Asignar las imágenes a los QLabel después de cargar la UI
        ui.label.setPixmap(QPixmap("../../igs/logos/logo_euro.png"))
        ui.label.setScaledContents(True)  # Asegúrate de que la imagen se ajuste al QLabel

        ui.label_2.setPixmap(QPixmap("../../igs/logos/robolab.png"))
        ui.label_2.setScaledContents(True)  # Ajusta la imagen a los límites del QLabel


        ui.story_button.clicked.connect(self.story_clicked)
        ui.simon_button.clicked.connect(self.simon_clicked)
        ui.pasapalabra_button.clicked.connect(self.pasapalabra_clicked)
        ui.ip_button.clicked.connect(self.configurar_ip)
        ui.therapist_button.clicked.connect(self.therapist_clicked)
        ui.encuesta_button.clicked.connect(self.encuesta_clicked)
        ui.mimica_button.clicked.connect(self.mimica_clicked)
        ui.trivial_button.clicked.connect(self.trivial_clicked)
        ui.veoveo_button.clicked.connect(self.veoveo_clicked)

        ui.ayuda.hide()
        ui.ayuda_button.clicked.connect(self.ayuda_clicked)

        ui.resultados_button.clicked.connect(self.ejecutar_scrip)

        self.verificar_ping(ui.cuadradito)

        # Asegurar que el diccionario de UIs existe
        if not hasattr(self, 'ui_numbers'):
            self.ui_numbers = {}

        self.ui_numbers[ui] = 1
        ui.installEventFilter(self)

        return ui

    def _launch_game(self, proxy_attr: str) -> None:
        if self.ebo_listo:
            proxy = getattr(self, proxy_attr)

            try:
                if hasattr(self, 'therapistpanel_proxy'):
                    # Enviamos el nombre del juego recién asignado
                    self.therapistpanel_proxy.updateGameStatus(self.gameName, "Paciente", "Iniciando...")
                    print(f"Enviado inmediato al panel: {self.gameName}")
            except Exception as e:
                print(f"Panel no disponible: {e}")

            if proxy_attr == "therapistpanel_proxy":
                # PARA EL TERAPEUTA: Solo lanzamos el panel, NO cerramos la UI
                try:
                    print("Lanzando Therapist Panel en paralelo...")
                    proxy.ice_ping()
                    proxy.StartPanel()
                except Exception as e:
                    print(f"ERROR: No se pudo conectar con el Panel: {e}")
                    QMessageBox.critical(
                        self.ui,
                        "Error de Conexión",
                        "El componente TherapistPanel no está en marcha. Por favor, inícielo primero."
                    )
            elif proxy_attr == "encuesta_proxy":
                try:
                    print("Lanzando Encuesta...")
                    proxy.ice_ping()
                    self.ui.removeEventFilter(self)
                    self.ui.hide()
                    self.ui.installEventFilter(self)

                    proxy.StartSurvey()
                except Exception as e:
                    print(f"ERROR: No se pudo conectar con el Panel: {e}")
                    QMessageBox.critical(
                        self.ui,
                        "Error de Conexión",
                        "El componente Encuesta no está en marcha. Por favor, inícielo primero."
                    )

            else:
                # PARA LOS JUEGOS: Cerramos la UI y marcamos juego en curso
                print(f"Lanzando juego: {self.gameName}")
                # Desactivamos y activamos el eventfilter antes y después de cerrar la ventana para que no se raye
                self.ui.removeEventFilter(self)
                self.ui.hide()
                self.ui.installEventFilter(self)

                self.juego_seleccionado = True
                proxy.StartGame()
        else:
            QMessageBox.warning(
                self.ui,
                "Advertencia",
                "Por favor, configura la IP de ebo."
            )

    def story_clicked(self):
        self.gameName = "Storytelling"
        self._launch_game("storytelling_proxy")

    def simon_clicked(self):
        self.gameName = "Simón Dice"
        self._launch_game("juegosimonsay_proxy")

    def pasapalabra_clicked(self):
        self.gameName = "Pasapalabra"
        self._launch_game("pasapalabra_proxy")

    def therapist_clicked (self):
        self._launch_game("therapistpanel_proxy")

    def encuesta_clicked(self):
        self._launch_game("encuesta_proxy")

    def mimica_clicked(self):
        self.gameName = "Mímica"
        self._launch_game("juegomirror_proxy")

    def trivial_clicked(self):
        self.gameName = "Trivial"
        self._launch_game("juegotrivial_proxy")

    def veoveo_clicked(self):
        self.gameName = "Veo Veo"
        self._launch_game("juegoveoveo_proxy")

    def ayuda_clicked(self):
        if self.ui.ayuda.isVisible():  # Verifica si está visible
            self.ui.ayuda.hide()  # Si está visible, ocultarlo
        else:
            self.ui.ayuda.show()

    def ejecutar_scrip(self):
        try:
            subprocess.run(["python3", "../../generar_resultados.py"], check=True)
            QMessageBox.information(self, "Completado",
                                    "La generación de resultados se ha completado con éxito.")
        except subprocess.CalledProcessError as e:
            QMessageBox.critical(self, "Error", f"Hubo un error al generar los resultados:\n{e}")

    def configurar_ip(self):
        ruta_actual = os.getcwd()
        ruta_base = os.path.dirname(ruta_actual)

        # Intentamos obtener el resultado de la GUI de configuración
        resultado = lanzar_gui_configuracion(ruta_base)

        if resultado.get("ok"):
            try:
                # Construimos la ruta absoluta al script
                script_path = os.path.abspath(os.path.join(ruta_base, "iniciar_juegos.sh"))
                print(f"Reiniciando sistema desde: {script_path}")

                # Lanzamos la terminal usando 'nohup'.
                # Esto desvincula el proceso del terminal actual de forma segura.
                subprocess.Popen(
                    ["nohup", "gnome-terminal", "--", "bash", script_path],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True
                )

                # Damos un margen mínimo para que el sistema procese el Popen
                self.time.sleep(0.5)

                # Cierre total
                print("Cerrando instancia antigua...")
                os._exit(0)

            except Exception as e:
                # Ahora el except está correctamente dentro del bloque try
                print(f"Error al relanzar el script: {e}")
                if hasattr(self, 'ui'):
                    QMessageBox.critical(self.ui, "Error", f"No se pudo relanzar el script:\n{e}")
        else:
            print("Configuración cancelada o sin cambios en la IP.")


    def verificar_ping(self, indicador: QFrame):
        print("COMPROBANDO PING")
        try:
            resultado = subprocess.run(
                ["ping", "-c", "1", "-W", "1", self.ip],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=2
            )
            if resultado.returncode == 0:
                self._set_indicator_color(indicador, "green")
                self.ebo_listo = True
            else:
                self._set_indicator_color(indicador, "red")
                self.ebo_listo = False
        except subprocess.TimeoutExpired:
            # Conservador: tratar como fallo sin imprimir mensajes adicionales
            self._set_indicator_color(indicador, "red")
            self.ebo_listo = False
        except Exception:
            self._set_indicator_color(indicador, "red")
            self.ebo_listo = False

    def _set_indicator_color(self, indicador: QFrame, color: str):
        indicador.setStyleSheet(f"background-color: {color}; border: 1px solid black;")

        ####################################################################################################################################

    def eventFilter(self, obj, event):
        """ Captura eventos de la UI """
        ui_number = self.ui_numbers.get(obj, None)

        if ui_number is not None and event.type() == QtCore.QEvent.Close:
            target_ui = self.ui if ui_number == 1 else getattr(self, f'ui{ui_number}', None)

            if obj == target_ui:
                respuesta = QMessageBox.question(
                    target_ui, "Cerrar", "¿Estás seguro de que quieres cerrar los juegos?",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                )
                if respuesta == QMessageBox.Yes:
                    print(f"Ventana {ui_number} cerrada por el usuario.")
                    # Ejecutar reinicio con manejo de errores conservador
                    try:
                        subprocess.run(["python3", "../reiniciar.py"], check=False)
                    except FileNotFoundError:
                        print("[ERROR] No se encontró el script ../reiniciar.py")
                    except Exception as e:
                        print(f"[ERROR] Falló la ejecución de reiniciar.py: {e}")
                    return False  # Permitir el cierre
                else:
                    print(f"Cierre de la ventana {ui_number} cancelado.")
                    event.ignore()  # Bloquear el cierre
                    return True  # Detener la propagación del evento

        return False  # Propaga otros eventos normalmente

    ####################################################################################################################################

    # =============== Methods for Component Implements ==================
    # ===================================================================

    #
    # IMPLEMENTATION of LanzarApp method from GestorSG interface
    #
    def GestorSG_LanzarApp(self):
        self.juego_seleccionado = False
        self.ui.installEventFilter(self)
        self.centrar_ventana(self.ui)
        self.ui.show()
        QApplication.processEvents()
        pass


    def centrar_ventana(self, ventana):
        # Obtener la geometría de la pantalla
        pantalla = QApplication.primaryScreen().availableGeometry()

        # Obtener el tamaño de la ventana
        tamano_ventana = ventana.size()

        # Calcular las coordenadas para centrar la ventana
        x = (pantalla.width() - tamano_ventana.width()) // 2
        y = (pantalla.height() - tamano_ventana.height()) // 2

        # Mover la ventana a la posición calculada
        ventana.move(x, y)
    # ===================================================================
    # ===================================================================


    ######################
    # From the RoboCompEncuesta you can call this methods:
    # RoboCompEncuesta.void self.encuesta_proxy.StartSurvey()

    ######################
    # From the RoboCompJuegoMirror you can call this methods:
    # RoboCompJuegoMirror.void self.juegomirror_proxy.StartGame()

    ######################
    # From the RoboCompJuegoSimonSay you can call this methods:
    # RoboCompJuegoSimonSay.void self.juegosimonsay_proxy.StartGame()

    ######################
    # From the RoboCompJuegoTrivial you can call this methods:
    # RoboCompJuegoTrivial.void self.juegotrivial_proxy.StartGame()

    ######################
    # From the RoboCompJuegoVeoVeo you can call this methods:
    # RoboCompJuegoVeoVeo.void self.juegoveoveo_proxy.StartGame()

    ######################
    # From the RoboCompPasapalabra you can call this methods:
    # RoboCompPasapalabra.void self.pasapalabra_proxy.StartGame()

    ######################
    # From the RoboCompStoryTelling you can call this methods:
    # RoboCompStoryTelling.void self.storytelling_proxy.StartGame()

    ######################
    # From the RoboCompTherapistPanel you can call this methods:
    # RoboCompTherapistPanel.void self.therapistpanel_proxy.StartPanel()
    # RoboCompTherapistPanel.void self.therapistpanel_proxy.updateGameStatus(str gameName, str userName, str current)


