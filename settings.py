import configparser
import logging
import os


def load_settings(path='config.cfg'):
    if not os.path.exists(path):
        raise FileExistsError(f'配置文件{path}不存在')
    cfg = configparser.ConfigParser()
    cfg.read(path, encoding='utf-8')
    try:
        user_auth_token = cfg['account']['user_auth_token']
        proxy = cfg['network']['proxy']
        format_id = cfg.getint('download', 'format_id')
        path = cfg['download']['path']
        min_interval = cfg.getint('download', 'min_interval')
    except Exception:
        logging.error('必填内容读取失败，请重新填写', exc_info=True)
        raise KeyError('必填内容存在空值')

    return {
        'email': cfg['account']['email'],
        'password': cfg['account']['password'],
        'path': path,
        'format_id': format_id,
        'min_interval': min_interval,
        'proxy': proxy,
        'mongodb_address': cfg['account'].get('mongodb_address', None),
        'user_auth_token': user_auth_token
    }


def main():
    result = load_settings()
    print(result)


if __name__ == '__main__':
    main()