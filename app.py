from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from werkzeug.security import generate_password_hash, check_password_hash
from openpyxl import Workbook, load_workbook
import os, json
from datetime import datetime
from functools import wraps
import yfinance as yf  # Added for tracking real-time market data

app = Flask(__name__)
app.secret_key = 'smart_advisor_secret_key_2024'

USERS_FILE   = 'data_users.xlsx'
HISTORY_FILE = 'data_history.xlsx'
CONTACT_FILE = 'data_contacts.xlsx'

# ── Excel helpers ──────────────────────────────────────────────────────────────

def init_excel():
    if not os.path.exists(USERS_FILE):
        wb = Workbook(); ws = wb.active; ws.title = 'Users'
        ws.append(['id','name','email','username','password','mobile',
                   'qualification','age','income','savings','expenses',
                   'investments','created_at','is_admin'])
        ws.append([1,'Admin','admin@advisor.com','admin',
                   generate_password_hash('admin123'),
                   '','',25,0,0,0,0,
                   datetime.now().strftime('%Y-%m-%d %H:%M:%S'),1])
        wb.save(USERS_FILE)

    if not os.path.exists(HISTORY_FILE):
        wb = Workbook(); ws = wb.active; ws.title = 'History'
        ws.append(['id','user_id','age','income','risk','goal','result','created_at'])
        wb.save(HISTORY_FILE)

    if not os.path.exists(CONTACT_FILE):
        wb = Workbook(); ws = wb.active; ws.title = 'Contacts'
        ws.append(['id','name','email','mobile','subject','message','created_at'])
        wb.save(CONTACT_FILE)

def _load_ws(filepath):
    wb = load_workbook(filepath); return wb, wb.worksheets[0]

def _rows_as_dicts(ws):
    headers = [c.value for c in ws[1]]
    result = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if all(v is None for v in row): continue
        result.append(dict(zip(headers, row)))
    return result

def _next_id(ws):
    max_id = 0
    for row in ws.iter_rows(min_row=2, values_only=True):
        if row[0] and isinstance(row[0], int): max_id = max(max_id, row[0])
    return max_id + 1

def _delete_row_by_id(filepath, rid):
    wb, ws = _load_ws(filepath)
    header = [list(ws[1])]
    keep = header + [list(r) for r in ws.iter_rows(min_row=2) if r[0].value != rid]
    for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
        for cell in row: cell.value = None
    for r_idx, row in enumerate(keep[1:], start=2):
        for c_idx, cell in enumerate(row, start=1):
            ws.cell(row=r_idx, column=c_idx, value=cell.value)
    wb.save(filepath)

# ── User helpers ───────────────────────────────────────────────────────────────

def get_all_users():
    _, ws = _load_ws(USERS_FILE); return _rows_as_dicts(ws)

def get_user_by_id(uid):
    return next((u for u in get_all_users() if u['id'] == uid), None)

def get_user_by_identifier(identifier):
    return next((u for u in get_all_users() if u['email'] == identifier or u['username'] == identifier), None)

def create_user(name, email, username, password, mobile='', qualification='', age=25, income=50000):
    wb, ws = _load_ws(USERS_FILE)
    ws.append([_next_id(ws), name, email, username, password, mobile, qualification,
               int(age), float(income), 0, 0, 0, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 0])
    wb.save(USERS_FILE)

def update_user(uid, **kwargs):
    wb, ws = _load_ws(USERS_FILE)
    headers = [c.value for c in ws[1]]
    for row in ws.iter_rows(min_row=2):
        if row[0].value == uid:
            for k, v in kwargs.items():
                if k in headers: row[headers.index(k)].value = v
            break
    wb.save(USERS_FILE)

# ── History helpers ────────────────────────────────────────────────────────────

