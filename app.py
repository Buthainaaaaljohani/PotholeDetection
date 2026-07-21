import streamlit as st
from ultralytics import YOLO
from PIL import Image
import tempfile
import os
from supabase import create_client, Client

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
# 2. الإعداد والربط بقاعدة بيانات Supabase
# ---------------------------------------------------------
SUPABASE_URL = "https://lja-u87h8j10nde0zu-2cq-bfsgkq-8.supabase.co"
SUPABASE_KEY = "sb_publishable_ljA_u87H8J10nDE0zu_2CQ_BFsGKq_8"

@st.cache_resource
def init_supabase() -> Client:
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        return None

supabase = init_supabase()

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
                        try:
                            # حفظ مؤقت للصورة للتحليل
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

                            # تجهيز بيانات البلاغ
                            report_data = {
                                "city": city,
                                "district": district,
                                "street": street,
                                "detections": detections,
                                "confidence": f"{confidence_val:.1f}%",
                                "status": "قيد المعالجة"
                            }

                            # الحفظ في Supabase
                            if supabase:
                                try:
                                    res_db = supabase.table("reports").insert(report_data).execute()
                                    new_id = res_db.data[0]['id'] if (res_db.data and len(res_db.data) > 0) else "مسجل"
                                    st.success(f"🎉 تم تسجيل البلاغ بنجاح! رقم البلاغ الخاص بك هو: **#{new_id}**")
                                except Exception as db_err:
                                    st.error(f"تم التحليل بنجاح، لكن حدث خطأ أثناء الحفظ في قاعدة البيانات: {db_err}")
                                    st.info("💡 تأكدي من وجود أعمدة (city, district, street, detections, confidence, status) في جدول reports داخل Supabase.")
                            else:
                                st.error("تعذر الاتصال بقاعدة البيانات Supabase.")

                        except Exception as err:
                            st.error(f"حدث خطأ أثناء معالجة الصورة: {err}")

# ---------------------------------------------------------
# 6. الصفحة الثانية: متابعة بلاغ
# ---------------------------------------------------------
elif page == "متابعة بلاغ":
    st.title("🔎 متابعة حالة بلاغ")
    report_id_input = st.text_input("أدخل رقم البلاغ:")

    if st.button("بحث 🔍"):
        if report_id_input.isdigit() and supabase:
            try:
                res = supabase.table("reports").select("*").eq("id", int(report_id_input)).execute()
                if res.data and len(res.data) > 0:
                    rep = res.data[0]
                    st.success(f"تفاصيل البلاغ رقم #{rep['id']}")
                    st.write(f"**المدينة:** {rep.get('city', '-')}")
                    st.write(f"**الحي:** {rep.get('district', '-')}")
                    st.write(f"**الشارع:** {rep.get('street', '-')}")
                    st.write(f"**عدد العيوب المرصودة:** {rep.get('detections', 0)}")
                    st.write(f"**نسبة الثقة:** {rep.get('confidence', '-')}")
                    st.info(f"**حالة البلاغ الحالية:** {rep.get('status', 'قيد المعالجة')}")
                else:
                    st.error("عذراً، لم يتم العثور على بلاغ بهذا الرقم.")
            except Exception as e:
                st.error(f"خطأ أثناء البحث: {e}")
        else:
            st.warning("يرجى إدخال رقم بلاغ صحيح.")

# ---------------------------------------------------------
# 7. الصفحة الثالثة: بوابة الموظفين (البلدية)
# ---------------------------------------------------------
elif page == "بوابة الموظفين (البلدية)":
    st.title("🏛️ لوحة تحكم أمانة / بلدية المنطقة")

    if supabase:
        try:
            res = supabase.table("reports").select("*").order("id", desc=True).execute()
            reports_list = res.data if res.data else []
        except Exception as e:
            st.error(f"فشل جلب البلاغات من قاعدة البيانات: {e}")
            reports_list = []
    else:
        reports_list = []

    st.subheader(f"📋 جميع البلاغات المسجلة ({len(reports_list)})")

    if reports_list:
        for rep in reports_list:
            with st.expander(f"بلاغ رقم #{rep['id']} - {rep.get('district', '')} ({rep.get('status', 'قيد المعالجة')})"):
                st.write(f"**الموقع:** {rep.get('city', '')} - {rep.get('district', '')} - {rep.get('street', '')}")
                st.write(f"**عدد الحفريات:** {rep.get('detections', 0)}")
                st.write(f"**الدقة:** {rep.get('confidence', '')}")
                
                status_options = ["قيد المعالجة", "جاري العمل ميدانياً", "تمت الصيانة وإغلاق البلاغ"]
                current_status = rep.get('status', 'قيد المعالجة')
                curr_idx = status_options.index(current_status) if current_status in status_options else 0

                new_status = st.selectbox(
                    "تحديث حالة البلاغ:",
                    status_options,
                    index=curr_idx,
                    key=f"status_select_{rep['id']}"
                )

                if st.button("حفظ التحديث 💾", key=f"btn_update_{rep['id']}"):
                    try:
                        supabase.table("reports").update({"status": new_status}).eq("id", rep['id']).execute()
                        st.success("تم تحديث حالة البلاغ بنجاح!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"فشل تحديث الحالة: {e}")
    else:
        st.info("لا توجد بلاغات مسجلة حالياً.")