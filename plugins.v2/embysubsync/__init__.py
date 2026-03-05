from typing import Any, Dict, List
from app.core.event import EventManager, EventType
from app.plugins import _PluginBase

# 1. 适配订阅助手
try:
    from app.modules.subscription import SubscriptionHelper as SubHelper
except ImportError:
    try:
        from app.modules.subscription.sub_helper import SubHelper
    except ImportError:
        SubHelper = None

# 2. 动态获取事件类型，避开不存在的属性导致的崩溃
_EVENT_TYPE = getattr(EventType, "MediaAddedSuccess", getattr(EventType, "MediaAdded", None))

class EmbySubSync(_PluginBase):
    __name__ = "Emby 订阅同步"
    __description__ = "监控 Emby 入库通知，自动同步更新电视剧订阅进度。"
    __author__ = "BigApple96"
    __version__ = "1.2.9"

    def init_plugin(self, config: dict = None):
        self.enabled = config.get("enabled") if config else True

    def get_event_filters(self) -> List[EventType]:
        # 返回系统支持的事件类型
        return [_EVENT_TYPE] if _EVENT_TYPE else []

    def get_plugin_config(self) -> List[dict]:
        return [{"name": "enabled", "type": "switch", "label": "启用自动同步", "default": True}]

    # 使用 getattr 动态绑定装饰器，防止类加载时报错
    @EventManager.register(_EVENT_TYPE)
    def on_event(self, event_data: Dict[str, Any]):
        """处理入库成功后的进度同步"""
        if not self.enabled or not event_data or not SubHelper:
            return

        # 仅处理电视剧分类
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

        if not subs:
            return

        for sub in subs:
            is_match = False
            if tmdb_id and sub.get("tmdb_id") and str(sub.get("tmdb_id")) == str(tmdb_id):
                is_match = True
            elif sub.get("title") == title:
                is_match = True
            
            if is_match and int(sub.get("season") or 0) == season:
                current_saved_ep = int(sub.get("current_episode") or 0)
                if episode > current_saved_ep:
                    sh.update_subscription(sub.get("id"), {"current_episode": episode})
                    self.info(f"【EmbySubSync】《{title}》订阅进度已同步至第 {episode} 集")
                break

    def stop_service(self):
        pass
