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

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from rich.console import Console
from genericworker import *
import interfaces as ifaces

import json
from time import sleep
import pandas as pd
import time
from datetime import datetime
import random
import os
import sys
import traceback

from PySide6 import QtUiTools, QtCore
from PySide6.QtCore import Qt, QTimer, QFile, Slot
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtGui import QPixmap, QPainter, QColor, QPen, QFont

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

UI_RESP = "../../igs/Trivial_respuesta.ui"
UI_MENU = "../../igs/Trivial_menu.ui"
UI_CHECK =  "../../igs/botonUI.ui"
UI_START = "../../igs/comenzarUI.ui"
UI_PLAYER = "../../igs/trivial_player.ui"
UI_CATEGORIA = "../../igs/seleccioncategoria_TRIVIAL.ui"

LOGO_1 = "../../igs/logos/logo_euro.png"
LOGO_2 = "../../igs/logos/robolab.png"

PREGUNTAS_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "preguntas"))

sys.path.append('/opt/robocomp/lib')
console = Console(highlight=False)


class SpecificWorker(GenericWorker):
    update_ui_signal = QtCore.Signal()
    def __init__(self, proxy_map, configData, startup_check=False):
        super(SpecificWorker, self).__init__(proxy_map, configData)
        self.Period = configData["Period"]["Compute"]
        self.NUM_LEDS = 52
        if startup_check:
            self.startup_check()
        else:
            self.timer.timeout.connect(self.compute)
            self.timer.start(self.Period)
        self.hide()

        self.reiniciar_variables()

        QApplication.processEvents()

        self.ui = self.load_ui()
        self.ui2 = self.therapist_ui()
        self.ui3 = self.load_check()
        self.ui4 = self.comenzar_check()
        self.ui5 = self.player_ui()
        self.ui6 = self.seleccion_categoria_ui()

        self.update_ui_signal.connect(self.handle_update_ui)


        ########## BATERÍA DE RESPUESTAS ##########
        self.bateria_aciertos = [
            "¡Muy bien, respuesta correcta!",
            "¡Correcto, lo has hecho genial!",
            "¡Perfecto, esa era!",
            "¡Estupendo, seguimos así!",
            "¡Muy bien, vas fenomenal!",
            "¡Has acertado!",
            "¡Lo estás haciendo genial!",
            "¡Acertaste, increíble!",
            "¡Eso es correcto, muy bien hecho!",
            "¡Perfecto, acertaste!",
            "¡Muy bien, respuesta correcta!",
            "¡Qué acierto tan brillante!",
            "¡Excelente, lo conseguiste!"
        ]

        self.bateria_fallos = [
            "No pasa nada, seguimos con la siguiente.",
            "Esta vez no era, pero lo estás haciendo muy bien.",
            "No te preocupes, la siguiente seguro que sale mejor.",
            "Casi, pero seguimos jugando.",
            "No pasa nada, lo importante es participar.",
            "Fallo, pero no te preocupes!",
            "No pasa nada, todos fallamos!",
            "Sigue intentándolo, ¡lo harás mejor!",
            "Es un error, pero no te rindas!",
            "¡Ánimo, la próxima será mejor!",
            "¡No te preocupes, sigue adelante!",
            "¡Un tropiezo no define tu esfuerzo!",
            "¡No pasa nada, la práctica hace al maestro!"
        ]

        self.bateria_saltar = [
            "Pasamos esta pregunta y seguimos.",
            "No pasa nada, vamos con otra.",
            "Saltamos esta pregunta.",
            "De acuerdo, pasamos a la siguiente.",
            "Seguimos con otra pregunta."
        ]

        self.bateria_fin_juego = [
            "El juego ha terminado, ¡lo has hecho genial!",
            "¡Fin del juego, muy bien jugado!",
            "Esto ha sido todo, ¡excelente trabajo!",
            "¡Gran final, lo hiciste estupendamente!",
            "Juego terminado, ¡felicitaciones por tu esfuerzo!",
            "¡Increíble, has completado el juego!",
            "¡Fantástico, qué gran partida!",
            "¡Finalizado, te has lucido!"
        ]

    def __del__(self):
        """Destructor"""

    def set_all_LEDS_colors(self, red=0, green=0, blue=0, white=0):
        pixel_array = {i: ifaces.RoboCompLEDArray.Pixel(red=red, green=green, blue=blue, white=white) for i in
                       range(self.NUM_LEDS)}
        self.ledarray_proxy.setLEDArray(pixel_array)

    def terminaHablar(self):
        sleep(2.5)
        while self.speech_proxy.isBusy():
            pass

    def archivo(self, archivo_json):
        # Cargar las preguntas desde el archivo JSON de la categoría seleccionada
        self.bd = archivo_json

        with open(self.bd, 'r', encoding='utf-8') as json_file:
            self.datos = json.load(json_file)

        self.preguntas = []
        self.opciones = []
        self.respuestas = []

        for pregunta in self.datos:
            # Si una pregunta no tiene dificultad, se considera fácil para no perderla.
            dificultad_pregunta = pregunta.get("dificultad", "Fácil")

            if dificultad_pregunta == self.dificultad:
                self.preguntas.append(pregunta["pregunta"])
                self.opciones.append(pregunta["opciones"])
                self.respuestas.append(pregunta["correcta"])

    def reiniciar_variables(self):
        self.datos = []

        self.preguntas = []
        self.opciones = []
        self.respuestas = []
        self.preguntas_usadas = set()

        self.aciertos = 0
        self.fallos = 0
        self.pasadas = 0

        self.nombre = ""
        self.dificultad = ""
        self.categoria = ""
        self.categoria_texto = ""
        self.bd = ""

        self.fecha = 0
        self.hora = 0

        self.numero_rondas = 0
        self.ronda_actual = 0

        self.start_time = None
        self.end_time = None
        self.elapsed_time = None

        self.start_question_time = 0
        self.end_question_time = 0
        self.response_time = 0
        self.responses_times = []
        self.media = 0

        self.pregunta_actual = ""
        self.opciones_actuales = []
        self.respuesta_correcta = ""

        self.resultados_categorias = []
        self.resultados_preguntas = []
        self.resultados_opciones = []
        self.resultados_respuestas_correctas = []
        self.resultados_respuestas_terapeuta = []
        self.resultados_tiempos = []

        self.resp = ""
        self.check = ""

        self.running = False
        self.comenzar_pulsado = False
        self.categoria_elegida = False

    # ################################### INTERFACES GRÁFICAS ##########################################################

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

        # Ayuda
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

    def toggle_ayuda(self, ui):
        if hasattr(ui, "ayuda"):
            ui.ayuda.setVisible(not ui.ayuda.isVisible())

    def back_clicked_ui(self, ui_number):
        self.boton = False
        self.cerrar_ui(ui_number)
        self.gestorsg_proxy.LanzarApp()

    def eventFilter(self, obj, event):
        """ Captura eventos de la UI """
        # Obtener el número de UI asociado al objeto
        ui_number = self.ui_numbers.get(obj, None)
        if ui_number is not None and event.type() == QtCore.QEvent.Close:
            target_ui = self.ui if ui_number == 1 else getattr(self, f'ui{ui_number}', None)
            if obj == target_ui:
                respuesta = QMessageBox.question(
                    target_ui, "Cerrar", f"¿Estás seguro de que quieres salir del juego?",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                )
                if respuesta == QMessageBox.Yes:
                    print(f"Ventana {ui_number} cerrada por el usuario.")
                    self.running = False

                    self.reiniciar_variables()
                    self.set_all_LEDS_colors(0, 0, 0, 0)

                    self.gestorsg_proxy.LanzarApp()
                    target_ui.hide()
                    event.ignore()
                    return True  # Permitir el cierre
                else:
                    print(f"Cierre de la ventana {ui_number} cancelado.")
                    event.ignore()  # Bloquear el cierre
                    return True  # **DETENER la propagación del evento para que no se cierre**
        return False  # Propaga otros eventos normalmente

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

    @QtCore.Slot()
    def handle_update_ui(self):
        if not self.ui2:
            print("Error: la interfaz de usuario no se ha cargado correctamente.")
            return

        self.centrar_ventana(self.ui)
        self.ui2.raise_()
        self.ui2.show()
        QApplication.processEvents()

    ##########################################################################################

    def load_ui(self):
        ui = self.load_ui_generic(
            UI_RESP, ui_number=1,
            # titulo="Trivial EBO - Terapeuta",
            logo_paths={"label_2": LOGO_1, "label_3": LOGO_2},
            botones={
                "correcta": self.correcta_clicked,
                "incorrecta": self.incorrecta_clicked,
                "saltar": self.saltar_clicked,
                "repetir": self.repetir_clicked,
            },
            ayuda_button="ayuda_button",
            back_button="back_button"
        )
        return ui

    def correcta_clicked(self):
        self.resp = "si"
        print("Terapeuta: respuesta correcta")
        self.cerrar_ui(1)


    def incorrecta_clicked(self):
        self.resp = "no"
        print("Terapeuta: respuesta incorrecta")
        self.cerrar_ui(1)

    def saltar_clicked(self):
        self.resp = "saltar"
        print("Terapeuta: pregunta saltada")
        self.cerrar_ui(1)

    def repetir_clicked(self):
        print("Terapeuta: repetir la pregunta")

        if self.speech_proxy.isBusy():
            pass
        else:
            texto = self.pregunta_actual

            for opcion in self.opciones_actuales:
                texto += f". {opcion}"

            self.speech_proxy.say(texto, False)
            print(f"EBO: {texto}")
            self.terminaHablar()

        ##########################################################################################

    def therapist_ui(self):
        self.running = True
        ui = self.load_ui_generic(
            UI_MENU, ui_number=2,
            # titulo="Trivial EBO - Configuración",
            logo_paths={"label": LOGO_1, "label_2": LOGO_2},
            botones={
                "confirmar_button": self.therapist,
                "facil_button": lambda: self.dificultad_clicked("Fácil"),
                "medio_button": lambda: self.dificultad_clicked("Medio"),
                "dificil_button": lambda: self.dificultad_clicked("Difícil"),
            },
            ayuda_button="ayuda_button",
            back_button="back_button"
        )
        return ui

    def dificultad_clicked(self, dificultad):
        self.dificultad = dificultad

    def therapist(self):

        self.nombre = self.ui2.usuario.toPlainText().strip()
        texto_rondas = self.ui2.num_rondas.text()

        if not self.nombre:
            print("Falta el nombre de usuario.")
            return

        if not texto_rondas.isdigit():
            print("El número de rondas no es válido.")
            return

        if self.dificultad == "":
            print("Falta seleccionar la dificultad.")
            return

        self.numero_rondas = int(texto_rondas)

        if self.numero_rondas <= 0:
            print("El número de rondas debe ser mayor que cero.")
            return

        print(f"Partida: {self.nombre} · {self.dificultad} · {self.numero_rondas} rondas")

        self.running = True
        self.ui2.hide()
        self.ui2.usuario.clear()
        self.ui2.num_rondas.clear()
        self.introduccion()


    ##########################################################################################

    def seleccion_categoria_ui(self):
        ui = self.load_ui_generic(
            UI_CATEGORIA, ui_number=6,
            # titulo="Trivial EBO - Selección de categoría",
            botones={
                "entretenimiento_btn": lambda: self.categoria_clicked("entretenimiento.json", "Entretenimiento"),
                "geografia_btn": lambda: self.categoria_clicked("geografia.json", "Geografía"),
                "ciencias_btn": lambda: self.categoria_clicked("cienciaynaturaleza.json", "Ciencia y naturaleza"),
                "histori_btn": lambda: self.categoria_clicked("historia.json", "Historia"),
                "art_cultura_btn": lambda: self.categoria_clicked("arteycultura.json", "Arte y cultura"),
                "vida_cotidiana_btn": lambda: self.categoria_clicked("vidacotidiana.json", "Vida cotidiana"),
            }
        )
        return ui

    def categoria_clicked(self, categoria, categoria_texto):
        self.categoria = categoria
        self.categoria_texto = categoria_texto
        self.bd = os.path.join(PREGUNTAS_DIR, self.categoria)

        if not os.path.exists(self.bd):
            print(f"No existe el archivo de preguntas: {self.bd}")
            return

        self.categoria_elegida = True
        print(f"Terapeuta: categoría {self.categoria_texto}")
        self.ui6.hide()

    ##########################################################################################

    def load_check(self):
        ui = self.load_ui_generic(
            UI_CHECK, ui_number=3,
            # titulo="Trivial EBO - Explicación del juego",
            botones={"si": self.si_clicked, "no": self.no_clicked}
        )
        return ui

    def si_clicked(self):
        self.check = "si"
        print("Terapeuta: sí, explicar el juego")
        self.ui3.accept()

    def no_clicked(self):
        self.check = "no"
        print("Terapeuta: no explicar el juego")
        self.ui3.accept()

    ##########################################################################################

    def comenzar_check(self):
        ui = self.load_ui_generic(
            UI_START, ui_number=4,
            # titulo="Trivial EBO - Comenzar",
            botones={"comenzar": self.comenzar}
        )
        return ui

    def comenzar(self):
        self.running = True
        print("¡El juego ha comenzado!")
        self.ui4.accept()  # Cierra el diálogo cuando el botón es presionado
        self.start_time = time.time()
        self.fecha = datetime.now().strftime("%d-%m-%Y")
        self.hora = datetime.now().strftime("%H:%M:%S")

    ##########################################################################################

    def player_ui(self):
        ui = self.load_ui_generic(
            UI_PLAYER,
            ui_number=5,
            # titulo="Trivial EBO - Jugador"
        )

        # if hasattr(ui, "label_player_titulo"):
        #     ui.label_player_titulo.setText("TRIVIAL EBO")

        if hasattr(ui, "label_circulo"):
            ui.label_circulo.clear()

        return ui

    def pintar_circulo(self, aciertos=0):
        #Actualización de círculo de progreso
        total = max(1, self.numero_rondas)
        aciertos = max(0, min(aciertos, total))
        progreso = aciertos / total

        label = self.ui5.label_circulo
        ancho = label.width()
        alto = label.height()

        if ancho <= 50 or alto <= 50:
            size = 420
        else:
            size = min(500, max(320, min(ancho, alto) - 20))

        margen = 18

        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = pixmap.rect().adjusted(margen, margen, -margen, -margen)

        painter.setBrush(QColor("#E6E6E6"))
        painter.setPen(QPen(QColor("#A0A0A0"), 5))
        painter.drawEllipse(rect)

        painter.setBrush(QColor("#FFD700"))
        painter.setPen(Qt.NoPen)
        # Qt mide los ángulos en dieciseisavos de grado: 90*16 empieza arriba y
        # el signo negativo hace que avance en sentido horario.
        painter.drawPie(rect, 90 * 16, int(-360 * 16 * progreso))

        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor("#555555"), 5))
        painter.drawEllipse(rect)

        fuente = QFont()
        fuente.setPointSize(32)
        fuente.setBold(True)

        painter.setFont(fuente)
        painter.setPen(QColor("#222222"))
        painter.drawText(rect, Qt.AlignCenter, f"{aciertos}/{total}")

        painter.end()

        label.setPixmap(pixmap)
        label.setAlignment(Qt.AlignCenter)

    ########## PROCESO DEL JUEGO ##########

    def introduccion(self):
        while self.running:
            if not self.running:
                break

            QApplication.processEvents()

            self.fecha = datetime.now().strftime("%d-%m-%Y")
            self.hora = datetime.now().strftime("%H:%M:%S")

            self.emotionalmotor_proxy.expressJoy()
            self.speech_proxy.say(f"Hola {self.nombre}, vamos a jugar al Trivial.", False)
            print(f"EBO: Hola {self.nombre}, vamos a jugar al Trivial.")
            self.speech_proxy.say("En este juego tendrás que responder preguntas de distintas categorías.", False)
            print("EBO: En este juego tendrás que responder preguntas de distintas categorías.")
            self.speech_proxy.say("¿Quieres que te explique el juego?", False)
            print("EBO: ¿Quieres que te explique el juego?")
            self.terminaHablar()

            self.check = ""
            self.ui3.show()
            self.ui3.exec_()

            if self.check == "si":
                self.speech_proxy.say("Antes de cada ronda se elegirá una categoría.", False)
                print("EBO: Antes de cada ronda se elegirá una categoría.")
                self.speech_proxy.say("Después escucharás una pregunta con varias opciones de respuesta.", False)
                print("EBO: Después escucharás una pregunta con varias opciones de respuesta.")
                self.speech_proxy.say(
                    "Yo te indicaré si la respuesta ha sido correcta, incorrecta o si pasamos la pregunta.", False)
                print("EBO: Yo te indicaré si la respuesta ha sido correcta, incorrecta o si pasamos la pregunta.")
                self.speech_proxy.say("El juego termina cuando se completen todas las rondas seleccionadas.", False)
                print("EBO: El juego termina cuando se completen todas las rondas seleccionadas.")
            else:
                # Incluye el caso de cerrar el diálogo sin responder.
                self.speech_proxy.say("Perfecto. Empezamos directamente.", False)
                print("EBO: Perfecto. Empezamos directamente.")

            self.terminaHablar()
            self.ui4.show()
            self.ui4.exec_()
            self.juego()


    def juego(self):
        self.start_time = time.time()
         #TODO revisar que hace esto
        archivo_resultados = "../resultados_trivial.json"
        preguntas_historicas = set()

        if os.path.exists(archivo_resultados):
            try:
                df_historico = pd.read_json(archivo_resultados, orient='records', lines=True)
                df_historico = df_historico[df_historico["Dificultad"] == self.dificultad]

                for preguntas in df_historico["Pregunta"]:
                    if isinstance(preguntas, list):
                        preguntas_historicas.update(preguntas)
            except Exception as e:
                print(f"No se pudo leer el histórico de preguntas: {e}")

        self.ui5.show()

        if hasattr(self.ui5, "label_circulo"):
            self.pintar_circulo(self.aciertos)

        QApplication.processEvents()
        ronda = 0

        while ronda < self.numero_rondas and self.running:
            self.ronda_actual = ronda + 1
            self.resp = ""
            self.categoria_elegida = False

            print(f"--- Ronda {self.ronda_actual}/{self.numero_rondas} ---")


            self.ui6.show()

            while not self.categoria_elegida and self.running:
                QApplication.processEvents()
                sleep(0.1)


            # Si un JSON está mal formado, se trata igual que una categoría sin preguntas y el terapeuta elige otra.

            self.archivo(self.bd)


            if len(self.preguntas) == 0:
                print(f"Sin preguntas de dificultad {self.dificultad} en {self.categoria_texto}.")
                self.speech_proxy.say("Ya hemos completado esta categoría. Vamos a elegir otra.", False)
                print("EBO: Ya hemos completado esta categoría. Vamos a elegir otra.")
                self.terminaHablar()
                continue

            indices_disponibles = [
                i for i, pregunta in enumerate(self.preguntas)
                if pregunta not in self.preguntas_usadas and pregunta not in preguntas_historicas
            ]

            if len(indices_disponibles) == 0:
                # Buscamos qué preguntas nos faltan por hacer
                indices_disponibles = [
                    i for i, pregunta in enumerate(self.preguntas)
                    if pregunta not in self.preguntas_usadas
                ]




            indice = random.choice(indices_disponibles)
            self.preguntas_usadas.add(self.preguntas[indice])

            self.pregunta_actual = self.preguntas[indice]
            self.opciones_actuales = self.opciones[indice]
            self.respuesta_correcta = self.respuestas[indice]

            print(f"Respuesta correcta: {self.respuesta_correcta}")

            # if hasattr(self.ui5, "label_player_titulo"):
            #     self.ui5.label_player_titulo.setText(f"TRIVIAL EBO - Aciertos: {self.aciertos}")



            if hasattr(self.ui, "respuesta_correcta"):
                self.ui.respuesta_correcta.clear()
                self.ui.respuesta_correcta.insertPlainText(self.respuesta_correcta)

            for nombre_boton in ("correcta", "incorrecta", "saltar"):
                if hasattr(self.ui, nombre_boton):
                    getattr(self.ui, nombre_boton).setEnabled(True)



            texto_pregunta = self.pregunta_actual

            for opcion in self.opciones_actuales:
                texto_pregunta += f". {opcion}"

            self.speech_proxy.say(f"Categoría {self.categoria_texto}.", False)
            print(f"EBO: Categoría {self.categoria_texto}.")

            self.speech_proxy.say(texto_pregunta, False)
            print(f"EBO: {texto_pregunta}")

            self.terminaHablar()

            self.ui.show()
            self.ui.raise_()
            self.ui.activateWindow()
            QApplication.processEvents()

            self.start_question_time = time.time()

            while self.resp == "":
                QApplication.processEvents()
                sleep(0.1)

            if self.resp == "si":
                self.aciertos += 1
                frase = random.choice(self.bateria_aciertos)
                self.speech_proxy.say(frase, False)
                print(f"EBO: {frase}")
                self.set_all_LEDS_colors(0, 255, 0)
                self.emotionalmotor_proxy.expressJoy()
                sleep(1)
                self.set_all_LEDS_colors(0, 0, 0)

            elif self.resp == "no":
                self.fallos += 1
                frase = random.choice(self.bateria_fallos)
                self.speech_proxy.say(frase, False)
                print(f"EBO: {frase}")
                self.set_all_LEDS_colors(255, 0, 0)
                self.emotionalmotor_proxy.expressSadness()
                sleep(1)
                self.set_all_LEDS_colors(0, 0, 0)

            elif self.resp == "saltar":
                self.pasadas += 1
                frase = random.choice(self.bateria_saltar)
                self.speech_proxy.say(frase, False)
                print(f"EBO: {frase}")
                self.set_all_LEDS_colors(255, 180, 0)
                sleep(1)
                self.set_all_LEDS_colors(0, 0, 0)

            self.ui.hide()

            self.end_question_time = time.time()
            self.response_time = self.end_question_time - self.start_question_time
            self.responses_times.append(self.response_time)



            self.resultados_categorias.append(self.categoria_texto)
            self.resultados_preguntas.append(self.pregunta_actual)
            self.resultados_opciones.append(self.opciones_actuales)
            self.resultados_respuestas_correctas.append(self.respuesta_correcta)
            self.resultados_respuestas_terapeuta.append(self.resp)
            self.resultados_tiempos.append(round(self.response_time, 2))

            # if hasattr(self.ui5, "label_player_titulo"):
            #     self.ui5.label_player_titulo.setText(f"TRIVIAL EBO - Aciertos: {self.aciertos}")

            if hasattr(self.ui5, "label_circulo"):
                self.pintar_circulo(self.aciertos)

            # self.cerrar_ui(1)

            ronda += 1

        self.end_time = time.time()
        self.elapsed_time = self.end_time - self.start_time
        self.media = (sum(self.responses_times) / len(self.responses_times)) if self.responses_times else 0.0
        # self.running = False

        # if hasattr(self.ui5, "label_player_titulo"):
        #     self.ui5.label_player_titulo.setText(f"FIN DEL JUEGO - Aciertos: {self.aciertos}/{self.numero_rondas}")

        if hasattr(self.ui5, "label_circulo"):
            self.pintar_circulo(self.aciertos)

        QApplication.processEvents()

        self.speech_proxy.say("Fin del juego. Lo has hecho genial.", False)
        print("EBO: Fin del juego. Lo has hecho genial.")
        self.terminaHablar()

        print(f"Fin de la partida: {self.aciertos} aciertos, {self.fallos} fallos, {self.pasadas} saltadas")
        self.cerrar_ui(5)
        self.guardar_resultados()
        self.reiniciar_variables()
        self.gestorsg_proxy.LanzarApp()

    def guardar_resultados(self):
        archivo = "../resultados_trivial.json"

        if not self.resultados_preguntas:
            print("No se ha completado ninguna ronda: no se guardan resultados.")
            return

        # Una fila por partida: los datos de las rondas van en arrays.
        self.df = pd.DataFrame([{
            "Nombre": self.nombre,
            "Dificultad": self.dificultad,
            "Categoria": self.resultados_categorias,
            "Pregunta": self.resultados_preguntas,
            "Opciones": self.resultados_opciones,
            "Respuesta correcta": self.resultados_respuestas_correctas,
            "Respuesta terapeuta": self.resultados_respuestas_terapeuta,
            "Fecha": self.fecha,
            "Hora": self.hora,
            "Aciertos": self.aciertos,
            "Fallos": self.fallos,
            "Preguntas saltadas": self.pasadas,
            "Tiempo de respuesta (seg)": self.resultados_tiempos,
            "Tiempo de respuesta medio (seg)": round(self.media, 2),
            "Tiempo transcurrido total (seg)": round(self.elapsed_time, 2)
        }])

        datos_existentes = pd.DataFrame()

        if os.path.exists(archivo):
            try:
                datos_existentes = pd.read_json(archivo, orient='records', lines=True)
            except ValueError:
                print("El histórico tenía un formato inválido: se sobrescribe.")

        if not datos_existentes.empty:
            self.df = pd.concat([datos_existentes, self.df], ignore_index=True)

        self.df.to_json(archivo, orient='records', lines=True, force_ascii=False)
        print(f"Resultados guardados en {archivo}")

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
        print(f"Testing RoboCompCameraSimple.TImage from ifaces.RoboCompCameraSimple")
        test = ifaces.RoboCompCameraSimple.TImage()
        print(f"Testing RoboCompLEDArray.Pixel from ifaces.RoboCompLEDArray")
        test = ifaces.RoboCompLEDArray.Pixel()
        QTimer.singleShot(200, QApplication.instance().quit)




    # =============== Methods for Component Implements ==================
    # ===================================================================

    #
    # IMPLEMENTATION of StartGame method from JuegoTrivial interface
    #
    def JuegoTrivial_StartGame(self):
        print("Iniciando Trivial...")
        self.set_all_LEDS_colors(0, 0, 0, 255)
        self.boton = False
        self.centrar_ventana(self.ui2)
        self.ui2.show()
        pass


    # ===================================================================
    # ===================================================================


    ######################
    # From the RoboCompCameraSimple you can call this methods:
    # RoboCompCameraSimple.TImage self.camerasimple_proxy.getImage()

    ######################
    # From the RoboCompCameraSimple you can use this types:
    # ifaces.RoboCompCameraSimple.TImage

    ######################
    # From the RoboCompEmotionalMotor you can call this methods:
    # RoboCompEmotionalMotor.void self.emotionalmotor_proxy.expressAnger()
    # RoboCompEmotionalMotor.void self.emotionalmotor_proxy.expressDisgust()
    # RoboCompEmotionalMotor.void self.emotionalmotor_proxy.expressFear()
    # RoboCompEmotionalMotor.void self.emotionalmotor_proxy.expressJoy()
    # RoboCompEmotionalMotor.void self.emotionalmotor_proxy.expressSadness()
    # RoboCompEmotionalMotor.void self.emotionalmotor_proxy.expressSurprise()
    # RoboCompEmotionalMotor.void self.emotionalmotor_proxy.isanybodythere(bool isAny)
    # RoboCompEmotionalMotor.void self.emotionalmotor_proxy.listening(bool setListening)
    # RoboCompEmotionalMotor.void self.emotionalmotor_proxy.pupposition(float x, float y)
    # RoboCompEmotionalMotor.void self.emotionalmotor_proxy.talking(bool setTalk)

    ######################
    # From the RoboCompGestorSG you can call this methods:
    # RoboCompGestorSG.void self.gestorsg_proxy.LanzarApp()

    ######################
    # From the RoboCompLEDArray you can call this methods:
    # RoboCompLEDArray.PixelArray self.ledarray_proxy.getLEDArray()
    # RoboCompLEDArray.bool self.ledarray_proxy.setLEDArray(PixelArray pixelArray)

    ######################
    # From the RoboCompLEDArray you can use this types:
    # ifaces.RoboCompLEDArray.Pixel

    ######################
    # From the RoboCompSpeech you can call this methods:
    # RoboCompSpeech.bool self.speech_proxy.isBusy()
    # RoboCompSpeech.bool self.speech_proxy.say(str text, bool overwrite)


