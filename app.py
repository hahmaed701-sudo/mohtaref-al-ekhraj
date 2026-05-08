
import os, json
import streamlit as st
from modules.models import *
from modules.state import init_state, default_scene, default_shot, save_video, ensure_library
from modules.prompt_engine import build_shot_prompt, build_full_scene_prompt
from modules.utils import trim_prompt, split_lines_to_shots, now_label
from modules.runway import build_payload, create_task, poll_task, extract_video_url

st.set_page_config(page_title="محترف الإخراج", page_icon="🎬", layout="wide")
RUNWAY_API_KEY = os.getenv("RUNWAYML_API_SECRET", "")
init_state()

st.markdown("""
<style>
.stApp {background:#080812;color:#f5f2ff;direction:rtl}
[data-testid="stSidebar"] {background:linear-gradient(180deg,#0c0c18,#17112b)}
.block-container {padding-top:1rem}
div[data-testid="stExpander"] {border:1px solid #33285c;border-radius:14px}
.stButton button {border-radius:12px;font-weight:800}
.badge{display:inline-block;padding:6px 12px;margin:3px;border-radius:999px;background:#24184d;color:#f2e9ff;border:1px solid #8a65ff}
.logo{font-size:36px;font-weight:900;color:#f7d58a}
</style>
""", unsafe_allow_html=True)

c1, c2 = st.columns([3,1])
with c1:
    st.markdown('<div class="logo">🎬 محترف الإخراج</div><div>AI Drama Director Studio</div>', unsafe_allow_html=True)
with c2:
    st.success("Runway Key ✅" if RUNWAY_API_KEY else "Runway Key ❌")

st.sidebar.header("🎞️ هوية الفيلم")
project_type = st.sidebar.selectbox("نوع المشروع", PROJECT_TYPES)
director_style = st.sidebar.selectbox("أسلوب الإخراج", DIRECTOR_STYLES)
camera = st.sidebar.selectbox("نوع الكاميرا", CAMERAS)
model = st.sidebar.selectbox("نوع الأداة / الموديل", list(MODEL_FEATURES.keys()), index=0)
features = MODEL_FEATURES[model]
duration = st.sidebar.selectbox("مدة Runway حسب الموديل", features["durations"], index=min(2, len(features["durations"])-1))
ratio = st.sidebar.selectbox("الاتجاه / المقاس", features["ratios"], index=0)
generation_mode = st.sidebar.radio("🎬 وضع التوليد", ["Runway حقيقي", "Mock / تجربة بدون رصيد"], index=0)
st.sidebar.caption(f"أقصى مدة لهذا الموديل: {features['max_duration']} ثانية")

global_settings = {"project_type":project_type,"director_style":director_style,"camera":camera,"model":model,"duration":duration,"ratio":ratio}

st.markdown('<span class="badge">🎯 الالتزام الكامل دائمًا</span><span class="badge">📸 الواقعية القصوى دائمًا</span><span class="badge">👤 حماية الوجه دائمًا</span><span class="badge">🔒 قفل المشهد دائمًا</span>', unsafe_allow_html=True)
st.divider()

def collect_reference_urls(scene):
    urls = []
    for key in ["characters","clothing","environment","color_urls"]:
        for u in scene.get("refs",{}).get(key,[]):
            if u and isinstance(u,str) and (u.startswith("http") or u.startswith("runway://")):
                urls.append(u)
    return urls[:9]

def nearest_allowed(value, allowed):
    return min(allowed, key=lambda x: abs(int(x)-int(value)))

