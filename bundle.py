import re

import base64
import logging
import requests
from urllib.parse import urljoin
from collections import OrderedDict

# 这个文件的主要目的是获取appid和secrets

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s: %(message)s')

_BASE_URL = "https://play.qobuz.com"

# 这个模板用于匹配时区以及种子字符串
_SEED_TIMEZONE_REGEX = re.compile(
    r'[a-z]\.initialSeed\("(?P<seed>[\w=]+)",window\.utimezone\.(?P<timezone>[a-z]+)\)'
)

# 这个模板用于抓取extras的字符串，用来平凑secrets
_INFO_EXTRAS_REGEX = r'name:"\w+/(?P<timezone>{timezones})",info:"(?P<info>[\w=]+)",extras:"(?P<extras>[\w=]+)"'

# 这个模板用于获取获取app_id和appSecret
_APP_ID_REGEX = re.compile(
    r'production:{api:{appId:"(?P<app_id>\d{9})",appSecret:"\w{32}"'
)

'''
匹配结果如下：
c={
    integration:{
        api:{appId:"377257687",appSecret:"f686f063cb0841079d48495d4dea7cf2"},
        braze:u,
        extra:l
        },
    nightly:{
        api:{appId:"377257687",appSecret:"05a4851e74ee47fda346f50cfdfc4f09"},
        braze:u,
        extra:l
        },
    recette:{
        api:{appId:"724307056",appSecret:"05a4851e74ee47fda346f50cfdfc4f09"},
        braze:u,
        extra:l
        },
    beta:{
        api:{
        appId:"XXXXX",appSecret:"XXXXX"},braze:u,extra:l},
        production:{api:{appId:"798273057",appSecret:"05a4851e74ee47fda346f50cfdfc4f09"},
        braze:o(o({},u),{},{apiKey:"b464b6f4-ee64-4efe-91b5-5b43f8932bed"}),
        extra:l
        }
    }
'''

# 这个模板用于获取bundle.js的文件地址，因为bundle.js文件会更新，所以需要模板来匹配地址
_BUNDLE_URL_REGEX = re.compile(
    r'<script src="(/resources/\d+\.\d+\.\d+-[a-z]\d{3}/bundle\.js)"></script>'
)

_SESSION_PROFILE_REGEX = re.compile(
    r'profile\s*:\s*["\'](?P<profile>[^"\']+)["\']'
)


class Bundle:
    def __init__(self):
        self.proxies = {'http': 'http://127.0.0.1:7890'}

        logging.info('获取登录页')
        response = requests.get(urljoin(_BASE_URL, '/login'), proxies=self.proxies)

        # 获取bundle的href
        bundle_url_match = _BUNDLE_URL_REGEX.search(response.text)  # 如果匹配成功就是这样的：<re.Match object; span=(5936, 5991), match='<script src="/resources/8.2.0-b034/bundle.js"></s>
        if not bundle_url_match:
            raise logging.info('bundle.js地址匹配失败')

        bundle_href = bundle_url_match.group(1)  # /resources/8.2.0-b034/bundle.js

        # 获取bundle.js文件
        bundle_response = requests.get(urljoin(_BASE_URL, bundle_href), proxies=self.proxies)
        self.bundle = bundle_response.text

    def get_app_id(self):
        logging.info('获取appID')
        match = _APP_ID_REGEX.search(self.bundle)
        if not match:
            logging.info('appID匹配失败')
        return match.group("app_id")

    def get_secrets(self):
        logging.info('获取secrets')
        seed_match = _SEED_TIMEZONE_REGEX.finditer(self.bundle)

        secrets = OrderedDict()
        for match in seed_match:
            seed, timezone = match.group('seed', 'timezone')
            secrets[timezone] = seed

        keypairs = list(secrets.items())
        secrets.move_to_end(keypairs[1][0], last=False)  # 交换字典前两个元素的位置
        info_extras_regex = _INFO_EXTRAS_REGEX.format(
            timezones="|".join([timezone.capitalize() for timezone in secrets])
        )
        '''
         info_extras_regex = name:"\w+/(?P<timezone>Abidjan|London|Berlin)",info:"(?P<info>[\w=]+)",extras:"(?P<extras>[\w=]+)"
         这里是在构造正则的匹配模板，大致含义是：
         name字段提取出一个timezone,只允许是Abidjan、London、Berlin三者其一。这三者是在seed_matches这个对象获取的
         info提取info内容
         extras提取extras内容
        '''

        info_extras_matches = re.finditer(info_extras_regex, self.bundle)
        for match in info_extras_matches:
            timezone, info, extras = match.group("timezone", "info", "extras")
            secrets[timezone.lower()] = [secrets[timezone.lower()], info, extras]  # 这里在做密文拼接，将三个seed拼到一个列表里面，方便后续编码
        for secret_pair in secrets:
            secrets[secret_pair] = base64.standard_b64decode(
                "".join(secrets[secret_pair])[:-44]
            ).decode("utf-8")
        return secrets  # 是一个类似字典的对象

    def get_profile(self):
        logging.info('开始获取profile')
        pro_match = _SESSION_PROFILE_REGEX.search(self.bundle)
        if not pro_match:
            logging.info('profile获取失败')
        return pro_match.group("profile")

