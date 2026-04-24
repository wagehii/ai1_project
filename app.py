import streamlit as st
import pandas as pd
from ortools.sat.python import cp_model
import hashlib

st.set_page_config(page_title="Nexus AI Scheduler", page_icon="⚡", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;700&display=swap');
    html, body, [class*="css"] {
        font-family: 'Tajawal', sans-serif;
        direction: rtl;
        text-align: right;
    }
    .main { 
        background: linear-gradient(135deg, #0d1117 0%, #1a1e29 100%); 
    }
    h1 { color: #00ffcc; text-shadow: 2px 2px 4px rgba(0,0,0,0.5); }
    h2, h3 { color: #f72585; }
    
    .stButton>button {
        background: linear-gradient(90deg, #4361ee 0%, #4cc9f0 100%);
        color: white;
        border-radius: 8px;
        border: none;
        font-weight: bold;
        transition: 0.3s;
        box-shadow: 0 4px 15px rgba(67, 97, 238, 0.4);
    }
    .stButton>button:hover { 
        transform: scale(1.03); 
        box-shadow: 0 6px 20px rgba(67, 97, 238, 0.6);
    }
    
    button[kind="primary"] {
        background: linear-gradient(90deg, #f72585 0%, #b5179e 100%);
    }
    
    .stMetric {
        background-color: rgba(22, 27, 34, 0.8);
        padding: 20px;
        border-radius: 12px;
        border-right: 5px solid #00ffcc;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        backdrop-filter: blur(5px);
    }
    
    [data-testid="stDataFrame"] {
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 8px 32px rgba(0,0,0,0.3);
    }
    </style>
""", unsafe_allow_html=True)

COLOR_PALETTE = [
    "#FFB3BA", "#FFDFBA", "#FFFFBA", "#BAFFC9", "#BAE1FF",
    "#D0A9FE", "#FFC6FF", "#A0E8AF", "#FFD6A5", "#FDFFB6",
    "#CAFFBF", "#9BF6FF", "#A0C4FF", "#BDB2FF", "#F4F1DE",
    "#E29578", "#83C5BE", "#FFDDD2", "#EDF6F9", "#00F5D4",
    "#FEE440", "#F15BB5", "#00BBF9", "#9B5DE5", "#00F5D4"
]

def get_color_for_subject(subject_name):
    if not subject_name or pd.isna(subject_name) or subject_name.strip() == "":
        return "background-color: transparent"
    
    hash_val = int(hashlib.md5(str(subject_name).encode('utf-8')).hexdigest(), 16)
    color = COLOR_PALETTE[hash_val % len(COLOR_PALETTE)]
    return f"background-color: {color}; color: #000000; font-weight: bold; border: 1px solid #ffffff; text-align: center;"

# State initialization
if 'rooms' not in st.session_state:
    st.session_state.rooms = pd.DataFrame(columns=["اسم المكان", "السعة القصوى"])
if 'personnel' not in st.session_state:
    st.session_state.personnel = pd.DataFrame(columns=["الاسم", "المسمى الوظيفي"])
if 'tasks' not in st.session_state:
    st.session_state.tasks = pd.DataFrame(columns=["النوع", "اسم النشاط", "المسؤول", "السكشن", "عدد الطلاب", "مرات أسبوعياً"])
if 'nlp_constraints' not in st.session_state:
    st.session_state.nlp_constraints = []

DAYS  = ["السبت", "الأحد", "الإثنين", "الثلاثاء", "الأربعاء", "الخميس"]
TIMES = ["الفترة 1", "الفترة 2", "الفترة 3", "الفترة 4"]

def generate_dynamic_schedule(rooms_df, tasks_df, soft_constraints):
    model = cp_model.CpModel()

    rooms_dict = rooms_df.set_index("اسم المكان").to_dict("index")
    tasks_list = tasks_df.to_dict("records")

    n_days  = len(DAYS)
    n_times = len(TIMES)
    rooms   = list(rooms_dict.keys())

    x = {}
    task_day = {}  

    for t_idx, task in enumerate(tasks_list):
        n_sessions = task["مرات أسبوعياً"]
        for s_idx in range(n_sessions):
            for r in rooms:
                for d_idx in range(n_days):
                    for t_slot in TIMES:
                        x[(t_idx, s_idx, r, d_idx, t_slot)] = model.new_bool_var(f"x_{t_idx}_{s_idx}_{r}_{d_idx}_{t_slot}")
        for d_idx in range(n_days):
            task_day[(t_idx, d_idx)] = model.new_bool_var(f"td_{t_idx}_{d_idx}")

    # Hard Constraints
    for t_idx, task in enumerate(tasks_list):
        n_sessions = task["مرات أسبوعياً"]

        for s_idx in range(n_sessions):
            model.add_exactly_one(
                x[(t_idx, s_idx, r, d_idx, t_slot)]
                for r in rooms for d_idx in range(n_days) for t_slot in TIMES
            )

        for d_idx in range(n_days):
            sessions_on_day = [
                x[(t_idx, s_idx, r, d_idx, t_slot)]
                for s_idx in range(n_sessions) for r in rooms for t_slot in TIMES
            ]
            model.add_max_equality(task_day[(t_idx, d_idx)], sessions_on_day)

        if n_sessions > 1:
            for d_idx in range(n_days - 1):
                model.add(task_day[(t_idx, d_idx)] + task_day[(t_idx, d_idx + 1)] <= 1)

        for r, r_data in rooms_dict.items():
            if task["عدد الطلاب"] > r_data["السعة القصوى"]:
                for s_idx in range(n_sessions):
                    for d_idx in range(n_days):
                        for t_slot in TIMES:
                            model.add(x[(t_idx, s_idx, r, d_idx, t_slot)] == 0)

    for r in rooms:
        for d_idx in range(n_days):
            for t_slot in TIMES:
                model.add_at_most_one(
                    x[(t_idx, s_idx, r, d_idx, t_slot)]
                    for t_idx, task in enumerate(tasks_list)
                    for s_idx in range(task["مرات أسبوعياً"])
                )

    person_to_tasks = {}
    for t_idx, task in enumerate(tasks_list):
        person_to_tasks.setdefault(task["المسؤول"], []).append(t_idx)

    for d_idx in range(n_days):
        for t_slot in TIMES:
            for person, task_indices in person_to_tasks.items():
                model.add_at_most_one(
                    x[(t_idx, s_idx, r, d_idx, t_slot)]
                    for t_idx in task_indices
                    for s_idx in range(tasks_list[t_idx]["مرات أسبوعياً"])
                    for r in rooms
                )
                
    for d_idx in range(n_days):
        for t_slot in TIMES:
            for target_sec in set([t["السكشن"] for t in tasks_list if t["السكشن"] != "الكل"]):
                conflicting_tasks = []
                for t_idx, task in enumerate(tasks_list):
                    if task["السكشن"] == target_sec or task["السكشن"] == "الكل":
                        conflicting_tasks.append(t_idx)
                
                model.add_at_most_one(
                    x[(t_idx, s_idx, r, d_idx, t_slot)]
                    for t_idx in conflicting_tasks
                    for s_idx in range(tasks_list[t_idx]["مرات أسبوعياً"])
                    for r in rooms
                )

    # Symmetry breaking
    for t_idx, task in enumerate(tasks_list):
        if task["مرات أسبوعياً"] >= 2:
            for s_idx in range(task["مرات أسبوعياً"] - 1):
                s0_time, s1_time = [], []
                for r in rooms:
                    for d_idx in range(n_days):
                        for i, t_slot in enumerate(TIMES):
                            linear_time = d_idx * n_times + i
                            s0_time.append((x[(t_idx, s_idx, r, d_idx, t_slot)], linear_time))
                            s1_time.append((x[(t_idx, s_idx+1, r, d_idx, t_slot)], linear_time))
                model.add(sum(v * t for v, t in s0_time) <= sum(v * t for v, t in s1_time))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 20.0
    status = solver.solve(model)

    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        schedule = []
        for t_idx, task in enumerate(tasks_list):
            for s_idx in range(task["مرات أسبوعياً"]):
                for r in rooms:
                    for d_idx, day in enumerate(DAYS):
                        for t_slot in TIMES:
                            if solver.value(x[(t_idx, s_idx, r, d_idx, t_slot)]) == 1:
                                schedule.append({
                                    "اليوم": day,
                                    "الوقت": t_slot,
                                    "السكشن": task["السكشن"],
                                    "النشاط": f"{task['اسم النشاط']}\n({task['المسؤول']})\n[{r}]",
                                    "Sort_Day": d_idx,
                                    "Sort_Time": TIMES.index(t_slot)
                                })
        return pd.DataFrame(schedule), 0, "نجاح التوليد"
    else:
        return None, 0, "مستحيل إيجاد حل بناءً على القيود الحالية."

def format_timetable(df_schedule):
    pivot_df = df_schedule.pivot_table(
        index='السكشن', 
        columns=['Sort_Day', 'اليوم', 'Sort_Time', 'الوقت'], 
        values='النشاط', 
        aggfunc=lambda x: ' \n '.join(x)
    )
    
    pivot_df = pivot_df.sort_index(axis=1)
    pivot_df.columns = pd.MultiIndex.from_tuples([(col[1], col[3]) for col in pivot_df.columns])
    
    if "الكل" in pivot_df.index:
        sections = ["الكل"] + sorted([s for s in pivot_df.index if s != "الكل"])
        pivot_df = pivot_df.reindex(sections)
        
    pivot_df = pivot_df.fillna("")
    return pivot_df

# UI Layout
st.title("Nexus AI | Smart Scheduler")
st.caption("نظام جدولة ديناميكي متقدم للمؤسسات التعليمية.")

tab1, tab2 = st.tabs(["🏗️ بناء بيئة العمل وإدخال البيانات", "📅 عرض الجدول المجمع"])

with tab1:
    if st.button("📥 تحميل بيانات تجريبية (Mock Data)", type="primary", use_container_width=True):
        st.session_state.rooms = pd.DataFrame({
            "اسم المكان": ["مدرج 1", "مدرج 2", "مدرج 3", "معمل 1", "معمل 2", "معمل 3"],
            "السعة القصوى": [300, 250, 200, 40, 40, 40]
        })
        st.session_state.personnel = pd.DataFrame({
            "الاسم": ["د/ محمد حندوسة", "د/ سارة المتولي", "د/ رشا صقر", "د/ أمل أبو العينين", "م/ وليد العروسي", "م/ أحمد العيد", "م/ علي أنور"],
            "المسمى الوظيفي": ["دكتور", "دكتور", "دكتور", "دكتور", "معيد", "معيد", "معيد"]
        })
        st.session_state.tasks = pd.DataFrame({
            "النوع": ["محاضرة", "محاضرة", "محاضرة", "محاضرة", "سكشن", "سكشن", "سكشن", "سكشن", "سكشن", "سكشن"],
            "اسم النشاط": [
                "نظم التشغيل", "الذكاء الاصطناعي", "تصميم لغات الحاسب", "هندسة برمجيات",
                "نظم التشغيل", "نظم التشغيل", "الذكاء الاصطناعي", "الذكاء الاصطناعي", "لغات الحاسب", "لغات الحاسب"
            ],
            "المسؤول": [
                "د/ محمد حندوسة", "د/ سارة المتولي", "د/ رشا صقر", "د/ أمل أبو العينين",
                "م/ وليد العروسي", "م/ وليد العروسي", "م/ أحمد العيد", "م/ أحمد العيد", "م/ علي أنور", "م/ علي أنور"
            ],
            "السكشن": ["الكل", "الكل", "الكل", "الكل", "سكشن 1", "سكشن 2", "سكشن 1", "سكشن 2", "سكشن 1", "سكشن 2"],
            "عدد الطلاب": [200, 200, 200, 200, 35, 35, 35, 35, 35, 35],
            "مرات أسبوعياً": [1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
        })
        st.rerun()
        
    st.markdown("### 🏢 الخطوة 1: تحديد القاعات والمعامل")
    st.session_state.rooms = st.data_editor(
        st.session_state.rooms,
        column_config={
            "السعة القصوى": st.column_config.ProgressColumn("السعة القصوى", min_value=0, max_value=500, format="%d")
        },
        num_rows="dynamic", 
        use_container_width=True
    )

    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("### 👥 الخطوة 2: هيئة التدريس")
        # Apply styler for personnel types
        styled_personnel = st.session_state.personnel.style.map(
            lambda v: 'background-color: rgba(247,37,133,0.2); color: #f72585; font-weight: bold;' if v == 'دكتور' else ('background-color: rgba(67,97,238,0.2); color: #4361ee; font-weight: bold;' if v == 'معيد' else ''),
            subset=['المسمى الوظيفي']
        ) if not st.session_state.personnel.empty and 'المسمى الوظيفي' in st.session_state.personnel.columns else st.session_state.personnel
        
        st.session_state.personnel = st.data_editor(
            styled_personnel, 
            num_rows="dynamic", 
            use_container_width=True
        )
        
    with col2:
        st.markdown("### 📚 الخطوة 3: المهام الأكاديمية")
        # Apply styler for task types
        styled_tasks = st.session_state.tasks.style.map(
            lambda v: 'background-color: rgba(114,9,183,0.3); color: #dfb2f4; font-weight: bold;' if v == 'محاضرة' else ('background-color: rgba(72,149,239,0.3); color: #a0c4ff; font-weight: bold;' if v == 'سكشن' else ''),
            subset=['النوع']
        ) if not st.session_state.tasks.empty and 'النوع' in st.session_state.tasks.columns else st.session_state.tasks
        
        st.session_state.tasks = st.data_editor(
            styled_tasks,
            column_config={
                "عدد الطلاب": st.column_config.ProgressColumn("عدد الطلاب", min_value=0, max_value=500, format="%d")
            },
            num_rows="dynamic", 
            use_container_width=True
        )

with tab2:
    st.markdown("### 🚀 معالجة البيانات وتوليد الجدول")
    if st.button("توليد الجدول الذكي ⚡", use_container_width=True):
        if st.session_state.tasks.empty or st.session_state.rooms.empty:
            st.error("الرجاء إدخال البيانات المطلوبة أولاً.")
        else:
            with st.spinner("جاري بناء الجدول..."):
                df_schedule, penalties, msg = generate_dynamic_schedule(
                    st.session_state.rooms,
                    st.session_state.tasks,
                    st.session_state.nlp_constraints,
                )

                if df_schedule is not None:
                    pivot_table = format_timetable(df_schedule)
                    
                    styled_table = pivot_table.style.map(
                        get_color_for_subject
                    ).set_properties(**{
                        'white-space': 'pre-wrap', 
                        'min-width': '120px', 
                        'height': '60px',
                        'vertical-align': 'middle'
                    })

                    c1, c2 = st.columns(2)
                    c1.metric("الحالة", "✅ مكتمل بدون تضارب")
                    c2.metric("إجمالي المهام الموزعة", len(df_schedule))

                    st.markdown("#### الجدول الدراسي المجمع")
                    st.dataframe(styled_table, use_container_width=True, height=600)
                    
                    st.success("تم توليد وتنسيق الجدول بنجاح.")
                else:
                    st.error(f"❌ خطأ: {msg}")
