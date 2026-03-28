"""
Event Equipment Rental & Booking Management System
Flask Backend - app.py  (Complete Final Version)
"""

import os, re, uuid, csv, sqlite3 as _sqlite3, io, json, secrets
from datetime import datetime, date, timedelta
from functools import wraps
from flask import (Flask, render_template, request, redirect, url_for,
                   flash, jsonify, make_response, g)
from flask.json.provider import DefaultJSONProvider
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# ── App Setup ─────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = 'sl-events-2025'
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'images', 'equipment')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
DATABASE    = 'database.db'
TOKEN_COOKIE = 'sl_token'

# GCash / Maya — edit these to your real numbers
GCASH_NUMBER = '0992 963 4997'
GCASH_NAME   = 'ERWIL M OLIVARE JR'
MAYA_NUMBER  = '0992 963 4997'
MAYA_NAME    = 'ERWIL M OLIVARE JR'
  
# Make sqlite3.Row JSON-serializable globally
class _RowAwareJSON(DefaultJSONProvider):
    def default(self, o):
        if isinstance(o, _sqlite3.Row):
            return dict(o)
        return super().default(o)

app.json_provider_class = _RowAwareJSON
app.json = _RowAwareJSON(app)

# ── Database ──────────────────────────────────────────────────────
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = _sqlite3.connect(
            os.path.join(os.path.dirname(__file__), DATABASE))
        db.row_factory = _sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def query_db(query, args=(), one=False, commit=False):
    db  = get_db()
    cur = db.execute(query, args)
    if commit:
        db.commit()
        return cur.lastrowid
    rv = cur.fetchall()
    return (rv[0] if rv else None) if one else rv

