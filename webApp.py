from flask import Flask, render_template, request, redirect, url_for, session
import psycopg2
import psycopg2.extras
import hashlib, datetime
import os
import psycopg2
import psycopg2.extras
from flask import Flask, render_template, request, redirect, url_for, session
import hashlib, datetime

app = Flask(__name__)
app.secret_key = 'YOUR_SECRET_KEY_HERE'

def get_connection():
    """
    Connects to PostgreSQL using an environment variable called DATABASE_URL.
    If it's not set, default to a local DB (for local testing).
    """
    db_url = os.environ.get("DATABASE_URL", "dbname=library_project user=postgres password=postgres host=localhost port=5432")
    return psycopg2.connect(db_url)

@app.route('/')
def index():
    return render_template('index.html')

# ... (Other routes like /login, /register, /books, etc.) ...

if __name__ == '__main__':
    # For local testing:
    app.run(debug=True)

###################################
# 2) USER REGISTRATION
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
        cur.execute("""
            INSERT INTO users (username, password_hash, location, age)
            VALUES (%s, %s, %s, %s)
            """,
                    (username, password_hash, location, age)
                    )
        conn.commit()
        cur.close()
        conn.close()

        return redirect(url_for('login'))
    return render_template('register.html')


###################################
# 3) USER LOGIN
###################################
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        password_hash = hashlib.sha256(password.encode()).hexdigest()

        conn = get_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("""
            SELECT * FROM users
            WHERE username = %s AND password_hash = %s
            """, (username, password_hash))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user:
            session['user_id'] = user['user_id']
            session['username'] = user['username']
            return redirect(url_for('index'))
        else:
            return "Invalid credentials. Try again."
    return render_template('login.html')


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
    """Show all books in the library."""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    # Example: sort by title
    cur.execute("SELECT * FROM books ORDER BY book_title ASC")
    all_books = cur.fetchall()
    cur.close()
    conn.close()

    return render_template('books.html', books=all_books)


###################################
# 6) RENT A BOOK
###################################
@app.route('/rent/<string:isbn>', methods=['POST'])
def rent_book(isbn):
    """User rents a book for 14 days."""
    if 'user_id' not in session:
        return "Please login first."

    user_id = session['user_id']
    checkout_date = datetime.date.today()
    due_date = checkout_date + datetime.timedelta(days=14)
    rental_price = 10.00  # Example base price

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO rentals (user_id, isbn, checkout_date, due_date, rental_price)
        VALUES (%s, %s, %s, %s, %s)
    """, (user_id, isbn, checkout_date, due_date, rental_price))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('list_books'))


###################################
# 7) RETURN A BOOK
###################################
@app.route('/return/<int:rental_id>', methods=['POST'])
def return_book(rental_id):
    if 'user_id' not in session:
        return "Please login first."

    return_date = datetime.date.today()
    late_fee = 0.0

    conn = get_connection()
    cur = conn.cursor()

    # get due_date from rentals
    cur.execute("SELECT due_date FROM rentals WHERE rental_id = %s", (rental_id,))
    row = cur.fetchone()
    if not row:
        cur.close()
        conn.close()
        return "Rental not found."

    due_date = row[0]
    # Calculate late fee if returned after due_date
    if return_date > due_date:
        days_late = (return_date - due_date).days
        late_fee = days_late * 1.0  # $1/day late fee

    # update rentals
    cur.execute("""
        UPDATE rentals
        SET return_date = %s, late_fee = %s
        WHERE rental_id = %s
    """, (return_date, late_fee, rental_id))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('list_books'))


###################################
# 8) PROFILE PAGE (OPTIONAL)
###################################
@app.route('/profile')
def profile():
    """Example page that shows user info & their rentals."""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # Get basic user info
    cur.execute("SELECT username, location, age FROM users WHERE user_id = %s", (user_id,))
    user_data = cur.fetchone()

    # Get current rentals for this user
    cur.execute("""
        SELECT r.rental_id, b.book_title, r.checkout_date, r.due_date, r.return_date, r.late_fee
        FROM rentals r
        JOIN books b ON r.isbn = b.isbn
        WHERE r.user_id = %s
        ORDER BY r.checkout_date DESC
    """, (user_id,))
    rentals = cur.fetchall()

    cur.close()
    conn.close()

    return render_template('profile.html', user=user_data, rentals=rentals)


###################################
# RUN THE APP
###################################
if __name__ == '__main__':
    app.run(debug=True)
