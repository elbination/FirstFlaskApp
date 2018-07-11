from flask import Flask, render_template, flash, redirect, url_for, session, logging, request
# from data import Articles
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import pbkdf2_sha256
from functools import wraps
from jinja2 import Template

app = Flask(__name__)

# Config MySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '12345678'
app.config['MYSQL_DB'] = 'myFlaskApp'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

#init MYSQL
mysql = MySQL(app)

# Articles = Articles()

@app.route('/')
def index():
    return render_template('home.html')


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/articles')
def articles():
    # Create cursor
    cur = mysql.connection.cursor()

    # Get articles
    result = cur.execute("SELECT * FROM articles")

    articles = cur.fetchall()

    if result > 0:
        return render_template('articles.html', articles = articles)
    else:
        msg = 'No articles found'
        return render_template('articles.html', msg = msg)

    # Close connection
    cur.close()

# Single article
@app.route('/article/<string:id>')
def article(id):
    # Create cursor
    cur = mysql.connection.cursor()

    # Get article
    cur.execute("SELECT * FROM articles WHERE id = %s", [id])

    article = cur.fetchone()

    return render_template('article.html', article = article)

# Register Form Class
class RegisterForm(Form):
    name = StringField('Name', [validators.Length(min=4, max=50)])
    username = StringField('Username', [validators.Length(min=4, max=25)])
    email = StringField('Email', [validators.Length(min=4, max=50)])
    password = PasswordField('Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Passwords must match')
    ])
    confirm = PasswordField('Confirm Password')

# User register
@app.route('/register', methods = ['GET', 'POST'])
def register():
    form = RegisterForm(request.form)
    if session.get('logged_in'):
        return redirect(url_for('index'))
    else:
        if request.method == 'POST' and form.validate():
            name = form.name.data
            email = form.email.data
            username = form.username.data
            password = pbkdf2_sha256.hash(str(form.password.data))

            # Create cursor
            cur = mysql.connection.cursor()
            cur.execute("INSERT INTO users(name, email, username, password) VALUES(%s, %s, %s, %s)", (name, email, username, password))

            # Commit to DB
            mysql.connection.commit()

            # Close connection
            cur.close()

            flash("You are now registered and can log in", "success")

            return redirect(url_for('index'))

        return render_template('register.html', form = form)    

# User login
@app.route('/login', methods = ['GET', 'POST'])
def login():
    if session.get('logged_in'):
        return redirect(url_for('index'))
    else:
        if request.method == 'POST':
            username = request.form['username']
            password_candidate = request.form['password']

            # Create cursor
            cur = mysql.connection.cursor()

            # Get user by username
            result = cur.execute("SELECT * FROM users WHERE username = %s", [username])

            if result > 0:
                # Get stored hash
                data = cur.fetchone()
                password = data['password']

                # Compare password
                if pbkdf2_sha256.verify(password_candidate, password):
                    # Passed
                    session['logged_in'] = True
                    session['username'] = username

                    flash('You are now logged in', 'success')
                    return redirect(url_for('dashboard'))
                else:
                    error = "Invalid login"
                    return render_template('login.html', error = error)
                # Close connection
                cur.close()
            else:
                error = 'Username not found'
                return render_template('login.html', error = error)
            
        return render_template('login.html')

# Check if user logged in
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            # flash('Please log in', 'danger')
            return redirect(url_for('login'))
    return wrap

# Log out
@app.route('/logout')
def logout():
    if session.get('logged_in'):
        session.clear()
        flash('You are now logged out', 'success')
        return redirect(url_for('index'))
    else:
        return redirect(url_for('index'))

# Dashboard
@app.route('/dashboard')
@is_logged_in
def dashboard():
    # Create cursor
    cur = mysql.connection.cursor()

    # Get articles
    result = cur.execute("SELECT * FROM articles")

    articles = cur.fetchall()

    if result > 0:
        return render_template('dashboard.html', articles = articles)
    else:
        msg = 'No articles found'
        return render_template('dashboard.html', msg = msg)

    # Close connection
    cur.close()

# Article Form Class
class ArticleForm(Form):
    title = StringField('Title', [validators.Length(min=4, max=50)])
    body = TextAreaField('Body', [validators.Length(min=5)])

# Add article
@app.route('/add-article', methods = ['GET', 'POST'])
@is_logged_in
def add_article():
    form = ArticleForm(request.form)
    if request.method == 'POST' and form.validate():
        title = form.title.data
        body = form.body.data

        # Create cursor
        cur = mysql.connection.cursor()

        # Execute
        cur.execute("INSERT INTO articles(title, body, author) VALUES(%s, %s, %s)", (title, body, session['username']))

        # Commit
        mysql.connection.commit()

        # Close
        cur.close()

        flash('Article Created', 'success')
        return redirect(url_for('dashboard'))

    return render_template('add-article.html', form = form)

@app.route('/edit-article/<string:id>', methods = ['GET', 'POST'])
@is_logged_in
def edit_article(id):
    # Create cursor
    cur = mysql.connection.cursor()

    # Get article by id
    cur.execute("SELECT * FROM articles WHERE id = %s", [id])

    article = cur.fetchone()

    cur.close()

    # Get form
    form = ArticleForm(request.form)

    # Populate article from fields
    form.title.data = article['title']
    form.body.data = article['body']

    if request.method == 'POST' and form.validate():
        title = request.form['title']
        body = request.form['body']

        # Create cursor
        cur = mysql.connection.cursor()

        # Execute
        cur.execute("UPDATE articles SET title = %s, body = %s WHERE id = %s", (title, body, id))

        # Commit to db
        mysql.connection.commit()

        # Close connection
        cur.close()

        flash('Article Updated', 'success')

        return redirect(url_for('dashboard'))

    return render_template('edit-article.html', form = form)

@app.route('/delete-article/<string:id>', methods = ['POST'])
@is_logged_in
def delete_article(id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM articles WHERE id = %s", [id])
    mysql.connection.commit()
    cur.close()

    flash('Article Deleted', 'success')
    return redirect('dashboard')

if __name__ == '__main__':
    app.secret_key = 'secret123'
    app.run(debug=True)
