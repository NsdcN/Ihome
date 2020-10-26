import re
import random
import json

from rq import Queue
from redis import Redis

from django.views import View
from iHome.libs.captcha.captcha import captcha
from django_redis import get_redis_connection
from rq_tasks.sms_task import ccp_send_sms_code
from django.http import HttpResponse, JsonResponse
import logging

logger = logging.getLogger('django')


# 图形验证码接口
class ImageCodeView(View):

    def get(self, request):
        """
        获取请求 生成图片验证码
        保存到 缓存数据库中
        :param request:
        :return:
        """
        cur = request.GET.get('cur')
        text, image = captcha.generate_captcha()
        print("图片验证码 :", text)
        conn = get_redis_connection('image_code')

        try:
            conn.setex('img_%s' % cur, 300, text)
        except Exception as e:
            logger.error(e)

        return HttpResponse(image)


# 短信验证码接口
class SMSCodeView(View):

    def post(self, request):
        """
        校验图形验证码 并生成短信验证码
        rq 异步实现短信发送
        :param request:
        :return:
        """
        date = json.loads(request.body.decode())
        sms_mobile = date.get('mobile')
        img_id = date.get('id')
        img_text = date.get('text')

        # 校验参数
        if not all([sms_mobile, img_id, img_text]):
            return JsonResponse({
                "errno": "4103",
                "errmsg": "参数错误, 必要参数缺失"
            })
        if not re.match(r'^\w{4}$', img_text):
            return JsonResponse({
                'errno': '4103',
                'errmsg': '参数错误,短信验证码格式错误'
            })
        if not re.match(r'^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$', img_id):
            return JsonResponse({
                'errno': '4103',
                'errmsg': '参数错误'
            })

        # 校验图片验证码
        conn = get_redis_connection('image_code')
        image_code_redis = conn.get('img_%s' % img_id)
        if not image_code_redis:
            return ({
                'errno': '4002',
                'errmsg': '无数据'
            })
        # 解码二进制的 缓存数据
        image_code_redis = image_code_redis.decode()
        # 读取一次后,即可直接删除缓存库内的图形验证码,防止二次验证
        conn.delete('img_%s' % img_id)

        # 忽略大小写对比图片验证码
        if img_text.lower() != image_code_redis.lower():
            return JsonResponse({
                'errno': '4103',
                'errmsg': '参数错误'
            })

        # 防止60秒内频发发短信
        conn = get_redis_connection('sms_code')
        flag = conn.get('flag_%s' % sms_mobile)
        if flag:
            return JsonResponse({'errno': '4201', 'errmsg': '非法请求或请求次数受限'})

        # 生成6位数短信验证码
        sms_code = "%06d" % random.randint(0, 999999)
        print("手机验证码： ", sms_code)

        # 存入redis库
        p = conn.pipeline()
        p.setex("sms_%s" % sms_mobile, 300, sms_code)
        p.setex("flag_%s" % sms_mobile, 60, '1')
        p.execute()

        # 异步函数调用！ 采用 rq 简化 celery 的异步过程,轻化代码
        # ccp_send_sms_code.delay(sms_mobile, sms_code)
        q = Queue(connection=Redis())
        q.enqueue(ccp_send_sms_code, sms_mobile, sms_code)

        return JsonResponse({
            'errno': '0',
            'errmsg': 'ok'
        })
