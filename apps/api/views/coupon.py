
from django.db import transaction
from rest_framework import exceptions, serializers, status
from rest_framework.generics import ListAPIView, CreateAPIView
from collections import OrderedDict
from utils.auth import UserAuthentication, GeneralAuthentication
from apps.api import models

class CouponModelSerializer(serializers.ModelSerializer):
    apply_start_date = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S')
    apply_stop_date = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S')
    status_text = serializers.CharField(source='get_status_display')
    cover = serializers.CharField(source='auction.cover')
    remain = serializers.SerializerMethodField()
    class Meta:
        model = models.Coupon
        exclude = ['apply_start_task_id', 'apply_stop_task_id', 'deleted', 'count']
    
    def get_remain(self, obj):
        return obj.count - obj.apply_count
    
class CouponView(ListAPIView):
    queryset = models.Coupon.objects.filter(deleted=False).exclude(status=1).order_by('-id')
    serializer_class = CouponModelSerializer

# 用户领用优惠券
class UserCouponModelSerializer(serializers.ModelSerializer):
    remain = serializers.SerializerMethodField()
    class Meta:
        model = models.UserCoupon
        fields = ['remain', 'coupon']
    def get_remain(self, obj):
        return obj.coupon.count-obj.coupon.apply_count
    
    def validate_coupon(self, value): # 对post提交的数据进行验证
        user_object = self.context['request'].user
        if not value or value.deleted:
            raise exceptions.ValidationError('优惠券不存在')
        if value.status != 2:
            raise exceptions.ValidationError('优惠券不可领取')
        # 优惠券个数是否合法
        if (value.apply_count + 1) > value.count:
            raise exceptions.ValidationError('优惠券已领完')
        # 是否已领取优惠券
        exists = models.UserCoupon.objects.filter(user=user_object, coupon=value).exists()
        if exists:
            raise exceptions.ValidationError('已领取此优惠券')
        return value

class MyUserCouponModelSerializer(serializers.ModelSerializer):
    status_text = serializers.CharField(source='get_status_display')
    coupon = serializers.CharField(source='coupon.title')
    cover = serializers.CharField(source='coupon.auction.cover')
    money = serializers.CharField(source='coupon.money')

    class Meta:
        model = models.UserCoupon
        fields = "__all__"

class UserCouponView(ListAPIView, CreateAPIView):
    # authentication_classes = [UserAuthentication, ]
    authentication_classes = [GeneralAuthentication, ]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return UserCouponModelSerializer
        return MyUserCouponModelSerializer

    def perform_create(self, serializer):
        # post请求过来 事务+锁
        with transaction.atomic():
            coupon_object = models.Coupon.objects.filter(id=serializer.validated_data['coupon'].id).select_for_update().first()
            if (coupon_object.apply_count + 1) > coupon_object.count:
                raise exceptions.ValidationError('优惠券已领完')
            serializer.save(user=self.request.user)
            coupon_object.apply_count += 1
            coupon_object.save() # 这是存到数据库中
    
    def get_queryset(self):
        # 只能取当前用户的优惠券 所以要用这个函数
        return models.UserCoupon.objects.filter(user=self.request.user)

    def list(self, *args, **kwargs):
        response = super().list(*args, **kwargs)
        if response.status_code != status.HTTP_200_OK:
            return response
        """
        {
            1:{text:'未使用',child:[..]}
            2:{text:'已使用',child:[...]}
            3:{text:'已过期',child:[...]}
        }
        """
        status_dict = OrderedDict()
        for item in models.UserCoupon.status_choices:
            status_dict[item[0]] = {'text': item[1], 'child': []}
        for row in response.data: # 已经序列化成json data了
            status_dict[row['status']]['child'].append(row)
        response.data = status_dict
        return response
    
class ChooseCouponModelSerializer(serializers.ModelSerializer):
    title = serializers.CharField(source='coupon.title')
    cover = serializers.CharField(source='coupon.auction.cover')
    money = serializers.CharField(source='coupon.money')

    class Meta:
        model = models.UserCoupon
        fields = ['id', 'title', 'money', 'cover']
        
class ChooseCouponView(ListAPIView):
    """ 支付页面 选择优惠券 """
    authentication_classes = [UserAuthentication, ]
    serializer_class = ChooseCouponModelSerializer

    def get_queryset(self):
        auction = self.request.query_params.get('auction')
        # return models.UserCoupon.objects.filter(user=self.request.user, coupon__auction_id=auction, status=1)
        return models.UserCoupon.objects.all()