from datetime import date

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from app.extensions import db


auth_bp = Blueprint('auth', __name__)

User = db.db.user
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        
        valid_credentials = User.find_one({"email": email})
        
        if valid_credentials:
            if password == valid_credentials["password"]:
                session['user'] = valid_credentials["username"]
                session['selected_date'] = str(date.today())
                flash('Logged in successfully', 'success')
                return redirect(url_for('tasks.view')) 
            else:
                flash('Invalid credentials', 'danger')
        else:
            flash('User not found. Please register first.', 'warning')
            return redirect(url_for('auth.register'))
            
    return render_template('login.html')

@auth_bp.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == "POST":
        reg_username = request.form['username']
        reg_email = request.form['email']
        reg_password = request.form['password']
        re_pas = request.form['confirm_password']

        if reg_password == re_pas:
            if User.find_one({"username": reg_username}):
                flash('Username already exists.', 'danger')
                return redirect(url_for('auth.login'))

            new_user = {
                'username': reg_username,
                'email': reg_email,
                'password': reg_password
            }
            User.insert_one(new_user)
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('auth.register'))

    return render_template('register.html')


@auth_bp.route('/logout')
def logout():
    session.pop('user', None)
    flash('Logged out.', 'info')
    return redirect(url_for('auth.login'))
