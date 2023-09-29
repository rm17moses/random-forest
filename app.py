from flask import Flask, render_template, request, redirect, url_for, session
# from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import sqlite3

import pandas as pd
import pickle
from sklearn.preprocessing import LabelEncoder

app = Flask(__name__, template_folder='templates')
app.secret_key = 'contamination'  # Replace with your own secret key

# Define a route for the login page
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        session['username'] = username
        return redirect(url_for('index'))
    return render_template('login.html')

def username_exists(username):
    conn = sqlite3.connect('prediction.db')
    c = conn.cursor()
    c.execute('SELECT * FROM user_data WHERE username=?', (username,))
    result = c.fetchone()
    conn.close()
    return result is not None

# Add a logout route
@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

# Add a check for logged in users
def check_logged_in():
    return 'username' in session

@app.route('/')
def index():
    if not check_logged_in():
        return redirect(url_for('login'))
    username = session.get('username')
    return render_template('index-homepage.html', name=username)

@app.route('/contact_us')
def contact_us():
    return render_template('index-contact-us.html')

@app.route('/about_us')
def about_us():
    return render_template('index-about-us.html')

@app.route('/soil_quality_standards')
def soil_quality_standards():
    return render_template('index-soil-quality-sta.html')

@app.route('/predictor')
def go_back():
    if not check_logged_in():
        return redirect(url_for('login'))
    return render_template('prediction.html')

@app.route('/map')
def map():
    return render_template('map.html')


# Load the model using pickle
with open('rf_model.pkl', 'rb') as model_file:
    rf_model = pickle.load(model_file)

# Load the label encoder
with open('label_encoder.pkl', 'rb') as encoder_file:
    label_encoder = pickle.load(encoder_file)

def has_exceeded_limit(username):
    conn = sqlite3.connect('prediction.db')
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM user_data WHERE username=?', (username,))
    count = c.fetchone()[0]
    conn.close()
    return count >= 10

@app.route('/predict', methods=['GET', 'POST'])
def predict():
    latitude = None
    longitude = None
    
    if request.method == 'POST':
        # Handle the POST request
        latitude = request.form.get('latitude')
        longitude = request.form.get('longitude')
        cd_value = request.form.get('cd_value')
        cr_value = request.form.get('cr_value')
        ni_value = request.form.get('ni_value')
        pb_value = request.form.get('pb_value')
        zn_value = request.form.get('zn_value')
        cu_value = request.form.get('cu_value')
        co_value = request.form.get('co_value')
        username = request.form.get('username')

        # Check if any of the input fields are empty
        if any(val is None or val == '' for val in [latitude, longitude, cd_value, cr_value, ni_value, pb_value, zn_value, cu_value, co_value]):
            return render_template('error.html', message="All fields are required.")

        # Convert values to float
        latitude = float(latitude)
        longitude = float(longitude)
        cd_value = float(cd_value)
        cr_value = float(cr_value)
        ni_value = float(ni_value)
        pb_value = float(pb_value)
        zn_value = float(zn_value)
        cu_value = float(cu_value)
        co_value = float(co_value)

        # Create a numpy array with the user input values
        X_new = pd.DataFrame([[latitude, longitude, cd_value, cr_value, ni_value, pb_value, zn_value, cu_value, co_value]],
                             columns=['Latitude', 'Longitude', 'Cd_value', 'Cr_value', 'Ni_value', 'Pb_value', 'Zn_value', 'Cu_value', 'Co_value'])

        # Make a prediction
        y_pred_new = rf_model.predict(X_new)

        # Inverse transform the prediction to get the original label
        predicted_label = label_encoder.inverse_transform(y_pred_new)

        conn = sqlite3.connect('prediction.db')
        c = conn.cursor()
        c.execute('''INSERT INTO user_data
                 (username, latitude, longitude, cd_value, cr_value, ni_value, pb_value, zn_value, cu_value, co_value, predicted_label)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (session['username'], latitude, longitude, cd_value, cr_value, ni_value, pb_value, zn_value, cu_value, co_value, predicted_label[0]))
        conn.commit()
        conn.close()

        return render_template('prediction_result.html', predicted_label=predicted_label[0], name=username, latitude=latitude, longitude=longitude)

    if has_exceeded_limit(session['username']):
        return render_template('error.html', message="You have reached the maximum limit of 10 entries.", show_clear_database_button=True)


        # Check for duplicate entry
    if username_exists(session['username'], latitude, longitude):
        return render_template('error.html', message="You have already submitted an entry with these coordinates.")

    else:
        # Handle the GET request
        if not check_logged_in():
            return redirect(url_for('login'))
        return render_template('prediction.html')
    
# Helper function to check for duplicate entry
def username_exists(username, latitude, longitude):
    conn = sqlite3.connect('prediction.db')
    c = conn.cursor()
    c.execute('SELECT * FROM user_data WHERE username=? AND latitude=? AND longitude=?', (username, latitude, longitude))
    result = c.fetchone()
    conn.close()
    return result is not None

@app.route('/user_data')
def user_data():
    if not check_logged_in():
        return redirect(url_for('login'))

    conn = sqlite3.connect('prediction.db')
    c = conn.cursor()
    c.execute('SELECT * FROM user_data WHERE username=?', (session['username'],))
    user_data = c.fetchall()
    conn.close()

    return render_template('user_data.html', user_data=user_data)

@app.route('/clear_database', methods=['GET', 'POST'])
def clear_database():
    if request.method == 'POST':
        # Clear the database for the current user
        conn = sqlite3.connect('prediction.db')
        c = conn.cursor()
        c.execute('DELETE FROM user_data WHERE username=?', (session['username'],))
        conn.commit()
        conn.close()
        
        return redirect(url_for('index'))
        
    return render_template('clear_database.html')


def init_db():
    conn = sqlite3.connect('prediction.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS user_data
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT,
                  latitude REAL,
                  longitude REAL,
                  cd_value REAL,
                  cr_value REAL,
                  ni_value REAL,
                  pb_value REAL,
                  zn_value REAL,
                  cu_value REAL,
                  co_value REAL,
                  predicted_label TEXT)''')
    conn.commit()
    conn.close()


if __name__ == '__main__':
    init_db()
    app.run(debug=True)
