import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="Student Intervention Generator", layout="centered")
st.title("📊 Student Intervention Report Generator")
st.write("Upload your student test results below. The system will automatically detect the subject and grade level to generate your targeted intervention list.")

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

def detect_subject_and_grade(df, filename):
    subject, grade = "math", "K" # Defaults
    
    filename_lower = filename.lower()
    if 'reading' in filename_lower:
        subject = "reading"
    elif 'math' in filename_lower:
        subject = "math"
        
    if 'Class' in df.columns:
        classes = df['Class'].dropna().astype(str).unique()
        for c in classes:
            match = re.search(r'([K1-9])(st|nd|rd|th)?\s*Grade', c, re.IGNORECASE)
            if match:
                return subject, match.group(1).upper()

    if 'Name' in df.columns:
        first_col = df.iloc[:, 0].dropna().astype(str)
        for val in first_col:
            val = val.strip()
            match_reading = re.match(r"^(RL|RI|RF|W|SL)\.?([K1-9])", val, re.IGNORECASE)
            if match_reading:
                return "reading", match_reading.group(2).upper()
                
            match_math = re.match(r"^([K1-9])\.(OA|NC|MD)", val, re.IGNORECASE)
            if match_math:
                return "math", match_math.group(1).upper()

    return subject, grade

# --- NEW: Reusable Data Cleaning Function ---
# This ensures both Pre and Post tests get the exact same column names
def clean_student_data(raw_df):
    if 'Question #' in raw_df.columns and 'Student' in raw_df.columns:
        # Process the NEW Format (Long)
        df = raw_df[['Student', 'Question #', 'Raw Score']].copy()
        df = df.rename(columns={'Student': 'Student_Name', 'Question #': 'Question_ID', 'Raw Score': 'Score'})
        df['Question_ID'] = 'Q' + df['Question_ID'].astype(str)
        df['Score'] = pd.to_numeric(df['Score'], errors='coerce').fillna(0)
        return df
    else:
        # Process the OLD Format (Wide)
        q_cols = [col for col in raw_df.columns if col.startswith('Q') and col[1:].isdigit()]
        columns_to_keep = ['Name'] + q_cols
        
        df = raw_df[columns_to_keep].dropna(subset=['Name', 'Q1'])
        df = df[~df['Name'].str.contains('Total|Name|Class|Assignment|Standard', na=False, case=False)]
        df = df.rename(columns={'Name': 'Student_Name'})
        
        df = pd.melt(df, id_vars=['Student_Name'], value_vars=q_cols, var_name='Question_ID', value_name='Score')
        
        def parse_score(score_str):
            try:
                if '/' in str(score_str):
                    achieved, total = map(float, str(score_str).split('/'))
                    return 1 if achieved == total else 0
                else:
                    return float(score_str)
            except:
                return score_str
                
        df['Score'] = df['Score'].apply(parse_score)
        return df

# Create TWO file uploaders side-by-side
col1, col2 = st.columns(2)
with col1:
    pre_file = st.file_uploader("1. Upload Pretest (CSV)", type="csv")
with col2:
    post_file = st.file_uploader("2. Upload Posttest (CSV)", type="csv")

if pre_file and post_file:
    raw_pre_df = pd.read_csv(pre_file)
    raw_post_df = pd.read_csv(post_file)
    
    # Auto-Detect from the Posttest file
    detected_subject, detected_grade = detect_subject_and_grade(raw_post_df, post_file.name)
    pretty_grade = grade_names.get(detected_grade, f"Grade {detected_grade}")
    
    st.success(f"Files uploaded! Auto-detected **{pretty_grade} {detected_subject.capitalize()}**. Generating report...")
    
    file_to_load = f"{detected_subject}_item_analysis_{detected_grade}.csv"
    
    try:
        item_df = load_item_analysis(file_to_load)
        item_df['Question_ID'] = 'Q' + item_df['Question_ID'].astype(str)
        
        # 1. Clean BOTH datasets using the new unified function
        clean_pre_df = clean_student_data(raw_pre_df)
        clean_post_df = clean_student_data(raw_post_df)
        
        # 2. Merge Pretest and Posttest safely
        # Now they both securely have 'Student_Name' and 'Question_ID' columns!
        merged_student_df = pd.merge(
            clean_pre_df, 
            clean_post_df, 
            on=['Student_Name', 'Question_ID'], 
            suffixes=('_pre', '_post')
        )
        
        # 3. Add the Item Analysis Key to the merged data
        combined_data = pd.merge(merged_student_df, item_df, on="Question_ID")
        
        # 4. Filter for students who still missed the question on the POSTTEST
        missed_questions = combined_data[combined_data['Score_post'] == 0].copy()
        
        missed_questions['Lesson_Number'] = missed_questions['Lesson_Number'].astype(str).str.split(',')
        missed_questions = missed_questions.explode('Lesson_Number')
        missed_questions['Lesson_Number'] = missed_questions['Lesson_Number'].str.strip()
        
        missed_questions['Lesson_Number'] = pd.to_numeric(missed_questions['Lesson_Number'], errors='coerce')
        missed_questions = missed_questions.dropna(subset=['Lesson_Number'])
        
        intervention_report = missed_questions.groupby('Lesson_Number')['Student_Name'].unique().apply(lambda x: ', '.join(sorted(x))).reset_index()
        intervention_report = intervention_report.sort_values(by='Lesson_Number')
        
        intervention_report['Lesson_Number'] = intervention_report['Lesson_Number'].astype(int)
        intervention_report.columns = ['Lesson Number', 'Students Needing Support']
        
        st.subheader("Post-Test Intervention Report")
        st.write("These students answered incorrectly on the **Posttest** and need targeted instruction for these lessons:")
        
        if intervention_report.empty:
            st.info("Great news! No students missed questions tied to these lessons on the posttest.")
        else:
            st.dataframe(intervention_report, use_container_width=True, hide_index=True)
            
            csv_export = intervention_report.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Report as CSV",
                data=csv_export,
                file_name=f"{detected_subject}_posttest_interventions_{pretty_grade.replace(' ', '_')}.csv",
                mime="text/csv",
            )
            
    except FileNotFoundError:
        st.error(f"System Error: The master item analysis key for {pretty_grade} {detected_subject.capitalize()} ({file_to_load}) is missing. Please contact the administrator.")
    except Exception as e:
        st.error(f"Error processing files: {e}. Please ensure both files are standard testing exports.")
