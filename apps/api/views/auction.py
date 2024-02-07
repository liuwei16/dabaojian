
from django.forms import model_to_dict
from django.db.models import Max
from django.db import transaction
from rest_framework.viewsets import GenericViewSet
from rest_framework.mixins import RetrieveModelMixin, ListModelMixin
from rest_framework import exceptions
from rest_framework.generics import ListAPIView, RetrieveAPIView, CreateAPIView
from rest_framework import serializers

from utils.auth import UserAuthentication, GeneralAuthentication
from utils.filters import MinFilterBackend, MaxFilterBackend
from utils.pagination import SplitLimitPagination
from apps.api import models


class AuctionModelSerializer(serializers.ModelSerializer):
    # status = serializers.CharField(source='get_status_display') # 取它的中文而非id
    status = serializers.SerializerMethodField()
    preview_start_time = serializers.DateTimeField(format="%Y-%m-%d")
    goods = serializers.SerializerMethodField() # 因为要取几条商品的图片所以加上这个
    cover = serializers.CharField()
    class Meta:
        model = models.Auction
        fields = ['id', 'title', 'cover', 'status', 'preview_start_time',
                  'look_count', 'goods_count', 'total_price', 'bid_count', 'goods']
    def get_goods(self, obj):
        queryset = models.AuctionItem.objects.filter(auction=obj)[:5]
        return [row.cover.name for row in queryset]
    def get_status(self, obj):
        status_class_mapping = {
            1: 'before',
            2: 'preview',
            3: 'auction',
            4: 'stop'
        }
        return {'text': obj.get_status_display(), 'class': status_class_mapping.get(obj.status)}
    
# 专场列表
class AuctionView(ListAPIView):
    queryset = models.Auction.objects.filter(status__gt=0).order_by('-id')
    serializer_class = AuctionModelSerializer
    filter_backends = [MinFilterBackend, MaxFilterBackend]
    pagination_class = SplitLimitPagination
    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        # 1.根据response.data获取所有的专场id id_list = [1,3,4,5]
        # 2.相关所有的单品  models.AuctionItem.objects.filter(auction_id__in=id_list)
        return response
    
class AuctionDetailItemModelSerializer(serializers.ModelSerializer):
    cover = serializers.CharField()
    status_text = serializers.CharField(source='get_status_display')

    class Meta:
        model = models.AuctionItem
        fields = [
            'id', 'status', 'status_text', 'cover', 'unit', 'title', 'start_price',
            'deal_price', 'reserve_price', 'highest_price'
        ]


class AuctionDetailModelSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    items = serializers.SerializerMethodField()
    deposit = serializers.SerializerMethodField(label='保证金')
    cover = serializers.CharField()

    class Meta:
        model = models.Auction
        fields = ['id', 'status', 'title', 'cover', 'look_count', 'goods_count', 'bid_count', 'items', 'deposit']

    def get_status(self, obj):
        status_class_mapping = {
            1: 'before',
            2: 'preview',
            3: 'auction',
            4: 'stop'
        }
        return {'text': obj.get_status_display(), 'class': status_class_mapping.get(obj.status)}

    def get_items(self, obj):
        # queryset = models.AuctionItem.objects.filter(auction=obj).exclude(status=1)
        queryset = models.AuctionItem.objects.filter(auction=obj)
        ser = AuctionDetailItemModelSerializer(instance=queryset, many=True)
        return ser.data

    def get_deposit(self, obj):
        context = {
            'total': False,
            'single': {}
        }
        user_object = self.context['request'].user
        if not user_object:
            return context
        queryset = models.DepositRecord.objects.filter(user=user_object, auction=obj, status=2)
        if not queryset.exists():
            return context

        if queryset.filter(deposit_type=2).exists():
            context['total'] = True
            return context

        context['single'] = {row.item_id: True for row in queryset}
        return context


# 专场详细
class AuctionDetailView(RetrieveAPIView):
    """专场详细-多个单品"""
    queryset = models.Auction.objects.filter(status__gt=0)
    serializer_class = AuctionDetailModelSerializer

class AuctionItemDetailModelSerializer(serializers.ModelSerializer):
    image_list = serializers.SerializerMethodField()
    carousel_list = serializers.SerializerMethodField() # 获取轮播图
    detail_list = serializers.SerializerMethodField()
    record = serializers.SerializerMethodField()
    
    class Meta:
        model = models.AuctionItem
        fields = "__all__"
    def get_image_list(self, obj):
        querset = models.AuctionItemImage.objects.filter(item=obj).order_by('-order')
        return [row.img for row in querset]
    def get_carousel_list(self, obj):
        querset = models.AuctionItemImage.objects.filter(item=obj, carousel=True).order_by('-order')
        return [row.img for row in querset]
    def get_detail_list(self, obj):
        querset = models.AuctionItemDetail.objects.filter(item=obj)
        return [model_to_dict(row, ['key', 'value']) for row in querset]
    def get_record(self, obj):
        querset = models.BrowseRecord.objects.filter(item=obj)
        result = {
            'record_list': [row.user.avatar for row in querset[:5]],
            'total_count': querset.count()
        }
        return result

