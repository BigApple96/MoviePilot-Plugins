from typing import Any, Dict, List, Tuple
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
    # 插件名称
    plugin_name = "Emby入库刷新"
    # 插件描述
    plugin_desc = "根据Emby的入库通知刷新已订阅的电视剧集数"
    # 插件图标
    plugin_icon = "https://raw.githubusercontent.com/jxxghp/MoviePilot-Plugins/refs/heads/main/icons/cloud.png"
    # 插件版本
    plugin_version = "1.3.5"
    # 插件作者
    plugin_author = "BigApple96"
    # 作者主页
    author_url = "https://github.com/BigApple96"
    # 插件配置项ID前缀
    plugin_config_prefix = "embysubsync_"
    # 加载顺序
    plugin_order = 20
    # 可使用的用户级别
    auth_level = 1

    # 参数规范
    _enabled = False
    _event_types = []

    def init_plugin(self, config: dict = None):
        """初始化"""
        if config:
            self._enabled = config.get("enabled")
        
        # 识别支持的事件
        target_events = ["TransferComplete", "MediaAddedSuccess", "MediaAdded"]
        self._event_types = []
        for name in target_events:
            if hasattr(EventType, name):
                self._event_types.append(getattr(EventType, name))

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        """
        拼装插件配置页面，需要返回两块数据：1、页面配置；2、数据结构
        """
        return [
            {
                "component": "VForm",
                "content": [
                    {
                        "component": "VRow",
                        "content": [
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 12},
                                "content": [
                                    {
                                        "component": "VSwitch",
                                        "props": {
                                            "model": "enabled",
                                            "label": "启用插件",
                                        },
                                    }
                                ],
                            }
                        ],
                    }
                ],
            }
        ], {"enabled": False}

    def get_event_filters(self) -> List[EventType]:
        """获取事件过滤"""
        return self._event_types if self._enabled else []

    def on_event(self, event: EventType, event_data: Dict[str, Any]):
        """事件回调"""
        if not self._enabled or not event_data or not SubHelper:
            return

        # 数据提取
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

    def get_state(self) -> bool:
        """获取状态"""
        return self._enabled

    def stop_service(self):
        """停止服务"""
        pass
