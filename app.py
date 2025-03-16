import os
import sqlite3
import logging
import datetime
import json
import io
import csv
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, make_response
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import base64
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from flask import Response

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "development_secret_key")

# Database connection helper
def get_db_connection():
    conn = sqlite3.connect('sitin_system.db')
    conn.row_factory = sqlite3.Row
    return conn

# Initialize database tables
def init_db():
    conn = get_db_connection()
    
    # Create tables
    conn.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL,
        date_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    conn.execute('''
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        program TEXT NOT NULL,
        year_level INTEGER,
        date_registered TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    conn.execute('''
    CREATE TABLE IF NOT EXISTS laboratories (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        capacity INTEGER NOT NULL,
        description TEXT
    )
    ''')
    
    conn.execute('''
    CREATE TABLE IF NOT EXISTS sit_ins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        purpose TEXT NOT NULL,
        lab_id INTEGER NOT NULL,
        login_time TIMESTAMP NOT NULL,
        logout_time TIMESTAMP,
        status TEXT DEFAULT 'active',
        session_remaining INTEGER,
        FOREIGN KEY (student_id) REFERENCES students (id),
        FOREIGN KEY (lab_id) REFERENCES laboratories (id)
    )
    ''')
    
    conn.execute('''
    CREATE TABLE IF NOT EXISTS announcements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        content TEXT NOT NULL,
        posted_by TEXT NOT NULL,
        date_posted TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    conn.execute('''
    CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        lab_id INTEGER NOT NULL,
        message TEXT NOT NULL,
        date_submitted TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (student_id) REFERENCES students (id),
        FOREIGN KEY (lab_id) REFERENCES laboratories (id)
    )
    ''')
    
    conn.execute('''
    CREATE TABLE IF NOT EXISTS reservations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        lab_id INTEGER NOT NULL,
        purpose TEXT NOT NULL,
        date DATE NOT NULL,
        start_time TIME NOT NULL,
        end_time TIME NOT NULL,
        status TEXT DEFAULT 'pending',
        date_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (student_id) REFERENCES students (id),
        FOREIGN KEY (lab_id) REFERENCES laboratories (id)
    )
    ''')
    
    # Insert default admin user if not exists
    admin_exists = conn.execute("SELECT id FROM users WHERE username = 'admin'").fetchone()
    
    if not admin_exists:
        conn.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                     ('admin', generate_password_hash('admin123'), 'admin'))
    
    # Insert sample laboratory data if not exists
    labs_exist = conn.execute("SELECT id FROM laboratories").fetchone()
    
    if not labs_exist:
        lab_data = [
            (524, 'Laboratory 524', 30, 'General Programming Lab'),
            (526, 'Laboratory 526', 25, 'C# Programming Lab'),
            (528, 'Laboratory 528', 30, 'Web Development Lab'),
            (530, 'Laboratory 530', 35, 'Java Programming Lab'),
            (542, 'Laboratory 542', 25, 'Mobile Development Lab')
        ]
        
        conn.executemany("INSERT INTO laboratories (id, name, capacity, description) VALUES (?, ?, ?, ?)", lab_data)
    
    conn.commit()
    conn.close()

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Admin required decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_role' not in session or session['user_role'] != 'admin':
            flash('Admin access required', 'error')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('home'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['user_role'] = user['role']
            return redirect(url_for('home'))
        else:
            flash('Invalid credentials', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('register.html')
        
        conn = get_db_connection()
        
        # Check if username already exists
        existing_user = conn.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
        
        if existing_user:
            conn.close()
            flash('Username already exists', 'error')
            return render_template('register.html')
        
        # Insert new user
        conn.execute('INSERT INTO users (username, password, role) VALUES (?, ?, ?)',
                    (username, generate_password_hash(password), 'user'))
        conn.commit()
        conn.close()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/home')
@login_required
def home():
    conn = get_db_connection()
    
    # Get statistics
    students_registered = conn.execute('SELECT COUNT(*) as count FROM students').fetchone()['count']
    currently_sit_in = conn.execute('SELECT COUNT(*) as count FROM sit_ins WHERE status = "active"').fetchone()['count']
    total_sit_in = conn.execute('SELECT COUNT(*) as count FROM sit_ins').fetchone()['count']
    
    # Get programming languages statistics
    programming_stats = conn.execute('''
        SELECT purpose, COUNT(*) as count 
        FROM sit_ins 
        GROUP BY purpose
    ''').fetchall()
    
    # Get announcements
    announcements = conn.execute('''
        SELECT content, posted_by, date_posted 
        FROM announcements 
        ORDER BY date_posted DESC 
        LIMIT 10
    ''').fetchall()
    
    conn.close()
    
    # Prepare programming stats for chart
    prog_labels = [row['purpose'] for row in programming_stats]
    prog_counts = [row['count'] for row in programming_stats]
    
    return render_template('home.html', 
                          students_registered=students_registered,
                          currently_sit_in=currently_sit_in,
                          total_sit_in=total_sit_in,
                          prog_labels=json.dumps(prog_labels),
                          prog_counts=json.dumps(prog_counts),
                          announcements=announcements)

@app.route('/search', methods=['GET', 'POST'])
@login_required
def search():
    # Get data for dropdowns
    conn = get_db_connection()
    programs = conn.execute('SELECT DISTINCT program FROM students ORDER BY program').fetchall()
    laboratories = conn.execute('SELECT * FROM laboratories').fetchall()
    
    student = None
    recent_activity = []
    
    # Check for GET parameter first
    student_id_param = request.args.get('student_id')
    if student_id_param:
        student = conn.execute('SELECT * FROM students WHERE id = ?', (student_id_param,)).fetchone()
        if student:
            recent_activity = conn.execute('''
                SELECT purpose, lab_id, login_time, logout_time 
                FROM sit_ins 
                WHERE student_id = ? 
                ORDER BY login_time DESC LIMIT 5
            ''', (student_id_param,)).fetchall()
    
    # Handle POST search
    if request.method == 'POST':
        student_id = request.form.get('student_id')
        program = request.form.get('program')
        year_level = request.form.get('year_level')
        
        if not student_id and not program and not year_level:
            flash('Please enter search criteria', 'error')
            conn.close()
            return redirect(url_for('search'))
        
        # Build query dynamically based on parameters
        query = 'SELECT * FROM students WHERE 1=1'
        params = []
        
        if student_id:
            # Try both exact ID match and name/program contains search
            query += ' AND (id = ? OR name LIKE ? OR program LIKE ?)'
            params.extend([student_id, f'%{student_id}%', f'%{student_id}%'])
        
        if program:
            query += ' AND program = ?'
            params.append(program)
        
        if year_level:
            query += ' AND year_level = ?'
            params.append(year_level)
        
        # Limit to first result if there are multiple matches
        query += ' LIMIT 1'
        
        student = conn.execute(query, params).fetchone()
        
        if student:
            recent_activity = conn.execute('''
                SELECT purpose, lab_id, login_time, logout_time 
                FROM sit_ins 
                WHERE student_id = ? 
                ORDER BY login_time DESC LIMIT 5
            ''', (student['id'],)).fetchall()
        else:
            flash('No matching student found', 'error')
    
    conn.close()
    
    return render_template('search.html', 
                          student=student, 
                          programs=programs,
                          laboratories=laboratories,
                          recent_activity=recent_activity)

@app.route('/api/search-students', methods=['GET'])
@login_required
def api_search_students():
    query = request.args.get('query', '')
    
    if not query or len(query) < 2:
        return jsonify({'students': []})
    
    conn = get_db_connection()
    
    # Search by ID, name, and program with LIKE
    students = conn.execute('''
        SELECT id, name, program, year_level
        FROM students
        WHERE id LIKE ? OR name LIKE ? OR program LIKE ?
        LIMIT 5
    ''', (f'%{query}%', f'%{query}%', f'%{query}%')).fetchall()
    
    # Convert row objects to dictionaries
    result = []
    for student in students:
        result.append({
            'id': student['id'],
            'name': student['name'],
            'program': student['program'],
            'year_level': student['year_level']
        })
    
    conn.close()
    
    return jsonify({'students': result})

@app.route('/student/<int:student_id>')
@login_required
def get_student(student_id):
    conn = get_db_connection()
    student = conn.execute('SELECT * FROM students WHERE id = ?', (student_id,)).fetchone()
    conn.close()
    
    if student:
        return jsonify({
            'id': student['id'],
            'name': student['name'],
            'program': student['program']
        })
    else:
        return jsonify({'error': 'Student not found'}), 404

@app.route('/sit-in', methods=['GET', 'POST'])
@login_required
def sit_in():
    if request.method == 'POST':
        student_id = request.form.get('student_id')
        student_name = request.form.get('student_name')
        purpose = request.form.get('purpose')
        lab_id = request.form.get('lab')
        remaining_session = request.form.get('remaining_session', 30)
        
        # Check if student exists
        conn = get_db_connection()
        student = conn.execute('SELECT * FROM students WHERE id = ?', (student_id,)).fetchone()
        
        # If student doesn't exist, add them
        if not student:
            conn.execute('INSERT INTO students (id, name, program, year_level) VALUES (?, ?, ?, ?)',
                        (student_id, student_name, purpose.split(' ')[0], 1))
        
        # Check if student already has an active sit-in
        active_sit_in = conn.execute('''
            SELECT * FROM sit_ins 
            WHERE student_id = ? AND status = "active"
        ''', (student_id,)).fetchone()
        
        if active_sit_in:
            conn.close()
            flash('Student already has an active sit-in session', 'error')
            return redirect(url_for('sit_in'))
        
        # Create new sit-in record
        now = datetime.datetime.now()
        conn.execute('''
            INSERT INTO sit_ins (student_id, purpose, lab_id, login_time, status, session_remaining)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (student_id, purpose, lab_id, now, 'active', remaining_session))
        
        conn.commit()
        conn.close()
        
        flash('Student successfully checked in', 'success')
        return redirect(url_for('view_sit_in'))
    
    # GET method - display form
    conn = get_db_connection()
    laboratories = conn.execute('SELECT * FROM laboratories').fetchall()
    current_sit_ins = conn.execute('''
        SELECT s.id, s.student_id, st.name, s.purpose, s.lab_id, l.name as lab_name, 
               s.login_time, s.status, s.session_remaining
        FROM sit_ins s
        JOIN students st ON s.student_id = st.id
        JOIN laboratories l ON s.lab_id = l.id
        WHERE s.status = "active"
        ORDER BY s.login_time DESC
    ''').fetchall()
    conn.close()
    
    return render_template('sit_in.html', laboratories=laboratories, current_sit_ins=current_sit_ins)

@app.route('/checkout/<int:sit_in_id>')
@login_required
def checkout(sit_in_id):
    conn = get_db_connection()
    
    # Update sit-in status and logout time
    now = datetime.datetime.now()
    conn.execute('''
        UPDATE sit_ins 
        SET status = "completed", logout_time = ? 
        WHERE id = ?
    ''', (now, sit_in_id))
    
    conn.commit()
    conn.close()
    
    flash('Student successfully checked out', 'success')
    return redirect(url_for('view_sit_in'))

@app.route('/view-sit-in')
@login_required
def view_sit_in():
    conn = get_db_connection()
    current_sit_ins = conn.execute('''
        SELECT s.id, s.student_id, st.name, s.purpose, s.lab_id, l.name as lab_name, 
               s.login_time, s.status, s.session_remaining
        FROM sit_ins s
        JOIN students st ON s.student_id = st.id
        JOIN laboratories l ON s.lab_id = l.id
        WHERE s.status = "active"
        ORDER BY s.login_time DESC
    ''').fetchall()
    conn.close()
    
    return render_template('sit_in.html', current_sit_ins=current_sit_ins)

@app.route('/sit-in-records')
@login_required
def sit_in_records():
    # Get filter parameters
    date_filter = request.args.get('date', datetime.date.today().strftime('%Y-%m-%d'))
    lab_filter = request.args.get('lab', 'all')
    purpose_filter = request.args.get('purpose', 'all')
    
    conn = get_db_connection()
    
    # Build query based on filters
    query = '''
        SELECT s.id, s.student_id, st.name, s.purpose, s.lab_id, l.name as lab_name, 
               s.login_time, s.logout_time, s.status
        FROM sit_ins s
        JOIN students st ON s.student_id = st.id
        JOIN laboratories l ON s.lab_id = l.id
        WHERE DATE(s.login_time) = ?
    '''
    params = [date_filter]
    
    if lab_filter != 'all':
        query += ' AND s.lab_id = ?'
        params.append(lab_filter)
    
    if purpose_filter != 'all':
        query += ' AND s.purpose LIKE ?'
        params.append(f'%{purpose_filter}%')
    
    query += ' ORDER BY s.login_time DESC'
    
    records = conn.execute(query, params).fetchall()
    
    # Get programming language statistics
    programming_stats = conn.execute('''
        SELECT purpose, COUNT(*) as count 
        FROM sit_ins 
        WHERE DATE(login_time) = ?
        GROUP BY purpose
    ''', (date_filter,)).fetchall()
    
    # Get laboratory usage statistics
    lab_stats = conn.execute('''
        SELECT l.id, l.name, COUNT(*) as count 
        FROM sit_ins s
        JOIN laboratories l ON s.lab_id = l.id
        WHERE DATE(s.login_time) = ?
        GROUP BY s.lab_id
    ''', (date_filter,)).fetchall()
    
    laboratories = conn.execute('SELECT * FROM laboratories').fetchall()
    
    conn.close()
    
    # Prepare programming stats for chart
    prog_labels = [row['purpose'] for row in programming_stats]
    prog_counts = [row['count'] for row in programming_stats]
    
    # Prepare lab stats for chart
    lab_labels = [row['name'] for row in lab_stats]
    lab_counts = [row['count'] for row in lab_stats]
    
    return render_template('sit_in_records.html', 
                          records=records,
                          laboratories=laboratories,
                          date_filter=date_filter,
                          lab_filter=lab_filter,
                          purpose_filter=purpose_filter,
                          prog_labels=json.dumps(prog_labels),
                          prog_counts=json.dumps(prog_counts),
                          lab_labels=json.dumps(lab_labels),
                          lab_counts=json.dumps(lab_counts))

@app.route('/sit-in-reports')
@login_required
def sit_in_reports():
    # Get filter parameters
    date_from = request.args.get('date_from', (datetime.date.today() - datetime.timedelta(days=30)).strftime('%Y-%m-%d'))
    date_to = request.args.get('date_to', datetime.date.today().strftime('%Y-%m-%d'))
    lab_filter = request.args.get('lab', 'all')
    student_filter = request.args.get('student', '')
    purpose_filter = request.args.get('purpose', 'all')
    
    conn = get_db_connection()
    
    # Build query based on filters
    query = '''
        SELECT s.id, s.student_id, st.name, s.purpose, s.lab_id, l.name as lab_name, 
               s.login_time, s.logout_time, s.status
        FROM sit_ins s
        JOIN students st ON s.student_id = st.id
        JOIN laboratories l ON s.lab_id = l.id
        WHERE DATE(s.login_time) BETWEEN ? AND ?
    '''
    params = [date_from, date_to]
    
    if lab_filter != 'all':
        query += ' AND s.lab_id = ?'
        params.append(lab_filter)
    
    if purpose_filter != 'all':
        query += ' AND s.purpose LIKE ?'
        params.append(f'%{purpose_filter}%')
    
    if student_filter:
        query += ' AND (st.id LIKE ? OR st.name LIKE ?)'
        params.extend([f'%{student_filter}%', f'%{student_filter}%'])
    
    query += ' ORDER BY s.login_time DESC'
    
    reports = conn.execute(query, params).fetchall()
    laboratories = conn.execute('SELECT * FROM laboratories').fetchall()
    
    conn.close()
    
    return render_template('sit_in_reports.html', 
                          reports=reports,
                          laboratories=laboratories,
                          date_from=date_from,
                          date_to=date_to,
                          lab_filter=lab_filter,
                          student_filter=student_filter,
                          purpose_filter=purpose_filter)

@app.route('/export-report')
@login_required
def export_report():
    format_type = request.args.get('format', 'csv')
    
    # Get filter parameters
    date_from = request.args.get('date_from', (datetime.date.today() - datetime.timedelta(days=30)).strftime('%Y-%m-%d'))
    date_to = request.args.get('date_to', datetime.date.today().strftime('%Y-%m-%d'))
    lab_filter = request.args.get('lab', 'all')
    student_filter = request.args.get('student', '')
    purpose_filter = request.args.get('purpose', 'all')
    
    conn = get_db_connection()
    
    # Build query based on filters
    query = '''
        SELECT s.id, s.student_id, st.name, s.purpose, l.name as lab_name, 
               s.login_time, s.logout_time, 
               CASE 
                   WHEN s.logout_time IS NOT NULL THEN 
                       (strftime('%s', s.logout_time) - strftime('%s', s.login_time)) / 60 
                   ELSE 0 
               END as duration_minutes
        FROM sit_ins s
        JOIN students st ON s.student_id = st.id
        JOIN laboratories l ON s.lab_id = l.id
        WHERE DATE(s.login_time) BETWEEN ? AND ?
    '''
    params = [date_from, date_to]
    
    if lab_filter != 'all':
        query += ' AND s.lab_id = ?'
        params.append(lab_filter)
    
    if purpose_filter != 'all':
        query += ' AND s.purpose LIKE ?'
        params.append(f'%{purpose_filter}%')
    
    if student_filter:
        query += ' AND (st.id LIKE ? OR st.name LIKE ?)'
        params.extend([f'%{student_filter}%', f'%{student_filter}%'])
    
    query += ' ORDER BY s.login_time DESC'
    
    reports = conn.execute(query, params).fetchall()
    conn.close()
    
    # Convert to pandas DataFrame
    data = []
    for row in reports:
        login_time = datetime.datetime.strptime(row['login_time'], '%Y-%m-%d %H:%M:%S.%f')
        logout_time = None if row['logout_time'] is None else datetime.datetime.strptime(row['logout_time'], '%Y-%m-%d %H:%M:%S.%f')
        
        data.append({
            'ID Number': row['student_id'],
            'Name': row['name'],
            'Purpose': row['purpose'],
            'Laboratory': row['lab_name'],
            'Login': login_time.strftime('%Y-%m-%d %H:%M:%S'),
            'Logout': '' if logout_time is None else logout_time.strftime('%Y-%m-%d %H:%M:%S'),
            'Duration (min)': row['duration_minutes']
        })
    
    df = pd.DataFrame(data)
    
    # Export based on format
    if format_type == 'csv':
        output = io.StringIO()
        df.to_csv(output, index=False)
        response = make_response(output.getvalue())
        response.headers["Content-Disposition"] = "attachment; filename=sit_in_report.csv"
        response.headers["Content-type"] = "text/csv"
        return response
    
    elif format_type == 'excel':
        output = io.BytesIO()
        df.to_excel(output, index=False)
        response = make_response(output.getvalue())
        response.headers["Content-Disposition"] = "attachment; filename=sit_in_report.xlsx"
        response.headers["Content-type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        return response
    
    elif format_type == 'pdf':
        # Simple PDF export using HTML rendering
        html = df.to_html(classes='table table-striped', index=False)
        
        # Add CSS styling
        styled_html = f'''
        <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; }}
                    .table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                    .table th {{ background-color: #004080; color: white; text-align: left; padding: 8px; }}
                    .table td {{ border: 1px solid #ddd; padding: 8px; }}
                    .table-striped tr:nth-child(even) {{ background-color: #f2f2f2; }}
                    h1 {{ color: #004080; }}
                </style>
            </head>
            <body>
                <h1>Sit-In Report</h1>
                <p>From: {date_from} To: {date_to}</p>
                {html}
            </body>
        </html>
        '''
        
        # Return HTML content with PDF headers
        response = make_response(styled_html)
        response.headers["Content-Disposition"] = "attachment; filename=sit_in_report.html"
        response.headers["Content-type"] = "text/html"
        return response
    
    else:
        return jsonify({'error': 'Unsupported format'}), 400

@app.route('/feedback-reports')
@login_required
def feedback_reports():
    # Get filter parameters
    lab_filter = request.args.get('lab', 'all')
    date_filter = request.args.get('date', 'all')
    
    conn = get_db_connection()
    
    # Build query based on filters
    query = '''
        SELECT f.id, f.student_id, st.name, f.lab_id, l.name as lab_name, 
               f.message, f.date_submitted
        FROM feedback f
        JOIN students st ON f.student_id = st.id
        JOIN laboratories l ON f.lab_id = l.id
        WHERE 1=1
    '''
    params = []
    
    if lab_filter != 'all':
        query += ' AND f.lab_id = ?'
        params.append(lab_filter)
    
    if date_filter != 'all':
        query += ' AND DATE(f.date_submitted) = ?'
        params.append(date_filter)
    
    query += ' ORDER BY f.date_submitted DESC'
    
    feedbacks = conn.execute(query, params).fetchall()
    laboratories = conn.execute('SELECT * FROM laboratories').fetchall()
    
    conn.close()
    
    return render_template('feedback_reports.html', 
                          feedbacks=feedbacks,
                          laboratories=laboratories,
                          lab_filter=lab_filter,
                          date_filter=date_filter)

@app.route('/add-feedback', methods=['POST'])
@login_required
def add_feedback():
    student_id = request.form.get('student_id')
    lab_id = request.form.get('lab_id')
    message = request.form.get('message')
    
    conn = get_db_connection()
    
    # Check if student exists
    student = conn.execute('SELECT * FROM students WHERE id = ?', (student_id,)).fetchone()
    
    if not student:
        conn.close()
        flash('Student not found', 'error')
        return redirect(url_for('feedback_reports'))
    
    # Add feedback
    conn.execute('''
        INSERT INTO feedback (student_id, lab_id, message)
        VALUES (?, ?, ?)
    ''', (student_id, lab_id, message))
    
    conn.commit()
    conn.close()
    
    flash('Feedback successfully added', 'success')
    return redirect(url_for('feedback_reports'))

@app.route('/reservation', methods=['GET', 'POST'])
@login_required
def reservation():
    if request.method == 'POST':
        student_id = request.form.get('student_id')
        lab_id = request.form.get('lab_id')
        purpose = request.form.get('purpose')
        date = request.form.get('date')
        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')
        
        # Validate the data
        if not all([student_id, lab_id, purpose, date, start_time, end_time]):
            flash('All fields are required', 'error')
            return redirect(url_for('reservation'))
        
        # Check if the laboratory is available at the requested time
        conn = get_db_connection()
        
        # Check if student exists
        student = conn.execute('SELECT * FROM students WHERE id = ?', (student_id,)).fetchone()
        
        if not student:
            # Get student name from form
            student_name = request.form.get('student_name', 'Unknown')
            # Add student to database
            conn.execute('INSERT INTO students (id, name, program, year_level) VALUES (?, ?, ?, ?)',
                        (student_id, student_name, purpose.split(' ')[0], 1))
        
        # Add reservation
        conn.execute('''
            INSERT INTO reservations (student_id, lab_id, purpose, date, start_time, end_time, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (student_id, lab_id, purpose, date, start_time, end_time, 'pending'))
        
        conn.commit()
        
        # Get all reservations
        reservations = conn.execute('''
            SELECT r.id, r.student_id, st.name, r.lab_id, l.name as lab_name, 
                   r.purpose, r.date, r.start_time, r.end_time, r.status, r.date_created
            FROM reservations r
            JOIN students st ON r.student_id = st.id
            JOIN laboratories l ON r.lab_id = l.id
            ORDER BY r.date, r.start_time
        ''').fetchall()
        
        laboratories = conn.execute('SELECT * FROM laboratories').fetchall()
        
        conn.close()
        
        flash('Reservation successfully added', 'success')
        return render_template('reservation.html', reservations=reservations, laboratories=laboratories)
    
    # GET method - display form
    conn = get_db_connection()
    
    reservations = conn.execute('''
        SELECT r.id, r.student_id, st.name, r.lab_id, l.name as lab_name, 
               r.purpose, r.date, r.start_time, r.end_time, r.status, r.date_created
        FROM reservations r
        JOIN students st ON r.student_id = st.id
        JOIN laboratories l ON r.lab_id = l.id
        ORDER BY r.date, r.start_time
    ''').fetchall()
    
    laboratories = conn.execute('SELECT * FROM laboratories').fetchall()
    
    conn.close()
    
    return render_template('reservation.html', reservations=reservations, laboratories=laboratories)

@app.route('/update-reservation-status/<int:reservation_id>/<status>')
@login_required
@admin_required
def update_reservation_status(reservation_id, status):
    if status not in ['approved', 'rejected', 'completed']:
        flash('Invalid status', 'error')
        return redirect(url_for('reservation'))
    
    conn = get_db_connection()
    conn.execute('UPDATE reservations SET status = ? WHERE id = ?', (status, reservation_id))
    conn.commit()
    conn.close()
    
    flash(f'Reservation {status}', 'success')
    return redirect(url_for('reservation'))

@app.route('/add-announcement', methods=['POST'])
@login_required
@admin_required
def add_announcement():
    content = request.form.get('content')
    
    if not content:
        flash('Announcement content cannot be empty', 'error')
        return redirect(url_for('home'))
    
    conn = get_db_connection()
    
    # Add announcement
    current_date = datetime.datetime.now().strftime('%Y-%m-%d')
    conn.execute('''
        INSERT INTO announcements (content, posted_by, date_posted)
        VALUES (?, ?, ?)
    ''', (content, 'CCS Admin', current_date))
    
    conn.commit()
    conn.close()
    
    flash('Announcement successfully added', 'success')
    return redirect(url_for('home'))

@app.route('/edit-announcement/<int:announcement_id>', methods=['POST'])
@admin_required
def edit_announcement(announcement_id):
    content = request.form.get('content')
    
    if not content:
        flash('Announcement content cannot be empty', 'error')
        return redirect(url_for('home'))
    
    conn = get_db_connection()
    
    # Update announcement
    conn.execute('''
        UPDATE announcements 
        SET content = ?
        WHERE id = ?
    ''', (content, announcement_id))
    
    conn.commit()
    conn.close()
    
    flash('Announcement successfully updated', 'success')
    return redirect(url_for('home'))

@app.route('/delete-announcement/<int:announcement_id>')
@admin_required
def delete_announcement(announcement_id):
    conn = get_db_connection()
    
    # Delete announcement
    conn.execute('DELETE FROM announcements WHERE id = ?', (announcement_id,))
    
    conn.commit()
    conn.close()
    
    flash('Announcement successfully deleted', 'success')
    return redirect(url_for('home'))

# Main entry point
if __name__ == '__main__':
    # Initialize database
    init_db()
    
    # Run the app
    app.run(host='0.0.0.0', port=5000, debug=True)
