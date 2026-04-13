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

# --- UPDATED: Smarter Auto-Detect Engine ---
def detect_subject_and_grade(df, filename):
    subject = "math" # Default
    grade = "K"      # Default
    
    # 1. Detect Subject from the file name
    filename_lower = filename.lower()
    if 'reading' in filename_lower:
        subject = "reading"
    elif 'math' in filename_lower:
        subject = "math"
        
    # 2. Detect Grade from the "Class" column (Used in the NEW format)
    if 'Class' in df.columns:
        classes = df['Class'].dropna().astype(str).unique()
        for c in classes:
            # Looks for things like "4th Grade", "1st Grade", "K"
            match = re.search(r'([K1-9])(st|nd|rd|th)?\s*Grade', c, re.IGNORECASE)
            if match:
                grade = match.group(1).upper()
                return subject, grade

    # 3. Backup: Detect from the standards (Used in the OLD format)
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

st.subheader("Upload Student Data")
student_file = st.file_uploader("Upload Student Results (CSV)", type="csv")

if student_file:
    raw_student_df = pd.read_csv(student_file)
    
    # Run the new auto-detect engine, passing in the file name as well
    detected_subject, detected_grade = detect_subject_and_grade(raw_student_df, student_file.name)
    pretty_grade = grade_names.get(detected_grade, f"Grade {detected_grade}")
    
    st.success(f"File uploaded successfully! Auto-detected **{pretty_grade} {detected_subject.capitalize()}**. Generating report...")
    
    file_to_load = f"{detected_subject}_item_analysis_{detected_grade}.csv"
    
    try:
        item_df = load_item_analysis(file_to_load)
        item_df['Question_ID'] = 'Q' + item_df['Question_ID'].astype(str)
        
        # --- NEW: Adapt to either the OLD (Wide) or NEW (Long) file formats ---
        if 'Question #' in raw_student_df.columns and 'Student' in raw_student_df.columns:
            # Process the NEW Format
            student_df = raw_student_df[['Student', 'Question #', 'Raw Score']].copy()
            student_df = student_df.rename(columns={
                'Student': 'Student_Name', 
                'Question #': 'Question_ID', 
                'Raw Score': 'Score'
            })
            student_df['Question_ID'] = 'Q' + student_df['Question_ID'].astype(str)
            student_df['Score'] = pd.to_numeric(student_df['Score'], errors='coerce').fillna(0)
            
        else:
            # Process the OLD Format
            q_cols = [col for col in raw_student_df.columns if col.startswith('Q') and col[1:].isdigit()]
            columns_to_keep = ['Name'] + q_cols
            
            student_data = raw_student_df[columns_to_keep].dropna(subset=['Name', 'Q1'])
            student_data = student_data[~student_data['Name'].str.contains('Total|Name|Class|Assignment|Standard', na=False, case=False)]
            student_data = student_data.rename(columns={'Name': 'Student_Name'})
            
            student_df = pd.melt(
                student_data, 
                id_vars=['Student_Name'], 
                value_vars=q_cols, 
                var_name='Question_ID', 
                value_name='Score'
            )
            
            def parse_score(score_str):
                try:
                    if '/' in str(score_str):
                        achieved, total = map(float, str(score_str).split('/'))
                        return 1 if achieved == total else 0
                    else:
                        return float(score_str)
                except:
                    return score_str
                    
            student_df['Score'] = student_df['Score'].apply(parse_score)
        
        # --- GENERATE REPORT ---
        combined_data = pd.merge(student_df, item_df, on="Question_ID")
        missed_questions = combined_data[combined_data['Score'] == 0].copy()
        
        missed_questions['Lesson_Number'] = missed_questions['Lesson_Number'].astype(str).str.split(',')
        missed_questions = missed_questions.explode('Lesson_Number')
        missed_questions['Lesson_Number'] = missed_questions['Lesson_Number'].str.strip()
        
        missed_questions['Lesson_Number'] = pd.to_numeric(missed_questions['Lesson_Number'], errors='coerce')
        missed_questions = missed_questions.dropna(subset=['Lesson_Number'])
        
        intervention_report = missed_questions.groupby('Lesson_Number')['Student_Name'].unique().apply(lambda x: ', '.join(sorted(x))).reset_index()
        intervention_report = intervention_report.sort_values(by='Lesson_Number')
        
        intervention_report['Lesson_Number'] = intervention_report['Lesson_Number'].astype(int)
        intervention_report.columns = ['Lesson Number', 'Students Needing Support']
        
        st.subheader("Intervention Report")
        
        if intervention_report.empty:
            st.info("Great news! No students missed questions tied to these lessons based on the uploaded data.")
        else:
            st.dataframe(intervention_report, use_container_width=True, hide_index=True)
            
            csv_export = intervention_report.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Report as CSV",
                data=csv_export,
                file_name=f"{detected_subject}_interventions_{pretty_grade.replace(' ', '_')}.csv",
                mime="text/csv",
            )
            
    except FileNotFoundError:
        st.error(f"System Error: The master item analysis key for {pretty_grade} {detected_subject.capitalize()} ({file_to_load}) is missing. Please contact the administrator.")
    except Exception as e:
        st.error(f"Error processing files: {e}. Please ensure your files contain the correct formatting.")
