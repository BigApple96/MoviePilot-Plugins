from typing import Any, Dict, List, Tuple
from app.core.event import EventManager, EventType
from app.plugins import _PluginBase
from app.log import logger

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
    plugin_version = "1.3.7"
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

    def init_plugin(self, config: dict = None):
        self.enabled = config.get("enabled") if config else True
        
        # 动态获取当前环境支持的事件类型
        self.event_types = []
        for name in ["TransferComplete", "MediaAddedSuccess", "MediaAdded"]:
            if hasattr(EventType, name):
                self.event_types.append(getattr(EventType, name))
        
        if self.event_types:
            logger.info(f"【EmbySubSync】初始化成功，将通过系统分发监听 {len(self.event_types)} 个事件")
        else:
            logger.error("【EmbySubSync】初始化失败：未找到可用的事件枚举")

    def get_event_filters(self) -> List[EventType]:
        """
        这是 MoviePilot 核心调用的标准接口。
        系统会自动将此处声明的事件分发给本类的回调函数。
        """
        return self.event_types

    def callback(self, event_type: EventType, event_data: Dict[str, Any]):
        """
        这是插件基类定义的标准回调入口。
        不再依赖 register 装饰器，直接接收系统分发的事件。
        """
        if not self.enabled or not event_data or not SubHelper:
            return

        logger.info(f"【EmbySubSync】收到事件通知: {event_type}")
        
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

        # 执行同步
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
                    logger.info(f"【EmbySubSync】《{title}》同步成功: 第 {episode} 集")
                break

    def get_state(self) -> bool: return True
    def stop_service(self): pass

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        """
        拼装插件配置页面，严格遵循模板
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
        ], {"enabled": True}

    def get_api(self) -> List[Dict[str, Any]]:
        """获取插件 API 接口定义"""
        return []

    def get_page(self) -> List[Dict[str, Any]]:
        """获取插件页面定义"""
        return []
