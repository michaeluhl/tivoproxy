import configparser
import io
import threading

from pubnub.enums import PNOperationType, PNStatusCategory
from pubnub.callbacks import SubscribeCallback
from pubnub.pnconfiguration import PNConfiguration
from pubnub.pubnub import PubNub


class ServedObject(object):
    # Request format:
    # {
    #   type='request',
    #   cmd='cmd',
    #   params={
    #     param_a=value_a,
    #     param_b=value_b
    #   }
    # }
    #
    # Response:
    # {
    #   type='response',
    #   cmd='cmd',
    #   result={}
    # }
    # If there's an error, there may be an 'error' field in the response

    def __init__(self, server):
        self.server = server

    def handle_message(self, pubnub, message):
        content = message.message
        try:
            cmd = content['cmd']
        except KeyError as e:
            return {'type': 'response',
                    'error': 'Message does not contain a command directive.'}
        try:
            cmd_fn = getattr(self, 'do_' + cmd)
        except AttributeError as e:
            return {'type': 'response',
                    'cmd': cmd,
                    'error': 'Command ({}) is not a valid directive.'.format(cmd)}
        try:
            return cmd_fn(**content['params'])
        except TypeError as e:
            return {'type': 'response',
                    'cmd': cmd,
                    'error': 'Incorrect number of parameters for command.'}



class PNObjectServer(SubscribeCallback):

    def __init__(self, config, served_class, server_name="PNObjectServer"):
        self.__config = config
        self.__server_name = server_name
        self.__served_class = served_class
        self.__served_object = None
        self.__connected = threading.Event()

        pn_cfg = self.__config[self.__server_name]

        self.__pnconfig = PNConfiguration()
        self.__pnconfig.publish_key = pn_cfg['PUBKEY']
        self.__pnconfig.subscribe_key = pn_cfg['SUBKEY']
        self.__pnconfig.uuid = pn_cfg['CLIENT_ID']
        self.__pnconfig.ssl = True

        self.__channel_pub = pn_cfg['PUBLISH_CHANNEL']
        self.__channel_sub = pn_cfg['SUBSCRIBE_CHANNEL']

    @property
    def config(self):
        cfg_str = io.StringIO()
        self.__config.write(cfg_str)
        cfg_str.seek(0)
        cfg_copy = configparser.ConfigParser()
        cfg_copy.read_file(cfg_str)
        return cfg_copy

    @property
    def server_name(self):
        return self.__server_name

    @property
    def served_class(self):
        return self.__served_class

    @property
    def connected(self):
        return self.__connected.is_set()

    def status(self, pubnub, status):
        if status.operation in (PNOperationType.PNSubscribeOperation, PNOperationType.PNUnsubscribeOperation):
            if status.category == PNStatusCategory.PNConnectedCategory:
                self.__connected.set()
            elif status.category == PNStatusCategory.PNDisconnectedCategory:
                self.__connected.clear()

    def presence(self, pubnub, presence):
        pass

    def message(self, pubnub, message):
        if self.__served_object is not None:
            response = self.__served_object.handle_message(pubnub=pubnub, message=message)
            pubnub.publish().channel(self.__channel_pub).message(response).sync()

    def run(self):
        self.__served_object = self.__served_class(self)
        pn = PubNub(self.__pnconfig)
        pn.add_listener(self)
        pn.subscribe().channels(self.__channel_sub).execute()
