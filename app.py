from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import io
import base64
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "secret123"


# ---------------- DATABASE CONNECTION ----------------
def get_db():
    conn = sqlite3.connect("app.db")
    conn.row_factory = sqlite3.Row
    return conn


# ---------------- INIT DATABASE ----------------
def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            amount INTEGER,
            category TEXT,
            date TEXT
        )
    """)

    conn.commit()
    conn.close()


def generate_base64_chart(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    buf.seek(0)
    image_base64 = base64.b64encode(buf.read()).decode("utf-8")
    plt.close(fig)
    return image_base64


def create_category_pie(category_data):
    labels = [row["category"] for row in category_data]
    sizes = [row["total"] for row in category_data]

    if not sizes:
        labels = ["No Data"]
        sizes = [1]

    fig, ax = plt.subplots(figsize=(4, 4), dpi=100)
    colors = plt.cm.Set3(range(len(labels)))
    wedges, texts, autotexts = ax.pie(
        sizes,
        labels=labels,
        autopct="%.0f%%",
        startangle=140,
        colors=colors,
        textprops={"color": "#334155", "fontsize": 8},
    )
    ax.axis("equal")
    return generate_base64_chart(fig)


def create_expense_activity(expenses):
    daily_totals = {}
    for expense in reversed(expenses):
        date = expense["date"]
        daily_totals[date] = daily_totals.get(date, 0) + expense["amount"]

    if not daily_totals:
        daily_totals = {"No Data": 0}

    dates = sorted(daily_totals.keys())
    values = [daily_totals[d] for d in dates]

    fig, ax = plt.subplots(figsize=(8, 4), dpi=100)
    ax.plot(dates, values, marker="o", color="#10b981", linewidth=2)
    ax.fill_between(dates, values, color="#a7f3d0", alpha=0.35)
    ax.set_title("Expense Activity", fontsize=12, color="#0f172a")
    ax.set_ylabel("Amount", color="#334155")
    ax.set_xlabel("Date", color="#334155")
    ax.grid(axis="y", color="#e2e8f0", linewidth=0.8)
    ax.set_xticks(dates)
    ax.set_xticklabels(dates, rotation=45, ha="right", fontsize=8)
    ax.tick_params(colors="#334155")
    for spine in ax.spines.values():
        spine.set_color("#cbd5e1")
    fig.tight_layout()
    return generate_base64_chart(fig)


# ---------------- LOGIN ----------------
@app.route("/", methods=["GET", "POST"])
def login():
    error = None

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE username=?", (username,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session["username"] = username
            return redirect(url_for("dashboard"))
        else:
            error = "Invalid Username or Password"

    return render_template("login.html", error=error)


# ---------------- REGISTER ----------------
@app.route("/register", methods=["GET", "POST"])
def register():
    error = None

    if request.method == "POST":
        username = request.form["username"]
        password = generate_password_hash(request.form["password"])

        try:
            conn = get_db()
            cursor = conn.cursor()

            cursor.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                (username, password)
            )

            conn.commit()
            conn.close()

            return redirect(url_for("login"))

        except sqlite3.IntegrityError:
            error = "Username already exists"

    return render_template("register.html", error=error)


# ---------------- DASHBOARD ----------------
@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    username = session.get("username")

    if not username:
        return redirect(url_for("login"))

    conn = get_db()
    cursor = conn.cursor()

    # -------- ADD EXPENSE --------
    if request.method == "POST":
        amount = request.form.get("amount")
        category = request.form.get("category")
        date = request.form.get("date")

        if not amount or not category or not date:
            return redirect(url_for("dashboard"))

        try:
            amount = int(amount)
        except ValueError:
            return redirect(url_for("dashboard"))

        cursor.execute("""
            INSERT INTO expenses (username, amount, category, date)
            VALUES (?, ?, ?, ?)
        """, (username, amount, category, date))

        conn.commit()

    # -------- FETCH EXPENSES --------
    cursor.execute("""
        SELECT id, amount, category, date
        FROM expenses
        WHERE username=?
        ORDER BY id DESC
    """, (username,))
    
    expenses = cursor.fetchall()

    # -------- TOTAL --------
    total = sum(exp["amount"] for exp in expenses)

    # -------- CATEGORY DATA --------
    cursor.execute("""
        SELECT category, SUM(amount) as total
        FROM expenses
        WHERE username=?
        GROUP BY category
    """, (username,))

    category_data = sorted(cursor.fetchall(), key=lambda row: row["total"], reverse=True)
    expense_count = len(expenses)
    top_category = category_data[0]["category"] if category_data else "—"
    top_category_value = category_data[0]["total"] if category_data else 0
    category_chart = create_category_pie(category_data)
    activity_chart = create_expense_activity(expenses)

    conn.close()

    return render_template(
        "dashboard.html",
        username=username,
        expenses=expenses,
        total=total,
        category_data=category_data,
        expense_count=expense_count,
        category_count=len(category_data),
        top_category=top_category,
        top_category_value=top_category_value,
        category_chart=category_chart,
        activity_chart=activity_chart,
    )


# ---------------- DELETE ----------------
@app.route("/delete/<int:id>")
def delete(id):
    username = session.get("username")

    if not username:
        return redirect(url_for("login"))

    conn = get_db()
    cursor = conn.cursor()

    # Ensure user deletes only their data
    cursor.execute(
        "DELETE FROM expenses WHERE id=? AND username=?",
        (id, username)
    )

    conn.commit()
    conn.close()

    return redirect(url_for("dashboard"))


# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------------- RUN ----------------
if __name__ == "__main__":
    init_db()
    app.run(debug=True)