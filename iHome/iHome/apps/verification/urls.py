from django.urls import re_path
from verification import views

urlpatterns = [
    # 图形验证码
    re_path(r'^api/v1.0/imagecode$', views.ImageCodeView.as_view()),
    # 短信验证码
    re_path(r'^api/v1.0/sms$', views.SMSCodeView.as_view()),
]