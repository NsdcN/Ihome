import datetime
import time

from django.shortcuts import render
from django.views import View


from house.models import Area
from django.http import JsonResponse
import json
from django.utils.decorators import method_decorator

from iHome.libs.qiniuyun.demo import Qiniuyun
from iHome.settings.dev import BASE_DIR
from iHome.utils.login_decorator import login_required
import logging

logger = logging.getLogger('django')
from house.models import House, HouseImage
from order.models import Order
from django.db.models import Q
from django.core.paginator import Paginator, EmptyPage
import os


# Create your views here.
# 展示所有地址类函数
class AreasListView(View):
    def get(self, request):
        area_list = []
        areas = Area.objects.all()
        for area in areas:
            area_dict = {'aid': area.id, 'aname': area.name}
            area_list.append(area_dict)

        # print(area_list)
        return JsonResponse({
            "errmsg": "获取成功",
            "errno": "0",
            "data": area_list

        })


# 发布房源，搜索房源
class PostHouses(View):
    # 发布房源
    @method_decorator(login_required)
    def post(self, request):
        # 获取参数
        dict = json.loads(request.body.decode())
        title = dict.get('title')
        price = dict.get('price')
        area_id = dict.get('area_id')
        address = dict.get('address')
        room_count = dict.get('room_count')
        acreage = dict.get('acreage')
        unit = dict.get('unit')
        capacity = dict.get('capacity')
        beds = dict.get('beds')
        deposit = dict.get('deposit')
        min_days = dict.get('min_days')
        max_days = dict.get('max_days')
        facility = dict.get('facility')
        # 校验参数
        if not all([title, price, area_id, address, room_count, acreage,
                    unit, capacity, beds, deposit, min_days, max_days, facility]):
            return JsonResponse({
                'errno': '4103',
                'errmsg': '缺少必传参数',
            })
        user = request.user
        # try:
        #     House.objects.get(user=user,
        #                       address=address)
        # except House.DoesNotExist:
        # 创建房屋表
        try:
            my_home = House.objects.create(
                user=user,
                price=price,
                area_id=area_id,
                address=address,
                room_count=room_count,
                acreage=acreage,
                unit=unit,
                capacity=capacity,
                beds=beds,
                deposit=deposit,
                min_days=min_days,
                max_days=max_days,
                title=title,
            )
            my_home.facility.set(facility)
        except Exception as e:
            logger.error(e)
            return JsonResponse({
                'errno': '4302',
                'errmsg': 'IOERR'
            })
        else:
            return JsonResponse({
                'errno': '0',
                'errmsg': 'ok',
                'house_id': my_home.id
            })
        # else:
        #     return JsonResponse({
        #         'errno': 4003,
        #         'errmsg': '该房间信息已经存在',
        #     })

    # 房屋搜索
    def get(self, request):
        # 接收参数
        aid = request.GET.get('aid')
        sd = request.GET.get('sd')  # 房间订房起始时间
        ed = request.GET.get('ed')  # 房间订房结束时间
        sk = request.GET.get('sk')  # 排序方式
        p = request.GET.get('p', 1)  # 页数，不传默认为1
        # 从用户选择的订房或者退房时间筛选符合用户的订单查询集
        try:
            orders = Order.objects.filter(
                Q(begin_date__gt=sd, begin_date__lt=ed) | Q(end_date__gt=sd, end_date__lt=ed)
            )
        except Exception:
            houses = House.objects.all()
        else:
        # 可能会存在很多个符合订单的重复的house对象，用set集合去重
            houses_in_order = set()
            for order in orders:
                houses_in_order.add(
                    order.house.id
                )

            if sk == 'new':
                houses = House.objects.filter(~Q(id__in=houses_in_order)).order_by('-create_time')
            else:
                houses = House.objects.filter(~Q(id__in=houses_in_order)).order_by(sk)

        # 继续筛选符合用户筛选地区的房间
        # houses_selected_area = []
        # for house in houses:

        # 如果用户不选择地区
        if aid:
            try:
                house_objs = houses.filter(area_id=aid)
                # houses_selected_area.append(house_obj)
            except House.DoesNotExist as e:
                logger.info(e)
                return JsonResponse({
                    'errno': '4003',
                    'errmsg': '没有查询到符合的房源'
                })
        else:
            house_objs = houses
            # 拿到所有符合用户筛选的房间，使用分页器展示
        paginator = Paginator(house_objs, 2)  # 指定每页展示2个
        total_page = paginator.num_pages

        try:
            per_page_house = paginator.page(p)  # 根据用户传入的页码得到每页的房屋对象
        except EmptyPage as e:
            print('空页')
            logger.info('空页')
            return JsonResponse({
                'errno': '4003',
                'errmsg': '按照当前筛选没有对象，空页'
            }
            )
        # 构建响应返回
        data = {}
        houses = []  # 最终用户数据列表
        for per_house in per_page_house:
            houses.append({
                'address': per_house.address,
                'area_name': per_house.area.name,
                'house_id': per_house.id,
                'img_url': per_house.index_image_url,
                'price': per_house.price,
                'room_count': per_house.room_count,
                'title': per_house.title,
                'user_avatar': 'http://qetrkfm0g.bkt.clouddn.com/' + per_house.user.avatar.url
            })
        data["houses"] = houses
        data["total_page"] = total_page
        return JsonResponse({
            'data': data,
            'errno': '0',
            'errmsg': '请求成功'
        })


