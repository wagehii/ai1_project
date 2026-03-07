import tkinter as tk
import random

class CondensedScheduler:
    def init(self, root):
        self.root = root
        self.root.title("نظام الجداول 2026 - المحاضرات المكثفة")
        self.root.geometry("1500x850")
        
        self.days = ["Saturday", "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday"]
        self.slots = ["1", "2", "3", "4"] 
        self.sections = [f"Sec {i}" for i in range(1, 10)]
        self.courses = ["AI", "OS", "SE", "DSP"]
        
        # محاضرات مكثفة (يومين فقط بدل 4)
        self.fixed_lectures = {
            ("Saturday", "1"): "AI (Lec)",
            ("Saturday", "2"): "OS (Lec)", # محاضرة تانية وراها
            ("Sunday", "1"): "SE (Lec)",
            ("Sunday", "2"): "DSP (Lec)"  # محاضرة تانية وراها
        }
        
        self.setup_ui()

    def setup_ui(self):
        header = tk.Frame(self.root, bg="#1a1a1a", pady=15)
        header.pack(fill="x")
        tk.Label(header, text="جدول حاسبات (محاضرات مكثفة + فواصل سوداء + غياب كامل)", 
                 fg="#f1c40f", bg="#1a1a1a", font=("Arial", 14, "bold")).pack()

        tk.Button(self.root, text="توليد الجدول المكثف ⚡️", command=self.generate, 
                  bg="#16a085", fg="white", font=("Arial", 11, "bold"), pady=10).pack(pady=5)

        # حاوية الجدول بخلفية سوداء لعمل الفواصل
        self.container = tk.Frame(self.root, bg="black", bd=2)
        self.container.pack(fill="both", expand=True, padx=15, pady=10)

    def generate(self):
        for widget in self.container.winfo_children(): widget.destroy()
        
        # رسم الهيدر
        tk.Label(self.container, text="SEC", bg="#2c3e50", fg="white", width=6).grid(row=0, column=0, rowspan=2, sticky="nsew", padx=(0,2), pady=(0,2))
        
        col_ptr = 1
        for day_idx, day in enumerate(self.days):
            # فاصل أسود عريض (5px) بين الأيام
            tk.Label(self.container, text=day, bg="#34495e", fg="white", font=("Arial", 10, "bold")).grid(row=0, column=col_ptr, columnspan=4, sticky="nsew", padx=(0, 5 if day_idx < len(self.days)-1 else 0), pady=(0,2))
            for s in self.slots:
                tk.Label(self.container, text=s, bg="#ecf0f1").grid(row=1, column=col_ptr, sticky="nsew", padx=(0, 1 if int(s) < 4 else 5), pady=(0,2))
                col_ptr += 1

        for i, sec_name in enumerate(self.sections):
            tk.Label(self.container, text=sec_name, bg="white", font=("Arial", 9, "bold")).grid(row=i+2, column=0, sticky="nsew", padx=(0,2), pady=(0,2))
            
            # تحديد يوم الغياب (تبادلي)
            if i+1 == 8: off_day = "Monday"
            elif i+1 == 9: off_day = "Tuesday"
            else:
                other_potential = ["Wednesday", "Thursday", "Monday", "Tuesday"]
                off_day = other_potential[i % len(other_potential)]

            # توزيع السكاشن العملية الـ 4
            remaining_mats = [f"{c} (Sec)" for c in self.courses]
            random.shuffle(remaining_mats)
            
            # حجز أماكن للسكاشن (بشرط مش يوم غياب ومش ميعاد محاضرة مكثفة)
            available_slots = []
            for d in self.days:
                if d != off_day:
                    for s in self.slots:
                        if (d, s) not in self.fixed_lectures:
                            available_slots.append((d, s))
            
            mat_map = {}
            if len(available_slots) >= 4:
                chosen = random.sample(available_slots, 4)
                for m in remaining_mats:
                    mat_map[chosen.pop()] = m

            curr_col = 1
            for day_idx, day in enumerate(self.days):
                for slot_idx, slot in enumerate(self.slots):
                    cell_text, bg, fg = "", "white", "black"
                    
                    # الفواصل
                    p_x = (0, 5 if slot_idx == 3 and day_idx < len(self.days)-1 else 1)
                    p_y = (0, 2)
if day == off_day:
                        bg = "#f1c40f" # إجازة صفراء
                    elif (day, slot) in self.fixed_lectures:
                        cell_text = self.fixed_lectures[(day, slot)]
                        bg, fg = "#3498db", "white" # محاضرة زرقاء
                    elif (day, slot) in mat_map:
                        cell_text = mat_map[(day, slot)]

                    tk.Label(self.container, text=cell_text, bg=bg, fg=fg, 
                             font=("Arial", 7, "bold"), height=4).grid(row=i+2, column=curr_col, sticky="nsew", padx=p_x, pady=p_y)
                    curr_col += 1

        for r in range(len(self.sections)+2): self.container.rowconfigure(r, weight=1)
        for c in range(len(self.days)*4 + 1): self.container.columnconfigure(c, weight=1)

