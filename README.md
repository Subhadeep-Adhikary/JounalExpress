# JournalExpress

A simple web diary application built with HTML, CSS, and Flask. Write, save, and revisit journal entries from your browser.

## Features

- Create and save journal entries
- View past entries
- Clean interface built with HTML and CSS

## Tech Stack

| Area | Tools |
| --- | --- |
| Backend | Python, Flask |
| Frontend | HTML, CSS, JavaScript |
| Templating | Jinja2 |
| Storage | MongoDB |

## Project Structure

```text
JournalExpress/
├── app/
│   ├── models/
│   ├── routes/
│   ├── static/
│   └── templates/
├── tests/
└── run.py
```

## Getting Started

### Prerequisites

- Python 3.9 or later
- MongoDB

### Installation

```bash
git clone https://github.com/Subhadeep-Adhikary/JounalExpress.git
cd JounalExpress
python -m venv .venv
```

Activate the virtual environment:

```bash
# macOS or Linux
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1
```

Install the project dependencies using your preferred package manager, then configure the MongoDB connection in your environment.

### Run the App

```bash
python run.py
```

Open <http://127.0.0.1:5000> in your browser.

## Future Improvements

- User authentication
- Search and filter entries by date
- Mood tags and categories
- Deployment with a live demo

## Author

Subhadeep Adhikary
