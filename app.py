import streamlit as st
import pandas as pd
from ortools.sat.python import cp_model

# ==========================================
# 1. إعدادات الواجهة والتصميم (UI & CSS)
# ==========================================
st.set_page_config(page_title="Nexus AI Scheduler", page_icon="⚡", layout="wide")

# تصميم احترافي يدعم العربية (RTL) والألوان العصرية
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;700&display=swap');
    html, body, [class*="css"] {
        font-family: 'Tajawal', sans-serif;
        direction: rtl;
        text-align: right;
    }
    .main { background-color: #0d1117; }
    h1, h2, h3 { color: #00ffcc; }
    .stButton>button {
        background: linear-gradient(90deg, #00ffcc 0%, #00b3ff 100%);
        color: black;
        border-radius: 8px;
        border: none;
        font-weight: bold;
        transition: 0.3s;
    }
    .stButton>button:hover { transform: scale(1.02); }
    .stMetric {
        background-color: #161b22; 
        padding: 20px; 
        border-radius: 12px; 
        border-right: 5px solid #00ffcc;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    .dataframe { border-radius: 10px; overflow: hidden; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. إدارة حالة التطبيق (State Management)
# ==========================================
# تهيئة الجداول الفارغة ليبدأ المستخدم بإدخال البيانات
if 'rooms' not in st.session_state:
    st.session_state.rooms = pd.DataFrame({"اسم المكان": ["مدرج أ", "معمل 1"], "السعة القصوى": [150, 40]})

if 'personnel' not in st.session_state:
    st.session_state.personnel = pd.DataFrame({"الاسم": ["د. أحمد", "م. ملك"], "المسمى الوظيفي": ["دكتور", "معيد"]})

if 'tasks' not in st.session_state:
    st.session_state.tasks = pd.DataFrame({
        "اسم النشاط (مادة/سكشن)": ["خوارزميات", "برمجة منطقية"],
        "المسؤول": ["د. أحمد", "م. ملك"],
        "عدد الطلاب": [120, 35],
        "عدد المرات أسبوعياً": [2, 1] # لإجبار النظام على توزيعها
    })

if 'nlp_constraints' not in st.session_state:
    st.session_state.nlp_constraints = []

# ثوابت النظام
DAYS = ["الأحد", "الإثنين", "الثلاثاء", "الأربعاء", "الخميس"]
TIMES = ["08:00 AM", "10:00 AM", "12:00 PM", "02:00 PM"]

# ==========================================
# 3. محرك الذكاء الاصطناعي (OR-Tools Engine)
# ==========================================
def generate_dynamic_schedule(rooms_df, tasks_df, soft_constraints):
    model = cp_model.CpModel()
    
    # تحويل البيانات إلى قواميس لسهولة التعامل
    rooms_dict = rooms_df.set_index("اسم المكان").to_dict('index')
    tasks_list = tasks_df.to_dict('records')
    
    x = {} # متغير القرار الأساسي
    task_day_active = {} # متغير إضافي لضمان عدم توالي الأيام
    
    # إنشاء المتغيرات
    for t_idx, task in enumerate(tasks_list):
        for s_idx in range(task["عدد المرات أسبوعياً"]): # رقم الجلسة
            for r in rooms_dict.keys():
                for d_idx, day in enumerate(DAYS):
                    for t in TIMES:
                        x[(t_idx, s_idx, r, d_idx, t)] = model.NewBoolVar(f'x_{t_idx}_{s_idx}_{r}_{d_idx}_{t}')
                        
        # إنشاء متغيرات لمعرفة هل المادة تُدرس في هذا اليوم أم لا (لتوزيع الأيام)
        for d_idx in range(len(DAYS)):
            task_day_active[(t_idx, d_idx)] = model.NewBoolVar(f'active_{t_idx}_{d_idx}')

    # --- القيود الصارمة (Hard Constraints) ---
    
    for t_idx, task in enumerate(tasks_list):
        # 1. كل جلسة من المادة يجب أن تُعطى مرة واحدة فقط
        for s_idx in range(task["عدد المرات أسبوعياً"]):
            model.AddExactlyOne(
                x[(t_idx, s_idx, r, d_idx, t)] 
                for r in rooms_dict.keys() for d_idx in range(len(DAYS)) for t in TIMES
            )
            
        # 2. ربط المتغير النشط بالمتغير الأساسي (متى يكون اليوم نشطاً لهذه المادة؟)
        for d_idx in range(len(DAYS)):
            sessions_on_this_day = [
                x[(t_idx, s_idx, r, d_idx, t)]
                for s_idx in range(task["عدد المرات أسبوعياً"])
                for r in rooms_dict.keys()
                for t in TIMES
            ]
            # إذا تم جدولة أي جلسة في هذا اليوم، المتغير يكون 1
            model.AddMaxEquality(task_day_active[(t_idx, d_idx)], sessions_on_this_day)
            
        # 3. التوزيع الذكي: منع توالي الأيام لنفس المادة (No Consecutive Days)
        if task["عدد المرات أسبوعياً"] > 1:
            for d_idx in range(len(DAYS) - 1):
                # لا يمكن أن يكون اليوم واليوم الذي يليه نشطين معاً لنفس المادة
                model.Add(task_day_active[(t_idx, d_idx)] + task_day_active[(t_idx, d_idx + 1)] <= 1)
                
        # 4. سعة القاعة يجب أن تستوعب الطلاب
        for r, r_data in rooms_dict.items():
            if task["عدد الطلاب"] > r_data["السعة القصوى"]:
                for s_idx in range(task["عدد المرات أسبوعياً"]):
                    for d_idx in range(len(DAYS)):
                        for t in TIMES:
                            model.Add(x[(t_idx, s_idx, r, d_idx, t)] == 0)

    # 5. منع تعارض القاعات (قاعة واحدة لدرس واحد في نفس الوقت)
    for r in rooms_dict.keys():
        for d_idx in range(len(DAYS)):
            for t in TIMES:
                model.AddAtMostOne(
                    x[(t_idx, s_idx, r, d_idx, t)]
                    for t_idx, task in enumerate(tasks_list)
                    for s_idx in range(task["عدد المرات أسبوعياً"])
                )

    # 6. منع تعارض الأشخاص (الشخص لا يمكنه التواجد في مكانين)
    for d_idx in range(len(DAYS)):
        for t in TIMES:
            # تجميع المهام حسب المسؤول
            person_tasks = {}
            for t_idx, task in enumerate(tasks_list):
                person = task["المسؤول"]
                if person not in person_tasks: person_tasks[person] = []
                person_tasks[person].append(t_idx)
                
            for person, task_indices in person_tasks.items():
                model.AddAtMostOne(
                    x[(t_idx, s_idx, r, d_idx, t)]
                    for t_idx in task_indices
                    for s_idx in range(tasks_list[t_idx]["عدد المرات أسبوعياً"])
                    for r in rooms_dict.keys()
                )

    # --- القيود المرنة (Soft Constraints - NLP) ---
    penalties = []
    for constraint in soft_constraints:
        if constraint['type'] == 'day_off':
            person = constraint['person']
            day_idx = DAYS.index(constraint['day'])
            
            # البحث عن مهام هذا الشخص
            for t_idx, task in enumerate(tasks_list):
                if task["المسؤول"] == person:
                    for s_idx in range(task["عدد المرات أسبوعياً"]):
                        for r in rooms_dict.keys():
                            for t in TIMES:
                                penalties.append(x[(t_idx, s_idx, r, day_idx, t)])
    
    model.Minimize(sum(penalties))

    # --- حل النموذج ---
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 15.0
    status = solver.Solve(model)

    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        schedule = []
        for t_idx, task in enumerate(tasks_list):
            for s_idx in range(task["عدد المرات أسبوعياً"]):
                for r in rooms_dict.keys():
                    for d_idx, day in enumerate(DAYS):
                        for t in TIMES:
                            if solver.Value(x[(t_idx, s_idx, r, d_idx, t)]) == 1:
                                schedule.append({
                                    "اليوم": day,
                                    "الوقت": t,
                                    "المادة/النشاط": task["اسم النشاط (مادة/سكشن)"],
                                    "المسؤول": task["المسؤول"],
                                    "المكان": r,
                                    "الطلاب": task["عدد الطلاب"]
                                })
        return pd.DataFrame(schedule), int(solver.ObjectiveValue()), "نجاح التوليد!"
    else:
        return None, 0, "مستحيل إيجاد حل! القيود متضاربة جداً."

# ==========================================
# 4. تخطيط الواجهة (Dashboard Layout)
# ==========================================
st.title("⚡ Nexus AI | Multi-Domain Smart Scheduler")
st.caption("أقوى محرك جدولة ديناميكي يعتمد على القيود الصارمة والمرنة.")

# Sidebar للتحكم
with st.sidebar:
    st.header("⚙️ إعدادات النظام")
    domain = st.selectbox("نوع المؤسسة:", ["جامعة / كلية", "مدرسة", "مستشفى", "مؤتمر / فعالية"])
    st.info(f"أنت الآن تقوم ببرمجة نظام مخصص لقطاع: **{domain}**")
    st.divider()
    
    st.markdown("### 🤖 إدخال القيود بالذكاء الاصطناعي")
    nlp_input = st.text_input("مثال: د. أحمد عايز إجازة الأحد")
    if st.button("تحليل الطلب"):
        # محاكاة بسيطة لمعالج النصوص
        found = False
        for day in DAYS:
            if day in nlp_input:
                for person in st.session_state.personnel["الاسم"]:
                    if person in nlp_input:
                        st.session_state.nlp_constraints.append({"type": "day_off", "person": person, "day": day})
                        st.success(f"تم تسجيل القيد لـ {person}")
                        found = True
        if not found: st.error("لم يتم فهم النص بشكل كامل.")

# الشاشة الرئيسية لادخال البيانات
tab1, tab2 = st.tabs(["🏗️ بناء بيئة العمل (Dynamic Setup)", "📅 لوحة الجدول النهائي"])

with tab1:
    st.markdown("### 🏢 الخطوة 1: تحديد الأماكن المتاحة والسعة")
    st.session_state.rooms = st.data_editor(st.session_state.rooms, num_rows="dynamic", use_container_width=True)
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 👥 الخطوة 2: الكادر (أشخاص/دكاترة/أطباء)")
        st.session_state.personnel = st.data_editor(st.session_state.personnel, num_rows="dynamic", use_container_width=True)
    with col2:
        st.markdown("### 📚 الخطوة 3: المهام (محاضرات/ورديات)")
        st.session_state.tasks = st.data_editor(st.session_state.tasks, num_rows="dynamic", use_container_width=True)

with tab2:
    st.markdown("### 🚀 معالجة البيانات وتوليد الجدول")
    if st.button("توليد الجدول النهائي بالذكاء الاصطناعي ⚡", use_container_width=True):
        if st.session_state.tasks.empty or st.session_state.rooms.empty:
            st.error("الرجاء إدخال البيانات في قسم بناء بيئة العمل أولاً!")
        else:
            with st.spinner("جاري حل ملايين الاحتمالات وتوزيع الأيام بذكاء..."):
                df_schedule, penalties, msg = generate_dynamic_schedule(
                    st.session_state.rooms, 
                    st.session_state.tasks, 
                    st.session_state.nlp_constraints
                )
                
                if df_schedule is not None:
                    # ترتيب الجدول حسب الأيام والأوقات
                    df_schedule['اليوم'] = pd.Categorical(df_schedule['اليوم'], categories=DAYS, ordered=True)
                    df_schedule['الوقت'] = pd.Categorical(df_schedule['الوقت'], categories=TIMES, ordered=True)
                    df_schedule = df_schedule.sort_values(by=["اليوم", "الوقت"])
                    
                    # لوحة مؤشرات النجاح
                    c1, c2, c3 = st.columns(3)
                    c1.metric("حالة الجدول", "100% بدون تضارب ✅")
                    c2.metric("إجمالي الأنشطة", len(df_schedule))
                    c3.metric("الرغبات التي تم كسرها (Penalties)", penalties)
                    
                    st.dataframe(df_schedule, use_container_width=True, hide_index=True)
                else:
                    st.error(f"❌ فشل: {msg} (تأكد من وجود قاعات كافية بسعة تناسب أعداد الطلاب)")
