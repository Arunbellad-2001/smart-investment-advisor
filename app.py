import os
import json
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from werkzeug.security import generate_password_hash, check_password_hash
from supabase import create_client, Client

# yfinance for live market data
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False

# Dynamically resolve absolute path to the templates and static folders
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, 'templates'),
    static_folder=os.path.join(BASE_DIR, 'static')
)

app.secret_key = os.environ.get('SECRET_KEY', 'smart_advisor_secret_key_2024')

# ─── SUPABASE CONFIG ───────────────────────────────────────────────────────────
SUPABASE_URL = "https://xndvlkiyguwzwnuiolza.supabase.co"   # ← replace
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InhuZHZsa2l5Z3V3endudWlvbHphIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODk4MzcyMzgsImV4cCI6MjEwNTQxMzIzOH0.Myi9qyS1WTOCnwA6ZdFfenDMqC10Hb8nIBRD0u96VM4"                  # ← replace

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# ─── LIVE MARKET DATA ──────────────────────────────────────────────────────────

def _fetch_ticker(symbol):
    """Fetch price + change for one ticker. Returns dict or None on failure."""
    try:
        t    = yf.Ticker(symbol)
        fi   = t.fast_info
        price  = round(float(fi.last_price), 2)
        prev   = round(float(fi.previous_close), 2)
        change = round(price - prev, 2)
        pct    = round((change / prev) * 100, 2) if prev else 0.0
        return {
            'price':  price,
            'change': change,
            'pct':    pct,
            'up':     change >= 0
        }
    except Exception:
        return None


def get_market_data():
    """
    Returns a dict with live Nifty 50, Sensex, Gold and USD/INR data.
    Falls back to placeholder values if yfinance / network is unavailable.
    Best library: yfinance — free, no API key, same as Yahoo Finance.
    Tickers:  Nifty=^NSEI  Sensex=^BSESN  Gold=GC=F  USD/INR=USDINR=X
    """
    # ── Fallback (shown when market is closed or network fails) ──────────────
    fallback = {
        'nifty':  {'price': '—',  'change': 0, 'pct': 0.0, 'up': True,  'label': 'Nifty 50'},
        'sensex': {'price': '—',  'change': 0, 'pct': 0.0, 'up': True,  'label': 'Sensex'},
        'gold':   {'price': '—',  'change': 0, 'pct': 0.0, 'up': True,  'label': 'Gold ($/oz)'},
        'usdinr': {'price': '—',  'change': 0, 'pct': 0.0, 'up': False, 'label': 'USD/INR'},
        'live':   False
    }

    if not YFINANCE_AVAILABLE:
        return fallback

    try:
        nifty  = _fetch_ticker('^NSEI')
        sensex = _fetch_ticker('^BSESN')
        gold   = _fetch_ticker('GC=F')
        usdinr = _fetch_ticker('USDINR=X')

        if not any([nifty, sensex, gold, usdinr]):
            return fallback

        def fmt(data, label):
            if data:
                data['label'] = label
                return data
            return {**fallback[label.lower().replace(' ','').replace('/','')],
                    'label': label}

        return {
            'nifty':  {**(nifty  or fallback['nifty']),  'label': 'Nifty 50'},
            'sensex': {**(sensex or fallback['sensex']), 'label': 'Sensex'},
            'gold':   {**(gold   or fallback['gold']),   'label': 'Gold ($/oz)'},
            'usdinr': {**(usdinr or fallback['usdinr']), 'label': 'USD/INR'},
            'live':   True
        }
    except Exception:
        return fallback


# ─── AUTH DECORATORS ───────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('is_admin'):
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated


# ─── USER HELPERS ──────────────────────────────────────────────────────────────

def get_user_by_identifier(identifier):
    res = supabase.table('users').select('*').eq('email', identifier).execute()
    if res.data:
        return res.data[0]
    res = supabase.table('users').select('*').eq('username', identifier).execute()
    return res.data[0] if res.data else None

def get_user_by_id(uid):
    res = supabase.table('users').select('*').eq('id', uid).execute()
    return res.data[0] if res.data else None

def email_exists(email):
    res = supabase.table('users').select('id').eq('email', email).execute()
    return len(res.data) > 0

def username_exists(username):
    res = supabase.table('users').select('id').eq('username', username).execute()
    return len(res.data) > 0

def create_user(name, email, username, password,
                mobile='', qualification='', age=25, income=50000):
    supabase.table('users').insert({
        'name':          name,
        'email':         email,
        'username':      username,
        'password':      password,
        'mobile':        mobile,
        'qualification': qualification,
        'age':           int(age),
        'income':        float(income),
        'savings':       0,
        'expenses':      0,
        'investments':   0,
        'is_admin':      False,
        'created_at':    datetime.now().isoformat()
    }).execute()

