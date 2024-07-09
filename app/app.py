from flask import Flask, render_template, jsonify, request
import os
import psycopg2
from datetime import datetime, timedelta
import secrets
from dotenv import load_dotenv
import time

load_dotenv()  # Load environment variables from .env file

app = Flask(__name__)

# Simulated credential rotation interval (5 minutes for demo purposes)
ROTATION_INTERVAL = 300  # seconds

def get_db_connection():
    max_retries = 5
    retry_delay = 2

    for attempt in range(max_retries):
        try:
            print("Connecting to the database...")
            conn = psycopg2.connect(
                dbname=os.getenv('DB_NAME', 'demo_db'),
                user=os.getenv('DB_USER'),
                password=os.getenv('DB_PASS'),
                host=os.getenv('DB_HOST', 'localhost'),
                port=os.getenv('DB_PORT', '5432')
            )
            print("Connected to the database successfully.")
            return conn
        except psycopg2.OperationalError as e:
            if attempt < max_retries - 1:
                print(f"Connection attempt {attempt + 1} failed. Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                raise e

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS sensitive_data (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            credit_card TEXT NOT NULL,
            ssn TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    cur.close()
    conn.close()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/connection-info')
def connection_info():
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute('SELECT version();')
            version = cur.fetchone()[0]
        conn.close()

        # Simulating credential creation time and expiration
        now = datetime.now()
        created_at = now - timedelta(seconds=now.timestamp() % ROTATION_INTERVAL)
        expires_at = created_at + timedelta(seconds=ROTATION_INTERVAL)

        return jsonify({
            'success': True,
            'message': f'Connected successfully. PostgreSQL version: {version}',
            'username': os.getenv('DB_USER'),
            'created_at': created_at.isoformat(),
            'expires_at': expires_at.isoformat(),
            'rotation_interval': ROTATION_INTERVAL
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/add-record', methods=['POST'])
def add_record():
    try:
        data = request.json
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO sensitive_data (name, credit_card, ssn) VALUES (%s, %s, %s)",
            (data['name'], data['credit_card'], data['ssn'])
        )
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'success': True, 'message': 'Record added successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/get-records')
def get_records():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM sensitive_data ORDER BY created_at DESC LIMIT 5")
        records = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify({'success': True, 'records': records})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', debug=True)
