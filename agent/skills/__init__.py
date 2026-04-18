# 引入管理器
from .context.location_skill import LocationPerceptionSkill
from .external.route_planning_skill import TransitRouteSkill
from .external.xhs_mcp_skill import XhsMcpSearchSkill
from .profile.rag_skill import RagSkill
from .profile.save_global_feedback_skill import SaveGlobalFeedbackSkill
from .profile.user_profile_skill import FindSimilarVibeSkill, UpdateUserProfileSkill, GetUserProfileSkill
from .skill_manager import skill_manager

# 引入各个具体的技能类
from .context.time_skill import TimePerceptionSkill
# from .context.location_skill import LocationPerceptionSkill  # 你可以按此模式完成定位技能
from .external.weather_skill import WeatherQuerySkill
# from .profile.user_profile_skill import UserProfileSkill     # 画像技能

# 1. 实例化技能
time_skill = TimePerceptionSkill()
weather_skill = WeatherQuerySkill()
location_skill = LocationPerceptionSkill()
route_plan_skill = TransitRouteSkill()
update_profile_skill = UpdateUserProfileSkill()
find_vibe_skill = FindSimilarVibeSkill()
xhs_search_skill = XhsMcpSearchSkill()
get_profile_skill = GetUserProfileSkill()
save_global_feedback_skill = SaveGlobalFeedbackSkill()
rag_skill = RagSkill()

# 2. 将技能注册到管理器中
skill_manager.register_skills([
    time_skill,
    weather_skill,
    location_skill,
    route_plan_skill,
    update_profile_skill,
    find_vibe_skill,
    xhs_search_skill,
    get_profile_skill,
    save_global_feedback_skill,
    rag_skill

    # 后续新增技能只需在这里添加一行即可

])

# 3. 对外暴露注册表
__all__ = ["skill_manager"]