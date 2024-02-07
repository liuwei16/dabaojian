import collections
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import CreateAPIView, ListAPIView, RetrieveAPIView
from django.forms import model_to_dict
from django.db.models import F
from django.db.models import Max
from apps.api import models
from utils.auth import GeneralAuthentication, UserAuthentication
from utils.filters import MinFilterBackend, MaxFilterBackend
from utils.pagination import SplitLimitPagination
# ############################# 动态列表 #############################

class NewsImageModelSerializer(serializers.Serializer):
    key = serializers.CharField()
    cos_path = serializers.CharField()

class CreateNewsModelSerializer(serializers.ModelSerializer):
    imageList = NewsImageModelSerializer(many=True)
    class Meta:
        model= models.News
        exclude = ['user', 'viewer_count', 'comment_count']
    def create(self, validated_data):
        image_list = validated_data.pop('imageList')
        news_object = models.News.objects.create(**validated_data)
        data_list = models.NewsDetail.objects.bulk_create(
            [models.NewsDetail(**info, news=news_object) for info in image_list]
        )
        news_object.imageList = data_list
        if news_object.topic:
            models.Topic.objects.filter(id=news_object.topic_id).update(count=F('count') + 1)
        return news_object

class NewsModelSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    topic = serializers.SerializerMethodField() # 需要重新定义序列化方法get_
    class Meta:
        model = models.News
        fields = ['id', 'cover', 'content', 'topic', "user", 'favor_count']
    def get_user(self, obj):
        return model_to_dict(obj.user, fields=['id', 'nickname', 'avatar'])
    def get_topic(self, obj):
        if not obj.topic:
            return
        return model_to_dict(obj.topic, fields=['id', 'title'])
"""
# 原始写法-取多条数据，实际上是一个ListView
class NewsView(APIView):
    def get(self, request, *args, **kwargs):
        min_id = request.query_params.get('min_id')
        max_id = request.query_params.get('max_id')
        if min_id:
            queryset = models.News.objects.filter(id__lt=min_id).order_by('-id')[:10]
        elif max_id:
            queryset = models.News.objects.filter(id__gt=max_id).order_by('id')[:10]
        else:
            queryset = models.News.objects.all().order_by('-id')[:10]
        ser = NewsModelSerializer(instance=queryset, many=True)
        return Response(data=ser.data, status=200)
"""

"""
# 动态列表的写法
1. 首先定义两个filter
2. 根据数量定义翻页
"""
class NewsView(ListAPIView, CreateAPIView):
    serializer_class = NewsModelSerializer
    # queryset = models.News.objects.all().order_by('-id')
    queryset = models.News.objects.prefetch_related('user', 'topic').order_by('-id')
    pagination_class = SplitLimitPagination
    filter_backends = [MinFilterBackend, MaxFilterBackend]

    def get_authenticators(self):
        if self.request.method == 'POST':
            # return [UserAuthentication(), ]
            return [GeneralAuthentication(), ]
        return []

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CreateNewsModelSerializer
        if self.request.method == 'GET':
            return NewsModelSerializer
    
    def perform_create(self, serializer):
        print(self.request.user)
        new_object = serializer.save(user_id=self.request.user.id)
        return new_object

# ############################# 动态详细 #############################
class NewsDetailModelSerializer(serializers.ModelSerializer):
    # 这里还需要额外增加一些信息
    images = serializers.SerializerMethodField()
    create_date = serializers.DateTimeField(format="%Y-%m-%d %H:%M")
    user = serializers.SerializerMethodField()
    topic = serializers.SerializerMethodField()
    viewer = serializers.SerializerMethodField()
    comment = serializers.SerializerMethodField()
    
    class Meta:
        model = models.News
        exclude = ['cover']
    def get_images(self, obj): # 进来的是news单个实例
        # 怎么拿到images，需要到Detail表中取
        deatail_queryset = models.NewsDetail.objects.filter(news=obj) # 传进来的是news
        return [model_to_dict(row, ['id', 'cos_path']) for row in deatail_queryset]
    def get_user(self, obj):
        return model_to_dict(obj.user, fields=['id', 'nickname', 'avatar'])
    def get_topic(self, obj):
        if not obj.topic:
            return
        return model_to_dict(obj.topic, fields=['id', 'title'])
    def get_viewer(self, obj):
        # 怎么拿到viewer，需要到Record表中取
        queryset = models.ViewerRecord.objects.filter(news_id=obj.id) # news里面的id这么表达
        viewer_list = queryset.order_by('-id')[:10]
        context = {
            'count': queryset.count(),
            'result': [model_to_dict(row.user, ['nickname', 'avatar']) for row in viewer_list]
        }
        return context
    def get_comment(self, obj):
        """获取所有一级评论 及其一个二级评论"""
        # 1 获取一级评论
        first_queryset = models.CommentRecord.objects.filter(news=obj, depth=1).order_by('id')[:10].values(
            'id',
            'content',
            'depth',
            'user__nickname',
            'user__avatar',
            'create_date'
        ) # __双引号表示根据外键id关联到user模型的nickname字段
        first_id_list = [item['id'] for item in first_queryset]
        # 2 获取一级评论下的第一个二级评论
        result = models.CommentRecord.objects.filter(news=obj, depth=2, reply_id__in=first_id_list).values('reply_id').annotate(max_id=Max('id'))
        second_id_list = [item['max_id'] for item in result]
        second_queryset = models.CommentRecord.objects.filter(id__in=second_id_list).values(
            'id',
            'content',
            'depth',
            'user__nickname',
            'user__avatar',
            'create_date',
            'reply_id',
            'reply__user__nickname'
        )
        first_dict = collections.OrderedDict()
        for item in first_queryset:
            item['create_date'] = item['create_date'].strftime('%Y-%m-%d')
            first_dict[item['id']] = item
        for node in second_queryset:
            first_dict[node['reply_id']]['child'] = [node,]
        return first_dict.values()

