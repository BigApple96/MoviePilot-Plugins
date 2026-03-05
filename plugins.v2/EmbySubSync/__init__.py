from typing import Any, Dict, List
import logging
from app.plugins import _PluginBase
from app.core.event import EventManager, EventType

# 动态适配 MoviePilot V2 不同版本的导入路径
try:
    from app.modules.tmdb.sub_helper import SubHelper
except ImportError:
    try:
        from app.helper.sub import SubHelper
    except ImportError:
        SubHelper = None

class EmbySubSync(_PluginBase):
    # 插件元数据
    __name__ = "Emby 订阅同步"
    __description__ = "监控 Emby 入库通知，自动更新订阅中的已完成集数。"
    __author__ = "BigApple96"
    __version__ = "1.0.0"

    def init_plugin(self, config: dict = None):
        """插件初始化"""
        self.enabled = config.get("enabled") if config else True

    def get_event_filters(self) -> List[EventType]:
        """声明监听入库事件"""
        return [EventType.MediaAdded]

    def get_plugin_config(self) -> List[dict]:
        """定义 WebUI 配置项"""
        return [
            {
                "name": "enabled",
                "type": "switch",
                "label": "启用自动同步进度",
                "default": True
            }
        ]

    @EventManager.register(EventType.MediaAdded)
    def handle_event(self, event_data: Dict[str, Any]):
        """事件处理核心逻辑"""
        if not self.enabled or not event_data or not SubHelper:
            return

        # 仅处理电视剧
        if event_data.get("category") != "tv":
            return

        title = event_data.get("title")
        season = int(event_data.get("season") or 0)
        episode = int(event_data.get("episode") or 0)
        tmdb_id = event_data.get("tmdb_id")

        self.info(f"【Emby同步】检测到入库: {title} S{season}E{episode}")

        sh = SubHelper()
        # 兼容不同版本的订阅列表获取方法
        try:
            subs = sh.list_subscriptions()
        except AttributeError:
            subs = sh.get_subscriptions()

        if not subs:
            return

        for sub in subs:
            is_match = False
            # 1. 优先使用 TMDB ID 匹配
            if tmdb_id and sub.get("tmdb_id") and str(sub.get("tmdb_id")) == str(tmdb_id):
                is_match = True
            # 2. 其次使用标题匹配
            elif sub.get("title") == title:
                is_match = True
            
            # 3. 校验季号并更新进度
            if is_match and int(sub.get("season") or 0) == season:
                current_saved_ep = int(sub.get("current_episode") or 0)
                if episode > current_saved_ep:
                    sh.update_subscription(sub.get("id"), {"current_episode": episode})
                    self.info(f"【Emby同步】成功将《{title}》订阅进度更新至第 {episode} 集")
                break

    def stop_service(self):
        """停止服务"""
        pass

# 这一步非常重要，确保加载器能直接从包名找到类
__all__ = ["EmbySubSync"]
