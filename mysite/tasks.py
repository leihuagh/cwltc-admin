import logging
from celery import shared_task, Celery

from celery.schedules import crontab

from celery.utils.log import get_task_logger
from datetime import datetime

stdlogger = logging.getLogger(__name__)
app = Celery()

@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    # Calls test('hello') every 10 seconds.
    sender.add_periodic_task(10.0, test.s('hello'), name='add every 10')

    # Calls test('world') every 30 seconds
    sender.add_periodic_task(30.0, test.s('world'), expires=10)

    # Executes every Monday morning at 7:30 a.m.
    sender.add_periodic_task(
        crontab(hour=7, minute=30, day_of_week=1),
        test.s('Happy Mondays!'),
    )

@app.task
def test(arg):
    stdlogger.warning(f'Celery beat {arg}')
    print(arg)
#
# # A periodic task that will run every minute (the symbol "*" means every)
# @periodic_task(run_every=(crontab(hour="*", minute="*", day_of_week="*")))
# def scraper_example():
#     logger.info("Start task")
#     now = datetime.now()
#     result = scrapers.scraper_example(now.day, now.minute)
#     logger.info("Task finished: result = %i" % result)
#
#
#
import time

@shared_task
def addxy(x, y):
    time.sleep(10)
    return x + y