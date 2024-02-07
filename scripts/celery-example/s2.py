from s1 import x1
result = x1.delay(1, 4) # 将函数和参数放入队列
print(result.id)