from django.contrib.auth.backends import ModelBackend

from user.models import User


class LoginWithMulitaccount(ModelBackend):
    """
    重写 backend 下的 authenticate 认证方法方法
        def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(UserModel.USERNAME_FIELD)
        try:
            user = UserModel._default_manager.get_by_natural_key(username)
        except UserModel.DoesNotExist:
            # Run the default password hasher once to reduce the timing
            # difference between an existing and a nonexistent user (#20760).
            UserModel().set_password(password)
        else:
            if user.check_password(password) and self.user_can_authenticate(user):
                return user
    更改他的验证方式,使得认证时可以多方式认证

    重写 Django 内的方法后， 需要在配置文件中声明 程序 调用时 使用自己重写后的方法
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist as e:
            try:
                user = User.objects.get(mobile=username)
            except User.DoesNotExist as e:
                return None
        if user.check_password(password):
            return user
