from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
import psycopg2.extras
import os

app = Flask(__name__, template_folder='.', static_folder='static')
app.secret_key = os.environ.get('SECRET_KEY', 'dev_key_change_me')

DB_URL = "postgresql://neondb_owner:npg_v5UnzHmfSRj1@ep-falling-hat-aep2j8gp-pooler.c-2.us-east-2.aws.neon.tech/shiva?sslmode=require"

def get_db_connection():
    conn = psycopg2.connect(DB_URL)
    return conn

@app.route('/logo.png')
def logo():
    return send_from_directory('.', 'logo.png')

# ... (login, logout, dashboard routes remain the same) ...
@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    # Your existing login code here
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

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html')


@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if 'user_id' not in session or session['role'] != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        modules = ','.join(request.form.getlist('modules'))
        
        # Only hash password if a new one is provided
        if password:
            hashed_password = generate_password_hash(password)
            cur.execute("INSERT INTO users (username, password_hash, role, modules) VALUES (%s, %s, %s, %s)",
                        (username, hashed_password, role, modules))
        else: # Handle case where password is not provided on creation
            flash('Password is required for new users.', 'danger')
            return redirect(url_for('admin'))
            
        conn.commit()
        flash(f"User '{username}' created successfully!", 'success')
        return redirect(url_for('admin'))

    cur.execute("SELECT * FROM users ORDER BY user_id")
    users = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('admin.html', users=users)

# ===== NEW EDIT AND DELETE ROUTES =====

@app.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
def edit_user(user_id):
    if 'user_id' not in session or session['role'] != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        modules = ','.join(request.form.getlist('modules'))

        if password:
            hashed_password = generate_password_hash(password)
            cur.execute("UPDATE users SET username=%s, password_hash=%s, role=%s, modules=%s WHERE user_id=%s",
                        (username, hashed_password, role, modules, user_id))
        else: # If password field is blank, don't update it
            cur.execute("UPDATE users SET username=%s, role=%s, modules=%s WHERE user_id=%s",
                        (username, role, modules, user_id))
        
        conn.commit()
        cur.close()
        conn.close()
        flash('User updated successfully!', 'success')
        return redirect(url_for('admin'))

    # GET request: fetch user and display edit form
    cur.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
    user = cur.fetchone()
    cur.close()
    conn.close()
    return render_template('edit_user.html', user=user)

@app.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if 'user_id' not in session or session['role'] != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Prevent admin from deleting themselves
    if user_id == session['user_id']:
        flash("You cannot delete your own account.", 'danger')
        return redirect(url_for('admin'))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
    conn.commit()
    cur.close()
    conn.close()
    flash('User deleted successfully.', 'success')
    return redirect(url_for('admin'))


# ... (Dynamic Module Routes remain the same) ...
def module_route(module_name, template_name):
    # Your existing module_route code here
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

module_route('clients', 'clients.html')
module_route('quotations', 'quotations.html')
module_route('pis', 'pi.html')
module_route('pos', 'po.html')
module_route('material_receipts', 'receipts.html')
module_route('shipments', 'shipments.html')
module_route('documents', 'documents.html')


if __name__ == '__main__':
    app.run(debug=True)