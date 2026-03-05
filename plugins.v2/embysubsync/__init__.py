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
    # 对齐新版 V2 的元数据要求
    plugin_name = "Emby 订阅同步"
    plugin_desc = "监控入库或转移事件，自动同步更新电视剧订阅进度。"
    plugin_author = "BigApple96"
    plugin_version = "1.5.0"

    def init_plugin(self, config: dict = None):
        self.enabled = config.get("enabled") if config else True
        
        # 动态匹配事件类型并手动注册
        target_events = ["TransferComplete", "MediaAddedSuccess", "MediaAdded"]
        self.event_type = None
        for name in target_events:
            if hasattr(EventType, name):
                self.event_type = getattr(EventType, name)
                EventManager.register(self.event_type)(self.on_event)
                self.info(f"【EmbySubSync】已成功监听事件: {name}")
                break

    # --- 必须实现的抽象方法 (Abstract Methods) ---
    def get_api(self) -> List[dict]:
        """补全基类要求"""
        return []

    def get_form(self) -> List[dict]:
        """补全基类要求，即原 get_plugin_config"""
        return [
            {
                "name": "enabled",
                "type": "switch",
                "label": "启用自动同步",
                "default": True
            }
        ]

    def get_page(self) -> List[dict]:
        """补全基类要求"""
        return []

    def get_state(self) -> bool:
        """补全基类要求"""
        return self.enabled

    # --- 逻辑处理 ---
    def get_event_filters(self) -> List[EventType]:
        return [self.event_type] if self.event_type else []

    def on_event(self, event_data: Dict[str, Any]):
        if not self.enabled or not event_data or not SubHelper:
            return

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
