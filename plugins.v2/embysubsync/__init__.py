from typing import Any, Dict, List
from app.core.event import EventManager, EventType
from app.plugins import _PluginBase

# 适配订阅助手路径
try:
    from app.modules.subscription.sub_helper import SubHelper
except ImportError:
    try:
        from app.modules.subscription import SubscriptionHelper as SubHelper
    except ImportError:
        SubHelper = None

class EmbySubSync(_PluginBase):
    __name__ = "Emby 订阅同步"
    __description__ = "监控文件转移完成或媒体入库，自动同步更新电视剧订阅进度。"
    __author__ = "BigApple96"
    __version__ = "1.3.8"

    def init_plugin(self, config: dict = None):
        self.enabled = config.get("enabled") if config else True

    def get_event_filters(self) -> List[EventType]:
        # 仿照 p115strgmsub，监听转移完成和媒体添加
        return [EventType.TransferComplete, EventType.MediaAdded]

    def get_plugin_config(self) -> List[dict]:
        return [{"name": "enabled", "type": "switch", "label": "启用自动同步", "default": True}]

    @EventManager.register(EventType.TransferComplete)
    def on_transfer_complete(self, event_data: Dict[str, Any]):
        """监听转移完成事件"""
        self.info("【EmbySubSync】收到转移完成通知，准备同步...")
        self.process_sync(event_data)

    @EventManager.register(EventType.MediaAdded)
    def on_media_added(self, event_data: Dict[str, Any]):
        """监听媒体添加事件"""
        self.info("【EmbySubSync】收到媒体入库通知抽，准备同步...")
        self.process_sync(event_data)

    def process_sync(self, event_data: Dict[str, Any]):
        if not self.enabled or not event_data or not SubHelper:
            return

        # 核心逻辑：提取标题、季、集
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
                current_saved_ep = int(sub.get("current_episode") or 0)
                if episode > current_saved_ep:
                    sh.update_subscription(sub.get("id"), {"current_episode": episode})
                    self.info(f"【EmbySubSync】《{title}》订阅进度同步成功：第 {episode} 集")
                break

    def stop_service(self):
        pass
