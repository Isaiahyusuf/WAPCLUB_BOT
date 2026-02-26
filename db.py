import psycopg2
from psycopg2.extras import RealDictCursor
import os
from datetime import datetime, timedelta

DB_URL = os.getenv('DATABASE_URL')

def get_conn():
    return psycopg2.connect(DB_URL, cursor_factory=RealDictCursor)

def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS payments (
        user_id BIGINT PRIMARY KEY,
        package TEXT,
        paid_at TIMESTAMP,
        expires_at TIMESTAMP,
        tx_hash TEXT,
        notified BOOLEAN DEFAULT FALSE
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS groups (
        group_id BIGINT PRIMARY KEY
    )''')
    conn.commit()
    conn.close()

init_db()

def record_payment(user_id, package, tx_hash, duration_days):
    paid_at = datetime.utcnow()
    expires_at = paid_at + timedelta(days=duration_days)
    conn = get_conn()
    c = conn.cursor()
    c.execute('''INSERT INTO payments (user_id, package, paid_at, expires_at, tx_hash, notified)
                 VALUES (%s, %s, %s, %s, %s, FALSE)
                 ON CONFLICT (user_id) DO UPDATE SET package = EXCLUDED.package, paid_at = EXCLUDED.paid_at, expires_at = EXCLUDED.expires_at, tx_hash = EXCLUDED.tx_hash, notified = FALSE''',
              (user_id, package, paid_at, expires_at, tx_hash))
    conn.commit()
    conn.close()

def get_expired_users():
    now = datetime.utcnow()
    conn = get_conn()
    c = conn.cursor()
    c.execute('''SELECT user_id, package, expires_at, notified FROM payments WHERE expires_at <= %s''', (now,))
    users = c.fetchall()
    conn.close()
    return users

def mark_notified(user_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute('''UPDATE payments SET notified = TRUE WHERE user_id = %s''', (user_id,))
    conn.commit()
    conn.close()

def get_user_package(user_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute('''SELECT package FROM payments WHERE user_id = %s''', (user_id,))
    result = c.fetchone()
    conn.close()
    return result['package'] if result else None

def add_group_db(group_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute('''INSERT INTO groups (group_id) VALUES (%s) ON CONFLICT DO NOTHING''', (group_id,))
    conn.commit()
    conn.close()

def get_all_groups():
    conn = get_conn()
    c = conn.cursor()
    c.execute('''SELECT group_id FROM groups''')
    groups = [row['group_id'] for row in c.fetchall()]
    conn.close()
    return groups
