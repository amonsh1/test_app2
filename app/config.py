import os

import dotenv


dotenv.load_dotenv()

HOST = os.environ['HOST']  # Меняем здесь - меняем в supervisor.conf
PORT = os.environ['PORT']

PG_HOST = os.environ['PG_HOST']
PG_DB_NAME = os.environ['PG_DB_NAME']
PG_USER = os.environ['PG_USER']
PG_PASS = os.environ['PG_PASS']
PG_PORT = os.environ['PG_PORT']

PAGE_SIZES = list(map(int, os.environ['PAGE_SIZES'].split(',')))

REDIS_DSN = os.environ['REDIS_DSN']
BG_WORKER_TIMEOUT = int(os.environ['BG_WORKER_TIMEOUT'])
CACHE_TIMEOUT = int(os.environ['CACHE_TIMEOUT'])
