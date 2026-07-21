import streamlit as st
from ultralytics import YOLO
from PIL import Image
import tempfile
import os

# ---------------------------------------------------------
# 1. إعدادات الصفحة والتصميم
# ---------------------------------------------------------
st.set_page_config(
    page_title="نظام كشف الحفريات والطرق",
    page_icon="🛣️",
    layout="wide"
)

# تحميل ملف الاستايل الخارجي
if os.path.exists("style.css"):
    with open("style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. تهيئة الذاكرة المؤقتة للبلاغات
# ---------------------------------------------------------
if 'reports' not in st.session_state:
    st.session_state['reports'] = []

# ---------------------------------------------------------
# 3. تحميل نموذج الذكاء الاصطناعي (YOLO)
# ---------------------------------------------------------
@st.cache_resource
def load_model():
    model_path = "best.pt"
    if os.path.exists(model_path):
        return YOLO(model_path)
    return None

model = load_model()

# ---------------------------------------------------------
# 4. القائمة الجانبية للتنقل
# ---------------------------------------------------------
st.sidebar.title("📌 القائمة الرئيسية")
page = st.sidebar.radio(
    "اختر الخدمة:",
    ["تقديم بلاغ جديد", "متابعة بلاغ", "بوابة الموظفين (البلدية)"]
)

# ---------------------------------------------------------
# 5. الصفحة الأولى: تقديم بلاغ جديد
# ---------------------------------------------------------
if page == "تقديم بلاغ جديد":
    st.title("🚨 تقديم بلاغ عن حفرية / عيب طريق")
    st.write("قم برفع صورة الطريق وتحديد الموقع لتسجيل البلاغ في النظام.")

    col1, col2 = st.columns([1, 1])

    with col1:
        city = st.text_input("المدينة", value="المدينة المنورة")
        district = st.text_input("الحي")
        street = st.text_input("الشارع / اسم الطريق")
        uploaded_file = st.file_uploader("رفع صورة الطريق", type=["jpg", "jpeg", "png"])

    with col2:
        if uploaded_file is not None:
            image = Image.open(uploaded_file)
            st.image(image, caption="الصورة المرفوعة", use_container_width=True)

            if st.button("فحص الصورة وتسجيل البلاغ 🔍"):
                if not district or not street:
                    st.warning("يرجى إدخال اسم الحي والشارع أولاً!")
                elif model is None:
                    st.error("النموذج (best.pt) غير متوفر حالياً.")
                else:
                    with st.spinner("جاري تحليل الصورة بواسطة الذكاء الاصطناعي..."):
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
                            image.convert("RGB").save(tmp.name)
                            tmp_path = tmp.name

                        results = model(tmp_path)
                        res = results[0]

                        detections = len(res.boxes)
                        confidence_val = 0.0
                        if detections > 0:
                            confidence_val = float(res.boxes.conf.max() * 100)

                        st.subheader("📊 نتيجة التحليل:")
                        if detections > 0:
                            st.error(f"⚠️ تم رصد عدد ({detections}) حفرية/عيب بنسبة دقة {confidence_val:.1f}%")
                        else:
                            st.success("✅ لم يتم رصد عيوب واضحة في الصورة.")

                        # إضافة البلاغ للذاكرة المؤقتة
                        new_id = len(st.session_state['reports']) + 1001
                        new_report = {
                            "id": new_id,
                            "city": city,
                            "district": district,
                            "street": street,
                            "detections": detections,
                            "confidence": f"{confidence_val:.1f}%",
                            "status": "قيد المعالجة"
                        }
                        st.session_state['reports'].append(new_report)
                        st.success(f"🎉 تم تسجيل البلاغ بنجاح! رقم البلاغ الخاص بك هو: **#{new_id}**")

# ---------------------------------------------------------
# 6. الصفحة الثانية: متابعة بلاغ
# ---------------------------------------------------------
elif page == "متابعة بلاغ":
    st.title("🔎 متابعة حالة بلاغ")
    report_id_input = st.text_input("أدخل رقم البلاغ:")

    if st.button("بحث 🔍"):
        if report_id_input.isdigit():
            rep_id = int(report_id_input)
            found = [r for r in st.session_state['reports'] if r['id'] == rep_id]
            if found:
                rep = found[0]
                st.success(f"تفاصيل البلاغ رقم #{rep['id']}")
                st.write(f"**المدينة:** {rep['city']}")
                st.write(f"**الحي:** {rep['district']}")
                st.write(f"**الشارع:** {rep['street']}")
                st.write(f"**عدد العيوب المرصودة:** {rep['detections']}")
                st.write(f"**نسبة الثقة:** {rep['confidence']}")
                st.info(f"**حالة البلاغ الحالية:** {rep['status']}")
            else:
                st.error("عذراً، لم يتم العثور على بلاغ بهذا الرقم.")
        else:
            st.warning("يرجى إدخال رقم بلاغ صحيح.")

# ---------------------------------------------------------
# 7. الصفحة الثالثة: بوابة الموظفين (البلدية)
# ---------------------------------------------------------
elif page == "بوابة الموظفين (البلدية)":
    st.title("🏛️ لوحة تحكم أمانة / بلدية المنطقة")
    st.subheader(f"📋 جميع البلاغات المسجلة ({len(st.session_state['reports'])})")

    if st.session_state['reports']:
        for idx, rep in enumerate(st.session_state['reports']):
            with st.expander(f"بلاغ رقم #{rep['id']} - {rep['district']} ({rep['status']})"):
                st.write(f"**الموقع:** {rep['city']} - {rep['district']} - {rep['street']}")
                st.write(f"**عدد الحفريات:** {rep['detections']}")
                st.write(f"**الدقة:** {rep['confidence']}")
                
                status_options = ["قيد المعالجة", "جاري العمل ميدانياً", "تمت الصيانة وإغلاق البلاغ"]
                curr_idx = status_options.index(rep['status']) if rep['status'] in status_options else 0

                new_status = st.selectbox(
                    "تحديث حالة البلاغ:",
                    status_options,
                    index=curr_idx,
                    key=f"status_select_{rep['id']}"
                )

                if st.button("حفظ التحديث 💾", key=f"btn_update_{rep['id']}"):
                    st.session_state['reports'][idx]['status'] = new_status
                    st.success("تم تحديث حالة البلاغ بنجاح!")
                    st.rerun()
    else:
        st.info("لا توجد بلاغات مسجلة حالياً.")