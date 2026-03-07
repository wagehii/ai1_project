import streamlit as st
import pandas as pd
import random

# 1. إعدادات الصفحة
st.set_page_config(layout="wide", page_title="نظام الجداول 2026 - المحاضرات المكثفة")

# 2. الثوابت والمتغيرات الأساسية
DAYS = ["Saturday", "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday"]
SLOTS = ["1", "2", "3", "4"]
SECTIONS = [f"Sec {i}" for i in range(1, 10)]
COURSES = ["AI", "OS", "SE", "DSP"]

# محاضرات مكثفة (يومين فقط)
FIXED_LECTURES = {
    ("Saturday", "1"): "AI (Lec)",
    ("Saturday", "2"): "OS (Lec)",
    ("Sunday", "1"): "SE (Lec)",
    ("Sunday", "2"): "DSP (Lec)"
}

# 3. دالة توليد الجدول
def generate_schedule():
    data = []
    for i, sec_name in enumerate(SECTIONS):
        row_data = {}
        
        # تحديد يوم الغياب (تبادلي)
        if i + 1 == 8: 
            off_day = "Monday"
        elif i + 1 == 9: 
            off_day = "Tuesday"
        else:
            other_potential = ["Wednesday", "Thursday", "Monday", "Tuesday"]
            off_day = other_potential[i % len(other_potential)]

        # توزيع السكاشن العملية الـ 4
        remaining_mats = [f"{c} (Sec)" for c in COURSES]
        random.shuffle(remaining_mats)
        
        # حجز أماكن للسكاشن (بشرط مش يوم غياب ومش ميعاد محاضرة مكثفة)
        available_slots = []
        for d in DAYS:
            if d != off_day:
                for s in SLOTS:
                    if (d, s) not in FIXED_LECTURES:
                        available_slots.append((d, s))
        
        mat_map = {}
        if len(available_slots) >= 4:
            chosen = random.sample(available_slots, 4)
            for m in remaining_mats:
                mat_map[chosen.pop()] = m

        # بناء صف السكشن الحالي
        for day in DAYS:
            for slot in SLOTS:
                if day == off_day:
                    val = "إجازة" # بدلاً من الفراغ لتكون واضحة بصرياً
                elif (day, slot) in FIXED_LECTURES:
                    val = FIXED_LECTURES[(day, slot)]
                elif (day, slot) in mat_map:
                    val = mat_map[(day, slot)]
                else:
                    val = ""
                
                row_data[(day, slot)] = val
                
        data.append(row_data)

    # إنشاء عناوين مدمجة للأعمدة (MultiIndex: الأيام تحتها الفترات)
    columns = pd.MultiIndex.from_product([DAYS, SLOTS], names=["Day", "Slot"])
    df = pd.DataFrame(data, index=SECTIONS, columns=columns)
    return df

# 4. دالة التلوين (CSS مخصص للخلايا)
def style_dataframe(val):
    if val == "إجازة":
        return 'background-color: #f1c40f; color: black; font-weight: bold; text-align: center;'
    elif "(Lec)" in str(val):
        return 'background-color: #3498db; color: white; font-weight: bold; text-align: center;'
    elif "(Sec)" in str(val):
        return 'background-color: #ecf0f1; color: black; text-align: center;'
    return 'background-color: white; color: black;'

# 5. واجهة المستخدم (Streamlit UI)
st.markdown("<h2 style='text-align: center; color: #f1c40f; background-color: #1a1a1a; padding: 15px; border-radius: 5px;'>جدول حاسبات (محاضرات مكثفة + غياب كامل) 🎓</h2>", unsafe_allow_html=True)
st.write("") # مسافة فارغة

# زر التوليد
if st.button("توليد الجدول المكثف ⚡️", type="primary", use_container_width=True):
    df = generate_schedule()
    
    # تطبيق التنسيقات والألوان على الجدول
    # نستخدم try/except لدعم إصدارات Pandas القديمة والحديثة
    try:
        styled_df = df.style.map(style_dataframe)
    except AttributeError:
        styled_df = df.style.applymap(style_dataframe)
    
    # عرض الجدول النهائي
    st.dataframe(styled_df, use_container_width=True, height=400)
