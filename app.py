import datetime
import os
import sys
import ctypes
import subprocess
import time
import re
import webbrowser
from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
from threading import Timer

app = Flask(__name__)
app.secret_key = "121012"

# Database connection
db = mysql.connector.connect(
    host="127.0.0.1",
    user="root",  # Update with your MySQL username
    password="amish12",  # Update with your MySQL password
    database="attendance_system"
)

def is_admin():
    """Check if the script is running with administrative privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False

def run_as_admin():
    """Relaunch the script with administrator privileges."""
    if not is_admin():
        print("Script is not running as an administrator. Attempting to elevate...")
        try:
            ctypes.windll.shell32.ShellExecuteW(
                None,
                "runas",
                sys.executable,
                " ".join(sys.argv),
                None,
                1
            )
        except Exception as e:
            print(f"Failed to elevate privileges: {e}")
            sys.exit(1)
        sys.exit(0)

# Ensure script is running as admin
run_as_admin()

def open_browser():
    """Automatically open the Flask app in the default web browser."""
    webbrowser.open("http://127.0.0.1:5000")

# Function to ping devices in the subnet to populate ARP cache
def ping_sweep(router_ip):
    ip_base = router_ip.rsplit('.', 1)[0]
    print(f"Performing ping sweep on subnet {ip_base}.0...")
    for i in range(1, 255):
        ip = f"{ip_base}.{i}"
        subprocess.Popen(['ping', '-n', '1', '-w', '100', ip], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(5)

def get_connected_devices(router_ip):
    print("Flushing ARP cache...")
    try:
        subprocess.run(['arp', '-d', '*'], shell=True, check=True)
        print("ARP cache cleared.")
    except subprocess.CalledProcessError as e:
        print(f"Error clearing ARP cache: {e}")
        return []

    # Populate ARP cache
    ping_sweep(router_ip)

    try:
        # Get updated ARP table
        devices = subprocess.check_output(['arp', '-a'], shell=True).decode('utf-8')
        print("ARP Output after scanning:\n", devices)

        mac_addresses = []
        mac_regex = r"([a-f0-9]{2}[:-]){5}[a-f0-9]{2}"

        for line in devices.splitlines():
            if router_ip.rsplit('.', 1)[0] in line:
                mac_address = re.search(mac_regex, line)
                if mac_address:
                    mac_addresses.append(mac_address.group(0))

        print(f"Detected MAC addresses: {mac_addresses}")
        return mac_addresses
    except subprocess.CalledProcessError as e:
        print(f"Error executing ARP command: {e}")
        return []


# Function to mark attendance for each sweep
def mark_sweep_attendance(sweep_results, mac_addresses):
    for mac in mac_addresses:
        if mac in sweep_results:
            sweep_results[mac] += 1  # Increment the count if the MAC address was already detected
        else:
            sweep_results[mac] = 1  # Start counting if this is the first appearance

# Final attendance marking after all sweeps
def finalize_attendance(sweep_results, subject):
    cursor = db.cursor()
    today = datetime.date.today()

    # Get the list of students and their MAC addresses from the database
    cursor.execute("SELECT id, mac_address FROM students")
    students = cursor.fetchall()

    print(f"Finalizing attendance for subject '{subject}' on {today}...")
    for student_id, student_mac in students:
        # Check if the student was detected in at least 2 sweeps
        if sweep_results.get(student_mac, 0) >= 2:
            print(f"Student ID {student_id} (MAC: {student_mac}) was detected in {sweep_results[student_mac]} sweeps. Marking as present.")
            cursor.execute(
                "INSERT INTO attendance (student_id, subject, date) VALUES (%s, %s, %s)",
                (student_id, subject, today)
            )
            db.commit()
        else:
            print(f"Student ID {student_id} (MAC: {student_mac}) was detected in {sweep_results.get(student_mac, 0)} sweeps. Not marking as present.")

# Login route
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s AND password = %s", (username, password))
        user = cursor.fetchone()

        if user:
            session['user_id'] = user['id']
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials, please try again.')

    return render_template('login.html')

# Dashboard route
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

# Route to add students
@app.route('/add_student', methods=['GET', 'POST'])
def add_student():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form['name']
        mac_address = request.form['mac_address']
        cursor = db.cursor()
        cursor.execute("INSERT INTO students (name, mac_address) VALUES (%s, %s)", (name, mac_address))
        db.commit()
        flash("Student added successfully!")
        return redirect(url_for('dashboard'))

    return render_template('add_student.html')

# Route to trigger automated attendance
@app.route('/run_attendance', methods=['POST'])
def run_attendance():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    router_ip = "192.168.29.1"  # Update with your router's IP address
    subject = request.form.get('subject')  # Subject name provided in the form

    try:
        print("Starting attendance scans...")
        sweep_results = {}  # Dictionary to track the number of sweeps a device was detected

        # First scan
        print("First scan started...")
        mac_addresses = get_connected_devices(router_ip)
        print(f"Connected MAC addresses: {mac_addresses}")
        mark_sweep_attendance(sweep_results, mac_addresses)

        # Second scan after 30 minutes
        print("Waiting 30 minutes for second scan...")
        time.sleep(1800)  # Use 30 seconds for testing, adjust to 1800 seconds (30 minutes) as needed
        print("Second scan started...")
        mac_addresses = get_connected_devices(router_ip)
        print(f"Connected MAC addresses: {mac_addresses}")
        mark_sweep_attendance(sweep_results, mac_addresses)

        # Third scan at the end of the hour
        print("Waiting 30 seconds for third scan...")
        time.sleep(1740)  # Use 30 seconds for testing, adjust to 1740 seconds (29 minutes) as needed
        print("Third scan started...")
        mac_addresses = get_connected_devices(router_ip)
        print(f"Connected MAC addresses: {mac_addresses}")
        mark_sweep_attendance(sweep_results, mac_addresses)

        # Finalize attendance
        finalize_attendance(sweep_results, subject)
        flash("Attendance scans completed successfully!")
    except Exception as e:
        flash(f"Error during attendance: {e}")
        print(f"Error during attendance scans: {e}")

    return redirect(url_for('dashboard'))


# Logout route
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

if __name__ == "__main__":
    Timer(1, open_browser).start()
    app.run(debug=True)
    
sys.exit(0)