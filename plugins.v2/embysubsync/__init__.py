from typing import Any, Dict, List
from app.core.event import EventManager, EventType
from app.plugins import _PluginBase

# 尝试 V2 订阅模块的多种可能路径
try:
    from app.modules.subscription import SubscriptionHelper as SubHelper
except ImportError:
    try:
        from app.modules.subscription.sub_helper import SubHelper
    except ImportError:
        SubHelper = None

class EmbySubSync(_PluginBase):
    __name__ = "Emby 订阅同步"
    __description__ = "监控 Emby 入库通知，自动更新订阅进度。"
    __author__ = "BigApple96"
    __version__ = "1.2.1" # 必须改这个，即便 package.json 不改

    def init_plugin(self, config: dict = None):
        self.enabled = config.get("enabled") if config else True

    def get_event_filters(self) -> List[EventType]:
        # 显式指向 V2 入库成功事件
        return [EventType.MediaAddedSuccess]

    def get_plugin_config(self) -> List[dict]:
        return [{"name": "enabled", "type": "switch", "label": "启用自动同步", "default": True}]

    @EventManager.register(EventType.MediaAddedSuccess)
    def handle_event(self, event_data: Dict[str, Any]):
        if not self.enabled or not event_data or not SubHelper:
            return

        if event_data.get("category") != "tv":
            return

        title = event_data.get("title")
        season = int(event_data.get("season") or 0)
        episode = int(event_data.get("episode") or 0)
        tmdb_id = event_data.get("tmdb_id")

        self.info(f"【EmbySubSync】收到入库: {title} S{season}E{episode}")

        sh = SubHelper()
        try:
            subs = sh.list_subscriptions()
        except:
            subs = sh.get_subscriptions()

        if not subs: return

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
                    self.info(f"【EmbySubSync】已更新《{title}》进度至 {episode} 集")
                break

    def stop_service(self):
        pass
