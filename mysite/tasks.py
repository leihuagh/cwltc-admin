from celery import shared_task
import time

@shared_task
def addxy(x, y):
    time.sleep(10)
    return x + y