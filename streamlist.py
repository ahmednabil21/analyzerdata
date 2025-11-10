import streamlit as st
import pandas as pd
import io

# إعداد صفحة التطبيق
st.set_page_config(
    page_title="تحليل ملفات CSV",
    page_icon="📊",
    layout="wide"
)

# العنوان الرئيسي
st.title("📊 نظام تحليل ملفات CSV")
st.markdown("---")

# رفع الملف
uploaded_file = st.file_uploader(
    "اختر ملف CSV لتحليله",
    type=['csv'],
    help="يمكنك رفع ملف CSV بحد أقصى 200 ميجابايت"
)

if uploaded_file is not None:
    try:
        # قراءة ملف CSV
        df = pd.read_csv(uploaded_file)
        
        # عرض معلومات أساسية
        st.success("✅ تم رفع الملف بنجاح!")
        
        # عرض معاينة البيانات
        st.subheader("👁️ معاينة البيانات")
        st.dataframe(df.head(10), use_container_width=True)
        
        st.markdown("---")
        
        # حساب الإحصائيات
        st.subheader("📈 الإحصائيات")
        
        # الحقول المستثناة من حساب الأعمدة المكتملة
        excluded_columns = ['CreatedAt', 'ModifiedAt', 'DeletedAt', 'IsDeleted', 
                           'CreatedById', 'ModifiedById', 'DeletedById', 'Governorate']
        
        # حساب عدد الأعمدة المكتملة (بدون بيانات فارغة) مع استثناء الحقول المحددة
        columns_to_check = [col for col in df.columns if col not in excluded_columns]
        complete_columns = []
        for col in columns_to_check:
            if df[col].notna().all():  # إذا كان العمود لا يحتوي على أي بيانات فارغة
                complete_columns.append(col)
        complete_columns_count = len(complete_columns)
        
        # إنشاء أعمدة لعرض الإحصائيات
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="عدد الصفوف",
                value=f"{len(df):,}"
            )
        
        with col2:
            st.metric(
                label="عدد الأعمدة",
                value=f"{len(df.columns):,}"
            )
        
        with col3:
            # حساب عدد الصفوف المكررة
            duplicate_rows = df.duplicated().sum()
            st.metric(
                label="عدد الصفوف المكررة",
                value=f"{duplicate_rows:,}"
            )
        
        with col4:
            st.metric(
                label="عدد الأعمدة المكتملة",
                value=f"{complete_columns_count:,}",
                help="الأعمدة المكتملة (بدون بيانات فارغة) باستثناء: CreatedAt, ModifiedAt, DeletedAt, IsDeleted, CreatedById, ModifiedById, DeletedById, Governorate"
            )
        
        st.markdown("---")
        
        # عرض الأعمدة المكتملة
        st.subheader("✅ الأعمدة المكتملة")
        
        # حساب حالة جميع الأعمدة (مكتملة أم لا)
        all_columns_status = []
        for col in columns_to_check:
            missing_count = df[col].isnull().sum()
            complete_count = df[col].notna().sum()
            completion_rate = (complete_count / len(df) * 100) if len(df) > 0 else 0
            is_complete = missing_count == 0
            
            all_columns_status.append({
                'اسم العمود': col,
                'حالة الاكتمال': '✅ مكتمل' if is_complete else '❌ غير مكتمل',
                'عدد البيانات المكتملة': complete_count,
                'عدد البيانات الفارغة': missing_count,
                'نسبة الاكتمال': f"{completion_rate:.2f}%",
                'نوع البيانات': str(df[col].dtype)
            })
        
        all_columns_df = pd.DataFrame(all_columns_status)
        
        # إضافة حقل بحث للفلترة في جميع الأعمدة
        search_term = st.text_input(
            "🔍 البحث في جميع الأعمدة:",
            placeholder="اكتب اسم العمود للبحث (مثل: Id, BookNumber, FilePath...)",
            key="search_all_columns"
        )
        
        # فلترة الأعمدة حسب البحث
        if search_term:
            filtered_df = all_columns_df[
                all_columns_df['اسم العمود'].str.contains(
                    search_term, 
                    case=False, 
                    na=False
                )
            ]
            
            if len(filtered_df) > 0:
                st.metric(
                    label="عدد الأعمدة الموجودة (بعد الفلترة)",
                    value=f"{len(filtered_df):,}"
                )
                st.dataframe(
                    filtered_df, 
                    use_container_width=True, 
                    hide_index=True
                )
            else:
                st.warning(f"⚠️ لم يتم العثور على أعمدة تطابق البحث: '{search_term}'")
                st.info("💡 جرب البحث بأسماء الأعمدة الموجودة في الجدول")
        else:
            # عرض الأعمدة المكتملة فقط إذا لم يكن هناك بحث
            if complete_columns_count > 0:
                st.markdown("#### الأعمدة المكتملة فقط:")
                complete_columns_df = pd.DataFrame({
                    'اسم العمود': complete_columns,
                    'عدد الصفوف المكتملة': [len(df)] * len(complete_columns),
                    'نسبة الاكتمال': ['100%'] * len(complete_columns),
                    'نوع البيانات': [str(df[col].dtype) for col in complete_columns]
                })
                st.dataframe(
                    complete_columns_df, 
                    use_container_width=True, 
                    hide_index=True
                )
            
            # زر لعرض جميع الأعمدة
            if st.button("📋 عرض جميع الأعمدة مع حالتها"):
                st.markdown("#### جميع الأعمدة مع حالة الاكتمال:")
                st.dataframe(
                    all_columns_df, 
                    use_container_width=True, 
                    hide_index=True
                )
        
        # عرض الأعمدة المستثناة
        excluded_found = [col for col in excluded_columns if col in df.columns]
        if excluded_found:
            st.info(f"""
            **ملاحظة:** تم استثناء الحقول التالية من الحساب: 
            {', '.join(excluded_found)}
            """)
        
        st.markdown("---")
        
        # البحث عن كلمات معينة في البيانات
        st.markdown("#### 🔎 البحث عن كلمات في البيانات")
        word_search = st.text_input(
            "ابحث عن كلمة أو نص معين:",
            placeholder="مثال: بلا، null، فارغ...",
            key="word_search"
        )
        
        if word_search:
            # البحث عن الكلمة في جميع الأعمدة
            word_results = []
            total_occurrences = 0
            
            for col in columns_to_check:
                # تحويل جميع القيم إلى نص والبحث عن الكلمة
                col_text = df[col].astype(str)
                matches = col_text.str.contains(word_search, case=False, na=False)
                count = matches.sum()
                
                if count > 0:
                    word_results.append({
                        'اسم العمود': col,
                        'عدد مرات الظهور': count,
                        'نسبة الظهور': f"{(count / len(df) * 100):.2f}%"
                    })
                    total_occurrences += count
            
            if len(word_results) > 0:
                st.success(f"✅ تم العثور على الكلمة '{word_search}' في {len(word_results)} عمود")
                
                # عرض الإحصائية الإجمالية
                col1, col2 = st.columns(2)
                with col1:
                    st.metric(
                        label="إجمالي مرات الظهور",
                        value=f"{total_occurrences:,}"
                    )
                with col2:
                    st.metric(
                        label="عدد الأعمدة التي تحتوي على الكلمة",
                        value=f"{len(word_results):,}"
                    )
                
                # عرض جدول النتائج
                word_results_df = pd.DataFrame(word_results)
                word_results_df = word_results_df.sort_values('عدد مرات الظهور', ascending=False)
                st.dataframe(
                    word_results_df,
                    use_container_width=True,
                    hide_index=True
                )
                
                # عرض أمثلة من البيانات
                st.markdown("##### أمثلة من البيانات التي تحتوي على الكلمة:")
                example_rows = []
                for col in columns_to_check:
                    col_text = df[col].astype(str)
                    matches = col_text.str.contains(word_search, case=False, na=False)
                    if matches.any():
                        matched_indices = df.loc[matches].index[:3].tolist()  # أول 3 أمثلة
                        for idx in matched_indices:
                            example_rows.append({
                                'اسم العمود': col,
                                'رقم الصف': idx + 1,
                                'القيمة': str(df.loc[idx, col])[:100]  # أول 100 حرف
                            })
                
                if example_rows:
                    example_df = pd.DataFrame(example_rows[:10])  # أول 10 أمثلة
                    st.dataframe(
                        example_df,
                        use_container_width=True,
                        hide_index=True
                    )
            else:
                st.warning(f"⚠️ لم يتم العثور على الكلمة '{word_search}' في أي عمود")
                st.info("💡 تأكد من كتابة الكلمة بشكل صحيح")
        
        st.markdown("---")
        
        # تحليل البيانات الفارغة
        st.subheader("🔍 تحليل البيانات الفارغة")
        
        # حساب البيانات الفارغة لكل عمود
        missing_data = df.isnull().sum()
        total_missing = missing_data.sum()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric(
                label="إجمالي البيانات الفارغة",
                value=f"{total_missing:,}"
            )
        
        with col2:
            # حساب نسبة البيانات الفارغة
            total_cells = len(df) * len(df.columns)
            missing_percentage = (total_missing / total_cells * 100) if total_cells > 0 else 0
            st.metric(
                label="نسبة البيانات الفارغة",
                value=f"{missing_percentage:.2f}%"
            )
        
        # عرض جدول تفصيلي للبيانات الفارغة
        if total_missing > 0:
            st.markdown("#### تفاصيل البيانات الفارغة حسب العمود:")
            missing_df = pd.DataFrame({
                'العمود': missing_data.index,
                'عدد البيانات الفارغة': missing_data.values,
                'النسبة المئوية': (missing_data.values / len(df) * 100).round(2)
            })
            missing_df = missing_df[missing_df['عدد البيانات الفارغة'] > 0].sort_values(
                'عدد البيانات الفارغة', 
                ascending=False
            )
            st.dataframe(missing_df, use_container_width=True, hide_index=True)
        else:
            st.info("✨ لا توجد بيانات فارغة في الملف!")
        
        st.markdown("---")
        
        # معلومات إضافية
        st.subheader("ℹ️ معلومات إضافية")
        
        info_col1, info_col2 = st.columns(2)
        
        with info_col1:
            st.markdown("**أسماء الأعمدة:**")
            st.write(", ".join(df.columns.tolist()))
        
        with info_col2:
            st.markdown("**أنواع البيانات:**")
            dtype_info = df.dtypes.astype(str).to_dict()
            for col, dtype in dtype_info.items():
                st.write(f"- {col}: {dtype}")
        
    except Exception as e:
        st.error(f"❌ حدث خطأ أثناء قراءة الملف: {str(e)}")
        st.info("تأكد من أن الملف بصيغة CSV صحيحة")

else:
    # رسالة ترحيبية عند عدم رفع ملف
    st.info("👆 يرجى رفع ملف CSV لبدء التحليل")
    
    st.markdown("""
    ### المميزات:
    - ✅ رفع ملفات CSV بسهولة
    - 📊 عرض إحصائيات شاملة
    - 🔍 تحليل البيانات الفارغة
    - 📈 اكتشاف الصفوف المكررة
    - 👁️ معاينة البيانات
    """)
