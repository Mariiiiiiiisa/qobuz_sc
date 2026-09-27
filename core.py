import re
import sys
import time

import logging

from data import DataGet
from bundle import Bundle
from downloader import Downloader

# 主程序，负责调度各个模块

logging.basicConfig(level=logging.INFO,
                    stream=sys.stdout,
                    format='%(asctime)s - %(levelname)s: %(message)s')

album_url = input('请输出想要下载的专辑链接')


class Core:
    def __init__(self):
        self.email = 'xkqk1l0r@outlook.tw'
        self.password = 'Hebe1234'  # 账号密码记得定期修改
        self.bundle = Bundle()
        # self.client = pymongo.MongoClient('mongodb://localhost:27017')  # mongodb端口预留
        # self.db = self.client['qobuz']
        # self.collection = self.db['track']
        self.last_request_time = 0
        self.min_interval = 10
        self.downloader = Downloader()
        self.app_id = self.bundle.get_app_id()
        self.secrets = self.bundle.get_secrets()
        self.profile = self.bundle.get_profile()
        self.format_id = 27  # 默认下载最高音质
        self.track_datas = dict()  # 负责存储音轨元数据，它的数据结构是{"cover": str, "album_title": str, "tracks": list}
        self.data_get = DataGet(email=self.email, password=self.password, app_id=self.app_id, secrets=self.secrets, profile=self.profile)

    def wait_interval(self):
        now = time.time()
        sleep_time = self.min_interval - (now - self.last_request_time)
        if sleep_time > 0:
            logging.info(f"休眠 {sleep_time}秒")
            time.sleep(sleep_time)
        self.last_request_time = time.time()

    def album_data(self):
        logging.info('开始获取专辑数据')
        try:
            pattern = re.compile(r'/album/(?P<album_id>[^/?#]+)')
            match = pattern.search(album_url)
            if not match:
                raise logging.info('专辑id匹配失败')
            album_id = match.group('album_id')
            data = self.data_get.get_album_data(album_id)  # 返回的是json对象
            return data
        except Exception:
            raise logging.info('获取专辑信息失败', exc_info=True)

    def get_album_data(self, data):
        logging.info('开始解析专辑数据')
        cover = data.get('image').get('large')  # 获取封面地址
        self.track_datas['cover'] = cover
        title = data.get('title')  # 返回专辑标题
        self.track_datas['album_title'] = title

        track_items = data.get('tracks').get('items')  # 返回专辑中的所有音轨信息
        return track_items

    def meta_data(self, data):
        track_data = dict()

        track_data['track_title'] = data.get('title')  # 音轨标题
        track_data['track_id'] = data.get('id')  # 音轨id
        track_data['performer'] = data.get('performer').get('name')  # 作者
        track_data['track_number'] = data.get('track_number')  # 音轨号

        track_data['copyright'] = data.get('copyright')  # 获取版权标识
        track_data['version'] = data.get('version')

        track_data['streamable'] = data.get('streamable')  # 返回布尔值，是否可流式下载

        return track_data

    def file_url(self, track_id, format_id):
        logging.info('开始获取音频文件信息')
        data = self.data_get.get_file_url(track_id=track_id, format_id=format_id)
        return data

    def track_file_url(self, track_id, format_id):
        logging.info('开始获取音频文件信息')
        data = self.data_get.track_get_file_url(track_id=track_id, format_id=format_id)
        return data

    def download_model(self, model, **kwargs):
        total_track_data = kwargs['total_track_data']
        length = len(total_track_data)
        if not model:
            logging.info('开始下载整张专辑')
            for track_data in total_track_data:
                logging.info(f"开始下载{track_data['track_title']}")
                track_data['album_title'] = self.track_datas['album_title']
                track_data['cover'] = self.track_datas['cover']
                file_data = self.track_file_url(track_id=track_data['track_id'], format_id=self.format_id)
                if track_data['streamable']:
                    self.wait_interval()
                    self.downloader.download_music(file_data=file_data, track_data=track_data)
                else:
                    logging.info('该曲目不可下载')
        else:
            try:
                numbers = model.split(" ")  # 返回字符串列表
                for number in numbers:
                    num = int(number)
                    if 0 < num <= length:
                        index = num - 1
                        logging.info(f"开始下载单曲{total_track_data[index]['track_title']}")
                        track_data = total_track_data[index]
                        track_data['album_title'] = self.track_datas['album_title']
                        track_data['cover'] = self.track_datas['cover']
                        file_data = self.track_file_url(track_id=track_data['track_id'], format_id=self.format_id)
                        if track_data['streamable']:
                            self.wait_interval()
                            self.downloader.download_music(file_data=file_data, track_data=track_data)
                        else:
                            logging.info('该曲目不可下载')
                    else:
                        model = input('输入值非法，请重新输入')
                        return self.download_model(model, total_track_data=total_track_data)
            except ValueError:
                model = input('输入值非法，请重新输入')
                return self.download_model(model, total_track_data=total_track_data)


def colored(text, color):  # 设置输出颜色
    colors = {"red": "31", "green": "32", "yellow": "33",
              "blue": "34", "purple": "35", "cyan": "36", "bold": "1"}
    code = colors.get(color, "0")
    return f"\033[{code}m{text}\033[0m"


def main():
    core = Core()
    album_data = core.album_data()
    track_items = core.get_album_data(album_data)  # 返回专辑中的所有音轨数据，包括id等信息

    logging.info('开始解析元数据')
    total_track_data = []
    for index in range(len(track_items)):
        result_data = core.meta_data(track_items[index])
        total_track_data.append(result_data)
        print(colored(f"曲目{index+1}: {result_data['track_title']}", 'yellow'))
    core.track_datas['tracks'] = total_track_data

    model = input(f'请输入想要下载的曲目，取值范围在1-{len(total_track_data)}，多首曲目请输入空格隔开，如果要下载整张专辑，请直接回车执行')

    core.download_model(model, total_track_data=total_track_data)


if __name__ == '__main__':
    main()


