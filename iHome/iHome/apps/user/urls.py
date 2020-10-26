from django.urls import re_path
from user import views

urlpatterns = (
    # 注册
    re_path(r'^api/v1.0/users$', views.RegisterView.as_view()),
    # 登录
    re_path(r'^api/v1.0/session$', views.LoginView.as_view()),
    # 更改用户名
    re_path(r'^api/v1.0/user/name$', views.ChangeUsername.as_view()),
    # 验证用户实名制
    re_path(r'^api/v1.0/user/auth$', views.UserIdentivify.as_view()),
    # 个人主页
    re_path(r"^api/v1.0/user$", views.UserInfoView.as_view()),
    # 上传用户头像
    re_path(r'^api/v1.0/user/avatar$', views.AvatarView.as_view()),

)