# 上传房源图片
class UploadHouseImage(View):
    @method_decorator(login_required)
    def post(self, request, house_id):
        # 获取并校验参数
        image = request.FILES.get('house_image')
        cp_image = image.file.read()
        # house_image = json.loads(request.body.decode())
        if not cp_image:
            return JsonResponse({
                'errno': '4103',
                'errmsg': 'PARAMERR',
            })
        local_image_url = BASE_DIR + '/apps/house/houseimages/' + image.name
        with open(local_image_url, 'wb') as f:
            print(cp_image)
            f.write(cp_image)

        q = Qiniuyun()
        key = q.uploadimage(local_image_url)
        web_image_url = q.get_img_url(key)
        # 尝试写入用户数据，
        try:
            my_house = House.objects.get(id=house_id)
            # 判断是否存在房屋首页，存在则添加到house_image表中，不存在就添加到house表中
            if my_house.index_image_url:
                try:
                    HouseImage.objects.create(house_id=house_id, url=web_image_url)
                    os.remove(local_image_url)
                    return JsonResponse({
                        'errno': '0',
                        'errmsg': '图片上传成功',
                        'data': {'url': web_image_url},
                    })

                except Exception as e:
                    logger.error(e)
                    return JsonResponse({
                        'errno': '4004',
                        'errmsg': '创建房屋图片失败'
                    })
            else:
                try:
                    my_house.index_image_url = web_image_url
                    my_house.save()
                    os.remove(local_image_url)
                    return JsonResponse({
                        'errno': '0',
                        'errmsg': '图片上传成功',
                        'data': {'url': web_image_url},
                    })
                except Exception as e:
                    logger.error(e)
                    return JsonResponse({
                        'errno': '4004',
                        'errmsg': '创建房屋图片失败'
                    })


        except House.DoesNotExist as e:
            print(e)
            return JsonResponse({
                'errno': '4001',
                'errmsg': '数据库查询失败, 未找到该房屋'
            })


