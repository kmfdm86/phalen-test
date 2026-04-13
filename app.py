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
    if pd.isna(text):
        return "Unknown"
    match = re.search(r'(?:Grade\s*([Kk0-9])|([Kk0-9])(?:th|nd|rd|st)\s*Grade)', str(text), re.IGNORECASE)
    if match:
        grade = match.group(1) or match.group(2)
        grade = grade.upper()
        return "K" if grade == "K" else f"Grade {grade}"
    return "Unknown"

def extract_subject(text):
    text_lower = str(text).lower()
    if 'math' in text_lower:
        return 'Math'
    elif 'reading' in text_lower or 'literacy' in text_lower:
        return 'Reading'
    return 'Other'

def preprocess_data(df):
    """Formats the dataframe depending on which CSV version was uploaded."""
    df.columns = df.columns.str.strip()
    
    if 'Test Raw Score' in df.columns and 'Test Max Score' in df.columns:
        if 'Student Name' not in df.columns and 'Student' in df.columns:
            df = df.rename(columns={'Student': 'Student Name'})
            
        df = df.drop_duplicates(subset=['Student Name', 'Submit Date', 'Test Raw Score', 'Test Max Score']).copy()
        df['% Score'] = (df['Test Raw Score'] / df['Test Max Score']) * 100
        df['ProgramInfo'] = df['Class'].astype(str) + " " + df['School'].astype(str)
    else:
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
    
    # Preprocess
    pre_df = preprocess_data(pre_df)
    post_df = preprocess_data(post_df)

    # Merge
    merge_cols = ['Student Name', 'Teacher', 'School']
    merged_df = pd.merge(pre_df, post_df, on=merge_cols, suffixes=('_pre', '_post'))
    
    if merged_df.empty:
        st.error("No matching students found between the Pretest and Posttest files based on Student Name and Teacher.")
    else:
        # Calculate Growth
        merged_df['Growth (%)'] = merged_df['% Score_post'] - merged_df['% Score_pre']
        merged_df['Subject'] = merged_df['ProgramInfo_post'].apply(extract_subject)
        merged_df['Grade Level'] = merged_df['ProgramInfo_post'].apply(extract_grade)
        
        # --- Sidebar Filters ---
        st.sidebar.header("Filter Data")
        
        subject_filter = st.sidebar.multiselect(
            "Select Subject", 
            options=merged_df['Subject'].unique(), 
            default=merged_df['Subject'].unique()
        )
        
        grade_filter = st.sidebar.multiselect(
            "Select Grade Level", 
            options=sorted(merged_df['Grade Level'].unique()), 
            default=sorted(merged_df['Grade Level'].unique())
        )
        
        filtered_df = merged_df[
            (merged_df['Subject'].isin(subject_filter)) & 
            (merged_df['Grade Level'].isin(grade_filter))
        ]
        
        st.success(f"Data successfully merged! Analyzing {len(filtered_df)} student records.")
        
        # --- Shared Formatting Dictionary ---
        # This prevents long-line errors when copy/pasting!
        num_format = {
            '% Score_pre': "{:.1f}", 
            '% Score_post': "{:.1f}", 
            'Growth (%)': "{:.1f}"
        }
        
        # --- Navigation ---
        view_option = st.radio("Select View:", ("By Student", "By Teacher", "By Grade Level"), horizontal=True)
        st.divider()
        
        # --- 1. View By Student ---
        if view_option == "By Student":
            st.subheader("Student Growth")
            teacher_filter = st.selectbox("Optional: Filter by Teacher", ["All"] + list(filtered_df['Teacher'].unique()))
            
            student_view = filtered_df.copy()
            if teacher_filter != "All":
                student_view = student_view[student_view['Teacher'] == teacher_filter]
                
            display_cols = ['Student Name', 'Grade Level', 'Subject', 'Teacher', '% Score_pre', '% Score_post', 'Growth (%)']
            
            # Apply styling and formatting cleanly
            styled_student_df = student_view[display_cols].style.background_gradient(subset=['Growth (%)'], cmap='RdYlGn').format(num_format)
            st.dataframe(styled_student_df)
            
            if not student_view.empty:
                fig = px.bar(student_view, x='Student Name', y='Growth (%)', color='Growth (%)', 
                             color_continuous_scale='RdYlGn', title="Growth Percentage per Student")
                st.plotly_chart(fig, use_container_width=True)

        # --- 2. View By Teacher ---
        elif view_option == "By Teacher":
            st.subheader("Average Growth by Teacher")
            
            if not filtered_df.empty:
                teacher_agg = filtered_df.groupby('Teacher').agg({
                    '% Score_pre': 'mean',
                    '% Score_post': 'mean',
                    'Growth (%)': 'mean',
                    'Student Name': 'count'
                }).reset_index().rename(columns={'Student Name': 'Student Count'})
                
                styled_teacher_df = teacher_agg.style.background_gradient(subset=['Growth (%)'], cmap='RdYlGn').format(num_format)
                st.dataframe(styled_teacher_df)
                
                fig = px.bar(teacher_agg, x='Teacher', y='Growth (%)', color='Growth (%)',
                             color_continuous_scale='RdYlGn', title="Average Growth by Teacher")
                st.plotly_chart(fig, use_container_width=True)

        # --- 3. View By Grade Level ---
        elif view_option == "By Grade Level":
            st.subheader("Average Growth by Grade Level")
            
            if not filtered_df.empty:
                grade_agg = filtered_df.groupby(['Grade Level', 'Subject']).agg({
                    '% Score_pre': 'mean',
                    '% Score_post': 'mean',
                    'Growth (%)': 'mean',
                    'Student Name': 'count'
                }).reset_index().rename(columns={'Student Name': 'Student Count'})
                
                styled_grade_df = grade_agg.style.background_gradient(subset=['Growth (%)'], cmap='RdYlGn').format(num_format)
                st.dataframe(styled_grade_df)
                
                fig = px.bar(grade_agg, x='Grade Level', y='Growth (%)', color='Subject', barmode='group',
                             title="Average Growth by Grade Level & Subject")
                st.plotly_chart(fig, use_container_width=True)

else:
    st.info("Please upload both the Pretest and Posttest files from the main window to begin.")
