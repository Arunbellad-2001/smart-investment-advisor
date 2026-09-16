from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os, json
from datetime import datetime
from functools import wraps
import yfinance as yf  # Added for tracking real-time market data

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "smart_advisor_secret_key_2024")

# ── Database Configuration (Supabase PostgreSQL) ──────────────────────────────

DEFAULT_DB_URL = "postgresql://postgres:ArunBellad2001@db.fkfahqjquqtwnexibhnp.supabase.co:5432/postgres"
db_url = os.getenv("DATABASE_URL", DEFAULT_DB_URL)

# SQLAlchemy requires 'postgresql://' instead of legacy 'postgres://'
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ── Database Models ────────────────────────────────────────────────────────────

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    mobile = db.Column(db.String(20), default='')
    qualification = db.Column(db.String(100), default='')
    age = db.Column(db.Integer, default=25)
    income = db.Column(db.Float, default=50000.0)
    savings = db.Column(db.Float, default=0.0)
    expenses = db.Column(db.Float, default=0.0)
    investments = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_admin = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'username': self.username,
            'password': self.password,
            'mobile': self.mobile,
            'qualification': self.qualification,
            'age': self.age,
            'income': self.income,
            'savings': self.savings,
            'expenses': self.expenses,
            'investments': self.investments,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else '',
            'is_admin': int(self.is_admin)
        }

class History(db.Model):
    __tablename__ = 'history'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    income = db.Column(db.Float, nullable=False)
    risk = db.Column(db.String(50), nullable=False)
    goal = db.Column(db.String(50), nullable=False)
    result = db.Column(db.Text, nullable=False)  # JSON Stringified
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'age': self.age,
            'income': self.income,
            'risk': self.risk,
            'goal': self.goal,
            'result': json.loads(self.result) if isinstance(self.result, str) else self.result,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else ''
        }

class Contact(db.Model):
    __tablename__ = 'contacts'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    mobile = db.Column(db.String(20), default='')
    subject = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'mobile': self.mobile,
            'subject': self.subject,
            'message': self.message,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else ''
        }

# Automatic DB Initialization and Default Admin Creation
with app.app_context():
    db.create_all()
    # Create Default Admin if absent
    if not User.query.filter_by(username='admin').first():
        admin = User(
            name='Admin',
            email='admin@advisor.com',
            username='admin',
            password=generate_password_hash('admin123'),
            age=25,
            income=0.0,
            is_admin=True
        )
        db.session.add(admin)
        db.session.commit()

# ── User Helpers ───────────────────────────────────────────────────────────────

def get_all_users():
    return [u.to_dict() for u in User.query.all()]

def get_user_by_id(uid):
    user = User.query.get(uid)
    return user.to_dict() if user else None

def get_user_by_identifier(identifier):
    user = User.query.filter((User.email == identifier) | (User.username == identifier)).first()
    return user.to_dict() if user else None

def create_user(name, email, username, password_hash, mobile='', qualification='', age=25, income=50000):
    new_user = User(
        name=name,
        email=email,
        username=username,
        password=password_hash,
        mobile=mobile,
        qualification=qualification,
        age=int(age),
        income=float(income)
    )
    db.session.add(new_user)
    db.session.commit()

def update_user(uid, **kwargs):
    user = User.query.get(uid)
    if user:
        for k, v in kwargs.items():
            if hasattr(user, k):
                setattr(user, k, v)
        db.session.commit()

# ── History Helpers ────────────────────────────────────────────────────────────

def add_history(user_id, age, income, risk, goal, result):
    history_entry = History(
        user_id=user_id,
        age=int(age),
        income=float(income),
        risk=risk,
        goal=goal,
        result=json.dumps(result)
    )
    db.session.add(history_entry)
    db.session.commit()

def get_user_history(user_id, limit=5):
    history_entries = History.query.filter_by(user_id=user_id).order_by(History.id.desc()).limit(limit).all()
    return [h.to_dict() for h in history_entries]

def get_all_history():
    return [h.to_dict() for h in History.query.all()]

# ── Contact Helpers ────────────────────────────────────────────────────────────

def add_contact(name, email, mobile, subject, message):
    new_contact = Contact(
        name=name,
        email=email,
        mobile=mobile,
        subject=subject,
        message=message
    )
    db.session.add(new_contact)
    db.session.commit()

def get_all_contacts():
    contacts = Contact.query.order_by(Contact.id.desc()).all()
    return [c.to_dict() for c in contacts]

def delete_contact(cid):
    contact = Contact.query.get(cid)
    if contact:
        db.session.delete(contact)
        db.session.commit()

def _delete_row_by_id(model_type, rid):
    if model_type == 'users':
        obj = User.query.get(rid)
    elif model_type == 'contacts':
        obj = Contact.query.get(rid)
    else:
        obj = None
    
    if obj:
        db.session.delete(obj)
        db.session.commit()

# ── Live Market Data Helper ────────────────────────────────────────────────────

def get_live_market_data():
    try:
        tickers = yf.Tickers('^NSEI ^BSESN GC=F')
        nifty = tickers.tickers['^NSEI'].fast_info
        sensex = tickers.tickers['^BSESN'].fast_info
        gold = tickers.tickers['GC=F'].fast_info
        
        n_price = nifty.last_price
        n_change = ((n_price - nifty.previous_close) / nifty.previous_close) * 100
        
        s_price = sensex.last_price
        s_change = ((s_price - sensex.previous_close) / sensex.previous_close) * 100
        
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
        return {
            'nifty': 24064.55, 'nifty_change': 0.31,
            'sensex': 77058.35, 'sensex_change': 0.33,
            'gold': 72450.00
        }

# ── Auth Decorators ────────────────────────────────────────────────────────────

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

# ── Investment Engine ──────────────────────────────────────────────────────────

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
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'error')
        elif User.query.filter_by(username=username).first():
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
    _delete_row_by_id('users', uid)
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