# 我的房屋列表
class ShowMyHouses(View):
    @method_decorator(login_required)
    def get(self, request):
        user = request.user
        data = {}
        houses = []

        try:
            my_houses = House.objects.filter(user=user)

            for house in my_houses:
                houses.append({
                    'house_id': house.id,
                    "address": house.address,
                    "area_name": house.area.name,
                    "ctime": house.create_time.ctime(),
                    "img_urls": house.index_image_url,
                    "order_count": house.order_count,
                    "price": house.price,
                    "room_count": house.room_count,
                    "title": house.title,
                    "user_avatar": 'http://qetrkfm0g.bkt.clouddn.com/' + house.user.avatar.url,
                })
            # 构建响应返回
            data["houses"] = houses
            return JsonResponse({
                "data": data,
                "errmsg": 'ok',
                'errno': '0'
            })
        except Exception as e:
            logger.error(e)
            return JsonResponse({
                'errno': '4002',
                'errmsg': "NODATA",
            })


# 首页房屋推荐
class RecommendHouses(View):
    def get(self, request):
        data = []
        # 按照房间订单数量降序排列查询集，只去前5个
        try:
            houses = House.objects.order_by('-order_count')[:4]
        except Exception as e:
            logger.error(e)
            return JsonResponse({
                'errno': '4002',
                'errmsg': 'NODATA'
            })
        for house in houses:
            data.append({
                "house_id": house.id,
                "img_url": house.index_image_url,
                "title": house.title
            })
        return JsonResponse({
            'errno': '0',
            'errmsg': 'ok',
            'data': data,
        })


# 展示房屋祥情
class HouseDetail(View):

    def get(self, request, house_id):
        """
        房屋详情页展示
        1. 通过house_id获取房屋和订单对象
        2. 构建响应数据
        3. 返回响应（判断用户是否登录来返回）
        :param request:
        :param house_id:
        :return:
        """
        # 接收参数
        user = request.user

        try:

            house = House.objects.get(id=house_id)
        except House.DoesNotExist as e:
            print(e)
            return JsonResponse({'errno': '4001', 'errmsg': '数据库查询错误, 未找到该房屋'})
        try:
            orders_obj = Order.objects.filter(id=house_id)
        except Order.DoesNotExist as e:
            print(e)
            return JsonResponse({'errno': '4001', 'errmsg': '数据库查询错误, 未找到该订单'})

        comment_list = []
        # 遍历订单信息获取评论
        for order_obj in orders_obj:
            comment_list.append(
                {
                    'comment': order_obj.comment,
                    'ctime': order_obj.create_time,
                    'user_name': order_obj.user.username
                }
            )
        cur_house_facilities = house.facility.all()
        # 构建设备列表返回值
        facilities = []
        for i in cur_house_facilities:
            facilities.append(i.id)
        # 构建房屋图片列表返回
        index_image_url = House.objects.get(pk=house_id).index_image_url  # 获取首页图片路径
        house_images = []
        try:
            images = HouseImage.objects.filter(house_id=house_id)
        except HouseImage.DoesNotExist:
            house_images.append(index_image_url)
        else:
            house_images = [index_image_url]
            for i in images:
                house_images.append(i.url)

        house_dict = {
            'acreage': house.acreage,
            'address': house.address,
            'beds': house.beds,
            'capacity': house.capacity,
            'comments': comment_list,
            'deposit': house.deposit,
            'facilities': facilities,
            'hid': house.id,
            'img_urls': house_images,
            'max_days': house.max_days,
            'min_days': house.min_days,
            'price': house.price,
            'root_count': house.room_count,
            'title': house.title,
            'unit': house.unit,
            'user_avatar': 'http://qetrkfm0g.bkt.clouddn.com/' + house.user.avatar.url,
            'user_id': house.user.id,
            'user_name': house.user.username

        }
        # 用户已登录
        if user.is_authenticated:
            return JsonResponse({
                'errno': '0',
                'errmsg': 'ok',
                'data': {
                    "house": house_dict,
                    "user_id": user.id,
                },
            })
        # 用户未登录
        else:
            return JsonResponse({
                'errno': '0',
                'errmsg': '用户未登录',
                'data': {
                    "house": house_dict,
                    "user_id": -1,
                }
            })
