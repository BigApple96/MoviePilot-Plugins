from typing import Any, Dict, List
from app.core.event import EventManager, EventType
from app.plugins import _PluginBase

# 尝试导入订阅助手，兼容不同版本路径
try:
    from app.modules.tmdb.sub_helper import SubHelper
except ImportError:
    try:
        from app.helper.sub import SubHelper
    except ImportError:
        SubHelper = None

class EmbySubSync(_PluginBase):
    __name__ = "Emby 订阅同步"
    __description__ = "监控 Emby 入库通知，自动同步更新电视剧订阅进度。"
    __author__ = "BigApple96"
    __version__ = "1.0.0"

    def init_plugin(self, config: dict = None):
        """初始化配置"""
        self.enabled = config.get("enabled") if config else True

    def get_event_filters(self) -> List[EventType]:
        """注册监听媒体入库事件"""
        return [EventType.MediaAdded]

    def get_plugin_config(self) -> List[dict]:
        """定义插件配置界面"""
        return [
            {
                "name": "enabled",
                "type": "switch",
                "label": "启用自动同步",
                "default": True
            }
        ]

    @EventManager.register(EventType.MediaAdded)
    def handle_event(self, event_data: Dict[str, Any]):
        """入库事件回调"""
        if not self.enabled or not event_data or not SubHelper:
            return

        # 仅处理电视剧（tv），忽略电影
        if event_data.get("category") != "tv":
            return

        title = event_data.get("title")
        season = int(event_data.get("season") or 0)
        episode = int(event_data.get("episode") or 0)
        tmdb_id = event_data.get("tmdb_id")

        self.info(f"【EmbySubSync】收到入库通知: {title} S{season}E{episode}")

        # 实例化订阅助手
        sub_helper = SubHelper()
        try:
            # 兼容不同版本的订阅列表获取
            subs = sub_helper.list_subscriptions()
        except AttributeError:
            subs = sub_helper.get_subscriptions()

        if not subs:
            return

        for sub in subs:
            # 匹配逻辑：优先使用 TMDB ID，其次使用标题
            is_match = False
            if tmdb_id and sub.get("tmdb_id") and str(sub.get("tmdb_id")) == str(tmdb_id):
                is_match = True
            elif sub.get("title") == title:
                is_match = True
            
            # 匹配成功且季号一致时更新
            if is_match and int(sub.get("season") or 0) == season:
                current_ep = int(sub.get("current_episode") or 0)
                if episode > current_ep:
                    sub_helper.update_subscription(sub.get("id"), {"current_episode": episode})
                    self.info(f"【EmbySubSync】《{title}》订阅进度已更新: 第 {current_ep} 集 -> 第 {episode} 集")
                break

    def stop_service(self):
        """停止服务（清理工作）"""
        pass
