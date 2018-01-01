import re

from fuzzywuzzy import fuzz, process

from libtivomind import api, rpc
from tivoproxy.server import ServedObject


class ChannelCache(object):

    AFFILIATE_REFINERS = {'sports', 'business', 'news'}

    def __init__(self, hd_only=True, channel_list=None):
        self.hd_only = hd_only
        self.by_name = {}
        self.by_number = {}
        self.by_affiliate = {}
        if channel_list is not None:
            self.fill(channel_list=channel_list)

    def fill(self, channel_list):
        filtered = [c for c in channel_list if c['isHdtv']] if self.hd_only else channel_list
        self.by_name = {c['name']: c for c in filtered}
        self.by_number = {c['channelNumber']: c for c in filtered}
        self.by_affiliate = {c['affiliate']: c for c in filtered}

    def _get_name_or_affiliate(self, name, collection, prefer_hd):
        refiners = self.AFFILIATE_REFINERS
        unused_refiners = refiners - ({t.lower() for t in re.split(' +', name)} & refiners)
        coll_f = collection
        if prefer_hd and not self.hd_only:
            coll_f = {k: v for k, v in coll_f.items() if v['isHdtv']}
        if unused_refiners:
            coll_f = {k: v for k, v in coll_f.items() if not any(ss in k.lower() for ss in unused_refiners)}
        best_matches = process.extractBests(name, coll_f.keys(), scorer=fuzz.token_set_ratio)
        return best_matches

    def get_by_name(self, name, prefer_hd=False):
        return self._get_name_or_affiliate(name=name, collection=self.by_name, prefer_hd=prefer_hd)

    def get_by_affiliate(self, name, prefer_hd=False):
        return self._get_name_or_affiliate(name=name, collection=self.by_affiliate, prefer_hd=prefer_hd)

    def get_by_number(self, number):
        return self.by_number[str(number)]


class TiVoProxy(ServedObject):

    def __init__(self, server):
        super().__init__(server)
        self.config = server.config
        tp_config = self.config['TiVoProxy']
        self.manager = api.MindManager(cert_path=tp_config['CERT_PATH'],
                                       cert_password=tp_config['CERT_PWD'],
                                       address=tp_config['TIVO_ADDR'],
                                       credential=rpc.MRPCCredential.new_mak(tp_config['TIVO_MAK']))
        with self.manager.mind() as mind:
            self.channels = ChannelCache(hd_only=True)
            self.channels.fill(mind.channel_search(no_limit=True))

    def do_pause(self):
        result = {'type': 'response', 'cmd': 'pause'}
        with self.manager.mind() as mind:
            resp = mind.send_key(api.RemoteKey.pause)
            if resp['type'] == 'success':
                result['result'] = {'status': 'success'}
                return result
        result['error'] = 'An unknown error has occurred.'
        return result
