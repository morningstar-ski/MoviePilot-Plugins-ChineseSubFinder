from functools import lru_cache
from pathlib import Path
from typing import List, Tuple, Dict, Any

from app.core.config import settings
from app.core.context import MediaInfo
from app.core.event import eventmanager, Event
from app.log import logger
from app.plugins import _PluginBase
from app.schemas import TransferInfo, FileItem
from app.schemas.types import EventType, MediaType
from app.utils.http import RequestUtils
from app.utils.system import SystemUtils


class ChineseSubFinder(_PluginBase):
    # 插件名称
    plugin_name = "ChineseSubFinder"
    # 插件描述
    plugin_desc = "整理入库时通知 ChineseSubFinder 下载字幕（内置中文影视剧多重过滤，杜绝误刮与死循环）"
    # 插件图标
    plugin_icon = "chinesesubfinder.png"
    # 插件版本
    plugin_version = "2.1"
    # 插件作者
    plugin_author = "morningstar-ski"
    # 作者主页
    author_url = "https://github.com/morningstar-ski/MoviePilot-Plugins-ChineseSubFinder"
    # 插件配置项ID前缀
    plugin_config_prefix = "chinesesubfinder_"
    # 加载顺序
    plugin_order = 5
    # 可使用的用户级别
    auth_level = 1

    # 私有属性
    _save_tmp_path = None
    _enabled = False
    _host = None
    _api_key = None
    _remote_path = None
    _local_path = None

    def init_plugin(self, config: dict = None):
        self._save_tmp_path = settings.TEMP_PATH
        if config:
            self._enabled = config.get("enabled")
            self._api_key = config.get("api_key")
            self._host = config.get("host")
            if self._host:
                if not self._host.startswith("http"):
                    self._host = "http://" + self._host
                if not self._host.endswith("/"):
                    self._host = self._host + "/"
            self._local_path = config.get("local_path")
            self._remote_path = config.get("remote_path")

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        pass

    def get_api(self) -> List[Dict[str, Any]]:
        pass

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        return [
            {
                "component": "VForm",
                "content": [
                    {
                        "component": "VRow",
                        "content": [
                            {
                                "component": "VCol",
                                "props": {
                                    "cols": 12,
                                    "md": 6
                                },
                                "content": [
                                    {
                                        "component": "VSwitch",
                                        "props": {
                                            "model": "enabled",
                                            "label": "启用插件",
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        "component": "VRow",
                        "content": [
                            {
                                "component": "VCol",
                                "props": {
                                    "cols": 12,
                                    "md": 6
                                },
                                "content": [
                                    {
                                        "component": "VTextField",
                                        "props": {
                                            "model": "host",
                                            "label": "服务器"
                                        }
                                    }
                                ]
                            },
                            {
                                "component": "VCol",
                                "props": {
                                    "cols": 12,
                                    "md": 6
                                },
                                "content": [
                                    {
                                        "component": "VTextField",
                                        "props": {
                                            "model": "api_key",
                                            "label": "API密钥"
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        "component": "VRow",
                        "content": [
                            {
                                "component": "VCol",
                                "props": {
                                    "cols": 12,
                                    "md": 6
                                },
                                "content": [
                                    {
                                        "component": "VTextField",
                                        "props": {
                                            "model": "local_path",
                                            "label": "本地路径"
                                        }
                                    }
                                ]
                            },
                            {
                                "component": "VCol",
                                "props": {
                                    "cols": 12,
                                    "md": 6
                                },
                                "content": [
                                    {
                                        "component": "VTextField",
                                        "props": {
                                            "model": "remote_path",
                                            "label": "远端路径"
                                        }
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        ], {
            "enabled": False,
            "host": "",
            "api_key": "",
            "local_path": "",
            "remote_path": ""
        }

    def get_state(self) -> bool:
        return self._enabled

    def get_page(self) -> List[dict]:
        pass

    def stop_service(self):
        pass

    def _is_chinese_media(self, item_media: MediaInfo, item_transfer: TransferInfo) -> bool:
        """
        多重判定媒体是否为中文影视剧（华语/国产/国漫/港剧/台剧等）。
        若判定为中文内容，返回 True 彻底拦截推送，防止误刮和死循环。
        """
        try:
            # 1. 检查原始语言
            orig_lang = getattr(item_media, "original_language", "") or ""
            if isinstance(orig_lang, str):
                orig_lang = orig_lang.lower().strip()
                if orig_lang in ["zh", "cn", "zho", "chi", "cmn", "yue", "zh-cn", "zh-tw", "zh-hk"]:
                    logger.info(f"ChineseSubFinder: 检测到原始语言为中文 ({orig_lang})，跳过字幕推送: {getattr(item_media, 'title', '')}")
                    return True

            # 2. 检查分类或二级分类名称
            category = getattr(item_transfer, "category", "") or getattr(item_media, "category", "") or ""
            if isinstance(category, str) and category:
                chinese_keywords = ["国产", "华语", "国剧", "国漫", "港台", "港剧", "台剧", "大陆", "内地", "中国"]
                for kw in chinese_keywords:
                    if kw in category:
                        logger.info(f"ChineseSubFinder: 检测到媒体分类为中文/华语 ({category})，跳过字幕推送: {getattr(item_media, 'title', '')}")
                        return True

            # 3. 检查目的存储路径关键字
            target_dir = getattr(item_transfer, "target_diritem", None)
            target_path = getattr(target_dir, "path", "") if target_dir else ""
            if not target_path and hasattr(item_transfer, "target_path"):
                target_path = str(item_transfer.target_path or "")

            if target_path:
                norm_path = target_path.replace("\\", "/")
                path_keywords = ["/国产剧/", "/华语电影/", "/国漫/", "/国产动画/", "/华语/", "/港剧/", "/台剧/", "/国产/"]
                for pkw in path_keywords:
                    if pkw in norm_path:
                        logger.info(f"ChineseSubFinder: 检测到目标路径属于中文分类 ({pkw})，跳过字幕推送: {norm_path}")
                        return True

        except Exception as e:
            logger.warning(f"ChineseSubFinder: 判定中文媒体逻辑异常: {e}")

        return False

    @eventmanager.register(EventType.TransferComplete)
    def download(self, event: Event):
        """
        调用ChineseSubFinder下载字幕
        """
        if not self._enabled or not self._host or not self._api_key:
            return
        item = event.event_data
        if not item:
            return

        # 媒体信息
        item_media: MediaInfo = item.get("mediainfo")
        # 转移信息
        item_transfer: TransferInfo = item.get("transferinfo")

        # 核心多重过滤：严防误刮中文剧
        if self._is_chinese_media(item_media, item_transfer):
            return

        # 请求地址
        req_url = "%sapi/v1/add-job" % self._host

        # 类型
        item_type = item_media.type
        # 目的路径
        item_dest: FileItem = item_transfer.target_diritem
        # 是否蓝光原盘
        item_bluray = SystemUtils.is_bluray_dir(Path(item_dest.path))
        # 文件清单
        item_file_list = item_transfer.file_list_new

        if item_bluray:
            # 蓝光原盘虚拟个文件
            item_file_list = ["%s.mp4" % Path(item_dest.path) / item_dest.name]

        for file_path in item_file_list:
            # 路径替换
            if self._local_path and self._remote_path and file_path.startswith(self._local_path):
                file_path = file_path.replace(self._local_path, self._remote_path).replace('\\', '/')

            # 调用CSF下载字幕
            self.__request_csf(req_url=req_url,
                               file_path=file_path,
                               item_type=0 if item_type == MediaType.MOVIE else 1,
                               item_bluray=item_bluray)

    @lru_cache(maxsize=128)
    def __request_csf(self, req_url, file_path, item_type, item_bluray):
        # 一个名称只建一个任务
        logger.info("ChineseSubFinder: 通知ChineseSubFinder下载外语字幕: %s" % file_path)
        params = {
            "video_type": item_type,
            "physical_video_file_full_path": file_path,
            "task_priority_level": 3,
            "media_server_inside_video_id": "",
            "is_bluray": item_bluray
        }
        try:
            res = RequestUtils(headers={
                "Authorization": "Bearer %s" % self._api_key
            }).post(req_url, json=params)
            if not res or res.status_code != 200:
                logger.error("ChineseSubFinder: 调用ChineseSubFinder API失败！")
            else:
                if res.text:
                    job_id = res.json().get("job_id")
                    message = res.json().get("message")
                    if not job_id:
                        logger.warning("ChineseSubFinder: ChineseSubFinder下载字幕出错：%s" % message)
                    else:
                        logger.info("ChineseSubFinder: ChineseSubFinder任务添加成功：%s" % job_id)
                elif res.status_code != 200:
                    logger.warning(f"ChineseSubFinder: ChineseSubFinder调用出错：{res.status_code} - {res.reason}")
        except Exception as e:
            logger.error("ChineseSubFinder: 连接ChineseSubFinder出错：" + str(e))
