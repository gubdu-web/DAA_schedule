# Synapse Schedule 📅
### AI-Powered School Timetable Generator using Genetic Algorithms

Synapse Schedule is a modern web application designed to help educational institutions automate the preparation of weekly class schedules. It accepts a plain text dataset and runs a heuristic Genetic Algorithm on a Flask backend to search for valid, conflict-free timetables while optimizing soft constraints.

---

## ✨ Features
* **Constraint Satisfaction**: Eliminates hard conflicts (e.g., faculty double-bookings, classroom overlaps, student group clashes) and respects faculty unavailability windows.
* **Soft Constraint Optimization**: Minimizes schedule gaps (free periods) for student groups and faculty, and ensures balanced subject distribution.
* **Real-time Monitoring**: Visualizes the optimization process live with progress bars, statistics, and conflict logs.
* **Multiple Calendar Views**: Filter the generated schedule instantly by **Student Group**, **Faculty Member**, or **Classroom**.
* **Export Options**: Export the final timetable as a formatted CSV spreadsheet or print it directly.

---

## 🛠️ Tech Stack
* **Backend**: Python (Flask)
* **Algorithm**: Heuristic Genetic Algorithm (Custom mutation & selection heuristics)
* **Frontend**: HTML5, Vanilla CSS3 (Glassmorphism design system), ES6 JavaScript
* **Visualizations**: Chart.js (Live progress monitoring)

---

## 🚀 How to Run Locally

### 1. Prerequisites
Make sure you have **Python 3.x** installed. You will need Flask installed:
```bash
pip install flask
