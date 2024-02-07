from celery.result import AsyncResult
# from s1 import app
# result_object = AsyncResult(id="626fc97b-8c13-4953-bf16-f52fae6abbd2", app=app)
import os, sys
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(base_dir)

from dabaojian import celery_app
result_object = AsyncResult(id="1f4e10ec-ca6b-49d6-a441-a0d8003d20da", app=celery_app)
# print(result_object.status) # 获取状态和结果
# print(result_object.get())
print(result_object.revoke()) # 取消任务
