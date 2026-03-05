from typing import Any, Dict, List
from app.core.event import EventManager, EventType
from app.plugins import _PluginBase

# 适配 MoviePilot V2 最新的订阅模块路径
try:
    from app.modules.subscription.sub_helper import SubHelper
except ImportError:
    # 备用路径，防止某些特定版本差异
    try:
        from app.modules.tmdb.sub_helper import SubHelper
    except ImportError:
        SubHelper = None

class EmbySubSync(_PluginBase):
    __name__ = "Emby 订阅同步"
    __description__ = "监控 Emby 入库通知，自动同步更新电视剧订阅进度。"
    __author__ = "BigApple96"
    __version__ = "1.0.0"

    def init_plugin(self, config: dict = None):
        self.enabled = config.get("enabled") if config else True

    def get_event_filters(self) -> List[EventType]:
        # 确保只在 V2 下运行，使用入库成功事件
        return [EventType.MediaAddedSuccess]

    def get_plugin_config(self) -> List[dict]:
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
        if not self.enabled or not event_data or not SubHelper:
            if not SubHelper:
                self.error("【EmbySubSync】未找到 SubHelper 模块，插件无法运行")
            return

        if event_data.get("category") != "tv":
            return

        title = event_data.get("title")
        season = int(event_data.get("season") or 0)
        episode = int(event_data.get("episode") or 0)
        tmdb_id = event_data.get("tmdb_id")

        self.info(f"【EmbySubSync】收到入库通知: {title} S{season}E{episode}")

        sh = SubHelper()
        # 获取订阅列表
        try:
            subs = sh.list_subscriptions()
        except AttributeError:
            subs = sh.get_subscriptions()

        if not subs:
            return

        for sub in subs:
            match = False
            if tmdb_id and sub.get("tmdb_id") and str(sub.get("tmdb_id")) == str(tmdb_id):
                match = True
            elif sub.get("title") == title:
                match = True
            
            if match and int(sub.get("season") or 0) == season:
                curr = int(sub.get("current_episode") or 0)
                if episode > curr:
                    sh.update_subscription(sub.get("id"), {"current_episode": episode})
                    self.info(f"【EmbySubSync】《{title}》订阅进度已同步至第 {episode} 集")
                break

    def stop_service(self):
        pass
