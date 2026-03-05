from typing import Any, Dict, List
from app.core.event import EventManager, EventType
from app.plugins import _PluginBase

# 导入 V2 订阅助手
try:
    from app.modules.tmdb.sub_helper import SubHelper
except ImportError:
    from app.helper.sub import SubHelper

class EmbySubSync(_PluginBase):
    # 插件元数据
    __name__ = "Emby 订阅同步"
    __description__ = "监控 Emby 入库通知，自动同步更新电视剧订阅进度。"
    __author__ = "BigApple96"
    __version__ = "1.0.0"

    def init_plugin(self, config: dict = None):
        """初始化"""
        self.enabled = config.get("enabled") if config else True

    def get_event_filters(self) -> List[EventType]:
        """声明监听 V2 入库成功事件"""
        return [EventType.MediaAddedSuccess]

    def get_plugin_config(self) -> List[dict]:
        """插件配置项"""
        return [
            {
                "name": "enabled",
                "type": "switch",
                "label": "启用自动同步",
                "default": True
            }
        ]

    @EventManager.register(EventType.MediaAddedSuccess)
    def handle_event(self, event_data: Dict[str, Any]):
        """处理入库成功后的进度同步"""
        if not self.enabled or not event_data:
            return

        # 仅处理电视剧分类
        if event_data.get("category") != "tv":
            return

        title = event_data.get("title")
        season = int(event_data.get("season") or 0)
        episode = int(event_data.get("episode") or 0)
        tmdb_id = event_data
