from django.http import JsonResponse


def login_required(func):
    # 内层函数
    def inner(request, *args, **kwargs):
        if request.user.is_authenticated:
            return func(request, *args, **kwargs)

        else:
            return JsonResponse({
                'errno': '4101',
                'errmsg': '用户未登录'
            }, status=401)

    return inner
