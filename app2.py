from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
import re
from bs4 import BeautifulSoup
from fpdf import FPDF
import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components

# ---------------------------------------------------------
# Global Configurations
# ---------------------------------------------------------
MAX_THREADS = 10

OPTIONAL_SUBJECT_KEYWORDS = [
    "agriculture",
    "agricultural",
    "higher math",
    "higher mathematics",
    "home science",
    "computer",
    "biology",
    "physical education",
]

DEV_PHOTO_URL = "https://scontent.fdac96-2.fna.fbcdn.net/v/t39.30808-6/643773069_122124760743127318_3810708861551349936_n.jpg?stp=c0.106.960.960a_dst-jpg_tt6&cstp=mx960x960&ctp=s960x960&_nc_cat=103&_nc_map=urlgen_bucketless&ccb=1-7&_nc_sid=6ee11a&_nc_eui2=AeEgso8F3KkSlHhn2anxAdXs9-LciZbPc2v34tyJls9za-LXwBVvFQfW7eY6ii8M4dQ9U5Nc0XhNxVMnQE2PelNl&_nc_ohc=zhYoLp85PrAQ7kNvwFsOAfy&_nc_oc=Adow_wPwqjrjNRbsPujsTQubSIfAbkhdnmRaZilAXup9-TQZvEYC1s-sEDpSJsvDRe8&_nc_zt=23&_nc_ht=scontent.fdac96-2.fna&_nc_gid=bLqFBXmUXzWzlCULXELrwg&_nc_ss=7b2a8&oh=00_AQHRxzjc7FnI88mEpXqiUi9Kg29zjnZnqF6m_0nfGWFY1Q&oe=6A7E7800"


def get_board_urls(year):
    if str(year) == "2026":
        institute_url = "https://results.dinajpurboard.gov.bd/search/institute"
        student_action_url = (
            "https://results.dinajpurboard.gov.bd/search/student"
        )
    else:
        institute_url = f"https://result.dinajpurboard.gov.bd/ssc_result_{year}/search/search.php"
        student_action_url = f"https://result.dinajpurboard.gov.bd/ssc_result_{year}/search/search_student.php"
    return institute_url, student_action_url


def sanitize_filename(name):
    clean_name = re.sub(r"[^\w\s-]", "", name)
    return re.sub(r"[-\s]+", "_", clean_name).strip("_")


def solve_captcha(question_text):
    """ক্যাপচা থেকে গাণিতিক সমীকরণ সমাধান করা"""
    match = re.search(r"(\d+)\s*([\+\-\*])\s*(\d+)", question_text)
    if match:
        num1, op, num2 = int(match.group(1)), match.group(2), int(match.group(3))
        if op == "+":
            return str(num1 + num2)
        elif op == "-":
            return str(num1 - num2)
        elif op == "*":
            return str(num1 * num2)
    return "4"


# ---------------------------------------------------------
# Streamlit Page Configuration
# ---------------------------------------------------------
st.set_page_config(
    page_title="Dinajpur Board SSC Result Check", page_icon="🎓", layout="wide"
)

