from __future__ import absolute_import, unicode_literals

import os

from celery import Celery
from celery.schedules import crontab
from django.conf import settings
from dotenv import load_dotenv
from kombu import Queue


# set the default Django settings module for the 'celery' program.
# from celery.five import monotonic

load_dotenv()

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'testprep.settings')

app = Celery("testprep")

app.config_from_object('django.conf:settings', namespace='CELERY')
app.conf.task_default_queue = 'celery'
app.conf.accept_content = ['application/json']
app.conf.task_track_started = True

