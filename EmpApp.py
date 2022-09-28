from tkinter import E
from flask import Flask, render_template, request, redirect, session, flash
from pymysql import connections
import os
import boto3
from flask_session import Session
from datetime import datetime
from config import *

app = Flask(__name__)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# For Flash #
app.secret_key = "secret" 

s3 = boto3.resource('s3')
s3_client = boto3.client('s3')

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

def get_file_extension(filename):
    if '.' in filename:
        return filename.rsplit('.', 1)[1].lower()


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
            if row != None and row[3] == password:
                # record the user name
                session["id"] = row[0]
                session["name"] = row[1]
                cursor.close()
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
    sql_query = "SELECT * FROM certificate WHERE emp_id ='"+ session["id"] +"'"
    cursor = db_conn.cursor()
    try:
        cursor.execute(sql_query)
        records = list(cursor.fetchall())

        certificate = []
        for rows in records:
            certificate.append(list(rows))
        cursor.close()
        return render_template('certificate.html', certificate = certificate)
    except Exception as e:
        return str(e)

app.route("/viewcertificate", methods=['GET','POST'])
def viewcertificate():
    if request.method == "POST":
        certid = request.form['certId']
        sql_query = "SELECT * FROM certificate WHERE certificateID ='"+ certid +"'"
        cursor = db_conn.cursor()
        try:
            cursor.execute(sql_query)
            cert = list(cursor.fetchone())

            public_url = s3_client.generate_presigned_url('get_object', 
                                                                Params = {'Bucket': custombucket, 
                                                                            'Key': cert[4]})

            cert.append(public_url)
            cert.append("checked")

            cursor.close()

            return render_template('viewcertificate.html', cert = cert)
        except Exception as e:
            return str(e)

@app.route("/addcertificate", methods=['GET','POST'])
def addcertificate():
    if request.method == "POST":
        cName = request.form.get("certName")
        cDesc = request.form.get("certDesc")
        cDateTime =  str(datetime.now().strftime("%Y-%m-%d"))
        cFile = request.form["myCert"]

        if cFile.filename == "":
            return "Please select a image file"

        sql_query = "SELECT * FROM certificate"
        cursor = db_conn.cursor()
        try:
            cursor.execute(sql_query)
            records = cursor.fetchall()
            cID =  int(len(records)) + 1
            cursor.close()
        except Exception as e:
            return str(e)

        sql_query = "INSERT INTO certificate employee VALUES (%s, %s, %s, %s, %s, %s)"

        try:
            image_file_name_in_s3 = "cert/" + str(session["id"]) + "_image_file" + str(cID) + get_file_extension(cFile.filename)
            cursor.execute(sql_query, (cID, cName, cDesc, cDateTime, ))
            db_conn.commit()

            try:
                print("Data inserted in MySQL RDS... uploading image to S3...")
                s3.Bucket(custombucket).put_object(Key=image_file_name_in_s3, Body=cFile)
                bucket_location = boto3.client('s3').get_bucket_location(Bucket=custombucket)
                s3_location = (bucket_location['LocationConstraint'])

                if s3_location is None:
                    s3_location = ''
                else:
                    s3_location = '-' + s3_location

                object_url = "https://s3{0}.amazonaws.com/{1}/{2}".format(
                    s3_location,
                    custombucket,
                    image_file_name_in_s3)

                flash("Certificate added successfully!")

            except Exception as e:
                return str(e)

        except Exception as e:
            return str(e)

        finally:
            cursor.close()
            return redirect("/certificate.html")

    return render_template('addcertificate.html')

@app.route("/deletecertificate", method=['GET','POST'])
def deletecertificate():

    if request.method == "POST":
        cID = request.form['certId']
        sql_query = "SELECT * FROM certificate WHERE certificateID ='"+ cID+"'"
        cursor = db_conn.cursor()

        try:
            try:
                cursor.execute(sql_query)
                cert = list(cursor.fetchone())
                s3.Object(custombucket, cert[4]).delete()
            except Exception as e:
                return str(e)
            sql_query = "DELETE FROM certificate WHERE certificateID ='"+ cID+"'"
            cursor.execute(sql_query)
            db_conn.commit
            cursor.close()
            return render_template('certificate.html')
        except Exception as e:
            return str(e)
    else:
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
