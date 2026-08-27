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
from collections import Counter

import cv2
import numpy as np
import torch
import open_clip
from PIL import Image

from PySide6 import QtUiTools, QtWidgets, QtCore
from PySide6.QtCore import QTimer, QFile, Slot
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtGui import QPixmap

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

UI_RESP = "../../igs/veoveoEBO_respuesta.ui"
UI_MENU = "../../igs/veoveoEBO_menu.ui"
UI_CHECK = "../../igs/botonUI.ui"
UI_START = "../../igs/comenzarUI.ui"

LOGO_1 = "../../igs/logos/logo_euro.png"
LOGO_2 = "../../igs/logos/robolab.png"

TARJETAS_DIR = os.path.abspath(os.path.join(BASE_DIR, "../tarjetas"))




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

        QApplication.instance().setQuitOnLastWindowClosed(False)
        self.hide()
        self.margen_tarjeta = 6
        self.num_analisis_vlm = 15
        self.umbral_vlm = 0.80

        self.reiniciar_variables ()

        QApplication.processEvents()

        self.ui = self.load_ui()
        self.ui2 = self.therapist_ui()
        self.ui3 = self.load_check()
        self.ui4 = self.comenzar_check()
        self.ui.hide()


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

        self.update_ui_signal.connect(self.handle_update_ui)


    def set_all_LEDS_colors(self, red=0, green=0, blue=0, white=0):
        pixel_array = {i: ifaces.RoboCompLEDArray.Pixel(red=red, green=green, blue=blue, white=white) for i in
                       range(self.NUM_LEDS)}
        self.ledarray_proxy.setLEDArray(pixel_array)

    def terminaHablar(self):
        sleep(2.5)
        while self.speech_proxy.isBusy():
            pass

    ########## OBTIENE LAS TARJETAS ##########

    def archivo(self, archivo_json):
        """Cargar las tarjetas desde el archivo JSON de la categoría seleccionada"""
        self.bd = archivo_json

        self.datos = []
        self.objetivos = []
        self.pistas = []
        self.prompts_vlm = []
        self.tarjetas_usadas = []

        with open(self.bd, 'r', encoding='utf-8') as json_file:
            self.datos = json.load(json_file)

        # Los archivos de tarjetas son un array plano, pero se acepta también el formato {"tarjetas": [...]} por si alguno viene envuelto.
        if isinstance(self.datos, dict):
            self.datos = self.datos.get("tarjetas", [])

        for tarjeta in self.datos:
            self.objetivos.append(tarjeta["nombre"])
            self.pistas.append(tarjeta["pista"])
            self.prompts_vlm.append(tarjeta["prompt_vlm"])

    ########## REINICIO DE VARIABLES ##########

    def reiniciar_variables(self):
        self.datos = []

        self.objetivos = []
        self.pistas = []
        self.prompts_vlm = []
        self.tarjetas_usadas = []

        self.aciertos = 0
        self.fallos = 0

        self.nombre = ""
        self.categoria = ""
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

        self.resultados_objetivos = []
        self.resultados_terapeuta = []
        self.resultados_scores_vlm = []
        self.resultados_tiempos = []

        self.objetivo_actual = ""
        self.pista_actual = ""

        self.resp = ""
        self.check = ""

        self.running = False
        self.comenzar_pulsado = False

        self.ebo_detecta_objeto = False
        self.prediccion_vlm = "-"
        self.score_vlm = 0.0
        self.sin_camara_avisado = False

        self.modelo_vlm = None
        self.preprocess_vlm = None
        self.tokenizer_vlm = None
        self.device_vlm = "cpu"

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

        self.centrar_ventana(self.ui2)
        self.ui2.raise_()
        self.ui2.show()
        QApplication.processEvents()

    ##########################################################################################

    def load_ui(self):
        ui = self.load_ui_generic(
            UI_RESP, ui_number=1,
            logo_paths={"label_2": LOGO_1, "label_3": LOGO_2},
            botones={
                "correcta": self.correcta_clicked,
                "incorrecta": self.incorrecta_clicked,
                "repetir": self.repetir_clicked,
            },
            ayuda_button="ayuda_button",
            back_button="back_button",
            after_load=lambda u: (hasattr(u, "ayuda") and u.ayuda.hide())
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


    def repetir_clicked(self):
        print("Terapeuta: repetir la pista")
        self.resp = "repetir"

        if self.speech_proxy.isBusy():
            pass

    ##########################################################################################

    def therapist_ui(self):
        ui = self.load_ui_generic(
            UI_MENU, ui_number=2,
            logo_paths={"label": LOGO_1, "label_2": LOGO_2},
            botones={"confirmar_button": self.therapist},
            ayuda_button="ayuda_button",
            back_button="back_button",
            after_load=lambda u: self.configure_combobox(u, TARJETAS_DIR)
        )
        return ui

    def therapist(self):

        self.nombre = self.ui2.usuario.toPlainText().strip()
        self.categoria = self.ui2.categoria_combo.currentText()
        texto_rondas = self.ui2.num_rondas.text()

        if not self.nombre:
            print("Falta el nombre de usuario.")
            return

        if not self.categoria or self.categoria == "Seleccionar categoría...":
            print("Falta seleccionar la categoría.")
            return

        if not texto_rondas.isdigit():
            print("El número de rondas no es válido.")
            return

        self.numero_rondas = int(texto_rondas)

        if self.numero_rondas <= 0:
            print("El número de rondas debe ser mayor que cero.")
            return

        self.bd = os.path.join(TARJETAS_DIR, f"{self.categoria}.json")

        if not os.path.exists(self.bd):
            print(f"No existe el archivo de tarjetas: {self.bd}")
            return

        print(f"Partida: {self.nombre} · {self.categoria} · {self.numero_rondas} rondas")

        self.running = True
        self.ui2.hide()
        self.ui2.usuario.clear()
        self.ui2.categoria_combo.clear()
        self.ui2.num_rondas.clear()
        self.introduccion()

    def configure_combobox(self, ui, folder_path):
        # Acceder al QComboBox por su nombre de objeto
        combobox = ui.findChild(QtWidgets.QComboBox, "categoria_combo")
        if combobox:
            combobox.addItem("Seleccionar categoría...")
            # Obtener la lista de archivos en la carpeta
            try:
                archivos = [
                    archivo for archivo in os.listdir(folder_path)
                    if os.path.isfile(os.path.join(folder_path, archivo))
                ]
                # Agregar los nombres de los archivos al QComboBox sin la extensión .json
                for archivo in archivos:
                    nombre_sin_extension, ext = os.path.splitext(archivo)
                    # Agregar solo el nombre sin la extensión
                    combobox.addItem(nombre_sin_extension)
            except FileNotFoundError:
                print(f"La carpeta {folder_path} no existe.")
            except Exception as e:
                print(f"Error al listar archivos: {e}")
        else:
            print("No se encontró el QComboBox")

    ##########################################################################################

    def load_check(self):
        ui = self.load_ui_generic(
            UI_CHECK, ui_number=3,
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
            botones={"comenzar": self.comenzar}
        )
        return ui

    def comenzar(self):
        self.comenzar_pulsado = True
        print("Terapeuta: comenzar la partida")
        self.ui4.accept()  # Cierra el diálogo cuando el botón es presionado
        self.start_time = time.time()
        self.fecha = datetime.now().strftime("%d-%m-%Y")
        self.hora = datetime.now().strftime("%H:%M:%S")

    ########## FUNCIONES DEL VLM ##########

    def cargar_modelo_vlm(self):
        self.device_vlm = "cpu"

        self.modelo_vlm, _, self.preprocess_vlm = open_clip.create_model_and_transforms(
            "MobileCLIP2-S0",
            pretrained="dfndr2b",
            device=self.device_vlm
        )

        self.tokenizer_vlm = open_clip.get_tokenizer("MobileCLIP2-S0")
        self.modelo_vlm.eval()

    def analizar_vlm(self):
        """Analiza una imagen. Devuelve (tarjeta más probable, puntuación)."""
        try:
            imagen = self.camerasimple_proxy.getImage()

            if imagen is None or imagen.image is None:
                return "-", 0.0

            frame = np.frombuffer(imagen.image, dtype=np.uint8)

            if frame.size == 0:
                return "-", 0.0

            frame = frame.reshape((imagen.height, imagen.width, imagen.depth))

            if imagen.depth == 3:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            else:
                frame_rgb = frame

            imagen_pil = Image.fromarray(frame_rgb)

            image_tensor = self.preprocess_vlm(imagen_pil).unsqueeze(0).to(self.device_vlm)
            text_tokens = self.tokenizer_vlm(self.prompts_vlm).to(self.device_vlm)

            with torch.no_grad():
                image_features = self.modelo_vlm.encode_image(image_tensor)
                text_features = self.modelo_vlm.encode_text(text_tokens)

                image_features /= image_features.norm(dim=-1, keepdim=True)
                text_features /= text_features.norm(dim=-1, keepdim=True)

                probs = (100.0 * image_features @ text_features.T).softmax(dim=-1)
                probs = probs.cpu().numpy()[0]

            indice = int(np.argmax(probs))

            return self.objetivos[indice], float(probs[indice])

        except Exception as e:
            print(f"Error analizando la imagen: {e}")
            return "-", 0.0

    def analizar_ronda_vlm(self):
        """Varios análisis seguidos para dar un veredicto estable. Solo se
        imprime la decisión final"""
        resultados = []

        for _ in range(self.num_analisis_vlm):
            # Si el terapeuta ya ha calificado, se corta la tanda pero se da
            # veredicto con lo visto hasta ahora: salir sin él dejaría el
            # score a cero en los resultados.
            if not self.running or self.resp != "":
                break

            QApplication.processEvents()
            prediccion, score = self.analizar_vlm()

            if prediccion != "-":
                resultados.append((prediccion, score))

            # Freno mínimo: si la cámara falla, analizar_vlm() devuelve al
            # instante y esto sería un bucle a toda CPU.
            sleep(0.05)

        if not resultados:
            self.prediccion_vlm = "-"
            self.score_vlm = 0.0
            self.ebo_detecta_objeto = False

            # Una sola vez por ronda: si no, llena el terminal.
            if not self.sin_camara_avisado:
                print("EBO no ve nada por la cámara.")
                self.sin_camara_avisado = True

            return

        votos = Counter(prediccion for prediccion, _ in resultados)
        self.prediccion_vlm, numero_votos = votos.most_common(1)[0]

        scores_prediccion_final = [
            score for prediccion, score in resultados
            if prediccion == self.prediccion_vlm
        ]
        self.score_vlm = sum(scores_prediccion_final) / len(scores_prediccion_final)

        # Mayoría de las imágenes realmente analizadas, que pueden ser menos
        # que NUM_ANALISIS_VLM si el terapeuta ha cortado la tanda.
        votos_necesarios = (len(resultados) // 2) + 1
        self.ebo_detecta_objeto = (
                self.prediccion_vlm == self.objetivo_actual
                and numero_votos >= votos_necesarios
                and self.score_vlm >= self.umbral_vlm
        )

        veredicto = "SI" if self.ebo_detecta_objeto else "NO"
        print(
            f"EBO ve: {self.prediccion_vlm} "
            f"({numero_votos}/{self.num_analisis_vlm} votos, {self.score_vlm:.2f}) -> {veredicto}"
        )


    ########## PROCESO DEL JUEGO ##########

    def introduccion(self):
        while self.running:
            if not self.running:
                break

            QApplication.processEvents()

            self.fecha = datetime.now().strftime("%d-%m-%Y")
            self.hora = datetime.now().strftime("%H:%M:%S")

            self.emotionalmotor_proxy.expressJoy()

            self.speech_proxy.say(f"Hola {self.nombre}, vamos a jugar al Veo Veo.", False)
            print(f"EBO: Hola {self.nombre}, vamos a jugar al Veo Veo.")
            self.speech_proxy.say("En este juego tendrás que enseñar a la cámara la tarjeta que te vaya pidiendo.",
                                  False)
            print("EBO: En este juego tendrás que enseñar a la cámara la tarjeta que te vaya pidiendo.")
            self.speech_proxy.say("¿Quieres que te explique el juego?", False)
            print("EBO: ¿Quieres que te explique el juego?")
            self.terminaHablar()

            # La pantalla se muestra ANTES de hablar: no debe existir ningún
            # momento sin interfaz a la vista.
            self.check = ""
            self.ui3.show()
            self.ui3.exec_()

            if self.check == "si":
                self.speech_proxy.say("Primero escucharás una pista. Después tendrás que enseñar la tarjeta correspondiente a la cámara.", False)
                print("EBO: Primero escucharás una pista. Después tendrás que enseñar la tarjeta correspondiente a la cámara.")
                self.speech_proxy.say("EBO intentará reconocer la tarjeta y decir si la respuesta ha sido correcta o incorrecta.", False)
                print("EBO: EBO intentará reconocer la tarjeta y decir si la respuesta ha sido correcta o incorrecta.")
                self.speech_proxy.say("El juego termina cuando se completen todas las rondas seleccionadas.", False)
                print("EBO: El juego termina cuando se completen todas las rondas seleccionadas.")
            else:
                # Incluye el caso de cerrar el diálogo sin responder.
                self.speech_proxy.say("Perfecto. Escucha bien la pista y enseña la tarjeta correspondiente.", False)
                print("EBO: Perfecto. Escucha bien la pista y enseña la tarjeta correspondiente.")
                self.speech_proxy.say("¡Comencemos con el juego!", False)
                print("EBO: ¡Comencemos con el juego!")

            self.terminaHablar()
            self.ui4.show()
            self.ui4.exec_()
            self.juego()

    def juego(self):
        # Un archivo de tarjetas mal formado no debe tumbar la sesión.
        try:
            self.archivo(self.bd)
        except Exception as e:
            print(f"No se pudieron leer las tarjetas de {self.categoria}: {e}")
            print("EBO: No he podido cargar las tarjetas de esta categoría.")
            self.gestorsg_proxy.LanzarApp()
            return

        self.start_time = time.time()

        if self.modelo_vlm is None:
            print("Cargando el modelo de visión, un momento...")
            self.cargar_modelo_vlm()

        ronda = 0

        while ronda < self.numero_rondas and self.running:
            if len(self.objetivos) == 0:
                print("No hay tarjetas cargadas.")
                break

            if len(self.tarjetas_usadas) == len(self.objetivos):
                self.tarjetas_usadas = []

            indice = random.randint(0, len(self.objetivos) - 1)

            while indice in self.tarjetas_usadas:
                indice = random.randint(0, len(self.objetivos) - 1)

            self.tarjetas_usadas.append(indice)

            self.ronda_actual = ronda + 1
            self.objetivo_actual = self.objetivos[indice]
            self.pista_actual = self.pistas[indice]

            self.resp = ""
            self.ebo_detecta_objeto = False
            self.prediccion_vlm = "-"
            self.score_vlm = 0.0
            self.sin_camara_avisado = False

            print(f"--- Ronda {self.ronda_actual}/{self.numero_rondas} ---")
            print(f"Tarjeta a buscar: {self.objetivo_actual}")



            self.speech_proxy.say("Veo veo.", False)
            print("EBO: Veo veo.")
            self.speech_proxy.say(self.pista_actual, False)
            print(f"EBO: {self.pista_actual}")
            self.terminaHablar()


            self.start_question_time = time.time()

            # Margen para que el usuario busque la tarjeta y la ponga delante antes de la primera captura. S
            margen = time.time() + self.margen_tarjeta

            while self.resp == "" and time.time() < margen:
                QApplication.processEvents()
                sleep(0.05)

            self.speech_proxy.say("Es tu turno. Enseñame la tarjeta", False)
            print("Es tu turno. Enseñame la tarjeta.")
            self.terminaHablar()

            self.analizar_ronda_vlm()

            self.respuesta()

            QApplication.processEvents()

            self.end_question_time = time.time()
            self.response_time = self.end_question_time - self.start_question_time
            self.responses_times.append(self.response_time)


            self.resultados_objetivos.append(self.objetivo_actual)
            self.resultados_terapeuta.append(self.resp)
            self.resultados_scores_vlm.append(round(self.score_vlm, 4))
            self.resultados_tiempos.append(round(self.response_time, 2))



            ronda += 1

        self.end_time = time.time()
        self.elapsed_time = self.end_time - self.start_time
        self.media = (sum(self.responses_times) / len(self.responses_times)) if self.responses_times else 0.0

        QApplication.processEvents()

        self.speech_proxy.say("Fin del juego. Lo has hecho genial.", False)
        print("EBO: Fin del juego. Lo has hecho genial.")
        self.terminaHablar()

        print(f"Fin de la partida: {self.aciertos} aciertos, {self.fallos} fallos")

        self.running = False

        self.guardar_resultados()
        self.reiniciar_variables()
        self.gestorsg_proxy.LanzarApp()

    def repetir_pista(self, pista):
        self.resp = ""
        self.speech_proxy.say("Atención, voy a repetirte la pista.", False)
        self.speech_proxy.say(pista, False)
        self.speech_proxy.say("Tu turno. Muestrame la tarjeta.", False)
        self.terminaHablar()
        margen = time.time() + self.margen_tarjeta
        while self.resp == "" and time.time() < margen:
            QApplication.processEvents()
            sleep(0.05)
        self.analizar_ronda_vlm()
        self.respuesta()


    def respuesta (self):
        self.resp = ""
        self.ui.respuesta_EBO.clear()
        self.ui.respuesta_EBO.insertPlainText("SI" if self.ebo_detecta_objeto else "NO")

        self.ui.respuesta.clear()
        self.ui.respuesta.insertPlainText(self.objetivo_actual)

        self.ui.show()
        while self.ui.isVisible() and self.resp == "":
            QApplication.processEvents()
            sleep(0.05)
        if self.resp == "si":
            self.aciertos += 1
            frase = random.choice(self.bateria_aciertos)
            self.speech_proxy.say(frase, False)
            print(f"EBO: {frase}")
            self.set_all_LEDS_colors(0, 255, 0)
            self.emotionalmotor_proxy.expressJoy()
            sleep(1)
            self.set_all_LEDS_colors(0, 0, 0)
            sleep(1)
            self.emotionalmotor_proxy.expressJoy()

        elif self.resp == "no":
            self.fallos += 1
            frase = random.choice(self.bateria_fallos)
            self.speech_proxy.say(frase, False)
            print(f"EBO: {frase}")
            self.set_all_LEDS_colors(255, 0, 0)
            self.emotionalmotor_proxy.expressSadness()
            sleep(1)
            self.set_all_LEDS_colors(0, 0, 0)
            sleep(1)
            self.emotionalmotor_proxy.expressJoy()
        elif self.resp == "repetir":
            self.cerrar_ui(1)
            self.repetir_pista(self.pista_actual)


        self.cerrar_ui(1)

     ########## FUNCIÓN QUE GUARDA LOS RESULTADOS DEL JUEGO ##########

    def guardar_resultados(self):
        archivo = os.path.abspath(os.path.join(BASE_DIR, "../resultados_veoveo.json"))

        if not self.resultados_objetivos:
            print("No se ha completado ninguna ronda: no se guardan resultados.")
            return

        resultado_partida = {
            "Nombre": self.nombre,
            "Categoria": self.categoria,
            "Objetivo": self.resultados_objetivos,
            "Respuesta terapeuta": self.resultados_terapeuta,
            "Score VLM": self.resultados_scores_vlm,
            "Fecha": self.fecha,
            "Hora": self.hora,
            "Aciertos": self.aciertos,
            "Fallos": self.fallos,
            "Tiempo de respuesta (seg)": self.resultados_tiempos,
            "Tiempo de respuesta medio (seg)": round(self.media, 2)
        }
        self.df = pd.DataFrame([resultado_partida])

        datos_existentes = pd.DataFrame()

        if os.path.exists(archivo):
            try:
                datos_existentes = pd.read_json(archivo, orient='records', lines=True)

                if not set(resultado_partida.keys()).issubset(datos_existentes.columns):
                    print("El histórico usaba el formato antiguo: se reemplaza.")
                    datos_existentes = pd.DataFrame()
            except ValueError:
                print("El histórico tenía un formato inválido: se sobrescribe.")

        if not datos_existentes.empty:
            self.df = pd.concat([datos_existentes, self.df], ignore_index=True)

        self.df.to_json(archivo, orient='records', lines=True, force_ascii=False)
        print(f"Resultados guardados en {archivo}")



    def __del__(self):
        """Destructor"""


    @QtCore.Slot()
    def compute(self):

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
    # IMPLEMENTATION of StartGame method from JuegoVeoVeo interface
    #
    def JuegoVeoVeo_StartGame(self):
        print("Iniciando Veo Veo...")
        self.set_all_LEDS_colors(0,0,0,255)
        self.boton = False
        self.update_ui_signal.emit()
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


