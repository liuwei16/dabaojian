from django.shortcuts import HttpResponse
import datetime
from celery.result import AsyncResult
from dabaojian import celery_app
from apps.api.tasks import add

def create_task(request):
    print('请求来了')
    # 1.立即执行
    # result = add.delay(2,2)
    # 2.定时执行
    # 获取本地时间
    ctime = datetime.datetime.now()
    # 本地时间转换成utc时间
    utc_ctime = datetime.datetime.utcfromtimestamp(ctime.timestamp())
    target_time = utc_ctime + datetime.timedelta(seconds=5)
    result = add.apply_async(args=[11, 3], eta=target_time)
    print('执行完毕')
    return HttpResponse(result.id)

def get_result(request):
    nid = request.GET.get('nid')
    result_object = AsyncResult(id=nid, app=celery_app)
    print(result_object.status) # 获取状态
    data = result_object.get() # 获取数据
    # result_object.forget()  # 把数据在backend中移除。
    # # 取消任务 不想让它执行了
    # result_object.revoke()
    # if result_object.successful():
    #     result_object.get()
    #     result_object.forget()
    # elif result_object.failed():
    #     pass
    # else:
    #     pass
    return HttpResponse(data)