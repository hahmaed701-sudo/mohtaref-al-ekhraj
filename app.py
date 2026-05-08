import os, json, time, zipfile, io, base64, re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

import requests
import streamlit as st
from dotenv import load_dotenv
from PIL import Image

load_dotenv()

APP_NAME_AR = "محترف الإخراج"
APP_NAME_EN = "Mohtaref Al Ekhraj"
RUNWAY_API_KEY = os.getenv("RUNWAYML_API_SECRET") or st.secrets.get("RUNWAYML_API_SECRET", "") if hasattr(st, 'secrets') else os.getenv("RUNWAYML_API_SECRET", "")
RUNWAY_URL = "https://api.dev.runwayml.com/v1/text_to_video"
RUNWAY_TASK_URL = "https://api.dev.runwayml.com/v1/tasks/{task_id}"
RUNWAY_VERSION = "2024-11-06"
PROJECTS_DIR = Path("projects")
PROJECTS_DIR.mkdir(exist_ok=True)

MODELS = ["veo3.1_fast", "veo3.1", "seedance2", "kling3.0_standard"]
MODEL_DURATION_MAP = {m: [4, 6, 8] for m in MODELS}
RATIOS = {
    "🎬 عرضي 1920:1080": "1920:1080",
    "📱 طولي 1080:1920": "1080:1920",
    "◼️ مربع 1440:1440": "1440:1440",
}
SHOT_TYPES = ["Wide", "Medium", "Close-up", "Extreme Close-up", "Two Shot", "Over Shoulder", "POV", "Insert", "Reaction Shot"]
ANGLES = ["Eye Level", "Low Angle", "High Angle", "Dutch Angle", "Top Shot", "Over Shoulder"]
MOVEMENTS = ["Static", "Dolly In", "Dolly Out", "Pan", "Tilt", "Handheld", "Crane", "Drone", "Slow Push-in", "Zoom", "Slider"]
FPS_OPTIONS = [24, 25, 30, 50, 60]
CAMERAS = ["ARRI Alexa Mini LF", "RED Komodo", "RED V-Raptor", "Sony Venice", "Sony FX3", "Blackmagic URSA Mini Pro", "Canon C70", "Phantom Flex", "Documentary handheld camera", "Custom camera"]
LENSES = ["16mm Wide Lens", "24mm Cinema Lens", "35mm Cinema Lens", "50mm Prime Lens", "85mm Portrait Lens", "100mm Macro Lens", "70-200mm Telephoto Lens", "Anamorphic Lens", "Vintage Cinema Lens", "Custom Lens"]
LIGHT_PRESETS = ["Soft Cinematic Key Light", "Golden Hour", "Window Light", "Diffused Studio Light", "Warm Yemeni Indoor", "Documentary Natural", "Moody Drama", "Commercial Beauty Light", "Soft Interview Lighting", "Lantern Night Light", "Realistic Museum Light"]
DIFFUSION = ["No Filter", "Black Pro Mist 1/8", "Black Pro Mist 1/4", "Black Pro Mist 1/2", "Hollywood Black Magic", "Soft FX", "Glimmerglass", "Natural Skin Softening"]
COLOR_MODES = ["Cinematic LUT", "Flat / Log", "Natural Rec709", "Warm Yemeni Earthy", "Documentary Neutral", "Dark Dramatic", "Luxury Gold"]
YEMEN_ENV = ["None", "حضرموت - وادي دوعن", "سيئون - شوارع طينية", "شبام", "تريم", "المكلا", "سوق شعبي", "متحف تراثي", "بيت طيني"]
YEMEN_CLOTHES = ["None", "ثوب يمني", "عمامة حضرمية", "معوز", "جنبية", "ملابس ريفية", "ملابس حضرمية قديمة"]
YEMEN_CHARS = ["None", "رجل يمني كبير", "شاب يمني", "امرأة يمنية", "طفل يمني", "فلاح", "مذيع", "شيخ قبيلة"]
YEMEN_DIALECTS = ["فصحى", "يمنية", "حضرمية", "بدون كلام"]
FILM_STYLES = ["Hollywood", "Netflix", "Documentary", "Arabic Drama", "Yemeni Heritage", "Dark Thriller", "Sports", "Luxury Commercial"]
PREVIEW_PROVIDERS = ["Manual Upload", "Mock Preview", "Runway Image", "Nano Banana", "OpenAI Image"]

