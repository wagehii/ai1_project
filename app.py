import streamlit as st
import pandas as pd
from ortools.sat.python import cp_model

# ==========================================
# 1. إعدادات الواجهة والتصميم (UI & CSS)
# ==========================================
st.set_page_config(page_title="Nexus AI Scheduler", page_icon="⚡", layout="wide")

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
if 'rooms' not in st.session_state:
    st.session_state.rooms = pd.DataFrame({
        "اسم المكان": ["مدرج أ", "معمل 1"],
        "السعة القصوى": [150, 40]
    })

if 'personnel' not in st.session_state:
    st.session_state.personnel = pd.DataFrame({
        "الاسم": ["د. أحمد", "م. ملك"],
        "المسمى الوظيفي": ["دكتور", "معيد"]
    })

if 'tasks' not in st.session_state:
    st.session_state.tasks = pd.DataFrame({
        "اسم النشاط (مادة/سكشن)": ["خوارزميات", "برمجة منطقية"],
        "المسؤول": ["د. أحمد", "م. ملك"],
        "عدد الطلاب": [120, 35],
        "عدد المرات أسبوعياً": [2, 1]
    })

if 'nlp_constraints' not in st.session_state:
    st.session_state.nlp_constraints = []

DAYS  = ["الأحد", "الإثنين", "الثلاثاء", "الأربعاء", "الخميس"]
TIMES = ["08:00 AM", "10:00 AM", "12:00 PM", "02:00 PM"]

