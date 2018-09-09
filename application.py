import os

from flask import Flask, render_template, request, session, flash, redirect, url_for
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from functools import wraps

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

def login_required(f):
    @wraps(f)
    def decorated_function(*args,**kwargs):
        if 'logged_in' not in session:
            flash("You need to login first")
            return redirect(url_for('login'))
        return f(*args,**kwargs)

    return decorated_function

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
        user = db.execute("SELECT * FROM public.users WHERE username=:username and password=:password",
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
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        error = ""

        if username is None or password is None or email is None:
            print("error")
            error = "Please fill all the fields"
        else:
            db.execute("INSERT INTO public.users (username,password,email,regdate,active_status) VALUES(:username,:password,:email,DEFAULT,FALSE)",
                       {"username": username, "password": password, "email": email})
            db.commit()
            flash("Successfully Registered")
            return redirect(url_for("login"))

    return render_template("Registration.html")

@app.route("/search")
@login_required
def search():
    username = session['user_name']
    return render_template("Search.html",username=username)

@app.route("/result")
@login_required
def result():
    username = session['user_name']
    return render_template("Result.html",username=username)

@app.route("/book")
@login_required
def book():
    username = session['user_name']
    return render_template("Book.html",username=username)

@app.route("/reviews")
@login_required
def reviews():
    username = session['user_name']
    return render_template("Reviews.html",username=username)

if __name__ == "__main__":
    app.run()