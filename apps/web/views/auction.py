import json
import uuid
import datetime
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from apps.api import models
from apps.web.forms.auction import AuctionModelForm, AuctionItemModelForm, AuctionItemDetailModelForm, AuctionItemImageModelForm,  CouponModelForm
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse
# from utils.tencent.cos import upload_file
from utils.os_utils import upload_img_qiniu
from apps.web import tasks
from dabaojian import celery_app
from celery.result import AsyncResult

def auction_list(request):
    """拍卖专场列表"""
    queryset = models.Auction.objects.all().order_by('-id')
    return render(request, 'web/auction_list.html', {'queryset': queryset})

def auction_add(request):
    """创建拍卖专场任务"""
    if request.method == 'GET':
        ctime = datetime.datetime.now()
        form = AuctionModelForm(initial={ # 给定时任务用的
            'preview_start_time': ctime + datetime.timedelta(minutes=1),
            'preview_end_time': ctime + datetime.timedelta(minutes=3),
            'auction_start_time': ctime + datetime.timedelta(minutes=3),
            'auction_end_time': ctime + datetime.timedelta(minutes=5),
        })
        return render(request, 'web/auction_form.html', {'form': form})
    # 如果是发的post请求
    form = AuctionModelForm(data=request.POST, files=request.FILES)
    print(request.POST)
    if form.is_valid():
        instance = form.save()
        # 创建定时任务
        # 1 从为开拍到预展中
        print(datetime.datetime.now())
        preview_utc_starttime = datetime.datetime.utcfromtimestamp(form.instance.preview_start_time.timestamp())
        print(form.instance.preview_start_time)
        print(preview_utc_starttime)
        preview_task_id = tasks.to_preview_status_task.apply_async(args=[instance.id], eta=preview_utc_starttime).id # 返回id
        # 2 从预展中到开拍
        auction_utc_starttime = datetime.datetime.utcfromtimestamp(form.instance.auction_start_time.timestamp())
        auction_task_id = tasks.to_auction_status_task.apply_async(args=[instance.id], eta=auction_utc_starttime).id # 返回id
        # 3.从开拍到结束
        auction_end_utc_datetime = datetime.datetime.utcfromtimestamp(form.instance.auction_end_time.timestamp())
        auction_end_task_id = tasks.end_auction_task.apply_async(args=[instance.id], eta=auction_end_utc_datetime).id
        
        models.AuctionTask.objects.create(
            auction=instance,
            preview_task=preview_task_id,
            auction_task=auction_task_id,
            auction_end_task=auction_end_task_id
        ) # 存到task库中
        return redirect('auction_list')
    return render(request, 'web/auction_form.html', {'form': form})

def auction_edit(request, pk):
    auction_object = models.Auction.objects.filter(id=pk).first()
    if request.method == 'GET':
        form = AuctionModelForm(instance=auction_object)
        return render(request, 'web/auction_form.html', {'form': form})
    # 如果是post请求
    form = AuctionModelForm(data=request.POST, files=request.FILES, instance= auction_object)
    if form.is_valid():
        form.save()
        return redirect('auction_list')
    return render(request, 'web/auction_form.html', {'form': form})
    
def auction_delete(request, pk):
    models.Auction.objects.filter(id=pk).delete()
    # 1.取消所有定时任务，根据ID来进行取消, 还有从worker队列中删除吧
    models.AuctionTask.objects.filter(auction_id=pk).delete()
    return JsonResponse({'status': True})

def auction_item_list(request, auction_id):
    print(request)
    auction_object = models.Auction.objects.filter(id=auction_id).first()
    item_list = models.AuctionItem.objects.filter(auction=auction_object)
    context = {
        'auction_object': auction_object,
        'item_list': item_list
    }
    return render(request, 'web/auction_item_list.html', context)