# ==========================================
# 3. محرك الذكاء الاصطناعي (OR-Tools Engine)  ← النسخة المُحسَّنة
# ==========================================
def generate_dynamic_schedule(rooms_df, tasks_df, soft_constraints):
    """
    Optimal OR-Tools CP-SAT Scheduler
    ===================================
    التحسينات على النسخة الأصلية:
    1. إصلاح Bug قيد تعارض الأشخاص (كان يُعاد بناؤه خطأً داخل الحلقة)
    2. Symmetry Breaking لتسريع البحث
    3. Spread Bonus: تعظيم التباعد بين جلسات نفس المادة
    4. دالة هدف مركّبة (penalties + spread)
    5. Parallel Solver + Presolve + LP linearization
    """

    model = cp_model.CpModel()

    rooms_dict = rooms_df.set_index("اسم المكان").to_dict("index")
    tasks_list = tasks_df.to_dict("records")

    n_days  = len(DAYS)
    n_times = len(TIMES)
    rooms   = list(rooms_dict.keys())

    # ── إنشاء متغيرات القرار ────────────────────────────────────────────────
    x        = {}   # x[t_idx, s_idx, room, d_idx, t_slot]
    task_day = {}   # task_day[t_idx, d_idx]

    for t_idx, task in enumerate(tasks_list):
        n_sessions = task["عدد المرات أسبوعياً"]
        for s_idx in range(n_sessions):
            for r in rooms:
                for d_idx in range(n_days):
                    for t_slot in TIMES:
                        x[(t_idx, s_idx, r, d_idx, t_slot)] = model.new_bool_var(
                            f"x_{t_idx}_{s_idx}_{r}_{d_idx}_{t_slot}"
                        )
        for d_idx in range(n_days):
            task_day[(t_idx, d_idx)] = model.new_bool_var(f"td_{t_idx}_{d_idx}")

    # ── القيود الصارمة (Hard Constraints) ───────────────────────────────────

    for t_idx, task in enumerate(tasks_list):
        n_sessions = task["عدد المرات أسبوعياً"]

        # H1: كل جلسة تُعطى مرة واحدة بالضبط
        for s_idx in range(n_sessions):
            model.add_exactly_one(
                x[(t_idx, s_idx, r, d_idx, t_slot)]
                for r in rooms
                for d_idx in range(n_days)
                for t_slot in TIMES
            )

        # H2: ربط task_day بالمتغير الأساسي
        for d_idx in range(n_days):
            sessions_on_day = [
                x[(t_idx, s_idx, r, d_idx, t_slot)]
                for s_idx in range(n_sessions)
                for r in rooms
                for t_slot in TIMES
            ]
            model.add_max_equality(task_day[(t_idx, d_idx)], sessions_on_day)

        # H3: منع اليومين المتتاليين (No Consecutive Days)
        if n_sessions > 1:
            for d_idx in range(n_days - 1):
                model.add(
                    task_day[(t_idx, d_idx)] + task_day[(t_idx, d_idx + 1)] <= 1
                )

        # H4: الغرفة يجب أن تستوعب الطلاب
        for r, r_data in rooms_dict.items():
            if task["عدد الطلاب"] > r_data["السعة القصوى"]:
                for s_idx in range(n_sessions):
                    for d_idx in range(n_days):
                        for t_slot in TIMES:
                            model.add(x[(t_idx, s_idx, r, d_idx, t_slot)] == 0)

    # H5: لا تعارض في القاعات
    for r in rooms:
        for d_idx in range(n_days):
            for t_slot in TIMES:
                model.add_at_most_one(
                    x[(t_idx, s_idx, r, d_idx, t_slot)]
                    for t_idx, task in enumerate(tasks_list)
                    for s_idx in range(task["عدد المرات أسبوعياً"])
                )

    # H6: لا تعارض للأشخاص — إصلاح الـ Bug الأصلي
    # ⚠️ القديم: person_tasks كان يُبنى داخل حلقة d_idx/t_slot → خطأ
    # ✅ الجديد: نبنيه مرة واحدة برّا الحلقات
    person_to_tasks = {}
    for t_idx, task in enumerate(tasks_list):
        person_to_tasks.setdefault(task["المسؤول"], []).append(t_idx)

    for d_idx in range(n_days):
        for t_slot in TIMES:
            for person, task_indices in person_to_tasks.items():
                model.add_at_most_one(
                    x[(t_idx, s_idx, r, d_idx, t_slot)]
                    for t_idx in task_indices
                    for s_idx in range(tasks_list[t_idx]["عدد المرات أسبوعياً"])
                    for r in rooms
                )

    # ── Symmetry Breaking (تسريع الحل) ──────────────────────────────────────
    for t_idx, task in enumerate(tasks_list):
        n_sessions = task["عدد المرات أسبوعياً"]
        if n_sessions < 2:
            continue
        for s_idx in range(n_sessions - 1):
            time_index_s0, time_index_s1 = [], []
            for r in rooms:
                for d_idx in range(n_days):
                    for t_i, t_slot in enumerate(TIMES):
                        linear_time = d_idx * n_times + t_i
                        time_index_s0.append((x[(t_idx, s_idx,     r, d_idx, t_slot)], linear_time))
                        time_index_s1.append((x[(t_idx, s_idx + 1, r, d_idx, t_slot)], linear_time))
            model.add(
                sum(v * t for v, t in time_index_s0) <=
                sum(v * t for v, t in time_index_s1)
            )

    # ── دالة الهدف المركّبة ──────────────────────────────────────────────────
    # Soft penalties
    soft_penalty_vars = []
    for constraint in soft_constraints:
        if constraint["type"] == "day_off":
            person  = constraint["person"]
            day_idx = DAYS.index(constraint["day"])
            for t_idx, task in enumerate(tasks_list):
                if task["المسؤول"] == person:
                    for s_idx in range(task["عدد المرات أسبوعياً"]):
                        for r in rooms:
                            for t_slot in TIMES:
                                soft_penalty_vars.append(x[(t_idx, s_idx, r, day_idx, t_slot)])

    # Spread bonus — مكافأة الفجوة ≥ يومين بين جلسات نفس المادة
    spread_bonus_vars = []
    for t_idx, task in enumerate(tasks_list):
        if task["عدد المرات أسبوعياً"] < 2:
            continue
        for d1 in range(n_days):
            for d2 in range(d1 + 2, n_days):
                gap = model.new_bool_var(f"gap_{t_idx}_{d1}_{d2}")
                model.add(gap <= task_day[(t_idx, d1)])
                model.add(gap <= task_day[(t_idx, d2)])
                model.add(gap >= task_day[(t_idx, d1)] + task_day[(t_idx, d2)] - 1)
                spread_bonus_vars.append(gap)

    PENALTY_WEIGHT = 10
    SPREAD_WEIGHT  = 2

    model.minimize(
        PENALTY_WEIGHT * sum(soft_penalty_vars)
        - SPREAD_WEIGHT * sum(spread_bonus_vars)
    )

    # ── إعدادات الـ Solver ───────────────────────────────────────────────────
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 20.0
    solver.parameters.num_search_workers  = 4
    solver.parameters.log_search_progress = False
    solver.parameters.cp_model_presolve   = True
    solver.parameters.linearization_level = 2

    status = solver.solve(model)

    # ── استخراج النتائج ──────────────────────────────────────────────────────
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        schedule = []
        for t_idx, task in enumerate(tasks_list):
            for s_idx in range(task["عدد المرات أسبوعياً"]):
                for r in rooms:
                    for d_idx, day in enumerate(DAYS):
                        for t_slot in TIMES:
                            if solver.value(x[(t_idx, s_idx, r, d_idx, t_slot)]) == 1:
                                schedule.append({
                                    "اليوم":         day,
                                    "الوقت":         t_slot,
                                    "المادة/النشاط": task["اسم النشاط (مادة/سكشن)"],
                                    "المسؤول":       task["المسؤول"],
                                    "المكان":        r,
                                    "الطلاب":        task["عدد الطلاب"],
                                })
        return (
            pd.DataFrame(schedule),
            max(0, int(solver.objective_value())),
            "نجاح التوليد!",
        )
    else:
        return None, 0, "مستحيل إيجاد حل! القيود متضاربة جداً."


