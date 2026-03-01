import redis


def handler(event, context):
    r = redis.Redis(host="localhost")  # error: PW006


# OK: module scope
r = redis.Redis(host="localhost")


def handler_ok(event, context):
    r.get("key")
