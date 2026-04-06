# 📊 Student Growth Analysis Tool

A Python-based web application built with [Streamlit](https://streamlit.io/) designed for school administrators. This tool allows educators to easily upload pretest and posttest score reports, automatically merge the data, and visualize student academic growth in Math and Reading.

## ✨ Features

* **Automated Data Merging:** Automatically links pretest and posttest records using unique Student IDs—no more manual Excel `VLOOKUP`s!
* **Smart Categorization:** Automatically extracts the Subject (Math/Reading) and Grade Level (K-9) based on the assessment program name.
* **Interactive Dashboards:** Switch between three distinct analytical views:
  * **By Student:** Granular view showing individual student growth percentages.
  * **By Teacher:** Aggregate view showing the average student growth within each teacher's classroom.
  * **By Grade Level:** High-level view comparing average growth across different grade levels and subjects.
* **Visual Data:** Color-coded data tables and interactive Plotly bar charts (Green for positive growth, Red for regression).

## 🛠️ Prerequisites

To run this application locally, you will need Python 3.7+ installed on your machine. You will also need the following Python libraries:

* `streamlit`
* `pandas`
* `plotly`

## 🚀 Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/yourusername/student-growth-analysis.git](https://github.com/yourusername/student-growth-analysis.git)
   cd student-growth-analysis