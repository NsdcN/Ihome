# Create your views here.
import os

from django.views import View
from django.http import JsonResponse
import json
from django.contrib.auth import authenticate, login, logout
import re
from django.utils.decorators import method_decorator

from iHome.settings.dev import BASE_DIR
from iHome.utils.login_decorator import login_required
from django_redis import get_redis_connection
from user.models import User
from iHome.libs.qiniuyun.demo import Qiniuyun


# 用户注册
class RegisterView(View):

    def post(self, request):

        # 接收参数
        dict = json.loads(request.body.decode())
        mobile = dict.get('mobile')
        phonecode = dict.get('phonecode')
        password = dict.get('password')

        # 校验参数
        if not all([mobile, phonecode, password]):
            return JsonResponse({"errno": "4002", "errmsg": "无数据，"})

        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return JsonResponse({"errno": "4103", "errmsg": '参数错误'})

        if not re.match(r'^[a-zA-Z0-9]{8,20}$', password):
            return JsonResponse({'errno': '4106', 'errmsg': '密码错误'})

        # 判断手机号是否重复注册, 查询mobile在mysql中的个数
        count = User.objects.filter(mobile=mobile).count()
        if count:
            return JsonResponse({'errno': '4003',
                                 'errmsg': '数据已存在'})
        # 链接缓存库, 获取短信验证码
        conn = get_redis_connection('sms_code')
        sms_code_from_redis = conn.get("sms_%s" % mobile)
        # 校验短信验证码
        if not sms_code_from_redis:
            return JsonResponse({'errno': '4002', 'errmsg': '无数据，手机验证码过期'})
        if sms_code_from_redis.decode() != phonecode:
            return JsonResponse({'errno': '4103', 'errmsg': '参数错误，手机验证码有误'})
        # 验证完成, 保存到数据库
        try:
            user = User.objects.create_user(username=mobile, password=password, mobile=mobile,)
            # 设定默认头像
            user.avatar = 'avatar20200811104854'
            user.save()
        except Exception as e:
            return JsonResponse({'errno': '4302', 'errmsg': '文件读写错误，保存到数据库出错'})

        # 实现状态保持
        login(request, user)

        # 返回响应
        return JsonResponse({'errno': 0, 'errmsg': '注册成功'})


# 用户登录
class LoginView(View):

    # 登陆接口
    def post(self, request):
        # 接收参数
        data = json.loads(request.body.decode())
        username = data.get('mobile')
        password = data.get('password')

        # 校验数据
        if not all([username, password]):
            return JsonResponse({'errno': '4002', 'errmsg': '缺少必要参数！'})

        user = authenticate(request, username=username, password=password)

        if user is None:
            return JsonResponse({'errno': '4004', 'errmsg': '账号或密码错误'})

        # 状态保持
        login(request, user)

        response = JsonResponse({'errno': '0', 'errmsg': '登陆成功'})

        response.set_cookie(
            'username',
            username,
            max_age=3600 * 24 * 14
        )

        return response

    # 判断是否登陆
    def get(self, request):
        # 已登录：
        user = request.user
        if user.is_authenticated:
            response = JsonResponse({
                "errno": "0",
                "errmsg": "已登录",
                "data": {
                    "name": user.username,
                    "user_id": user.id
                }
            })
        # 未登录：
        else:
            response = JsonResponse({
                "errno": "4101",
                "errmsg": "未登录"
            })

        return response

    def delete(self, request):
        logout(request)

        # 3、构建响应
        response = JsonResponse({'errno': '0', 'errmsg': 'ok'})
        response.delete_cookie('username')

        return response


# 用户个人中心接口
class UserInfoView(View):
    # 添加装饰器
    @method_decorator(login_required)
    def get(self, request):
        # 接收参数
        user = request.user
        if not user.avatar.url:
            user_avatar = 'http://qetrkfm0g.bkt.clouddn.com/' + 'avatar20200811104854'
        else:
            user_avatar = 'http://qetrkfm0g.bkt.clouddn.com/' + user.avatar.url
        user_info = {
            "name": user.username,
            "mobile": user.mobile,
            'user_id': user.id,
            'create_time': user.date_joined,
            "avatar_url": user_avatar,
        }

        # 构建响应返回
        return JsonResponse({
            'errno': '0',
            'errmsg': "ok",
            "data": user_info
        })


