# Import necessary modules
import pyrebase
from flask import Flask, flash, redirect, render_template, request, session, abort, url_for
from datetime import datetime
import re
from flask import Flask, render_template, Response,session
from flask_wtf import FlaskForm
from wtforms import FileField, SubmitField
from werkzeug.utils import secure_filename
from wtforms.validators import InputRequired
import os
import cv2
import math
import pyttsx3
import requests
from ultralytics import YOLO
import json
# from video import video_detection

# Create a new Flask application
app = Flask(__name__)

app.config['SECRET_KEY'] = 'vaishnavi12'
app.config['UPLOAD_FOLDER'] = 'static/files'

# Configuration for Firebase
config = {
    "apiKey": "AIzaSyApyIAgQjD9kePHjkpGWl07rJLM6c1pgNE",
    "authDomain": "auth-prj-17a88.firebaseapp.com",
    "projectId": "auth-prj-17a88",
    "storageBucket": "auth-prj-17a88.appspot.com",
    "messagingSenderId": "737962126459",
    "appId": "1:737962126459:web:5934c6405e87377c4f06de",
    "databaseURL": "https://auth-prj-17a88-default-rtdb.firebaseio.com"
}

# Initialize Firebase
firebase = pyrebase.initialize_app(config)

# Get reference to the auth service and database service
auth = firebase.auth()
db = firebase.database()
# Route for the login page

#for vedio passing
def generate_frames(path_x = ''):
    yolo_output = video_detection(path_x)
    for detection_ in yolo_output:
        ref,buffer=cv2.imencode('.jpg',detection_)
        if ref:
            frame=buffer.tobytes()
            yield (b'--frame\r\n'b'Content-Type: image/jpeg\r\n\r\n' + frame +b'\r\n')
        else:
            print("no valid input")

class UploadFileForm(FlaskForm):
    file = FileField("File",validators=[InputRequired()])
    submit = SubmitField("Run")

def generate_frames_web(path_x):
    yolo_output = video_detection(path_x)
    for detection in yolo_output:
        ref,buffer=cv2.imencode('.jpg',detection)
        if ref:
            frame=buffer.tobytes()
            yield (b'--frame\r\n'b'Content-Type: image/jpeg\r\n\r\n' + frame +b'\r\n')
        else:
            print("no valid input")

@app.route("/")
def login():
    return render_template("login.html")

# Route for the signup page
@app.route("/signup")
def signup():
    return render_template("signup.html")

# Route for the welcome page
@app.route("/welcome")
def welcome():
    # Check if user is logged in
    if session.get("is_logged_in", False):
        return render_template("indexproject.html", email=session["email"], name=session["name"])
    else:
        # If user is not logged in, redirect to login page
        return redirect(url_for('login'))

# Function to check password strength
def check_password_strength(password):
    # At least one lower case letter, one upper case letter, one digit, one special character, and at least 8 characters long
    return re.match(r'^(?=.*\d)(?=.*[!@#$%^&*])(?=.*[a-z])(?=.*[A-Z]).{8,}$', password) is not None

# Route for login result
@app.route("/result", methods=["POST", "GET"])
def result():
    if request.method == "POST":
        result = request.form
        email = result["email"]
        password = result["pass"]
        try:
            # Authenticate user
            user = auth.sign_in_with_email_and_password(email, password)
            session["is_logged_in"] = True
            session["email"] = user["email"]
            session["uid"] = user["localId"]
            # Fetch user data
            data = db.child("users").get().val()
            # Update session data
            if data and session["uid"] in data:
                session["name"] = data[session["uid"]]["name"]
                # Update last login time
                db.child("users").child(session["uid"]).update({"last_logged_in": datetime.now().strftime("%m/%d/%Y, %H:%M:%S")})
            else:
                session["name"] = "User"
            # Redirect to welcome page
            return redirect(url_for('indexproject'))
        except Exception as e:
            print("Error occurred: ", e)
            return redirect(url_for('login'))
    else:
        # If user is logged in, redirect to welcome page
        if session.get("is_logged_in", False):
            return redirect(url_for('indexproject'))
        else:
            return redirect(url_for('login'))

