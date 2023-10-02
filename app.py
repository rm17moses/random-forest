from flask import Flask, render_template, request, redirect, url_for, session, send_file, jsonify
import sqlite3
import pandas as pd
import pickle
from sklearn.preprocessing import LabelEncoder
import os
from werkzeug.utils import secure_filename
import json



app = Flask(__name__, template_folder='templates')
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = 'contamination'  # Replace with your own secret key

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'xls', 'xlsx'}
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/user_upload')
def user_upload():
    return render_template('upload.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'message': 'No file provided'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'message': 'No file selected'}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        # Process the uploaded file in chunks
        with open(file_path, 'wb') as f:
            while True:
                chunk = file.read(4096)  # Adjust the chunk size as needed
                if not chunk:
                    break
                f.write(chunk)

        # Process the uploaded file and get the result filename
        result_filename = process_excel_file(filename)

        # Provide the result filename in the response
        return jsonify({'result_filename': result_filename}), 200

    return jsonify({'message': 'Invalid file type'}), 400

@app.route('/download/<result_filename>')
def download_result(result_filename):
    return send_file(os.path.join(app.config['UPLOAD_FOLDER'], result_filename), as_attachment=True)

@app.route('/process/<filename>', methods=['GET', 'POST'])
def process_uploaded_file(filename):
    # Assuming you have a function to process the Excel data
    result = process_excel_file(filename)

    return render_template('result.html', result=result)

def process_excel_file(filename):
    # Assuming your function reads the Excel file and extracts the necessary data
    df = pd.read_excel(os.path.join(app.config['UPLOAD_FOLDER'], filename))

    # Drop rows with missing values
    df = df.dropna(subset=['Latitude', 'Longitude', 'Cd_value', 'Cr_value', 'Ni_value', 'Pb_value', 'Zn_value', 'Cu_value', 'Co_value'])

    # Assuming you have functions for data preprocessing and prediction
    results = []
    row_count = 0

    for index, row in df.iterrows():
        if row_count >= 100:
            break
        
        latitude = row['Latitude']
        longitude = row['Longitude']
        cd_value = row['Cd_value']
        cr_value = row['Cr_value']
        ni_value = row['Ni_value']
        pb_value = row['Pb_value']
        zn_value = row['Zn_value']
        cu_value = row['Cu_value']
        co_value = row['Co_value']

        # Create a numpy array with the user input values
        X_new = pd.DataFrame([[latitude, longitude, cd_value, cr_value, ni_value, pb_value, zn_value, cu_value, co_value]],
                             columns=['Latitude', 'Longitude', 'Cd_value', 'Cr_value', 'Ni_value', 'Pb_value', 'Zn_value', 'Cu_value', 'Co_value'])

        # Make a prediction
        y_pred_new = rf_model.predict(X_new)

        # Check if prediction is successful
        if y_pred_new is not None and len(y_pred_new) > 0:
            # Inverse transform the prediction to get the original label
            predicted_label = label_encoder.inverse_transform(y_pred_new)
            predicted_label = predicted_label[0]  # Get the first element of the array

            # Store the data in the results list
            results.append([latitude, longitude, cd_value, cr_value, ni_value, pb_value, zn_value, cu_value, co_value, predicted_label])

            # Store the data in the database
            conn = sqlite3.connect('prediction.db')
            c = conn.cursor()
            c.execute('''INSERT INTO user_data
                         (username, latitude, longitude, cd_value, cr_value, ni_value, pb_value, zn_value, cu_value, co_value, predicted_label)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                      (session['username'], latitude, longitude, cd_value, cr_value, ni_value, pb_value, zn_value, cu_value, co_value, predicted_label))
            conn.commit()
            conn.close()
            row_count += 1

    # Create a DataFrame from the results list
    result_df = pd.DataFrame(results, columns=['Latitude', 'Longitude', 'Cd_value', 'Cr_value', 'Ni_value', 'Pb_value', 'Zn_value', 'Cu_value', 'Co_value', 'Predicted_Contamination'])

    # Save the DataFrame to an Excel file
    result_filename = f"results_{filename}"
    result_df.to_excel(os.path.join(app.config['UPLOAD_FOLDER'], result_filename), index=False)

    return result_filename



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
    return count >= 150

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
        return render_template('error.html', message="You have reached the maximum limit of 150 entries.", show_clear_database_button=True)


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