@csrf_exempt
def auction_item_add(request, auction_id):
    auction_object = models.Auction.objects.filter(id=auction_id).first()
    if request.method == 'GET':
        form = AuctionItemModelForm()
        context = {
            'form': form,
            'auction_object': auction_object
        }
        return render(request, 'web/auction_item_add.html', context)
    # post请求过来
    form = AuctionItemModelForm(data=request.POST, files=request.FILES)
    if form.is_valid():
        # 再新增几个字段到form的instance
        form.instance.auction= auction_object
        form.instance.uid = datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')
        form.save()
        # 返回结果会交给下一个ajax处理
        #   reverse用于合成带有参数(args: e.g. /1)和查询参数(kwargs: e.g. ?item_id=1)的url
        #   Response是通用 HTTP 响应的类，可以返回各种类型的响应，例如 HTML 、纯文本、JSON 等，JsonResponse是Response的子类，会自动设置 Content-Type 头为application/json
        return JsonResponse({
            'status': True,
            'data': {
                'detail_url': reverse('auction_item_detail_add', kwargs={'item_id': form.instance.id}),
                'image_url': reverse('auction_item_image_add', kwargs={'item_id': form.instance.id}),
                'list_url': reverse('auction_item_list', kwargs={'auction_id': auction_id})
            }
        })
    return JsonResponse({'status': False, 'errors': form.errors})

@csrf_exempt
def auction_item_edit(request, auction_id, item_id):
    item_object = models.AuctionItem.objects.filter(id=item_id).first()
    item_detail_list = models.AuctionItemDetail.objects.filter(item=item_object)
    item_image_list = models.AuctionItemImage.objects.filter(item=item_object)
    context = {
        'item_object': item_object,
        'detail_object_list': item_detail_list,
        'image_object_list': item_image_list
    }
    if request.method == 'GET':
        form = AuctionItemModelForm(instance=item_object)
    else:
        print(request.POST)
        print(request.FILES)
        form = AuctionItemModelForm(instance=item_object, data=request.POST, files=request.FILES)
        if form.is_valid():
            form.save()
        else:
            print('fail')
    context['form'] = form
    # print(form)
    return render(request, 'web/auction_item_edit.html', context)

def auction_item_delete(request, item_id):
    models.AuctionItem.objects.filter(id=item_id).delete()
    return JsonResponse({'status': True})

### 以下函数处理商品详细规格 和 商品图片 ###
@csrf_exempt
def auction_item_detail_add(request, item_id):
    """创建规格"""
    detail_list = json.loads(request.body.decode('utf-8'))
    object_list = [models.AuctionItemDetail(**info, item_id=item_id) for info in detail_list if all(info.values())]
    models.AuctionItemDetail.objects.bulk_create(object_list)
    return JsonResponse({'status': True})

@csrf_exempt
def auction_item_detail_add_one(request, item_id):
    """创建规格-一条记录存入数据库-用于编辑时"""
    if request.method != 'POST':
        return JsonResponse({'status': False})
    form = AuctionItemDetailModelForm(data=request.POST)
    if form.is_valid():
        form.instance.item_id = item_id
        instance = form.save()
        return JsonResponse({'status': True, 'data': {'id': instance.id}}) # 返回id有什么用-用于删除按钮
    return JsonResponse({'status': False, 'errors': form.errors})

def auction_item_detail_delete_one(request):
    detail_id = request.GET.get('detail_id')
    models.AuctionItemDetail.objects.filter(id=detail_id).delete()
    return JsonResponse({'status': True})

@csrf_exempt
def auction_item_image_add(request, item_id):
    """创建图片"""
    show_list = request.POST.getlist('show')
    img_object_list = request.FILES.getlist('img')
    orm_object_list = []
    for i in range(len(img_object_list)):
        img_object = img_object_list[i]
        if not img_object:
            continue
        ext = img_object.name.rsplit('.', maxsplit=1)[-1]
        file_name = "{0}.{1}".format(str(uuid.uuid4()), ext)
        cos_path = upload_img_qiniu(key=file_name, file_data=img_object, body_type='bin')
        orm_object_list.append(models.AuctionItemImage(item_id=item_id, img=cos_path, carousel=bool(show_list[i])))
    if orm_object_list:
        models.AuctionItemImage.objects.bulk_create(orm_object_list)
    return JsonResponse({'status': True})
    
