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

from PySide6.QtCore import QElapsedTimer, Slot, QTimer, QFile, QIODevice, QTime
from PySide6.QtWidgets import QApplication, QWidget, QLabel, QMessageBox
from rich.console import Console
from genericworker import *
import interfaces as ifaces
import csv
from datetime import datetime
import os
import json
from PySide6 import QtUiTools


# Rutas de UIs y logos
UI_MENU     = "../../igs/therapistPanel.ui"
LOGO_1      = "../../igs/logos/logo_euro.png"
LOGO_2      = "../../igs/logos/robolab.png"

sys.path.append('/opt/robocomp/lib')
console = Console(highlight=False)


class SpecificWorker(GenericWorker):

    update_ui_signal = QtCore.Signal()

    update_game_data_signal = QtCore.Signal(str, str, str)

    def __init__(self, proxy_map, configData, startup_check=False):
        super(SpecificWorker, self).__init__(proxy_map, configData)
        self.Period = configData["Period"]["Compute"]
        if startup_check:
            self.startup_check()
        else:
            self.timer.timeout.connect(self.compute)
            self.timer.start(self.Period)
            self.timer_compute = QTimer()

            # QtCore.QTimer.singleShot(100, lambda: self.update_ui_signal.emit())

        # Si SpecificWorker es un Widget, lo ocultamos para que solo se vea tu UI cargada.
        if isinstance(self, QWidget):
            self.hide()

        self.update_ui_signal.connect(self.handle_update_ui)

        self.ui = self.therapistPanel_ui()

        self.tiempo_pasado = QTime(0,0)
        self.sesion_actual = None
        self.registrosesion = []
        self.juego = "Sin juego"
        self.usuario = "Sin usuario"

        self.estado_respuesta_anterior = None
        self.inicio_estado_respuesta = None

        self.counts = {
            "frustracion_button": 0,
            "comprension_button": 0,
            "afecto_button": 0
        }

        self.juegos_sesion = []

        ruta_script = os.path.dirname(os.path.abspath(__file__))

        self.log_dir = os.path.join(ruta_script, "..", "therapy_control")
        self.backup_path = os.path.join(self.log_dir, "backup_sesion.json")

        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)

        self.update_game_data_signal.connect(self.actualizar_interfaz_seguro)

    # =============== Methods for Component Implements ==================
    # ===================================================================

    #
    # IMPLEMENTATION of StartPanel method from TherapistPanel interface
    #
    def TherapistPanel_StartPanel(self):
        """Implementación del Panel para el GestorSG"""
        print("Recibida petición de apertura...")
        self.update_ui_signal.emit()

        pass

    def TherapistPanel_updateGameStatus (self, gameName, userName, current):
        print(f"Activo el juego: {gameName}, Usuario: {userName}, Estado: {current}")
        self.juego = gameName
        self.usuario = userName

        self.update_game_data_signal.emit(str(gameName), str(userName), str(current))

    @QtCore.Slot(str, str, str)
    def actualizar_interfaz_seguro(self, gameName, userName, current):
        # Esto corre en el hilo PRINCIPAL (Seguro para Qt)
        if hasattr(self, 'ui') and hasattr(self.ui, 'juego_show'):
            self.ui.juego_show.setPlainText(gameName)
            #Forzar refresco visual

        if self.sesion_actual is not None:
            marca_tiempo = self.tiempo_pasado.toString("mm:ss")
            evento_juego = f"{gameName} ({marca_tiempo})"
            if not self.juegos_sesion or not self.juegos_sesion[-1].startswith(gameName):
                self.juegos_sesion.append(evento_juego)

        self.ui.repaint()

    def comprobar_sesion_activa (self):
        """Verifica si hay una sesión iniciada. Si no, avisa al terapeuta"""
        if self.sesion_actual is None:
            QMessageBox.warning(
                self.ui,
                "Sesión no iniciada",
                "Por favor, pulsa el botón de 'Comenzar' para registrar los datos."
            )
            return False
        return True


    def  actualizar_cronometro(self):
        self.tiempo_pasado = self.tiempo_pasado.addSecs(1)
        texto_hora = self.tiempo_pasado.toString("mm:ss")

        self.playtime.display(texto_hora)
        self.playtime.repaint()

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
                event.ignore()
            self.finalizar_y_guardar()
            return True

        return super().eventFilter(obj, event)

    def solicitar_residencia_y_guardar(self):
        #Pedir el nombre del centro
        nombre, ok = QtWidgets.QInputDialog.getText(
            self.ui, "Finalizar sesión",
            "Introduzca el nombre del Centro:",
            text=""
        )

        #Si el usuario pulsa ok
        if ok:
            #Si dejó el nombre vacío pero dio a OK
            self.residencianame = nombre if nombre.strip() else "Centro_No_Especificado"

            #Guardamos en el CSV
            self.guardarSesionFinal()

            # Cerramos la aplicación
            self.registrosesion = []  #Limpiamos la lista para la próxima vez
            self.ui.hide()

            try:
                if self.gestorsg_proxy:
                    self.gestorsg_proxy.LanzarApp()
            except Exception as e:
                print(f"Error al volver al Gestor: {e}")

        else:
            #Si pulsa Cancel
            console.print("[yellow]⚠ Cierre cancelado por el usuario. No se ha creado el archivo CSV.[/yellow]")

            try:
                if self.gestorsg_proxy:
                    self.gestorsg_proxy.LanzarApp()
            except Exception as e:
                print(f"Error al volver al Gestor: {e}")

            self.registrosesion = []
            self.sesion_actual = None
            self.ui.hide()


    def guardarSesionFinal(self):
        """ Guarda un CSV final con todos los pacientes registrados durante la jornada """
        # Verificamos si hay algún clic suelto que no se haya registrado por paciente
        clics_pendientes = sum(self.counts.values())
        if clics_pendientes > 0:
             console.print("[yellow]⚠ Aviso: Había clics sin asignar a ningún paciente al cerrar.[/yellow]")

        fecha_str = datetime.now().strftime("%d%m%Y_%H%M")
        nombre_fichero = f"{self.residencianame.replace(' ', '_')}_{fecha_str}.csv"
        path_final = os.path.join(self.log_dir, nombre_fichero)

        # Headers actualizados con 'Hora'
        headers = ["Paciente", "Hora", "Juego", "Atención", "Pausa larga", "Distracción",
                   "Respuesta Autónoma", "Necesidad Ayuda", "Frustración", "Comprensión", "Afecto"]
        try:
            # 1. Intentamos escribir el archivo CSV
            with open(path_final, mode='w', newline='', encoding='utf-8') as f:
                f.write(f"# Residencia: {self.residencianame}\n")
                f.write(f"# Fecha: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}\n")

                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                for fila in self.registrosesion:
                    writer.writerow(fila)

            console.print(f"[bold green]✅ Archivo final de residencia guardado: {path_final}[/bold green]")

            # Si el guardado fue bien, borramos el backup para empezar limpios la próxima vez
            if os.path.exists(self.backup_path):
                os.remove(self.backup_path)
                console.print("[blue]🧹 Backup temporal eliminado con éxito.[/blue]")

        except Exception as e:
            console.print(f"[bold red]❌ Error crítico al guardar log final: {e}[/bold red]")

