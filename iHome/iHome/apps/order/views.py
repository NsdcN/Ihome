from django.shortcuts import render

# Create your views here.
from django.utils.decorators import method_decorator
from django.views import View
import json
from django.http import JsonResponse
from house.models import House
from iHome.utils.login_decorator import login_required
from order.models import Order
from order.utils import calday, judgedate


class OrderView(View):
    # 订单预定
    @method_decorator(login_required)
    def post(self, request):
        """
        完成 房屋 预定功能
        1. 提取请求 中 携带的 参数, 首先判断是否拥有 house_id !
        2. 验证是否是 自己 之前发布的 房屋 <要求此房屋的 House.user != request.user >
        3. 提取 开始时间 和 结束时间
        4. 验证开始和结束时间  <start_data 要在该 House 未其他租客使用状态下,
                            end_data 也是 未被其他租客使用状态下,
                            且 租用天数要大于 该房屋的 House.min_day, 小于 House.max_day>
        5. 将 预定 信息写入到 redis 数据库中
        6. 构建响应
        :param request:
        :return:
        """
        data = json.loads(request.body.decode())
        house_id = data.get('house_id')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        user = request.user

        # 判断该 房屋是否存在,验证 house_id
        try:
            house_wanted = House.objects.get(id=house_id)
        except House.DoesNotExist as e:
            print(e)
            return JsonResponse({
                'errno': '4001',
                'errmsg': '数据库查询错误'
            })
        # 验证 该房屋是否归属于 当前用户
        if house_wanted.user_id == user.id:
            return JsonResponse({
                'errno': '4105',
                'errmsg': '用户身份错误, 用户自己拥有的房源'
            })
        # 验证数据完成性
        if not all([start_date, end_date]):
            return JsonResponse({
                'errno': '4103',
                'errmsg': '参数错误, 关键参数不全'
            })
        # 验证租房时间的正确性
        # 1. 租期必须大于 1天
        period = calday(start_date, end_date)
        if not period > 0:
            return JsonResponse({
                'errno': '4004',
                'errmsg': '数据错误, 合约时间错误'
            })
        # 2. 租期内 不允许出现其他 用户使用 该房屋的情况
        This_house_exist_orders = Order.objects.filter(house_id=house_id)
        for exist_order in This_house_exist_orders:
            result = judgedate(exist_order, start_date, end_date)
            if not result:
                return JsonResponse({
                    'errno': '4004',
                    'errmsg': '数据错误, 合约期内已存在订单'
                })

        # 验证结束, 可以生成订单, 将 当前数据 写入到 订单表中
        try:
            order = Order.objects.create(user=user,
                                         house_id=house_id,
                                         begin_date=start_date,
                                         end_date=end_date,
                                         days=period,
                                         house_price=house_wanted.price,
                                         amount=house_wanted.price * period,
                                         status=Order.ORDER_STATUS['WAIT_ACCEPT'],
                                         comment=Order.ORDER_STATUS['WAIT_COMMENT'], )
        except Exception as e:
            print(e)
            return JsonResponse({
                'errno': '4302',
                'errmsg': '订单数据写入数据库失败'
            })
        # 订单创建成功, 构建响应
        return JsonResponse({
            'data': {
                'order_id': order.id
            },
            'errno': '0',
            'errmsg': '下单成功'
        })

    # 订单列表  用户是 我的订单  房东是 客户订单
    @method_decorator(login_required)
    def get(self, request):
        """
        获取订单列表
        构建响应
        :param request:
        :return:
        """
        role = request.GET.get('role')
        if not role:
            return JsonResponse({'errno': '4004', 'errmsg': '参数错误, 未传递 role 值'})
        user = request.user
        # 判断当前是 顾客 使用接口 还是 房东使用接口
        if role == 'custom':
            try:
                my_orders = Order.objects.filter(user=user)
            except Order.DoesNotExist as e:
                return JsonResponse({
                    'errno': '4002',
                    'errmsg': '无数据'
                })
            orders = []
            for order in my_orders:
                orders.append({
                    'amount': order.amount,
                    'comment': order.comment,
                    'ctime': order.create_time.ctime(),
                    'days': order.days,
                    'end_date': order.end_date,
                    'img_url': House.objects.get(id=order.house_id).index_image_url,
                    'order_id': order.id,
                    'start_date': order.begin_date,
                    'status': Order.ORDER_STATUS_ENUM[order.status],
                    'title': House.objects.get(id=order.house_id).title,
                })
            return JsonResponse({
                'data': {
                    'orders': orders
                },
                'errno': '0',
                'errmsg': 'ok',
            })
        # 返回 商家 看到的客户订单
        else:
            try:
                # orders = Order.objects.filter(house__user=user)
                my_houses = House.objects.filter(user=user)
                house_ids = []
                for house in my_houses:
                    house_ids.append(house.id)
                custom_orders = []
                for i in house_ids:
                    exist_orders = Order.objects.filter(house_id=i)
                    for order in exist_orders:
                        custom_orders.append({
                            'amount': order.amount,
                            'comment': order.comment,
                            'ctime': order.create_time.ctime(),
                            'days': order.days,
                            'end_date': order.end_date,
                            'img_url': House.objects.get(id=i).index_image_url,
                            'order_id': order.id,
                            'start_date': order.begin_date,
                            'status': Order.ORDER_STATUS_ENUM[order.status],
                            'title': House.objects.get(id=i).title,
                        })
            except Order.DoesNotExist as e:
                return JsonResponse({
                    'errno': '4002',
                    'errmsg': '无数据'
                })

            return JsonResponse({
                'data': {
                    'orders': custom_orders
                },
                'errno': '0',
                'errmsg': 'ok',
            })

    # 接单和拒单  针对房东
    @method_decorator(login_required)
    def put(self, request, order_id):
        """
        完成房东的 接单 和 拒单
        并 提供相应的 拒单回复
        1. 获取 请求参数 action 以及 拒单的 reason
        2. 若是 接单, 完成 订单中 该房屋订单 status 修改
        3. 若是 拒单, 返回 reason 修改 Order.comment 数据
        4. 构建响应
        :param request:
        :return:
        """
        data = json.loads(request.body.decode())
        action = data.get('action')
        user = request.user
        try:
            cur_order = Order.objects.get(id=order_id)
        except Order.DoesNotExist as e:
            print(e)
            return JsonResponse({'errno': '4002', 'errmsg': '无数据,订单找不到'})
        # action 是个布尔值, 直接判断房东是否接单
        # 拒单情况
        if action == 'reject':
            reason = data.get('reason')
            cur_order.comment = reason
            cur_order.status = Order.ORDER_STATUS['REJECTED']
            cur_order.save()
            return JsonResponse({'errno': '0', 'errmsg': '操作成功'})
        # 接单情况
        # 若需要支付,这里是修改 状态为 待支付
        cur_order.status = Order.ORDER_STATUS['WAIT_PAYMENT']
        # 现在不需要支付,这里是修改 状态为 待评价
        cur_order.status = Order.ORDER_STATUS['WAIT_COMMENT']
        cur_order.save()
        return JsonResponse({'errno': '0', 'errmsg': '操作成功'})


class OrderComment(View):
    # 订单评价
    def put(self, request, order_id):
        """
        完成订单评价
        这里直接 忽略了 用户支付的 接口, 跳转到 订单完成并评价
        1. 通过 order_id 获取到订单
        2. 修改 订单中 的 comment 和 status
        3. 构建响应
        :param request:
        :return:
        """
        comment = json.loads(request.body.decode()).get('comment')
        if not comment:
            return JsonResponse({'errno': '4004', 'errmsg': '数据错误, 未获取到 comment'})
        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist as e:
            print(e)
            return JsonResponse({'errno': '4002', 'errmsg': '无数据, 找不到订单'})
        try:
            # 完成订单数据库中 评价 更新
            order.comment = comment
            order.status = Order.ORDER_STATUS['COMPLETE']
            order.save()
            # 完成房屋数据库中 订单次数的 更新
            house = House.objects.get(id=order.house_id)
            house.order_count += 1
            house.save()
        except Exception as e:
            print(e)
            return JsonResponse({'errno': '4302', 'errmsg': '文件读取错误'})
        return JsonResponse({'errno': '0', 'errmsg': '评论成功'})
