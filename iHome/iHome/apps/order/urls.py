from django.urls import re_path
from order.views import *

urlpatterns = [

    re_path(r'^api/v1.0/orders$', OrderView.as_view()),

    re_path(r'^api/v1.0/orders/(?P<order_id>\d+)/status$', OrderView.as_view()),

    re_path(r'^api/v1.0/orders/(?P<order_id>\d+)/comment$', OrderComment.as_view()),

]
