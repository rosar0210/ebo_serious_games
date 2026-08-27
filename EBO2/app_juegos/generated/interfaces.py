import time
import Ice
import IceStorm
from rich.console import Console, Text
console = Console()

Ice.loadSlice("-I ./generated/ --all ./generated/Encuesta.ice")
import RoboCompEncuesta
Ice.loadSlice("-I ./generated/ --all ./generated/GestorSG.ice")
import RoboCompGestorSG
Ice.loadSlice("-I ./generated/ --all ./generated/JuegoMirror.ice")
import RoboCompJuegoMirror
Ice.loadSlice("-I ./generated/ --all ./generated/JuegoSimonSay.ice")
import RoboCompJuegoSimonSay
Ice.loadSlice("-I ./generated/ --all ./generated/JuegoTrivial.ice")
import RoboCompJuegoTrivial
Ice.loadSlice("-I ./generated/ --all ./generated/JuegoVeoVeo.ice")
import RoboCompJuegoVeoVeo
Ice.loadSlice("-I ./generated/ --all ./generated/Pasapalabra.ice")
import RoboCompPasapalabra
Ice.loadSlice("-I ./generated/ --all ./generated/StoryTelling.ice")
import RoboCompStoryTelling
Ice.loadSlice("-I ./generated/ --all ./generated/TherapistPanel.ice")
import RoboCompTherapistPanel


import gestorsgI

class Publishes:
    def __init__(self, ice_connector:Ice.CommunicatorI, topic_manager, parameters):
        self.ice_connector = ice_connector
        self.mprx={}
        self.topic_manager = topic_manager


    def create_topic(self, property_name, topic_name, prefix, ice_proxy):
        topic = False
        topic_full_name = f"{prefix}/{topic_name}" if prefix else topic_name

        while not topic:
            try:
                topic = self.topic_manager.retrieve(topic_full_name)
            except IceStorm.NoSuchTopic:
                try:
                    console.log(f"{Text('WARNING', style='yellow')} {topic_full_name} topic did not create. {Text('Creating...', style='green')}")
                    topic = self.topic_manager.create(topic_full_name)
                except:
                    console.log(f"{Text('WARNING', style='yellow')}publishing the {topic_full_name} topic. It is possible that other component have created")

        pub = topic.getPublisher().ice_oneway()
        proxy = ice_proxy.uncheckedCast(pub)
        self.mprx[property_name] = proxy
        return proxy

    def get_proxies_map(self):
        return self.mprx


class Requires:
    def __init__(self, ice_connector:Ice.CommunicatorI, parameters):
        self.ice_connector = ice_connector
        self.mprx={}

        self.Encuesta = self.create_proxy("Encuesta", RoboCompEncuesta.EncuestaPrx, parameters["Proxies"]["Encuesta"])
        self.JuegoMirror = self.create_proxy("JuegoMirror", RoboCompJuegoMirror.JuegoMirrorPrx, parameters["Proxies"]["JuegoMirror"])
        self.JuegoSimonSay = self.create_proxy("JuegoSimonSay", RoboCompJuegoSimonSay.JuegoSimonSayPrx, parameters["Proxies"]["JuegoSimonSay"])
        self.JuegoTrivial = self.create_proxy("JuegoTrivial", RoboCompJuegoTrivial.JuegoTrivialPrx, parameters["Proxies"]["JuegoTrivial"])
        self.JuegoVeoVeo = self.create_proxy("JuegoVeoVeo", RoboCompJuegoVeoVeo.JuegoVeoVeoPrx, parameters["Proxies"]["JuegoVeoVeo"])
        self.Pasapalabra = self.create_proxy("Pasapalabra", RoboCompPasapalabra.PasapalabraPrx, parameters["Proxies"]["Pasapalabra"])
        self.StoryTelling = self.create_proxy("StoryTelling", RoboCompStoryTelling.StoryTellingPrx, parameters["Proxies"]["StoryTelling"])
        self.TherapistPanel = self.create_proxy("TherapistPanel", RoboCompTherapistPanel.TherapistPanelPrx, parameters["Proxies"]["TherapistPanel"])

    def get_proxies_map(self):
        return self.mprx

    def create_proxy(self, property_name, ice_proxy, proxy_string):
        try:
            base_prx = self.ice_connector.stringToProxy(proxy_string)
            proxy = ice_proxy.uncheckedCast(base_prx)
            self.mprx[property_name] = proxy
            return True, proxy
        
        except Ice.Exception as e:
            console.print_exception(e)
            console.log(f'Cannot get {property_name} property.')
            self.status = -1
            return False, None


