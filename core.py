import re
import sys
import time
import random

import logging

from data import DataGet
from downloader import Downloader
from settings import load_settings
from exceptions import (
    AlbumDataError,
    FavoriteError,

)

# 主程序，负责调度各个模块

logging.basicConfig(level=logging.INFO,
                    stream=sys.stdout,
                    format='%(asctime)s - %(levelname)s: %(message)s')


class Core:
    def __init__(self):
        setting = load_settings()
        # self.client = pymongo.MongoClient('mongodb://localhost:27017')  # mongodb端口预留
        # self.db = self.client['qobuz']
        # self.collection = self.db['track']
        self.last_request_time = 0
        self.format_id = setting['format_id']
        self.min_interval = setting['min_interval']  # 休眠间隔
        self.downloader = Downloader()
        self.track_datas = dict()  # 负责存储音轨元数据，它的数据结构是{"cover": str, "album_title": str, "tracks": list, "album_id": str}
        self.data_get = DataGet()

    def wait_interval(self):
        now = time.time()
        sleep_time = self.min_interval - (now - self.last_request_time)
        if sleep_time > 0:
            logging.info(f"休眠 {sleep_time}秒")
            time.sleep(sleep_time)
        self.last_request_time = time.time()

    def album_data(self, album_url):
        logging.info('开始获取专辑数据')
        album_id = None
        try:
            pattern = re.compile(r'/album/(?P<album_id>[^/?#]+)')
            match = pattern.search(album_url)
            if not match:
                logging.exception('专辑id匹配失败')
                raise NotImplementedError('专辑id匹配失败')
            album_id = match.group('album_id')
            self.track_datas['album_id'] = album_id
            data = self.data_get.get_album_data(album_id)  # 返回的是json对象
            return data
        except AlbumDataError:
            logging.exception(f'获取专辑信息失败，album_id为{album_id}')
            raise

    def favorite_data(self):
        logging.info('开始获取收藏曲目')
        data = self.data_get.get_favorite_data()
        return data

    def call_album_data(self, data):
        logging.info('开始解析专辑数据')
        cover = data.get('image').get('large')  # 获取封面地址
        self.track_datas['cover'] = cover
        title = data.get('title')  # 返回专辑标题
        self.track_datas['album_title'] = title

        track_items = data.get('tracks').get('items')  # 返回专辑中的所有音轨信息
        return track_items

    def file_url(self, track_id, format_id):
        logging.info('开始获取音频文件信息')
        data = self.data_get.get_file_url(track_id=track_id, format_id=format_id)
        return data

    def track_file_url(self, track_id, format_id):
        logging.info('开始获取音频文件信息')
        data = self.data_get.track_get_file_url(track_id=track_id, format_id=format_id)
        return data


def run_download(core, model, **kwargs):
    total_track_data = kwargs['total_track_data']
    length = len(total_track_data)
    if model == 'album':  # 专辑下载模式
        logging.info('开始下载整张专辑')
        for track_data in total_track_data:
            logging.info(f"开始下载{track_data['track_title']}")
            result = call_download(core, track_data)  # 返回布尔值
            if result == 0:
                try:
                    core.data_get.create_track(track_id=track_data['track_id'])  # 如果下载失败就收藏该曲目
                    logging.info('创建收藏成功')
                except FavoriteError:
                    logging.exception('创建收藏失败')
                    continue
            core.wait_interval()
        try:
            core.data_get.delete_album(album_id=core.track_datas['album_id'])  # 下载完成后直接删除专辑收藏
            logging.info('删除专辑收藏成功')
        except FavoriteError:
            logging.exception('删除专辑收藏失败')
        logging.info('删除专辑收藏成功')
    elif model == 'track':  # 单曲下载模式
        track_id = kwargs['track_id']
        track_data = None
        for data in total_track_data:
            if data.get('track_id') == track_id:  # 通过音轨id去匹配专辑中的音轨
                track_data = data
                break
        logging.info(f"开始下载单曲{track_data['track_title']}")
        result = call_download(core, track_data)
        if result == 1:  # 下载成功直接删除收藏
            try:
                core.data_get.delete_track(track_id=track_id)
                logging.info('删除收藏成功')
            except FavoriteError:
                logging.exception('删除收藏失败')
        core.wait_interval()
    elif model == 'tracks':  # 下载一首或多首曲目
        try:
            track_choice = kwargs['track_choice']
            numbers = track_choice.split()  # 返回字符串列表
            for number in numbers:
                num = int(number)
                if 0 < num <= length:
                    index = num - 1
                    logging.info(f"开始下载单曲{total_track_data[index]['track_title']}")
                    track_data = total_track_data[index]
                    call_download(core, track_data)
                    core.wait_interval()
                else:
                    track_choice = input('输入值非法，请重新输入')
                    return run_download(core=core, model='tracks', total_track_data=total_track_data, track_choice=track_choice)
        except ValueError:
            track_choice = input('输入值非法，请重新输入')
            return run_download(core=core, model='tracks', total_track_data=total_track_data, track_choice=track_choice)


