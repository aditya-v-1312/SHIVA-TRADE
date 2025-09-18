from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
import psycopg2.extras
import os

# point template_folder to current directory and add static folder
app = Flask(__name__, template_folder='.', static_folder='static')

# The secret key is now read from an environment variable
app.secret_key = os.environ.get('SECRET_KEY')

# ===== Database connection =====
# The database URL is now read from an environment variable
DB_URL = os.environ.get('DATABASE_URL')

def get_db_connection():
    conn = psycopg2.connect(DB_URL)
    return conn

# ===== LOGIN =====
@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        cur.execute("SELECT * FROM users WHERE username=%s", (username,))
        user = cur.fetchone()

        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['user_id']
            session['username'] = user['username']
            session['role'] = user['role']
            session['modules'] = user['modules'].split(',') if user['modules'] else []
            cur.close()
            conn.close()
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'danger')
        
        cur.close()
        conn.close()
            
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

# ===== DASHBOARD =====
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html')

# ===== ADMIN PAGE =====
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if 'user_id' not in session or session['role'] != 'admin':
        flash('Access denied. You must be an admin to view this page.', 'danger')
        return redirect(url_for('dashboard'))

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        modules = ','.join(request.form.getlist('modules'))
        hashed_password = generate_password_hash(password)

        cur.execute("INSERT INTO users (username, password_hash, role, modules) VALUES (%s, %s, %s, %s)",
                    (username, hashed_password, role, modules))
        conn.commit()
        flash(f"User '{username}' created successfully!", 'success')
        return redirect(url_for('admin'))

    cur.execute("SELECT * FROM users")
    users = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('admin.html', users=users)

# ===== Dynamic Module Routes =====
def module_route(module_name, template_name):
    endpoint_name = f"{module_name}_view"

    @app.route(f'/{module_name}', endpoint=endpoint_name)
    def module_func():
        if 'user_id' not in session:
            return redirect(url_for('login'))
        if session['role'] != 'admin' and module_name not in session.get('modules', []):
            flash('You do not have access to this module.', 'danger')
            return redirect(url_for('dashboard'))
        return render_template(template_name)

    return module_func

# Create routes for each module
module_route('clients', 'clients.html')
module_route('quotations', 'quotations.html')
module_route('pis', 'pi.html')
module_route('pos', 'po.html')
module_route('material_receipts', 'receipts.html')
module_route('shipments', 'shipments.html')
module_route('documents', 'documents.html')

if __name__ == '__main__':
    app.run(debug=True)