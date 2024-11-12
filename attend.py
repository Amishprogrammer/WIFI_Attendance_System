import subprocess
import mysql.connector
import datetime
import re
import time

# Connect to the MySQL database
db = mysql.connector.connect(
    host="127.0.0.1",
    user="root",      # Update with your MySQL username
    password="amish12",      # Update with your MySQL password
    database="attendance_system"
)

# Function to ping all devices in the subnet to populate ARP cache
def ping_sweep(router_ip):
    ip_base = router_ip.rsplit('.', 1)[0]  # Get the subnet, e.g., "192.168.29"
    print("Performing ping sweep...")

    for i in range(1, 255):  # Pinging all devices from x.x.x.1 to x.x.x.254
        ip = f"{ip_base}.{i}"
        subprocess.Popen(['ping', '-n', '1', '-w', '100', ip], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Give some time for ARP table to update
    time.sleep(5)

# Function to scan for connected devices on the network
def get_connected_devices(router_ip):
    ping_sweep(router_ip)  # Populate ARP cache before scanning
    
    try:
        devices = subprocess.check_output(['arp', '-a'], shell=True).decode('utf-8')
        print("ARP Output:\n", devices)  # Debugging: Output the ARP table

        mac_addresses = []

        # Regular expression to match MAC addresses
        mac_regex = r"([a-f0-9]{2}[:-]){5}[a-f0-9]{2}"

        # Iterate over each line of output from arp -a command
        for line in devices.splitlines():
            if router_ip.rsplit('.', 1)[0] in line:  # Only process lines from our subnet
                # Search for MAC addresses in the output
                mac_address = re.search(mac_regex, line)
                if mac_address:
                    mac_addresses.append(mac_address.group(0))

        return mac_addresses

    except subprocess.CalledProcessError as e:
        print("Error executing arp command:", e)
        return []

# Function to mark attendance based on detected MAC addresses
def mark_attendance(mac_addresses, subject):
    cursor = db.cursor()
    today = datetime.date.today()

    cursor.execute("SELECT id, mac_address FROM students")
    all_students = cursor.fetchall()  # Fetches all student records

    for student_id, student_mac in all_students:
        print(f"Checking student ID: {student_id} with MAC: {student_mac}")  # Debugging: Display student being checked
        
        # Check if the student's MAC address is in the list of detected MAC addresses
        if student_mac in mac_addresses:
            print(f"MAC address {student_mac} found in detected MAC addresses.")  # Debugging: Confirm MAC match
            
            # Insert attendance record for the student
            cursor.execute("INSERT INTO attendance (student_id, subject, date) VALUES (%s, %s, %s)",
                        (student_id, subject, today))
            db.commit()
            print(f"Attendance marked for student ID {student_id} (MAC: {student_mac})")
        else:
            print(f"MAC address {student_mac} not found in the detected MAC addresses.")  # Debugging: MAC not found


if __name__ == "__main__":
    router_ip = "192.168.29.1"  # Update with your router's IP address
    subject = input("Enter the subject name: ")

    print("Scanning for connected devices...")
    mac_addresses = get_connected_devices(router_ip)

    if mac_addresses:
        mark_attendance(mac_addresses, subject)
        print("Attendance marked successfully.")
    else:
        print("No connected devices found or failed to detect MAC addresses.")
