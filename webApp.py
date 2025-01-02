from urllib.parse import quote
import os
import psycopg2
import psycopg2.extras
from flask import Flask, render_template, request, redirect, url_for, session, jsonify,flash
import hashlib
from urllib.parse import quote
from urllib.parse import quote
from flask import redirect

from urllib.parse import quote
app = Flask(__name__)
app.secret_key = 'YOUR_SECRET_KEY_HERE'






@app.route('/search_book/<string:book_title>')
def search_book(book_title):
    query = quote(book_title)
    return redirect(f"https://www.google.com/search?q={query}")



def get_connection():
    """Creates and returns a connection to the PostgreSQL database."""
    return psycopg2.connect(
        dbname="library_hm",
        user="mario_prisco00",
        password="gsaV0pReyfDAYbwoU9Jnfhkp7gH4lfks",
        host="dpg-ctp7okrtq21c73d2nk10-a.frankfurt-postgres.render.com",
        port="5432"
    )


###################################
# 1) HOME PAGE
###################################
@app.route('/')
def index():
    user_name = session.get('username', None)
    return render_template('index.html', user_name=user_name, page_class="home-page")


###################################
# 2) REGISTER
###################################
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        location = request.form['location']
        age = request.form['age'] or None

        # Hash the password for security
        password_hash = hashlib.sha256(password.encode()).hexdigest()

        conn = get_connection()
        cur = conn.cursor()

        # Check if the username already exists
        cur.execute("SELECT * FROM new_user WHERE username = %s", (username,))
        existing_user = cur.fetchone()

        if existing_user:
            cur.close()
            conn.close()
            return render_template('register.html',
                                   error="This username already exists. Please choose another.",
                                   page_class="register-page")

        cur.execute("""
            INSERT INTO new_user (username, password, location, age)
            VALUES (%s, %s, %s, %s)
        """, (username, password_hash, location, age))
        conn.commit()
        cur.close()
        conn.close()

        return redirect(url_for('login'))

    return render_template('register.html', page_class="register-page")


###################################
# 3) LOGIN
###################################
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        password_hash = hashlib.sha256(password.encode()).hexdigest()

        conn = get_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        # Check if the username exists
        cur.execute("SELECT * FROM new_user WHERE username = %s", (username,))
        user = cur.fetchone()

        if not user:
            cur.close()
            conn.close()
            return render_template('login.html',
                                   error="The user does not exist.",
                                   page_class="login-page")

        # Check if the password is correct
        if user['password'] != password_hash:
            cur.close()
            conn.close()
            return render_template('login.html',
                                   error="The password is not correct.",
                                   page_class="login-page")

        # Login successful
        session['user_id'] = user['readerid']
        session['username'] = user['username']
        cur.close()
        conn.close()
        return redirect(url_for('index'))

    return render_template('login.html', page_class="login-page")


###################################
# 4) LOGOUT
###################################
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


###################################
# 5) LIST BOOKS
###################################
@app.route('/books')
def list_books():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("SELECT * FROM book ORDER BY booktitle ASC")
    all_books = cur.fetchall()
    cur.close()
    conn.close()

    # Pass page_class for books page
    return render_template('books.html', books=all_books, page_class="books-page")


###################################
# 6) BOOK DETAIL PAGE
###################################

@app.route('/book/<string:book_title>')
def book_detail(book_title):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # Adjust column name if needed
    cur.execute("SELECT * FROM book WHERE booktitle = %s", (book_title,))
    book = cur.fetchone()

    cur.close()
    conn.close()

    if not book:
        return "Book not found."

    return render_template('book_detail.html', book=book, page_class="book-detail-page")


###################################
# 7) BOOKS BY SUBJECT
###################################
@app.route('/books/<string:subject>')
def books_by_subject(subject):
    """Display books filtered by subject."""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("SELECT * FROM book WHERE subject = %s ORDER BY booktitle ASC", (subject,))
    books = cur.fetchall()
    cur.close()
    conn.close()

    return render_template('books_by_subject.html', subject=subject, books=books, page_class="book-subject-page")


###################################
# 8) DATA FOR CHART (NEW ROUTE)
###################################
@app.route('/books_data')
def books_data():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cur.execute("""
        SELECT yearofpublication AS year, COUNT(*) AS count
        FROM book
        GROUP BY yearofpublication
        ORDER BY yearofpublication
    """)
    rows = cur.fetchall()

    cur.close()
    conn.close()

    data = []
    for row in rows:
        data.append({
            "year": row["year"],
            "count": row["count"]
        })

    return jsonify(data)


@app.route('/rate_book/<string:book_title>', methods=['POST'])
def rate_book(book_title):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    rating = request.form.get('rating')
    if rating is None:
        return "Rating not provided.", 400

    rating = int(rating)
    user_id = session['user_id']

    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # Look up ISBN (or whatever key you use)
    cur.execute("SELECT isbn FROM book WHERE booktitle = %s", (book_title,))
    row = cur.fetchone()
    if not row:
        cur.close()
        conn.close()
        return "Book not found in database."

    isbn = row['isbn']

    # Insert rating into new_rating
    cur.execute("""
        INSERT INTO new_rating (user_id, isbn, rating)
        VALUES (%s, %s, %s)
    """, (user_id, isbn, rating))
    conn.commit()

    cur.close()
    conn.close()

    # FLASH the thank you message:
    flash("Thank you for rating this book!")

    # Redirect back to the same book detail page
    return redirect(url_for('book_detail', book_title=book_title))

###################################
# RUN THE APP
###################################
if __name__ == '__main__':
    app.run(debug=True)
