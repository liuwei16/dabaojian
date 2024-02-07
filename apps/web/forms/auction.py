from typing import Any
import uuid
from django.forms import ModelForm
from django.db.models.fields.files import FieldFile
from django.core.files.uploadedfile import InMemoryUploadedFile
from apps.api import models
# from utils.tencent.cos import upload_file
from utils.os_utils import upload_img_qiniu
from .bootstrap import BootStrapModelForm

class AuctionModelForm(BootStrapModelForm):
    exclude_bootstrap_class = ['cover']
    
    class Meta:
        model = models.Auction
        exclude = ['status', 'total_price', 'goods_count', 'bid_count', 'look_count', 'video']
    
    """
    处理流程：
    1 自动校验
    2 clean_xx校验
    3 clean检验
    def clean_cover(self):
        # 钩子函数-只处理cover字段 如果只处理一个字段，推荐使用这个方法
        # 获取用户提交对象
        obj = self.cleaned_data.get('cover')
        # 上传到对象存储，获取url
        return url
    """
    def clean(self):
        cleaned_data = self.cleaned_data
        # 获取用户提交对象
        cover_file_object = cleaned_data.get('cover')
        # 如果用户没提交，或者是编辑文件时没有修改（修改后的提交是InMemoryUploadedFile）
        if not cover_file_object or isinstance(cover_file_object, FieldFile):
            return cleaned_data
        ext = cover_file_object.name.rsplit('.', maxsplit=1)[-1]
        file_name = "{0}.{1}".format(str(uuid.uuid4()), ext)
        # cleaned_data['cover'] = upload_file(cover_file_object, file_name)
        cleaned_data['cover'] = upload_img_qiniu(key=file_name, file_data=cover_file_object, body_type='bin')
        return cleaned_data
    
class AuctionItemModelForm(BootStrapModelForm):
    exclude_bootstrap_class = ['cover']
    class Meta:
        model = models.AuctionItem
        exclude = ['auction', 'uid', 'status', 'deal_price', 'video', 'bid_count', 'look_count']
    def clean(self):
        cleaned_data = self.cleaned_data
        # 上传文件
        cover_file_object = cleaned_data.get('cover')
        # print('item cover clean', type(cover_file_object))
        if not cover_file_object or isinstance(cover_file_object, FieldFile):
            return cleaned_data
        ext = cover_file_object.name.rsplit('.', maxsplit=1)[-1]
        file_name = "{0}.{1}".format(str(uuid.uuid4()), ext)
        cleaned_data['cover'] = upload_img_qiniu(key=file_name, file_data=cover_file_object, body_type='bin')
        return cleaned_data

class AuctionItemDetailModelForm(ModelForm):
    class Meta:
        model = models.AuctionItemDetail
        exclude = ['item']

class AuctionItemImageModelForm(BootStrapModelForm):
    class Meta:
        model = models.AuctionItemImage
        exclude = ['item', 'order']
    
    # clean函数用于忘数据库中存储时将原始数据格式化成数据库中需要的字段
    def clean_carousel(self):
        value = self.cleaned_data.get('carousel')
        return bool(value)
    
    def clean(self):
        cleaned_data = self.cleaned_data
        # 上传文件
        cover_file_object = cleaned_data.get('img')
        print('item image clean', type(cover_file_object))
        if not cover_file_object or isinstance(cover_file_object, FieldFile):
            return cleaned_data
        ext = cover_file_object.name.rsplit('.', maxsplit=1)[-1]
        file_name = "{0}.{1}".format(str(uuid.uuid4()), ext)
        cleaned_data['img'] = upload_img_qiniu(key=file_name, file_data=cover_file_object, body_type='bin')
        print('save img succ')
        return cleaned_data
    
class CouponModelForm(BootStrapModelForm):
    class Meta:
        model = models.Coupon
        exclude = ['status', 'apply_count', 'apply_start_task_id', 'apply_stop_task_id', 'deleted']