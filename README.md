JournalExpress

A simple web diary application built with HTML, CSS and Flask. Write, save and revisit your daily journal entries from the browser.

Features
Create and save journal entries
View past entries
[Edit / delete entries, if implemented]
[Login / user accounts, if implemented]
Clean, simple interface built with plain HTML and CSS
Tech Stack
Area	Tools
Backend	Python, Flask
Frontend	HTML, CSS
Templating	Jinja2 (Flask templates)
Storage MongoDB
Project Structure
JournalExpress/
├── app.py              # Flask application
├── templates/          # HTML templates
├── static/             # CSS and assets
├── requirements.txt
└── README.md

(Update this to match your actual folders.)

Getting Started
Prerequisites
Python 3.9+
Installation
bash
git clone https://github.com/Subhadeep-Adhikary/JounalExpress.git
cd JounalExpress
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
Run
bash
python app.py

Then open http://127.0.0.1:5000 in your browser.



Future Improvements
User authentication
Search and filter entries by date
Mood tags and categories
Deployment (e.g. Render) with a live demo link
Author

Subhadeep Adhikary

License