def call_download(core, track_data):
    track_data['album_title'] = core.track_datas['album_title']
    track_data['cover'] = core.track_datas['cover']
    track_id = track_data['track_id']
    if not track_data['streamable']:
        logging.info(f"该曲目{track_data['track_title']}不可下载")
        return 2
    downloaded = 0
    attempt = 1
    while attempt <= 3:  # 重试逻辑
        try:
            file_data = core.track_file_url(track_id=track_id, format_id=core.format_id)
            core.downloader.download_music(file_data=file_data, track_data=track_data)
            downloaded = 1
            break
        except Exception:
            logging.warning(f'下载异常，当前下载次数为第{attempt}次', exc_info=True)
            wait = 3 ** attempt + random.uniform(2, 5)
            time.sleep(wait)
            attempt += 1
    else:
        return downloaded
    return downloaded


def meta_data(data):
    track_data = dict()

    track_data['track_title'] = data.get('title')  # 音轨标题
    track_data['track_id'] = data.get('id')  # 音轨id
    try:
        performer = data.get('performer').get('name')
    except AttributeError:
        performer = data.get('performers')
    track_data['performer'] = performer  # 作者
    track_data['track_number'] = data.get('track_number')  # 音轨号

    track_data['copyright'] = data.get('copyright')  # 获取版权标识
    track_data['version'] = data.get('version')

    track_data['streamable'] = data.get('streamable')  # 返回布尔值，是否可流式下载

    return track_data


def colored(text, color):  # 设置输出颜色
    colors = {"red": "31", "green": "32", "yellow": "33",
              "blue": "34", "purple": "35", "cyan": "36", "bold": "1"}
    code = colors.get(color, "0")
    return f"\033[{code}m{text}\033[0m"


def is_url(text):  # 检验输入是否为url字符串
    URL_RE = re.compile(
        r'^https?://'  # 协议
        r'(?:(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,})'  # 域名
        r'(?::\d{1,5})?'  # 可选端口
        r'(?:/\S*)?$'  # 可选路径
    )
    return bool(URL_RE.match(text))


def call_core(core, album_data):
    track_items = core.call_album_data(album_data)  # 返回专辑中的所有音轨数据，包括id等信息

    logging.info('开始解析元数据')
    total_track_data = []
    for index in range(len(track_items)):
        result_data = meta_data(track_items[index])
        total_track_data.append(result_data)
        print(colored(f"曲目{index + 1}: {result_data['track_title']}", 'yellow'))
    core.track_datas['tracks'] = total_track_data
    return total_track_data


def main(text):
    if is_url(text):  # 判断为url，单独下载
        logging.info('开始单独下载')
        core = Core()
        album_data = core.album_data(text)
        total_track_data = call_core(core=core, album_data=album_data)
        model_choice = input(
            f'请输入想要下载的曲目，取值范围在1-{len(total_track_data)}，多首曲目请输入空格隔开，如果要下载整张专辑，请直接回车执行'
        )
        if not model_choice:
            model = 'album'
            run_download(core, model, total_track_data=total_track_data)
            is_continue = input('下载完成，是否继续下载。是请输入专辑链接，否则任意键退出')
            if is_url(is_continue):
                main(is_continue)
            else:
                logging.info('程序结束')
        else:
            model = 'tracks'
            run_download(core, model, total_track_data=total_track_data, track_choice=model_choice)
            is_continue = input('下载完成，是否继续下载。是请输入专辑链接，否则任意键退出')
            if is_url(is_continue):
                main(is_continue)
            else:
                logging.info('程序结束')
    elif text == '1':  # 判断为数字1，从收藏曲目中下载
        logging.info('开始下载收藏曲目')
        core = Core()
        favorite_data = core.favorite_data()  # 其实不只有album，还有track，但是track无法获取元数据，所以只能手动下载
        albums = favorite_data['albums']  # 每个专辑的id列表
        tracks = favorite_data['tracks']  # 返回收藏单曲列表
        if albums:  # 存在收藏的专辑
            for album_id in albums:
                core.track_datas['album_id'] = album_id
                album_data = core.data_get.get_album_data(album_id)
                total_track_data = call_core(core=core, album_data=album_data)
                model = 'album'
                run_download(core, model, total_track_data=total_track_data)
        if tracks:
            get_list = core.data_get.get_track_list(tracks_id=tracks)
            tracks_data = get_list.get('tracks')  # 获取所有音轨信息
            for track_data in tracks_data:
                album_id = track_data.get('album').get('id')
                core.track_datas['album_id'] = album_id
                track_id = track_data.get('id')
                album_data = core.data_get.get_album_data(album_id)
                total_track_data = call_core(core=core, album_data=album_data)
                model = 'track'
                run_download(core, model, total_track_data=total_track_data, track_id=track_id)
        else:
            logging.info('没有收藏曲目')
    else:
        logging.info('输入无效，请重试')
        retext = input(
        '如果要单独下载，请输入URL；\n如果要下载收藏曲目，请输入1；\n'
    )
        main(retext)


if __name__ == '__main__':
    main(input(
        '如果要单独下载，请输入URL；\n如果要下载收藏曲目，请输入1；\n'
    ))


