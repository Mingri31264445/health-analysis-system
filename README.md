# Health Analysis System

Integrated health analysis platform that combines traditional Chinese medicine face diagnosis (YOLO image recognition), BFS and meridian instrument data, and health questionnaires. Team capstone project at Ming Chuan University.

**Tech:** Python 3.11 · Django · SQLite · OpenCV · YOLO · HTML · CSS · JavaScript

## Features

- **User accounts** with multiple test records per user
- **Questionnaire** as the baseline health record
- **BFS** and **meridian instrument** measurements, including PDF report parsing
- **Face diagnosis** records with YOLO-based image analysis
- **Role-based access:** separate user accounts and admin accounts

## Team & my part

Team capstone project. See the
[contributors page](https://github.com/Mingri31264445/health-analysis-system/graphs/contributors)
for commit history.

My part: Django backend and BFS PDF parsing module.

## Run locally

1. Clone this repository
2. Create an environment: `conda create -n health-analysis python=3.11`
3. Install dependencies: `pip install -r requirements.txt`
4. Initialize the database: `python manage.py migrate`
5. Create the upload folder: `mkdir media`
6. Start the server: `python manage.py runserver`, then open http://localhost:8000
