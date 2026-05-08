
import streamlit as st
import os

st.set_page_config(page_title="محترف الإخراج", layout="wide")

RUNWAY_API_KEY = os.getenv("RUNWAYML_API_SECRET", "")

st.title("🎬 محترف الإخراج")
st.caption("AI Drama Director Studio")

st.sidebar.header("هوية الفيلم")

project_type = st.sidebar.selectbox("نوع المشروع", ["دراما", "إعلان", "فيلم قصير"])
style = st.sidebar.selectbox("أسلوب الإخراج", ["سينمائي واقعي", "هوليوودي", "وثائقي"])
camera = st.sidebar.selectbox("نوع الكاميرا", ["ARRI Alexa", "RED", "Sony FX3"])
model = st.sidebar.selectbox("الموديل", ["seedance2", "veo3.1_fast", "veo3.1"])

if model == "seedance2":
    duration = st.sidebar.slider("مدة الفيديو", 5, 15, 10)
else:
    duration = st.sidebar.selectbox("مدة الفيديو", [4,6,8])

ratio = st.sidebar.selectbox("المقاس", ["1920:1080", "1080:1920", "1440:1440"])

st.success("Runway Key: ✅ موجود" if RUNWAY_API_KEY else "Runway Key: ❌ غير موجود")

st.header("🎬 المشاهد")

scene_count = st.number_input("عدد المشاهد", 1, 20, 1)

for s in range(scene_count):
    with st.expander(f"المشهد {s+1}", expanded=True):

        scene_title = st.text_input(f"عنوان المشهد {s+1}")
        scene_desc = st.text_area(f"الوصف العام للمشهد {s+1}")

        storyboard = st.file_uploader(
            f"رفع Storyboard للمشهد {s+1}",
            type=["png", "jpg", "jpeg"],
            key=f"sb{s}"
        )

        lighting = st.selectbox(
            "إضاءة المشهد",
            ["Golden Hour", "Soft Cinematic", "Night Lantern"],
            key=f"light{s}"
        )

        st.subheader("الشخصيات")
        chars = st.text_area("اكتب الشخصيات")

        st.subheader("مراجع المشهد")
        refs = st.file_uploader(
            "رفع صور مرجعية",
            accept_multiple_files=True,
            type=["png","jpg","jpeg"],
            key=f"refs{s}"
        )

        st.subheader("🎞️ اللقطات")

        shot_count = st.number_input(
            f"عدد اللقطات للمشهد {s+1}",
            1, 50, 1,
            key=f"shots{s}"
        )

        for sh in range(shot_count):
            with st.container(border=True):
                st.markdown(f"### اللقطة {sh+1}")

                shot_desc = st.text_area(
                    "وصف اللقطة",
                    key=f"shotdesc{s}{sh}"
                )

                shot_duration = st.number_input(
                    "زمن اللقطة",
                    1, 15, 5,
                    key=f"shotdur{s}{sh}"
                )

                lens = st.selectbox(
                    "العدسة",
                    ["24mm", "35mm", "50mm", "85mm"],
                    key=f"lens{s}{sh}"
                )

                shot_type = st.selectbox(
                    "نوع اللقطة",
                    ["Wide", "Medium", "Close-up"],
                    key=f"type{s}{sh}"
                )

                move = st.selectbox(
                    "حركة الكاميرا",
                    ["Static", "Dolly In", "Handheld"],
                    key=f"move{s}{sh}"
                )

                dialogue = st.text_area(
                    "الحوار",
                    key=f"dialog{s}{sh}"
                )

                if st.button(f"🎥 توليد هذه اللقطة فقط", key=f"gen{s}{sh}"):
                    st.info(f"سيتم توليد اللقطة بزمن {shot_duration} ثانية")

        if st.button(f"🎬 توليد المشهد كامل كفيديو متصل", key=f"scene{s}"):
            st.success(
                f"سيتم توليد المشهد الكامل بزمن {duration} ثانية مع استمرارية بين اللقطات"
            )

st.header("📚 مكتبة الفيديو")
st.info("ستظهر هنا الفيديوهات المولدة من Runway")