if name == "main":
    root = tk.Tk()
    app = CondensedScheduler(root)
    root.mainloop()    "تصميم خوارزميات (Algorithms)": {"doctor": "د. أحمد", "students": 120},
    "شبكات حاسب (Networks)": {"doctor": "د. محمود", "students": 30},
    "ذكاء اصطناعي (Machine Learning)": {"doctor": "د. ملك", "students": 40},
    "برمجة منطقية (Prolog)": {"doctor": "د. أحمد", "students": 50},
    "لغة التجميع (Assembly)": {"doctor": "د. محمود", "students": 60}
}

DOCTORS = list(set(data["doctor"] for data in COURSES.values()))

# حالة حفظ القيود المرنة
if 'soft_constraints' not in st.session_state:
    st.session_state['soft_constraints'] = []

# ==========================================
# 3. محرك الجدولة الرياضي (OR-Tools Engine)
# ==========================================
def run_ai_scheduler(courses_data, rooms_data, days, times, soft_constraints):
    model = cp_model.CpModel()
    
    # x[c, r, d, t] = 1 if course c is scheduled in room r on day d at time t
    x = {}
    for c in courses_data.keys():
        for r in rooms_data.keys():
            for d in days:
                for t in times:
                    x[(c, r, d, t)] = model.NewBoolVar(f'x_{c}_{r}_{d}_{t}')
    
    # --- Hard Constraints (القيود الصارمة) ---
    
    # 1. كل مادة يجب أن تُدرس مرة واحدة فقط في قاعة ووقت محددين
    for c in courses_data.keys():
        model.AddExactlyOne(x[(c, r, d, t)] for r in rooms_data.keys() for d in days for t in times)
        
    # 2. القاعة لا يمكن أن تستضيف أكثر من مادة في نفس الوقت
    for r in rooms_data.keys():
        for d in days:
            for t in times:
                model.AddAtMostOne(x[(c, r, d, t)] for c in courses_data.keys())
                
    # 3. الدكتور لا يمكنه تدريس مادتين في نفس الوقت
    for doctor in DOCTORS:
        doc_courses = [c for c, data in courses_data.items() if data["doctor"] == doctor]
        for d in days:
            for t in times:
                model.AddAtMostOne(x[(c, r, d, t)] for c in doc_courses for r in rooms_data.keys())
                
    # 4. سعة القاعة يجب أن تكون أكبر من أو تساوي عدد الطلاب في المادة
    for c, c_data in courses_data.items():
        for r, r_data in rooms_data.items(): # ✅ تم التعديل إلى items()
            if c_data["students"] > r_data["capacity"]: # ✅ استخدام r_data مباشرة
                # منع جدولة هذه المادة في هذه القاعة
                for d in days:
                    for t in times:
                        model.Add(x[(c, r, d, t)] == 0)
    # --- Soft Constraints (القيود المرنة / الرغبات) ---
    penalties = []
    for constraint in soft_constraints:
        if constraint['type'] == 'day_off':
            doc = constraint['doctor']
            day_off = constraint['day']
            doc_courses = [c for c, data in courses_data.items() if data["doctor"] == doc]
            
            # نضيف عقوبة (Penalty) لكل مرة يتم فيها جدولة الدكتور في يوم إجازته
            for c in doc_courses:
                for r in rooms_data.keys():
                    for t in times:
                        penalties.append(x[(c, r, day_off, t)])
    
    # دالة الهدف: تقليل العقوبات للوصول لأفضل جدول يحترم الرغبات قدر الإمكان
    model.Minimize(sum(penalties))

    # --- Solve ---
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 10.0 # حد أقصى للبحث
    status = solver.Solve(model)

    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        schedule = []
        for d in days:
            for t in times:
                for r in rooms_data.keys():
                    for c in courses_data.keys():
                        if solver.Value(x[(c, r, d, t)]) == 1:
                            schedule.append({
                                "اليوم": d,
                                "الوقت": t,
                                "المادة": c,
                                "الدكتور": courses_data[c]["doctor"],
                                "القاعة": r,
                                "الطلاب": courses_data[c]["students"]
                            })
        # إرجاع الجدول وعدد الرغبات التي تم كسرها (إن وجدت)
        return pd.DataFrame(schedule), int(solver.ObjectiveValue()), "تم بناء الجدول بنجاح!"
    else:
        return None, 0, "القيود الصارمة متضاربة جداً، مستحيل إيجاد حل!"