# ── DB Init + Migration ───────────────────────────────────────────
def init_db():
    db_path = os.path.join(os.path.dirname(__file__), DATABASE)
    db = _sqlite3.connect(db_path)
    db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'admin',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS admin_sessions (
            token TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            username TEXT NOT NULL,
            expires_at DATETIME NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS equipment (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT,
            price_per_rent REAL NOT NULL DEFAULT 0,
            image_path TEXT DEFAULT 'default.jpg',
            status TEXT NOT NULL DEFAULT 'available',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_reference TEXT UNIQUE NOT NULL,
            customer_name TEXT NOT NULL,
            contact_number TEXT NOT NULL,
            email TEXT NOT NULL,
            address TEXT NOT NULL,
            event_date DATE NOT NULL,
            start_time TIME NOT NULL,
            end_time TIME NOT NULL,
            equipment_id INTEGER NOT NULL,
            special_instructions TEXT,
            total_price REAL NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'pending',
            payment_status TEXT NOT NULL DEFAULT 'unpaid',
            amount_paid REAL NOT NULL DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (equipment_id) REFERENCES equipment(id)
        );
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_id INTEGER NOT NULL,
            payment_reference TEXT UNIQUE NOT NULL,
            amount REAL NOT NULL,
            method TEXT NOT NULL,
            sender_name TEXT,
            sender_number TEXT,
            e_ref_number TEXT,
            payment_type TEXT NOT NULL DEFAULT 'full',
            status TEXT NOT NULL DEFAULT 'pending',
            notes TEXT,
            verified_by TEXT,
            verified_at DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (booking_id) REFERENCES bookings(id)
        );
        CREATE INDEX IF NOT EXISTS idx_bookings_date    ON bookings(event_date);
        CREATE INDEX IF NOT EXISTS idx_bookings_status  ON bookings(status);
        CREATE INDEX IF NOT EXISTS idx_payments_booking ON payments(booking_id);
        CREATE INDEX IF NOT EXISTS idx_payments_status  ON payments(status);
    """)

    # Seed admin user
    cur = db.execute("SELECT id FROM users WHERE username='admin'")
    if not cur.fetchone():
        db.execute("INSERT INTO users (username, password_hash, role) VALUES (?,?,?)",
                   ('admin', generate_password_hash('Admin@1234'), 'admin'))

    # Seed sample equipment
    cur = db.execute("SELECT COUNT(*) FROM equipment")
    if cur.fetchone()[0] == 0:
        sample = [
            ('Premium Sound System Pro', 'sound',   'Full PA system with 15" subwoofer, 2x tops, mixer, microphones. Perfect for events up to 500 guests.', 1500, 'sound1.jpg'),
            ('Basic Sound Package',      'sound',   'Portable Bluetooth PA system with 2 wireless mics. Ideal for small gatherings up to 100 guests.',      800,  'sound2.jpg'),
            ('Concert Lighting Rig',     'light',   'Moving head lights, LED par cans, strobe lights, fog machine. Full DJ/concert setup.',                  1200, 'light1.jpg'),
            ('Ambient Event Lighting',   'light',   'Warm fairy lights, uplighting, and pin spots. Perfect for weddings and formal events.',                  700,  'light2.jpg'),
            ('Videoke Pro System',       'videoke', '55" HD display, 50,000+ songs, echo mixer, 4 wireless mics. Party favorite!',                           600,  'videoke1.jpg'),
            ('Dual Videoke Setup',       'videoke', 'Two screens, 100,000+ songs library, colored lighting built-in. For large parties.',                     900,  'videoke2.jpg'),
        ]
        for row in sample:
            db.execute("INSERT INTO equipment (name,category,description,price_per_rent,image_path) VALUES (?,?,?,?,?)", row)

    # Auto-migration: safely add new columns to existing databases
    migrations = [
        ("ALTER TABLE bookings ADD COLUMN payment_status TEXT NOT NULL DEFAULT 'unpaid'", "bookings.payment_status"),
        ("ALTER TABLE bookings ADD COLUMN amount_paid REAL NOT NULL DEFAULT 0",            "bookings.amount_paid"),
    ]
    for sql, col in migrations:
        try:
            db.execute(sql)
            db.commit()
            print(f"  + Migrated: {col}")
        except Exception:
            pass  # Column already exists — safe

    db.commit()
    db.close()
    print("Database ready.")

# ── Server-Side Sessions ──────────────────────────────────────────
def create_admin_session(user_id, username):
    token   = secrets.token_hex(32)
    expires = datetime.utcnow() + timedelta(hours=24)
    query_db(
        "INSERT INTO admin_sessions (token, user_id, username, expires_at) VALUES (?,?,?,?)",
        [token, user_id, username, expires.strftime('%Y-%m-%d %H:%M:%S')],
        commit=True
    )
    return token

def get_admin_session():
    token = request.cookies.get(TOKEN_COOKIE)
    if not token:
        return None
    row = query_db(
        "SELECT * FROM admin_sessions WHERE token=? AND expires_at > datetime('now')",
        [token], one=True
    )
    return {'user_id': row['user_id'], 'username': row['username']} if row else None

def delete_admin_session():
    token = request.cookies.get(TOKEN_COOKIE)
    if token:
        query_db("DELETE FROM admin_sessions WHERE token=?", [token], commit=True)

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not get_admin_session():
            flash('Please log in.', 'warning')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated

# ── Context Processor ─────────────────────────────────────────────
@app.context_processor
def inject_admin():
    adm = get_admin_session()
    return {
        'admin_session': adm,
        'session': {'admin_name': adm['username'] if adm else ''}
    }

# ── Helpers ───────────────────────────────────────────────────────
def allowed_file(f):
    return '.' in f and f.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_email(e):
    return re.match(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$', e)

def generate_reference():
    return 'EVT-' + uuid.uuid4().hex[:8].upper()

def generate_payment_ref():
    return 'PAY-' + uuid.uuid4().hex[:10].upper()

def check_overlap(equipment_id, event_date, start_time, end_time, exclude_id=None):
    q    = """SELECT id FROM bookings WHERE equipment_id=? AND event_date=?
              AND status NOT IN ('rejected') AND (start_time < ? AND end_time > ?)"""
    args = [equipment_id, event_date, end_time, start_time]
    if exclude_id:
        q += " AND id != ?"
        args.append(exclude_id)
    return query_db(q, args, one=True)

def calc_price(equipment_id, start_time=None, end_time=None):
    eq = query_db("SELECT price_per_rent FROM equipment WHERE id=?", [equipment_id], one=True)
    if not eq:
        return 0
    return round(eq['price_per_rent'], 2)

def recalc_payment_status(booking_id):
    booking = query_db("SELECT total_price FROM bookings WHERE id=?", [booking_id], one=True)
    if not booking:
        return
    total = booking['total_price']
    paid  = query_db(
        "SELECT COALESCE(SUM(amount),0) as s FROM payments WHERE booking_id=? AND status='verified'",
        [booking_id], one=True
    )['s']
    if   paid <= 0:          ps = 'unpaid'
    elif paid >= total:      ps = 'full'
    elif paid >= total*0.75: ps = 'partial'
    else:                    ps = 'half'
    query_db("UPDATE bookings SET amount_paid=?, payment_status=? WHERE id=?",
             [paid, ps, booking_id], commit=True)

# ── Template Filters ──────────────────────────────────────────────
@app.template_filter('currency')
def currency_filter(v):
    try:    return f"₱{float(v):,.2f}"
    except: return '₱0.00'

@app.template_filter('timeformat')
def timeformat_filter(v):
    try:    return datetime.strptime(str(v), '%H:%M').strftime('%I:%M %p')
    except: return v

@app.template_filter('dateformat')
def dateformat_filter(v):
    try:    return datetime.strptime(str(v), '%Y-%m-%d').strftime('%B %d, %Y')
    except: return v

# ══════════════════════════════════════════════════════════════════
#  PUBLIC ROUTES
# ══════════════════════════════════════════════════════════════════

@app.route('/')
def index():
    equipment = query_db("SELECT * FROM equipment WHERE status='available' LIMIT 6")
    return render_template('index.html', equipment=equipment)


@app.route('/equipment')
def equipment_list():
    cat = request.args.get('category', '')
    if cat in ('sound', 'light', 'videoke'):
        equips = query_db("SELECT * FROM equipment WHERE status='available' AND category=?", [cat])
    else:
        equips = query_db("SELECT * FROM equipment WHERE status='available'")
        cat = ''
    return render_template('equipment.html', equipment=equips, active_cat=cat)


@app.route('/book', methods=['GET', 'POST'])
def book():
    equipment = query_db("SELECT * FROM equipment WHERE status='available'")
    errors    = {}
    form_data = {}
    pre_eq    = request.args.get('eq', '')

    if request.method == 'POST':
        fd = {k: request.form.get(k, '').strip() for k in [
            'customer_name', 'contact_number', 'email', 'address',
            'event_date', 'start_time', 'end_time', 'equipment_id', 'special_instructions'
        ]}
        form_data = fd

        if not fd['customer_name']:  errors['customer_name']  = 'Full name is required.'
        if not fd['contact_number']: errors['contact_number'] = 'Contact number is required.'
        if not fd['email']:          errors['email']          = 'Email is required.'
        elif not validate_email(fd['email']): errors['email'] = 'Invalid email format.'
        if not fd['address']:        errors['address']        = 'Event address is required.'
        if not fd['event_date']:
            errors['event_date'] = 'Event date is required.'
        else:
            try:
                ev = datetime.strptime(fd['event_date'], '%Y-%m-%d').date()
                if ev < date.today(): errors['event_date'] = 'Event date cannot be in the past.'
            except Exception:
                errors['event_date'] = 'Invalid date.'
        if not fd['start_time']: errors['start_time'] = 'Start time required.'
        if not fd['end_time']:   errors['end_time']   = 'End time required.'
        elif fd['start_time'] and fd['end_time'] <= fd['start_time']:
            errors['end_time'] = 'End time must be after start time.'
        if not fd['equipment_id']: errors['equipment_id'] = 'Please select equipment.'

        if not errors:
            eq_id = int(fd['equipment_id'])
            if check_overlap(eq_id, fd['event_date'], fd['start_time'], fd['end_time']):
                errors['equipment_id'] = 'Already booked for that slot. Choose another time.'
            else:
                total = calc_price(eq_id, fd['start_time'], fd['end_time'])
                ref   = generate_reference()
                query_db("""INSERT INTO bookings
                    (booking_reference,customer_name,contact_number,email,address,
                     event_date,start_time,end_time,equipment_id,special_instructions,total_price,status)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,'pending')""",
                    [ref, fd['customer_name'], fd['contact_number'], fd['email'], fd['address'],
                     fd['event_date'], fd['start_time'], fd['end_time'], eq_id,
                     fd['special_instructions'], total], commit=True)
                return redirect(url_for('confirmation', ref=ref))

    return render_template('booking.html', equipment=equipment,
                           errors=errors, form_data=form_data, pre_eq=pre_eq)


@app.route('/confirmation')
def confirmation():
    ref     = request.args.get('ref', '')
    booking = query_db("""SELECT b.*, e.name as eq_name, e.category
        FROM bookings b JOIN equipment e ON b.equipment_id=e.id
        WHERE b.booking_reference=?""", [ref], one=True)
    if not booking:
        flash('Booking not found.', 'danger')
        return redirect(url_for('index'))
    return render_template('confirmation.html', booking=booking)


@app.route('/api/check-availability', methods=['POST'])
def check_availability():
    data    = request.get_json() or {}
    eq_id   = data.get('equipment_id')
    ev_date = data.get('event_date')
    start   = data.get('start_time')
    end     = data.get('end_time')
    if not all([eq_id, ev_date, start, end]):
        return jsonify({'available': False, 'message': 'Missing fields'})
    overlap = check_overlap(eq_id, ev_date, start, end)
    price   = calc_price(eq_id, start, end) if not overlap else 0
    return jsonify({'available': not bool(overlap),
                    'message': 'Available!' if not overlap else 'Already booked for this slot.',
                    'estimated_price': price})


# ── TRACK BOOKING ─────────────────────────────────────────────────
@app.route('/track', methods=['GET', 'POST'])
def track_booking():
    booking  = None
    payments = []
    error    = None
    searched = False
    ref      = ''
    email    = ''

    if request.method == 'POST':
        ref      = request.form.get('ref',   '').strip().upper()
        email    = request.form.get('email', '').strip().lower()
        searched = True

        if not ref or not email:
            error = 'Please enter both your booking reference and email address.'
        else:
            row = query_db("""
                SELECT b.*, e.name as eq_name, e.category
                FROM bookings b JOIN equipment e ON b.equipment_id=e.id
                WHERE UPPER(b.booking_reference)=? AND LOWER(b.email)=?
            """, [ref, email], one=True)

            if not row:
                error = 'No booking found. Please check your reference number and email.'
            else:
                booking  = row
                payments = query_db(
                    "SELECT * FROM payments WHERE booking_id=? ORDER BY created_at DESC",
                    [booking['id']]
                )

    return render_template('track.html', booking=booking, payments=payments,
                           error=error, searched=searched, ref=ref, email=email)


# ══════════════════════════════════════════════════════════════════
#  PAYMENT ROUTES (Public)
# ══════════════════════════════════════════════════════════════════

@app.route('/pay/<ref>')
def payment_page(ref):
    booking = query_db("""SELECT b.*, e.name as eq_name, e.category
        FROM bookings b JOIN equipment e ON b.equipment_id=e.id
        WHERE b.booking_reference=?""", [ref], one=True)
    if not booking:
        flash('Booking not found.', 'danger')
        return redirect(url_for('index'))
    if booking['status'] == 'rejected':
        flash('This booking has been rejected and cannot be paid.', 'danger')
        return redirect(url_for('index'))

    payments    = query_db("SELECT * FROM payments WHERE booking_id=? ORDER BY created_at DESC",
                           [booking['id']])
    balance     = booking['total_price'] - booking['amount_paid']
    half_amount = round(booking['total_price'] * 0.5, 2)

    return render_template('payment.html', booking=booking, payments=payments,
                           balance=balance, half_amount=half_amount,
                           gcash_number=GCASH_NUMBER, gcash_name=GCASH_NAME,
                           maya_number=MAYA_NUMBER,   maya_name=MAYA_NAME)


@app.route('/pay/<ref>/submit', methods=['POST'])
def submit_payment(ref):
    booking = query_db("""SELECT b.*, e.name as eq_name
        FROM bookings b JOIN equipment e ON b.equipment_id=e.id
        WHERE b.booking_reference=?""", [ref], one=True)
    if not booking:
        flash('Booking not found.', 'danger')
        return redirect(url_for('index'))

    method       = request.form.get('method',        '').strip()
    sender_name  = request.form.get('sender_name',   '').strip()
    sender_num   = request.form.get('sender_number', '').strip()
    e_ref        = request.form.get('e_ref_number',  '').strip()
    amount_str   = request.form.get('amount',        '').strip()
    payment_type = request.form.get('payment_type',  'full').strip()
    notes        = request.form.get('notes',         '').strip()

    errors = []
    if method not in ('gcash', 'maya', 'cash'):
        errors.append('Please select a payment method.')
    if method in ('gcash', 'maya'):
        if not sender_name: errors.append('Sender name is required.')
        if not sender_num:  errors.append('Sender GCash/Maya number is required.')
        if not e_ref:       errors.append('GCash/Maya reference number is required.')
    try:
        amount  = float(amount_str)
        balance = booking['total_price'] - booking['amount_paid']
        if amount <= 0:             errors.append('Amount must be greater than zero.')
        if amount > balance + 0.01: errors.append(f'Amount exceeds remaining balance of P{balance:,.2f}.')
    except Exception:
        errors.append('Please enter a valid amount.')
        amount = 0

    if errors:
        for e in errors: flash(e, 'danger')
        return redirect(url_for('payment_page', ref=ref))

    pay_ref = generate_payment_ref()
    query_db("""INSERT INTO payments
        (booking_id,payment_reference,amount,method,sender_name,
         sender_number,e_ref_number,payment_type,status,notes)
        VALUES (?,?,?,?,?,?,?,?,?,?)""",
        [booking['id'], pay_ref, amount, method, sender_name,
         sender_num, e_ref, payment_type, 'pending', notes], commit=True)

    flash(f'Payment submitted! Reference: {pay_ref}. Please wait for admin verification.', 'success')
    return redirect(url_for('payment_page', ref=ref))


# ══════════════════════════════════════════════════════════════════
#  ADMIN AUTH
# ══════════════════════════════════════════════════════════════════

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if get_admin_session():
        return redirect(url_for('admin_dashboard'))
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user     = query_db("SELECT * FROM users WHERE username=?", [username], one=True)
        if user and check_password_hash(user['password_hash'], password):
            token = create_admin_session(user['id'], user['username'])
            resp  = make_response(redirect(url_for('admin_dashboard')))
            resp.set_cookie(TOKEN_COOKIE, token, max_age=86400,
                            httponly=True, samesite='Lax', path='/')
            return resp
        error = 'Invalid username or password. Try: admin / Admin@1234'
    return render_template('admin/login.html', error=error)


@app.route('/admin/logout')
def admin_logout():
    delete_admin_session()
    resp = make_response(redirect(url_for('admin_login')))
    resp.delete_cookie(TOKEN_COOKIE, path='/')
    return resp


# ══════════════════════════════════════════════════════════════════
#  ADMIN DASHBOARD
# ══════════════════════════════════════════════════════════════════

@app.route('/admin')
@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    stats = {
        'total':            query_db("SELECT COUNT(*) as c FROM bookings", one=True)['c'],
        'pending':          query_db("SELECT COUNT(*) as c FROM bookings WHERE status='pending'", one=True)['c'],
        'approved':         query_db("SELECT COUNT(*) as c FROM bookings WHERE status='approved'", one=True)['c'],
        'completed':        query_db("SELECT COUNT(*) as c FROM bookings WHERE status='completed'", one=True)['c'],
        'revenue':          query_db("SELECT COALESCE(SUM(total_price),0) as r FROM bookings WHERE status IN ('approved','completed')", one=True)['r'],
        'collected':        query_db("SELECT COALESCE(SUM(amount_paid),0) as r FROM bookings", one=True)['r'],
        'pending_payments': query_db("SELECT COUNT(*) as c FROM payments WHERE status='pending'", one=True)['c'],
    }
    recent  = query_db("""SELECT b.*, e.name as eq_name FROM bookings b
        JOIN equipment e ON b.equipment_id=e.id ORDER BY b.created_at DESC LIMIT 10""")
    monthly = [dict(r) for r in query_db("""
        SELECT strftime('%m',event_date) as month,
               COUNT(*) as cnt,
               COALESCE(SUM(total_price),0) as rev
        FROM bookings WHERE status IN ('approved','completed')
          AND strftime('%Y',event_date)=strftime('%Y','now')
        GROUP BY month ORDER BY month""")]
    return render_template('admin/dashboard.html', stats=stats, recent=recent, monthly=monthly)


# ══════════════════════════════════════════════════════════════════
#  ADMIN BOOKINGS
# ══════════════════════════════════════════════════════════════════

@app.route('/admin/bookings')
@login_required
def admin_bookings():
    sf     = request.args.get('status', '')
    pf     = request.args.get('payment_status', '')
    df     = request.args.get('date_from', '')
    dt     = request.args.get('date_to', '')
    search = request.args.get('search', '')
    q      = "SELECT b.*, e.name as eq_name FROM bookings b JOIN equipment e ON b.equipment_id=e.id WHERE 1=1"
    args   = []
    if sf:     q += " AND b.status=?";         args.append(sf)
    if pf:     q += " AND b.payment_status=?"; args.append(pf)
    if df:     q += " AND b.event_date>=?";    args.append(df)
    if dt:     q += " AND b.event_date<=?";    args.append(dt)
    if search:
        q += " AND (b.customer_name LIKE ? OR b.booking_reference LIKE ? OR b.email LIKE ?)"
        args += [f'%{search}%', f'%{search}%', f'%{search}%']
    q += " ORDER BY b.created_at DESC"
    bookings = query_db(q, args)
    return render_template('admin/bookings.html', bookings=bookings,
                           status_filter=sf, payment_filter=pf,
                           date_from=df, date_to=dt, search=search)


@app.route('/admin/bookings/<int:bid>/action', methods=['POST'])
@login_required
def booking_action(bid):
    action = request.form.get('action')
    map_   = {'approve': 'approved', 'reject': 'rejected', 'complete': 'completed'}
    if action == 'delete':
        query_db("DELETE FROM payments WHERE booking_id=?", [bid], commit=True)
        query_db("DELETE FROM bookings WHERE id=?",         [bid], commit=True)
        flash('Booking deleted.', 'info')
    elif action in map_:
        query_db("UPDATE bookings SET status=? WHERE id=?", [map_[action], bid], commit=True)
        flash(f'Booking {map_[action]}.', 'success')
    return redirect(url_for('admin_bookings'))


# ══════════════════════════════════════════════════════════════════
#  ADMIN PAYMENTS
# ══════════════════════════════════════════════════════════════════

@app.route('/admin/payments')
@login_required
def admin_payments():
    sf = request.args.get('status', '')
    mf = request.args.get('method', '')
    q  = """SELECT p.*, b.booking_reference, b.customer_name, b.total_price, b.amount_paid
            FROM payments p JOIN bookings b ON p.booking_id=b.id WHERE 1=1"""
    args = []
    if sf: q += " AND p.status=?"; args.append(sf)
    if mf: q += " AND p.method=?"; args.append(mf)
    q += " ORDER BY p.created_at DESC"
    payments = query_db(q, args)
    totals = {
        'pending':       query_db("SELECT COALESCE(SUM(amount),0) as s FROM payments WHERE status='pending'",  one=True)['s'],
        'verified':      query_db("SELECT COALESCE(SUM(amount),0) as s FROM payments WHERE status='verified'", one=True)['s'],
        'rejected':      query_db("SELECT COALESCE(SUM(amount),0) as s FROM payments WHERE status='rejected'", one=True)['s'],
        'count_pending': query_db("SELECT COUNT(*) as c FROM payments WHERE status='pending'", one=True)['c'],
    }
    return render_template('admin/payments.html', payments=payments, totals=totals,
                           status_filter=sf, method_filter=mf)


@app.route('/admin/payments/<int:pid>/verify', methods=['POST'])
@login_required
def verify_payment(pid):
    action  = request.form.get('action')
    notes   = request.form.get('notes', '')
    adm     = get_admin_session()
    payment = query_db("SELECT * FROM payments WHERE id=?", [pid], one=True)
    if not payment:
        flash('Payment not found.', 'danger')
        return redirect(url_for('admin_payments'))
    if action == 'verify':
        query_db("""UPDATE payments SET status='verified', notes=?, verified_by=?,
                    verified_at=datetime('now') WHERE id=?""",
                 [notes, adm['username'], pid], commit=True)
        recalc_payment_status(payment['booking_id'])
        flash('Payment verified! Booking payment status updated.', 'success')
    elif action == 'reject':
        query_db("UPDATE payments SET status='rejected', notes=? WHERE id=?",
                 [notes, pid], commit=True)
        recalc_payment_status(payment['booking_id'])
        flash('Payment rejected.', 'warning')
    return redirect(url_for('admin_payments'))


@app.route('/admin/payments/record', methods=['POST'])
@login_required
def record_payment():
    booking_id   = request.form.get('booking_id')
    amount_str   = request.form.get('amount', '')
    method       = request.form.get('method', 'cash')
    payment_type = request.form.get('payment_type', 'full')
    notes        = request.form.get('notes', '')
    adm          = get_admin_session()
    booking      = query_db("SELECT * FROM bookings WHERE id=?", [booking_id], one=True)
    if not booking:
        flash('Booking not found.', 'danger')
        return redirect(url_for('admin_payments'))
    try:
        amount = float(amount_str)
        assert amount > 0
    except Exception:
        flash('Invalid amount.', 'danger')
        return redirect(url_for('admin_payments'))
    pay_ref = generate_payment_ref()
    query_db("""INSERT INTO payments
        (booking_id,payment_reference,amount,method,payment_type,
         status,notes,verified_by,verified_at)
        VALUES (?,?,?,?,?,'verified',?,?,datetime('now'))""",
        [booking_id, pay_ref, amount, method, payment_type, notes, adm['username']], commit=True)
    recalc_payment_status(int(booking_id))
    flash(f'Cash payment of P{amount:,.2f} recorded and verified. Ref: {pay_ref}', 'success')
    return redirect(url_for('admin_payments'))


@app.route('/admin/booking/<int:bid>/payments')
@login_required
def booking_payments(bid):
    booking = query_db("""SELECT b.*, e.name as eq_name FROM bookings b
        JOIN equipment e ON b.equipment_id=e.id WHERE b.id=?""", [bid], one=True)
    if not booking:
        flash('Booking not found.', 'danger')
        return redirect(url_for('admin_bookings'))
    payments = query_db("SELECT * FROM payments WHERE booking_id=? ORDER BY created_at DESC", [bid])
    balance  = booking['total_price'] - booking['amount_paid']
    return render_template('admin/booking_payments.html',
                           booking=booking, payments=payments, balance=balance)


# ══════════════════════════════════════════════════════════════════
#  ADMIN EQUIPMENT
# ══════════════════════════════════════════════════════════════════

@app.route('/admin/equipment')
@login_required
def admin_equipment():
    equips = query_db("SELECT * FROM equipment ORDER BY category, name")
    return render_template('admin/equipment.html', equipment=equips)


@app.route('/admin/equipment/add', methods=['GET', 'POST'])
@login_required
def add_equipment():
    errors = {}
    if request.method == 'POST':
        name        = request.form.get('name',          '').strip()
        category    = request.form.get('category',      '').strip()
        description = request.form.get('description',   '').strip()
        price       = request.form.get('price_per_rent','').strip()
        status      = request.form.get('status', 'available')
        if not name: errors['name'] = 'Name required.'
        if category not in ('sound','light','videoke'): errors['category'] = 'Invalid category.'
        try:    price_val = float(price)
        except: errors['price'] = 'Valid price required.'; price_val = 0
        image_path = 'default.jpg'
        if 'image' in request.files:
            f = request.files['image']
            if f and f.filename and allowed_file(f.filename):
                fname = secure_filename(f.filename)
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                f.save(os.path.join(app.config['UPLOAD_FOLDER'], fname))
                image_path = fname
        if not errors:
            query_db("""INSERT INTO equipment
                (name,category,description,price_per_rent,image_path,status)
                VALUES (?,?,?,?,?,?)""",
                [name, category, description, price_val, image_path, status], commit=True)
            flash('Equipment added!', 'success')
            return redirect(url_for('admin_equipment'))
    return render_template('admin/equipment_form.html', errors=errors, eq=None, action='Add')


@app.route('/admin/equipment/<int:eid>/edit', methods=['GET', 'POST'])
@login_required
def edit_equipment(eid):
    eq = query_db("SELECT * FROM equipment WHERE id=?", [eid], one=True)
    if not eq:
        flash('Not found.', 'danger')
        return redirect(url_for('admin_equipment'))
    errors = {}
    if request.method == 'POST':
        name        = request.form.get('name',          '').strip()
        category    = request.form.get('category',      '').strip()
        description = request.form.get('description',   '').strip()
        price       = request.form.get('price_per_rent','').strip()
        status      = request.form.get('status', 'available')
        if not name: errors['name'] = 'Name required.'
        if category not in ('sound','light','videoke'): errors['category'] = 'Invalid category.'
        try:    price_val = float(price)
        except: errors['price'] = 'Valid price required.'; price_val = 0
        image_path = eq['image_path']
        if 'image' in request.files:
            f = request.files['image']
            if f and f.filename and allowed_file(f.filename):
                fname = secure_filename(f.filename)
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                f.save(os.path.join(app.config['UPLOAD_FOLDER'], fname))
                image_path = fname
        if not errors:
            query_db("""UPDATE equipment
                SET name=?,category=?,description=?,price_per_rent=?,image_path=?,status=?
                WHERE id=?""",
                [name, category, description, price_val, image_path, status, eid], commit=True)
            flash('Equipment updated.', 'success')
            return redirect(url_for('admin_equipment'))
    return render_template('admin/equipment_form.html', errors=errors, eq=eq, action='Edit')


@app.route('/admin/equipment/<int:eid>/delete', methods=['POST'])
@login_required
def delete_equipment(eid):
    query_db("DELETE FROM equipment WHERE id=?", [eid], commit=True)
    flash('Equipment deleted.', 'info')
    return redirect(url_for('admin_equipment'))


# ══════════════════════════════════════════════════════════════════
#  ADMIN CALENDAR & REPORTS
# ══════════════════════════════════════════════════════════════════

@app.route('/admin/calendar')
@login_required
def admin_calendar():
    rows   = query_db("""SELECT b.id,b.booking_reference,b.customer_name,b.event_date,
        b.start_time,b.end_time,b.status,e.name as eq_name,e.category
        FROM bookings b JOIN equipment e ON b.equipment_id=e.id
        WHERE b.status IN ('pending','approved') ORDER BY b.event_date""")
    colors = {'pending':'#f59e0b','approved':'#10b981','completed':'#6366f1','rejected':'#ef4444'}
    events = [{'title': f"{r['customer_name']} — {r['eq_name']}",
               'start': f"{r['event_date']}T{r['start_time']}",
               'end':   f"{r['event_date']}T{r['end_time']}",
               'color': colors.get(r['status'], '#888'),
               'extendedProps': {'ref': r['booking_reference'], 'status': r['status'],
                                 'customer': r['customer_name'], 'equipment': r['eq_name']}}
              for r in rows]
    return render_template('admin/calendar.html', events_json=json.dumps(events))


@app.route('/admin/reports')
@login_required
def admin_reports():
    df   = request.args.get('date_from', '')
    dt   = request.args.get('date_to', '')
    q    = """SELECT b.*, e.name as eq_name, e.category FROM bookings b
              JOIN equipment e ON b.equipment_id=e.id WHERE b.status IN ('approved','completed')"""
    args = []
    if df: q += " AND b.event_date>=?"; args.append(df)
    if dt: q += " AND b.event_date<=?"; args.append(dt)
    q += " ORDER BY b.event_date DESC"
    rows      = query_db(q, args)
    total_rev = sum(r['total_price'] for r in rows)
    by_cat    = {}
    for r in rows:
        by_cat[r['category']] = by_cat.get(r['category'], 0) + r['total_price']
    if request.args.get('download') == 'csv':
        out = io.StringIO()
        w   = csv.writer(out)
        w.writerow(['Reference','Customer','Email','Contact','Equipment','Category',
                    'Date','Start','End','Total','Amount Paid','Payment Status','Status'])
        for r in rows:
            w.writerow([r['booking_reference'], r['customer_name'], r['email'],
                        r['contact_number'], r['eq_name'], r['category'],
                        r['event_date'], r['start_time'], r['end_time'],
                        r['total_price'], r['amount_paid'], r['payment_status'], r['status']])
        resp = make_response(out.getvalue())
        resp.headers['Content-Disposition'] = 'attachment; filename=report.csv'
        resp.headers['Content-Type']        = 'text/csv'
        return resp
    return render_template('admin/reports.html', rows=rows, total_rev=total_rev,
                           by_cat=by_cat, date_from=df, date_to=dt)


# ══════════════════════════════════════════════════════════════════
#  ERROR HANDLERS
# ══════════════════════════════════════════════════════════════════

@app.errorhandler(404)
def not_found(e):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('errors/500.html'), 500


# ══════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════


# ── DB MIGRATION ──────────────────────────────────────────────────
def migrate_db():
    """Rename price_per_hour -> price_per_rent if the old column still exists."""
    db_path = os.path.join(os.path.dirname(__file__), DATABASE)
    db = _sqlite3.connect(db_path)
    cols = [row[1] for row in db.execute("PRAGMA table_info(equipment)").fetchall()]
    if 'price_per_hour' in cols and 'price_per_rent' not in cols:
        db.execute("ALTER TABLE equipment RENAME COLUMN price_per_hour TO price_per_rent")
        db.commit()
    db.close()

if __name__ == '__main__':
    os.makedirs(os.path.join('static', 'images', 'equipment'), exist_ok=True)
    init_db()
    migrate_db()
    app.run(debug=True, host='0.0.0.0', port=5000)