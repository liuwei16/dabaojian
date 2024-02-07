from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from apps.api import models

class GeneralAuthentication(BaseAuthentication):
    """
    通用认证，如果认证功能则返回数据，认证失败自己不处理，交给下一个认证组件处理。
    """

    def authenticate(self, request):
        token = request.META.get('HTTP_AUTHORIZATION', None)
        print(token)
        # 1.如果用户没有提供token,返回None（我不处理，交给下一个认证类处理，则默认是None）
        if not token:
            return None
        # 2.token错误，,返回None（我不处理，交给下一个认证类处理，则默认是None）
        user_object = models.UserInfo.objects.filter(token=token).first()
        print(user_object)
        
        if not user_object:
            return None
        # 3.认证成功
        return (user_object, token) # request.user/request.auth
    
class UserAuthentication(BaseAuthentication):
    """
    用户认证，如果认证功能则返回数据，认证失败则抛出一个异常
    """
    def authenticate(self, request):
        token = request.META.get('HTTP_AUTHORIZATION', None)
        if not token:
            raise AuthenticationFailed()
        user_object = models.UserInfo.objects.filter(token=token).first()
        if not user_object:
            raise AuthenticationFailed()
        # 3.认证成功
        return (user_object, token) # request.user/request.auth