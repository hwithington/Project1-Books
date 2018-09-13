# import os

from flask import Flask, render_template, request, session, flash, redirect, url_for, jsonify
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from functools import wraps
import requests
# import json
from datetime import datetime
from config import DATABASE_URL,BOOK_READ_API_KEY,BOOK_API_KEY

app = Flask(__name__)


# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(DATABASE_URL)
db = scoped_session(sessionmaker(bind=engine))

def login_required(f):
    @wraps(f)
    def decorated_function(*args,**kwargs):
        if 'logged_in' not in session:
            flash("Please Login or Signup to view website")
            return redirect(url_for('login'))
        return f(*args,**kwargs)

    return decorated_function

@app.context_processor
def book_processor():
    def book_details(isbn):
        dec = requests.get("https://www.googleapis.com/books/v1/volumes", params={"q": isbn, "key": BOOK_API_KEY})
        return dec.json()
    return dict(book_details=book_details)

@app.route("/", methods=["GET","POST"])
@login_required
def homepage():
    username = session['user_name']
    return render_template("Homepage.html", username=username)

@app.route("/login",methods=['GET','POST'])
def login():
    error = ""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = db.execute("SELECT * FROM users WHERE username=:username and password=:password",
                          {"username": username, "password": password}).fetchone()

        if user is None or username!=user.username or password!=user.password:
            error = "Invalid Login"
            return render_template("login.html", error=error)
        elif username==user.username and password==user.password and user.active_status==False:
            error = "You are Subscribed but your accounts awaiting approval"
            return render_template("login.html", error=error)
        else:
            session['logged_in'] = True
            session['user_name'] = user.username
            session['user_id'] = user.id
            return redirect(url_for('homepage'))
    return render_template("Login.html", error=error)

@app.route("/logout")
@login_required
def logout():
    session.pop('logged_in')
    flash('You are logged out')
    return redirect(url_for('login'))

@app.route("/registration",methods=['GET','POST'])
def registration():
    error = ""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm = request.form['confirm']
        email = request.form['email']

        if username is None or username=="" or password is None or password=="" or email is None or email=="":
            print("error")
            error = "Please fill all the fields."
        elif password!=confirm:
            print("error")
            error = "Password did not match!"
        else:
            db.execute("INSERT INTO users (username,password,email,regdate,active_status) VALUES(:username,:password,:email,DEFAULT,FALSE)",
                       {"username": username,"password": password,"email": email})
            db.commit()
            flash("Successfully Registered")
            return redirect(url_for("login"))

    return render_template('Registration.html',error=error)

@app.route("/search",methods=['GET'])
@login_required
def search():
    username = session['user_name']
    val = request.args.get('search')
    if val:
        books = db.execute("SELECT * FROM books WHERE lower(isbn) LIKE lower(:isbn) or lower(title) LIKE lower(:title)",
                           {'isbn': "%" + val + "%", 'title': "%" + val + "%"})
    else:
        books = db.execute("SELECT * FROM public.books LIMIT 12")

    return render_template("Search.html", username=username, books=books)

@app.route("/reviews")
@login_required
def reviews():
    username = session['user_name']
    user_id = session['user_id']
    if request.method == 'GET':
        user_reviews = db.execute("SELECT * FROM reviews WHERE userid=:userid ORDER BY review_date desc",{"userid":user_id}).fetchall()
        return render_template("Reviews.html", username=username, reviews=user_reviews)

@app.route("/books/<string:isbn>", methods=['GET','POST'])
@login_required
def book(isbn):
    username = session['user_name']
    error = ""
    user_id = session['user_id']
    book = db.execute("SELECT * FROM books WHERE isbn=:isbn",{'isbn':isbn}).fetchone()
    book_id = book.id
    if request.method == 'GET':
        res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": BOOK_READ_API_KEY, "isbns": isbn})
        return render_template('Book.html', username=username, response=res.json(), book=book)
    else:
        review_text = request.form['review']
        rating = request.form['rating']
        try:
            review_exist = db.execute("SELECT * FROM reviews WHERE userid=:userid and bookid=:bookid",{"userid":user_id,"bookid":book_id}).fetchone()
            if review_exist:
                error = "You have already reviewed this book!"
            else:
                print("INSERTING REVIEW FOR BOOK ID : {}, USER_ID : {}, RATING : {}, REVIEW : {}, REVIEW_DATE : {}".format(book_id,user_id,rating,review_text,datetime.now().date()))
                db.execute("INSERT INTO reviews (userid,bookid,rating,review,review_date)VALUES(:user_id,:book_id,:rating,:review_text,:review_date)",{"user_id":user_id,"book_id":book_id,"rating":rating,"review_text":review_text,"review_date":datetime.now().date()})
                print("INSERTED")
                db.commit()
                flash("REVIEW COMMITTED!")
                return redirect(url_for('reviews'))
        except:
            error="INSERT ERROR"
        return render_template('Book.html', username=username, error=error, book=book)

@app.route("/api/<string:isbn>")
@login_required
def book_api(isbn):
    book_item = db.execute("SELECT * FROM books WHERE isbn=:isbn",{'isbn':isbn}).fetchone()
    book_id = book_item.id
    book_json = {}
    if book:
        book_json = {"title": book_item.title, "author": book_item.author, "year": book_item.year, "isbn": book_item.isbn}
        rev_count = dict(
            db.execute("SELECT COUNT(*) FROM Reviews WHERE bookid=:bookid",{"bookid":book_id}).fetchone())
        avg_score = dict(
            db.execute("SELECT AVG(rating) FROM reviews WHERE bookid=:bookid", {"bookid": book_id}).fetchone())
        book_json.update(review_count = rev_count['count'], average_score = avg_score['avg'])
        return jsonify(book_json)
    else:
        return render_template('404.html')

if __name__ == "__main__":
    app.run()