import streamlit as st
import pandas as pd
import plotly.express as px
import re

# --- Configure Page ---
st.set_page_config(page_title="Student Growth Analysis", layout="wide")
st.title("📊 Student Growth Analysis Tool")
st.markdown("Upload Pretest and Posttest CSV reports to analyze student growth in Math and Reading.")

# --- Sidebar Settings ---
st.sidebar.header("Data Settings")
ignore_writing = st.sidebar.checkbox(
    "Ignore Pretest Writing Prompt", 
    value=True, 
    help="Automatically detects and removes the final question of the pretest if it is a writing prompt or an extra question, recalculating the student's score without it."
)

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

def categorize_growth(val):
    if pd.isna(val):
        return "Unknown"
    if val < 0:
        return "Negative (< 0%)"
    elif val == 0:
        return "Zero (0%)"
    elif val > 0 and val <= 10:
        return "Low Positive (1-10%)"
    else:
        return "High Positive (> 10%)"

def style_growth_col(s):
    # Applies exact colors to the dataframe column
    colors = []
    for val in s:
        if pd.isna(val):
            colors.append('')
        elif val < 0:
            colors.append('background-color: #ffcccc; color: #900;') # Red
        elif val == 0:
            colors.append('background-color: #ffe5b4; color: #960;') # Orange
        elif val > 0 and val <= 10:
            colors.append('background-color: #ffffcc; color: #880;') # Yellow
        else:
            colors.append('background-color: #ccffcc; color: #080;') # Green
    return colors

def preprocess_data(df, is_pretest=False):
    """Formats the dataframe depending on which CSV version was uploaded."""
    df.columns = df.columns.str.strip()
    
    if 'Test Raw Score' in df.columns and 'Test Max Score' in df.columns:
        if 'Student Name' not in df.columns and 'Student' in df.columns:
            df = df.rename(columns={'Student': 'Student Name'})
            
        # Feature: Ignore Writing Prompt in Pretest
        if is_pretest and ignore_writing and 'Question #' in df.columns:
            # Find the max question number for each student
            max_q_per_student = df.groupby('Student Name')['Question #'].transform('max')
            median_max_q = df.groupby('Student Name')['Question #'].max().median()
            
            # Check if the row is the student's last question
            is_last_q = df['Question #'] == max_q_per_student
            # Check if 'writing' exists in any string column for this row
            is_writing_str = df.astype(str).apply(lambda x: x.str.contains('writing', case=False, na=False)).any(axis=1)
            
            # Drop if it is the last question AND (contains 'writing' OR is an extra question beyond the class median)
            drop_mask = is_last_q & (is_writing_str | (df['Question #'] > median_max_q))
            df = df[~drop_mask].copy()
            
            # Recalculate raw and max scores using ONLY the remaining rows
            recalc = df.groupby(['Student Name']).agg(
                Calc_Raw=('Raw Score', 'sum'),
                Calc_Max=('Max Score', 'sum')
            ).reset_index()
            
            df = df.drop_duplicates(subset=['Student Name']).copy()
            df = df.merge(recalc, on=['Student Name'])
            df['% Score'] = (df['Calc_Raw'] / df['Calc_Max']) * 100
        else:
            df = df.drop_duplicates(subset=['Student Name', 'Test Raw Score', 'Test Max Score']).copy()
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
    pre_df = preprocess_data(pre_df, is_pretest=True)
    post_df = preprocess_data(post_df, is_pretest=False)

    # Merge
    merge_cols = ['Student Name', 'Teacher', 'School']
    merged_df = pd.merge(pre_df, post_df, on=merge_cols, suffixes=('_pre', '_post'))
    
    if merged_df.empty:
        st.error("No matching students found between the Pretest and Posttest files based on Student Name and Teacher.")
    else:
        # Calculate Growth & Categories
        merged_df['Growth (%)'] = merged_df['% Score_post'] - merged_df['% Score_pre']
        merged_df['Growth Category'] = merged_df['Growth (%)'].apply(categorize_growth)
        merged_df['Subject'] = merged_df['ProgramInfo_post'].apply(extract_subject)
        merged_df['Grade Level'] = merged_df['ProgramInfo_post'].apply(extract_grade)
        
        # --- Sidebar Filters ---
        st.sidebar.divider()
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
        
        # --- Success Message & Export Button ---
        col_success, col_export = st.columns([3, 1])
        with col_success:
            st.success(f"Data successfully merged! Analyzing {len(filtered_df)} student records.")
        with col_export:
            csv_export = filtered_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Comparison Data (CSV)",
                data=csv_export,
                file_name='student_growth_comparison.csv',
                mime='text/csv',
            )
        
        # --- Shared Formatting Dictionary & Colors ---
        num_format = {
            '% Score_pre': "{:.1f}", 
            '% Score_post': "{:.1f}", 
            'Growth (%)': "{:.1f}"
        }
        
        chart_color_map = {
            "Negative (< 0%)": "#EF553B",      # Red
            "Zero (0%)": "#FFA15A",            # Orange
            "Low Positive (1-10%)": "#FECB52", # Yellow
            "High Positive (> 10%)": "#00CC96" # Green
        }
        
        category_order = ["Negative (< 0%)", "Zero (0%)", "Low Positive (1-10%)", "High Positive (> 10%)"]
        
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
            
            # Apply 4-color custom styling
            styled_student_df = student_view[display_cols].style.apply(style_growth_col, subset=['Growth (%)']).format(num_format)
            st.dataframe(styled_student_df)
            
            if not student_view.empty:
                fig = px.bar(student_view, x='Student Name', y='Growth (%)', color='Growth Category', 
                             color_discrete_map=chart_color_map, 
                             category_orders={"Growth Category": category_order},
                             title="Growth Percentage per Student")
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
                
                teacher_agg['Growth Category'] = teacher_agg['Growth (%)'].apply(categorize_growth)
                
                styled_teacher_df = teacher_agg.drop(columns=['Growth Category']).style.apply(style_growth_col, subset=['Growth (%)']).format(num_format)
                st.dataframe(styled_teacher_df)
                
                fig = px.bar(teacher_agg, x='Teacher', y='Growth (%)', color='Growth Category',
                             color_discrete_map=chart_color_map, 
                             category_orders={"Growth Category": category_order},
                             title="Average Growth by Teacher")
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
                
                grade_agg['Growth Category'] = grade_agg['Growth (%)'].apply(categorize_growth)
                
                styled_grade_df = grade_agg.drop(columns=['Growth Category']).style.apply(style_growth_col, subset=['Growth (%)']).format(num_format)
                st.dataframe(styled_grade_df)
                
                fig = px.bar(grade_agg, x='Grade Level', y='Growth (%)', color='Growth Category', barmode='group',
                             color_discrete_map=chart_color_map, 
                             category_orders={"Growth Category": category_order},
                             title="Average Growth by Grade Level & Subject")
                st.plotly_chart(fig, use_container_width=True)

else:
    st.info("Please upload both the Pretest and Posttest files from the main window to begin.")
