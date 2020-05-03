import os
import math
from flask import Flask, session, render_template, request, flash, redirect, url_for, abort
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from helpers import pagination, login_required, good_reads
from werkzeug.security import check_password_hash, generate_password_hash


app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"

Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


@app.route("/")
def index():
    """Home page"""
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Log user in"""

    # make sure to clear session file first
    session.clear()

    if request.method == 'POST':
        username = request.form.get('username').lower()
        password = request.form.get('password')
        row = db.execute("SELECT * FROM users WHERE username =:username \
            AND password = :password", {'username': username, 'password': password}).fetchone()
        if row:
            # save user id to session
            session['user_id'] = row[0]
            return render_template('index.html')
        else:
            flash("Incorrect username or password", 'danger')
            return render_template('login.html')
    else:
        return render_template('login.html')


@app.route('/logout')
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to home page
    return redirect(url_for('index'))


@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username').lower()
        password = request.form.get('password')
        confirm_password = request.form.get('confirmation')

        # validate password input
        if password != confirm_password:
            flash(" Password and confirmation do not match. PLease Try Again", "warning")
            return render_template('register.html')
        else:
            # validate whether chosen username already exists
            try:
                db.execute("INSERT INTO users (username, password) VALUES \
                    (:username, :password)", {'username': username, 'password': generate_password_hash(password, method='pbkdf2:sha256', salt_length=8)})
            except:
                return render_template('register.html', error='This username is taken. Try something else.')
            db.commit()
            rows = db.execute("SELECT * FROM users WHERE username = :username", {'username': username}).fetchone()
            # log visitor in by saving id to session file
        session["user_id"] = rows[0]
        flash("You are registerd!", "success")
        return redirect('/')
    else:
        return render_template('register.html')


@app.route("/search", methods=['GET', 'POST'])
def search():
    """
    search books by title, author or isbn using partial or complete names and numbers then display 
    10 results per page.
    """
    q = request.args.get("query")
    s = "%" + q + "%"
    # default to first page
    page = request.args.get('page', 1, type=int)
    # get total result count
    total = db.execute("SELECT COUNT (*) FROM books WHERE title LIKE :s OR author LIKE :s OR\
             isbn LIKE :s", {'s': s}).fetchone()
    res = db.execute("SELECT * FROM books WHERE title LIKE :s \
          OR author LIKE :s OR isbn LIKE :s ORDER BY id ASC OFFSET ((:page -1) * 10)\
           ROWS FETCH NEXT 10 ROWS ONLY;", {'s': s, 'page': page}).fetchall()
    # calculate number of pages
    total_pages = math.ceil(total[0] / 10)
    page_list = pagination(page, total_pages)

    return render_template('search.html', res=res, q=q, total=total[0],
                           page_list=page_list, page=page)


@app.route("/book/<int:id>")
def book(id):
    """
    Display searched book and list reviews and ratings. 
    """
    page = request.args.get('page', 1, type=int)
    total = db.execute("SELECT COUNT (*) FROM reviews WHERE books_id = :id", {'id': id}).fetchone()
    res = db.execute("SELECT id, title, author, year, isbn FROM books WHERE id =:id", {'id': id}).fetchone()
    reviews = db.execute("SELECT users.username, books.title, reviews.content, reviews.date_posted \
        FROM users JOIN reviews ON users.id = reviews.user_id JOIN books ON books.id = reviews.books_id \
        WHERE books_id = :id ORDER BY date_posted DESC OFFSET ((:page -1) * 5)\
           ROWS FETCH NEXT 5 ROWS ONLY", {'id': id, 'page': page}).fetchall()
    # get average rating and total reviews from goodreads
    average_rating = good_reads(res.isbn)['average_rating']
    work_ratings_count = good_reads(res.isbn)['work_ratings_count']
    # get total pages
    total_pages = math.ceil(total[0] / 5)
    page_list = pagination(page, total_pages)

    return render_template('book.html', res=res, total=total[0],
                           page=page, reviews=reviews, id=id, page_list=page_list,
                           average_rating=average_rating, work_ratings_count=work_ratings_count)


@app.route("/review/new/<int:book_id>", methods=['GET', 'POST'])
@login_required
def new_review(book_id):
    """
    Logged in visitors can post one review per book.
    """
    id = session['user_id']
    rows = db.execute("SELECT * FROM reviews WHERE user_id = :id AND \
                books_id = :book_id", {'id': id, 'book_id': book_id}).fetchone()
    book_name = db.execute("SELECT title FROM books WHERE id = :id", {'id': book_id}).fetchone()
    if request.method == 'GET':
        # check if a post by visitor already exists for this book.
        if rows != None:
            return render_template('reviews_restricted.html', book_name=book_name[0])

    else:
        if request.method == 'POST':
            book_name = db.execute("SELECT title FROM books WHERE id = :id", {'id': book_id}).fetchone()
            content = request.form.get('content')
            rating = request.form.get('rating')
            db.execute("INSERT INTO reviews (content, rating, books_id, user_id) VALUES \
                        (:content, :rating, (SELECT id FROM books WHERE title = :book_name),\
                                                 (SELECT id FROM users WHERE id = :id))",
                       {'id': id, 'book_name': book_name[0], 'content': content, 'rating': rating})
            db.commit()
            flash("Your review has been posted!", "success")
            # redirect visitor to book page where the reviews has been posted
            return redirect(url_for('book', id=book_id))

    return render_template('create_review.html', book_name=book_name[0])


@app.route("/my_reviews")
@login_required
def my_reviews():
    """
    This allows the visitor to see all the reviews that he has posted.
    """
    id = session["user_id"]
    page = request.args.get('page', 1, type=int)
    total = db.execute("SELECT COUNT (*) FROM reviews WHERE user_id = :id", {'id': id}).fetchone()
    res = db.execute("SELECT users.username, books.id, books.title, reviews.content, \
        reviews.date_posted, reviews.rating FROM users JOIN reviews ON users.id = reviews.user_id\
        JOIN books ON books.id = reviews.books_id WHERE user_id = :id ORDER BY date_posted DESC OFFSET ((:page -1) * 5)\
           ROWS FETCH NEXT 5 ROWS ONLY", {'id': id, 'page': page}).fetchall()
    total_pages = math.ceil(total[0] / 5)
    page_list = pagination(page, total_pages)
    return render_template('my_reviews.html', res=res, total=total[0],
                           page=page, id=id, page_list=page_list)


@app.route("/api/<isbn>")
@login_required
def my_api(isbn):
    """
    A visit to "/api/<isbn>" returns a dict with title, author, year, isbn, total reviews and
    average rating for the book.
    """
    api_dict = {}

    res = db.execute("SELECT id, title, author, year, isbn FROM books \
        WHERE isbn = :isbn", {'isbn': isbn}).fetchone()
    # return page not found in case the isbn does not exist
    if res is None:
        return abort(404)
    review_count = db.execute("SELECT COUNT (*) FROM reviews WHERE \
        books_id = :books_id", {'books_id': res.id}).fetchone()
    average_score = db.execute("SELECT ROUND(AVG (rating),1) FROM reviews \
     WHERE books_id = :books_id", {'books_id': res.id}).fetchone()
    api_dict["title"] = res[1]
    api_dict["author"] = res[2]
    api_dict["year"] = res[3]
    api_dict["isbn"] = res[4]
    api_dict["review_count"] = review_count[0]

    # try for none value in case no average
    try:
        api_dict["average_score"] = float(average_score[0])
    except TypeError:
        api_dict["average_score"] = average_score[0]

    return api_dict


if __name__ == "__main__":
    app.run(debug=True)