def run_generation(scene, prompt, shot=None, is_full_scene=False, use_duration=None):
    runway_prompt = trim_prompt(prompt, 950)
    refs = collect_reference_urls(scene) if features.get("supports_image_refs") else []
    video_refs = scene.get("refs",{}).get("video_urls",[])[:3] if features.get("supports_video_refs") else []
    audio_refs = scene.get("refs",{}).get("audio_urls",[])[:3] if features.get("supports_audio_refs") else []
    final_duration = nearest_allowed(use_duration or duration, features["durations"])
    if generation_mode == "Mock / تجربة بدون رصيد":
        record = {"type":"full_scene" if is_full_scene else "shot","shot_number":"All" if is_full_scene else shot.get("number"),"shot_title":"المشهد كامل" if is_full_scene else shot.get("title"),"video_url":"","prompt":runway_prompt,"model":model,"duration":final_duration,"ratio":ratio,"status":"Mock","created_at":now_label()}
        save_video(scene["id"], record)
        return record
    payload = build_payload(model, runway_prompt, final_duration, ratio, refs, video_refs, audio_refs)
    st.json(payload)
    task = create_task(RUNWAY_API_KEY, payload)
    task_id = task.get("id") or task.get("taskId")
    if not task_id:
        raise RuntimeError(f"لم يرجع Runway رقم مهمة: {task}")
    with st.spinner("جاري انتظار نتيجة Runway..."):
        completed = poll_task(RUNWAY_API_KEY, task_id)
    if (completed.get("status") or "").upper() != "SUCCEEDED":
        raise RuntimeError(f"فشل التوليد: {completed}")
    video_url = extract_video_url(completed)
    record = {"type":"full_scene" if is_full_scene else "shot","shot_number":"All" if is_full_scene else shot.get("number"),"shot_title":"المشهد كامل" if is_full_scene else shot.get("title"),"video_url":video_url,"prompt":runway_prompt,"model":model,"duration":final_duration,"ratio":ratio,"status":"تم التوليد","created_at":now_label()}
    save_video(scene["id"], record)
    return record

def reference_block(scene, key, label):
    st.markdown(f"**{label}**")
    files = st.file_uploader(f"رفع صور {label}", type=["jpg","jpeg","png","webp"], accept_multiple_files=True, key=f"{scene['id']}_{key}_files")
    if files:
        cols = st.columns(4)
        for idx, f in enumerate(files[:12]):
            cols[idx % 4].image(f, caption=f.name, use_container_width=True)
    urls = st.text_area(f"روابط عامة تُرسل فعليًا إلى Runway — {label}", key=f"{scene['id']}_{key}_urls", help="ضع كل رابط في سطر. الصور المرفوعة محليًا معاينة فقط.")
    scene["refs"][key] = [u.strip() for u in urls.splitlines() if u.strip()]

st.subheader("🎬 المشاهد واللقطات")
target = st.number_input("عدد المشاهد", 1, 20, len(st.session_state.scenes))
if st.button("تطبيق عدد المشاهد"):
    while len(st.session_state.scenes) < target:
        st.session_state.scenes.append(default_scene(len(st.session_state.scenes)+1))
    st.session_state.scenes = st.session_state.scenes[:target]
    st.rerun()