class Subscribes:
    def __init__(self, ice_connector:Ice.CommunicatorI, topic_manager, default_handler, parameters):
        self.ice_connector = ice_connector
        self.topic_manager = topic_manager

    def create_adapter(self, topic_name, prefix, interface_handler, endpoint_string):
        topic_full_name = f"{prefix}/{topic_name}" if prefix else topic_name

        adapter = self.ice_connector.createObjectAdapterWithEndpoints(topic_full_name, endpoint_string)
        handler = interface_handler
        proxy = adapter.addWithUUID(handler).ice_oneway()
        subscribe_done = False
        while not subscribe_done:
            try:
                topic = self.topic_manager.retrieve(topic_full_name)
                subscribe_done = True
            except Ice.Exception as e:
                try:
                    console.log(f"{Text('WARNING', style='yellow')} {topic_full_name} topic did not create. {Text('Creating...', style='green')}")
                    topic = self.topic_manager.create(topic_full_name)
                    subscribe_done = True
                except:
                    print(f"{Text('WARNING', style='yellow')}publishing the {topic_full_name} topic. It is possible that other component have created")
        qos = {}
        topic.subscribeAndGetPublisher(qos, proxy)
        adapter.activate()
        return adapter


class Implements:
    def __init__(self, ice_connector:Ice.CommunicatorI, default_handler, parameters):
        self.ice_connector = ice_connector

        self.gestorsg = self.create_adapter("GestorSG", gestorsgI.GestorSGI(default_handler, ""), parameters["Endpoints"]["GestorSG"])

    def create_adapter(self, property_name, interface_handler, endpoint_string):
        try:
            adapter = self.ice_connector.createObjectAdapterWithEndpoints(property_name, endpoint_string)
            adapter.add(interface_handler, self.ice_connector.stringToIdentity(property_name.lower()))
            adapter.activate()
            console.log(f"{property_name} adapter created in port {endpoint_string}")
        except:
            console.log(f"{Text('ERROR', style='red')} creating or activating adapter for{property_name}")
            self.status = -1


class InterfaceManager:
    def __init__(self, configData):

        init_data = Ice.InitializationData()
        init_data.properties = Ice.createProperties()
        init_data.properties.setProperty("Ice.Warn.Connections", configData["Ice"]["Warn"]["Connections"])
        init_data.properties.setProperty("Ice.Trace.Network", configData["Ice"]["Trace"]["Network"])
        init_data.properties.setProperty("Ice.Trace.Protocol", configData["Ice"]["Trace"]["Protocol"])
        init_data.properties.setProperty("Ice.MessageSizeMax", configData["Ice"]["MessageSizeMax"])
        self.ice_connector = Ice.initialize(init_data)

        self.status = 0

        needs_rcnode = False
        self.topic_manager = self.init_topic_manager(configData) if needs_rcnode else None

        self.requires = Requires(self.ice_connector, configData)
        self.publishes = Publishes(self.ice_connector, self.topic_manager, configData)
        self.implements = None
        self.subscribes = None

    def init_topic_manager(self, configData):
        obj = self.ice_connector.stringToProxy(configData["Proxies"]["TopicManager"])
        try:
            return IceStorm.TopicManagerPrx.checkedCast(obj)
        except Ice.ConnectionRefusedException as e:
            console.log(Text('Cannot connect to rcnode! This must be running to use pub/sub.', 'red'))
            self.status = -1
            exit(-1)

    def set_default_hanlder(self, handler, configData):
        self.implements = Implements(self.ice_connector, handler, configData)
        self.subscribes = Subscribes(self.ice_connector, self.topic_manager, handler, configData)

    def get_proxies_map(self):
        result = {}
        result.update(self.requires.get_proxies_map())
        result.update(self.publishes.get_proxies_map())
        return result

    def destroy(self):
        if self.ice_connector:
            self.ice_connector.destroy()




