import streamlit as st
import requests

st.set_page_config(page_title="HSC Result Scraper", layout="wide")

st.title("🎓 দিনাজপুর বোর্ড এইচএসসি রেজাল্ট স্ক্র্যাপার")
st.write("রোল নম্বর প্রদান করে ফলাফলের সোর্স কোড (HTML) লাইভ দেখুন।")

# ইনপুট ফর্ম
with st.form("search_form"):
    roll_no = st.text_input("রোল নম্বর (Roll No)*", placeholder="যেমন: 222289")
    regi_no = st.text_input("রেজিস্ট্রেশন নম্বর (Registration No)", placeholder="যেমন: 1712345678 (ঐচ্ছিক)")
    submitted = st.form_submit_button("রেজাল্ট HTML ফেচ করুন")

if submitted:
    if not roll_no.strip():
        st.error("⚠️ অনুগ্রহ করে একটি সঠিক রোল নম্বর দিন।")
    else:
        # ১. সেশন তৈরি করা (যাতে Cookies বজায় থাকে)
        session = requests.Session()
        
        base_url = "https://result.dinajpurboard.gov.bd/hsc_result2025/search/each.php"
        target_url = "https://result.dinajpurboard.gov.bd/hsc_result2025/search/search_student.php"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": base_url,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Content-Type": "application/x-www-form-urlencoded"
        }

        with st.spinner("সার্ভার থেকে রেজাল্ট ফেচ করা হচ্ছে..."):
            try:
                # ২. সেশন চালুর জন্য প্রথমে মূল পেজে হিট করা
                session.get(base_url, headers=headers, timeout=10)
                
                # ৩. সঠিক ফর্ম ডেটা প্রস্তুত করা
                payload = {
                    "roll_no": roll_no.strip(),
                    "regi_no": regi_no.strip(),
                    "submit": "Submit"  # মূল ফর্মে বাটনের নাম অনুযায়ী এটি পরিবর্তন হতে পারে
                }
                
                # ৪. সেশনসহ POST রিকোয়েস্ট পাঠানো
                res = session.post(target_url, data=payload, headers=headers, timeout=15)
                
                if res.status_code == 200:
                    st.success("✅ সফলভাবে HTML কোড লোড হয়েছে!")
                    
                    tab1, tab2 = st.tabs(["📄 HTML Source Code", "🌐 Rendered View"])
                    
                    with tab1:
                        st.subheader("Raw HTML Code")
                        st.code(res.text, language="html")
                        
                    with tab2:
                        st.subheader("পেজের প্রিভিউ")
                        st.components.v1.html(res.text, height=600, scrolling=True)
                else:
                    st.error(f"❌ সার্ভার থেকে ভুল রেসপন্স এসেছে। Status Code: {res.status_code}")
            except Exception as e:
                st.error(f"❌ কানেকশন এরর: {e}")
