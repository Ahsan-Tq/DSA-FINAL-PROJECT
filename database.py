import sqlite3
import os

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(_BASE_DIR, "blockchain.db")

def init_database():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS blocks (
            "index" INTEGER PRIMARY KEY,
            timestamp TEXT NOT NULL,
            data TEXT NOT NULL,
            previous_hash TEXT NOT NULL,
            hash TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def insert_block(index, timestamp, data, previous_hash, hash_value):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO blocks ("index", timestamp, data, previous_hash, hash)
        VALUES (?, ?, ?, ?, ?)
    ''', (index, timestamp, data, previous_hash, hash_value))
    conn.commit()
    conn.close()

def get_all_blocks():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT "index", timestamp, data, previous_hash, hash FROM blocks ORDER BY "index"')
    results = cursor.fetchall()
    conn.close()
    return results

def update_block_hashes(index, previous_hash, hash_value):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE blocks SET previous_hash = ?, hash = ? WHERE "index" = ?',
        (previous_hash, hash_value, index),
    )
    conn.commit()
    conn.close()

def is_database_empty():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM blocks')
    count = cursor.fetchone()[0]
    conn.close()
    return count == 0
