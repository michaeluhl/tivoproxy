import json
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
        best_matches = process.extractBests(name, coll_f.keys(), scorer=fuzz.ratio)
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
        self.channels = ChannelCache(hd_only=True)
        try:
            with open(tp_config['CHAN_CACHE_FILE'], 'rt') as cache:
                channel_data = json.load(cache)
                print('Loading Channel Information from cache file...')
                self.channels.fill(channel_list=channel_data)
                print('...loaded.')
        except (KeyError, FileNotFoundError, json.JSONDecodeError):
            print('No/Invalid Cache File or Reload Requested.')
            print('Loading Channel Information from TiVo...')
            with self.manager.mind() as mind:
                channel_data = mind.channel_search(no_limit=True)
                self.channels.fill(channel_list=channel_data)
                if 'CHAN_CACHE_FILE' in tp_config:
                    print('Saving Cache...')
                    with open(tp_config['CHAN_CACHE_FILE'], 'wt') as cache:
                        json.dump(channel_data, cache)
                    print('...Saved.')
            print('Loaded.')


    def do_remote_key(self, key, value=None):
        result = {'type': 'response', 'cmd': 'remote_key'}
        print(key, value)
        try:
            with self.manager.mind() as mind:
                if key == 'string' and value:
                    for c in value.lower():
                        response = {'type': 'success'}
                        if c.isalpha():
                            response = mind.send_key(key_event='ascii', value=ord(c))
                        elif c.isdigit():
                            response = mind.send_key(key_event='num' + c)
                        elif c == ' ':
                            response = mind.send_key(key_event=api.RemoteKey.forward)
                        if response['type'] != 'success':
                            result['error'] = 'An unknown error has occurred.'
                            print(result)
                            return result
                else:
                    response = mind.send_key(key_event=api.RemoteKey[key])
                    if response['type'] != 'success':
                        result['error'] = 'An unknown error has occurred.'
                        print(result)
                        return result
                result['result'] = {'key': key, 'status': 'success'}
                if value:
                    result['result']['value'] = value
                return result
        except KeyError as ke:
            result['error'] = 'Key ({}) is not a valid key code.'.format(key)
            return result

    def do_change_channel(self, channel_number=None, channel_name=None):
        result = {'type': 'response', 'cmd': 'change_channel'}
        if (channel_number and channel_name) or (not channel_number and not channel_name):
            result['error'] = 'Specify either channel_num or channel_name, not both.'
            return result
        specifier_type = 'channel_number' if channel_number else 'channel_name'
        channel = None
        if channel_number:
            try:
                channel = self.channels.get_by_number(channel_number)
            except KeyError as ke:
                result['error'] = 'No channel matching number: {}'.format(channel_number)
                return result
        else:
            chan_affl, affl_rank = self.channels.get_by_affiliate(channel_name)[0]
            chan_name, name_rank = self.channels.get_by_name(channel_name)[0]
            if max([affl_rank, name_rank]) < 50:
                result['error'] = 'No good matches for channel: {}'.format(channel_name)
                return result
            channel = self.channels.by_name[chan_name]
            if affl_rank > name_rank:
                channel = self.channels.by_affiliate[chan_affl]
        print(specifier_type, channel['name'], channel['channelId'])
        with self.manager.mind() as mind:
            response = mind.change_channel(channel['channelId'])
        result['result'] = {'status': 'success'}
        if specifier_type == 'channel_number':
            result['result']['channel_number'] = channel_number
        else:
            result['result']['channel_name'] = channel_name
        return result
