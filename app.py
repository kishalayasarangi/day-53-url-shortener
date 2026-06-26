from flask import Flask, render_template, request, jsonify, redirect, abort
import sqlite3
import string
import random
import qrcode
import io
import base64
from datetime import datetime
from pathlib import Path

app = Flask(__name__)
DB = "urls.db"

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS urls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_url TEXT NOT NULL,
                short_code TEXT UNIQUE NOT NULL,
                clicks INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_clicked TEXT
            )
        ''')
        conn.commit()

def generate_code(length=6):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choices(chars, k=length))

def make_qr(url):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=6,
        border=2
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#7c3aed", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return base64.b64encode(buf.getvalue()).decode()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/shorten', methods=['POST'])
def shorten():
    data = request.get_json()
    url = data.get('url', '').strip()
    custom = data.get('custom', '').strip()

    if not url:
        return jsonify({'error': 'URL is required'}), 400

    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    with get_db() as conn:
        # Check if URL already shortened
        existing = conn.execute(
            'SELECT * FROM urls WHERE original_url = ?', (url,)
        ).fetchone()

        if existing and not custom:
            qr = make_qr(f"http://localhost:5000/{existing['short_code']}")
            return jsonify({
                'short_code': existing['short_code'],
                'short_url': f"http://localhost:5000/{existing['short_code']}",
                'original_url': url,
                'clicks': existing['clicks'],
                'qr': qr,
                'existing': True
            })

        # Use custom code or generate
        code = custom if custom else generate_code()

        # Check custom code availability
        if custom:
            taken = conn.execute(
                'SELECT id FROM urls WHERE short_code = ?', (code,)
            ).fetchone()
            if taken:
                return jsonify({'error': f'"{code}" is already taken!'}), 400

        conn.execute(
            'INSERT INTO urls (original_url, short_code) VALUES (?, ?)',
            (url, code)
        )
        conn.commit()

        qr = make_qr(f"http://localhost:5000/{code}")
        return jsonify({
            'short_code': code,
            'short_url': f"http://localhost:5000/{code}",
            'original_url': url,
            'clicks': 0,
            'qr': qr,
            'existing': False
        }), 201

@app.route('/<code>')
def redirect_url(code):
    with get_db() as conn:
        url = conn.execute(
            'SELECT * FROM urls WHERE short_code = ?', (code,)
        ).fetchone()
        if not url:
            abort(404)
        conn.execute(
            'UPDATE urls SET clicks = clicks + 1, last_clicked = ? WHERE short_code = ?',
            (datetime.now().strftime('%Y-%m-%d %H:%M'), code)
        )
        conn.commit()
        return redirect(url['original_url'])

@app.route('/api/stats/<code>')
def get_stats(code):
    with get_db() as conn:
        url = conn.execute(
            'SELECT * FROM urls WHERE short_code = ?', (code,)
        ).fetchone()
        if not url:
            return jsonify({'error': 'Not found'}), 404
        return jsonify(dict(url))

@app.route('/api/urls')
def get_all():
    with get_db() as conn:
        urls = conn.execute(
            'SELECT * FROM urls ORDER BY clicks DESC LIMIT 20'
        ).fetchall()
        return jsonify([dict(u) for u in urls])

@app.route('/api/urls/<code>', methods=['DELETE'])
def delete_url(code):
    with get_db() as conn:
        conn.execute('DELETE FROM urls WHERE short_code = ?', (code,))
        conn.commit()
        return jsonify({'success': True})

@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404

if __name__ == '__main__':
    init_db()
    print("\n🚀 URL Shortener running at http://localhost:5000\n")
    app.run(debug=True)