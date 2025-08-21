# PeerFinder - Peer Matching App

PeerFinder is a Flask-based web application designed to help learners find ideal study buddies, groups, or accountability partners tailored to their cohort, country, language, topic/module, availability, and support needs. It also supports learners offering or requesting academic support. The app facilitates structured peer connections, fostering collaboration, motivation, and mutual help.

---

## Features

### User Types / Connection Modes
- Find a Study Buddy / Group / Accountability Partner(s)
- Offer Support to Someone
- I Need Support (I’m Behind / Struggling)

### Flexible Matching Logic
- Match learners by country, cohort, topic/module, availability, preferred study setup, and kind of support needed/offered.
- Learners selecting “Flexible” availability can be matched with any other availability option.

### User Flow
1. Users choose their connection mode on landing page.
2. Fill in a tailored form based on selected mode with all required fields.
3. Join the queue for matching.
4. Check match status anytime.
5. Receive email with matched peer contact info upon successful matching.
6. Option to unpair and rejoin with reason submission.

### Admin Controls
- Admin login for downloading data CSV securely.
- View current queue and manage matches.

### Data Storage
- User data and matching info stored in a CSV file on AWS S3.
- Phone numbers handled as strings to avoid number formatting issues.

### Email Notifications
- Automated emails sent to matched peers with details for easy communication.

---

## Tech Stack
- **Backend:** Python Flask
- **Storage:** AWS S3 for CSV data file
- **Email:** Flask-Mail with SMTP (configured for Gmail in default)
- **Data Processing:** Pandas for CSV read/write and matching logic
- **Frontend:** Jinja2 templates with standard HTML/CSS, responsive design

---

## Installation & Setup

### Prerequisites
- Python 3.8+
- AWS Account with S3 bucket access
- Gmail account (or other SMTP) for sending emails
- Render (or other hosting) for deployment (optional)

### Clone the repository
```bash
git clone https://github.com/yourusername/peerfinder.git
cd peerfinder
```

### Create and activate Python virtual environment
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

### Install dependencies
```bash
pip install -r requirements.txt
```

### Environment Variables
Create a `.env` file with the following variables (or set them in your host environment):
```
SECRET_KEY=your_flask_secret_key
AWS_ACCESS_KEY_ID=your_aws_access_key_id
AWS_SECRET_ACCESS_KEY=your_aws_secret_access_key
AWS_DEFAULT_REGION=your_aws_region
MAIL_USERNAME=your_email@gmail.com
MAIL_PASSWORD=your_email_app_password
AWS_S3_BUCKET=your_s3_bucket_name
```
> Use an App Password for Gmail if 2FA is enabled.

### Run the app locally
```bash
flask run
```
or
```bash
python app.py
```
The app will be accessible at [http://localhost:5000](http://localhost:5000).

---

## Usage
1. **Landing Page:** Choose your connection type.
2. **Form Page:** Fill the required details tailored to your selection.
3. **Waiting:** After form submission, wait for peer matching.
4. **Check Match Status:** Use your unique ID to check if you’ve been matched.
5. **Matched Page:** See your group or partner details.
6. **Unpair:** Option to unpair with reason submission if needed.
7. **Admin Panel:** Secure access for admins to download CSV data.

---

## Folder Structure
```
/
├── app.py                  # Flask backend application
├── requirements.txt        # Python dependencies
├── templates/              # Jinja2 HTML templates
│   ├── landing.html        # Landing page
│   ├── form.html           # Dynamic input form
│   ├── waiting.html        # Waiting for match page
│   ├── matched.html        # Matched group view
│   ├── already_matched.html
│   ├── already_in_queue.html
│   ├── check.html          # Check match status page
│   ├── admin.html
│   ├── password_prompt.html
│   ├── disclaimer.html
│   └── ...other templates
├── static/                 # Static files (images, CSS if any)
├── .env                    # Environment variables (not committed)
└── README.md               # This file
```

---

## Notes & Recommendations
- Ensure unique email addresses per user for proper matching notifications.
- Phone numbers are stored as strings to preserve international formatting.
- The app currently uses CSV storage on S3; for larger scale, consider migrating to a database.
- Matching emails exclude the user’s own contact to avoid redundant info.
- Form fields and validations enforce required inputs for consistent data.
- Availability matching treats "Flexible" as compatible with any time.
- Unpairing updates user records but keeps matched status for transparency.

---

## License
MIT License

---

## Contributors
- Chukwudi Okereafor - Initial development
- 