# Route for user registration
@app.route("/register", methods=["POST", "GET"])
def register():
    if request.method == "POST":
        result = request.form
        email = result["email"]
        password = result["pass"]
        name = result["name"]
        if not check_password_strength(password):
            print("Password does not meet strength requirements")
            return redirect(url_for('signup'))
        try:
            # Create user account
            auth.create_user_with_email_and_password(email, password)
            # Authenticate user
            user = auth.sign_in_with_email_and_password(email, password)
            session["is_logged_in"] = True
            session["email"] = user["email"]
            session["uid"] = user["localId"]
            session["name"] = name
            # Save user data
            data = {"name": name, "email": email, "last_logged_in": datetime.now().strftime("%m/%d/%Y, %H:%M:%S")}
            db.child("users").child(session["uid"]).set(data)
            return redirect(url_for('welcome'))
        except Exception as e:
            print("Error occurred during registration: ", e)
            return redirect(url_for('signup'))
    else:
        # If user is logged in, redirect to welcome page
        if session.get("is_logged_in", False):
            return redirect(url_for('welcome'))
        else:
            return redirect(url_for('signup'))

# Route for password reset
@app.route("/reset_password", methods=["GET", "POST"])
def reset_password():
    if request.method == "POST":
        email = request.form["email"]
        try:
            # Send password reset email
            auth.send_password_reset_email(email)
            return render_template("reset_password_done.html")  # Show a page telling user to check their email
        except Exception as e:
            print("Error occurred: ", e)
            return render_template("reset_password.html", error="An error occurred. Please try again.")  # Show error on reset password page
    else:
        return render_template("reset_password.html")  # Show the password reset page

# Route for logout
@app.route("/logout")
def logout():
    # Update last logout time
    db.child("users").child(session["uid"]).update({"last_logged_out": datetime.now().strftime("%m/%d/%Y, %H:%M:%S")})
    session["is_logged_in"] = False

    directory = app.config["UPLOAD_FOLDER"]
    delete_files_in_directory(directory)

    session.clear()

    return redirect(url_for('login'))


@app.route("/home")
def home():
    # return render_template("index.html")
    return redirect(url_for('indexproject'))

def delete_files_in_directory(directory):
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
                print(f"File '{filename}' deleted successfully.")
        except Exception as e:
            print(f"Error deleting file '{filename}': {e}")
#new added
@app.route('/indexproject')
def indexproject():
    # session.clear()
    # Check if user is logged in
    if session.get("is_logged_in", False):
        return render_template("indexproject.html", email=session["email"], name=session["name"])
    else:
        # If user is not logged in, redirect to login page
        return redirect(url_for('login'))
    # return render_template('indexproject.html')

# @app.route("/webcam", methods=['GET','POST'])
# def webcam():
#     session.clear()
#     return render_template('ui.html')

# @app.route('/FrontPage', methods=['GET','POST'])
# def front():
#     # Upload File Form: Create an instance for the Upload File Form
#     form = UploadFileForm()
#     if form.validate_on_submit():
#         # Our uploaded video file path is saved here
#         file = form.file.data
#         file.save(os.path.join(os.path.abspath(os.path.dirname(__file__)), app.config['UPLOAD_FOLDER'],
#                                secure_filename(file.filename)))
#         session['video_path'] = os.path.join(os.path.abspath(os.path.dirname(__file__)), app.config['UPLOAD_FOLDER'],
#                                              secure_filename(file.filename))
#
#     return render_template('videoprojectnew.html', form=form)

