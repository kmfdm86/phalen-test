import streamlit as st
import pandas as pd
import plotly.express as px
import re

# --- Configure Page ---
st.set_page_config(page_title="Student Growth Analysis", layout="wide")
st.title("📊 Student Growth Analysis Tool")
st.markdown("Upload Pretest and Posttest CSV reports to analyze student growth in Math and Reading.")

# --- Helper Functions ---
def extract_grade(program_name):
    # Attempts to extract grade level from the Program or Assessment name (e.g. "Grade 1")
    if pd.isna(program_name):
        return "Unknown"
    match = re.search(r'Grade\s*([Kk0-9])', str(program_name), re.IGNORECASE)
    if match:
        grade = match.group(1).upper()
        return "K" if grade == "K" else f"Grade {grade}"
    return "Unknown"

def extract_subject(program_name):
    # Simplistic subject check based on keywords in Program
    program_lower = str(program_name).lower()
    if 'math' in program_lower:
        return 'Math'
    elif 'reading' in program_lower or 'literacy' in program_lower:
        return 'Reading'
    return 'Other'

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
    
    # Standardize column names (strip whitespace)
    pre_df.columns = pre_df.columns.str.strip()
    post_df.columns = post_df.columns.str.strip()

    # We need a primary key to merge on, 'Student ID' is perfect.
    # We will keep suffixes _pre and _post for overlapping columns.
    merged_df = pd.merge(
        pre_df, 
        post_df, 
        on=['Student ID', 'Student Name', 'Teacher', 'School', 'Class'], 
        suffixes=('_pre', '_post')
    )
    
    if merged_df.empty:
        st.error("No matching students found between the Pretest and Posttest files based on Student ID.")
    else:
        # --- Data Processing ---
        # Calculate Growth
        merged_df['Growth (%)'] = merged_df['% Score_post'] - merged_df['% Score_pre']
        
        # Extract Subject and Grade based on Posttest program (or pretest)
        merged_df['Subject'] = merged_df['Program_post'].apply(extract_subject)
        merged_df['Grade Level'] = merged_df['Program_post'].apply(extract_grade)
        
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
        
        # Apply filters
        filtered_df = merged_df[
            (merged_df['Subject'].isin(subject_filter)) & 
            (merged_df['Grade Level'].isin(grade_filter))
        ]
        
        st.success(f"Data successfully merged! Analyzing {len(filtered_df)} student records.")
        
        # --- Navigation / View Selection ---
        view_option = st.radio("Select View:", ("By Student", "By Teacher", "By Grade Level"), horizontal=True)
        
        st.divider()
        
        # --- 1. View By Student ---
        if view_option == "By Student":
            st.subheader("Student Growth")
            teacher_filter = st.selectbox("Optional: Filter by Teacher", ["All"] + list(filtered_df['Teacher'].unique()))
            
            student_view = filtered_df.copy()
            if teacher_filter != "All":
                student_view = student_view[student_view['Teacher'] == teacher_filter]
                
            display_cols = ['Student Name', 'Student ID', 'Grade Level', 'Subject', 'Teacher', '% Score_pre', '% Score_post', 'Growth (%)']
            st.dataframe(student_view[display_cols].style.background_gradient(subset=['Growth (%)'], cmap='RdYlGn'))
            
            # Chart
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
                    'Student ID': 'count'
                }).reset_index().rename(columns={'Student ID': 'Student Count'})
                
                # Round numbers
                teacher_agg = teacher_agg.round(2)
                
                st.dataframe(teacher_agg.style.background_gradient(subset=['Growth (%)'], cmap='RdYlGn'))
                
                # Chart
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
                    'Student ID': 'count'
                }).reset_index().rename(columns={'Student ID': 'Student Count'})
                
                # Round numbers
                grade_agg = grade_agg.round(2)
                
                st.dataframe(grade_agg.style.background_gradient(subset=['Growth (%)'], cmap='RdYlGn'))
                
                # Chart
                fig = px.bar(grade_agg, x='Grade Level', y='Growth (%)', color='Subject', barmode='group',
                             title="Average Growth by Grade Level & Subject")
                st.plotly_chart(fig, use_container_width=True)

else:
    st.info("Please upload both the Pretest and Posttest files from the sidebar to begin.")