# ==========================================
# 4. تخطيط الواجهة (Dashboard Layout)
# ==========================================
st.title("⚡ Nexus AI | Multi-Domain Smart Scheduler")
st.caption("أقوى محرك جدولة ديناميكي يعتمد على القيود الصارمة والمرنة.")

with st.sidebar:
    st.header("⚙️ إعدادات النظام")
    domain = st.selectbox("نوع المؤسسة:", ["جامعة / كلية", "مدرسة", "مستشفى", "مؤتمر / فعالية"])
    st.info(f"أنت الآن تقوم ببرمجة نظام مخصص لقطاع: **{domain}**")
    st.divider()

    st.markdown("### 🤖 إدخال القيود بالذكاء الاصطناعي")
    nlp_input = st.text_input("مثال: د. أحمد عايز إجازة الأحد")
    if st.button("تحليل الطلب"):
        found = False
        for day in DAYS:
            if day in nlp_input:
                for person in st.session_state.personnel["الاسم"]:
                    if person in nlp_input:
                        st.session_state.nlp_constraints.append({
                            "type": "day_off", "person": person, "day": day
                        })
                        st.success(f"تم تسجيل القيد لـ {person}")
                        found = True
        if not found:
            st.error("لم يتم فهم النص بشكل كامل.")

tab1, tab2 = st.tabs(["🏗️ بناء بيئة العمل (Dynamic Setup)", "📅 لوحة الجدول النهائي"])

with tab1:
    st.markdown("### 🏢 الخطوة 1: تحديد الأماكن المتاحة والسعة")
    st.session_state.rooms = st.data_editor(
        st.session_state.rooms, num_rows="dynamic", use_container_width=True
    )

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 👥 الخطوة 2: الكادر (أشخاص/دكاترة/أطباء)")
        st.session_state.personnel = st.data_editor(
            st.session_state.personnel, num_rows="dynamic", use_container_width=True
        )
    with col2:
        st.markdown("### 📚 الخطوة 3: المهام (محاضرات/ورديات)")
        st.session_state.tasks = st.data_editor(
            st.session_state.tasks, num_rows="dynamic", use_container_width=True
        )

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
                    st.session_state.nlp_constraints,
                )

                if df_schedule is not None:
                    df_schedule["اليوم"] = pd.Categorical(
                        df_schedule["اليوم"], categories=DAYS, ordered=True
                    )
                    df_schedule["الوقت"] = pd.Categorical(
                        df_schedule["الوقت"], categories=TIMES, ordered=True
                    )
                    df_schedule = df_schedule.sort_values(by=["اليوم", "الوقت"])

                    c1, c2, c3 = st.columns(3)
                    c1.metric("حالة الجدول", "100% بدون تضارب ✅")
                    c2.metric("إجمالي الأنشطة", len(df_schedule))
                    c3.metric("الرغبات التي تم كسرها (Penalties)", penalties)

                    st.dataframe(df_schedule, use_container_width=True, hide_index=True)
                else:
                    st.error(f"❌ فشل: {msg} (تأكد من وجود قاعات كافية بسعة تناسب أعداد الطلاب)")
