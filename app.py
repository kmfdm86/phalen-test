import streamlit as st
import pandas as pd
import plotly.express as px
import re

# --- Configure Page ---
st.set_page_config(page_title="Student Growth Analysis", layout="wide")
st.title("📊 Student Growth Analysis Tool")
st.markdown("Upload a single comprehensive CSV report. The tool will automatically pair students by looking for the words **'pretest'** and **'posttest'** in the Assessment column.")

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

def preprocess_single_file(df):
    """Formats the dataframe and handles question-level vs flat reporting."""
    df.columns = df.columns.str.strip()
    
    if 'School' not in df.columns:
        df['School'] = 'Unknown School'
        
    if 'Test Raw Score' in df.columns and 'Test Max Score' in df.columns:
        if 'Student Name' not in df.columns and 'Student' in df.columns:
            df = df.rename(columns={'Student': 'Student Name'})
            
        # Deduplicate to get one row per student per assessment
        df = df.drop_duplicates(subset=['Student Name', 'Assessment', 'Test Raw Score', 'Test Max Score']).copy()
        df['% Score'] = (df['Test Raw Score'] / df['Test Max Score']) * 100
        df['ProgramInfo'] = df['Class'].astype(str) + " " + df['School'].astype(str)
    else:
        if 'Program' in df.columns:
            df['ProgramInfo'] = df['Program']
        else:
            df['ProgramInfo'] = df['Class'].astype(str)
            
    return df

# --- File Uploader ---
uploaded_file = st.file_uploader("Upload Assessment Data (CSV)", type=['csv'])

