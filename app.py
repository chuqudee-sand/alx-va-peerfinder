import os
import uuid
import io
from datetime import datetime
from flask import Flask, request, jsonify, render_template, redirect, url_for, Response, flash
import pandas as pd
import boto3
from botocore.exceptions import ClientError
from flask_mail import Mail, Message
from flask import current_app
from flask import session


app = Flask(__name__)

# === ENVIRONMENT VARIABLES REQUIRED ===
SECRET_KEY = "e8f3473b716cfe3760fd522e38a3bd5b9909510b0ef003f050e0a445fa3a6e83"
AWS_ACCESS_KEY_ID = os.environ.get('WS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
AWS_DEFAULT_REGION = os.environ.get('AWS_DEFAULT_REGION')
EMAIL_APP_PASSWORD = os.environ.get('APP_PASSWORD')

app.secret_key = os.environ.get('SECRET_KEY', 'default_secret_key')  # [REQUIRED]

# Flask-Mail configuration
app.config.update(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT=587,
    MAIL_USE_TLS=True,
    MAIL_USERNAME="vaprogram@alxafrica.com",      # [REQUIRED]
    MAIL_PASSWORD=EMAIL_APP_PASSWORD,                  # [REQUIRED]
)
mail = Mail(app)

# AWS S3 configuration
AWS_S3_BUCKET = "alx-peer-finder-storage-bucket"
if not AWS_S3_BUCKET:
    raise Exception("AWS_S3_BUCKET environment variable not set")

s3 = boto3.client('s3')
CSV_OBJECT_KEY = 'va_peer-matcing_data.csv'

ADMIN_PASSWORD = "alx_admin_2025_peer_finder"

# === Helper Functions ===

def download_csv():
    try:
        obj = s3.get_object(Bucket=AWS_S3_BUCKET, Key=CSV_OBJECT_KEY)
        data = obj['Body'].read().decode('utf-8')
        df = pd.read_csv(io.StringIO(data))
        # Ensure phone as string and strip whitespace
        if 'phone' in df.columns:
            df['phone'] = df['phone'].astype(str).str.strip()
        if 'matched' in df.columns:
            df['matched'] = df['matched'].astype(str).str.upper() == 'TRUE'
        else:
            df['matched'] = False
        # Add missing columns if absent
        expected_columns = [
            'id', 'name', 'phone', 'email', 'country', 'language', 'cohort', 'topic_module',
            'learning_preferences', 'availability', 'preferred_study_setup', 'kind_of_support',
            'connection_type', 'timestamp', 'matched', 'group_id', 'unpair_reason', 'matched_timestamp'
        ]
        for col in expected_columns:
            if col not in df.columns:
                if col == 'matched':
                    df[col] = False
                else:
                    df[col] = ''
        return df
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchKey':
            columns = [
                'id', 'name', 'phone', 'email', 'country', 'language', 'cohort', 'topic_module',
                'learning_preferences', 'availability', 'preferred_study_setup', 'kind_of_support',
                'connection_type', 'timestamp', 'matched', 'group_id', 'unpair_reason', 'matched_timestamp'
            ]
            return pd.DataFrame(columns=columns)
        else:
            raise

def upload_csv(df):
    if 'phone' in df.columns:
        df['phone'] = df['phone'].astype(str).str.strip()
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    s3.put_object(Bucket=AWS_S3_BUCKET, Key=CSV_OBJECT_KEY, Body=csv_buffer.getvalue())

def availability_match(a1, a2):
    # Flexible matches any, else must match or one must be flexible
    if a1 == 'Flexible' or a2 == 'Flexible':
        return True
    return a1 == a2

def find_existing(df, phone, email, connection_type, **kwargs):
    # Find existing user by phone/email + connection_type + required matching fields depending on type
    base_mask = ((df['phone'] == phone) | (df['email'] == email)) & (df['connection_type'] == connection_type)
    if connection_type == 'find':
        mask = base_mask & \
               (df['country'] == kwargs.get('country')) & \
               (df['language'] == kwargs.get('language')) & \
               (df['cohort'] == kwargs.get('cohort')) & \
               (df['topic_module'] == kwargs.get('topic_module')) & \
               (df['preferred_study_setup'] == kwargs.get('preferred_study_setup'))
    elif connection_type in ['offer', 'need']:
        mask = base_mask & \
               (df['country'] == kwargs.get('country')) & \
               (df['language'] == kwargs.get('language')) & \
               (df['cohort'] == kwargs.get('cohort')) & \
               (df['topic_module'] == kwargs.get('topic_module'))
    else:
        mask = base_mask
    matches = df[mask]
    if not matches.empty:
        return matches.index[0]
    return None

def send_match_email(user_email, user_name, group_members):
    peer_info_list = []
    for m in group_members:
        if m['email'] != user_email and m['email'] != 'unpaired':
            support = m.get('kind_of_support', '')
            if support == '' or (isinstance(support, float) and math.isnan(support)):
                support = "Accountability"
            support_info = f"\nSupport Type: {support}"
            peer_info_list.append(f"Name: {m['name']}\nEmail Address: {m['email']}\nWhatsApp: {m['phone']}{support_info}")
    peer_info = '\n\n'.join(peer_info_list)
    if not peer_info:
        peer_info = "No other members found."
    body = f"""Hi {user_name},

You have been matched with the following peer(s):

{peer_info}

Kindly reach out to your peer(s) for collaboration and support!👍

⚠️ Please Read Carefully

We want this to be a positive and supportive experience for everyone. To help make that happen:

- Please show up for your partner or group — ghosting is discouraged and can affect their progress.

- Only fill this form with accurate details. If you've entered incorrect information, kindly unpair yourself.

- If you've completed all your modules, consider supporting others who are catching up — your help can make a real difference.🤗

- If you no longer wish to participate, let your partner/group know first before unpairing.

- If you'd like to be paired with someone new, you'll need to register again.

Thank you for helping create a respectful and encouraging learning community.

Best regards,

Peer Finder Team
"""
    msg = Message(
        subject="You've been matched!",
        sender=app.config['MAIL_USERNAME'],
        recipients=[user_email]
    )
    msg.body = body
    mail.send(msg)

def send_waiting_email(user_email, user_name, user_id):
    confirm_link = url_for('check_match', _external=True)
    body = f"""Hi {user_name},

Waiting to Be Matched

Your request is in the queue.

As soon as a suitable peer or group is available, you'll be matched.

Kindly copy your ID below to check your status later:

Your ID: {user_id}

Check your status here: {confirm_link}

Best regards,

Peer Finder Team
"""
    msg = Message(
        subject="PeerFinder - Waiting to Be Matched",
        sender=current_app.config['MAIL_USERNAME'],
        recipients=[user_email]
    )
    msg.body = body
    mail.send(msg)

def fallback_match_unmatched():
    df = download_csv()
    now = datetime.utcnow()
    updated = False

    unmatched = df[
        (df['matched'] == False) &
        (df['connection_type'] == 'find')
    ]

    def is_older_than_4_days(ts):
        try:
            dt = datetime.fromisoformat(ts)
            return (now - dt) > timedelta(days=4)
        except Exception:
            return False

    unmatched = unmatched[unmatched['timestamp'].apply(is_older_than_4_days)]

    for group_size in [2, 3, 5]:
        eligible = unmatched[unmatched['preferred_study_setup'] == str(group_size)]
        while len(eligible) >= group_size:
            group = eligible.iloc[:group_size]
            if len(set(group['id'])) < group_size:
                eligible = eligible.iloc[group_size:]
                continue
            group_id = f"group-fallback-{uuid.uuid4()}"
            now_iso = now.isoformat()
            df.loc[group.index, 'matched'] = True
            df.loc[group.index, 'group_id'] = group_id
            df.loc[group.index, 'matched_timestamp'] = now_iso
            updated = True
            eligible = eligible.iloc[group_size:]
    if updated:
        df['phone'] = df['phone'].astype(str).str.strip()
        upload_csv(df)

# === Flask Routes ===

@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/start/<connection_type>')
def start_form(connection_type):
    if connection_type not in ['find', 'offer', 'need']:
        return "Invalid connection type", 404
    return render_template('form.html', connection_type=connection_type)


@app.route('/join', methods=['POST'])
def join_queue():
    data = request.form
    connection_type = data.get('connection_type')
    if connection_type not in ['find', 'offer', 'need']:
        return render_template('landing.html', error="Invalid connection type selected.")

    # Parse and clean form data
    name = data.get('name', '').strip()
    phone = str(data.get('phone', '').strip())
    email = data.get('email', '').strip().lower()
    country = data.get('country', '').strip()
    language = data.get('language', '').strip()
    cohort = data.get('cohort', '').strip()
    topic_module = data.get('topic_module', '').strip()
    learning_preferences = data.get('learning_preferences', '').strip()
    availability = data.get('availability', '').strip()

    required_fields = [name, phone, email, country, language, cohort, topic_module, learning_preferences, availability]
    if not all(required_fields):
        return render_template('form.html', connection_type=connection_type, error="Please fill all required fields.")

    if not phone.startswith('+') or len(phone) < 7:
        return render_template('form.html', connection_type=connection_type, error="Please start your phone number with a plus (+) and enter a valid number.")

    preferred_study_setup = ''
    kind_of_support = ''

    if connection_type == 'find':
        preferred_study_setup = data.get('preferred_study_setup', '').strip()
        if not preferred_study_setup or preferred_study_setup not in ['2', '3', '5']:
            return render_template('form.html', connection_type=connection_type, error="Please select a valid preferred study setup.")
    elif connection_type in ['offer', 'need']:
        kind_of_support = data.get('kind_of_support', '').strip()
        if not kind_of_support:
            return render_template('form.html', connection_type=connection_type, error="Please select kind of support.")

    df = download_csv()

    # Duplicate check based on email, phone, cohort, preferred_study_setup and connection_type
    dup_mask = (
        ((df['email'] == email) | (df['phone'] == phone)) &
        (df['cohort'] == cohort) &
        (df['preferred_study_setup'] == preferred_study_setup) &
        (df['connection_type'] == connection_type)
    )
    duplicates = df[dup_mask]

    if not duplicates.empty:
        dup = duplicates.iloc[0]
        if dup['matched']:
            group_id = dup['group_id']
            group_members = df[df['group_id'] == group_id]
            return render_template('already_matched.html', user=dup, group_members=group_members.to_dict(orient='records'))
        else:
            return render_template('already_in_queue.html', user_id=dup['id'])

    # No duplicates - add new user
    new_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()
    new_row = {
        'id': new_id,
        'name': name,
        'phone': phone,
        'email': email,
        'country': country,
        'language': language,
        'cohort': cohort,
        'topic_module': topic_module,
        'learning_preferences': learning_preferences,
        'availability': availability,
        'preferred_study_setup': preferred_study_setup,
        'kind_of_support': kind_of_support,
        'connection_type': connection_type,
        'timestamp': timestamp,
        'matched': False,
        'group_id': '',
        'unpair_reason': '',
        'matched_timestamp': ''
    }
    new_row_df = pd.DataFrame([new_row])
    df = pd.concat([df, new_row_df], ignore_index=True)
    df['phone'] = df['phone'].astype(str).str.strip()
    upload_csv(df)

    send_waiting_email(email, name, new_id)
    return redirect(url_for('waiting', user_id=new_id))


@app.route('/waiting/<user_id>')
def waiting(user_id):
    return render_template('waiting.html', user_id=user_id)

@app.route('/match', methods=['POST'])
def match_users():
    data = request.json
    user_id = data.get('user_id')
    if not user_id:
        return jsonify({'error': 'User ID required'}), 400
    df = download_csv()
    user = df[df['id'] == user_id]
    if user.empty:
        return jsonify({'error': 'User not found'}), 404
    user = user.iloc[0]
    updated = False
    if user['connection_type'] == 'find':
        country = user['country']
        cohort = user['cohort']
        topic_module = user['topic_module']
        preferred_study_setup = user['preferred_study_setup']
        availability = user['availability']
        try:
            group_size = int(preferred_study_setup)
        except ValueError:
            return jsonify({'error': 'Invalid preferred study setup'}), 400
        if group_size not in [2, 3, 5]:
            return jsonify({'error': 'Unsupported group size'}), 400

        eligible = df[
            (df['matched'] == False) &
            (df['connection_type'] == 'find') &
            (df['country'] == country) &
            (df['cohort'] == cohort) &
            (df['topic_module'] == topic_module) &
            (df['preferred_study_setup'] == preferred_study_setup)
        ]
        eligible = eligible[eligible['availability'].apply(lambda x: availability_match(x, availability))]
        while len(eligible) >= group_size:
            group = eligible.iloc[:group_size]
            if len(set(group['id'])) < group_size:
                eligible = eligible.iloc[group_size:]
                continue
            group_id = f"group-{uuid.uuid4()}"
            now_iso = datetime.utcnow().isoformat()
            df.loc[group.index, 'matched'] = True
            df.loc[group.index, 'group_id'] = group_id
            df.loc[group.index, 'matched_timestamp'] = now_iso
            updated = True
            eligible = eligible.iloc[group_size:]

    elif user['connection_type'] in ['offer', 'need']:
        country = user['country']
        cohort = user['cohort']
        availability = user['availability']
        opposite_type = 'need' if user['connection_type'] == 'offer' else 'offer'
        eligible = df[
            (df['matched'] == False) &
            (df['connection_type'] == opposite_type) &
            (df['country'] == country) &
            (df['cohort'] == cohort)
        ]
        eligible = eligible[eligible['availability'].apply(lambda x: availability_match(x, availability))]
        if not eligible.empty:
            matched_user_idx = eligible.index[0]
            group_id = f"group-{uuid.uuid4()}"
            now_iso = datetime.utcnow().isoformat()
            df.at[user.name, 'matched'] = True
            df.at[user.name, 'group_id'] = group_id
            df.at[user.name, 'matched_timestamp'] = now_iso
            df.at[matched_user_idx, 'matched'] = True
            df.at[matched_user_idx, 'group_id'] = group_id
            df.at[matched_user_idx, 'matched_timestamp'] = now_iso
            updated = True
    else:
        return jsonify({'error': 'Unsupported connection type'}), 400

    if updated:
        df['phone'] = df['phone'].astype(str).str.strip()
        upload_csv(df)

    user = df[df['id'] == user_id].iloc[0]
    if user['matched']:
        group_id = user['group_id']
        group_members = df[df['group_id'] == group_id].to_dict(orient='records')
        for member in group_members:
            if member['email'] != 'unpaired':
                send_match_email(member['email'], member['name'], group_members)
        return jsonify({
            'matched': True,
            'group_id': group_id,
            'members': group_members
        })

    else:
        return jsonify({'matched': False})

@app.route('/matched/<user_id>')
def matched(user_id):
    df = download_csv()
    user = df[df['id'] == user_id]
    if user.empty:
        return "User not found", 404
    user = user.iloc[0]
    if not user['matched']:
        return redirect(url_for('waiting', user_id=user_id))
    group_id = user['group_id']
    group_members = df[df['group_id'] == group_id]
    return render_template('matched.html', user=user, group_members=group_members.to_dict(orient='records'))

@app.route('/check', methods=['GET', 'POST'])
def check_match():
    if request.method == 'POST':
        user_id = request.form.get('user_id', '').strip()
        if not user_id:
            return render_template('check.html', error="Please enter your ID.")
        df = download_csv()
        user = df[df['id'] == user_id]
        if user.empty:
            return render_template('check.html', error="ID not found. Please check and try again.")
        user = user.iloc[0]
        if user['matched']:
            group_id = user['group_id']
            group_members = df[df['group_id'] == group_id]
            return render_template('check.html', matched=True, group_members=group_members.to_dict(orient='records'), user=user)
        else:
            return render_template('check.html', matched=False, user=user)
    else:
        return render_template('check.html')

@app.route('/unpair', methods=['POST'])
def unpair():
    user_id = request.form.get('user_id')
    reason = request.form.get('reason', '').strip()
    if not user_id or not reason:
        return jsonify({'error': 'User ID and reason are required'}), 400
    df = download_csv()
    user_row = df[df['id'] == user_id]
    if user_row.empty:
        return jsonify({'error': 'User not found'}), 404
    user = user_row.iloc[0]
    group_id = user['group_id']
    if user['matched'] and group_id:
        group_indices = df.index[df['group_id'] == group_id].tolist()
    else:
        group_indices = [user_row.index[0]]
    for idx in group_indices:
        df.at[idx, 'email'] = 'unpaired'
        df.at[idx, 'cohort'] = 'unpaired'
        df.at[idx, 'topic_module'] = 'unpaired'
        df.at[idx, 'unpair_reason'] = reason  # Do NOT change matched status as requested
    df['phone'] = df['phone'].astype(str).str.strip()
    upload_csv(df)
    return jsonify({'success': True})

@app.route('/admin')
def admin():
    return render_template('admin.html')

@app.route('/admin/download_csv', methods=['GET', 'POST'])
def download_queue():
    if request.method == 'POST':
        password = request.form.get('password', '')
        if password == ADMIN_PASSWORD:
            df = download_csv()
            csv_buffer = io.StringIO()
            df.to_csv(csv_buffer, index=False)
            csv_buffer.seek(0)
            return Response(
                csv_buffer.getvalue(),
                mimetype='text/csv',
                headers={"Content-Disposition": "attachment;filename=students.csv"}
            )
        else:
            flash("Incorrect password. Access denied.")
            return redirect(url_for('download_queue'))
    return render_template('password_prompt.html', file_type='Queue CSV')

# Add these routes at the bottom (before your existing @app.route('/admin'))

@app.route('/admin/fallback', methods=['GET', 'POST'])
def admin_fallback():
    if request.method == 'POST':
        password = request.form.get('password', '')
        if password == ADMIN_PASSWORD:
            # Store password in session to avoid re-prompt if desired (optional)
            session['admin_authenticated'] = True
            return redirect(url_for('admin_fallback_match'))
        else:
            flash('Incorrect password. Access denied.')
            return redirect(url_for('admin_fallback'))
    return render_template('admin_fallback.html')  # Create this template (see below)

@app.route('/admin/fallback_match')
def admin_fallback_match():
    # Optional: Check if user is authenticated with session or else prompt password again
    if not session.get('admin_authenticated', False):
        flash('Please authenticate first.')
        return redirect(url_for('admin_fallback'))

    fallback_match_unmatched()
    flash("Fallback matching process executed successfully.")
    return redirect(url_for('admin'))


@app.route('/admin/download_feedback')
def download_feedback():
    # Placeholder for feedback CSV download
    return "Feedback download not implemented yet", 501

@app.route('/disclaimer')
def disclaimer():
    return render_template('disclaimer.html')


if __name__ == '__main__':
    app.run(debug=True)




