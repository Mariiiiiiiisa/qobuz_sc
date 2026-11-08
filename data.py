import time
import json
import hashlib

import logging
import requests
from urllib.parse import urljoin

from bundle import Bundle
# 这个文件主要获取访问各端口的载荷参数

_BASE_URL = "https://play.qobuz.com"

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s: %(message)s')


class DataGet:
    def __init__(self, email, password):
        self.email = email
        self.password = password
        self.bundle = Bundle()
        self.app_id = self.bundle.get_app_id()
        self.secrets = self.bundle.get_secrets()
        self.profile = self.bundle.get_profile()
        self.session = requests.session()
        self.proxies = {'http': 'http://127.0.0.1:7890'}
        self.api_port = 'https://www.qobuz.com/api.json/0.2/'
        self.sec = None  # secrets里面的参数还需要测试，这里先设None占位
        self.unix = int(time.time())
        self.user_auth_token = 'IIzvirRk8qLsgV5hektP5D_eVpq1hRQNY7Cg8KtmJD1zVX__LOwQI1Bvj48cbFRaCUMkTHjQaZvXf9mdqkYLKA'  # 由于技术原因，目前该对象只能手动获取
        self.session.headers.update(
            {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36',
                'X-App-Id': self.app_id,
                "Content-Type": "application/json;charset=UTF-8",
                'X-User-Auth-Token': self.user_auth_token,
                'Referer': 'https://play.qobuz.com/',
                'Origin': 'https://play.qobuz.com/',
            }
        )  # 更新请求头
        self.cfg_setup()  # 筛选出有效secret

    def api_call(self, endpoint, model, **kwargs):
        if endpoint == 'session/start':
            self.session.headers.update({"Content-Type": "application/json;charset=UTF-8"})
            r_sig = 'sessionstartprofile{}{}{}'.format(self.profile, self.unix, self.sec)
            r_sig_hashed = hashlib.md5(r_sig.encode('utf-8')).hexdigest()
            params = {
                'profile': self.profile,
                'request_ts': self.unix,
                'request_sig': r_sig_hashed
            }
            data = None
        elif endpoint == 'album/get':
            self.session.headers.update({"Content-Type": "application/json;charset=UTF-8"})
            params = {
                'album_id': kwargs.get('album_id'),
                'offset': 0,
                'limit': 150,
                'extras': 'track_ids,albumsFromSameArtist'
            }
            data = None
        elif endpoint == 'track/getList':
            self.session.headers.update({"Content-Type": "application/json;charset=UTF-8"})
            params = {
                'tracks_id': [kwargs.get('track_id')]
            }
            data = None
        elif endpoint == 'file/url':
            self.session.headers.update({"Content-Type": "application/json;charset=UTF-8"})
            r_sig = 'fileurlformat_id{}intentstreamtrack_id{}{}{}'.format(kwargs.get('format_id'), kwargs.get('track_id'), self.unix, self.sec)
            r_sig_hashed = hashlib.md5(r_sig.encode('utf-8')).hexdigest()
            params = {
                'track_id': kwargs.get('track_id'),
                'format_id': kwargs.get('format_id'),  # 这个format_id的值是字符串类型
                'intent': 'stream',
                'request_ts': self.unix,
                'request_sig': r_sig_hashed
            }
            data = None
        elif endpoint == 'track/getFileUrl':
            self.session.headers.update({"Content-Type": "application/json;charset=UTF-8"})
            r_sig = 'trackgetFileUrlformat_id{}intentstreamtrack_id{}{}{}'.format(kwargs.get('format_id'), kwargs.get('track_id'), self.unix, self.sec)
            r_sig_hashed = hashlib.md5(r_sig.encode('utf-8')).hexdigest()
            params = {
                'track_id': kwargs.get('track_id'),
                'format_id': kwargs.get('format_id'),  # 这个format_id的值是字符串类型
                'intent': 'stream',
                'request_ts': self.unix,
                'request_sig': r_sig_hashed
            }
            data = None
        elif endpoint == 'favorite/getUserFavoriteIds':  # 抓取账号的favorite内容
            params = None
            data = None

        elif endpoint == 'favorite/delete':  # 从收藏当中删除专辑
            self.session.headers.update({"Content-Type": "application/json;charset=UTF-8"})
            params = {
                'track_ids': kwargs.get('track_id', None),
                'album_ids': kwargs.get('album_id', None),
                'artist_ids': None,
                'label_ids': None,
                'award_ids': None
            }
            data = None
        elif endpoint == 'favorite/create':  # 将音轨添加为收藏
            self.session.headers.update({"Content-Type": "application/json;charset=UTF-8"})
            params = {
                'track_ids': kwargs['track_id'],
                'album_ids': None,
                'artist_ids': None,
                'label_ids': None,
                'award_ids': None
            }
            data = None
        elif endpoint == 'meta/getList':  # 获取收藏音轨的专辑信息
            # 注意请求头中的Content-Type，意味着服务器需要什么类型的数据。这里说明表单数据需要json文本，因此data不能裸传，需要包成json对象
            self.session.headers.update({'Content-Type': 'text/plain;charset=UTF-8'})
            data = json.dumps({
                'tracks_id': kwargs.get('tracks_id', []),
                'albums_id': [],
                'artists_id': [],
                'playlists_id': [],
                'labels_id': [],
                'awards_id': []
            })
            params = None
        else:
            params = kwargs
            data = kwargs
        logging.info('开始请求，请求端口 %s', endpoint)
        if model == 'post':
            # 这里注意params和data的差异：params可以理解为在url这个头上做文章，而data是身体，传递的是表单数据
            response = self.session.post(urljoin(self.api_port, endpoint), params=params, data=data, proxies=self.proxies)
            response.raise_for_status()
            return response.json()
        elif model == 'get':
            response = self.session.get(urljoin(self.api_port, endpoint), params=params, proxies=self.proxies)
            response.raise_for_status()
            return response.json()

    def get_session_start(self):
        result = self.api_call(endpoint='session/start', model='post')  # 返回json
        self.session.headers.update({'X-Session-id': result.get('session_id')})

    def get_album_data(self, album_id):
        return self.api_call(endpoint='album/get', model='get', album_id=album_id)

    def get_meta_data(self, track_id):
        return self.api_call(endpoint='track/getList', model='post', track_id=track_id)

    def get_file_url(self, track_id, format_id):  # 这个端口的音频数据被加密，需要跟进一步的分析，目前暂时停用
        self.get_session_start()
        return self.api_call(endpoint='file/url', model='get', track_id=track_id, format_id=format_id)

    def track_get_file_url(self, track_id, format_id):
        return self.api_call(endpoint='track/getFileUrl', model='get', track_id=track_id, format_id=format_id)

    def get_favorite_data(self):
        return self.api_call(endpoint='favorite/getUserFavoriteIds', model='get')

    def delete_album(self, album_id):
        return self.api_call(endpoint='favorite/delete', model='post', album_id=album_id)

    def delete_track(self, track_id):
        return self.api_call(endpoint='favorite/delete', model='post', track_id=track_id)

    def create_track(self, track_id):
        return self.api_call(endpoint='favorite/create', model='post', track_id=track_id)

    def get_track_list(self, tracks_id):
        return self.api_call(endpoint='meta/getList', model='post', tracks_id=tracks_id)

    # secrets要过这个测试例子进行筛选
    def test_secret(self):
        try:
            self.api_call(endpoint="session/start", model='post')
            return True
        except Exception:
            return logging.info('无效secret')

    def cfg_setup(self):
        for secret in self.secrets:
            # Falsy secrets
            self.sec = self.secrets.get(secret)
            if not secret:
                continue

            if self.test_secret():  # 如果成功直接break
                break

        if self.sec is None:
            raise logging.info('没有有效secret，抛出异常', exc_info=True)