################################################# LOGICA DE BOTONES #################################################################################################
    def hacer_backup_inmediato(self):
        """Guarda el estado actual por si el script .sh cierra la terminal"""
        estado = {
            "counts": self.counts,
            "registros": self.registrosesion
        }
        with open(self.backup_path, 'w') as f:
            json.dump(estado, f)

    def gestion_groupatencion (self, boton_click):
        #Comprobación si se ha iniciado la sesión antes de pulsar botones
        if not self.comprobar_sesion_activa():
            return

        self.momentoActual = QTime.currentTime()
        self.tiempo_transcurrido = self.inicio_estado_actual.secsTo(self.momentoActual)

        columna = f"{self.estado_anterior}"
        if columna in self.sesion_actual:
            self.sesion_actual[columna] += self.tiempo_transcurrido

        self.estado_anterior = boton_click.text()
        self.inicio_estado_actual = self.momentoActual

        print(f"Cambiando a {self.estado_anterior}...")

    def gestion_grouprespuesta (self, boton_click):
        # Comprobación si se ha iniciado la sesión antes de pulsar botones
        if not self.comprobar_sesion_activa():
            return

        self.momentoActual = QTime.currentTime()
        texto = boton_click.text()

        if self.estado_respuesta_anterior is not None:
            tiempo_transcurrido = self.inicio_estado_respuesta.secsTo(self.momentoActual)
            # Mapeamos el nombre del botón a la clave del diccionario
            clave = f"{self.estado_respuesta_anterior}"
            if clave in self.sesion_actual:
                self.sesion_actual[clave] += tiempo_transcurrido

        self.estado_respuesta_anterior = texto
        self.inicio_estado_respuesta = self.momentoActual

        print(f"Estado de respuesta: {self.estado_respuesta_anterior}")

    def frustracion_clicked(self):
        # Comprobación si se ha iniciado la sesión antes de pulsar botones
        if not self.comprobar_sesion_activa():
            return

        self.counts["frustracion_button"] += 1
        self.momento = self.tiempo_pasado.toString("mm:ss")
        self.cont_frustracion.display(self.counts["frustracion_button"])
        # Guardamos el momento y el número de click
        self.sesion_actual["Frustración"].append(f"{self.momento} (v.{self.counts['frustracion_button']})")

    def comprension_clicked(self):
        # Comprobación si se ha iniciado la sesión antes de pulsar botones
        if not self.comprobar_sesion_activa():
            return

        self.counts["comprension_button"] += 1
        self.momento = self.tiempo_pasado.toString("mm:ss")
        self.cont_comprension.display(self.counts["comprension_button"])

        # Guardamos el momento y el número de click
        self.sesion_actual["Comprensión"].append(f"{self.momento} (v.{self.counts['comprension_button']})")

    def afecto_clicked(self):
        # Comprobación si se ha iniciado la sesión antes de pulsar botones
        if not self.comprobar_sesion_activa():
            return

        self.counts["afecto_button"] += 1
        self.momento = self.tiempo_pasado.toString("mm:ss")
        self.cont_afecto.display(self.counts["afecto_button"])

        # Guardamos el momento y el número de click
        self.sesion_actual["Afecto"].append(f"{self.momento} (v.{self.counts['afecto_button']})")

    def comenzar_clicked(self):
        if self.sesion_actual is not None:
            return  # Evita duplicar si ya está corriendo

        self.juegos_sesion = []
        self.reg_juego = self.ui.juego_show.toPlainText().strip()

        if self.reg_juego:
            self.juegos_sesion.append(f"{self.reg_juego} (00:00)")

        self.inicio_estado_actual = QTime.currentTime()
        self.estado_anterior = "Atención"

        self.inicio_estado_respuesta = QTime.currentTime()
        self.estado_respuesta_anterior = "Respuesta Autónoma"

        if hasattr(self.ui, "juego_show"):
            self.registro_juego = self.ui.juego_show.toPlainText().strip()
        else:
            self.registro_juego = self.juego

        self.sesion_actual = {
            "Paciente": "Nombre",
            "Hora": datetime.now().strftime("%H:%M:%S"),
            "Juego": self.registro_juego,
            "Atención": 0,
            "Pausa larga": 0,
            "Distracción": 0,
            "Respuesta Autónoma": 0,
            "Necesidad Ayuda": 0,
            "Frustración": [],
            "Comprensión": [],
            "Afecto": []
        }

        # Arranca el cronómetro
        self.timer.start(1000)
        print(f"Sesión iniciada. Juego: {self.registro_juego}")

    def parar_clicked(self):
        if not self.comprobar_sesion_activa():
            return

        self.timer.stop()
        self.momentoActual = QTime.currentTime()

        # --- Sumar último tramo de Atención ---
        duracion_atencion = self.inicio_estado_actual.secsTo(self.momentoActual)
        clave_at = self.estado_anterior
        if clave_at in self.sesion_actual:
            self.sesion_actual[clave_at] += duracion_atencion

        # --- Sumar último tramo de Respuesta ---
        if self.estado_respuesta_anterior is not None:
            duracion_resp = self.inicio_estado_respuesta.secsTo(self.momentoActual)
            clave_resp = self.estado_respuesta_anterior
            if clave_resp in self.sesion_actual:
                self.sesion_actual[clave_resp] += duracion_resp

        self.sesion_actual["Juego"] = " ➔ ".join(self.juegos_sesion)

        #Pedir el nombre del paciente
        nombre, ok = QtWidgets.QInputDialog.getText(
            self.ui, "Sesión Finalizada",
            "Introduce el nombre del paciente para guardar el registro:",
            text="Paciente"
        )

        if ok and nombre:
            self.sesion_actual["Paciente"] = nombre
        else:
            self.sesion_actual["Paciente"] = "Usuario - " + datetime.now().strftime("%H%M")

        #Formatear datos para CSV
        fila_csv = {}
        for c, v in self.sesion_actual.items():
            if isinstance(v, int) and c not in ["Paciente", "Hora", "Juego"]:
                minutos = v // 60
                segundos = v % 60
                fila_csv[c] = f"{minutos:02d}:{segundos:02d}"
            elif isinstance(v, list):
                fila_csv[c] = ", ".join(v)
            else:
                fila_csv[c] = v

        self.registrosesion.append(fila_csv)

        # Añadimos esta sesión a la lista global
        if not hasattr(self, 'registrosesion'):
            self.registrosesion = []  #Por si no estaba inicializada

        self.hacer_backup_inmediato() #Por si se cierra sin guardar

        # Resetear contador
        if hasattr(self, 'counts'):
            for key in self.counts:
                self.counts[key] = 0

        # Reseteamos la pantalla para el siguiente paciente/juego
        self.tiempo_pasado = QTime(0, 0)
        self.playtime.display("00:00")
        self.cont_frustracion.display(0)
        self.cont_comprension.display(0)
        self.cont_afecto.display(0)
        self.juegos_sesion = []
        self.ui.juego_show.setPlainText("Sin juego")

        console.print(f"[bold blue]👤 Sesión registrada para: {nombre}[/bold blue]")
        QMessageBox.information(self.ui, "Completado", f"Datos de {nombre} guardados.\nContadores reiniciados.")

        self.sesion_actual = None  #Cerramos sesión

    def load_ui_generic(self, ui_path, ui_number, *, logo_paths=None, botones=None,
                        ayuda_button=None, back_button=None, after_load=None):
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
        if botones:
            for btn_name, func in botones.items():
                btn = getattr(ui, btn_name, None)
                if btn:
                    btn.clicked.connect(func)
                    print(f"[OK] Botón '{btn_name}' conectado correctamente.")
                else:
                    print(f"[ERROR] No encuentro un botón llamado '{btn_name}' en el archivo .ui")
                    print(f"       -> Revisa el 'objectName' en Qt Designer.")

        #Ayuda
        if ayuda_button and hasattr(ui, ayuda_button):
            getattr(ui, ayuda_button).clicked.connect(lambda: self.toggle_ayuda(ui))
            if hasattr(ui, "ayuda"):
                ui.ayuda.hide()

        # Back
        if back_button and hasattr(ui, back_button):
            getattr(ui, back_button).clicked.connect(lambda: self.back_clicked_ui(ui_number))

        # Hook opcional post-carga (por si quieres hacer algo extra)
        if callable(after_load):
            after_load(ui)

        # Registrar para eventFilter
        if not hasattr(self, 'ui_numbers'):
            self.ui_numbers = {}
        self.ui_numbers[ui] = ui_number
        ui.installEventFilter(self)
        return ui

    def finalizar_y_guardar (self):
        respuesta = QMessageBox.question(
            self.ui, "Cerrar", "¿Estás seguro de que quieres finalizar la sesión general?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )

        if respuesta == QMessageBox.Yes:
            # Llamamos a la función que pide el centro y guarda
            self.solicitar_residencia_y_guardar()
        else:

            pass

    @Slot()
    def toggle_ayuda(self, ui):
        if hasattr(ui, "ayuda"):
            ui.ayuda.setVisible(not ui.ayuda.isVisible())

    @Slot()
    def back_clicked_ui(self, ui_number):
        self.finalizar_y_guardar()

    def __del__(self):
        """Destructor"""

    def therapistPanel_ui(self):
        ui = self.load_ui_generic(
            UI_MENU, ui_number=1,
            logo_paths={"label": LOGO_1, "label_3": LOGO_2},
            botones={
                "frustracion_button": self.frustracion_clicked,
                "comprension_button": self.comprension_clicked,
                "afecto_button": self.afecto_clicked,
                "play_button": self.comenzar_clicked,
                "stop_button": self.parar_clicked,
            },
            ayuda_button="ayuda_button",
            back_button="back_button",
            after_load=lambda u: (hasattr(u, "ayuda") and u.ayuda.hide())
        )
        # --- CONFIGURACIÓN DE LOS TEXTOS ---
        self.juego_seleccionado = ui.juego_show

        # ---CONFIGURACIÓN GRUPO DE BOTONES---
        self.grupo_atencion = ui.atencion_group
        self.grupo_atencion.buttonClicked.connect(self.gestion_groupatencion)

        self.grupo_respuesta =ui.respuesta_group
        self.grupo_respuesta.buttonClicked.connect(self.gestion_grouprespuesta)

        # --- CONFIGURACIÓN DEL CRONÓMETRO ---
        self.playtime = ui.playtime
        self.tiempo_pasado = QTime(0,0)
        self.playtime.display("00:00")

        self.cont_frustracion = ui.cont_frustracion
        self.cont_comprension = ui.cont_comprension
        self.cont_afecto = ui.cont_afecto


        self.timer = QTimer()
        self.timer.timeout.connect(self.actualizar_cronometro)

        return ui



    ####################################################################################################################################

    def cerrar_ui(self, numero):
        ui_nombre = "ui" if numero == 1 else f"ui{numero}"
        ui_obj = getattr(self, ui_nombre, None)
        if ui_obj:
            ui_obj.removeEventFilter(self)  # Desactiva el event filter
            ui_obj.hide()  # Cierra la ventana
            ui_obj.installEventFilter(self)  # Reactiva el event filter
        else:
            print(f"Error: {ui_nombre} no existe en la instancia.")


    @QtCore.Slot()
    def compute(self):
        # Si por algún motivo la interfaz se ocultara, esto la mantiene viva
        # pero para no saturar el sistema, solo verificamos si es visible
        # if self.ui and not self.ui.isVisible():
        #     self.ui.show()
        # input("pulsa enter para probar ventana")
        # self.TherapistPanel_StartPanel()
        return True
    @Slot()
    def handle_update_ui(self):
        """ Esta función se encarga de hacer visible la ventana """
        if self.ui:
            self.ui.show()
            self.ui.raise_()
            self.ui.activateWindow() # La pone al frente de todas las carpetas
            print("LOG: Interfaz mostrada con éxito.")

    # def centrar_ventana(self, ventana):
    #     pantalla = QApplication.primaryScreen().availableGeometry()
    #     tamano_ventana = ventana.size()
    #     x = (pantalla.width() - tamano_ventana.width()) // 2
    #     y = (pantalla.height() - tamano_ventana.height()) // 2
    #     ventana.move(x, y)

    def startup_check(self):
        QTimer.singleShot(200, QApplication.instance().quit)

    # ===================================================================
    # ===================================================================


    ######################
    # From the RoboCompGestorSG you can call this methods:
    # RoboCompGestorSG.void self.gestorsg_proxy.LanzarApp()
