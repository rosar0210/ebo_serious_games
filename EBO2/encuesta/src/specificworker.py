#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
#    Copyright (C) 2026 by YOUR NAME HERE
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
from time import strftime

from PySide6.QtCore import QTimer, Slot, QFile
from PySide6.QtWidgets import QApplication, QInputDialog
from rich.console import Console
from genericworker import *
import interfaces as ifaces
import sys
import csv
import os
from datetime import datetime
from PySide6 import QtUiTools
from PySide6.QtGui import QPixmap, QIcon



sys.path.append('/opt/robocomp/lib')
console = Console(highlight=False)


# Rutas de UIs y logos
UI_MENU     = "../../igs/encuesta.ui"
LOGO_1      = "../../igs/logos/logo_euro.png"
LOGO_2      = "../../igs/logos/robolab.png"

cara1     = "../../igs/caras/muyinsatisfecho.png"
cara2     = "../../igs/caras/insatisfecho.png"
cara3     = "../../igs/caras/algoinsatisfecho.png"
cara4     = "../../igs/caras/neutro.png"
cara5     = "../../igs/caras/algosatisfecho.png"
cara6     = "../../igs/caras/satisfecho.png"
cara7     = "../../igs/caras/muysatisfecho.png"

class SpecificWorker(GenericWorker):

    update_ui_signal = QtCore.Signal()

    def __init__(self, proxy_map, configData, startup_check=False):
        super(SpecificWorker, self).__init__(proxy_map, configData)
        self.Period = configData["Period"]["Compute"]
        if startup_check:
            self.startup_check()
        else:
            self.timer.timeout.connect(self.compute)
            self.timer.start(self.Period)

        # Si SpecificWorker es un Widget, lo ocultamos para que solo se vea tu UI cargada.
        if isinstance(self, QWidget):
            self.hide()

        self.update_ui_signal.connect(self.handle_update_ui)

        self.ui = self.encuesta_ui()

        self.respuesta = 0
        self.usuario = ""

        ruta_script = os.path.dirname(os.path.abspath(__file__))

        self.log_dir = os.path.join(ruta_script, "..", "EncuestasSatisfaccion")

        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)

        # QtCore.QTimer.singleShot(500, self.update_ui_signal.emit)


    def __del__(self):
        """Destructor"""


    @QtCore.Slot()
    def compute(self):
        # print('SpecificWorker.compute...')
        # computeCODE
        # try:
        #   self.differentialrobot_proxy.setSpeedBase(100, 0)
        # except Ice.Exception as e:
        #   traceback.print_exc()
        #   print(e)

        return True

    def startup_check(self):
        QTimer.singleShot(200, QApplication.instance().quit)




    # =============== Methods for Component Implements ==================
    # ===================================================================
    #
    # IMPLEMENTATION of StartSurvey method from Encuesta interface
    #
    def Encuesta_StartSurvey(self):
        """Implementación del Panel para el GestorSG"""
        print("Recibida petición de apertura...")
        self.update_ui_signal.emit()
        pass

    def recuperar_estado_tras_reinicio(self):
        if os.path.exists(self.backup_path):
            try:
                with open(self.backup_path, 'r') as f:
                    data = json.load(f)
                    self.counts = data["counts"]
                    self.registrosesion = data["registros"]
                print("--- SESIÓN RECUPERADA TRAS REINICIO DE IP ---")
            except:
                pass

    def eventFilter (self, obj, event):
        """ Captura el cierre de la ventana principal """
        if event.type() == QtCore.QEvent.Close:
            if obj == self.ui:
                self.finalizar_encuesta(self.respuesta)

                event.ignore()
                self.finalizar_encuesta(0)
            return True

        return super().eventFilter(obj, event)

    ###########################LÓGICA DE LOS BOTONES###################################

    def muyinsatisfecho_clicked(self):
        self.respuesta = 1
        self.finalizar_encuesta(self.respuesta)

    def insatisfecho_clicked(self):
        self.respuesta = 2
        self.finalizar_encuesta(self.respuesta)


    def algoinsatisfecho_clicked(self):
        self.respuesta = 3
        self.finalizar_encuesta(self.respuesta)


    def neutro_clicked(self):
        self.respuesta = 4
        self.finalizar_encuesta(self.respuesta)


    def algosatisfecho_clicked(self):
        self.respuesta = 5
        self.finalizar_encuesta(self.respuesta)


    def satisfecho_clicked(self):
        self.respuesta = 6
        self.finalizar_encuesta(self.respuesta)


    def muysatisfecho_clicked(self):
        self.respuesta = 7
        self.finalizar_encuesta(self.respuesta)


    def finalizar_encuesta(self, puntuacion):
        if puntuacion != 0:
            self.guardar_csv(puntuacion)
        self.ui.removeEventFilter(self)
        self.ui.hide()
        self.ui.installEventFilter(self)

        try:
            print("Volviendo al menú principal")
            if hasattr(self, 'gestorsg_proxy'):
                self.gestorsg_proxy.LanzarApp()
            else:
                print("Error: No se encuentra el proxy gestorsg_proxy")
        except Exception as e:
            print(f"No se pudo volver al menú principal: {e}")

    def guardar_csv(self, puntuacion):
        fecha = datetime.now().strftime("%d%m%Y")
        nombre_archivo = os.path.join(self.log_dir,f"encuesta_{fecha}.csv")

        with open(nombre_archivo, mode='a', newline='', encoding='utf-8') as archivo:
            escritor = csv.writer(archivo)
            # Guardamos la fecha/hora, el usuario y la puntuación
            escritor.writerow([fecha, self.usuario, puntuacion])

