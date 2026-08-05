import streamlit as st
import requests

st.set_page_config(page_title="HSC Result Scraper", layout="wide")

st.title("🎓 দিনাজপুর বোর্ড এইচএসসি রেজাল্ট স্ক্যাপার")
st.write("রোল নম্বর প্রদান করে ফলাফলের সোর্স কোড (HTML) স্ট্রিমলিটে লাইভ দেখুন।")

# ইনপুট ফর্ম
with st.form("search_form"):
    roll_no = st.text_input("রোল নম্বর (Roll No)*", placeholder="যেমন: 123456")
    regi_no = st.text_input("রেজিস্ট্রেশন নম্বর (Registration No)", placeholder="যেমন: 1712345678 (ঐচ্ছিক)")
    submitted = st.form_submit_button("রেজাল্ট HTML ফেচ করুন")

if submitted:
    if not roll_no.strip():
        st.error("⚠️ অনুগ্রহ করে একটি সঠিক রোল নম্বর দিন।")
    else:
        target_url = "https://result.dinajpurboard.gov.bd/hsc_result2025/search/search_student.php"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Referer": "https://result.dinajpurboard.gov.bd/hsc_result2025/search/each.php"
        }
        payload = {
            "roll_no": roll_no.strip(),
            "regi_no": regi_no.strip(),
            "submit": ""
        }
        
        with st.spinner("সার্ভার থেকে রেজাল্ট ফেচ করা হচ্ছে..."):
            try:
                res = requests.post(target_url, data=payload, headers=headers, timeout=15)
                
                if res.status_code == 200:
                    st.success("✅ সফলভাবে HTML কোড লোড হয়েছে!")
                    
                    # দুটি ট্যাবে তথ্য দেখানো (একটি রেন্ডার করা পেজ, অন্যটি র HTML সোর্স কোড)
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
