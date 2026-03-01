import psycopg2


def handler(event, context):
    conn = psycopg2.connect(dsn="...")  # error: PW005


# OK: module scope
conn = psycopg2.connect(dsn="...")


def handler_ok(event, context):
    conn.cursor()
