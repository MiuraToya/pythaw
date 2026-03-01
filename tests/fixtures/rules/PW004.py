import pymysql


def handler(event, context):
    conn = pymysql.connect(host="localhost")  # error: PW004


# OK: module scope
conn = pymysql.connect(host="localhost")


def handler_ok(event, context):
    conn.cursor()
