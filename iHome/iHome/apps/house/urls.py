from django.urls import re_path
from house import views

urlpatterns = [
    # 城区列表
    re_path(r'^api/v1.0/areas$', views.AreasListView.as_view()),
    # 发布房源
    re_path(r'^api/v1.0/houses$', views.PostHouses.as_view()),
    # 上传房屋图片
    re_path(r'^api/v1.0/houses/(?P<house_id>\d+)/images$', views.UploadHouseImage.as_view()),
    # 展示登录用户的所有房屋
    re_path(r'^api/v1.0/user/houses$', views.ShowMyHouses.as_view()),
    # 首页房屋推荐
    re_path(r'^api/v1.0/houses/index$', views.RecommendHouses.as_view()),
    # 首页房屋搜索
    # re_path(r'^api/v1.0/houses$', views.SearchHouses.as_view()),
    # 房屋详情展示
    re_path(r'^api/v1.0/houses/(?P<house_id>\d+)$', views.HouseDetail.as_view()),
]