# 用户名修改接口
class ChangeUsername(View):
    # 添加装饰器
    @method_decorator(login_required)
    def put(self, request):
        # 接收参数
        user_dict = json.loads(request.body.decode())
        name = user_dict.get('name')

        # 匹配用户名正则，除了错误，先注释
        # if not re.match(r"^[a-zA-Z]\w{7,19}$",name):
        #     return JsonResponse({
        #         'errno':'4103',
        #         'errmsg':'参数错误'
        #     })

        # 异常捕获
        try:
            # 根据用户名获取用户对象
            user = User.objects.get(username=name)
            # 判断用户是否已经存在
            if user:
                # 如果存在则表示该用户名已经被注册
                return JsonResponse({
                    'errno': '4003',
                    'errmsg': '数据已存在'
                })

        except User.DoesNotExist:
            # 如果不存在则将新用户名写入数据库中，并进行异常捕获
            try:
                request.user.username = name
                request.user.save()
            except Exception as e:
                return JsonResponse({
                    'errno': '4302',
                    'errmsg': '文件读写错误'
                })

            # 修改完成，构建响应返回
            return JsonResponse({
                'errno': '0',
                'errmsg': '修改成功'
            })


# 用户身份认证
class UserIdentivify(View):
    @method_decorator(login_required)
    def post(self, request):
        # 接收用户参数
        user_data = json.loads(request.body.decode())

        real_name = user_data.get('real_name')
        id_card = user_data.get('id_card')

        # 对身份证信息进行正则匹配
        if not re.match(
                r"^[1-9]\d{7}((0\d)|(1[0-2]))(([0|1|2]\d)|3[0-1])\d{3}$|^[1-9]\d{5}[1-9]\d{3}((0\d)|(1[0-2]))(([0|1|2]\d)|3[0-1])\d{3}([0-9]|X)$",
                id_card):
            return JsonResponse({
                'errno': '4105',
                'errmsg': '用户身份错误'
            })
        # 将real_name和id_card写入数据库，进行异常捕获
        try:
            request.user.id_card = id_card
            request.user.real_name = real_name
            request.user.save()
        except Exception as e:
            return JsonResponse({
                'errno': '4302',
                'errmsg': '文件读写错误'
            })

        # 构建响应返回
        return JsonResponse({
            'errno': '0',
            'errmsg': '认证信息保存成功'
        })

    # 获取用户认证信息接口
    def get(self, request):
        # 获取参数
        user = request.user
        id_card = user.id_card
        real_name = user.real_name
        # 校验参数
        if not all([id_card, real_name]):
            # 参数有误则返回错误信息
            return JsonResponse({
                'errno': '4105',
                'errmsg': '用户身份错误'
            })
        # 返回校验成功响应
        return JsonResponse({
            'errno': 0,
            'errmsg': '认证成功',
            "data": {
                'id_card': id_card,
                "real_name": real_name
            }
        })


# 上传用户头像
class AvatarView(View):

    @method_decorator(login_required)
    def post(self, request):
        # 创建图片对象
        image = request.FILES.get('avatar')
        # 获取图片二维码
        cp_image = image.file.read()
        # 头像路径拼接
        image_url = BASE_DIR + '/apps/user/useravatarimages/' + image.name
        # 拷贝用户上传的头像到指定路径
        with open(image_url, 'wb') as f:
            f.write(cp_image)
        # 创建七牛云对象
        q = Qiniuyun()
        # 上传用户头像
        key = q.uploadimage(image_url)
        # 返回头像网页地址
        get_url = q.get_img_url(key)
        # print(get_url)
        # 删除临时保存的头像文件
        try:
            request.user.avatar = key
            request.user.save()
        except:
            return JsonResponse({'errno': '4302', 'errmsg': '上传头像失败'})
        os.remove(image_url)
        # 构建响应
        return JsonResponse({"data": {"avatar_url": get_url},
                             "errno": "0",
                             "errmsg": "头像上传成功"})