@app.route('/FrontPage', methods=['GET','POST'])
def front():
    # Check if user is logged in
    if session.get("is_logged_in", False):
        # Upload File Form: Create an instance for the Upload File Form
        form = UploadFileForm()
        if form.validate_on_submit():
            # Our uploaded video file path is saved here
            file = form.file.data
            file.save(os.path.join(os.path.abspath(os.path.dirname(__file__)), app.config['UPLOAD_FOLDER'],
                                   secure_filename(file.filename)))
            session['video_path'] = os.path.join(os.path.abspath(os.path.dirname(__file__)), app.config['UPLOAD_FOLDER'],
                                                 secure_filename(file.filename))
            print("welcome")

        return render_template('videoprojectnew.html', form=form, email=session.get('email', None), name=session.get('name', None))
    else:
        # If user is not logged in, redirect to login page
        return redirect(url_for('login'))

@app.route('/video',methods=['GET','POST'])
def video1():
    # user_data = db.child("users").child(auth.current_user["localId"]).get().val()
    # print(user_data)
    return Response(generate_frames(path_x = session.get('video_path', None)),mimetype='multipart/x-mixed-replace; boundary=frame')

# # To display the Output Video on Webcam page
# @app.route('/webapp')
# def webapp():
#     return Response(generate_frames_web(path_x=0), mimetype='multipart/x-mixed-replace; boundary=frame')
#

def video_detection(path_x):
    video_capture = path_x
    cap=cv2.VideoCapture(video_capture)
    text_speech = pyttsx3.init()

    model=YOLO("/home/vaishnavi/Flask-Firebase-Authentication/app/best.pt")

    # classNames = ["Pothole"]
    classNames = ["No Parking","Pothole","Speed Limit","Speed breaker ahead","crosswalk","pothole","speed-breaker","speed-breakers","stop","trafficlight","turn left","turn right"]
    alert_triggered = False

    while True:
        success, img = cap.read()
        # Doing detections using YOLOv8 frame by frame
        results=model(img,stream=True)

        for r in results:
            # boxes: ultralytics.engine.results.Boxes object
            boxes=r.boxes
            for box in boxes:
                #print(box)
                x1,y1,x2,y2=box.xyxy[0]
                # print(x1, y1, x2, y2)
                x1,y1,x2,y2=int(x1), int(y1), int(x2), int(y2)
                print(x1,y1,x2,y2)
                cv2.rectangle(img, (x1,y1), (x2,y2), (255,0,255),3)
                print(box.conf[0])
                conf=math.ceil((box.conf[0]*100))/100
                print(conf*100)
                cls = int(box.cls[0])
                class_name = classNames[cls]
                if class_name in classNames and not alert_triggered:
                    text_speech.say(f'{class_name} Ahead')
                    text_speech.runAndWait()
                    text_speech.setProperty('rate', 100)
                    alert_triggered = True

                label = f'{class_name}{conf}'
                t_size = cv2.getTextSize(label, 0, fontScale=1, thickness=1)[0]
                # print(t_size)
                # print('c2 :- ',x1+t_size[0])
                cv2.rectangle(img, (x1, y1), (x2, y2), [255, 0, 255], 0, cv2.LINE_AA)
                cv2.putText(img, label, (x1, y1 - 2), 0, 1, [255, 255, 255], thickness=1, lineType=cv2.LINE_AA)
                # if session["is_logged_in"] == True:
                #     print("ccccccccccccccccccccccccccccccccccccccccccccccccc")
                if class_name == 'Pothole':
                    # response = requests.get(
                    #     "https://ipgeolocation.abstractapi.com/v1/?api_key=576b4db174af4940ad60c65b99ff499f&ip_address=103.17.156.250")
                    # print(response.status_code)
                    # print(response.content)
                    # json_data = response.content
                    # data = json.loads(json_data.decode('utf-8'))
                    # longitude = data['longitude']
                    # latitude = data['latitude']
                    city = "Pune"
                    # country = data['country']
                    pothole_location = db.child("users").child(auth.current_user["localId"]).child("detection").child(datetime.now().strftime("%B/%d/%Y, %H:%M:%S"))
                    pothole_location.push({
                        "longitude" : 18.584366,
                        "latitude":73.736458,
                        "city": city,
                        # "country": country,
                        "servirity": conf,
                    })

        yield img

cv2.destroyAllWindows()


if __name__ == "__main__":
    app.run(debug=True)
