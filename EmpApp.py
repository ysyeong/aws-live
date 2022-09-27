from flask import Flask, render_template, request, redirect, session, flash
from pymysql import connections
import os
import boto3
from flask_session import Session
from config import *

app = Flask(__name__)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# For Flash #
app.secret_key = "secret" 

bucket = custombucket
region = customregion

db_conn = connections.Connection(
    host=customhost,
    port=3306,
    user=customuser,
    password=custompass,
    db=customdb

)
output = {}
table = 'employee'


@app.route("/", methods=['GET', 'POST'])
def home():
    # check if the users exist or not
    if not session.get("id"):
        # if not there in the session then redirect to the login page
        return redirect("/login")
    return render_template('index.html')

@app.route("/login", methods=['GET', 'POST'])
def login():
      # if form is submited
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        sql_query = "SELECT * FROM employee WHERE email ='" + email + "'"
        cursor = db_conn.cursor()
        try:
            cursor.execute(sql_query)
            row = cursor.fetchone()
            if row != None and row[4] == password:
                # record the user name
                session["id"] = row[1]
                session["name"] = row[2]
                # redirect to the main page
                return redirect("/")
            else:
                flash("Invalid email or password. Please try again.")
        except Exception as e:
            return str(e)
    return render_template('login.html')


@app.route("/about", methods=['POST'])
def about():
    return render_template('www.intellipaat.com')

@app.route("/certificate", methods=['GET','POST'])
def certificate():
    return render_template('certificate.html')


@app.route("/addemp", methods=['POST'])
def AddEmp():
    emp_id = request.form['emp_id']
    first_name = request.form['first_name']
    last_name = request.form['last_name']
    pri_skill = request.form['pri_skill']
    location = request.form['location']
    emp_image_file = request.files['emp_image_file']

    insert_sql = "INSERT INTO employee VALUES (%s, %s, %s, %s, %s)"
    cursor = db_conn.cursor()

    if emp_image_file.filename == "":
        return "Please select a file"

    try:

        cursor.execute(insert_sql, (emp_id, first_name, last_name, pri_skill, location))
        db_conn.commit()
        emp_name = "" + first_name + " " + last_name
        # Uplaod image file in S3 #
        emp_image_file_name_in_s3 = "emp-id-" + str(emp_id) + "_image_file"
        s3 = boto3.resource('s3')

        try:
            print("Data inserted in MySQL RDS... uploading image to S3...")
            s3.Bucket(custombucket).put_object(Key=emp_image_file_name_in_s3, Body=emp_image_file)
            bucket_location = boto3.client('s3').get_bucket_location(Bucket=custombucket)
            s3_location = (bucket_location['LocationConstraint'])

            if s3_location is None:
                s3_location = ''
            else:
                s3_location = '-' + s3_location

            object_url = "https://s3{0}.amazonaws.com/{1}/{2}".format(
                s3_location,
                custombucket,
                emp_image_file_name_in_s3)

        except Exception as e:
            return str(e)

    finally:
        cursor.close()

    print("all modification done...")
    return render_template('AddEmpOutput.html', name=emp_name)


@app.route("/logout")
def logout():
    session["id"] = None
    session["name"] = None
    return redirect("/")


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)
