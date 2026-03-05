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
    # 插件名称
    plugin_name = "Emby入库刷新"
    # 插件描述
    plugin_desc = "根据Emby的入库通知刷新已订阅的电视剧集数"
    # 插件图标
    plugin_icon = "https://raw.githubusercontent.com/jxxghp/MoviePilot-Plugins/refs/heads/main/icons/cloud.png"
    # 插件版本
    plugin_version = "1.3.1"
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

    # 私有属性
    _enabled = False
    _event_type = None

    def init_plugin(self, config: dict = None):
        """初始化"""
        if config:
            self._enabled = config.get("enabled")
        
        # 动态匹配事件类型并手动注册
        target_events = ["TransferComplete", "MediaAddedSuccess", "MediaAdded"]
        self._event_type = None
        for name in target_events:
            if hasattr(EventType, name):
                self._event_type = getattr(EventType, name)
                # 手动注册事件回调
                EventManager.register(self._event_type)(self.on_event)
                self.info(f"【EmbySubSync】已成功监听事件: {name}")
                break

    def get_form(self) -> List[dict]:
        """获取配置表单"""
        return [
            {
                "name": "enabled",
                "type": "switch",
                "label": "启用自动同步",
                "default": False
            }
        ]

    def get_state(self) -> bool:
        """获取插件状态"""
        return self._enabled

    def get_event_filters(self) -> List[EventType]:
        """获取事件过滤"""
        if not self._enabled:
            return []
        return [self._event_type] if self._event_type else []

    def on_event(self, event_data: Dict[str, Any]):
        """事件回调"""
        if not self._enabled or not event_data or not SubHelper:
            return

        # 提取元数据
        meta = event_data.get("meta") or event_data
        category = event_data.get("category") or (meta.get("category") if isinstance(meta, dict) else None)
        
        # 仅处理电视剧
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
            # 匹配策略：优先 TMDB ID，其次标题
            if tmdb_id and sub.get("tmdb_id") and str(sub.get("tmdb_id")) == str(tmdb_id):
                is_match = True
            elif sub.get("title") == title:
                is_match = True
            
            # 如果匹配成功且季号一致
            if is_match and int(sub.get("season") or 0) == season:
                curr_ep = int(sub.get("current_episode") or 0)
                # 仅当入库集数大于当前记录集数时更新
                if episode > curr_ep:
                    sh.update_subscription(sub.get("id"), {"current_episode": episode})
                    self.info(f"【EmbySubSync】《{title}》同步成功: 第 {episode} 集")
                break

    def get_api(self) -> List[dict]:
        """获取API"""
        return []

    def get_page(self) -> List[dict]:
        """获取页面"""
        return []

    def stop_service(self):
        """停止服务"""
        pass
