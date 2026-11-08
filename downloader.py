import re
import os

import requests
import logging

import metadata

# 负责下载音频文件


class Downloader:
    def __init__(self):
        self.path = 'F://music//{}'  # 下载路径
        self.proxies = {'http': 'http://127.0.0.1:7890'}

    def download_track(self, track_data, file_data):  # 这里是file/url的下载函数
        logging.info('开始检测音轨')

        sampling_rate = file_data.get('sampling_rate')  # 实际采样率
        bits_depth = file_data.get('bits_depth')  # 实际位深

        track_title = modify_title(track_data.get('track_title'), track_data)
        performer = track_data.get('performer')

        try:
            restrictions = track_data.get('restrictions')
            logging.info(f"检测到音质降级，实际音质为{bits_depth}-Bit, {sampling_rate}Hz")
        except Exception:
            logging.info(f"检测为最高音质，{bits_depth}-Bit, {sampling_rate}Hz")

        n_segments = file_data.get('n_segments')  # 获取片段数量
        url = file_data.get('url_template')
        # https://streaming-qobuz-sec.akamaized.net/file?uid=14919953&eid=57617887&fmt=6&fid=323347660&profile=sec-1&s={}&app_id=798273057&cid=4644592&etsp=1790425318&hmac=_VuRbcSmWWgXwk4TgDJTK-p_QdI
        pattern_url = url.replace('$SEGMENT$', "{}")
        # path = self.path.format(f'{track_title}-{performer}.flac')
        for segment in range(0, int(n_segments) + 1):
            path = self.path.format(f'seg{segment}.mp4')
            with open(path, 'wb') as file:
                segment_url = pattern_url.format(segment)
                response = requests.get(segment_url, stream=True, proxies=self.proxies)
                response.raise_for_status()
                for chunk in response.iter_content(chunk_size=1024*1024):
                    if chunk:
                        file.write(chunk)
        logging.info('音频文件下载完成')

    def download_music(self, track_data, file_data):  # 这里是track/getFileUrl端口的下载函数
        logging.info('开始检测音轨')

        quality = file_data.get('format_id')

        sampling_rate = file_data.get('sampling_rate')  # 实际采样率
        bit_depth = file_data.get('bit_depth')  # 实际位深

        track_title = modify_title(track_data.get('track_title'), track_data)
        album_title = safe_name(track_data['album_title'])

        dir_path = self.path.format(f"{album_title}")
        os.makedirs(dir_path, exist_ok=True)

        try:
            track_data.get('restrictions')
            logging.info(f"检测到音质降级，实际最高音质为{bit_depth}-Bit, {sampling_rate}kHz")
        except Exception:
            logging.info(f"检测为最高音质，{bit_depth}-Bit, {sampling_rate}kHz")

        url = file_data.get('url')
        if quality > 5:
            logging.info('音频格式为flac')
            path = os.path.join(dir_path, f"{track_title}.flac")
            with open(path, 'wb') as file:
                response = requests.get(url, stream=True, proxies=self.proxies, timeout=(10, 20))
                response.raise_for_status()
                for chunk in response.iter_content(chunk_size=1024*1024):
                    if chunk:
                        file.write(chunk)
                logging.info('音频文件下载完成')

            metadata.tag_flac(track_data=track_data, track_path=path)
        else:
            logging.info('音频格式为mp3')
            path = os.path.join(dir_path, f"{track_title}.mp3")
            with open(path, 'wb') as file:
                response = requests.get(url, stream=True, proxies=self.proxies)
                response.raise_for_status()
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        file.write(chunk)
            logging.info('音频文件下载完成')
            metadata.tag_mp3(track_data=track_data, track_path=path)


def modify_title(title, track_data):  # 修改文件名称
    # 定义不允许的字符模式
    illegal_chars = r'[<>:"/\\|?*\n]'
    # 将非法字符替换为空格
    file_name = re.sub(illegal_chars, ' ', title)
    version = track_data['version']
    if version and (version not in file_name):
        logging.info('检测到版本标识')
        version = re.sub(illegal_chars, ' ', version)
        new_name = f"{file_name} ({version})"
        return new_name
    else:
        return file_name


def safe_name(name):
    return re.sub(r'[\\/:*?"<>|]', "-", name).strip().rstrip(".")