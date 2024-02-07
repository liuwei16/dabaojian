import re
import random
import uuid
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import serializers, status
from rest_framework.exceptions import ValidationError
from django_redis import get_redis_connection

from apps.api import models

def phone_validator(value):
    if not re.match("^(1[3|4|5|6|7|8|9])\d{9}$",value):
        raise ValidationError('手机格式错误')

class MessageSerializer(serializers.Serializer):
    phone = serializers.CharField(label='手机号', validators=[phone_validator,])

class LoginSerializer(serializers.Serializer):
    phone = serializers.CharField(label='手机号', validators=[phone_validator, ])
    code = serializers.CharField(label='短信验证码')
    nickname = serializers.CharField(label='昵称')
    avatar = serializers.CharField(label='头像')
    def validate_code(self, value):
        if len(value) !=4:
            raise ValidationError('格式错误')
        if not value.isdecimal():
            raise ValidationError('格式错误')
        phone = self.initial_data.get('phone')
        conn = get_redis_connection()
        code = conn.get(phone)
        print('data in redis and user: ', code, value)
        if not code:
            raise ValidationError('验证码过期')
        if str(value) != code.decode('utf-8'):
            print(str(value), code.decode('utf-8'))
            raise ValidationError('验证码错误')
        return value


class MessageView(APIView):
    """发送短信接口"""
    def get(self, request, *args, **kwargs):
        print(request)
        ser = MessageSerializer(data=request.query_params) # get方法中只有query_params而没有data
        if not ser.is_valid():
            return Response(data={'status': False, 'message': '手机格式错误'})
        phone = ser.validated_data.get('phone')
        random_code = random.randint(1000, 9999)
        print(random_code)
        """result = send_message(phone, random_code) # 调用腾讯云的发短信功能"""
        # 存入redis 60s
        conn = get_redis_connection()
        conn.set(phone, random_code, ex=60)
        return Response(data={"status": True, 'message': '发送成功'})
    
class LoginView(APIView):
    def post(self, request, *args, **kwargs):
        ser = LoginSerializer(data=request.data)
        if not ser.is_valid():
            return Response(data={'status': False, 'message': '验证码错误'})
        phone = ser.validated_data.get('phone')
        nickname = ser.validated_data.get('nickname')
        avatar = ser.validated_data.get('avatar')
        # 存入数据库
        user_object, flag = models.UserInfo.objects.get_or_create(
            telephone = phone,
            defaults={"nickname": nickname, 'avatar': avatar}
        ) # 如果有就使用原来的值
        user_object.token = str(uuid.uuid4())
        user_object.save() # model query对象存入数据库
        return Response(data={"status": True, "data": {"token": user_object.token, 'phone': phone}})