# 单品详细
class AuctionItemDetailView(RetrieveAPIView):
    """单品详细"""
    queryset = models.AuctionItem.objects.filter(status__gt=0)
    serializer_class = AuctionItemDetailModelSerializer

class AuctionDepositModelSerializer(serializers.ModelSerializer):
    deposit = serializers.SerializerMethodField()
    balance = serializers.SerializerMethodField()
    cover = serializers.CharField()
    class Meta:
        model = models.AuctionItem
        fields = ['id', 'title', 'cover', 'reserve_price', 'highest_price', 'deposit', 'balance']
    def get_deposit(self, obj):
        # 展示单品保证金和全场保证金
        #   1. 如果已支付过单品保证金，则不能再支付全场保证金。
        #   2. 如果已支付过全场保证经，则无需再支付保证金
        context = {
            'selected': 1,
            'money': obj.deposit,
            'list': [
                {'id': 1, 'money': obj.deposit, 'text': '单品保证金', 'checked': True},
                {'id': 2, 'money': obj.auction.deposit, 'text': '全场保证金'}
            ]
        }
        return context
    def get_balance(self, obj):
        return self.context['request'].user.balance

    
# 保证金-如果要提交保证金则要加上CreateAPIView
class AuctionDepositView(RetrieveAPIView, CreateAPIView):
    # authentication_classes = [UserAuthentication, ] # 如果没有用户登录则失败
    authentication_classes = [GeneralAuthentication, ] # 如果没有用户登录则失败
    queryset = models.AuctionItem.objects.filter(status__in=[1,2,3])
    serializer_class = AuctionDepositModelSerializer

class BidModelSerializer(serializers.ModelSerializer):
    status_text = serializers.CharField(source='get_status_display', read_only=True) # read_only说明请求过来时可以不序列化，而从数据库中读取时需要带出去
    username = serializers.CharField(source='user.nickname', read_only=True)
    class Meta:
        model = models.BidRecord
        fields = ['price', 'item', 'status_text', 'username']
    def validate_item(self, value):
        exists = models.AuctionItem.objects.filter(id=value).exists()
        if not exists:
            raise exceptions.ValidationError('已拍卖完成或未开拍')
        return value
    def validate_price(self, value):
        # value=用户提交的价格
        # 底价/加价幅度/最高价
        item_id = self.initial_data.get('item')
        item_object = models.AuctionItem.objects.filter(id=item_id).first()
        if value <= item_object.start_price:
            raise exceptions.ValidationError('不能低于起拍价')

        div = (value - item_object.start_price) % item_object.unit
        if div:
            raise exceptions.ValidationError('必须按照加价幅度来竞价')

        max_price = models.BidRecord.objects.filter(item_id=item_id).aggregate(max_price=Max('price'))['max_price']
        if not max_price:
            return value

        if max_price >= value:
            raise exceptions.ValidationError('已经有人出这个价了，你再涨涨')
        return value

# 竞价    GET: http://www.xxx.com/deposit/?item_id=1
# 提交竞价 POST: http://www.xxx.com/deposit/
class BidView(ListAPIView, CreateAPIView):
    # authentication_classes = [UserAuthentication, ]
    authentication_classes = [GeneralAuthentication, ]
    queryset = models.BidRecord.objects.all().order_by('-id')
    serializer_class = BidModelSerializer
    def get_queryset(self):
        item_id = self.request.query_params.get('item_id')
        return self.queryset.filter(item_id=item_id)
    
    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        item_id = request.query_params.get('item_id')
        item_object = models.AuctionItem.objects.filter(id=item_id).first()
        max_price = models.BidRecord.objects.filter(item_id=item_id).aggregate(max_price=Max('price'))['max_price']
        result = {
            'unit': item_object.unit,
            'price': max_price or item_object.start_price,
            'bid_list': response.data
        }
        response.data = result
        return response

    def perform_create(self, serializer):
        with transaction.atomic(): # 加了了事务的全局锁，已经有人在加价了就不能再加了
            price = self.request.data.get('price')
            item_id = self.request.data.get('item')
            result = models.BidRecord.objects.filter(item_id=item_id).aggregate(max_price=Max('price')).select_for_update()
            max_price = result['max_price']
            if price > max_price:
                serializer.save(user=self.request.user)
            raise exceptions.ValidationError('已经被出价了，再涨涨.')


class Auction2View(ListModelMixin, RetrieveModelMixin, GenericViewSet):
    queryset = models.Auction.objects.filter(status__gt=0).order_by('-id')
    serializer_class = AuctionModelSerializer
    filter_backends = [MinFilterBackend, MaxFilterBackend, ]
    pagination_class = SplitLimitPagination

    def get_serializer_class(self):
        pk = self.kwargs.get('pk')
        if pk:
            return AuctionDetailModelSerializer
        return AuctionModelSerializer