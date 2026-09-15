# 💹 Smart Investment Advisor

Full-stack Flask web application with Excel (no SQL) backend.

## 🚀 Quick Start

```bash
pip install -r requirements.txt
python app.py
```
Open: http://localhost:5000

## 🔑 Default Credentials
| Role  | Username | Password  |
|-------|----------|-----------|
| Admin | admin    | admin123  |

Register a new user at /register


## 📁 Structure
```
smart_advisor/
├── app.py                  # Flask backend (Excel-powered, no SQL)
├── data_users.xlsx         # User accounts (auto-created)
├── data_history.xlsx       # Advice history (auto-created)
├── data_contacts.xlsx      # Contact form submissions (auto-created)
├── requirements.txt
└── templates/
    ├── login.html / register.html
    ├── dashboard.html      # Investment form + tips
    ├── result.html         # Portfolio chart + SIP calculator
    ├── about.html          # Project info
    ├── contact.html        # Contact form → saved to Excel
    ├── details.html        # User financial overview
    ├── profile.html        # Edit profile
    └── admin.html          # Users + Contacts tabs with delete
```

## ✨ Features
- 🔐 Auth with Werkzeug password hashing
- 📊 Excel database (openpyxl) — no SQL required
- 📈 Investment engine: Low/Medium/High risk portfolios
- 💹 Chart.js: Pie chart + SIP growth line chart
- 📬 Contact page — data stored in admin dashboard
- 🗑️ Admin can delete users AND contact messages
- 📅 SIP Calculator with compound interest formula