class NewsDetailView(RetrieveAPIView): # 会根据pk查询发挥一条实例
    # queryset = models.News.objects
    queryset = models.News.objects.all().order_by('-id')
    serializer_class = NewsDetailModelSerializer # 序列化决定了返回什么数据
    # authentication_classes = [GeneralAuthentication, ] # 全局setting中配置了，所以不需要了

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        
        # 判断当前用户是否已经登陆，在viewrecord中加一条;有以下两种写法
        """
        token = request.META.get('HTTP_AUTHORIZATION', None)
        print(token)
        if not token:
            return response
        user_object = models.UserInfo.objects.filter(token=token).first()
        """
        """
        全局中定义了GeneralAuthentication
        """
        user_object = request.user # token = request.auth
        print(user_object)
        if not user_object:
            return response
        # 判断当前用户是否访问过当前动态
        news_object = self.get_object() # models.News.objects.get(pk=pk)
        exists = models.ViewerRecord.objects.filter(user=user_object, news=news_object).exists()
        print(exists)
        if exists:
            return response
        models.ViewerRecord.objects.create(user=user_object, news=news_object)
        models.News.objects.filter(id=news_object.id).update(viewer_count=F('viewer_count')+1)
        return response

# ############################# 话题  #############################
class TopicModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Topic
        fields = '__all__'

class TopicView(ListAPIView):
    queryset = models.Topic.objects.all().order_by('-id')
    serializer_class = TopicModelSerializer
    pagination_class = SplitLimitPagination # 获取前10条
    filter_backends = [MinFilterBackend, MaxFilterBackend]

# ############################# 获取所有子评论  #############################
class CommentModelSerializer(serializers.ModelSerializer):
    create_date = serializers.DateTimeField(format='%Y-%m-%d')
    user__nickname = serializers.CharField(source='user.nickname') # 直接获取
    user__avatar = serializers.CharField(source='user.avatar')
    reply_id = serializers.CharField(source='user.avatar')
    reply__user__nickname = serializers.CharField(source='reply.user.nickname')
    class Meta:
        model = models.CommentRecord
        exclude = ['news', 'user', 'reply', 'root']

class CreateCommentModelSerializer(serializers.ModelSerializer):
    create_date = serializers.DateTimeField(format='%Y-%m-%d',read_only=True) # 序列化是会读取，反序列化时不会写入，因为这些属性本身就存在
    user__nickname = serializers.CharField(source='user.nickname',read_only=True)
    user__avatar = serializers.CharField(source='user.avatar',read_only=True)
    reply_id = serializers.CharField(source='reply.id',read_only=True)
    reply__user__nickname = serializers.CharField(source='reply.user.nickname',read_only=True)

    class Meta:
        model = models.CommentRecord
        exclude = ['user','favor_count']

class CommentView(APIView):

    def get_authenticators(self, request):
        if request.method == 'POST':
            return [UserAuthentication(), ]
        return [GeneralAuthentication(), ]
    
    def get(self, request, *args, **kwargs):
        root_id = request.query_params.get('root')
        # 获取所有子评论
        node_queryset = models.CommentRecord.objects.filter(root_id=root_id).order_by('id')
        ser = CommentModelSerializer(instance=node_queryset, many=True)
        return Response(data=ser.data, status=status.HTTP_200_OK)
    
    def post(self, request, *args, **kwargs):
        # 1 进行数据校验
        ser = CreateCommentModelSerializer(data=request.data) # data用于反序列化时的数据传入，instance用于模型类参数传入用于序列化
        if ser.is_valid():
            ser.save(user_id=1) # 保存到数据库，为啥user_id要设置为1，需要debug一下
            news_id = ser.data.get('news') # 序列化完成后得到的外键news是id
            models.News.objects.filter(id=news_id).update(comment_count=F('comment_count')+1)
            return Response(data=ser.data, status=status.HTTP_201_CREATED)
        return Response(data=ser.errors, status=status.HTTP_400_BAD_REQUEST)

# ############################ 新闻点赞 ##########################

class FavorModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.NewsFavorRecord
        fields = ['news']

class FavorView(APIView):
    authentication_classes = [UserAuthentication,]
    def post(self, request, *args, **kwargs):
        ser = FavorModelSerializer(data=request.data) # 传进来的是个news id
        if not ser.is_valid():
            return Response(data={}, status=status.HTTP_400_BAD_REQUEST)
        news_object = ser.validated_data.get('news')
        queryset = models.NewsFavorRecord.objects.filter(user=request.user, news=news_object)
        exists = queryset.exists()
        # 如果存在，则取消点赞，如果不存在，则增加点赞记录
        if exists:
            queryset.delete()
            return Response(data={}, status=status.HTTP_200_OK)
        models.NewsFavorRecord.objects.create(user=request.user, news=news_object)
        return Response(data={}, status=status.HTTP_201_CREATED)
        
class TestSER(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()
    class Meta:
        model = models.Topic
        fields = "__all__"

    def get_title(self,obj):
        request = self.context['request']

class TestView(ListAPIView):
    queryset = models.Topic.objects
    serializer_class = TestSER