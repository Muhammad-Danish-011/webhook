from flask import Flask, jsonify, request
from datetime import datetime
import csv
import pandas as pd
from flask_sqlalchemy import SQLAlchemy
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib


app = Flask(__name__)
CSV_FILE = 'Ad_Tracking_Data.csv'

# Your email configuration
smtp_server = 'smtp.gmail.com'  # Replace with your SMTP server address
smtp_port = 587  # Replace with your SMTP port
sender_email = 'aqsat1506@gmail.com'  # Replace with your email
sender_password = 'wykx edvn sgkl atfj'  # Replace with your email password
receiver_email = 'tauheedaqsa1@gmail.com'  # Replace with recipient's email

# Configure Flask to use PostgreSQL database
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:123@localhost/Ad_Expiration_managment '
db = SQLAlchemy(app)

# Define the database model
class AdTracking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ad_title = db.Column(db.String(255))
    start_date = db.Column(db.DateTime)
    expiration_date = db.Column(db.DateTime)

# Load Ad Tracking Data from the database
def load_Ad_Tracking_Data():
    Ad_Tracking_Data = {}
    ads = AdTracking.query.all()
    for ad in ads:
        Ad_Tracking_Data[ad.id] = {
            'Ad-Title': ad.ad_title,
            'Start_Date': ad.start_date,
            'Expiration_Date': ad.expiration_date
        }
    return Ad_Tracking_Data

# Save Ad Tracking Data to the database
def save_Ad_Tracking_Data(Ad_Tracking_Data):
    for ID, ad_data in Ad_Tracking_Data.items():
        ad = AdTracking.query.get(ID) or AdTracking()
        ad.id = ID
        ad.ad_title = ad_data.get('Ad-Title', '')
        ad.start_date = ad_data['Start_Date']
        ad.expiration_date = ad_data['Expiration_Date']
        db.session.add(ad)
    db.session.commit()

# Function to send email
def send_email(subject, message):
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = subject
    msg.attach(MIMEText(message, 'plain'))

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, receiver_email, msg.as_string())





def load_Ad_Tracking_Data():
    Ad_Tracking_Data = {}
    with open(CSV_FILE, mode='r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            start_date = datetime.strptime(row['Start_Date'], '%Y-%m-%d')
            expiration_date = datetime.strptime(row['Expiration_Date'], '%Y-%m-%d')
            Ad_Tracking_Data[int(row['ID'])] = {
                'Ad-Title': row.get('Ad-Title', ''),  # Use get to handle missing 'Ad-Title'
                'Start_Date': start_date,
                'Expiration_Date': expiration_date
            }
    
    return Ad_Tracking_Data

d = load_Ad_Tracking_Data()
print(d)

def save_Ad_Tracking_Data(Ad_Tracking_Data):
    with open(CSV_FILE, mode='w', newline='') as file:
        fieldnames = ['ID', 'Ad-Title', 'Start_Date', 'Expiration_Date']
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for ID, ad_data in Ad_Tracking_Data.items():
            writer.writerow({
                'ID': ID,
                'Ad-Title': ad_data.get('Ad-Title', ''),  # Assuming 'Ad-Title' is a key in ad_data
                'Start_Date': ad_data['Start_Date'].strftime('%Y-%m-%d'),
                'Expiration_Date': ad_data['Expiration_Date'].strftime('%Y-%m-%d')
            })


s = save_Ad_Tracking_Data(d)
print(s)

@app.route('/webhook', methods=['GET','POST'])
def webhook_handler():
    webhook_data = request.json
    ID = webhook_data.get('ID')
    expiration_date = webhook_data.get('Expiration_Date')

#------------------------------------------------------------
#add user information in database 

@app.route('/ad-expiration-post', methods=['GET','POST'])
def receive_Ad_Tracking_Data():
    if request.method == 'POST':
        data = request.json

        # Extract data from the JSON
        ad_id = data.get('id')
        ad_title = data.get('ad_title')
        start_date = data.get('start_date')
        expiration_date = data.get('expiration_date')

        if ad_id is not None and expiration_date is not None:
            # Convert date strings to datetime objects
            start_date = datetime.strptime(start_date, '%Y-%m-%dT%H:%M:%SZ')
            expiration_date = datetime.strptime(expiration_date, '%Y-%m-%dT%H:%M:%SZ')

            # Create or update the AdTracking record
            ad = AdTracking.query.get(ad_id) or AdTracking()
            ad.id = ad_id
            ad.ad_title = ad_title
            ad.start_date = start_date
            ad.expiration_date = expiration_date

            # Add to the database session and commit
            db.session.add(ad)
            db.session.commit()

            return jsonify({'message': f'Ad {ad_id} data saved successfully.'}), 201
        else:
            return jsonify({'message': 'Invalid data format.'}), 400
    elif request.method == 'GET':
        # Handle GET request if needed
        return jsonify({'message': 'Welcome to the Ad-Expiration API.'}), 200
    else:
        return jsonify({'message': 'Invalid request method.'}), 405

#-----------------------------------------------------------------------------







@app.route('/notify', methods=['GET','POST'])
def check_and_send_notifications():
    Ad_Tracking_Data = load_Ad_Tracking_Data()
    today = datetime.now()
    notifications = []

    for ID, ad_data in Ad_Tracking_Data.items():
        expiration_date = ad_data['Expiration_Date']
        days_until_expiration = (expiration_date - today).days

        if days_until_expiration <= 0:
            notifications.append(f'Ad {ID} has expired!')
            # Notify via email
            send_email(f'Ad {ID} has expired', f'Ad {ID} has expired!')

        elif days_until_expiration <= 3:
            notifications.append(f'Ad {ID} is nearing expiration!')
            # Notify via email
            send_email(f'Ad {ID} is nearing expiration', f'Ad {ID} is nearing expiration!')

    return jsonify({'notifications': notifications}), 200


def calculate_expiration():
    Ad_Tracking_Data = load_Ad_Tracking_Data()
    df = pd.DataFrame.from_dict(Ad_Tracking_Data, orient='index')
    df['Days_Until_Expiration'] = (df['Expiration_Date'] - pd.Timestamp.today()).dt.days
    return df

@app.route('/calculate-expiration', methods=['GET'])
def calculate_and_update():
    df = calculate_expiration()
    for idx, row in df.iterrows():
        # Update Ad_Tracking_Data with new expiration calculations
        df[idx]['Days_Until_Expiration'] = row['Days_Until_Expiration']
    save_Ad_Tracking_Data(df)
    return jsonify({'message': 'Expiration calculated and updated.'}), 200

@app.route('/get-notifications', methods=['GET'])
def get_notifications():
    notifications = app.config.get('notifications', [])
    return jsonify({'notifications': notifications}), 200



@app.route('/check-ad-expiration', methods=['GET'])
def check_ad_expiration():
    Ad_Tracking_Data = load_Ad_Tracking_Data()
    notifications = []
    today = datetime.now()

    for ID, ad_data in Ad_Tracking_Data.items():
        expiration_date = ad_data['Expiration_Date']
        days_until_expiration = (expiration_date - today).days

        if days_until_expiration <= 0:
            notifications.append(f'Ad {ID} has expired!')
        elif days_until_expiration <= 3:
            notifications.append(f'Ad {ID} is nearing expiration!')

    for notification in notifications:
        print(notification)

    return jsonify({'notifications': notifications}), 200

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, use_reloader=False)
