# Job / Project Tracker

Streamlit app for tracking small-business jobs and customer projects.

## What it does

- Add projects with customer, assigned person, deadline, status, priority, notes, and next action
- Shows action-focused dashboard for overdue, due today, due this week, blocked, waiting, and high-priority projects
- Creates copy-ready reminder drafts for overdue, due today, due this week, blocked, and waiting projects
- Supports CSV/Excel upload
- Editable project table
- Excel and CSV export
- Stores data locally in `job_project_tracker/data/projects.csv`

## Run locally

```bash
streamlit run job_project_tracker/app.py
```

## Upload columns

CSV or Excel files can include these columns:

```text
project_name, customer, assigned_person, status, priority, start_date, deadline, next_action, last_update, notes
```

Dates should use `YYYY-MM-DD`.
