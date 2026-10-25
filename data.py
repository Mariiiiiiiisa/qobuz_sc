import time
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
    def __init__(self, email, password, app_id, secrets, profile):
        self.email = email
        self.password = password
        self.app_id = app_id
        self.secrets = secrets
        self.profile = profile
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
            }
        )  # 更新请求头
        self.cfg_setup()  # 筛选出有效secret

    def api_call(self, endpoint, model, **kwargs):
        if endpoint == 'session/start':
            r_sig = 'sessionstartprofile{}{}{}'.format(self.profile, self.unix, self.sec)
            r_sig_hashed = hashlib.md5(r_sig.encode('utf-8')).hexdigest()
            params = {
                'profile': self.profile,
                'request_ts': self.unix,
                'request_sig': r_sig_hashed
            }
        elif endpoint == 'album/get':
            params = {
                'album_id': kwargs.get('album_id'),
                'offset': 0,
                'limit': 150,
                'extras': 'track_ids,albumsFromSameArtist'
            }
        elif endpoint == 'track/getList':
            params = {
                'tracks_id': [kwargs.get('track_id')]
            }
        elif endpoint == 'file/url':
            r_sig = 'fileurlformat_id{}intentstreamtrack_id{}{}{}'.format(kwargs.get('format_id'), kwargs.get('track_id'), self.unix, self.sec)
            r_sig_hashed = hashlib.md5(r_sig.encode('utf-8')).hexdigest()
            params = {
                'track_id': kwargs.get('track_id'),
                'format_id': kwargs.get('format_id'),  # 这个format_id的值是字符串类型
                'intent': 'stream',
                'request_ts': self.unix,
                'request_sig': r_sig_hashed
            }
        elif endpoint == 'track/getFileUrl':
            r_sig = 'trackgetFileUrlformat_id{}intentstreamtrack_id{}{}{}'.format(kwargs.get('format_id'), kwargs.get('track_id'), self.unix, self.sec)
            r_sig_hashed = hashlib.md5(r_sig.encode('utf-8')).hexdigest()
            params = {
                'track_id': kwargs.get('track_id'),
                'format_id': kwargs.get('format_id'),  # 这个format_id的值是字符串类型
                'intent': 'stream',
                'request_ts': self.unix,
                'request_sig': r_sig_hashed
            }
        elif endpoint == 'favorite/getUserFavoriteIds':  # 抓取账号的favorite内容
            params = None

        elif endpoint == 'favorite/delete':  # 从收藏当中删除专辑
            params = {
                'track_ids': None,
                'album_ids': kwargs['album_id'],
                'artist_ids': None,
                'label_ids': None,
                'award_ids': None
            }
        else:
            params = kwargs
        logging.info('开始请求，请求端口 %s', endpoint)
        if model == 'post':
            response = self.session.post(urljoin(self.api_port, endpoint), params=params, proxies=self.proxies)
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





