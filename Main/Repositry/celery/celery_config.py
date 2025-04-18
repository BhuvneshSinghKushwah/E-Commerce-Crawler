from celery import Celery
import os
from dotenv import load_dotenv

load_dotenv()

app = Celery('my_crawler',
             broker=f'redis://{os.getenv("redis_host")}:{os.getenv("redis_port")}/0',
             backend=f'redis://{os.getenv("redis_host")}:{os.getenv("redis_port")}/1')

app.conf.broker_transport_options = {'max_connections': 20}

import Main.scraper as scraper
