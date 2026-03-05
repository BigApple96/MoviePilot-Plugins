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
    __version__ = "1.4.1"

    def init_plugin(self, config: dict = None):
        self.enabled = config.get("enabled") if config else True
        
        # 动态匹配事件类型，手动注册
        target_events = ["TransferComplete", "MediaAddedSuccess", "MediaAdded", "MEDIA_ADDED"]
        matched_events = []
        
        for name in target_events:
            if hasattr(EventType, name):
                etype = getattr(EventType, name)
                # 手动注册
                EventManager.register(etype)(self.on_event)
                matched_events.append(name)
        
        if matched_events:
            self.info(f"【EmbySubSync】插件已启动，监听事件: {', '.join(matched_events)}")
        else:
            self.error("【EmbySubSync】启动失败：无法匹配系统入库事件类型")

    def get_event_filters(self) -> List[EventType]:
        filters = []
        for name in ["TransferComplete", "MediaAddedSuccess", "MediaAdded"]:
            if hasattr(EventType, name):
                filters.append(getattr(EventType, name))
        return filters

    def get_plugin_config(self) -> List[dict]:
        return [{"name": "enabled", "type": "switch", "label": "启用自动同步", "default": True}]

    def on_event(self, event_data: Dict[str, Any]):
        """处理进度同步"""
        if not self.enabled or not event_data or not SubHelper:
            return

        # 提取元数据
        meta = event_data.get("meta") or event_data
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

        # 核心循环，已补全冒号
        for sub in subs:
            is_match = False
            if tmdb_id and sub.get("tmdb_id") and str(sub.get("tmdb_id")) == str(tmdb_id):
                is_match = True
            elif sub.get("title") == title:
                is_match = True
            
            if is_match and int(sub.get("season") or 0) == season:
                curr_ep = int(sub.get("current_episode") or 0)
                if episode > curr_ep:
                    sh.update_subscription(sub.get("id"), {"current_episode": episode})
                    self.info(f"【EmbySubSync】《{title}》同步成功: 第 {episode} 集")
                break

    def stop_service(self):
        pass
