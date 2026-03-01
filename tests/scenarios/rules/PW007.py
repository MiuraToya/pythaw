import redis


def handler(event, context):
    r = redis.StrictRedis(host="localhost")  # error: PW007


# OK: module scope
r = redis.StrictRedis(host="localhost")


def handler_ok(event, context):
    r.get("key")
