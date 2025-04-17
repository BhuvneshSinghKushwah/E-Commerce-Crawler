import redis
import os
from dotenv import load_dotenv

load_dotenv()

redis_client = redis.Redis(
    host=os.getenv("redis_host"),
    port=os.getenv("redis_port"),
    db=0,
    decode_responses=True
)

def add_to_set(set_name, *values):
    redis_client.sadd(set_name, *values)

def delete_set(set_name):
    redis_client.delete(set_name)

def is_member(set_name, value):
    return redis_client.sismember(set_name, value)
