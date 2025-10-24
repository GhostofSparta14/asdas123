import sqlite3
from flask import Flask, render_template, session, redirect, url_for, request, flash, g
from werkzeug.security import generate_password_hash, check_password_hash
import os
import wikipedia
import requests
from bs4 import BeautifulSoup

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE = os.path.join(BASE_DIR, "users.db")

app = Flask(__name__)
app.secret_key = "çok-gizli-bir-anahtar-değiştir"

# ---------- Veritabanı yardımcıları ----------
def get_db():
    if "db" not in g:
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        g.db = conn
    return g.db

@app.teardown_appcontext
def close_db(error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db():
    db = sqlite3.connect(DATABASE)
    cur = db.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)
    db.commit()
    db.close()

init_db()

# ---------- Auth rotaları ----------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not password:
            flash("Kullanıcı adı ve şifre boş olamaz.")
            return render_template('register.html')

        db = get_db()
        try:
            hashed = generate_password_hash(password)
            db.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed))
            db.commit()
        except sqlite3.IntegrityError:
            flash("Bu kullanıcı adı zaten alınmış.")
            return render_template('register.html')

        session['user'] = username
        flash("Kayıt başarılı! Hoşgeldiniz.")
        return redirect(url_for('home'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not password:
            flash("Kullanıcı adı ve şifre girin.")
            return render_template('login.html')

        db = get_db()
        cur = db.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = cur.fetchone()
        if row and check_password_hash(row['password'], password):
            session['user'] = username
            next_page = request.args.get('next') or url_for('home')
            if not next_page.startswith('/'):
                next_page = url_for('home')
            return redirect(next_page)
        else:
            flash("Kullanıcı adı veya şifre yanlış.")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    flash("Çıkış yapıldı.")
    return redirect(url_for('login'))

# ---------- Oturum kontrolü ----------
@app.before_request
def require_login():
    allowed = {'login', 'register', 'static'}
    if request.endpoint is None:
        return
    if request.endpoint in allowed:
        return
    if 'user' in session:
        return
    return redirect(url_for('login', next=request.path))

# ---------- Sayfa rotaları ----------
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/search', methods=['GET', 'POST'])
def search():
    results = []
    if request.method == 'POST':
        query = request.form.get('query', '').strip()
        if query:
            # Örnek statik sonuçlar
            results = [
                {"title": f"{query} hakkında bilgi 1", "link": "#", "snippet": "Burada özet bilgi 1 yer alacak."},
                {"title": f"{query} hakkında bilgi 2", "link": "#", "snippet": "Burada özet bilgi 2 yer alacak."},
                {"title": f"{query} hakkında bilgi 3", "link": "#", "snippet": "Burada özet bilgi 3 yer alacak."},
            ]
    return render_template('search.html', results=results)

# ---------- Ask rotası (Wikipedia + Google) ----------
@app.route('/ask', methods=['GET', 'POST'])
def ask():
    answers = []
    if request.method == 'POST':
        question = request.form.get('question', '').strip()
        if question:
            wikipedia.set_lang("tr")
            try:
                summary = wikipedia.summary(question, sentences=3, auto_suggest=True, redirect=True)
                answers.append({
                    "title": question,
                    "snippet": summary,
                    "link": f"https://tr.wikipedia.org/wiki/{question.replace(' ', '_')}"
                })
            except (wikipedia.exceptions.DisambiguationError, wikipedia.exceptions.PageError):
                try:
                    search_url = f"https://www.google.com/search?q={question.replace(' ', '+')}"
                    headers = {'User-Agent': 'Mozilla/5.0'}
                    response = requests.get(search_url, headers=headers)
                    soup = BeautifulSoup(response.text, 'html.parser')
                    snippet_tag = soup.find('div', class_='BNeawe s3v9rd AP7Wnd')
                    snippet_text = snippet_tag.get_text() if snippet_tag else "Bilgi bulunamadı."
                    snippet_text = snippet_text[:600] + "..." if len(snippet_text) > 600 else snippet_text
                    answers.append({
                        "title": question,
                        "snippet": snippet_text,
                        "link": search_url
                    })
                except:
                    answers.append({
                        "title": question,
                        "snippet": "Bilgi alınamadı.",
                        "link": search_url
                    })
    return render_template('ask.html', answers=answers)

# ---------- Debug ----------
@app.route('/_debug_users')
def debug_users():
    db = get_db()
    rows = db.execute("SELECT username FROM users").fetchall()
    users = [r['username'] for r in rows]
    return "<br>".join(users) or "Kayıtlı kullanıcı yok."

# ---------- Ana program ----------
if __name__ == '__main__':
    app.run(debug=True)
