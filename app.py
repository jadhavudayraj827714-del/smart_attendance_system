from flask import Flask, request, redirect, url_for, session, jsonify
from flask import render_template_string
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from authlib.integrations.flask_client import OAuth
from pymongo import MongoClient
from bson import ObjectId

app = Flask(__name__)
app.secret_key = "secret123"

# ================= SQL DATABASE =================
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
db = SQLAlchemy(app)

# ================= MONGODB =================
mongo = MongoClient(
    "mongodb+srv://jadhavudaydada827714_db_user:oFGm9OY9Xj2jGleJ@cluster0.lgsejct.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0",
    serverSelectionTimeoutMS=5000
)
mdb = mongo["college"]
# ================= USER MODEL =================
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(200))
    role = db.Column(db.String(20))  # admin / teacher / cc / hod

with app.app_context():
    db.create_all()
# ================= OAUTH =================
oauth = OAuth(app)

google = oauth.register(
    name='google',
    client_id="YOUR_GOOGLE_CLIENT_ID",
    client_secret="YOUR_GOOGLE_CLIENT_SECRET",
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

# Apple (structure)
apple = oauth.register(
    name='apple',
    client_id="APPLE_CLIENT_ID",
    client_secret="APPLE_SECRET",
    access_token_url="https://appleid.apple.com/auth/token",
    authorize_url="https://appleid.apple.com/auth/authorize",
    client_kwargs={'scope': 'name email'}
)

# ================= HTML =================
html = """
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Attendance System</title>
<style>
body{font-family:sans-serif;background:#f2f2f2;padding:20px;}
.box{background:white;padding:20px;border-radius:10px;max-width:500px;margin:auto;}
input,select,button{width:100%;padding:10px;margin:5px 0;}
button{background:blue;color:white;}
table{width:100%;margin-top:20px;}
</style>
</head>
<body>

<div class="box">
<h2>Login / Signup</h2>

<form method="post" action="/login">
<input name="email" placeholder="Email" required>
<input name="password" type="password" required>
<button>Login</button>
</form>

<a href="/login/google"><button style="background:red;">Login with Google</button></a>
<a href="/login/apple"><button style="background:black;">Login with Apple</button></a>

<hr>

<form method="post" action="/signup">
<input name="name" placeholder="Name" required>
<input name="email" required>
<input name="password" type="password" required>
<select name="role">
<option value="teacher">Teacher</option>
<option value="cc">CC</option>
<option value="hod">HOD</option>
<option value="admin">Admin</option>
</select>
<button>Signup</button>
</form>
</div>

</body>
</html>
"""

# ================= ROUTES =================

@app.route("/")
def home():
    return render_template_string(html)

# LOGIN
@app.route("/login", methods=["POST"])
def login():
    user = User.query.filter_by(email=request.form["email"]).first()
    if user and check_password_hash(user.password, request.form["password"]):
        session["user"] = user.email
        session["role"] = user.role
        return redirect("/dashboard")
    return "Login Failed"

# SIGNUP
@app.route("/signup", methods=["POST"])
def signup():
    user = User(
        name=request.form["name"],
        email=request.form["email"],
        password=generate_password_hash(request.form["password"]),
        role=request.form["role"]
    )
    db.session.add(user)
    db.session.commit()
    return redirect("/")

# GOOGLE LOGIN
@app.route("/login/google")
def google_login():
    return google.authorize_redirect(url_for("google_callback", _external=True))

@app.route("/auth/google/callback")
def google_callback():
    token = google.authorize_access_token()
    user_info = google.get("userinfo").json()

    email = user_info["email"]
    name = user_info["name"]

    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(name=name, email=email, password="", role="teacher")
        db.session.add(user)
        db.session.commit()

    session["user"] = email
    session["role"] = user.role
    return redirect("/dashboard")

# ================= DASHBOARD =================

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/")

    role = session["role"]

    students = list(mdb.students.find())
    rows = ""

    for s in students:
        rows += f"""
        <tr>
        <td>{s.get('roll')}</td>
        <td>{s.get('name')}</td>
        <td>
        <a href='/present/{s['_id']}'>P</a>
        <a href='/absent/{s['_id']}'>A</a>
        </td>
        <td>{s.get('status','-')}</td>
        """

        if role in ["admin","cc","hod"]:
            rows += f"<td><a href='/delete/{s['_id']}'>Delete</a></td>"

        rows += "</tr>"

    add_form = ""
    if role in ["admin","cc","hod"]:
        add_form = """
        <form method='post' action='/add'>
        <input name='roll' placeholder='Roll'>
        <input name='name' placeholder='Name'>
        <button>Add Student</button>
        </form>
        """

    return f"""
    <h2>{role.upper()} DASHBOARD</h2>
    <a href='/logout'>Logout</a>

    {add_form}

    <table border=1>
    <tr>
    <th>Roll</th>
    <th>Name</th>
    <th>Action</th>
    <th>Status</th>
    <th>Delete</th>
    </tr>
    {rows}
    </table>
    """

# ================= ADD STUDENT =================

@app.route("/add", methods=["POST"])
def add():
    if session["role"] not in ["admin","cc","hod"]:
        return "No Access"

    mdb.students.insert_one({
        "roll": request.form["roll"],
        "name": request.form["name"],
        "status": "-"
    })
    return redirect("/dashboard")

# ================= DELETE =================

@app.route("/delete/<id>")
def delete(id):
    if session["role"] not in ["admin","cc","hod"]:
        return "No Access"

    mdb.students.delete_one({"_id": ObjectId(id)})
    return redirect("/dashboard")

# ================= ATTENDANCE =================

@app.route("/present/<id>")
def present(id):
    mdb.students.update_one({"_id": ObjectId(id)}, {"$set":{"status":"Present"}})
    return redirect("/dashboard")

@app.route("/absent/<id>")
def absent(id):
    mdb.students.update_one({"_id": ObjectId(id)}, {"$set":{"status":"Absent"}})
    return redirect("/dashboard")

# ================= LOGOUT =================

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ================= RUN =================

if __name__ == "__main__":
    app.run(debug=True)