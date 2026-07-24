import streamlit as st
import streamlit.components.v1 as components
import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
from fpdf import FPDF

# ---------------------------------------------------------
# Global Configurations
# ---------------------------------------------------------
MAX_THREADS = 10

# List of optional/4th subject keywords to ignore during fail calculation
OPTIONAL_SUBJECT_KEYWORDS = [
    "agriculture", "agricultural", "higher math", "higher mathematics", 
    "home science", "computer", "biology", "physical education"
]

def get_board_urls(exam_type, year):
    """Dynamically generate URLs for SSC and HSC based on selection."""
    exam_lower = exam_type.lower()
    if exam_lower == "ssc":
        institute_url = f"https://result.dinajpurboard.gov.bd/ssc_result_{year}/search/search.php"
        student_action_url = f"https://result.dinajpurboard.gov.bd/ssc_result_{year}/search/search_student.php"
    else:  # HSC
        # HTML Source Code অনুযায়ী HSC-এর Institute POST রিকোয়েস্ট search.php এ যায়
        institute_url = f"https://result.dinajpurboard.gov.bd/hsc_result{year}/search/search.php"
        student_action_url = f"https://result.dinajpurboard.gov.bd/hsc_result{year}/search/each.php"
        
    return institute_url, student_action_url

def sanitize_filename(name):
    clean_name = re.sub(r'[^\w\s-]', '', name)
    return re.sub(r'[-\s]+', '_', clean_name).strip('_')

# ---------------------------------------------------------
# Streamlit Page Configuration
# ---------------------------------------------------------
st.set_page_config(
    page_title="Dinajpur Board Result Check",
    page_icon="🎓",
    layout="wide"
)

