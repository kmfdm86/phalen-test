import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="Student Intervention Generator", layout="centered")
st.title("📊 Student Intervention Report Generator")
st.write("Upload your student test results below. The system automatically detects the platform (Realize/KCE), subject, and grade level to generate your targeted intervention list.")

@st.cache_data
def load_item_analysis(filename):
    df = pd.read_csv(filename)
    df.columns = df.columns.str.strip()
    
    if 'Question_ID' not in df.columns:
        df = pd.read_csv(filename, skiprows=1)
        df.columns = df.columns.str.strip()
        
    return df

grade_names = {
    "K": "Kindergarten", "1": "1st Grade", "2": "2nd Grade", "3": "3rd Grade",
    "4": "4th Grade", "5": "5th Grade", "6": "6th Grade", "7": "7th Grade",
    "8": "8th Grade", "9": "9th Grade"
}

# --- DETECTION FUNCTIONS ---
def detect_realize_subject_and_grade(df):
    first_col = df.iloc[:, 0].dropna().astype(str)
    for val in first_col:
        val = val.strip()
        match_reading = re.match(r"^(RL|RI|RF|W|SL|L)\.?([K1-9])", val, re.IGNORECASE)
        if match_reading:
            return "reading", match_reading.group(2).upper()
        match_math = re.match(r"^([K1-9])\.(OA|NC|MD)", val, re.IGNORECASE)
        if match_math:
            return "math", match_math.group(1).upper()
    return "math", "K"

def detect_kce_subject_and_grade(filename):
    # Default to math if not explicitly reading
    subject = "reading" if "reading" in filename.lower() else "math"
    
    # Extract grade strictly from the test file name (e.g., "Grade 1")
    grade = "K"
    grade_match = re.search(r'Grade\s*([K1-9])', filename, re.IGNORECASE)
    if grade_match:
        grade = grade_match.group(1).upper()
        
    return subject, grade

def extract_reading_lessons(lesson_string):
    if pd.isna(lesson_string):
        return []
    individual_lessons = []
    parts = str(lesson_string).split(';')
    for part in parts:
        part = part.strip()
        match = re.search(r"Week\s+(\d+),\s+Lessons?\s+([\d,\s]+)", part, re.IGNORECASE)
        if match:
            week_num = match.group(1)
            lessons_str = match.group(2)
            lessons = [l.strip() for l in lessons_str.split(',')]
            for l in lessons:
                individual_lessons.append(f"Week {week_num}: Lesson {l}")
        else:
            if part:
                individual_lessons.append(part)
    return individual_lessons

# --- MAIN APP LOGIC ---
st.subheader("Upload Student Data")
student_file = st.file_uploader("Upload Student Results (CSV)", type="csv")

if student_file:
    raw_student_df = pd.read_csv(student_file)
    
    # Check if the file is from KCE (has 'Question #' and 'Student' columns)
    is_kce = 'Question #' in raw_student_df.columns and 'Student' in raw_student_df.columns
    
    if is_kce:
        detected_subject, detected_grade = detect_kce_subject_and_grade(student_file.name)
        platform = "KCE"
    else:
        detected_subject, detected_grade = detect_realize_subject_and_grade(raw_student_df)
        platform = "Realize"
        
    pretty
