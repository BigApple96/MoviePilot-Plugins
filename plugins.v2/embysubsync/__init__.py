from typing import Any, Dict, List
import logging
from app.core.event import EventManager, EventType
from app.plugins import _PluginBase

# 1. 自动适配订阅助手路径
try:
    from app.modules.subscription import SubscriptionHelper as SubHelper
except ImportError:
    try:
        from app.modules.subscription.sub_helper import SubHelper
    except ImportError:
        try:
            from app.modules.tmdb.sub_helper import SubHelper
        except ImportError:
            SubHelper = None

# 2. 自动适配事件名称 (根据报错来看，你的环境可能是 MediaAdded)
# 我们遍历所有可能的名称，直到找到一个存在的
EVENT_NAME = None
for name in ["MediaAddedSuccess", "MediaAdded", "MEDIA_ADDED"]:
    if hasattr(EventType, name):
        EVENT_NAME = getattr(EventType, name)
        break

class EmbySubSync(_PluginBase):
    __name__ = "Emby 订阅同步"
    __description__ = "监控 Emby 入库通知，自动同步更新电视剧订阅进度。"
    __author__ = "BigApple96"
    __version__ = "1.2.1"

    def init_plugin(self, config: dict = None):
        self.enabled = config.get("enabled") if config else True

    def get_event_filters(self) -> List[EventType]:
        return [EVENT_NAME] if EVENT_NAME else []

    def get_plugin_config(self) -> List[dict]:
        return [{"name": "enabled", "type": "switch", "label": "启用自动同步", "default": True}]

    # 这里不再使用装饰器，因为 EVENT_NAME 是动态的，改在 init 或 register 中处理
    def register_event(self):
        if EVENT_NAME:
            @EventManager.register(EVENT_NAME)
            def handle_event(event_data: Dict[str, Any]):
                self.process_sync(event_data)
        else:
            self.error("【EmbySubSync】错误：无法在当前系统找到有效的入库事件类型")

    def process_sync(self, event_data: Dict[str, Any]):
        if not self.enabled or not event_data or not SubHelper:
            return

        if event_data.get("category") != "tv":
            return

        title = event_data.get("title")
        season = int(event_data.get("season") or 0)
        episode = int(event_data.get("episode") or 0)
        tmdb_id = event_data.get("tmdb_id")

        self.info(f"【EmbySubSync】检测到入库: {title} S{season}E{episode}")

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
                    self.info(f"【EmbySubSync】已自动同步《{title}》进度至 {episode} 集")
                break

    # 兼容 MP 的事件注册
    @EventManager.register(getattr(EventType, "MediaAddedSuccess", getattr(EventType, "MediaAdded", None)))
    def on_event(self, event_data: Dict[str, Any]):
        self.process_sync(event_data)

    def stop_service(self):
        pass