####################################################################################################################################
    def encuesta_ui(self):
        ui = self.load_ui_generic(
            UI_MENU, ui_number=1,
            logo_paths={"label": LOGO_1, "label_3": LOGO_2},
            iconos_botones={
            "muyinsatisfecho": cara1,
            "insatisfecho": cara2,
            "algoinsatisfecho": cara3,
            "neutro": cara4,
            "algosatisfecho": cara5,
            "satisfecho": cara6,
            "muysatisfecho": cara7
        },
            botones={
                "muyinsatisfecho": self.muyinsatisfecho_clicked,
                "insatisfecho": self.insatisfecho_clicked,
                "algoinsatisfecho": self.algoinsatisfecho_clicked,
                "neutro": self.neutro_clicked,
                "algosatisfecho": self.algosatisfecho_clicked,
                "satisfecho": self.satisfecho_clicked,
                "muysatisfecho": self.muysatisfecho_clicked
            },
        )

        return ui

    def load_ui_generic(self, ui_path, ui_number, *, logo_paths=None, botones=None,
                        after_load=None, iconos_botones=None):
        loader = QtUiTools.QUiLoader()
        file = QFile(ui_path)
        file.open(QFile.ReadOnly)
        ui = loader.load(file)
        file.close()

        # Logos
        if logo_paths:
            for label_name, path in logo_paths.items():
                label = getattr(ui, label_name, None)
                if label:
                    label.setPixmap(QPixmap(path))
                    label.setScaledContents(True)

        # Botones
        if iconos_botones:
            for btn_name, path in iconos_botones.items():
                btn = getattr(ui, btn_name, None)
                if btn:
                    icon = QIcon(path)
                    btn.setIcon(icon)
                    btn.setIconSize(QtCore.QSize(200, 200))

        if botones:
            for btn_name, func in botones.items():
                btn = getattr(ui, btn_name, None)
                if btn:
                    btn.clicked.connect(func)
                    print(f"[OK] Botón '{btn_name}' conectado correctamente.")
                else:
                    print(f"[ERROR] No encuentro un botón llamado '{btn_name}' en el archivo .ui")
                    print(f"       -> Revisa el 'objectName' en Qt Designer.")

        # Hook opcional post-carga (por si quieres hacer algo extra)
        if callable(after_load):
            after_load(ui)

        # Registrar para eventFilter
        if not hasattr(self, 'ui_numbers'):
            self.ui_numbers = {}
        self.ui_numbers[ui] = ui_number
        ui.installEventFilter(self)
        return ui


    def cerrar_ui(self, numero):
        ui_nombre = "ui" if numero == 1 else f"ui{numero}"
        ui_obj = getattr(self, ui_nombre, None)
        if ui_obj:
            ui_obj.removeEventFilter(self)  # Desactiva el event filter
            ui_obj.hide()  # Oculta la ventana
            ui_obj.installEventFilter(self)  # Reactiva el event filter
        else:
            print(f"Error: {ui_nombre} no existe en la instancia.")

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

    @Slot()
    def handle_update_ui(self):
        """ Esta función se encarga de hacer visible la ventana """
        dialogo = QInputDialog(None)
        dialogo.setWindowTitle("Paciente")
        dialogo.setLabelText("Introduce el nombre del paciente:")
        self.centrar_ventana(dialogo)

        ok = dialogo.exec_()
        nombre = dialogo.textValue()

        if ok and nombre.strip():
            self.usuario = nombre.strip()
        else:
            self.usuario = ""
        if self.ui:
            self.ui.removeEventFilter(self)
            self.ui.installEventFilter(self)
            self.centrar_ventana(self.ui)
            self.ui.show()
            self.ui.raise_()
            self.ui.activateWindow()  # La pone al frente de todas las carpetas
            print("LOG: Interfaz mostrada con éxito.")

    def startup_check(self):
        QTimer.singleShot(200, QApplication.instance().quit)


    # ===================================================================
    # ===================================================================


    ######################
    # From the RoboCompGestorSG you can call this methods:
    # RoboCompGestorSG.void self.gestorsg_proxy.LanzarApp()


