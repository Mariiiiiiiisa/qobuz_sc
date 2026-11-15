# Qobuz-sc

一个基于 Python 的命令行工具，用于下载来自qobuz的无损和hires流媒体资源。

> 本项目仅用于个人学习与技术研究。使用前请自行确认所在地区的法律法规及 Qobuz 服务条款，因使用本工具产生的任何后果由使用者自行承担。

---

## 功能

- 下载单张专辑的整张或指定曲目
- 下载账号收藏中的专辑与单曲
- 支持 FLAC / MP3，按 `format_id` 选择音质
- 自动写入标题、艺术家、专辑、音轨号、版权、封面

---

## 环境要求

- Python 3.8+
- 一个有效的 Qobuz 会员账号，并在 https://play.qobuz.com/discover 中登录
- 需要代理，请准备好 HTTP/HTTPS 代理地址

### 依赖

```bash
pip install requests mutagen
```

| 包          | 用途                   |
| ---------- | -------------------- |
| `requests` | 所有 HTTP 请求           |
| `mutagen`  | 写入 FLAC / MP3 元数据与封面 |

---

## 安装

方法一：

```bash
git clone https://github.com/Mariiiiiiiisa/qobuz_sc.git
cd qobuz_sc
pip install -r requirements.txt   # 或手动 pip install requests mutagen
```

方法二（推荐）：

直接下载zip文件并解压到本地，然后安装vscode，在vscode中打开解压的文件夹。然后下载python并安装requests库和mutagen库(这一步不会可以去b站搜教程)

---

项目文件结构如下：

```text
.
├── bundle.py          # 抓取并解析 bundle.js，提取 app_id / secrets / profile
├── config.cfg         # 配置文件
├── core.py            # 主调度：输入解析、下载流程、收藏管理
├── data.py            # Qobuz API 调用与签名
├── downloader.py      # 音频文件下载
├── exceptions.py      # 自定义异常
├── metadata.py        # FLAC / MP3 元数据与封面写入
├── settings.py        # 读取 config.cfg
└── README.md
```

---

## 配置

编辑项目根目录的 `config.cfg`：

```ini
[account]
email =
password =
mongodb_address =
; 用户认证必填
user_auth_token =

[download]
; 下载路径必填，例如 F://music//
path =
; 下载曲目的质量必填，27是默认最高音质
format_id = 27
; 最小下载间隔必填，单位秒
min_interval = 30

[network]
; 代理服务地址必填，例如 http://***.*.*.*:****
proxy =
```

### 字段说明

| 字段                           | 必填  | 说明                                       |
| ---------------------------- | --- | ---------------------------------------- |
| `account.user_auth_token`    | 是   | Qobuz 登录后的用户令牌，获取方式见下文                   |
| `account.email` / `password` | 否   | 当前版本未使用，保留字段                             |
| `account.mongodb_address`    | 否   | 当前版本未使用，预留字段                             |
| `download.path`              | 是   | 下载根目录，专辑会在此目录下建同名子文件夹                    |
| `download.format_id`         | 是   | 音质 ID，见下表                                |
| `download.min_interval`      | 是   | 两次下载之间的最小间隔（秒），建议不低于 30                  |
| `network.proxy`              | 是   | HTTP/HTTPS 代理地址；不需要代理时也需填写一个可用的值，否则请求会失败 |

### format_id 取值

| format_id | 音质                        |
| --------- | ------------------------- |
| 5         | MP3 320 kbps              |
| 6         | FLAC 16 bit / 44.1 kHz    |
| 7         | FLAC 24 bit / 96 kHz      |
| 27        | FLAC 24 bit / 192 kHz（最高） |

### 如何获取 user_auth_token

1. 浏览器打开 `https://play.qobuz.com` 并登录qobuz会员账号。
2. 打开开发者工具（F12）→ Network 面板。
3. 刷新页面，找到任意发往 `login` 的请求。
4. 点击login在请求头里找到 `X-User-Auth-Token`，复制其值填入 `config.cfg`。
   
   ![](C:\Users\吴晨宇\AppData\Roaming\marktext\images\2026-11-15-21-10-34-image.png)

### 如何获取自己的代理地址

前提是本地已有代理，例如客户端是使用clash verge，可以在系统代理开关处的设置图表中查看自己的服务地址，根据示例补充成完整的链接。

---

## 使用

```bash
python core.py
```

或者在vscode中选择core.py文件然后运行该文件。

启动后根据提示输入：