if uploaded_file:
    # Load and Preprocess Data
    raw_df = pd.read_csv(uploaded_file)
    df = preprocess_single_file(raw_df)
    
    # Clean up dates and scores
    if 'Submit Date' in df.columns:
        df['Submit Date'] = pd.to_datetime(df['Submit Date'], errors='coerce')
    df = df.dropna(subset=['% Score'])
    
    # Extract Subject and Grade Level for grouping
    df['Subject'] = df['ProgramInfo'].apply(extract_subject)
    df['Grade Level'] = df['ProgramInfo'].apply(extract_grade)
    
    # Enforce Assessment column check
    if 'Assessment' not in df.columns:
        st.error("The uploaded file must contain an 'Assessment' column to identify pretests and posttests.")
    else:
        # Find Pretests and Posttests using string matching
        pretest_mask = df['Assessment'].astype(str).str.contains('pretest', case=False, na=False)
        posttest_mask = df['Assessment'].astype(str).str.contains('posttest', case=False, na=False)
        
        pre_df_raw = df[pretest_mask].copy()
        post_df_raw = df[posttest_mask].copy()
        
        if pre_df_raw.empty:
            st.error("Could not find any records containing the word 'pretest' in the Assessment column.")
        elif post_df_raw.empty:
            st.error("Could not find any records containing the word 'posttest' in the Assessment column.")
        else:
            # Sort by date so if a student took the test twice, we use the most recent submission
            if 'Submit Date' in df.columns:
                pre_df_raw = pre_df_raw.sort_values('Submit Date', na_position='first')
                post_df_raw = post_df_raw.sort_values('Submit Date', na_position='first')
            
            # Group by our core identifiers
            group_cols = ['Student Name', 'Teacher', 'School', 'Subject', 'Grade Level']
            
            # Use the latest record for each student
            pre_df = pre_df_raw.groupby(group_cols).last().reset_index()
            post_df = post_df_raw.groupby(group_cols).last().reset_index()
            
            pre_df = pre_df.rename(columns={'% Score': '% Score_pre'})
            post_df = post_df.rename(columns={'% Score': '% Score_post'})
            
            # Merge them together (inner join requires them to be in both datasets)
            merged_df = pd.merge(
                pre_df[group_cols + ['% Score_pre']], 
                post_df[group_cols + ['% Score_post']], 
                on=group_cols
            )
            
            if merged_df.empty:
                st.warning("Found pretests and posttests in the file, but could not match any students who took both based on Name, Teacher, and School.")
            else:
                # Calculate Growth & Categories
                merged_df['Growth (%)'] = merged_df['% Score_post'] - merged_df['% Score_pre']
                merged_df['Growth Category'] = merged_df['Growth (%)'].apply(categorize_growth)
                
                # --- Sidebar Filters ---
                st.sidebar.divider()
                st.sidebar.header("Filter Data")
                
                school_filter = st.sidebar.multiselect(
                    "Select School", 
                    options=sorted(merged_df['School'].unique()), 
                    default=sorted(merged_df['School'].unique())
                )
                
                grade_filter = st.sidebar.multiselect(
                    "Select Grade Level", 
                    options=sorted(merged_df['Grade Level'].unique()), 
                    default=sorted(merged_df['Grade Level'].unique())
                )
                
                subject_filter = st.sidebar.multiselect(
                    "Select Subject", 
                    options=merged_df['Subject'].unique(), 
                    default=merged_df['Subject'].unique()
                )
                
                temp_df = merged_df[
                    (merged_df['School'].isin(school_filter)) &
                    (merged_df['Grade Level'].isin(grade_filter)) &
                    (merged_df['Subject'].isin(subject_filter))
                ]
                
                teacher_filter = st.sidebar.multiselect(
                    "Select Teacher", 
                    options=sorted(temp_df['Teacher'].unique()), 
                    default=sorted(temp_df['Teacher'].unique())
                )
                
                filtered_df = temp_df[temp_df['Teacher'].isin(teacher_filter)]
                
                # --- Success Message & Export Button ---
                col_success, col_export = st.columns([3, 1])
                with col_success:
                    st.success(f"Data successfully merged! Analyzed {len(filtered_df)} student records with matching pre/post tests.")
                with col_export:
                    csv_export = filtered_df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Download Filtered Data (CSV)",
                        data=csv_export,
                        file_name='student_growth_filtered.csv',
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
                view_option = st.radio("Select View:", ("By Student", "By Teacher", "By Grade Level", "By School"), horizontal=True)
                st.divider()
                
                # --- 1. View By Student ---
                if view_option == "By Student":
                    st.subheader("Student Growth")
                    
                    display_cols = ['Student Name', 'School', 'Grade Level', 'Subject', 'Teacher', '% Score_pre', '% Score_post', 'Growth (%)']
                    styled_student_df = filtered_df[display_cols].style.apply(style_growth_col, subset=['Growth (%)']).format(num_format)
                    st.dataframe(styled_student_df, use_container_width=True)
                    
                    if not filtered_df.empty:
                        if len(filtered_df) > 100:
                            st.warning("Chart hidden: Too many students selected. Please use the sidebar filters to narrow down the list to fewer than 100 students for charting.")
                        else:
                            fig = px.bar(filtered_df, x='Student Name', y='Growth (%)', color='Growth Category', 
                                         color_discrete_map=chart_color_map, 
                                         category_orders={"Growth Category": category_order},
                                         title="Growth Percentage per Student",
                                         hover_data=['School', 'Teacher', 'Grade Level'])
                            st.plotly_chart(fig, use_container_width=True)

                # --- 2. View By Teacher ---
                elif view_option == "By Teacher":
                    st.subheader("Average Growth by Teacher")
                    
                    if not filtered_df.empty:
                        teacher_agg = filtered_df.groupby(['Teacher', 'School']).agg({
                            '% Score_pre': 'mean',
                            '% Score_post': 'mean',
                            'Growth (%)': 'mean',
                            'Student Name': 'count'
                        }).reset_index().rename(columns={'Student Name': 'Student Count'})
                        
                        teacher_agg['Growth Category'] = teacher_agg['Growth (%)'].apply(categorize_growth)
                        styled_teacher_df = teacher_agg.drop(columns=['Growth Category']).style.apply(style_growth_col, subset=['Growth (%)']).format(num_format)
                        st.dataframe(styled_teacher_df, use_container_width=True)
                        
                        fig = px.bar(teacher_agg, x='Teacher', y='Growth (%)', color='Growth Category',
                                     color_discrete_map=chart_color_map, 
                                     category_orders={"Growth Category": category_order},
                                     title="Average Growth by Teacher",
                                     hover_data=['School', 'Student Count'])
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
                        st.dataframe(styled_grade_df, use_container_width=True)
                        
                        fig = px.bar(grade_agg, x='Grade Level', y='Growth (%)', color='Growth Category', barmode='group',
                                     color_discrete_map=chart_color_map, 
                                     category_orders={"Growth Category": category_order},
                                     title="Average Growth by Grade Level & Subject",
                                     hover_data=['Student Count'])
                        st.plotly_chart(fig, use_container_width=True)
                        
                # --- 4. View By School ---
                elif view_option == "By School":
                    st.subheader("Average Growth by School")
                    
                    if not filtered_df.empty:
                        school_agg = filtered_df.groupby('School').agg({
                            '% Score_pre': 'mean',
                            '% Score_post': 'mean',
                            'Growth (%)': 'mean',
                            'Student Name': 'count'
                        }).reset_index().rename(columns={'Student Name': 'Student Count'})
                        
                        school_agg['Growth Category'] = school_agg['Growth (%)'].apply(categorize_growth)
                        styled_school_df = school_agg.drop(columns=['Growth Category']).style.apply(style_growth_col, subset=['Growth (%)']).format(num_format)
                        st.dataframe(styled_school_df, use_container_width=True)
                        
                        fig = px.bar(school_agg, x='School', y='Growth (%)', color='Growth Category',
                                     color_discrete_map=chart_color_map, 
                                     category_orders={"Growth Category": category_order},
                                     title="Average Growth by School",
                                     hover_data=['Student Count'])
                        st.plotly_chart(fig, use_container_width=True)

else:
    st.info("Please upload your combined Assessment CSV file to begin.")
