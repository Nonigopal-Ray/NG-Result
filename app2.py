import streamlit as st
import requests

st.set_page_config(page_title="Dinajpur Board HSC Result", layout="wide")

st.title("🎓 দিনাজপুর বোর্ড এইচএসসি রেজাল্ট স্ক্যাপার")

with st.form("search_form"):
    roll_no = st.text_input("রোল নম্বর (Roll No)*", placeholder="যেমন: 222289")
    regi_no = st.text_input("রেজিস্ট্রেশন নম্বর (Registration No)", placeholder="যেমন: 1712345678 (ঐচ্ছিক)")
    submitted = st.form_submit_button("রেজাল্ট ফেচ করুন")

if submitted:
    if not roll_no.strip():
        st.error("⚠️ অনুগ্রহ করে একটি সঠিক রোল নম্বর দিন।")
    else:
        # ১. সেশন শুরু
        session = requests.Session()
        
        base_url = "https://result.dinajpurboard.gov.bd/hsc_result2025/search/each.php"
        target_url = "https://result.dinajpurboard.gov.bd/hsc_result2025/search/search_student.php"
        
        # ২. একদম আসল ব্রাউজারের মতো হেডার সেটআপ
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,bn;q=0.8",
            "Origin": "https://result.dinajpurboard.gov.bd",
            "Referer": base_url,
            "Content-Type": "application/x-www-form-urlencoded",
            "Upgrade-Insecure-Requests": "1"
        }

        with st.spinner("সার্ভার থেকে তথ্য সংগ্রহ করা হচ্ছে..."):
            try:
                # ৩. মূল পেজ ভিজিট করে কুকি সংগ্রহ
                session.get(base_url, headers=headers, timeout=10)
                
                # ৪. ব্রাউজারের অটো-সাবমিটের সাথে মিল রেখে পে-লোড (submit কী রাখা হয়নি)
                payload = {
                    "roll_no": roll_no.strip(),
                    "regi_no": regi_no.strip()
                }
                
                # ৫. POST রিকোয়েস্ট পাঠানো
                response = session.post(target_url, data=payload, headers=headers, timeout=15)
                
                # যদি কোনো কারণে Not Found আসে, তবে submit কী যুক্ত করে ব্যাকআপ রিকোয়েস্ট
                if "not found" in response.text.lower() or len(response.text.strip()) < 500:
                    payload_backup = {
                        "roll_no": roll_no.strip(),
                        "regi_no": regi_no.strip(),
                        "submit": ""
                    }
                    response = session.post(target_url, data=payload_backup, headers=headers, timeout=15)

                if response.status_code == 200:
                    st.success("✅ রেজাল্ট সফলভাবে লোড হয়েছে!")
                    
                    tab1, tab2 = st.tabs(["🌐 Rendered View", "📄 HTML Source Code"])
                    
                    with tab1:
                        st.components.v1.html(response.text, height=700, scrolling=True)
                    
                    with tab2:
                        st.code(response.text, language="html")
                else:
                    st.error(f"❌ সার্ভার রেসপন্স এরর! Status Code: {response.status_code}")

            except Exception as e:
                st.error(f"❌ কানেকশন ব্যর্থ হয়েছে: {e}")