# ==========================================
# 4. معالج اللغة الطبيعية (NLP / Regex Engine)
# ==========================================
def parse_nlp_constraint(text):
    """
    يحاكي عمل LLM لاستخراج الرغبات من النصوص.
    في النسخة النهائية للمسابقة، يمكنك استبدال هذا بطلب API لـ Gemini.
    """
    text = text.lower()
    found_doc = None
    found_day = None
    
    for doc in DOCTORS:
        # تبسيط البحث عن الاسم
        name = doc.replace("د. ", "").strip()
        if name in text:
            found_doc = doc
            break
            
    for day in DAYS:
        if day in text:
            found_day = day
            break
            
    if found_doc and found_day and ("إجازة" in text or "لا يريد" in text or "اوف" in text):
        return {"type": "day_off", "doctor": found_doc, "day": found_day}
    
    return None

# ==========================================
# 5. بناء الواجهة والتفاعل (Dashboard & Interaction)
# ==========================================

tab1, tab2, tab3 = st.tabs(["📊 لوحة المؤشرات والبيانات", "🧠 إدخال القيود بالذكاء الاصطناعي", "📅 الجدول الذكي"])

with tab1:
    st.header("إحصائيات النظام الحالية")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("عدد المواد", len(COURSES))
    col2.metric("عدد الدكاترة", len(DOCTORS))
    col3.metric("عدد القاعات", len(ROOMS))
    col4.metric("إجمالي الطلاب", sum(d["students"] for d in COURSES.values()))
    
    st.divider()
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("تفاصيل المواد")
        st.dataframe(pd.DataFrame(COURSES).T)
    with col_b:
        st.subheader("تفاصيل القاعات (الاستيعاب)")
        st.dataframe(pd.DataFrame(ROOMS).T)

with tab2:
    st.header("مدخلات اللغة الطبيعية (NLP constraints)")
    st.info("اكتب رغبات أعضاء هيئة التدريس وسيقوم النظام بتحليلها وتحويلها لمعادلات رياضية.")
    
    nlp_input = st.text_input("📝 اكتب رغبة (مثال: دكتور محمود عايز يوم الاثنين إجازة)")
    
    if st.button("تحليل وإضافة القيد"):
        if nlp_input:
            constraint = parse_nlp_constraint(nlp_input)
            if constraint:
                st.session_state['soft_constraints'].append(constraint)
                st.success(f"✅ تم التعرف على القيد: {constraint['doctor']} يفضل عدم العمل يوم {constraint['day']}.")
            else:
                st.error("⚠️ لم يتمكن النظام من فهم القيد بدقة. تأكد من كتابة اسم الدكتور واليوم بوضوح.")
                
    if st.session_state['soft_constraints']:
        st.write("### القيود المرنة النشطة:")
        for idx, c in enumerate(st.session_state['soft_constraints']):
            st.warning(f"{idx+1}. {c['doctor']} -> إجازة ({c['day']})")
            
        if st.button("مسح جميع القيود"):
            st.session_state['soft_constraints'] = []
            st.rerun()

with tab3:
    st.header("توليد الجدول النهائي وتصحيح التضاربات")
    
    if st.button("⚡ بدء عملية الجدولة بالذكاء الاصطناعي", type="primary", use_container_width=True):
        with st.spinner('يتم الآن معالجة آلاف الاحتمالات لضمان عدم تعارض (الأوقات، القاعات، الدكاترة، السعة)...'):
            df_schedule, penalties, msg = run_ai_scheduler(
                COURSES, ROOMS, DAYS, TIMES, st.session_state['soft_constraints']
            )
            
            if df_schedule is not None:
                if penalties == 0:
                    st.success(f"🎉 {msg} - تم تحقيق 100% من رغبات الدكاترة (Soft Constraints) بدون أي تضارب!")
                else:
                    st.warning(f"⚠️ {msg} - تم إنشاء الجدول لكن تم تجاهل {penalties} رغبة لضمان سير العمليات الأساسية.")
                
                # ترتيب الجدول ليكون منطقياً
                df_schedule['اليوم'] = pd.Categorical(df_schedule['اليوم'], categories=DAYS, ordered=True)
                df_schedule['الوقت'] = pd.Categorical(df_schedule['الوقت'], categories=TIMES, ordered=True)
                df_schedule = df_schedule.sort_values(by=["اليوم", "الوقت"])
                
                # تنسيق العرض ليظهر بشكل احترافي
                st.dataframe(
                    df_schedule.style.applymap(lambda x: 'background-color: #1e2530; color: #4CAF50', subset=['المادة', 'القاعة']),
                    use_container_width=True,
                    hide_index=True
                )
                
                # تصدير البيانات
                csv = df_schedule.to_csv(index=False).encode('utf-8')
                st.download_button("💾 تصدير الجدول إلى Excel (CSV)", data=csv, file_name="AI_Schedule.csv", mime="text/csv")
            else:
                st.error("❌ " + msg)