st.set_page_config(page_title=f"{APP_NAME_AR} | {APP_NAME_EN}", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
html, body, [data-testid="stAppViewContainer"] { background: radial-gradient(circle at top left,#25164a 0,#090914 32%,#050507 100%); color:#f7f7fb; }
[data-testid="stSidebar"] { background: linear-gradient(180deg,#100b22,#07070b); border-left:1px solid rgba(160,120,255,.16); }
.block-container { padding-top: 1.4rem; padding-bottom: 2rem; }
.card { border:1px solid rgba(160,120,255,.18); border-radius:20px; padding:18px; background:rgba(12,12,22,.72); box-shadow: 0 12px 35px rgba(0,0,0,.25); margin-bottom:16px; }
.hero { border:1px solid rgba(255,215,128,.2); border-radius:28px; padding:24px; background:linear-gradient(135deg,rgba(91,50,255,.24),rgba(255,196,87,.08)); box-shadow:0 20px 50px rgba(0,0,0,.35); }
.badge { display:inline-block; padding:6px 10px; border-radius:999px; background:rgba(126,92,255,.18); color:#e6ddff; border:1px solid rgba(162,134,255,.28); margin:3px; font-size:.85rem; }
.success-badge { background:rgba(35,180,110,.16); border-color:rgba(35,180,110,.35); color:#b9ffd8; }
.warn-badge { background:rgba(255,185,68,.16); border-color:rgba(255,185,68,.35); color:#ffe3a7; }
.stButton>button { border-radius:14px; border:1px solid rgba(160,120,255,.35); background:linear-gradient(135deg,#6a4cff,#9f68ff); color:white; font-weight:700; }
.stDownloadButton>button { border-radius:14px; }
textarea, input, .stSelectbox div { border-radius:12px !important; }
</style>
""", unsafe_allow_html=True)

T = {
    "ar": {
        "title": "🎬 محترف الإخراج", "subtitle": "منصة إخراج سينمائي بالذكاء الاصطناعي", "safe":"🛡️ الوضع الآمن", "strict":"🎯 وضع الالتزام الكامل", "realism":"📸 الواقعية القصوى", "face":"👤 حماية ملامح الشخصية", "scene_lock":"🔒 قفل المشهد الأصلي", "anatomy":"✋ حماية الجسم والأطراف", "expansion":"🖼️ حماية توسعة الكادر", "deform":"🚫 منع التشوهات", "real_ai":"🎥 مزج الواقعي بالذكاء الاصطناعي", "generate":"🎥 توليد فيديو Runway", "prompt":"🎬 توليد البرومبت", "allshots":"🎥 توليد كل لقطات المشهد", "previews":"🖼️ توليد صور كل اللقطات", "split":"🎞️ تقسيم المشهد تلقائيًا", "save":"💾 حفظ المشروع", "save_as":"💾 حفظ باسم", "load":"📁 فتح مشروع", "export":"📦 تصدير المشروع", "preview_provider":"🖼️ محرك المعاينة البصرية"},
    "en": {
        "title": "🎬 Mohtaref Al Ekhraj", "subtitle": "AI Cinematic Directing Studio", "safe":"🛡️ Safe Mode", "strict":"🎯 Strict Director Mode", "realism":"📸 Ultra Realism", "face":"👤 Face Protection", "scene_lock":"🔒 Scene Lock", "anatomy":"✋ Anatomy Protection", "expansion":"🖼️ Camera Expansion Protection", "deform":"🚫 Anti-Deformation", "real_ai":"🎥 Real Footage + AI Mode", "generate":"🎥 Generate Runway Video", "prompt":"🎬 Generate Prompt", "allshots":"🎥 Generate All Scene Shots", "previews":"🖼️ Generate All Shot Previews", "split":"🎞️ Auto Split Scene", "save":"💾 Save Project", "save_as":"💾 Save As", "load":"📁 Load Project", "export":"📦 Export Project", "preview_provider":"🖼️ Previsualization Provider"}
}

def tr(key):
    return T.get(st.session_state.get("lang", "ar"), T["ar"]).get(key, key)

def init_state():
    if "lang" not in st.session_state: st.session_state.lang = "ar"
    if "project" not in st.session_state:
        st.session_state.project = {
            "name": "مشروع جديد",
            "created": datetime.now().isoformat(),
            "modified": datetime.now().isoformat(),
            "identity": {}, "yemeni": {}, "library": {}, "characters": [], "scenes": [new_scene(1)],
            "settings": {"safe_mode": True, "model": "veo3.1_fast", "runway_duration": 4, "ratio_label": "🎬 عرضي 1920:1080", "preview_provider": "Mock Preview"}
        }

def new_scene(n:int):
    return {"id": f"scene_{int(time.time()*1000)}_{n}", "title": f"المشهد {n}", "goal":"", "idea":"", "duration_total":60, "emotion":"توتر", "lighting":"Golden Hour", "lut":"Cinematic LUT", "sound":"Ambience", "fps":25, "orientation":"🎬 عرضي 1920:1080", "storyboard_mode":False, "storyboards":[], "color_refs":[], "shots":[new_shot(1)]}

def new_shot(n:int):
    return {"id": f"shot_{int(time.time()*1000)}_{n}", "title": f"Shot {n}", "type":"Wide", "angle":"Eye Level", "movement":"Slow Push-in", "emotion":"توتر", "emotion_notes":"", "lighting":"Golden Hour", "fps":25, "planning_duration":6, "dialogue":"", "voiceover":"", "sound":"", "camera":"ARRI Alexa Mini LF", "lens":"50mm Prime Lens", "diffusion":"Black Pro Mist 1/4", "color_mode":"Cinematic LUT", "flat_log":False, "references":[], "color_refs":[], "storyboard":None, "prompt":"", "preview":None, "video_url":None, "transition":"Cut", "continuity_start":"", "continuity_end":""}

def trim_prompt(prompt, max_chars=950):
    prompt = re.sub(r"\s+", " ", prompt.strip())
    if len(prompt) <= max_chars: return prompt
    return prompt[:max_chars].rsplit(" ", 1)[0] + "..."

def upload_images(label, key, multiple=True):
    files = st.file_uploader(label, type=["jpg","jpeg","png","webp"], accept_multiple_files=multiple, key=key)
    out=[]
    if files:
        flist = files if isinstance(files, list) else [files]
        cols = st.columns(min(4, max(1,len(flist))))
        for i,f in enumerate(flist):
            try:
                img=Image.open(f)
                cols[i % len(cols)].image(img, caption=f.name, use_container_width=True)
                out.append({"name":f.name,"type":"image","note":"uploaded reference"})
            except Exception:
                out.append({"name":f.name,"type":"file","note":"uploaded reference"})
    return out

def build_identity_prompt(project):
    parts=[]
    ident=project.get("identity",{})
    if ident:
        parts.append(f"Directing style: {ident.get('style','cinematic')}, mood: {ident.get('mood','dramatic')}, camera style: {ident.get('camera_style','professional cinema')}.")
    y=project.get("yemeni",{})
    if y and y.get("environment") and y.get("environment") != "None":
        parts.append(f"Authentic Yemeni cultural realism, environment: {y.get('environment')}, clothing: {y.get('clothing')}, character type: {y.get('character')}, dialect: {y.get('dialect')}. Natural Yemeni faces, culturally accurate clothing, no fantasy cultural mixing.")
    lib=project.get("library",{})
    if any(lib.values()):
        parts.append("Maintain consistency with the uploaded project visual reference library: same cinematic identity, environment style, lighting, wardrobe, and visual tone.")
    return " ".join(parts)

def protection_prompt(settings, scene=None, shot=None):
    parts=[]
    if settings.get("strict"): parts.append("Strictly follow the provided direction and references. Do not invent or add new visual elements. Preserve exact framing, wardrobe, environment, and cinematic direction.")
    if settings.get("ultra_realism"): parts.append("Ultra realistic cinematic image, natural skin texture, realistic pores, photorealistic lighting, no AI plastic skin, no CGI look, natural imperfections.")
    if settings.get("face_protection"): parts.append("Maintain identical facial identity across all shots. Do not alter facial structure; preserve eyes, beard, hair, skin tone, age, and identity.")
    if settings.get("real_ai"): parts.append("Blend AI generation with real footage realism. Preserve original people, environment, lighting, wardrobe, and perspective exactly.")
    if settings.get("scene_lock"): parts.append("Do not add new people, locations, or background elements. Preserve original environment exactly.")
    if settings.get("anatomy"): parts.append("Correct human anatomy. Natural hands with five fingers only. Realistic ears, eyes, mouth, and body proportions. No distorted fingers or limbs.")
    if settings.get("expansion"): parts.append("When camera expands or moves, do not invent new locations or objects; extend only what matches the original image.")
    if settings.get("deform"): parts.append("No warped faces, melted skin, distorted hands, duplicated body parts, or AI artifacts.")
    if scene and scene.get("storyboard_mode"): parts.append("Follow uploaded storyboard composition exactly; storyboard overrides framing, composition, movement, and angle.")
    if shot and (shot.get("type") in ["Close-up","Extreme Close-up"]): parts.append("Natural facial skin texture, professional beauty lighting, natural eye reflections, soft cinematic diffusion.")
    return " ".join(parts)

def build_shot_prompt(project, scene, shot):
    settings = project.get("settings", {})
    parts = []
    parts.append(build_identity_prompt(project))
    parts.append(f"Scene: {scene.get('title')}. Goal: {scene.get('goal')}. Idea: {scene.get('idea')}.")
    parts.append(f"Shot: {shot.get('title')}, {shot.get('type')} shot, {shot.get('angle')} angle, camera movement: {shot.get('movement')}. Emotion: {shot.get('emotion')} {shot.get('emotion_notes')}. Shot duration planning: {shot.get('planning_duration')} seconds.")
    parts.append(f"Camera: shot on {shot.get('camera')}, lens: {shot.get('lens')}, professional cinematic optics, natural lens compression and realistic depth of field.")
    parts.append(f"Lighting: {shot.get('lighting') or scene.get('lighting')}, diffusion filter: {shot.get('diffusion')}. FPS: {shot.get('fps') or scene.get('fps')}.")
    if shot.get("flat_log") or shot.get("color_mode") == "Flat / Log":
        parts.append("Flat log cinematic profile, low contrast, neutral saturation, preserved highlights and shadows, designed for manual cinematic color grading. Do not bake strong LUT.")
    else:
        parts.append(f"Color mode: {shot.get('color_mode') or scene.get('lut')}. Match cinematic grading and color palette from uploaded references if present.")
    if shot.get("dialogue"): parts.append(f"Dialogue: {shot.get('dialogue')}.")
    if shot.get("voiceover"): parts.append(f"Voice over: {shot.get('voiceover')}.")
    if shot.get("sound"): parts.append(f"Sound design: {shot.get('sound')}.")
    if shot.get("continuity_start"): parts.append(f"Continuity start: {shot.get('continuity_start')}.")
    if shot.get("continuity_end"): parts.append(f"Continuity end: {shot.get('continuity_end')}.")
    parts.append("Continue directly from previous shot when applicable. Do not restart the action. Preserve motion direction naturally.")
    parts.append(protection_prompt(settings, scene, shot))
    parts.append("Premium film quality, grounded realism, no generic sci-fi look.")
    full=" ".join([p for p in parts if p])
    return full, trim_prompt(full)

def runway_generate(prompt, model, duration, ratio):
    if not RUNWAY_API_KEY:
        raise RuntimeError("لا يوجد مفتاح Runway API / Missing RUNWAYML_API_SECRET")
    payload = {"model": model, "promptText": prompt, "duration": int(duration), "ratio": ratio}
    st.json(payload)
    headers = {"Authorization": f"Bearer {RUNWAY_API_KEY}", "Content-Type":"application/json", "X-Runway-Version": RUNWAY_VERSION}
    res = requests.post(RUNWAY_URL, headers=headers, json=payload, timeout=60)
    if res.status_code >= 400:
        msg = res.json() if "application/json" in res.headers.get("content-type","") else res.text
        if "credits" in str(msg).lower(): raise RuntimeError("رصيد Runway غير كافٍ. استخدم الوضع الآمن أو أضف رصيدًا.")
        if "not available" in str(msg).lower(): raise RuntimeError("هذا الموديل غير متاح لحسابك. جرّب veo3.1_fast.")
        raise RuntimeError(f"Runway error {res.status_code}: {msg}")
    data=res.json()
    task_id=data.get("id")
    if not task_id: return data
    ph=st.empty(); prog=st.progress(0)
    for i in range(60):
        time.sleep(3)
        prog.progress(min((i+1)/60, .99))
        r=requests.get(RUNWAY_TASK_URL.format(task_id=task_id), headers=headers, timeout=30)
        status=r.json()
        ph.write(status.get("status", "processing"))
        if status.get("status") in ["SUCCEEDED","FAILED","CANCELED"]:
            prog.progress(1.0)
            return status
    return {"id": task_id, "status":"TIMEOUT"}

def save_project(name=None):
    p=st.session_state.project
    p["modified"] = datetime.now().isoformat()
    safe_name = re.sub(r"[^\w\-ا-ي ]+", "_", name or p.get("name","project")).strip().replace(" ", "_")
    folder=PROJECTS_DIR/safe_name
    folder.mkdir(parents=True, exist_ok=True)
    (folder/"project.json").write_text(json.dumps(p, ensure_ascii=False, indent=2), encoding="utf-8")
    return folder

def list_projects():
    return [d.name for d in PROJECTS_DIR.iterdir() if d.is_dir() and (d/"project.json").exists()]

def load_project(name):
    data=json.loads((PROJECTS_DIR/name/"project.json").read_text(encoding="utf-8"))
    st.session_state.project=data

def export_zip():
    p=st.session_state.project
    mem=io.BytesIO()
    with zipfile.ZipFile(mem, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("project.json", json.dumps(p, ensure_ascii=False, indent=2))
        prompts=[]
        for sc in p.get("scenes",[]):
            prompts.append(f"# {sc.get('title')}\n")
            for sh in sc.get("shots",[]):
                full, runp = build_shot_prompt(p, sc, sh)
                prompts.append(f"## {sh.get('title')}\nFULL:\n{full}\n\nRUNWAY:\n{runp}\n")
        z.writestr("prompts.txt", "\n\n".join(prompts))
    mem.seek(0)
    return mem

def mock_preview(scene, shot):
    text=f"{shot.get('type')} | {shot.get('title')} | {shot.get('emotion')}"
    return text

init_state()

# Header
lang_label = st.sidebar.selectbox("🌐 Language / اللغة", ["العربية", "English"], index=0 if st.session_state.lang=="ar" else 1)
st.session_state.lang = "ar" if lang_label == "العربية" else "en"
st.markdown(f"""<div class='hero'><h1>{tr('title')}</h1><p>{tr('subtitle')}</p><span class='badge'>Runway</span><span class='badge'>Storyboard</span><span class='badge'>Visual DNA</span><span class='badge'>Yemeni Identity</span><span class='badge'>Timeline</span></div>""", unsafe_allow_html=True)

p=st.session_state.project

with st.sidebar:
    st.header("🎬 Project")
    p["name"] = st.text_input("اسم المشروع / Project name", p.get("name",""))
    st.markdown("---")
    st.subheader("⚙️ Runway")
    settings=p.setdefault("settings",{})
    settings["safe_mode"] = st.toggle(tr("safe"), value=settings.get("safe_mode", True))
    settings["model"] = st.selectbox("🎬 Model", MODELS, index=MODELS.index(settings.get("model","veo3.1_fast")) if settings.get("model") in MODELS else 0)
    durations=MODEL_DURATION_MAP.get(settings["model"],[4,6,8])
    settings["runway_duration"] = st.selectbox("⏱️ Runway duration", durations, index=min(len(durations)-1, durations.index(settings.get("runway_duration", durations[0])) if settings.get("runway_duration") in durations else 0))
    st.caption(f"أقصى مدة لهذا الموديل: {max(durations)} ثواني")
    settings["ratio_label"] = st.selectbox("📱 اتجاه الفيديو", list(RATIOS.keys()), index=list(RATIOS.keys()).index(settings.get("ratio_label","🎬 عرضي 1920:1080")) if settings.get("ratio_label") in RATIOS else 0)
    settings["preview_provider"] = st.selectbox(tr("preview_provider"), PREVIEW_PROVIDERS, index=PREVIEW_PROVIDERS.index(settings.get("preview_provider","Mock Preview")) if settings.get("preview_provider") in PREVIEW_PROVIDERS else 1)
    st.markdown("---")
    st.subheader("🛡️ Protection")
    settings["strict"] = st.toggle(tr("strict"), value=settings.get("strict", True))
    settings["ultra_realism"] = st.toggle(tr("realism"), value=settings.get("ultra_realism", True))
    settings["face_protection"] = st.toggle(tr("face"), value=settings.get("face_protection", True))
    settings["real_ai"] = st.toggle(tr("real_ai"), value=settings.get("real_ai", True))
    settings["scene_lock"] = st.toggle(tr("scene_lock"), value=settings.get("scene_lock", True))
    settings["anatomy"] = st.toggle(tr("anatomy"), value=settings.get("anatomy", True))
    settings["expansion"] = st.toggle(tr("expansion"), value=settings.get("expansion", True))
    settings["deform"] = st.toggle(tr("deform"), value=settings.get("deform", True))
    st.markdown("---")
    c1,c2=st.columns(2)
    if c1.button(tr("save")): st.success(f"Saved: {save_project().name}")
    if c2.button(tr("save_as")): st.success(f"Saved as: {save_project(p['name']).name}")
    projects=list_projects()
    if projects:
        sel=st.selectbox("📁 Projects", projects)
        if st.button(tr("load")):
            load_project(sel); st.rerun()
    st.download_button(tr("export"), data=export_zip(), file_name=f"{p.get('name','project')}.zip", mime="application/zip")

# Tabs
tabs = st.tabs(["🎞️ الهوية", "🗂️ المكتبة", "🎬 المشاهد", "📂 المشاريع"])

with tabs[0]:
    col1,col2=st.columns(2)
    with col1:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.subheader("🎞️ هوية الفيلم / Film Identity")
        ident=p.setdefault("identity",{})
        ident["project_type"] = st.selectbox("Project Type", ["Drama", "Commercial", "Documentary", "Music Video", "Film", "AI Short"], index=0)
        ident["style"] = st.selectbox("Directing Style", FILM_STYLES, index=FILM_STYLES.index(ident.get("style","Yemeni Heritage")) if ident.get("style") in FILM_STYLES else 4)
        ident["culture"] = st.text_input("Country / Culture", ident.get("culture","Yemen / Hadramout"))
        ident["mood"] = st.text_input("Mood", ident.get("mood","cinematic, realistic, emotional"))
        ident["camera_style"] = st.selectbox("Camera Style", CAMERAS, index=0)
        ident["lighting_style"] = st.selectbox("Lighting Style", LIGHT_PRESETS, index=1)
        ident["main_lut"] = st.selectbox("Main LUT", COLOR_MODES, index=0)
        st.markdown("</div>", unsafe_allow_html=True)
    with col2:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.subheader("🇾🇪 مكتبة الهوية اليمنية")
        y=p.setdefault("yemeni",{})
        y["environment"] = st.selectbox("البيئة", YEMEN_ENV, index=YEMEN_ENV.index(y.get("environment","None")) if y.get("environment") in YEMEN_ENV else 0)
        y["clothing"] = st.selectbox("الأزياء", YEMEN_CLOTHES, index=YEMEN_CLOTHES.index(y.get("clothing","None")) if y.get("clothing") in YEMEN_CLOTHES else 0)
        y["character"] = st.selectbox("الشخصية", YEMEN_CHARS, index=YEMEN_CHARS.index(y.get("character","None")) if y.get("character") in YEMEN_CHARS else 0)
        y["dialect"] = st.selectbox("اللهجة", YEMEN_DIALECTS, index=YEMEN_DIALECTS.index(y.get("dialect","فصحى")) if y.get("dialect") in YEMEN_DIALECTS else 0)
        y["lighting"] = st.selectbox("إضاءة يمنية", ["None", "شمس حضرمية", "غروب ذهبي", "داخل بيت طيني", "فوانيس ليلية", "متحف دافئ"])
        y["color"] = st.selectbox("لون يمني", ["None", "طيني دافئ", "Hadramout LUT", "Golden cinematic", "Documentary warm", "Dark dramatic"])
        st.markdown("</div>", unsafe_allow_html=True)

with tabs[1]:
    st.subheader("🗂️ مكتبة المراجع البصرية / Visual Reference Library")
    st.caption("ارفع صور كثيرة للمشروع: شخصيات، بيئات، أزياء، ألوان، إضاءة، كاميرا، ستوري بورد.")
    lib=p.setdefault("library",{})
    cats=[("characters","👤 Characters"),("environments","🏛️ Environments"),("clothing","👕 Clothing"),("colors","🎨 Colors / LUT"),("lighting","💡 Lighting"),("camera_refs","🎥 Camera References"),("storyboards","🎞️ Storyboards"),("textures","🧱 Textures"),("frames","📸 Cinematic Frames")]
    for key,label in cats:
        with st.expander(label, expanded=False):
            refs=upload_images(f"Upload {label}", f"lib_{key}")
            if refs: lib[key]=lib.get(key,[])+refs
            st.write(f"Saved references: {len(lib.get(key,[]))}")
    st.info("🧬 Visual DNA Engine: سيتم استخدام هذه المكتبة للحفاظ على الهوية البصرية والاستمرارية في كل المشاهد.")

with tabs[2]:
    st.subheader("🎬 Scenes / المشاهد")
    cadd, cbrain = st.columns([1,2])
    if cadd.button("➕ إضافة مشهد / Add Scene"):
        p["scenes"].append(new_scene(len(p["scenes"])+1)); st.rerun()
    if cbrain.button("🧠 اقتراح إخراج المشهد / Smart Cinematic Brain"):
        st.info("اقتراح: Establishing → Medium → Close-up → Reaction → Insert → Final emotional beat. استخدم استمرارية الحركة والضوء بين اللقطات.")
    scene_titles=[s.get("title",f"Scene {i+1}") for i,s in enumerate(p["scenes"])]
    sidx=st.selectbox("اختر المشهد", range(len(scene_titles)), format_func=lambda i: scene_titles[i])
    scene=p["scenes"][sidx]
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader(f"🎬 {scene.get('title')}")
    cols=st.columns(4)
    scene["title"] = cols[0].text_input("Scene Title", scene.get("title"), key=f"scene_title_{scene['id']}")
    scene["duration_total"] = cols[1].number_input("⏳ مدة المشهد الكاملة", min_value=15, max_value=600, value=int(scene.get("duration_total",60)), step=15, key=f"dur_{scene['id']}")
    scene["fps"] = cols[2].selectbox("FPS", FPS_OPTIONS, index=FPS_OPTIONS.index(scene.get("fps",25)) if scene.get("fps") in FPS_OPTIONS else 1, key=f"fps_{scene['id']}")
    scene["orientation"] = cols[3].selectbox("📱 الاتجاه", list(RATIOS.keys()), index=list(RATIOS.keys()).index(scene.get("orientation","🎬 عرضي 1920:1080")) if scene.get("orientation") in RATIOS else 0, key=f"ori_{scene['id']}")
    scene["goal"] = st.text_input("هدف المشهد / Scene goal", scene.get("goal",""), key=f"goal_{scene['id']}")
    scene["idea"] = st.text_area("فكرة المشهد / Scene idea", scene.get("idea",""), key=f"idea_{scene['id']}")
    c1,c2,c3=st.columns(3)
    scene["lighting"] = c1.selectbox("💡 Lighting", LIGHT_PRESETS, index=LIGHT_PRESETS.index(scene.get("lighting","Golden Hour")) if scene.get("lighting") in LIGHT_PRESETS else 1, key=f"light_{scene['id']}")
    scene["lut"] = c2.selectbox("🎨 Color Mode", COLOR_MODES, index=COLOR_MODES.index(scene.get("lut","Cinematic LUT")) if scene.get("lut") in COLOR_MODES else 0, key=f"lut_{scene['id']}")
    scene["emotion"] = c3.text_input("🎭 Emotion", scene.get("emotion","توتر"), key=f"emo_{scene['id']}")
    scene["storyboard_mode"] = st.toggle("🎞️ Storyboard Mode / وضع الاستوري بورد", value=scene.get("storyboard_mode",False), key=f"story_{scene['id']}")
    if scene["storyboard_mode"]:
        scene["storyboards"] = upload_images("🖼️ ارفع صور الاستوري بورد", f"story_upload_{scene['id']}") or scene.get("storyboards", [])
    scene["color_refs"] = upload_images("🎨 مرجع الألوان للمشهد", f"scene_color_{scene['id']}") or scene.get("color_refs", [])
    st.markdown("</div>", unsafe_allow_html=True)

    bc1,bc2,bc3,bc4=st.columns(4)
    if bc1.button(tr("split")):
        n=max(1, round(scene["duration_total"]/6))
        scene["shots"]=[]
        drama_types=["Wide","Medium","Close-up","Reaction Shot","Over Shoulder","Insert","Close-up"]
        for i in range(n):
            sh=new_shot(i+1); sh["type"]=drama_types[i%len(drama_types)]; sh["planning_duration"]=min(8,max(4,round(scene["duration_total"]/n))); sh["title"]=f"Shot {i+1}"; sh["continuity_start"]="Continue from previous shot" if i>0 else "Opening shot"; sh["continuity_end"]="Prepare next action beat" if i<n-1 else "Final shot"; scene["shots"].append(sh)
        st.success(f"تم تقسيم المشهد إلى {n} لقطات")
        st.rerun()
    if bc2.button("➕ إضافة لقطة"):
        scene["shots"].append(new_shot(len(scene["shots"])+1)); st.rerun()
    if bc3.button(tr("previews")):
        for sh in scene["shots"]: sh["preview"] = mock_preview(scene, sh)
        st.success("تم تجهيز المعاينات")
    if bc4.button(tr("allshots")):
        if settings.get("safe_mode"):
            st.warning("الوضع الآمن مفعل: لن يتم استهلاك رصيد Runway")
        prog=st.progress(0)
        for i,sh in enumerate(scene["shots"]):
            full, runp=build_shot_prompt(p, scene, sh); sh["prompt"]=full
            st.write(f"جاري توليد اللقطة {i+1} من {len(scene['shots'])}")
            if not settings.get("safe_mode"):
                try:
                    result=runway_generate(runp, settings["model"], settings["runway_duration"], RATIOS[settings["ratio_label"]])
                    out=result.get("output") if isinstance(result,dict) else None
                    if out and isinstance(out,list): sh["video_url"]=out[0]
                    st.write(result)
                except Exception as e:
                    st.error(str(e))
            prog.progress((i+1)/len(scene["shots"]))

    st.markdown("### 🎥 Shots / اللقطات")
    for idx,shot in enumerate(scene["shots"]):
        with st.expander(f"🎥 {idx+1}. {shot.get('title')} — {shot.get('type')}", expanded=idx==0):
            c1,c2,c3,c4=st.columns(4)
            shot["title"] = c1.text_input("Shot title", shot.get("title"), key=f"sh_title_{shot['id']}")
            shot["type"] = c2.selectbox("Shot type", SHOT_TYPES, index=SHOT_TYPES.index(shot.get("type","Wide")) if shot.get("type") in SHOT_TYPES else 0, key=f"type_{shot['id']}")
            shot["angle"] = c3.selectbox("Angle", ANGLES, index=ANGLES.index(shot.get("angle","Eye Level")) if shot.get("angle") in ANGLES else 0, key=f"angle_{shot['id']}")
            shot["movement"] = c4.selectbox("Movement", MOVEMENTS, index=MOVEMENTS.index(shot.get("movement","Slow Push-in")) if shot.get("movement") in MOVEMENTS else 0, key=f"move_{shot['id']}")
            c5,c6,c7,c8=st.columns(4)
            shot["planning_duration"] = c5.selectbox("⏱️ زمن اللقطة", list(range(1,11)), index=int(shot.get("planning_duration",6))-1, key=f"pdur_{shot['id']}")
            shot["fps"] = c6.selectbox("FPS", FPS_OPTIONS, index=FPS_OPTIONS.index(shot.get("fps",25)) if shot.get("fps") in FPS_OPTIONS else 1, key=f"sfps_{shot['id']}")
            shot["camera"] = c7.selectbox("🎥 Camera", CAMERAS, index=CAMERAS.index(shot.get("camera","ARRI Alexa Mini LF")) if shot.get("camera") in CAMERAS else 0, key=f"cam_{shot['id']}")
            shot["lens"] = c8.selectbox("🔭 Lens", LENSES, index=LENSES.index(shot.get("lens","50mm Prime Lens")) if shot.get("lens") in LENSES else 3, key=f"lens_{shot['id']}")
            c9,c10,c11=st.columns(3)
            shot["diffusion"] = c9.selectbox("🎞️ Diffusion", DIFFUSION, index=DIFFUSION.index(shot.get("diffusion","Black Pro Mist 1/4")) if shot.get("diffusion") in DIFFUSION else 2, key=f"diff_{shot['id']}")
            shot["color_mode"] = c10.selectbox("🎨 Color", COLOR_MODES, index=COLOR_MODES.index(shot.get("color_mode","Cinematic LUT")) if shot.get("color_mode") in COLOR_MODES else 0, key=f"cmode_{shot['id']}")
            shot["flat_log"] = c11.toggle("🎨 Flat / Log", value=shot.get("flat_log",False) or shot.get("color_mode") == "Flat / Log", key=f"flat_{shot['id']}")
            shot["emotion"] = st.text_input("🎭 إحساس اللقطة", shot.get("emotion","توتر"), key=f"semotion_{shot['id']}")
            shot["emotion_notes"] = st.text_area("وصف الإحساس والأداء", shot.get("emotion_notes",""), key=f"enotes_{shot['id']}")
            shot["dialogue"] = st.text_area("🗣️ الحوار", shot.get("dialogue",""), key=f"dialogue_{shot['id']}")
            shot["voiceover"] = st.text_area("🎤 Voice Over", shot.get("voiceover",""), key=f"vo_{shot['id']}")
            shot["sound"] = st.text_input("🎧 Sound Design", shot.get("sound",""), key=f"sound_{shot['id']}")
            shot["continuity_start"] = st.text_input("🔁 Continuity start", shot.get("continuity_start",""), key=f"cstart_{shot['id']}")
            shot["continuity_end"] = st.text_input("🔁 Continuity end", shot.get("continuity_end",""), key=f"cend_{shot['id']}")
            shot["references"] = upload_images("🖼️ مراجع اللقطة", f"refs_{shot['id']}") or shot.get("references", [])
            shot["color_refs"] = upload_images("🎨 مرجع ألوان اللقطة", f"scolor_{shot['id']}") or shot.get("color_refs", [])
            colp1,colp2,colp3=st.columns(3)
            if colp1.button(tr("prompt"), key=f"prompt_btn_{shot['id']}"):
                full,runp=build_shot_prompt(p, scene, shot); shot["prompt"]=full
            if colp2.button("🖼️ توليد صورة اختبارية", key=f"prev_{shot['id']}"):
                if settings.get("preview_provider") == "Manual Upload": st.info("ارفع صورة من مراجع اللقطة لتكون المعاينة")
                else: shot["preview"] = mock_preview(scene, shot)
            if colp3.button(tr("generate"), key=f"run_{shot['id']}"):
                full,runp=build_shot_prompt(p, scene, shot); shot["prompt"]=full
                if not shot.get("preview"): st.warning("لم يتم توليد صورة اختبارية لهذه اللقطة. يمكنك المتابعة.")
                if settings.get("safe_mode"):
                    st.warning("الوضع الآمن مفعل: لن يتم استهلاك رصيد Runway")
                else:
                    try:
                        result=runway_generate(runp, settings["model"], settings["runway_duration"], RATIOS[settings["ratio_label"]])
                        out=result.get("output") if isinstance(result,dict) else None
                        if out and isinstance(out,list): shot["video_url"]=out[0]
                        st.write(result)
                    except Exception as e: st.error(str(e))
            if shot.get("preview"):
                st.markdown(f"<span class='badge success-badge'>🖼️ Preview ready</span>", unsafe_allow_html=True)
                st.info(shot["preview"])
            else:
                st.markdown(f"<span class='badge warn-badge'>No preview yet</span>", unsafe_allow_html=True)
            full, runp = build_shot_prompt(p, scene, shot)
            st.caption(f"Prompt length: {len(runp)} / 1000")
            st.text_area("FULL PROMPT", full, height=160, key=f"full_{shot['id']}")
            st.text_area("RUNWAY PROMPT", runp, height=100, key=f"runway_{shot['id']}")
            if shot.get("video_url"):
                st.video(shot["video_url"])

with tabs[3]:
    st.subheader("📂 Project Browser")
    projects=list_projects()
    if projects:
        for pr in projects:
            c1,c2,c3=st.columns([3,1,1])
            c1.write(f"📁 {pr}")
            if c2.button("Load", key=f"load_{pr}"):
                load_project(pr); st.rerun()
            if c3.button("Delete", key=f"del_{pr}"):
                import shutil; shutil.rmtree(PROJECTS_DIR/pr); st.rerun()
    else:
        st.info("لا توجد مشاريع محفوظة بعد")
    st.markdown("### 🧩 Stitching Preparation")
    st.write("بعد توليد كل اللقطات، صدّر خطة الدمج واستخدم ffmpeg/moviepy لاحقًا لدمج الفيديوهات بالترتيب مع الانتقالات والصوت.")
    st.markdown("### 🎧 Audio Timeline")
    st.text_area("Voice over / Ambience / Music / Sound bridge plan", height=150)
