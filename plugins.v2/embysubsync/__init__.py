from typing import Any, Dict, List, Tuple
from app.schemas import WebhookEventInfo
from app.schemas.types import EventType
from app.plugins import _PluginBase
from app.log import logger
from app.chain.subscribe import SubscribeOper
from app.plugins.subscribe import SyncHandler

# 适配订阅助手
try:
    from app.modules.subscription.sub_helper import SubHelper
except ImportError:
    try:
        from app.modules.subscription import SubscriptionHelper as SubHelper
    except ImportError:
        SubHelper = None

class EmbySubSync(_PluginBase):
    # 插件名称
    plugin_name = "Emby入库刷新"
    # 插件描述
    plugin_desc = "根据Emby的入库通知刷新已订阅的电视剧集数"
    # 插件图标
    plugin_icon = "https://raw.githubusercontent.com/jxxghp/MoviePilot-Plugins/refs/heads/main/icons/cloud.png"
    # 插件版本
    plugin_version = "1.3.8"
    # 插件作者
    plugin_author = "BigApple96"
    # 作者主页
    author_url = "https://github.com/BigApple96"
    # 插件配置项ID前缀
    plugin_config_prefix = "embysubsync_"
    # 加载顺序
    plugin_order = 20
    # 可使用的用户级别
    auth_level = 1

    # 私有变量
    _enble = False
    _webhook_actions = {
        "library.new": "新入库"
    }

    def init_plugin(self, config: dict = None):
        if config
            self._enble = config.get("enabled")

    @eventmanager.register(EventType.WebhookMessage)
    def send(self, event: Event):
        """
        发送通知消息
        """
        if not self._enabled:
            return
        
        event_info: WebhookEventInfo = event.event_data
        if not event_info:
            return

        # 不在支持范围不处理
        if not self._webhook_actions.get(event_info.event):
            return

        subscribe_oper = SubscribeOper(db=db)
        sub_item = None

        # 1. 优先使用 TMDB ID 匹配，这是最准确的
        if event_info.tmdb_id:
            # 注意：不同版本的 MP 这里的 API 名称可能略有不同，通常为 get_by_tmdbid 或 list 过滤
            subs = subscribe_oper.list() or []
            sub_item = next((s for s in subs if str(s.tmdb_id) == str(event_info.tmdb_id)), None)

        # 2. 如果没找到，尝试通过标题匹配
        if not sub_item and event_info.item_name:
            sub_item = subscribe_oper.get_by_title(event_info.item_name)

        if sub_item:
            logger.info(f"已匹配到订阅任务：{sub_item.name} (ID: {sub_item.id})")
            
            # 实例化订阅处理器
            sync_handler = SyncHandler()
            
            # 准备当前已有的媒体信息 (以《太平年》S1E2为例)
            # 构造格式为 {季号: [集数列表]}
            exist_media = {event_info.season_id: [event_info.episode_id]}

            # 入库后立即触发搜索（例如洗版）
            sync_handler.search(sub=sub_item, media_info=sub_item)

    def get_state(self) -> bool: return self._enabled
    def stop_service(self): pass

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        """
        拼装插件配置页面，严格遵循模板
        """
        return [
            {
                "component": "VForm",
                "content": [
                    {
                        "component": "VRow",
                        "content": [
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 12},
                                "content": [
                                    {
                                        "component": "VSwitch",
                                        "props": {
                                            "model": "enabled",
                                            "label": "启用插件",
                                        },
                                    }
                                ],
                            }
                        ],
                    }
                ],
            }
        ], {"enabled": True}

    def get_api(self) -> List[Dict[str, Any]]:
        """获取插件 API 接口定义"""
        return []

    def get_page(self) -> List[Dict[str, Any]]:
        """获取插件页面定义"""
        return []
