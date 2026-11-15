import os

import logging
import requests
from mutagen.flac import FLAC, Picture
from mutagen.id3 import ID3, ID3NoHeaderError
import mutagen.id3 as id3

from settings import load_settings



def tag_flac(track_data, track_path):
    logging.info('开始为flac文件添加元数据')
    # 打标签
    audio = FLAC(track_path)

    audio["TITLE"] = track_data.get('track_title')
    audio['ARTIST'] = track_data.get('performer')
    audio['ALBUM'] = track_data.get('album_title')
    audio['TRACKNUMBER'] = str(track_data.get('track_number'))
    audio['COPYRIGHT'] = track_data.get('copyright')

    # 嵌入封面
    picture = Picture()
    picture.type = 3
    picture.mime = 'image/jpeg'
    picture.desc = 'Cover'

    image_url = track_data.get('cover')
    response = requests.get(image_url, timeout=(10, 60))
    response.raise_for_status()
    picture.data = response.content
    audio.add_picture(picture)

    audio.save()


def tag_mp3(track_data, track_path):
    logging.info('开始为mp3文件添加元数据')
    try:
        audio = ID3(track_path)
    except ID3NoHeaderError:
        audio = ID3()

    audio["TIT2"] = id3.TIT2(encoding=3, text=track_data['track_title'])  # 标题
    audio["TPE1"] = id3.TPE1(encoding=3, text=track_data['performer'])  # 艺术家
    audio["TALB"] = id3.TALB(encoding=3, text=track_data['album_title'])  # 专辑

    image_url = track_data.get('cover')
    image = requests.get(image_url).content
    audio["APIC"] = id3.APIC(encoding=3, mime="image/jpeg", type=3, desc="", data=image)

    audio.save(track_path, v2_version=3)