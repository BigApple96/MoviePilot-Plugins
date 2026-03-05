from typing import Any, Dict, List
from app.core.event import EventManager, EventType
from app.plugins import _PluginBase

# 适配订阅助手
try:
    from app.modules.subscription.sub_helper import SubHelper
except ImportError:
    try:
        from app.modules.subscription import SubscriptionHelper as SubHelper
    except ImportError:
        SubHelper = None

class EmbySubSync(_PluginBase):
    __name__ = "Emby 订阅同步"
    __description__ = "监控入库或转移事件，自动同步更新电视剧订阅进度。"
    __author__ = "BigApple96"
    __version__ = "1.4.0"

    def init_plugin(self, config: dict = None):
        self.enabled = config.get("enabled") if config else True
        
        # 动态匹配事件类型，解决枚举名不一致导致的报错
        target_events = ["TransferComplete", "MediaAddedSuccess", "MediaAdded", "MEDIA_ADDED"]
        matched_events = []
        
        for name in target_events:
            if hasattr(EventType, name):
                etype = getattr(EventType, name)
                # 手动注册事件处理函数
                EventManager.register(etype)(self.on_event)
                matched_events.append(name)
        
        if matched_events:
            self.info(f"【EmbySubSync】插件启动成功，已挂载事件: {', '.join(matched_events)}")
        else:
            self.error("【EmbySubSync】警告：未能匹配到任何系统入库事件，插件可能无法自动触发。")

    def get_event_filters(self) -> List[EventType]:
        # 这种方式可以让插件在 WebUI 的事件过滤中正常显示
        filters = []
        for name in ["TransferComplete", "MediaAddedSuccess", "MediaAdded"]:
            if hasattr(EventType, name):
                filters.append(getattr(EventType, name))
        return filters

    def get_plugin_config(self) -> List[dict]:
        return [{"name": "enabled", "type": "switch", "label": "启用自动同步", "default": True}]

    def on_event(self, event_data: Dict[str, Any]):
        """处理进度同步的核心方法"""
        if not self.enabled or not event_data or not SubHelper:
            return

        # 获取元数据
        meta = event_data.get("meta") or event_data
        # 兼容不同事件的数据结构
        category = event_data.get("category") or (meta.get("category") if isinstance(meta, dict) else None)
        
        if category != "tv":
            return

        title = event_data.get("title") or meta.get("title")
        season = int(event_data.get("season") or meta.get("season") or 0)
        episode = int(event_data.get("episode") or meta.get("episode") or 0)
        tmdb_id = event_data.get("tmdb_id") or meta.get("tmdb_id")

        if not title or not episode:
            return

        sh = SubHelper()
        try:
            subs = sh.list_subscriptions()
        except:
            subs = sh.get_subscriptions()

        if not subs:
            return

        for sub in subs
