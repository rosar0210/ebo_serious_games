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
from fcntl import F_ADD_SEALS

from PySide6.QtCore import QTimer, Qt, QFile, Signal, Slot, QEvent
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtGui import QPixmap
from rich.console import Console
from genericworker import *
import interfaces as ifaces
import numpy as np
import cv2
import mediapipe as mp
import pandas as pd
import random
import time
from time import sleep
from datetime import datetime
from PySide6 import QtUiTools

import sys
import os

os.environ['GLOG_minloglevel'] = '2'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['QT_LOGGING_RULES'] = '*.warning=false'

sys.path.append('/opt/robocomp/lib')
console = Console(highlight=False)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IGS_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "igs"))

UI_MENU = "../../igs/mirror_menu.ui"
UI_START = "../../igs/comenzarUI.ui"
UI_CALIB = "../../igs/calibracion.ui"
UI_RESP = "../../igs/mimica_respuesta.ui"
UI_CAMERA = "../../igs/camera.ui"


LOGO_1      = "../../igs/logos/logo_euro.png"
LOGO_2      = "../../igs/logos/robolab.png"


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

        self.NUM_LEDS = 54

        self.imagen = None
        self.landmarker = None


        self.imag_final = None

        self.ratio_bocaa_ref = None
        self.ratio_bocaa = None
        self.ratio_boca_ref = None
        self.ratio_boca = None
        self.ratio_ojos_ref = None
        self.ratio_ojos = None
        self.ratio_cejas_ref = None
        self.ratio_cejas = None
        self.ceja_triste = None
        self.ratio_tristeza_ref = None
        self.ratio_tristeza = None
        self.calibrado = False
        self.calib = False
        self.detectada = True
        self.blendshapes_base = {}
        self.umbrales = {}

        self.mood_aleatorio = []
        self.respuesta = []

        self.running = False
        self.nombre = ""
        self.modo_juego = "usuario_imita"
        self.rondas = 0
        self.intentos = 0
        self.fallos = 0
        self.rondas_complet = 0
        self.responses_times = []
        self.start_time= None
        self.df = pd.DataFrame(columns=[
            "Nombre", "Intentos", "Rondas", "Modo Juego", "Dificultad", "Fecha", "Hora",
            "Rondas completadas", "Fallos", "Emociones jugadas (Detección)","Tiempo transcurrido (min)", "Tiempo transcurrido (seg)",
            "Tiempo medio respuesta (seg):"
        ])


        self.ui = self.therapist_ui()
        self.ui2 = self.comenzar_checked()
        self.ui3 = self.calibracion_checked()
        self.ui4 = self.respuesta_ui()
        self.ui5 = self.camera_ui()

        self.reiniciar_variables()

        # Si SpecificWorker es un Widget, lo ocultamos para que solo se vea tu UI cargada.
        if isinstance(self, QWidget):
            self.hide()

        if QApplication.instance():
            QApplication.instance().setQuitOnLastWindowClosed(False)

        self.update_ui_signal.connect(self.handle_update_ui)

        ########## BATERÍA DE RESPUESTAS ##########
        self.bateria_responder = [
            "Responde ahora!",
            "Te toca responder!",
            "Es tu turno, adelante!",
            "Vamos, responde ya!",
            "Es tu momento, responde ahora!",
            "¡Adelante, es tu turno!",
            "¡Responde con confianza!",
            "¡Vamos, tú puedes responder ahora!"
        ]

        self.bateria_aciertos = [
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
            "Fallo, pero no te preocupes!",
            "No pasa nada, todos fallamos!",
            "Sigue intentándolo, ¡lo harás mejor!",
            "Es un error, pero no te rindas!",
            "¡Ánimo, la próxima será mejor!",
            "¡No te preocupes, sigue adelante!",
            "¡Un tropiezo no define tu esfuerzo!",
            "¡No pasa nada, la práctica hace al maestro!"
        ]

        self.bateria_rondas = [
            "Es hora de la ronda número {ronda}!",
            "¡Ronda número {ronda}, vamos allá!",
            "¡Toca la ronda número {ronda}!",
            "Preparados para la ronda número {ronda}!",
            "Comienza la ronda número {ronda}, ¡suerte!",
            "¡Atentos, comienza la ronda {ronda}!",
            "¡Vamos con la emocionante ronda número {ronda}!",
            "¡Que comience la ronda número {ronda}, mucha suerte!"
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
        self.bateria_contento = [
            "¡Intenta sonreír un poco más!",
            "Sube bien las comisuras y enseña los dientes."
            "Imagina que viene a verte tu familiar favorito."
        ]

        self.bateria_enfadado = [
            "Frunce bien el ceño.",
            "Imagina que te han quitado tu postre favorito.",
            "¡Intenta juntar las cejas!"
        ]

        self.bateria_sorprendido = [
            "Abre la boca como si vieras un extraterrestre",
            "¡Imagina que te toca la lotería de repente!"
            "Intenta abrir la boca como diciendo la letra o"
        ]

        self.bateria_tristeza = {
            "¡Pon cara de pena!",
            "Baja las comisuras de los labios como si estuvieras haciendo pucheros",
            "Imagina que se ha acabado su fiesta preferia"
        }

    def __del__(self):
        """Destructor"""
        cv2.destroyAllWindows()



    @QtCore.Slot()
    def compute(self):

        return True

    def startup_check(self):
        print(f"Testing RoboCompCameraSimple.TImage from ifaces.RoboCompCameraSimple")
        test = ifaces.RoboCompCameraSimple.TImage()
        print(f"Testing RoboCompLEDArray.Pixel from ifaces.RoboCompLEDArray")
        test = ifaces.RoboCompLEDArray.Pixel()
        QTimer.singleShot(200, QApplication.instance().quit)

    def elegir_respuesta(self, bateria, **kwargs):
        if "ronda" in kwargs:
            # Si el kwargs contiene 'ronda', formatea las respuestas de las rondas
            bateria = [respuesta.format(ronda=kwargs["ronda"]) if "ronda" in respuesta else respuesta for respuesta in
                       bateria]
        return random.choice(bateria)


    # =============== Methods for Component Implements ==================
    # ===================================================================

    #
    # IMPLEMENTATION of StartGame method from JuegoMirror interface
    #
    def JuegoMirror_StartGame(self):
        print("\n>>> [PASO 1] Petición de inicio recibida desde la App Principal.")
        self.set_all_LEDS_colors(0, 0, 0, 255)
        self.update_ui_signal.emit()
        pass

    def iniciar_modelo(self):
        # Inicialización módulo de malla facial
        if getattr(self, 'landmarker', None) is None:
            print("Cargando modelo de reconocimiento facial...")
            modelo_path = os.path.join(os.path.dirname(__file__), 'face_landmarker.task')
            options = mp.tasks.vision.FaceLandmarkerOptions(
                base_options=mp.tasks.BaseOptions(model_asset_path=modelo_path),
                running_mode=mp.tasks.vision.RunningMode.IMAGE,
                output_face_blendshapes=True
            )
            self.landmarker = mp.tasks.vision.FaceLandmarker.create_from_options(options)

    def captura_imagen(self):
        "Captura la imagen y devuelve los puntos necesarios"
        #Captura y extracción de dimensiones de la imagen
        self.iniciar_modelo()

        self.imag = self.camerasimple_proxy.getImage()
        self.ancho = self.imag.width
        self.alto = self.imag.height

        #Conversión a binario y RGB para usar OpenCV
        self.imagen = np.frombuffer(self.imag.image, dtype=np.uint8).reshape((self.alto, self.ancho, 3))
        self.imagen_rgb = cv2.cvtColor(self.imagen, cv2.COLOR_BGR2RGB)

        self.imagen_rgb = cv2.flip(self.imagen_rgb, 0)

        #Mostrar imagen
        # cv2.imshow("Camara RoboComp - Juego Mirror", self.imagen)
        # cv2.waitKey(20)
        # ------------------------------------------
        self.mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=self.imagen_rgb)

        #Procesado de la imagen
        self.imag_final = self.landmarker.detect(self.mp_image)

        imagen_debug = self.imagen.copy()

        #Mostrar valores de referencia una vez calibrado
        if self.calibrado:
            txt_ref = f"REF: BocaA: {self.ratio_bocaa_ref:.3f}, OjosW: {self.ratio_ojos_ref:.3f}"
            cv2.putText(imagen_debug, txt_ref, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

        puntos = None

        if self.imag_final.face_blendshapes:
            self.detectada = True
            puntos = {b.category_name: b.score for b in self.imag_final.face_blendshapes[0]}
            # Extraemos los valores actuales exactos que nos interesan
            boca_abierta_actual = puntos.get('jawOpen', 0.0)
            ojos_anchos_actual = (puntos.get('eyeWideLeft', 0.0) + puntos.get('eyeWideRight', 0.0)) / 2

            # Dibujamos los valores actuales sobre la imagen
            txt_boca = f"BocaOpen (%): {boca_abierta_actual*100:.3f}"
            txt_ojos = f"EyeWide (%): {ojos_anchos_actual*100:.3f}"

            # Mostrar imagen con depuración visual
            # cv2.imshow("Camara en vivo", cv2.flip(imagen_debug, 0))
            cv2.putText(imagen_debug, txt_boca, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0),  2)
            cv2.putText(imagen_debug, txt_ojos, (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            # cv2.waitKey(20)

            # return puntos
        else:
            # cv2.imshow("No se detecta cara", cv2.flip(imagen_debug, 0))
            self.detectada = False
            cv2.putText(imagen_debug, "NO SE DETECTA CARA", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
            cv2.waitKey(20)
            # return None

        #Envío de la imagen a la UI
        # imagen_debug = cv2.flip(imagen_debug, 0)
        imagen_visor = cv2.cvtColor(imagen_debug, cv2.COLOR_BGR2RGB)

        #Conversión de píxeles a formato QT
        h, w, ch = imagen_visor.shape
        bytes = ch * w
        img_qt = QImage(imagen_visor.data, w, h, bytes, QImage.Format_RGB888)

        if hasattr(self, 'ui5'):
            self.ui5.camera.setScaledContents(True)
            self.ui5.camera.setPixmap(QPixmap.fromImage(img_qt))

            if not self.ui5.isVisible():
                self.ui5.show()
                self.ui5.raise_()

            self.ui5.camera.repaint()
            QApplication.processEvents()

        return puntos

    def calibracion (self):
        "Captura la cara con emoción neutra para tener valores de referencia"
        puntos = self.captura_imagen()
        if puntos:
            self.ratio_bocaa_ref = puntos.get('jawOpen', 0.0)
            self.ratio_boca_ref = (puntos.get('mouthSmileLeft', 0.0) + puntos.get('mouthSmileRight',0.0)) / 2
            self.ratio_ojos_ref = (puntos.get('eyeWideLeft', 0.0) + puntos.get('eyeWideRight', 0.0)) / 2
            self.ratio_cejas_ref = (puntos.get('browDownLeft', 0.0) + puntos.get('browDownRight', 0.0)) / 2
            self.ratio_tristeza_ref = (puntos.get('mouthFrownLeft', 0.0) + puntos.get('mouthFrownRight', 0.0)) / 2

            self.calibrado = True
            print("Calibración completada con éxito.")
            return True
        return False

    def sorprendido(self, imag_actual):
        if imag_actual is None: return False

        # Extraemos los valores del diccionario recibido
        self.ratio_bocaa = imag_actual.get('jawOpen', 0.0)
        self.ratio_ojos = (imag_actual.get('eyeWideLeft', 0.0) + imag_actual.get('eyeWideRight', 0.0)) / 2

        boca_abierta = self.ratio_bocaa > (self.ratio_bocaa_ref+self.umbrales["sorprendidov1"])
        ojos_abiertos = self.ratio_ojos > (self.ratio_ojos_ref + self.umbrales["sorprendidov1"])

        # Si la boca está más abierta que en el reposo y los ojos más abiertos
        if (boca_abierta and ojos_abiertos) or self.ratio_bocaa > self.umbrales["sorprendidov2"]:
            return True
        return False

    def contento(self, imag_actual):
        if imag_actual is None: return False

        self.ratio_boca = (imag_actual.get('mouthSmileLeft', 0.0) + imag_actual.get('mouthSmileRight', 0.0)) / 2

        if self.ratio_boca > (self.ratio_boca_ref + self.umbrales["contentov1"]) or self.ratio_boca > self.umbrales["contentov2"]:
            return True
        return False

    def enfadado(self, imag_actual):
        if imag_actual is None: return False

        self.ratio_cejas = (imag_actual.get('browDownLeft', 0.0) + imag_actual.get('browDownRight', 0.0)) / 2

        cejas_ira = self.ratio_cejas > (self.ratio_cejas_ref+self.umbrales["enfadado"])

        if cejas_ira:
            return True
        return False

    def triste (self, imag_actual):
        if imag_actual is None: return False

        self.ratio_tristeza = (imag_actual.get('mouthFrownLeft', 0.0) + imag_actual.get('mouthFrownRight', 0.0)) / 2
        self.ceja_triste = imag_actual.get('browInnerUp', 0.0)

        if self.ratio_tristeza > (self.ratio_tristeza_ref + self.umbrales["tristev1"]) or self.ceja_triste > (self.ratio_cejas_ref + self.umbrales["tristev2"]):
            return True
        return False

    # def asco (self, imag_actual):
    #     if imag_actual is None: return False
    #
    #     lengua_fuera = imag_actual.get('tongueOut', 0.0)
    #     nariz_arrugada = (imag_actual.get('noseSneerLeft', 0.0) + imag_actual.get('noseSneerRight', 0.0)) / 2
    #
    #     if lengua_fuera > 0.2 or nariz_arrugada > 0.15:
    #         return True
    #     return False


################################ FLUJO DEL JUEGO ############################################
    def introduccion  (self):

        self.ebomoods_proxy.expressJoy()
        self.speech_proxy.say(f"Hola {self.nombre}, vamos a jugar a la mímica de emociones.", False)
        print(f"Hola {self.nombre}, vamos a jugar a la mímica de emociones.")
        self.terminaHablar()

        self.speech_proxy.say("Antes de nada, vamos a calibrar la cámara. Pon cara neutra y relajada y mira a la cámara.", False)
        print("Antes de nada, vamos a calibrar la cámara. Pon cara neutra y relajada y mira a la cámara.")
        self.terminaHablar()

        while not self.calibrado:
            self.ui3.show()
            self.ui5.show()
            self.captura_imagen()
            QApplication.processEvents()
            cv2.waitKey(40)

            if not self.boton:
                return

        if self.calibrado:
            self.speech_proxy.say("En este juego yo pondré una cara y tú tendrás que imitarla. "
                    "Prepárate para poner tu mejor cara.", False)
            print("En este juego yo pondré una cara y tú tendrás que imitarla. Prepárate para poner tu mejor cara.")
            self.terminaHablar()
            self.ui2.show()
            self.ui2.exec()

        if self.running:
            self.usuario_imita()

        # if self.modo_juego == "usuario_imita":
        #     self.speech_proxy.say("En este juego yo pondré una cara y tú tendrás que imitarla. "
        #         "Prepárate para poner tu mejor cara.", False)
        #     print("En este juego yo pondré una cara y tú tendrás que imitarla. Prepárate para poner tu mejor cara.")
        #     self.terminaHablar()
        #     self.usuario_imita()
        # else:
        #     self.speech_proxy.say("En este juego tú pondrás una cara y yo intentaré imitarte. "
        #         "Vamos a ver lo bien que te leo.", False)
        #     print("En este juego tú pondrás una cara y yo intentaré imitarte. Vamos a ver lo bien que te leo.")
        #     self.terminaHablar()
        #     self.robot_imita()

    def usuario_imita(self):
        self.mood_aleatorio= []
        i = 0

        while i < int(self.rondas) and self.running:
            self.speech_proxy.say(self.elegir_respuesta(self.bateria_rondas, rondas = i+1), False)
            print(f"Ronda número {i+1}.")
            self.rondas_complet = i +1
            self.terminaHablar()

            mood = self.random_mood()
            print(self.mood_aleatorio)
            self.mostrar_emocion(mood)
            sleep(1)

            self.start_answer_time = None

            self.get_respuesta(mood)

            if not self.running:
                break

            print(f"La respuesta ha sido: {self.respuesta}")
            i+= 1

            if i == int(self.rondas):
                self.finJuego()

    def set_dificultad(self):
        if self.dificultad == "facil":
            self.umbrales = {
                "contentov1" : 0.05,
                "contentov2" : 0.06,
                "enfadado": 0.001,
                "tristev1": 0.48,
                "tristev2": 0.64,
                "sorprendidov1": 0.07,
                "sorprendidov2": 0.1
            }
        elif self.dificultad == "medio":
            self.umbrales = {
                "contentov1": 0.07,
                "contentov2": 0.04,
                "enfadado": 0.002,
                "tristev1": 0.96,
                "tristev2": 0.128,
                "sorprendidov1": 0.1,
                "sorprendidov2": 0.15
            }
        elif self.dificultad == "dificil":
            self.umbrales = {
                "contentov1": 0.09,
                "contentov2": 0.12,
                "enfadado": 0.003,
                "tristev1": 1.44,
                "tristev2": 1.92,
                "sorprendidov1": 0.13,
                "sorprendidov2": 0.2
            }

    def finJuego(self):
        self.end_time = time.time()
        self.elapsed_time = self.end_time - self.start_time

        minutes = int(self.elapsed_time // 60)
        seconds = int(self.elapsed_time % 60)

        self.speech_proxy.say(self.elegir_respuesta(self.bateria_fin_juego), False)
        print("Juego terminado")
        self.terminaHablar()
        if len(self.responses_times) > 0:
            self.media = sum(self.responses_times) / len(self.responses_times)
        else:
            self.media = 0.0

        self.agregar_resultados(self.nombre, self.intentos, self.rondas, self.modo_juego, self.dificultad, self.fecha, self.hora, self.rondas_complet, self.fallos, self.historial, minutes, seconds, self.media)
        self.guardar_resultados()
        self.running = False
        cv2.destroyAllWindows()
        self.gestorsg_proxy.LanzarApp()
        return

    def get_respuesta(self, mood):
        self.imita = False
        self.intent = 0

        if self.start_answer_time is None:
            self.start_answer_time = time.time()

        print(f"Imitación de {mood}")

        while self.running and not self.imita:
            self.speech_proxy.say(self.elegir_respuesta(self.bateria_responder), False)
            print("Turno del usuario")
            self.set_all_LEDS_colors(0,0,0,0)
            self.terminaHablar()

            detectado = self.detectar_emocion(mood)


            if detectado:
                texto = "Sí"
            elif not detectado:
                texto = "No"
            else:
                texto = "Repitiendo"

            self.resultado_terapeuta = None
            #Mostrar la UI de respuesta
            self.mostrar_ui_respuesta(mood, texto)
            self.esperando_validacion = True

            #Evaluación en tiempo real mientras el terapeuta decide
            while self.esperando_validacion and self.running:
                QApplication.processEvents()
                cv2.waitKey(20)

            #Si cerramos el juego forzosamente
            if not self.running:
                return

            if self.resultado_terapeuta is not None and self.resultado_terapeuta != "Repitiendo":
                registro = f"{mood}({str(detectado).lower()})"
                self.historial.append(registro)


            #Respuesta del terapeuta tras pulsar botón
            if self.resultado_terapeuta:
                self.imita = True
                self.respuesta.append(mood)
                self.responses_times.append(time.time() - self.start_answer_time)
                self.speech_proxy.say(self.elegir_respuesta(self.bateria_aciertos), False)
                print(f"Emocion {mood} detectada y validada")
                self.terminaHablar()
            elif self.resultado_terapeuta is False:
                self.intent += 1
                self.restantes = int(self.intentos) - int(self.intent)
                self.speech_proxy.say(f"{self.elegir_respuesta(self.bateria_fallos)} Te quedan {self.restantes} intentos", False)
                print(f"Te quedan {self.restantes} intentos.")
                self.terminaHablar()
                self.fallos += 1

                if self.restantes <= 0:
                    self.game_over()
                    return

                self.repetir_mood()
                sleep(1)
            elif self.resultado_terapeuta == "Repitiendo":
                print("El terapeuta ha decidido repetir la emoción.")
                self.speech_proxy.say("Vamos a repetirlo para que lo veas bien.", False)
                self.terminaHablar()

                self.repetir_mood()
                sleep(1)

    def detectar_emocion(self, emocion):
        self.aciertos = 0
        self.necesarios = 20
        i = 0

        while i <= 70 and self.running:
            imag = self.captura_imagen()
            self.ui5.show()
            if self.detectada:
                i += 1

            if emocion == "alegría" and self.contento(imag):
                self.aciertos += 1
            elif emocion == "ira" and self.enfadado(imag):
                self.aciertos += 1
            elif emocion == "sorpresa" and self.sorprendido(imag):
                self.aciertos += 1
            elif emocion== "tristeza" and self.triste(imag):
                self.aciertos += 1
            # elif emocion == "asco" and self.asco(imag):
            #     self.aciertos += 1

            if self.aciertos >= self.necesarios:
                self.cerrar_ui(5)
                return True

            QApplication.processEvents()
            cv2.waitKey(50)

        self.cerrar_ui(5)
        return False

    def repetir_mood(self):
        self.ebomoods_proxy.expressJoy()
        print("Mostrando emoción nuevamente...")
        self.speech_proxy.say("Atención, voy a mostrarte de nuevo la emoción", False)
        self.terminaHablar()
        if self.mood_aleatorio == "alegría":
            self.speech_proxy.say(self.elegir_respuesta(self.bateria_contento),False)
        elif self.mood_aleatorio == "sorpresa":
            self.speech_proxy.say(self.elegir_respuesta(self.bateria_sorprendido),False)
        elif self.mood_aleatorio == "tristeza":
            self.speech_proxy.say(self.elegir_respuesta(self.bateria_tristeza),False)
        elif self.mood_aleatorio == "ira":
            self.speech_proxy.say(self.elegir_respuesta(self.bateria_enfadado),False)
        print(self.mood_aleatorio)
        self.mostrar_emocion(self.mood_aleatorio[-1])

    def game_over(self):
        self.end_time = time.time()
        self.elapsed_time = self.end_time - self.start_time

        if len(self.responses_times) > 0:
            self.media = (sum(self.responses_times)/len(self.responses_times))
        else:
            self.media = 0.0
        minutes = int(self.elapsed_time // 60)
        seconds = int(self.elapsed_time % 60)
        rondas = int(self.rondas_complet) - 1
        print("Game Over")
        self.speech_proxy.say(self.elegir_respuesta(self.bateria_fin_juego), False)
        print(f"Juego terminado. Tiempo transcurrido: {minutes} minutos y {seconds} segundos.")
        self.terminaHablar()
        self.running = False
        self.agregar_resultados(self.nombre, self.intentos, self.rondas, self.modo_juego, self.dificultad, self.fecha, self.hora, self.rondas_complet, self.fallos, self.historial, minutes, seconds, self.media)
        self.guardar_resultados()
        cv2.destroyAllWindows()
        self.gestorsg_proxy.LanzarApp()


    def terminaHablar(self):
        sleep(2.5)
        while self.speech_proxy.isBusy():
            pass
        ########## FUNCIÓN QUE GENERA LA SECUENCIA DE EMOCIONES  ##########

    def random_mood(self):
        mood = random.choice(["alegría", "ira", "sorpresa", "tristeza"])
        # Comprobar si el último color es el mismo que el nuevo
        while self.mood_aleatorio and self.mood_aleatorio[-1] == mood:
            mood = random.choice(["alegría", "ira", "sorpresa", "tristeza"])
        self.mood_aleatorio.append(mood)
        return mood

    def mostrar_emocion (self, emocion):
        self.emotionalmotor_proxy.expressJoy()
        self.set_all_LEDS_colors(red=0, green=0, blue=0, white=0)
        sleep(2)
        if isinstance(emocion, list):
            emocion = emocion[0]
        print (f"EBO expresando {emocion}")

        if emocion == "alegría":
            self.ebomoods_proxy.expressJoy()
        elif emocion == "ira":
            self.ebomoods_proxy.expressAnger()
        elif emocion == "sorpresa":
            self.ebomoods_proxy.expressSurprise()
        elif emocion == "tristeza":
            self.ebomoods_proxy.expressSadness()
        # elif emocion == "asco":
        #     self.ebomoods_proxy.expressDisgust()

        sleep(2.5)

    def set_all_LEDS_colors(self, red=0, green=0, blue=0, white=0):
        pixel_array = {i: ifaces.RoboCompLEDArray.Pixel(red=red, green=green, blue=blue, white=white) for i in
                       range(self.NUM_LEDS)}
        self.ledarray_proxy.setLEDArray(pixel_array)

##################################### GUARDAR RESULTADOS ###############################################################
    def agregar_resultados(self, nombre, intentos, rondas, modo_juego, dificultad, fecha, hora, rondas_completadas, fallos, historial,
                           tiempo_transcurrido_min, tiempo_transcurrido_seg, tiempo_medio_respuesta):

        # Crea un diccionario con los datos nuevos
        nuevo_resultado = {
            "Nombre": nombre,
            "Intentos": intentos,
            "Rondas": rondas,
            "Modo Juego": modo_juego,
            "Dificultad": dificultad,
            "Fecha": fecha,
            "Hora": hora,
            "Rondas completadas": rondas_completadas,
            "Fallos": fallos,
            "Emociones jugadas (Detección)": str(historial),
            "Tiempo transcurrido (min)": tiempo_transcurrido_min,
            "Tiempo transcurrido (seg)": tiempo_transcurrido_seg,
            "Tiempo medio respuesta (seg):": tiempo_medio_respuesta

        }

        # Convierte el diccionario en un DataFrame de una fila
        nuevo_df = pd.DataFrame([nuevo_resultado])

        # Agrega la nueva fila al DataFrame existente
        self.df = pd.concat([self.df, nuevo_df], ignore_index=True)

    def guardar_resultados(self):
        archivo = "resultados_mirror.json"
        # Inicializar un DataFrame vacío para los datos existentes
        datos_existentes = pd.DataFrame()
        # Intentar leer el archivo existente si existe
        if os.path.exists(archivo):
            try:
                datos_existentes = pd.read_json(archivo, orient='records', lines=True)
            except ValueError:
                print("El archivo JSON existente tiene un formato inválido o está vacío. Sobrescribiendo el archivo.")

        # Verificar que el DataFrame actual no esté vacío
        if self.df.empty:
            print("El DataFrame de nuevos resultados está vacío. No se guardará nada.")
            return

        # Concatenar los datos existentes con los nuevos (si existen)
        if not datos_existentes.empty:
            self.df = pd.concat([datos_existentes, self.df], ignore_index=True)

        # Eliminar duplicados basados en todas las columnas
        self.df = self.df.drop_duplicates()
        # Guardar el DataFrame combinado en formato JSON
        self.df.to_json(archivo, orient='records', lines=True)
        print(f"Resultados guardados correctamente en {archivo}")
        # Leer y mostrar el archivo actualizado para verificar
        df_resultados = pd.read_json(archivo, orient='records', lines=True)
        print(df_resultados)
        # Reiniciar la variable self.df para la próxima partida
        self.reiniciar_variables()
        print("Variable self.df reiniciada para la próxima partida.")

    def reiniciar_variables(self):
        self.nombre = ""
        self.modo_juego = "usuario_imita"
        self.calibrado = False
        self.intentos = 0
        self.running = False
        self.respuesta = []
        self.rondas = 0
        self.historial = []

        self.boton = False
        self.reiniciar = False
        self.gameOver = False
        self.start_time = None
        self.end_time = None
        self.elapsed_time = None

        self.rondas_complet = 0
        self.fecha = 0
        self.hora = 0
        self.fallos = 0

        self.start_question_time = None
        self.end_question_time = 0
        self.response_time = 0
        self.responses_times = []
        self.media = 0

        self.dificultad = None
        self.start_question_time = None
        self.esperando_validacion = False
        self.resultado_terapeuta = None
        self.imita = False
        self.intent = 0
        self.restantes = 0

        self.df = pd.DataFrame(columns=[
            "Nombre", "Intentos", "Rondas", "Modo Juego", "Dificultad", "Fecha", "Hora",
            "Rondas completadas", "Fallos", "Emociones jugadas (Detección)", "Tiempo transcurrido (min)", "Tiempo transcurrido (seg)",
            "Tiempo medio respuesta (seg):"
        ])


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

    def therapist_ui(self):
        # UI 1: menú (terapeuta)
        ui = self.load_ui_generic(
            UI_MENU, ui_number=1,
            logo_paths={"label": LOGO_1, "label_3": LOGO_2},
            botones={
                "facil": self.facil_clicked,
                "medio": self.medio_clicked,
                "dificil": self.dificil_clicked,
                "confirmar_button": self.therapist,
            },
            ayuda_button="ayuda_button",
            back_button="back_button",
            after_load=lambda u: (hasattr(u, "ayuda") and u.ayuda.hide())
        )
        return ui

    def facil_clicked(self):
        self.dificultad = "facil"
        self.ui.dificultad_elegida.setText("Dificultad elegida: Fácil")
        print("Dificultad elegida: Fácil")

    def medio_clicked(self):
        self.dificultad = "medio"
        self.ui.dificultad_elegida.setText("Dificultad elegida: Medio")
        print("Dificultad seleccionada: Medio")

    def dificil_clicked(self):
        self.dificultad = "dificil"
        self.ui.dificultad_elegida.setText("Dificultad elegida: Difícil")
        print("Dificultad seleccionada: Difícil")

    def calibracion_clicked(self):
        calibrado = self.calibracion()


        if calibrado:
            print("Calibración existosa")
            self.ui3.accept()
            self.cerrar_ui(5)
            self.cerrar_ui(3)
        else:
            print("No se detecto la cara. Intentalo de nuevo.")
            self.speech_proxy.say("No he podido detectar tu cara. Recuerda, mira a la cámara con expresión neutra y relajada.", False)

    def therapist(self):
            # Obtiene los valores ingresados en los campos
            self.nombre = self.ui.usuario.toPlainText()
            self.intentos = self.ui.intentos.toPlainText()
            self.rondas = self.ui.rondas.toPlainText()
            # Validaciones simples
            if not self.nombre:
                print("Por favor ingresa un nombre de usuario.")
                return
            if not self.intentos.isdigit() or int(self.intentos) <= 0:
                print("Por favor ingresa un número válido de intentos.")
                return
            if not self.rondas.isdigit() or int(self.rondas) <= 0:
                print("Por favor ingresa un número válido de rondas.")
                return
            if not self.dificultad:
                print("Por favor selecciona una dificultad.")
                return

            # Muestra los valores en consola
            self.set_all_LEDS_colors(0, 0, 0, 0)
            print(f"Usuario: {self.nombre}")
            print(f"Intentos: {self.intentos}")
            print(f"Rondas: {self.rondas}")
            print(f"Dificultad: {self.dificultad}")
            print("Valores confirmados. Juego listo para comenzar.")
            self.boton = True
            self.fallos = 0  # Reinicia contador al empezar juego
            self.cerrar_ui(1)
            self.ui.usuario.clear()
            self.ui.intentos.clear()
            self.ui.rondas.clear()
            self.set_dificultad()
            self.introduccion()


    def comenzar_checked(self):
            # UI 2: diálogo comenzar
            ui = self.load_ui_generic(
                UI_START, ui_number=2,
                botones={"comenzar": self.comenzar}
            )
            return ui

    def comenzar (self):
        self.running = True
        print("¡El juego ha comenzado!")
        self.ui2.accept()  # Cierra el diálogo cuando el botón es presionado
        self.start_time = time.time()
        self.fecha = datetime.now().strftime("%d-%m-%Y")
        self.hora = datetime.now().strftime("%H:%M:%S")

    def calibracion_checked(self):
        ui = self.load_ui_generic(
            UI_CALIB, ui_number=3,
            botones={"calibrar_button": self.calibracion_clicked},
            ayuda_button = "ayuda_button",
            back_button = "back_button"
        )
        return ui

    def respuesta_ui(self):
        ui = self.load_ui_generic(
            UI_RESP, ui_number=4,
            botones={
                "correcta": self.correcta_clicked,
                "incorrecta": self.incorrecta_clicked,
                "repetir": self.repetir_emocion_clicked,
            },
            back_button="back_button",
            ayuda_button="ayuda_button",
            after_load=lambda u: (hasattr(u, "ayuda") and u.ayuda.hide())
        )
        return ui

    def correcta_clicked(self):
        self.resultado_terapeuta = True
        self.esperando_validacion = False
        self.cerrar_ui(4)

    def incorrecta_clicked(self):
        self.resultado_terapeuta = False
        self.esperando_validacion = False
        self.cerrar_ui(4)

    def repetir_emocion_clicked(self):
        self.resultado_terapeuta = "Repitiendo"
        self.esperando_validacion = False
        self.cerrar_ui(4)


    def mostrar_ui_respuesta(self, mood, detectada):
        if hasattr(self.ui4, 'respuesta'):
            self.ui4.respuesta.setPlainText(str(mood))
        if hasattr(self.ui4, 'detectada'):
            self.ui4.detectada.setPlainText(str(detectada))
        self.centrar_ventana(self.ui4)
        self.ui4.show()


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
                    cv2.destroyAllWindows()

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

    def camera_ui (self):
        ui = self.load_ui_generic(
            UI_CAMERA, ui_number = 5,
            back_button="back_button",
            ayuda_button="ayuda_button",
            after_load=lambda u: (u.setWindowTitle("Cámara del EBO - Visor Terapeuta"))
        )
        return ui


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
        if not self.ui:
            print("Error: la interfaz de usuario no se ha cargado correctamente.")
            return

        self.centrar_ventana(self.ui)
        self.ui.raise_()
        self.ui.show()
        QApplication.processEvents()

    # ===================================================================
    # ===================================================================


    ######################
    # From the RoboCompCameraSimple you can call this methods:
    # RoboCompCameraSimple.TImage self.camerasimple_proxy.getImage()

    ######################
    # From the RoboCompCameraSimple you can use this types:
    # ifaces.RoboCompCameraSimple.TImage

    ######################
    # From the RoboCompEboMoods you can call this methods:
    # RoboCompEboMoods.void self.ebomoods_proxy.expressAnger()
    # RoboCompEboMoods.void self.ebomoods_proxy.expressDisgust()
    # RoboCompEboMoods.void self.ebomoods_proxy.expressFear()
    # RoboCompEboMoods.void self.ebomoods_proxy.expressJoy()
    # RoboCompEboMoods.void self.ebomoods_proxy.expressSadness()
    # RoboCompEboMoods.void self.ebomoods_proxy.expressSurprise()

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


