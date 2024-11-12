from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector

app = Flask(__name__)
app.secret_key = "121012"

db = mysql.connector.connect(
    host="127.0.0.1",
    user="root",      # Update with your MySQL username
    password="amish12",      # Update with your MySQL password
    database="attendance_system"
)

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Check credentials in the database
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s AND password = %s", (username, password))
        user = cursor.fetchone()

        if user:
            session['user_id'] = user['id']
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials, please try again.')

    return render_template('login.html')

# Route for dashboard page (only accessible if logged in)
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT students.name, attendance.subject, attendance.date 
        FROM attendance 
        JOIN students ON attendance.student_id = students.id
    """)
    records = cursor.fetchall()
    return render_template('dashboard.html', records=records)

# Route for adding new student
@app.route('/add_student', methods=['GET', 'POST'])
def add_student():
    if request.method == 'POST':
        name = request.form['name']
        mac_address = request.form['mac_address']
        cursor = db.cursor()
        cursor.execute("INSERT INTO students (name, mac_address) VALUES (%s, %s)", (name, mac_address))
        db.commit()
        return redirect(url_for('dashboard'))

    return render_template('add_student.html')

# Route for logout
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(debug=True)