def update_user(uid, **kwargs):
    supabase.table('users').update(kwargs).eq('id', uid).execute()

def delete_user(uid):
    supabase.table('advice_history').delete().eq('user_id', uid).execute()
    supabase.table('users').delete().eq('id', uid).execute()

def get_all_non_admin_users():
    res = (supabase.table('users').select('*')
           .eq('is_admin', False)
           .order('created_at', desc=True)
           .execute())
    return res.data or []


# ─── HISTORY HELPERS ───────────────────────────────────────────────────────────

def add_history(user_id, age, income, risk, goal, result):
    supabase.table('advice_history').insert({
        'user_id':    user_id,
        'age':        int(age),
        'income':     float(income),
        'risk':       risk,
        'goal':       goal,
        'result':     json.dumps(result),
        'created_at': datetime.now().isoformat()
    }).execute()

def get_user_history(user_id, limit=5):
    res = (supabase.table('advice_history').select('*')
           .eq('user_id', user_id)
           .order('created_at', desc=True)
           .limit(limit)
           .execute())
    return res.data or []

def get_all_history():
    res = supabase.table('advice_history').select('*').execute()
    return res.data or []


# ─── CONTACT HELPERS ───────────────────────────────────────────────────────────

def add_contact(name, email, mobile, subject, message):
    supabase.table('contacts').insert({
        'name':       name,
        'email':      email,
        'mobile':     mobile,
        'subject':    subject,
        'message':    message,
        'created_at': datetime.now().isoformat()
    }).execute()

def get_all_contacts():
    res = (supabase.table('contacts').select('*')
           .order('created_at', desc=True)
           .execute())
    return res.data or []

def delete_contact(cid):
    supabase.table('contacts').delete().eq('id', cid).execute()


# ─── INVESTMENT ENGINE ─────────────────────────────────────────────────────────

def predict_investment(age, income, risk, goal):
    risk   = risk.lower()
    goal   = goal.lower()
    age    = int(age)
    income = float(income)

    if risk == 'low':
        portfolio   = {'Fixed Deposits': 40, 'Government Bonds': 30, 'PPF': 20, 'Gold': 10}
        investments = ['Fixed Deposits', 'Government Bonds', 'PPF']
        return_range = '5%–8%'
        risk_score   = 20
    elif risk == 'medium':
        portfolio   = {'Mutual Funds': 40, 'ETFs': 25, 'Stocks': 20, 'FD': 15}
        investments = ['Mutual Funds', 'ETFs', 'Blue-chip Stocks']
        return_range = '9%–14%'
        risk_score   = 50
    else:
        portfolio   = {'Stocks': 35, 'Crypto': 25, 'Small Cap Funds': 25, 'Commodities': 15}
        investments = ['Small Cap Funds', 'Stocks', 'Crypto']
        return_range = '15%–25%'
        risk_score   = 80

    if age < 30:
        reason = f"At {age}, you have a long investment horizon. Aggressive growth strategies suit you well."
    elif age < 45:
        reason = f"At {age}, a balanced approach between growth and stability is ideal."
    else:
        reason = f"At {age}, capital preservation with steady returns is recommended."

    goal_note = {
        'savings':    'Focus on liquid, safe instruments for easy access.',
        'wealth':     'Long-term wealth creation through equity-heavy portfolio.',
        'education':  'Medium-term goal — mix of debt and equity for stability.',
        'retirement': 'SIP-based investments with systematic rebalancing recommended.',
        'home':       'Debt-oriented instruments with 5–7 year horizon.',
    }.get(goal, 'Diversified portfolio aligned with your financial goal.')

    return {
        'investments':    investments,
        'portfolio':      portfolio,
        'return_range':   return_range,
        'risk_score':     risk_score,
        'reason':         reason,
        'goal_note':      goal_note,
        'sip_suggestion': max(1000, int(income * 0.2))
    }