st.markdown(
    """
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
    .dev-photo {
        display: block;
        margin-left: auto;
        margin-right: auto;
        width: 120px;
        height: 120px;
        border-radius: 50%;
        object-fit: cover;
        box-shadow: 0px 4px 10px rgba(0,0,0,0.2);
        border: 3px solid #1E88E5;
    }
    </style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    "<h1>🎓 Dinajpur Board Result check with Student Name</h1>",
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="developer-badge">✨ App Developed by: <a style="color: white;'
    ' text-decoration: underline;"'
    ' href="https://www.facebook.com/nonigopalrays" target="_blank">Nonigopal'
    " Ray</a> ✨</div>",
    unsafe_allow_html=True,
)
st.write("---")

# ---------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------


def parse_institute_summary(raw_html, eiin_code):
    soup = BeautifulSoup(raw_html, "html.parser")

    info = {
        "EIIN": str(eiin_code),
        "Institute": "Unknown Institute",
        "Thana/Upazilla": "-",
        "District": "-",
        "No. of Students Appeared": "-",
        "No. of Students Passed": "-",
        "No. of Students Failed": "-",
        "Percentage of Pass": "-",
        "No of GPA5": "-",
    }

    # ১. HTML টেবিল সেল ও গ্রিড থেকে ডাটা পার্সিং
    all_elements = soup.find_all(["td", "th", "div", "span", "p", "h3", "h4"])

    for i, el in enumerate(all_elements):
        txt = el.get_text(strip=True)
        txt_lower = txt.lower()

        if i + 1 < len(all_elements):
            next_val = all_elements[i + 1].get_text(strip=True)

            if (
                "institute" in txt_lower or "school" in txt_lower
            ) and info["Institute"] == "Unknown Institute":
                if (
                    next_val
                    and len(next_val) > 3
                    and not next_val.isdigit()
                    and "result" not in next_val.lower()
                ):
                    info["Institute"] = next_val

            elif "thana" in txt_lower or "upazilla" in txt_lower or "upazila" in txt_lower:
                if next_val and info["Thana/Upazilla"] == "-":
                    info["Thana/Upazilla"] = next_val

            elif "district" in txt_lower and info["District"] == "-":
                if next_val:
                    info["District"] = next_val

            elif "appeared" in txt_lower and info["No. of Students Appeared"] == "-":
                m = re.search(r"\d+", next_val)
                if m:
                    info["No. of Students Appeared"] = m.group(0)

            elif "passed" in txt_lower and info["No. of Students Passed"] == "-":
                m = re.search(r"\d+", next_val)
                if m:
                    info["No. of Students Passed"] = m.group(0)

            elif (
                "pass rate" in txt_lower or "percentage" in txt_lower or "pass (%)" in txt_lower
            ) and info["Percentage of Pass"] == "-":
                m = re.search(r"[\d\.]+", next_val)
                if m:
                    info["Percentage of Pass"] = m.group(0)

            elif (
                "gpa5" in txt_lower or "gpa 5" in txt_lower or "gpa-5" in txt_lower
            ) and info["No of GPA5"] == "-":
                m = re.search(r"\d+", next_val)
                if m:
                    info["No of GPA5"] = m.group(0)

    # ২. ফ্লেক্সিবল রেগেক্স (Regex) পার্সিং ফলব্যাক
    text_lines = [
        line.strip()
        for line in soup.get_text("\n").split("\n")
        if line.strip()
    ]
    full_text = "\n".join(text_lines)

    patterns = {
        "Institute": [
            r"Institute(?:\s*Name)?\s*[:\-]?\s*([^\n\r<]+)",
            r"School(?:\s*Name)?\s*[:\-]?\s*([^\n\r<]+)",
        ],
        "Thana/Upazilla": [
            r"(?:Thana/Upazilla|Thana|Upazilla|Upazila)\s*[:\-]?\s*([^\n\r<]+)"
        ],
        "District": [r"District\s*[:\-]?\s*([^\n\r<]+)"],
        "No. of Students Appeared": [
            r"(?:No\.\s*of\s*Students\s*Appeared|Appeared)\s*[:\-]?\s*(\d+)"
        ],
        "No. of Students Passed": [
            r"(?:No\.\s*of\s*Students\s*Passed|Passed)\s*[:\-]?\s*(\d+)"
        ],
        "Percentage of Pass": [
            r"(?:Percentage\s*of\s*Pass|Pass\s*Rate)\s*[:\-]?\s*([\d\.]+)"
        ],
        "No of GPA5": [
            r"(?:No\s*of\s*GPA5|GPA5|GPA\s*5)\s*[:\-]?\s*(\d+)"
        ],
    }

    for key, pat_list in patterns.items():
        if info[key] in ["Unknown Institute", "-"]:
            for pat in pat_list:
                match = re.search(pat, full_text, re.IGNORECASE)
                if match:
                    val = match.group(1).strip()
                    if val and len(val) < 100:
                        info[key] = val
                        break

    try:
        app = int(info["No. of Students Appeared"])
        pas = int(info["No. of Students Passed"])
        info["No. of Students Failed"] = str(app - pas)
    except Exception:
        pass

    return info


def fetch_student_detail(
    roll, action_url, session_headers, year="2026", initial_status="-"
):
    session = requests.Session()
    try:
        if str(year) == "2026":
            get_res = session.get(action_url, headers=session_headers, timeout=12)
            if get_res.status_code != 200:
                return {
                    "Group": "-",
                    "Roll": str(roll),
                    "Name": "Server Error",
                    "GPA": initial_status,
                    "Total Mark": "-",
                    "Subject Grade": "-",
                }

            soup_init = BeautifulSoup(get_res.text, "html.parser")
            token_input = soup_init.find("input", {"name": "_token"})
            csrf_token = token_input["value"] if token_input else ""

            captcha_q = soup_init.find("span", {"class": "board-captcha-q"})
            captcha_answer = (
                solve_captcha(captcha_q.text) if captcha_q else "4"
            )

            payload = {
                "_token": csrf_token,
                "roll_no": str(roll),
                "regi_no": "",
                "captcha": captcha_answer,
                "submit": "1",
            }
            response = session.post(
                action_url, data=payload, headers=session_headers, timeout=12
            )
        else:
            payload = {"roll_no": str(roll), "regi_no": "", "submit": "Submit"}
            response = session.post(
                action_url, data=payload, headers=session_headers, timeout=12
            )

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")

            if soup.find(
                text=lambda t: t and "no result found" in str(t).lower()
            ):
                return {
                    "Group": "-",
                    "Roll": str(roll),
                    "Name": "No Result Found",
                    "GPA": "F",
                    "Total Mark": "-",
                    "Subject Grade": "-",
                }

            name = "Not Found"
            group = "Not Found"
            result_val = initial_status
            total_mark_val = "-"

            all_tds = soup.find_all("td")
            for i, td in enumerate(all_tds):
                txt = td.text.strip().lower()

                if "name" in txt and i + 1 < len(all_tds) and name == "Not Found":
                    possible_name = all_tds[i + 1].text.strip()
                    if len(possible_name) > 2 and not possible_name.isdigit():
                        name = possible_name

                if (
                    "group" in txt
                    and i + 1 < len(all_tds)
                    and group == "Not Found"
                ):
                    possible_group = all_tds[i + 1].text.strip()
                    if possible_group:
                        group = possible_group

                if "result" in txt and i + 1 < len(all_tds):
                    val = all_tds[i + 1].text.strip()
                    if val:
                        result_val = val

                if "total mark" in txt and i + 1 < len(all_tds):
                    val = all_tds[i + 1].text.strip()
                    if val:
                        total_mark_val = val

            subject_grades = []
            compulsory_failed_count = 0

            for i, td in enumerate(all_tds):
                txt = td.text.strip()
                if txt in ["A+", "A", "A-", "B", "C", "D", "F"]:
                    if i - 1 >= 0:
                        sub = all_tds[i - 1].text.strip()
                        if len(sub) > 2:
                            subject_grades.append(f"{sub}:{txt}")
                            if txt == "F":
                                sub_lower = sub.lower()
                                is_optional = any(
                                    opt_key in sub_lower
                                    for opt_key in OPTIONAL_SUBJECT_KEYWORDS
                                )
                                if not is_optional:
                                    compulsory_failed_count += 1

            if compulsory_failed_count > 0:
                result_val = f"F{compulsory_failed_count}"
            elif "PASSED" in result_val.upper() or "GPA=" in result_val.upper():
                match = re.search(r"\d+\.\d+|\d+", result_val)
                if match:
                    result_val = match.group(0)

            grades_str = ", ".join(subject_grades) if subject_grades else "-"

            return {
                "Group": group,
                "Roll": str(roll),
                "Name": name,
                "GPA": result_val,
                "Total Mark": total_mark_val,
                "Subject Grade": grades_str,
            }
        else:
            return {
                "Group": "-",
                "Roll": str(roll),
                "Name": "Server Error",
                "GPA": initial_status,
                "Total Mark": "-",
                "Subject Grade": "-",
            }
    except Exception:
        return {
            "Group": "-",
            "Roll": str(roll),
            "Name": "Connection Error",
            "GPA": initial_status,
            "Total Mark": "-",
            "Subject Grade": "-",
        }


# Custom PDF Class
class ColorPDF(FPDF):

    def __init__(self, year="2026", img_bytes=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.year = year
        self.img_bytes = img_bytes

    def footer(self):
        self.set_y(-12)
        if self.img_bytes:
            try:
                self.image(self.img_bytes, x=10, y=self.get_y() - 1, w=7, h=7)
                text_x_offset = 19
            except Exception:
                text_x_offset = 10
        else:
            text_x_offset = 10

        self.set_x(text_x_offset)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(30, 136, 229)

        fb_url = "https://www.facebook.com/nonigopalrays"
        self.cell(
            140,
            5,
            f"App Developed by: Nonigopal Ray | Dinajpur Board SSC {self.year}"
            " Result System",
            align="L",
            link=fb_url,
        )

        self.set_text_color(100, 100, 100)
        self.cell(0, 5, f"Page {self.page_no()}/{{nb}}", align="R")

    def format_subject_lines(self, text, max_width):
        self.set_font("Helvetica", "", 5)
        items = [item.strip() for item in text.split(",") if item.strip()]
        lines = []
        current_line = []
        current_w = 0

        for item in items:
            item_str = f"{item}, "
            item_w = self.get_string_width(item_str)
            if current_w + item_w > max_width - 2 and current_line:
                lines.append(current_line)
                current_line = [item]
                current_w = self.get_string_width(f"{item}, ")
            else:
                current_line.append(item)
                current_w += item_w

        if current_line:
            lines.append(current_line)

        return lines

    def draw_colored_grades(self, x, y, line_lines):
        self.set_font("Helvetica", "", 5)
        curr_y = y + 1.8

        for line in line_lines:
            curr_x = x + 1.0
            for item in line:
                parts = item.split(":")
                sub, grade = (
                    (parts[0], parts[1]) if len(parts) == 2 else (item, "")
                )
                item_str = f"{sub}:{grade}, " if grade else f"{item}, "

                if grade == "F":
                    self.set_text_color(211, 47, 47)
                else:
                    self.set_text_color(0, 0, 0)

                self.text(curr_x, curr_y, item_str)
                curr_x += self.get_string_width(item_str)
            curr_y += 2.6

        self.set_text_color(0, 0, 0)


def generate_pdf(dataframe, institute_info, year):
    img_stream = None
    try:
        resp = requests.get(DEV_PHOTO_URL, timeout=5)
        if resp.status_code == 200:
            img_stream = BytesIO(resp.content)
    except Exception:
        img_stream = None

    pdf = ColorPDF(
        year=year, img_bytes=img_stream, orientation="L", unit="mm", format="A4"
    )
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 13)
    inst_name = str(
        institute_info.get(
            "Institute", "BOARD OF INTERMEDIATE & SECONDARY EDUCATION, DINAJPUR"
        )
    )
    pdf.cell(0, 6, inst_name[:80], ln=True, align="C")

    pdf.set_font("Helvetica", "", 8.5)
    pdf.cell(
        0,
        5,
        "BOARD OF INTERMEDIATE AND SECONDARY EDUCATION, DINAJPUR | SSC"
        f" {year}",
        ln=True,
        align="C",
    )

    thana = str(institute_info.get("Thana/Upazilla", "-"))
    dist = str(institute_info.get("District", "-"))
    eiin = str(institute_info.get("EIIN", "-"))
    pdf.cell(
        0,
        5,
        f"EIIN/ID: {eiin} | Thana/Upazilla: {thana} | District: {dist}",
        ln=True,
        align="C",
    )
    pdf.ln(2)

    pdf.set_font("Helvetica", "B", 8.5)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(
        55,
        6,
        f"Appeared: {institute_info.get('No. of Students Appeared', '-')}",
        border=1,
        align="C",
        fill=True,
    )
    pdf.cell(
        55,
        6,
        f"Passed: {institute_info.get('No. of Students Passed', '-')}",
        border=1,
        align="C",
        fill=True,
    )
    pdf.cell(
        55,
        6,
        f"Failed: {institute_info.get('No. of Students Failed', '-')}",
        border=1,
        align="C",
        fill=True,
    )
    pdf.cell(
        55,
        6,
        f"Pass Rate: {institute_info.get('Percentage of Pass', '-')}%",
        border=1,
        align="C",
        fill=True,
    )
    pdf.cell(
        57,
        6,
        f"GPA 5: {institute_info.get('No of GPA5', '-')}",
        border=1,
        align="C",
        fill=True,
    )
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
        name = str(row["Name"])[:30]
        gpa = str(row["GPA"])
        tm = str(row["Total Mark"])[:8]
        sg = str(row["Subject Grade"])

        grade_lines = pdf.format_subject_lines(sg, widths[5])
        num_lines = max(1, len(grade_lines))
        row_h = max(5.5, num_lines * 2.6 + 1.8)

        if pdf.get_y() + row_h > 185:
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

        is_gpa5 = gpa == "5.00" or gpa == "5"
        is_fail = "F" in gpa

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
        pdf.draw_colored_grades(x + sum(widths[:5]), y, grade_lines)

        pdf.set_xy(x, y + row_h)

    return pdf.output(dest="S")


# ---------------------------------------------------------
# User Input Section
# ---------------------------------------------------------
col_input, col_year = st.columns([3, 1])

with col_input:
    user_input = st.text_input(
        "📊 Enter EIIN Code or Roll Number(s):",
        placeholder="Example EIIN: 125057  OR  Rolls: 123456, 123457",
    )

with col_year:
    selected_year = st.selectbox(
        "📅 Select Year:", options=["2026", "2025", "2024"], index=0
    )

if st.button("Search Result 🚀"):
    raw_input = user_input.strip()
    if not raw_input:
        st.error("⚠️ Please enter a valid EIIN or Roll Number(s)!")
    else:
        institute_url, student_action_url = get_board_urls(selected_year)

        session = requests.Session()
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                " (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            ),
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            ),
            "Content-Type": "application/x-www-form-urlencoded",
        }

        extracted_pairs = []
        institute_info = {}
        is_eiin_search = False

        tokens = [
            t.strip()
            for t in re.split(r"[\s,]+", raw_input)
            if t.strip().isdigit()
        ]
        first_candidate = tokens[0] if tokens else raw_input

        try:
            if selected_year == "2026":
                get_res = session.get(
                    institute_url, headers=headers, timeout=12
                )
                soup_init = BeautifulSoup(get_res.text, "html.parser")
                token_input = soup_init.find("input", {"name": "_token"})
                csrf_token = token_input["value"] if token_input else ""

                payload = {
                    "_token": csrf_token,
                    "eiin_no": first_candidate,
                    "submit": "1",
                }
                res = session.post(
                    institute_url, data=payload, headers=headers, timeout=15
                )
            else:
                payload = {
                    "einn_no": first_candidate,
                    "eiin_no": first_candidate,
                    "submit": "Get Result",
                }
                res = session.post(
                    institute_url, data=payload, headers=headers, timeout=12
                )

            raw_text = res.text

            pairs = re.findall(r"(\d{6,8})\s*\[([^\]]+)\]", raw_text)
            all_raw_rolls = re.findall(r"\b\d{6,8}\b", raw_text)
            all_raw_rolls = [r for r in all_raw_rolls if r != first_candidate]

            existing_rolls = set([p[0] for p in pairs])
            for r in all_raw_rolls:
                if r not in existing_rolls:
                    pairs.append((r, "F"))
                    existing_rolls.add(r)

            # ফ্লেক্সিবল EIIN সার্চ ডিটেকশন
            if pairs and (
                len(first_candidate) == 6
                or any(
                    k in raw_text.lower()
                    for k in ["institute", "eiin", "appeared", "passed", "board-panel-title"]
                )
            ):
                is_eiin_search = True
                extracted_pairs = pairs
                institute_info = parse_institute_summary(
                    raw_text, first_candidate
                )
        except Exception:
            pass

        if not is_eiin_search:
            extracted_pairs = [(r, "-") for r in tokens]
            institute_info = {
                "EIIN": "Individual",
                "Institute": "Individual Roll Result Sheet",
                "Thana/Upazilla": "-",
                "District": "-",
                "No. of Students Appeared": str(len(extracted_pairs)),
                "No. of Students Passed": "-",
                "No. of Students Failed": "-",
                "Percentage of Pass": "-",
                "No of GPA5": "-",
            }

        if extracted_pairs:
            progress_bar = st.progress(0)
            status_text = st.empty()

            results_data = []
            total_students = len(extracted_pairs)

            with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
                futures = [
                    executor.submit(
                        fetch_student_detail,
                        pair[0],
                        student_action_url,
                        headers,
                        selected_year,
                        pair[1],
                    )
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
            df = df[
                ["Group", "Roll", "Name", "GPA", "Total Mark", "Subject Grade"]
            ]
            df = df.sort_values(by="Roll").reset_index(drop=True)

            # অটো-ক্যালকুলেশন ব্যাকআপ (বোর্ড থেকে ডাটা মিস হলেও অটো হিসাব করবে)
            passed_count = sum(
                1
                for g in df["GPA"]
                if "F" not in str(g) and str(g) not in ["-", "Server Error", "Connection Error", "No Result Found"]
            )
            failed_count = sum(1 for g in df["GPA"] if "F" in str(g))
            gpa5_count = sum(
                1 for g in df["GPA"] if str(g) in ["5.00", "5"]
            )
            pass_rate = (
                round((passed_count / total_students) * 100, 2)
                if total_students > 0
                else 0
            )

            if institute_info.get("No. of Students Appeared") in ["-", "0", ""]:
                institute_info["No. of Students Appeared"] = str(total_students)
            if institute_info.get("No. of Students Passed") in ["-", "0", ""]:
                institute_info["No. of Students Passed"] = str(passed_count)
            if institute_info.get("No. of Students Failed") in ["-", "0", ""]:
                institute_info["No. of Students Failed"] = str(failed_count)
            if institute_info.get("Percentage of Pass") in ["-", "0", "0.0", ""]:
                institute_info["Percentage of Pass"] = str(pass_rate)
            if institute_info.get("No of GPA5") in ["-", ""]:
                institute_info["No of GPA5"] = str(gpa5_count)

            st.session_state["df_results"] = df
            st.session_state["eiin_code"] = (
                first_candidate if is_eiin_search else "Individual"
            )
            st.session_state["institute_info"] = institute_info
            st.session_state["selected_year"] = selected_year
            st.session_state["is_eiin_search"] = is_eiin_search

        else:
            st.error(
                "⚠️ No results found for the provided EIIN / Roll Number(s)."
            )

# ---------------------------------------------------------
# Display Result Sheet
# ---------------------------------------------------------
if (
    "df_results" in st.session_state
    and not st.session_state["df_results"].empty
):
    df = st.session_state["df_results"]
    eiin_code = st.session_state.get("eiin_code", "")
    info = st.session_state.get("institute_info", {})
    year = st.session_state.get("selected_year", "2026")
    is_eiin_search = st.session_state.get("is_eiin_search", False)

    st.write("---")

    if is_eiin_search:
        st.subheader(
            f"🏫 {info.get('Institute', 'Institute Result Sheet')} (EIIN:"
            f" {eiin_code})"
        )
        st.caption(
            f"📍 Thana/Upazilla: {info.get('Thana/Upazilla', '-')} | District:"
            f" {info.get('District', '-')}"
        )
    else:
        st.subheader("🏫 Individual Student Result Sheet")

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Appeared", info.get("No. of Students Appeared", "-"))
    m2.metric("Passed", info.get("No. of Students Passed", "-"))
    m3.metric("Failed", info.get("No. of Students Failed", "-"))
    m4.metric("Pass Rate", f"{info.get('Percentage of Pass', '-')}%")
    m5.metric("GPA 5", info.get("No of GPA5", "-"))

    st.write("---")
    st.subheader(f"📊 Result Sheet ({year})")

    table_css = """
    <style>
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            margin: 0; 
            padding: 0; 
            background-color: #ffffff !important; 
        }
        .custom-table { 
            width: 100%; 
            border-collapse: collapse; 
            margin-top: 5px; 
            font-size: 13px; 
            text-align: center; 
            background-color: #ffffff !important; 
        }
        .custom-table th { 
            background-color: #f2f2f2 !important; 
            color: #000; 
            padding: 8px; 
            border: 1px solid #BDBDBD; 
            font-weight: bold; 
            white-space: nowrap; 
        }
        .custom-table td { 
            padding: 8px; 
            border: 1px solid #E0E0E0; 
            white-space: nowrap; 
            background-color: #ffffff !important; 
        }
        .text-left { text-align: left !important; }
        .gpa5-row { color: #1976D2; font-weight: bold; }
        .fail-row { color: #D32F2F; font-weight: bold; }
    </style>
    """

    table_rows = ""
    for _, row in df.iterrows():
        gpa = str(row["GPA"])
        is_gpa5 = gpa == "5.00" or gpa == "5"
        is_fail = "F" in gpa

        row_class = ""
        if is_gpa5:
            row_class = "gpa5-row"
        elif is_fail:
            row_class = "fail-row"

        sg_formatted = []
        for item in str(row["Subject Grade"]).split(","):
            item_str = item.strip()
            if ":F" in item_str:
                sg_formatted.append(
                    "<span style='color:#D32F2F;"
                    f" font-weight:bold;'>{item_str}</span>"
                )
            else:
                sg_formatted.append(
                    f"<span style='color:#333;'>{item_str}</span>"
                )
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
        clean_school_name = sanitize_filename(info.get("Institute", "School"))
        pdf_filename = f"SSC_{year}_Result_{clean_school_name}_{eiin_code}.pdf"
    else:
        pdf_filename = f"SSC_{year}_Result_Individual.pdf"

    col1, col2 = st.columns(2)
    with col1:
        try:
            pdf_bytes = generate_pdf(df, info, year)
            st.download_button(
                label="📥 Download PDF File",
                data=bytes(pdf_bytes),
                file_name=pdf_filename,
                mime="application/pdf",
            )
        except Exception as pdf_err:
            st.error(f"Failed to generate PDF: {str(pdf_err)}")

    with col2:
        csv_data = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Download Excel (CSV) Backup",
            data=csv_data,
            file_name=pdf_filename.replace(".pdf", ".csv"),
            mime="text/csv",
        )

# ---------------------------------------------------------
# Developer Profile Section
# ---------------------------------------------------------
st.write("---")
st.subheader("👨‍💻 Developer Profile")

st.markdown(
    f"""
    <div style="text-align: center;">
        <a href="https://www.facebook.com/nonigopalrays" target="_blank">
            <img src="{DEV_PHOTO_URL}" class="dev-photo" alt="Nonigopal Ray">
        </a>
        <h4 style="margin-top: 10px; color: #1E88E5;">
            <a href="https://www.facebook.com/nonigopalrays" target="_blank" style="text-decoration: none; color: #1E88E5;">Nonigopal Ray</a>
        </h4>
    </div>
""",
    unsafe_allow_html=True,
)

st.markdown(
    '<p style="text-align: center; color: #757575;"><b>Dinajpur Board SSC Result'
    ' Processing System</b><br>Designed & Developed by <b><a'
    ' href="https://www.facebook.com/nonigopalrays" target="_blank">Nonigopal'
    " Ray</a></b></p>",
    unsafe_allow_html=True,
)