```text```
如果要单独下载，请输入URL；
如果要下载收藏曲目，请输入1；
```

### 1. 单独下载专辑

输入专辑链接，例如：

```text
https://play.qobuz.com/album/xxxxxxxxxxxxx
```

程序会：

1. 解析 `album_id`
2. 获取专辑元数据并打印曲目列表
3. 提示输入要下载的曲目编号

```text
请输入想要下载的曲目，取值范围在1-N，多首曲目请输入空格隔开，如果要下载整张专辑，请直接回车执行
```

- 直接回车：下载整张专辑
- 输入 `1 3 5`：只下载第 1、3、5 首
- 输入 `1`：只下载第 1 首

下载完成后，程序会询问是否继续：

```
下载完成，是否继续下载。是请输入专辑链接，否则任意键退出
```

输入新的专辑链接可继续，输入其他任意内容退出。

### 2. 下载收藏

输入 `1`，程序会：

1. 拉取账号收藏的专辑 ID 列表与单曲 ID 列表
2. 注意！！！逐张专辑下载全部曲目，完成后移除专辑收藏
3. 注意！！！逐个单曲下载，完成后移除单曲收藏

如果介意收藏删除的话请手动下载，不要使用该下载模式。

### 输出目录结构

```text
<download.path>/
└── <专辑名>/
    ├── <曲名>.flac
```

文件名会自动清理 Windows 不允许的字符（`<>:"/\|?*` 等）。

---

## 工作流程

```
core.py
  ├─ Core.__init__
  │    ├─ settings.load_settings()         读取 config.cfg
  │    └─ DataGet.__init__
  │         ├─ Bundle.__init__             请求 /login，匹配 bundle.js 地址，下载 bundle.js
  │         ├─ Bundle.get_app_id()         正则匹配 app_id
  │         ├─ Bundle.get_secrets()        匹配 seed / info / extras，base64 解码
  │         ├─ Bundle.get_profile()        匹配 profile
  │         └─ cfg_setup()                 逐个 secret 调用 session/start 测试，选出有效的
  │
  ├─ album_data(url)                        解析 album_id，调用 album/get
  ├─ call_core(album_data)                  解析封面、标题、曲目列表，打印曲目编号
  │
  ├─ run_download(model='album'|'track'|'tracks')
  │    └─ call_download(track_data)
  │         ├─ 检查 streamable
  │         ├─ 重试最多 3 次：
  │         │    ├─ track/getFileUrl 获取音频地址
  │         │    └─ downloader.download_music 下载并写标签
  │         └─ 失败时创建收藏，成功时删除收藏
  │
  └─ wait_interval()                        两次下载之间休眠
```

---

## 常见问题

### 启动时报 `FileNotFoundError: 配置文件 config.cfg 不存在`

请确保在项目根目录运行 `python core.py`，或修改 `settings.load_settings(path=...)` 中的路径。

### 报 `KeyError: 必填内容存在空值`

`config.cfg` 中以下字段不能为空：

- `user_auth_token`
- `download.path`
- `download.format_id`
- `download.min_interval`
- `network.proxy`

### 报 `InvalidSecretError: 没有有效secret`

说明从 `bundle.js` 提取的 secret 全部无效，通常原因：

1. Qobuz 前端代码结构变更，正则不再匹配 → 需要更新 `bundle.py` 中的正则
2. 网络请求被拦截或返回了非预期页面 → 检查代理是否可用，手动访问 `https://play.qobuz.com/discover` 是否能正常打开

### 所有曲目都下载失败

常见原因：

- 代理未生效：`network.proxy` 填写错误，或代理只支持 HTTP 不支持 HTTPS
- 账号无权限：会员过期

### 程序在某首歌上卡住很久

`call_download()` 失败时会进行最多 3 次重试，等待时间为 `3^attempt + random(2, 5)` 秒，最坏情况下单曲重试约 40 秒。属正常现象。

---

## 已知限制

- **依赖 Qobuz 私有 API 与前端 bundle**：Qobuz 更新前端或调整接口后，`bundle.py` 的正则和 `data.py` 的端点可能失效。
- **`email` / `password` 未使用**：当前认证完全依赖 `user_auth_token`，请勿在公开仓库提交含真实 token 的 `config.cfg`。
- **不支持并发下载**：所有请求串行执行，通过 `min_interval` 控制频率。请勿将 `min_interval` 设为 0，以免触发风控。

---

## 致谢

本项目特别致谢vitiko98的项目[*qobuz-dl*](https://github.com/vitiko98/qobuz-dl)本项目的签证构造在很大程度上依赖前者的探索。

---

## 保命声明（

脚本小子写的粪作，还望大佬海涵，轻点喷

---

## 免责声明

本项目仅供学习 Python 网络请求、正则解析、文件下载与元数据处理等技术使用。请勿用于商业用途或大规模抓取。使用者应自行确保其行为符合 Qobuz 服务条款及所在地区法律法规。项目作者不对因使用本项目造成的任何账号封禁、数据丢失或法律纠纷承担责任。
