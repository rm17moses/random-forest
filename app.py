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
    return render_template('prediction.html')

@app.route('/predictor')
def go_back():
    if not check_logged_in():
        return redirect(url_for('login'))
    return render_template('prediction.html')

# Load the model using pickle
with open('rf_model.pkl', 'rb') as model_file:
    rf_model = pickle.load(model_file)

# Load the label encoder
with open('label_encoder.pkl', 'rb') as encoder_file:
    label_encoder = pickle.load(encoder_file)

@app.route('/predict', methods=['POST'])
def predict():
    if not check_logged_in():
        return redirect(url_for('login'))

    # ... (rest of the code remains the same)
    latitude = float(request.form['latitude'])
    longitude = float(request.form['longitude'])
    cd_value = float(request.form['cd_value'])
    cr_value = float(request.form['cr_value'])
    ni_value = float(request.form['ni_value'])
    pb_value = float(request.form['pb_value'])
    zn_value = float(request.form['zn_value'])
    cu_value = float(request.form['cu_value'])
    co_value = float(request.form['co_value'])

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

    return render_template('prediction_result.html', predicted_label=predicted_label[0], latitude=latitude, longitude=longitude)

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