def add_history(user_id, age, income, risk, goal, result):
    wb, ws = _load_ws(HISTORY_FILE)
    ws.append([_next_id(ws), user_id, int(age), float(income), risk, goal,
               json.dumps(result), datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
    wb.save(HISTORY_FILE)

def get_user_history(user_id, limit=5):
    _, ws = _load_ws(HISTORY_FILE)
    rows = [r for r in _rows_as_dicts(ws) if r['user_id'] == user_id]
    return list(reversed(rows))[:limit]

def get_all_history():
    _, ws = _load_ws(HISTORY_FILE); return _rows_as_dicts(ws)

# ── Contact helpers ────────────────────────────────────────────────────────────

def add_contact(name, email, mobile, subject, message):
    wb, ws = _load_ws(CONTACT_FILE)
    ws.append([_next_id(ws), name, email, mobile, subject, message,
               datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
    wb.save(CONTACT_FILE)

def get_all_contacts():
    _, ws = _load_ws(CONTACT_FILE); return list(reversed(_rows_as_dicts(ws)))

def delete_contact(cid): _delete_row_by_id(CONTACT_FILE, cid)

# ── Live Market Data Helper ────────────────────────────────────────────────────

def get_live_market_data():
    try:
        # Fetching Yahoo Finance trackers for Nifty 50, Sensex, and Gold futures
        tickers = yf.Tickers('^NSEI ^BSESN GC=F')
        nifty = tickers.tickers['^NSEI'].fast_info
        sensex = tickers.tickers['^BSESN'].fast_info
        gold = tickers.tickers['GC=F'].fast_info
        
        # Real-time data calculations
        n_price = nifty.last_price
        n_change = ((n_price - nifty.previous_close) / nifty.previous_close) * 100
        
        s_price = sensex.last_price
        s_change = ((s_price - sensex.previous_close) / sensex.previous_close) * 100
        
        # Approximate global Gold USD conversion to safe local MCX metric equivalents for 10g 
        raw_gold_oz = gold.last_price
        estimated_gold_10g = (raw_gold_oz * 83.50) / 2.83495
        
        return {
            'nifty': round(n_price, 2),
            'nifty_change': round(n_change, 2),
            'sensex': round(s_price, 2),
            'sensex_change': round(s_change, 2),
            'gold': round(estimated_gold_10g, 2)
        }
    except Exception as e:
        print(f"Error fetching live market data: {e}")
        # Academic standard fallbacks to load smoothly if system is offline
        return {
            'nifty': 24064.55, 'nifty_change': 0.31,
            'sensex': 77058.35, 'sensex_change': 0.33,
            'gold': 72450.00
        }

# ── Auth decorators ────────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def d(*a, **kw):
        if 'user_id' not in session: return redirect(url_for('login'))
        return f(*a, **kw)
    return d

def admin_required(f):
    @wraps(f)
    def d(*a, **kw):
        if not session.get('is_admin'): return redirect(url_for('dashboard'))
        return f(*a, **kw)
    return d

# ── Investment engine ──────────────────────────────────────────────────────────

def predict_investment(age, income, risk, goal):
    risk = risk.lower(); goal = goal.lower()
    age = int(age); income = float(income)

    if risk == 'low':
        portfolio = {'Fixed Deposits':40,'Government Bonds':30,'PPF':20,'Gold':10}
        investments = ['Fixed Deposits','Government Bonds','PPF']
        return_range = '5%–8%'; risk_score = 20
    elif risk == 'medium':
        portfolio = {'Mutual Funds':40,'ETFs':25,'Stocks':20,'FD':15}
        investments = ['Mutual Funds','ETFs','Blue-chip Stocks']
        return_range = '9%–14%'; risk_score = 50
    else:
        portfolio = {'Stocks':35,'Crypto':25,'Small Cap Funds':25,'Commodities':15}
        investments = ['Small Cap Funds','Stocks','Crypto']
        return_range = '15%–25%'; risk_score = 80

    reason = ("At {}, you have a long investment horizon. Aggressive growth strategies suit you well." if age < 30
              else "At {}, a balanced approach between growth and stability is ideal." if age < 45
              else "At {}, capital preservation with steady returns is recommended.").format(age)

    goal_note = {
        'savings':'Focus on liquid, safe instruments for easy access.',
        'wealth':'Long-term wealth creation through equity-heavy portfolio.',
        'education':'Medium-term goal — mix of debt and equity for stability.',
        'retirement':'SIP-based investments with systematic rebalancing recommended.',
        'home':'Debt-oriented instruments with 5–7 year horizon.',
    }.get(goal, 'Diversified portfolio aligned with your financial goal.')

    return {'investments':investments,'portfolio':portfolio,'return_range':return_range,
            'risk_score':risk_score,'reason':reason,'goal_note':goal_note,
            'sip_suggestion':max(1000, int(income*0.2))}

# ── Routes ─────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return redirect(url_for('dashboard') if 'user_id' in session else url_for('login'))

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        user = get_user_by_identifier(request.form['identifier'])
        if user and check_password_hash(str(user['password']), request.form['password']):
            session.update({'user_id':user['id'],'username':user['username'],
                            'name':user['name'],'is_admin':bool(user['is_admin'])})
            return redirect(url_for('admin_panel') if user['is_admin'] else url_for('dashboard'))
        flash('Invalid credentials. Please try again.', 'error')
    return render_template('login.html')

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        username = request.form['username']
        
        if any(u['email']==email for u in get_all_users()):
            flash('Email already registered.', 'error')
        elif any(u['username']==username for u in get_all_users()):
            flash('Username already taken.', 'error')
        else:
            create_user(
                request.form['name'], 
                email, 
                username, 
                generate_password_hash(request.form['password']),
                request.form.get('mobile',''), 
                request.form.get('qualification',''),
                request.form.get('age', 25), 
                request.form.get('income', 50000)
            )
            flash('Account created! Please login.', 'success')
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear(); return redirect(url_for('login'))

# UPDATED ROUTE: Handing structured live metrics safely downstream
@app.route('/dashboard')
@login_required
def dashboard():
    market_data = get_live_market_data()
    return render_template('dashboard.html', 
                           history=get_user_history(session['user_id']), 
                           market=market_data)

@app.route('/predict', methods=['POST'])
@login_required
def predict():
    age=request.form.get('age',30); income=request.form.get('income',50000)
    risk=request.form.get('risk','medium'); goal=request.form.get('goal','wealth')
    result = predict_investment(age, income, risk, goal)
    add_history(session['user_id'], age, income, risk, goal, result)
    return render_template('result.html', age=age, income=income, risk=risk, goal=goal, result=result)

@app.route('/about')
@login_required
def about():
    return render_template('about.html')

@app.route('/contact', methods=['GET','POST'])
@login_required
def contact():
    if request.method == 'POST':
        name=request.form.get('name','').strip()
        email=request.form.get('email','').strip()
        mobile=request.form.get('mobile','').strip()
        subject=request.form.get('subject','').strip()
        message=request.form.get('message','').strip()
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

@app.route('/profile', methods=['GET','POST'])
@login_required
def profile():
    if request.method == 'POST':
        update_user(session['user_id'],
            name=request.form['name'], mobile=request.form.get('mobile',''),
            age=int(request.form.get('age',25)), income=float(request.form.get('income',50000)),
            qualification=request.form.get('qualification',''),
            savings=float(request.form.get('savings',0)),
            expenses=float(request.form.get('expenses',0)),
            investments=float(request.form.get('investments',0)))
        session['name'] = request.form['name']
        flash('Profile updated!', 'success')
        return redirect(url_for('profile'))
    return render_template('profile.html', user=get_user_by_id(session['user_id']))

@app.route('/api/sip', methods=['POST'])
@login_required
def sip_api():
    d=request.json; P=float(d.get('monthly',1000)); years=int(d.get('years',10))
    r=float(d.get('rate',12))/100/12; n=years*12
    fv = P*(((1+r)**n-1)/r)*(1+r) if r else P*n
    growth=[{'year':y,'value':round(P*(((1+r)**(y*12)-1)/r)*(1+r) if r else P*y*12,2),
             'invested':round(P*y*12,2)} for y in range(1,years+1)]
    return jsonify({'future_value':round(fv,2),'growth':growth,'total_invested':round(P*n,2)})

@app.route('/admin')
@login_required
@admin_required
def admin_panel():
    users = [u for u in get_all_users() if not u['is_admin']]
    contacts = get_all_contacts()
    avg_income = (sum(float(u['income'] or 0) for u in users)/len(users)) if users else 0
    return render_template('admin.html', users=users, contacts=contacts,
        total=len(users), avg_income=round(avg_income,2),
        total_advice=len(get_all_history()), total_contacts=len(contacts))

@app.route('/admin/delete/user/<int:uid>', methods=['POST'])
@login_required
@admin_required
def admin_delete_user(uid):
    _delete_row_by_id(USERS_FILE, uid)
    flash('User deleted successfully.', 'success')
    return redirect(url_for('admin_panel'))

@app.route('/admin/delete/contact/<int:cid>', methods=['POST'])
@login_required
@admin_required
def admin_delete_contact(cid):
    delete_contact(cid)
    flash('Contact message deleted.', 'success')
    return redirect(url_for('admin_panel'))

# Initialize Excel files on app startup
init_excel()

if __name__ == '__main__':
    app.run(debug=True, port=5000)