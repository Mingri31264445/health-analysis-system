# Health Analysis System

Integrated health analysis platform that combines traditional Chinese medicine face diagnosis (YOLO image recognition), BFS and meridian instrument data, and health questionnaires. Team capstone project at Ming Chuan University.

**Tech:** Python 3.11 · Django · SQLite · OpenCV · YOLO · HTML · CSS · JavaScript

## Features

- **Subject accounts** with multiple test records per subject
- **Questionnaire** as the baseline health record
- **BFS** and **meridian instrument** measurements, including PDF report parsing
- **Face diagnosis** records with YOLO-based image analysis
- **Role-based access:** subjects see only their own records, researchers can view all subjects' records without managing accounts, and admins have full control through Django Admin

## Team & my part

Team capstone project. See the
[contributors page](https://github.com/Mingri31264445/health-analysis-system/graphs/contributors)
for commit history.

My part: Django backend and BFS PDF parsing module.

<details>
<summary>Run locally</summary>

1. Clone this repository
2. Create an environment: `conda create -n health-analysis python=3.11`
3. Install dependencies: `pip install -r requirements.txt`
4. Initialize the database: `python manage.py migrate`
5. Create the upload folder: `mkdir media`
6. Start the server: `python manage.py runserver`, then open http://localhost:8000

</details>
