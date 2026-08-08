import streamlit as st
import requests

st.set_page_config(page_title="HSC Result Scraper", layout="wide")

st.title("🎓 দিনাজপুর বোর্ড এইচএসসি রেজাল্ট স্ক্র্যাপার")

# ইনপুট ফর্ম
with st.form("search_form"):
    roll_no = st.text_input("রোল নম্বর (Roll No)*", placeholder="যেমন: 222289")
    regi_no = st.text_input("রেজিস্ট্রেশন নম্বর (Registration No)", placeholder="যেমন: 1712345678 (ঐচ্ছিক)")
    submitted = st.form_submit_button("রেজাল্ট HTML ফেচ করুন")

if submitted:
    if not roll_no.strip():
        st.error("⚠️ অনুগ্রহ করে একটি সঠিক রোল নম্বর দিন।")
    else:
        # ১. সেশন বজায় রাখার জন্য Session অবজেক্ট তৈরি
        session = requests.Session()
        
        base_url = "https://result.dinajpurboard.gov.bd/hsc_result2025/search/each.php"
        target_url = "https://result.dinajpurboard.gov.bd/hsc_result2025/search/search_student.php"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Referer": base_url,
            "Origin": "https://result.dinajpurboard.gov.bd",
            "Content-Type": "application/x-www-form-urlencoded"
        }

        with st.spinner("সার্ভার থেকে রেজাল্ট ফেচ করা হচ্ছে..."):
            try:
                # ২. সেশন ও কুকি সেট করতে প্রথমে মূল পেজে হিট করুন
                session.get(base_url, headers=headers, timeout=10)
                
                # ৩. ব্রাউজারের JS অটো-সাবমিট স্টাইলের পে-লোড (submit ফিল্ড ছাড়া)
                payload_auto = {
                    "roll_no": roll_no.strip(),
                    "regi_no": regi_no.strip()
                }
                
                # প্রথম চেষ্টা: JS Auto-submit পে-লোড দিয়ে
                res = session.post(target_url, data=payload_auto, headers=headers, timeout=15)
                
                # যদি রেজাল্ট না পাওয়া যায়, তবে সাধারণ Submit বাটনের পে-লোড দিয়ে দ্বিতীয় চেষ্টা
                if "Not Found" in res.text or "not found" in res.text.lower():
                    payload_manual = {
                        "roll_no": roll_no.strip(),
                        "regi_no": regi_no.strip(),
                        "submit": ""
                    }
                    res = session.post(target_url, data=payload_manual, headers=headers, timeout=15)

                if res.status_code == 200:
                    st.success("✅ সফলভাবে ডাটা ফেচ করা হয়েছে!")
                    
                    tab1, tab2 = st.tabs(["📄 HTML Source Code", "🌐 Rendered View"])
                    
                    with tab1:
                        st.subheader("Raw HTML Code")
                        st.code(res.text, language="html")
                        
                    with tab2:
                        st.subheader("পেজের প্রিভিউ")
                        st.components.v1.html(res.text, height=600, scrolling=True)
                else:
                    st.error(f"❌ সার্ভার এরর! Status Code: {res.status_code}")

            except Exception as e:
                st.error(f"❌ কানেকশন এরর: {e}")