for si, scene in enumerate(st.session_state.scenes):
    scene["number"] = si + 1
    with st.expander(f"🎬 المشهد {scene['number']} — {scene.get('title','')}", expanded=(si==0)):
        left, right = st.columns([2,1])
        with left:
            scene["title"] = st.text_input("عنوان المشهد", value=scene.get("title",""), key=f"title_{scene['id']}")
            scene["description"] = st.text_area("الوصف العام للمشهد", value=scene.get("description",""), height=120, key=f"desc_{scene['id']}")
            scene["storyboard_text"] = st.text_area("Storyboard نصي", value=scene.get("storyboard_text",""), height=90, key=f"sbtxt_{scene['id']}")
            sb_img = st.file_uploader("Storyboard صورة", type=["jpg","jpeg","png"], key=f"sbimg_{scene['id']}")
            if sb_img:
                st.image(sb_img, width=240)
        with right:
            scene["duration"] = st.number_input("مدة المشهد", 5, 180, int(scene.get("duration",10)), key=f"scdur_{scene['id']}")
            scene["lighting"] = st.selectbox("إضاءة المشهد", LIGHTS, key=f"light_{scene['id']}")
            scene["clothing"] = st.text_input("اللبس", value=scene.get("clothing",""), key=f"cloth_{scene['id']}")
            scene["environment"] = st.text_input("البيئة", value=scene.get("environment",""), key=f"env_{scene['id']}")
            scene["color_mode"] = st.radio("اللون / LUT", ["رفع صورة مرجعية للون", "Flat / Log"], index=1 if scene.get("color_mode")=="Flat / Log" else 0, key=f"colorm_{scene['id']}")
            color_img = st.file_uploader("صورة مرجعية للون", type=["jpg","jpeg","png"], key=f"colorfile_{scene['id']}")
            scene["has_color_ref"] = bool(color_img)
            if color_img: st.image(color_img, width=160)

        st.markdown("### 👤 الشخصيات")
        char_count = st.number_input("عدد الشخصيات", 1, 10, max(1, len(scene.get("characters",[])) or 1), key=f"chcount_{scene['id']}")
        while len(scene["characters"]) < char_count:
            scene["characters"].append({"name":"","description":"","wardrobe":""})
        scene["characters"] = scene["characters"][:char_count]
        for ci, ch in enumerate(scene["characters"]):
            cc = st.columns(3)
            ch["name"] = cc[0].text_input(f"اسم الشخصية {ci+1}", value=ch.get("name",""), key=f"chname_{scene['id']}_{ci}")
            ch["description"] = cc[1].text_input("وصف الشخصية", value=ch.get("description",""), key=f"chdesc_{scene['id']}_{ci}")
            ch["wardrobe"] = cc[2].text_input("لبس الشخصية", value=ch.get("wardrobe",""), key=f"chward_{scene['id']}_{ci}")

        st.markdown("### 📚 مراجع المشهد")
        r1, r2, r3 = st.columns(3)
        with r1: reference_block(scene, "clothing", "مراجع اللبس")
        with r2: reference_block(scene, "characters", "مراجع الشخصيات")
        with r3: reference_block(scene, "environment", "مراجع البيئة")
        if features.get("supports_video_refs"):
            scene["refs"]["video_urls"] = [u.strip() for u in st.text_area("مراجع فيديو seedance2 — روابط عامة", key=f"vrefs_{scene['id']}").splitlines() if u.strip()]
        if features.get("supports_audio_refs"):
            scene["refs"]["audio_urls"] = [u.strip() for u in st.text_area("مراجع صوت seedance2 — روابط عامة", key=f"arefs_{scene['id']}").splitlines() if u.strip()]

        if st.button("🎞️ تقسيم المشهد إلى لقطات حسب الاستوري بورد / الوصف", key=f"split_{scene['id']}"):
            lines = split_lines_to_shots(scene.get("storyboard_text") or scene.get("description"))
            if not lines: lines = [scene.get("description") or "لقطة افتتاحية"]
            scene["shots"] = []
            for i, line in enumerate(lines, 1):
                sh = default_shot(i)
                sh["description"] = line
                scene["shots"].append(sh)
            st.rerun()

        st.markdown("### 🎞️ اللقطات")
        if st.button("➕ إضافة لقطة جديدة", key=f"addshot_{scene['id']}"):
            scene["shots"].append(default_shot(len(scene["shots"])+1)); st.rerun()

        for shi, shot in enumerate(scene["shots"]):
            shot["number"] = shi + 1
            with st.container(border=True):
                cols = st.columns([2,1,1,1])
                shot["title"] = cols[0].text_input("عنوان اللقطة", value=shot.get("title",""), key=f"shtitle_{scene['id']}_{shi}")
                shot["duration"] = cols[1].number_input("الزمن", 1, 15, int(shot.get("duration",5)), key=f"shdur_{scene['id']}_{shi}")
                shot["lens"] = cols[2].selectbox("العدسة", LENSES, index=LENSES.index(shot.get("lens","50mm")) if shot.get("lens") in LENSES else 3, key=f"lens_{scene['id']}_{shi}")
                shot["type"] = cols[3].selectbox("نوع اللقطة", SHOT_TYPES, index=SHOT_TYPES.index(shot.get("type","Medium")) if shot.get("type") in SHOT_TYPES else 1, key=f"type_{scene['id']}_{shi}")
                shot["description"] = st.text_area("وصف اللقطة", value=shot.get("description",""), height=80, key=f"shdesc_{scene['id']}_{shi}")
                m = st.columns(4)
                shot["movement"] = m[0].selectbox("حركة الكاميرا", MOVEMENTS, key=f"move_{scene['id']}_{shi}")
                shot["transition"] = m[1].selectbox("الانتقال", TRANSITIONS, key=f"trans_{scene['id']}_{shi}")
                shot["filter"] = m[2].selectbox("فلتر النعومة", FILTERS, key=f"filter_{scene['id']}_{shi}")
                shot["status"] = m[3].selectbox("الحالة", ["غير مكتملة","جاهزة للتوليد","تم توليدها","معتمدة","فشل التوليد"], key=f"status_{scene['id']}_{shi}")
                shot["dialogue"] = st.text_area("الحوار", value=shot.get("dialogue",""), height=60, key=f"dialog_{scene['id']}_{shi}")
                a,b = st.columns(2)
                shot["music"] = a.text_input("الموسيقى", value=shot.get("music",""), key=f"music_{scene['id']}_{shi}")
                shot["sfx"] = b.text_input("المؤثرات", value=shot.get("sfx",""), key=f"sfx_{scene['id']}_{shi}")
                prompt = build_shot_prompt(global_settings, scene, shot)
                with st.expander("✍️ البرومبت النهائي"):
                    st.code(trim_prompt(prompt, 1400))

                b1,b2,b3,b4 = st.columns(4)
                if b1.button("🎥 توليد هذه اللقطة فقط", key=f"gen_{scene['id']}_{shi}"):
                    try:
                        run_generation(scene, prompt, shot=shot, is_full_scene=False, use_duration=shot["duration"])
                        shot["status"] = "تم توليدها"
                        st.success("تم حفظ الفيديو في مكتبة المشهد.")
                        st.rerun()
                    except Exception as e:
                        shot["status"] = "فشل التوليد"
                        st.error(str(e))
                if b2.button("➕ إضافة لقطة بعد هذه", key=f"ins_{scene['id']}_{shi}"):
                    scene["shots"].insert(shi+1, default_shot(shi+2)); st.rerun()
                if b3.button("📑 نسخ اللقطة", key=f"dup_{scene['id']}_{shi}"):
                    new = dict(shot); new["id"] = f"shot_{len(scene['shots'])+1}"; scene["shots"].insert(shi+1, new); st.rerun()
                if b4.button("🗑️ حذف اللقطة", key=f"del_{scene['id']}_{shi}"):
                    scene["shots"].pop(shi); st.rerun()

        if st.button("🎬 توليد المشهد كامل كفيديو متصل", key=f"genfull_{scene['id']}"):
            try:
                full_prompt = build_full_scene_prompt(global_settings, scene, scene["shots"])
                run_generation(scene, full_prompt, is_full_scene=True, use_duration=scene["duration"])
                st.success("تم توليد المشهد الكامل وحفظه.")
                st.rerun()
            except Exception as e:
                st.error(str(e))

        st.markdown("### 📚 مكتبة فيديوهات المشهد")
        ensure_library(scene["id"])
        lib = st.session_state.scene_video_library.get(scene["id"], [])
        if not lib: st.info("لا توجد فيديوهات بعد.")
        for vi, rec in enumerate(lib):
            with st.container(border=True):
                st.markdown(f"**{rec.get('shot_title')}** — {rec.get('status')} — {rec.get('created_at')}")
                if rec.get("video_url"): st.video(rec["video_url"])
                else: st.warning("Mock أو لم يرجع رابط فيديو.")
                st.caption(f"Model: {rec.get('model')} | Duration: {rec.get('duration')} | Ratio: {rec.get('ratio')}")
                with st.expander("Prompt"): st.code(rec.get("prompt",""))
                vc = st.columns(3)
                if vc[0].button("⭐ اعتماد", key=f"app_{scene['id']}_{vi}"):
                    rec["approved"] = True; st.rerun()
                if vc[1].button("📋 عرض البرومبت", key=f"prompt_{scene['id']}_{vi}"):
                    st.code(rec.get("prompt",""))
                if vc[2].button("🗑️ حذف", key=f"delvid_{scene['id']}_{vi}"):
                    lib.pop(vi); st.rerun()

st.divider()
st.subheader("📦 تصدير المشروع")
if st.button("تصدير JSON"):
    data = {"global": global_settings, "scenes": st.session_state.scenes, "video_library": st.session_state.scene_video_library}
    st.download_button("تحميل JSON", json.dumps(data, ensure_ascii=False, indent=2), file_name="mohtaref_project.json", mime="application/json")
