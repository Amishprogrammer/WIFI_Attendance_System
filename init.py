import subprocess


# Install necessary libraries
def install_libraries():
    try:
        import mysql.connector
        print("mysql-connector-python is already installed.")
    except ImportError:
        print("Installing mysql-connector-python library...")
        subprocess.check_call(['pip', 'install', 'mysql-connector-python'])
import mysql.connector
from mysql.connector import errorcode
# Function to connect to MySQL and create database and tables
def setup_database():
    try:
        # Connect to MySQL server
        db = mysql.connector.connect(
            host="127.0.0.1",
            user="root",      # Replace with your MySQL username
            password="password"  # Replace with your MySQL password
        )
        cursor = db.cursor()
        
        # Create the database if it doesn't exist
        cursor.execute("CREATE DATABASE IF NOT EXISTS attendance_system")
        print("Database 'attendance_system' is ready.")
        
        # Connect to the 'attendance_system' database
        db.database = "attendance_system"
        
        # Create 'students' table if it doesn't exist
        create_students_table = """
        CREATE TABLE IF NOT EXISTS students (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            mac_address VARCHAR(17) UNIQUE NOT NULL
        )
        """
        cursor.execute(create_students_table)
        print("Table 'students' is ready.")
        
        # Create 'attendance' table if it doesn't exist
        create_attendance_table = """
        CREATE TABLE IF NOT EXISTS attendance (
            id INT AUTO_INCREMENT PRIMARY KEY,
            student_id INT,
            subject VARCHAR(100),
            date DATE,
            FOREIGN KEY (student_id) REFERENCES students(id)
        )
        """
        cursor.execute(create_attendance_table)
        print("Table 'attendance' is ready.")

    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("Access denied: Check your username and password.")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            print("Database does not exist, and creation failed.")
        else:
            print(f"Error: {err}")
    finally:
        # Close the connection
        cursor.close()
        db.close()

# Run the installation and setup
if __name__ == "__main__":
    install_libraries()
    setup_database()