# Custom Styling & Badges
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button {
        background-color: #1E88E5; color: white; border-radius: 8px;
        padding: 10px 24px; font-size: 16px; border: none; width: 100%;
        font-weight: bold;
    }
    .stButton>button:hover { background-color: #1565C0; color: white; }
    h1 { color: #1A237E; text-align: center; font-family: 'Helvetica Neue', sans-serif; font-weight: bold; }
    .developer-badge {
        background: linear-gradient(135deg, #1E88E5, #1565C0);
        color: white; padding: 8px 15px; border-radius: 20px;
        text-align: center; font-weight: bold; font-size: 14px;
        margin-top: 10px; margin-bottom: 20px;
        box-shadow: 0px 4px 6px rgba(0,0,0,0.1);
    }
    .developer-badge a {
        color: #ffffff !important;
        text-decoration: underline;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("<h1>🎓 Dinajpur Board Result Check System</h1>", unsafe_allow_html=True)
st.markdown("<div class='developer-badge'>✨ App Developed by: <a href='https://www.facebook.com/nonigopalrays' target='_blank'>Nonigopal Ray</a> ✨</div>", unsafe_allow_html=True)
st.write("---")

# ---------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------

def parse_institute_summary(raw_html, eiin_code):
    soup = BeautifulSoup(raw_html, 'html.parser')
    text_content = soup.get_text()
    
    info = {
        'EIIN': eiin_code,
        'Institute': 'Unknown Institute',
        'Thana/Upazilla': '-',
        'District': '-',
        'No. of Students Appeared': '-',
        'No. of Students Passed': '-',
        'No. of Students Failed': '-',
        'Percentage of Pass': '-',
        'No of GPA5': '-'
    }
    
    patterns = {
        'Institute': r'Institute\s*[:\-]\s*(.+)',
        'Thana/Upazilla': r'(?:Thana/Upazilla|Thana|Upazilla)\s*[:\-]\s*(.+)',
        'District': r'District\s*[:\-]\s*(.+)',
        'No. of Students Appeared': r'(?:No\.\s*of\s*Students\s*Appeared|Appeared)\s*[:\-]\s*(\d+)',
        'No. of Students Passed': r'(?:No\.\s*of\s*Students\s*Passed|Passed)\s*[:\-]\s*(\d+)',
        'Percentage of Pass': r'(?:Percentage\s*of\s*Pass|Pass\s*Rate)\s*[:\-]\s*([\d\.]+)',
        'No of GPA5': r'(?:No\s*of\s*GPA5|GPA5|GPA\s*5)\s*[:\-]\s*(\d+)'
    }
    
    for key, pattern in patterns.items():
        match = re.search(pattern, text_content, re.IGNORECASE)
        if match:
            clean_val = match.group(1).split('\n')[0].strip()
            info[key] = clean_val
            
    try:
        app = int(info['No. of Students Appeared'])
        pas = int(info['No. of Students Passed'])
        info['No. of Students Failed'] = str(app - pas)
    except Exception:
        pass

    return info


def fetch_student_detail(roll, action_url, session_headers, initial_status="-"):
    payload = {'roll_no': str(roll), 'regi_no': '', 'submit': 'Submit'}
    
    try:
        response = requests.post(action_url, data=payload, headers=session_headers, timeout=12)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            if soup.find(text=lambda t: t and "no result found" in str(t).lower()):
                return {
                    "Group": "-", "Roll": str(roll), "Name": "No Result Found",
                    "GPA": "F", "Total Mark": "-", "Subject Grade": "-"
                }
            
            name = "Not Found"
            group = "Not Found"
            result_val = initial_status
            total_mark_val = "-"
            
            all_tds = soup.find_all('td')
            for i, td in enumerate(all_tds):
                txt = td.text.strip().lower()
                
                if "name" in txt and i + 1 < len(all_tds) and name == "Not Found":
                    possible_name = all_tds[i+1].text.strip()
                    if len(possible_name) > 2 and not possible_name.isdigit():
                        name = possible_name
                
                if "group" in txt and i + 1 < len(all_tds) and group == "Not Found":
                    possible_group = all_tds[i+1].text.strip()
                    if possible_group: group = possible_group
                
                if "result" in txt and i + 1 < len(all_tds):
                    val = all_tds[i+1].text.strip()
                    if val: result_val = val
                        
                if "total mark" in txt and i + 1 < len(all_tds):
                    val = all_tds[i+1].text.strip()
                    if val: total_mark_val = val
            
            subject_grades = []
            compulsory_failed_count = 0
            
            for i, td in enumerate(all_tds):
                txt = td.text.strip()
                if txt in ['A+', 'A', 'A-', 'B', 'C', 'D', 'F']:
                    if i - 1 >= 0:
                        sub = all_tds[i-1].text.strip()
                        if len(sub) > 2: 
                            subject_grades.append(f"{sub}:{txt}")
                            if txt == 'F':
                                sub_lower = sub.lower()
                                is_optional = any(opt_key in sub_lower for opt_key in OPTIONAL_SUBJECT_KEYWORDS)
                                if not is_optional:
                                    compulsory_failed_count += 1
            
            if compulsory_failed_count > 0:
                result_val = f"F{compulsory_failed_count}"
            elif "PASSED" in result_val.upper() or "GPA=" in result_val.upper():
                match = re.search(r'\d+\.\d+|\d+', result_val)
                if match: result_val = match.group(0)
            
            grades_str = ", ".join(subject_grades) if subject_grades else "-"
            
            return {
                "Group": group,
                "Roll": str(roll),
                "Name": name,
                "GPA": result_val,
                "Total Mark": total_mark_val,
                "Subject Grade": grades_str
            }
        else:
            return {"Group": "-", "Roll": str(roll), "Name": "Server Error", "GPA": initial_status, "Total Mark": "-", "Subject Grade": "-"}
    except Exception:
        return {"Group": "-", "Roll": str(roll), "Name": "Connection Error", "GPA": initial_status, "Total Mark": "-", "Subject Grade": "-"}


# Custom PDF Class
class ColorPDF(FPDF):
    def __init__(self, exam_type="SSC", year="2026", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.exam_type = exam_type
        self.year = year

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(100, 100, 100)
        
        # Clickable URL in PDF Footer
        self.cell(25, 5, "App Developed by: ", align="L")
        self.set_text_color(0, 0, 255)
        self.set_font("Helvetica", "U", 8)
        self.cell(22, 5, "Nonigopal Ray", align="L", link="https://www.facebook.com/nonigopalrays")
        
        self.set_text_color(100, 100, 100)
        self.set_font("Helvetica", "I", 8)
        self.cell(93, 5, f" | Dinajpur Board {self.exam_type} {self.year} Result System", align="L")
        self.cell(0, 5, f"Page {self.page_no()}/{{nb}}", align="R")

    def draw_colored_grades(self, x, y, width, height, text):
        items = [i.strip() for i in text.split(',') if i.strip()]
        current_x = x + 1.2
        current_y = y + 1.0
        line_height = 3.0
        
        self.set_font("Helvetica", "", 6)
        
        for item in items:
            parts = item.split(':')
            if len(parts) == 2:
                sub, grade = parts[0], parts[1]
                item_str = f"{sub}:{grade}, "
            else:
                item_str = f"{item}, "
                grade = ""

            item_width = self.get_string_width(item_str)
            
            if current_x + item_width > x + width - 1.2:
                current_x = x + 1.2
                current_y += line_height
                if current_y + line_height > y + height + 2:
                    break

            if grade == 'F':
                self.set_text_color(211, 47, 47)
            else:
                self.set_text_color(0, 0, 0)

            self.text(current_x, current_y + 2.0, item_str)
            current_x += item_width

        self.set_text_color(0, 0, 0)


def calculate_required_height(pdf, width, text, line_h=3.0):
    """Calculates optimal row height using 6pt font size."""
    items = [i.strip() for i in text.split(',') if i.strip()]
    pdf.set_font("Helvetica", "", 6)
    
    current_x = 1.2
    lines = 1
    
    for item in items:
        item_str = f"{item}, "
        item_w = pdf.get_string_width(item_str)
        
        if current_x + item_w > width - 1.2:
            lines += 1
            current_x = 1.2 + item_w
        else:
            current_x += item_w
            
    return max(6, (lines * line_h) + 2.0)


def generate_pdf(dataframe, institute_info, exam_type, year):
    pdf = ColorPDF(exam_type=exam_type, year=year, orientation="L", unit="mm", format="A4")
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    pdf.set_font("Helvetica", "B", 13)
    inst_name = str(institute_info.get('Institute', 'BOARD OF INTERMEDIATE & SECONDARY EDUCATION, DINAJPUR'))
    pdf.cell(0, 6, inst_name[:85], ln=True, align="C")
    
    pdf.set_font("Helvetica", "", 8.5)
    pdf.cell(0, 5, f"BOARD OF INTERMEDIATE AND SECONDARY EDUCATION, DINAJPUR | {exam_type} {year}", ln=True, align="C")
    
    thana = str(institute_info.get('Thana/Upazilla', '-'))
    dist = str(institute_info.get('District', '-'))
    eiin = str(institute_info.get('EIIN', '-'))
    pdf.cell(0, 5, f"EIIN/ID: {eiin} | Thana/Upazilla: {thana} | District: {dist}", ln=True, align="C")
    pdf.ln(2)
    
    pdf.set_font("Helvetica", "B", 8.5)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(55, 6, f"Appeared: {institute_info.get('No. of Students Appeared', '-')}", border=1, align="C", fill=True)
    pdf.cell(55, 6, f"Passed: {institute_info.get('No. of Students Passed', '-')}", border=1, align="C", fill=True)
    pdf.cell(55, 6, f"Failed: {institute_info.get('No. of Students Failed', '-')}", border=1, align="C", fill=True)
    pdf.cell(55, 6, f"Pass Rate: {institute_info.get('Percentage of Pass', '-')}%", border=1, align="C", fill=True)
    pdf.cell(57, 6, f"GPA 5: {institute_info.get('No of GPA5', '-')}", border=1, align="C", fill=True)
    pdf.ln(8)
    
    widths = [22, 18, 55, 18, 20, 144]
    headers = ["Group", "Roll", "Name", "GPA", "Total Mark", "Subject Grade"]
    
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(220, 220, 220)
    for i, head in enumerate(headers):
        pdf.cell(widths[i], 7, head, border=1, align="C", fill=True)
    pdf.ln()
    
    for _, row in dataframe.iterrows():
        grp = str(row["Group"])[:12]
        roll = str(row["Roll"])[:8]
        name = str(row["Name"])[:32]
        gpa = str(row["GPA"])
        tm = str(row["Total Mark"])[:8]
        sg = str(row["Subject Grade"])
        
        row_h = calculate_required_height(pdf, widths[5], sg)
        
        if pdf.get_y() + row_h > 180:
            pdf.add_page()
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_fill_color(220, 220, 220)
            for i, head in enumerate(headers):
                pdf.cell(widths[i], 7, head, border=1, align="C", fill=True)
            pdf.ln()

        x = pdf.get_x()
        y = pdf.get_y()

        pdf.set_font("Helvetica", "", 8)
        pdf.cell(widths[0], row_h, grp, border=1, align="C")
        pdf.cell(widths[1], row_h, roll, border=1, align="C")
        
        is_gpa5 = (gpa == "5.00" or gpa == "5")
        is_fail = ('F' in gpa)

        if is_gpa5:
            pdf.set_text_color(25, 118, 210)
        elif is_fail:
            pdf.set_text_color(211, 47, 47)
        else:
            pdf.set_text_color(0, 0, 0)
            
        pdf.set_font("Helvetica", "B" if (is_gpa5 or is_fail) else "", 7.5)
        pdf.cell(widths[2], row_h, name, border=1, align="L")
        
        pdf.set_font("Helvetica", "B" if (is_gpa5 or is_fail) else "", 8)
        pdf.cell(widths[3], row_h, gpa, border=1, align="C")
        
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Helvetica", "", 8)
        pdf.cell(widths[4], row_h, tm, border=1, align="C")
        
        pdf.cell(widths[5], row_h, "", border=1)
        pdf.draw_colored_grades(x + sum(widths[:5]), y, widths[5], row_h, sg)
        
        pdf.set_xy(x, y + row_h)

    return pdf.output(dest="S")

# ---------------------------------------------------------
# User Input Section
# ---------------------------------------------------------
col_input, col_exam, col_year = st.columns([2.5, 1, 1])

with col_input:
    user_input = st.text_input(
        "📊 Enter EIIN Code or Roll Number(s):", 
        placeholder="Example EIIN: 125057  OR  Rolls: 123456, 123457"
    )

with col_exam:
    selected_exam = st.selectbox(
        "📝 Select Exam:",
        options=["SSC", "HSC"],
        index=0  # Default SSC
    )

with col_year:
    selected_year = st.selectbox(
        "📅 Select Year:",
        options=["2026", "2025", "2024"],
        index=0
    )

if st.button("Search Result 🚀"):
    raw_input = user_input.strip()
    if not raw_input:
        st.error("⚠️ Please enter a valid EIIN or Roll Number(s)!")
    else:
        institute_url, student_action_url = get_board_urls(selected_exam, selected_year)
        
        session = requests.Session()
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        extracted_pairs = []
        institute_info = {}
        is_eiin_search = False
        
        tokens = [t.strip() for t in re.split(r'[\s,]+', raw_input) if t.strip().isdigit()]
        first_candidate = tokens[0] if tokens else raw_input
        
        try:
            # HTML input field name="einn_no" 
            payload = {'einn_no': first_candidate, 'eiin_no': first_candidate, 'submit': 'Get Result'}
            res = session.post(institute_url, data=payload, headers=headers, timeout=12)
            raw_text = res.text
            
            pairs = re.findall(r'(\d{6,8})\s*\[([^\]]+)\]', raw_text)
            all_raw_rolls = re.findall(r'\b\d{6,8}\b', raw_text)
            all_raw_rolls = [r for r in all_raw_rolls if r != first_candidate]
            
            existing_rolls = set([p[0] for p in pairs])
            for r in all_raw_rolls:
                if r not in existing_rolls:
                    pairs.append((r, "F"))
                    existing_rolls.add(r)
            
            if pairs and "Institute" in raw_text:
                is_eiin_search = True
                extracted_pairs = pairs
                institute_info = parse_institute_summary(raw_text, first_candidate)
        except Exception:
            pass 

        if not is_eiin_search:
            extracted_pairs = [(r, "-") for r in tokens]
            institute_info = {
                'EIIN': 'Individual',
                'Institute': 'Individual Roll Result Sheet',
                'Thana/Upazilla': '-',
                'District': '-',
                'No. of Students Appeared': str(len(extracted_pairs)),
                'No. of Students Passed': '-',
                'No. of Students Failed': '-',
                'Percentage of Pass': '-',
                'No of GPA5': '-'
            }

        if extracted_pairs:
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            results_data = []
            total_students = len(extracted_pairs)
            
            with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
                futures = [
                    executor.submit(fetch_student_detail, pair[0], student_action_url, headers, pair[1])
                    for pair in extracted_pairs
                ]
                
                for i, future in enumerate(futures):
                    res_item = future.result()
                    results_data.append(res_item)
                    
                    progress = (i + 1) / total_students
                    progress_bar.progress(progress)
                    status_text.text(f"⚡ Processing: {i+1}/{total_students}")
            
            status_text.text("✅ All results fetched successfully!")
            progress_bar.empty()
            
            df = pd.DataFrame(results_data)
            df = df[["Group", "Roll", "Name", "GPA", "Total Mark", "Subject Grade"]]
            df = df.sort_values(by="Roll").reset_index(drop=True)
            
            if not is_eiin_search:
                passed_count = sum(1 for g in df['GPA'] if 'F' not in str(g) and str(g) != '-')
                failed_count = sum(1 for g in df['GPA'] if 'F' in str(g))
                gpa5_count = sum(1 for g in df['GPA'] if str(g) in ['5.00', '5'])
                pass_rate = round((passed_count / total_students) * 100, 2) if total_students > 0 else 0
                
                institute_info['No. of Students Passed'] = str(passed_count)
                institute_info['No. of Students Failed'] = str(failed_count)
                institute_info['Percentage of Pass'] = str(pass_rate)
                institute_info['No of GPA5'] = str(gpa5_count)

            st.session_state['df_results'] = df
            st.session_state['eiin_code'] = first_candidate if is_eiin_search else "Individual"
            st.session_state['institute_info'] = institute_info
            st.session_state['selected_exam'] = selected_exam
            st.session_state['selected_year'] = selected_year
            st.session_state['is_eiin_search'] = is_eiin_search

        else:
            st.error("⚠️ No results found for the provided EIIN / Roll Number(s).")

# ---------------------------------------------------------
# Display Result Sheet
# ---------------------------------------------------------
if 'df_results' in st.session_state and not st.session_state['df_results'].empty:
    df = st.session_state['df_results']
    eiin_code = st.session_state.get('eiin_code', '')
    info = st.session_state.get('institute_info', {})
    exam_type = st.session_state.get('selected_exam', 'SSC')
    year = st.session_state.get('selected_year', '2026')
    is_eiin_search = st.session_state.get('is_eiin_search', False)
    
    st.write("---")
    
    if is_eiin_search:
        st.subheader(f"🏫 {info.get('Institute', 'Institute Result Sheet')} (EIIN: {eiin_code})")
        st.caption(f"📍 Thana/Upazilla: {info.get('Thana/Upazilla', '-')} | District: {info.get('District', '-')}")
    else:
        st.subheader("🏫 Individual Student Result Sheet")
    
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Appeared", info.get('No. of Students Appeared', '-'))
    m2.metric("Passed", info.get('No. of Students Passed', '-'))
    m3.metric("Failed", info.get('No. of Students Failed', '-'))
    m4.metric("Pass Rate", f"{info.get('Percentage of Pass', '-')}%")
    m5.metric("GPA 5", info.get('No of GPA5', '-'))
    
    st.write("---")
    st.subheader(f"📊 Result Sheet ({exam_type} - {year})")
    
    table_css = """
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 0; background-color: #ffffff !important; }
        .custom-table { width: 100%; border-collapse: collapse; margin-top: 5px; font-size: 13px; text-align: center; background-color: #ffffff !important; }
        .custom-table th { background-color: #f2f2f2 !important; color: #000; padding: 8px; border: 1px solid #BDBDBD; font-weight: bold; white-space: nowrap; }
        .custom-table td { padding: 8px; border: 1px solid #E0E0E0; white-space: nowrap; background-color: #ffffff !important; }
        .text-left { text-align: left !important; }
        .gpa5-row { color: #1976D2; font-weight: bold; }
        .fail-row { color: #D32F2F; font-weight: bold; }
    </style>
    """
    
    table_rows = ""
    for _, row in df.iterrows():
        gpa = str(row['GPA'])
        is_gpa5 = (gpa == "5.00" or gpa == "5")
        is_fail = ('F' in gpa)
        
        row_class = ""
        if is_gpa5: row_class = "gpa5-row"
        elif is_fail: row_class = "fail-row"
        
        sg_formatted = []
        for item in str(row['Subject Grade']).split(','):
            item_str = item.strip()
            if ':F' in item_str:
                sg_formatted.append(f"<span style='color:#D32F2F; font-weight:bold;'>{item_str}</span>")
            else:
                sg_formatted.append(f"<span style='color:#333;'>{item_str}</span>")
        sg_html = ", ".join(sg_formatted)

        table_rows += f"""
            <tr class='{row_class}'>
                <td>{row['Group']}</td>
                <td>{row['Roll']}</td>
                <td class='text-left'>{row['Name']}</td>
                <td>{row['GPA']}</td>
                <td>{row['Total Mark']}</td>
                <td class='text-left'>{sg_html}</td>
            </tr>
        """
        
    full_html = f"""
    <!DOCTYPE html>
    <html>
    <head>{table_css}</head>
    <body>
        <div style="overflow-x:auto;">
            <table class='custom-table'>
                <thead>
                    <tr>
                        <th>Group</th>
                        <th>Roll</th>
                        <th class='text-left'>Name</th>
                        <th>GPA</th>
                        <th>Total Mark</th>
                        <th class='text-left'>Subject Grade</th>
                    </tr>
                </thead>
                <tbody>
                    {table_rows}
                </tbody>
            </table>
        </div>
    </body>
    </html>
    """
    
    calculated_height = min(600, max(200, len(df) * 40 + 50))
    components.html(full_html, height=calculated_height, scrolling=True)
    
    st.write("<br>", unsafe_allow_html=True)
    
    if is_eiin_search:
        clean_school_name = sanitize_filename(info.get('Institute', 'School'))
        pdf_filename = f"{exam_type}_{year}_Result_{clean_school_name}_{eiin_code}.pdf"
    else:
        pdf_filename = f"{exam_type}_{year}_Result_Individual.pdf"

    col1, col2 = st.columns(2)
    with col1:
        try:
            pdf_bytes = generate_pdf(df, info, exam_type, year)
            st.download_button(
                label="📥 Download PDF File",
                data=bytes(pdf_bytes),
                file_name=pdf_filename,
                mime="application/pdf"
            )
        except Exception as pdf_err:
            st.error(f"Failed to generate PDF: {str(pdf_err)}")
            
    with col2:
        csv_data = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Excel (CSV) Backup",
            data=csv_data,
            file_name=pdf_filename.replace('.pdf', '.csv'),
            mime="text/csv"
        )

# Footer Developer Credit with Link
st.write("---")
st.markdown(
    "<p style='text-align: center; color: #757575;'>"
    "<b>Dinajpur Board Result Processing System</b><br>"
    "Designed & Developed by <a href='https://www.facebook.com/nonigopalrays' target='_blank' style='color: #1E88E5; text-decoration: none; font-weight: bold;'>Nonigopal Ray</a>"
    "</p>", 
    unsafe_allow_html=True
)