# ─── ROUTES ────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return redirect(url_for('dashboard') if 'user_id' in session else url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = get_user_by_identifier(request.form['identifier'])
        if user and check_password_hash(str(user['password']), request.form['password']):
            session.update({
                'user_id':  user['id'],
                'username': user['username'],
                'name':     user['name'],
                'is_admin': bool(user['is_admin'])
            })
            return redirect(url_for('admin_panel') if user['is_admin'] else url_for('dashboard'))
        flash('Invalid credentials. Please try again.', 'error')
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name          = request.form.get('name', '').strip()
        email         = request.form.get('email', '').strip()
        username      = request.form.get('username', '').strip()
        password      = request.form.get('password', '')
        mobile        = request.form.get('mobile', '').strip()
        qualification = request.form.get('qualification', '')
        age           = request.form.get('age', 25)
        income        = request.form.get('income', 50000)

        if not all([name, email, username, password]):
            flash('Please fill all required fields.', 'error')
        elif email_exists(email):
            flash('Email already registered.', 'error')
        elif username_exists(username):
            flash('Username already taken.', 'error')
        else:
            try:
                create_user(name, email, username,
                            generate_password_hash(password),
                            mobile, qualification, age, income)
                flash('Account created successfully! Please login.', 'success')
                return redirect(url_for('login'))
            except Exception as e:
                flash(f'Registration failed: {str(e)}', 'error')

    return render_template('register.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# ── DASHBOARD — fixed: now fetches and passes market data ────────────────────
@app.route('/dashboard')
@login_required
def dashboard():
    history = get_user_history(session['user_id'])
    market  = get_market_data()                   # ← this was missing before
    return render_template('dashboard.html', history=history, market=market)


@app.route('/predict', methods=['POST'])
@login_required
def predict():
    age    = request.form.get('age', 30)
    income = request.form.get('income', 50000)
    risk   = request.form.get('risk', 'medium')
    goal   = request.form.get('goal', 'wealth')
    result = predict_investment(age, income, risk, goal)
    add_history(session['user_id'], age, income, risk, goal, result)
    return render_template('result.html',
                           age=age, income=income,
                           risk=risk, goal=goal, result=result)


@app.route('/about')
@login_required
def about():
    return render_template('about.html')


@app.route('/contact', methods=['GET', 'POST'])
@login_required
def contact():
    if request.method == 'POST':
        name    = request.form.get('name', '').strip()
        email   = request.form.get('email', '').strip()
        mobile  = request.form.get('mobile', '').strip()
        subject = request.form.get('subject', '').strip()
        message = request.form.get('message', '').strip()
        if name and email and subject and message:
            add_contact(name, email, mobile, subject, message)
            flash('Your message has been sent! We will get back to you soon. ✅', 'success')
            return redirect(url_for('contact'))
        flash('Please fill all required fields.', 'error')
    return render_template('contact.html')


@app.route('/details')
@login_required
def details():
    return render_template('details.html', user=get_user_by_id(session['user_id']))


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        update_user(session['user_id'],
            name          = request.form.get('name'),
            mobile        = request.form.get('mobile', ''),
            age           = int(request.form.get('age', 25)),
            income        = float(request.form.get('income', 50000)),
            qualification = request.form.get('qualification', ''),
            savings       = float(request.form.get('savings', 0)),
            expenses      = float(request.form.get('expenses', 0)),
            investments   = float(request.form.get('investments', 0))
        )
        session['name'] = request.form.get('name')
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))
    return render_template('profile.html', user=get_user_by_id(session['user_id']))


@app.route('/api/sip', methods=['POST'])
@login_required
def sip_api():
    data  = request.json
    P     = float(data.get('monthly', 1000))
    years = int(data.get('years', 10))
    r     = float(data.get('rate', 12)) / 100 / 12
    n     = years * 12
    fv    = P * (((1 + r) ** n - 1) / r) * (1 + r) if r else P * n
    growth = []
    for y in range(1, years + 1):
        ny  = y * 12
        val = P * (((1 + r) ** ny - 1) / r) * (1 + r) if r else P * ny
        growth.append({'year': y, 'value': round(val, 2), 'invested': round(P * ny, 2)})
    return jsonify({
        'future_value':   round(fv, 2),
        'growth':         growth,
        'total_invested': round(P * n, 2)
    })


# ── API: refresh market data (called by dashboard JS every 60s) ──────────────
@app.route('/api/market')
@login_required
def api_market():
    return jsonify(get_market_data())


@app.route('/admin')
@login_required
@admin_required
def admin_panel():
    users      = get_all_non_admin_users()
    contacts   = get_all_contacts()
    history    = get_all_history()
    avg_income = (sum(float(u.get('income') or 0) for u in users) / len(users)) if users else 0
    return render_template('admin.html',
        users          = users,
        contacts       = contacts,
        total          = len(users),
        avg_income     = round(avg_income, 2),
        total_advice   = len(history),
        total_contacts = len(contacts)
    )


@app.route('/admin/delete/user/<int:uid>', methods=['POST'])
@login_required
@admin_required
def admin_delete_user(uid):
    delete_user(uid)
    flash('User deleted successfully.', 'success')
    return redirect(url_for('admin_panel'))


@app.route('/admin/delete/contact/<int:cid>', methods=['POST'])
@login_required
@admin_required
def admin_delete_contact(cid):
    delete_contact(cid)
    flash('Contact message deleted.', 'success')
    return redirect(url_for('admin_panel'))


if __name__ == '__main__':
    app.run(debug=True, port=5000)