@csrf_exempt
def auction_item_image_add_one(request, item_id):
    """创建图片-一条图片记录存入数据库-用于编辑时"""
    form = AuctionItemImageModelForm(data=request.POST, files=request.FILES)
    if form.is_valid():
        form.instance.item_id = item_id
        instance = form.save()
        return JsonResponse({'status': True, 'data': {'id': instance.id}}) # 返回id有什么用-用于删除？
    return JsonResponse({'status': False, 'errors': form.errors})

@csrf_exempt
def auction_item_image_delete_one(request):
    image_id = request.GET.get('image_id')
    models.AuctionItemImage.objects.filter(id=image_id).delete()
    return JsonResponse({'status': True})

def coupon_list(request):
    queryset = models.Coupon.objects.filter(deleted=False).order_by('-id')
    return render(request, 'web/coupon_list.html', {'queryset': queryset})

def coupon_add(request):
    if request.method == 'GET':
        ctime = datetime.datetime.now()
        form = CouponModelForm(initial={
            'apply_start_date': ctime + datetime.timedelta(minutes=5),
            'apply_stop_date': ctime + datetime.timedelta(minutes=20),
        })
        return render(request, 'web/coupon_form.html', {'form': form})
    form = CouponModelForm(data=request.POST)
    if form.is_valid():
        instance = form.save()
        # 开启定时任务-改变优惠券状态
        start_apply_datetime = datetime.datetime.utcfromtimestamp(instance.apply_start_date.timestamp())
        start_task_id = tasks.coupon_start_apply.apply_async(args=[instance.id], eta=start_apply_datetime).id
        stop_apply_datetime = datetime.datetime.utcfromtimestamp(form.instance.apply_stop_date.timestamp())
        stop_task_id = tasks.coupon_stop_apply.apply_async(args=[instance.id], eta=stop_apply_datetime).id
        instance.apply_start_task_id = start_task_id
        instance.apply_stop_task_id = stop_task_id
        instance.save()
        return redirect('coupon_list')
    return render(request, 'web/coupon_form.html', {'form': form})

def coupon_edit(request, pk):
    coupon_object = models.Coupon.objects.filter(id=pk, deleted=False).first()
    if not coupon_object or coupon_object.status!=1:
        return HttpResponse('优惠券不存在或优惠券已开始申请')
    if request.method == 'GET':
        form = CouponModelForm(instance=coupon_object) # instance中传入的是queryset对象
        return render(request, 'web/coupon_form.html', {'form': form})
    form = CouponModelForm(data=request.POST, instance=coupon_object) # instance中传入的是queryset对象
    if form.is_valid():
        if 'apply_start_date' in form.changed_data:
            # 注意要从数据库中取id,因此应该是而非form.instance
            async_result = AsyncResult(id=coupon_object.apply_start_task_id, app=celery_app)
            async_result.revoke()
            start_apply_datetime = datetime.datetime.utcfromtimestamp(form.instance.apply_start_date.timestamp())
            start_task_id = tasks.coupon_start_apply.apply_async(args=[form.instance.id], eta=start_apply_datetime).id
            form.instance.apply_start_task_id = start_task_id
        if 'apply_stop_date' in form.changed_data:
            async_result = AsyncResult(id=coupon_object.apply_stop_task_id, app=celery_app)
            async_result.revoke()
            stop_apply_datetime = datetime.datetime.utcfromtimestamp(form.instance.apply_stop_date.timestamp())
            stop_task_id = tasks.coupon_start_apply.apply_async(args=[form.instance.id], eta=stop_apply_datetime).id
            form.instance.apply_stop_task_id = stop_task_id
        form.save()
        return redirect('coupon_list')
    return render(request, 'web/coupon_form.html', {'form': form})

def coupon_delete(request, pk):
    coupon_object = models.Coupon.objects.filter(id=pk, deleted=False).first()
    if not coupon_object:
        return JsonResponse({'status': False, 'error': '优惠券不存在'})
    # 逻辑删除
    models.Coupon.objects.filter(id=pk, deleted=False).update(deleted=True)
    # 取消定时任务
    async_result = AsyncResult(id=coupon_object.apply_start_task_id, app=celery_app)
    async_result.revoke()
    async_result = AsyncResult(id=coupon_object.apply_stop_task_id, app=celery_app)
    async_result.revoke()
    return JsonResponse({'status': True}) # 为什么返回json数据，是要展示么

