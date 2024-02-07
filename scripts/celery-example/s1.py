from celery import Celery

app = Celery('test', broker='redis://127.0.0.1:6379/1', backend='redis://127.0.0.1:6379/2')
app.conf.timezone = 'Asia/Shanghai'

@app.task
def x1(x, y):
    return x + y


@app.task
def x2(x, y):
    return x - y