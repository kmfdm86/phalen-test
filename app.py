import streamlit as st
import pandas as pd
import plotly.express as px
import re

# --- Configure Page ---
st.set_page_config(page_title="Student Growth Analysis", layout="wide")
st.title("📊 Student Growth Analysis Tool")
st.markdown("Upload Pretest and Posttest CSV reports to analyze student growth in Math and Reading.")

# --- Helper Functions ---
def extract_grade(text):
    # Attempts to extract grade level from Class, Program, or School name (e.g. "Grade 1" or "4th Grade")
    if pd.isna(text):
        return "Unknown"
    match = re.search(r'(?:Grade\s*([Kk0-9])|([Kk0-9])(?:th|nd|rd|st)\s*Grade)', str(text), re.IGNORECASE)
    if match:
        grade = match.group(1) or match.group(2)
        grade = grade.upper()
        return "K" if grade == "K" else f"Grade {grade}"
    return "Unknown"

def extract_subject(text):
    # Simplistic subject check based on keywords
    text_lower = str(text).lower()
    if 'math' in text_lower:
        return 'Math'
    elif 'reading' in text_lower or 'literacy' in text_lower:
        return 'Reading'
    return 'Other'

def preprocess_data(df):
    """Formats the dataframe depending on which CSV version was uploaded."""
    df.columns = df.columns.str.strip()
    
    # Handle the new format (Question-level rows with 'Test Raw Score')
    if 'Test Raw Score' in df.columns and 'Test Max Score' in df.columns:
        # Standardize names to match the old format
        if 'Student Name' not in df.columns and 'Student' in df.columns:
            df = df.rename(columns={'Student': 'Student Name'})
            
        # Deduplicate to get one row per student test submission
        df = df.drop_duplicates(subset=['Student Name', 'Submit Date', 'Test Raw Score', 'Test Max Score']).copy()
        
        # Calculate the % Score
        df['% Score'] = (df['Test Raw Score'] / df['Test Max Score']) * 100
        
        # Create a combined 'ProgramInfo' column to search for grade/subject context
        df['ProgramInfo'] = df['Class'].astype(str) + " " + df['School'].astype(str)
        
    else:
        # Handle the original format
        if 'Program' in df.columns:
            df['ProgramInfo'] = df['Program']
        else:
            df['ProgramInfo'] = df['Class'].astype(str)
            
    return df

# --- File Uploaders ---
col1, col2 = st.columns(2)
with col1:
    pretest_file = st.file_uploader("Upload Pretest Report (CSV)", type=['csv'])
with col2:
    posttest_file = st.file_uploader("Upload Posttest Report (CSV)", type=['csv'])

if pretest_file and posttest_file:
    # Load data
    pre_df = pd.read_csv(pretest_file)
    post_df = pd.read_csv(posttest_file)
    
    # Preprocess (Deduplicate multiple question rows, map columns, calculate % Score)
    pre_df = preprocess_data(pre_df)
    post_df = preprocess_data(post_df)

    # Merge on Student Name, Teacher, and School since Student ID is missing in the new format
    merge_cols = ['Student Name', 'Teacher', 'School']
    
    merged_df = pd.merge(
        pre_df, 
        post_df, 
        on=merge_cols, 
        suffixes=('_pre', '_post')
    )
    
    if merged_df.empty:
        st.error("No matching students found between the Pretest and Posttest files based on Student Name and Teacher.")
    else:
        # --- Data Processing ---
        # Calculate Growth
        merged_df['Growth (%)'] = merged_df['% Score_post'] - merged_df['% Score_pre']
        
        # Extract Subject and Grade based on contextual columns (Class/School/Program)
        merged_df['Subject'] = merged_df['ProgramInfo_post'].apply(extract_subject)
        merged_df['Grade Level'] = merged_df['ProgramInfo_post'].apply(extract_grade)
        
        # In case the automated extraction misses the subject due to naming conventions, 
        # let's allow users to override via the UI if it returns 'Other'.
        
        # --- Sidebar Filters ---
        st.sidebar.header("Filter Data")
        
        subject_filter = st.sidebar.multiselect(
            "Select Subject", 
            options=merged_df['Subject'].unique(), 
            default=merged_df['Subject'].unique()
        )
        
        grade_filter = st.sidebar.multiselect(
            "Select Grade Level", 
            options=
