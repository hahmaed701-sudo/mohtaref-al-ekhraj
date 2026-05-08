import os
import time
from datetime import datetime
from typing import Dict, List, Any

import requests
import streamlit as st
from PIL import Image

# =============================
# Render / Env
# =============================
RUNWAY_API_KEY = os.getenv("RUNWAYML_API_SECRET", "")
RUNWAY_BASE_URL = "https://api.dev.runwayml.com/v1"
RUNWAY_VERSION = "2024-11-06"

st.set_page_config(page_title="محترف الإخراج", page_icon="🎬", layout="wide")

# =============================
# Styles
# =============================
st.markdown(
    """
    <style>
    html, body, [class*="css"] { direction: rtl; text-align: right; }
    .stApp { background: radial-gradient(circle at top left, #241235 0%, #070710 45%, #050506 100%); color: #f4f4f5; }
    .block-container { padding-top: 1.2rem; max-width: 1500px; }
    .card { background: rgba(18,18,28,.88); border:1px solid rgba(178,124,255,.22); border-radius:18px; padding:18px; margin:12px 0; box-shadow: 0 10px 40px rgba(0,0,0,.25); }
    .small-card { background: rgba(255,255,255,.045); border:1px solid rgba(255,255,255,.09); border-radius:14px; padding:12px; margin:8px 0; }
    .badge { display:inline-block; padding:6px 10px; border-radius:999px; background:rgba(142,82,255,.18); border:1px solid rgba(178,124,255,.35); color:#dec8ff; margin:3px; font-size:13px; }
    .gold { color:#ffd37a; }
    .muted { color:#a1a1aa; font-size:13px; }
    .hero-title { font-size: 34px; font-weight: 800; letter-spacing: -.5px; }
    .thumb img { border-radius:10px; border:1px solid rgba(255,255,255,.15); }
    </style>
    """,
    unsafe_allow_html=True,
)

# =============================
# Constants
# =============================
MODEL_FEATURES = {
    "veo3.1_fast": {
        "durations": [4, 6, 8],
        "ratios": ["1920:1080", "1080:1920", "1440:1440"],
        "seedance": False,
    },
    "veo3.1": {
        "durations": [4, 6, 8],
        "ratios": ["1920:1080", "1080:1920", "1440:1440"],
        "seedance": False,
    },
    "kling3.0_standard": {
        "durations": [4, 6, 8],
        "ratios": ["1920:1080", "1080:1920", "1440:1440"],
        "seedance": False,
    },
    "seedance2": {
        "durations": list(range(5, 16)),
        "ratios": ["1280:720", "720:1280", "960:960", "640:640", "992:432", "864:496", "752:560", "560:752", "496:864", "1470:630", "1112:834", "834:1112"],
        "seedance": True,
    },
}

CAMERAS = ["ARRI Alexa Mini LF", "RED V-Raptor", "Sony Venice", "Sony FX3", "Blackmagic URSA", "Canon C70", "Phantom Flex"]
DIRECTING_STYLES = ["Hollywood", "Netflix", "Documentary", "Arabic Drama", "Yemeni Heritage", "Dark Thriller", "Sports", "Luxury Commercial"]
PROJECT_TYPES = ["دراما", "إعلان", "وثائقي", "فيلم قصير", "فيديو موسيقي", "مشهد تجريبي"]
LIGHTS = ["Golden Hour", "Soft Cinematic Light", "Natural Daylight", "Warm Indoor", "Night Lantern", "Studio Light"]
LENSES = ["16mm", "24mm", "35mm", "50mm", "85mm", "100mm Macro", "70-200mm", "Anamorphic", "Vintage Lens"]
SHOT_TYPES = ["Wide", "Medium", "Close-up", "Extreme Close-up", "Two Shot", "Over Shoulder", "POV", "Insert", "Reaction Shot"]
MOVEMENTS = ["Static", "Dolly In", "Dolly Out", "Push-in", "Pan", "Tilt", "Handheld", "Crane", "Drone", "Slow Motion"]
TRANSITIONS = ["Cut", "Match Cut", "Fade", "Motion Cut", "Sound Bridge", "Reaction Cut"]
FILTERS = ["No Filter", "Black Pro Mist 1/8", "Black Pro Mist 1/4", "Black Pro Mist 1/2", "Soft FX", "Glimmerglass", "Natural Skin Softening"]
STATUSES = ["⚪ غير مكتملة", "🟡 جاهزة للتوليد", "🔵 تم توليدها", "🟢 معتمدة", "🔴 فشل التوليد"]

# =============================
# Helpers
# =============================
def trim_prompt(prompt: str, max_chars: int = 950) -> str:
    prompt = (prompt or "").strip()
    if len(prompt) <= max_chars:
        return prompt
    return prompt[:max_chars].rsplit(" ", 1)[0] + "..."


def runway_headers() -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {RUNWAY_API_KEY}",
        "Content-Type": "application/json",
        "X-Runway-Version": RUNWAY_VERSION,
    }


def build_payload(model: str, prompt: str, duration: int, ratio: str, seedance_refs: Dict[str, Any] | None = None) -> Dict[str, Any]:
    payload = {"model": model, "promptText": trim_prompt(prompt), "duration": int(duration), "ratio": ratio}
    # Placeholder for public URI references only. Local uploads require Runway upload API before use.
    if model == "seedance2" and seedance_refs:
        for key in ["references", "referenceVideos", "referenceAudio", "promptImage", "promptVideo"]:
            if seedance_refs.get(key):
                payload[key] = seedance_refs[key]
    return payload


def supported_duration(model: str, desired: int) -> int:
    """Return the closest Runway-supported duration for the selected model."""
    allowed = MODEL_FEATURES.get(model, {}).get("durations", [4, 6, 8])
    desired = int(desired)
    if desired in allowed:
        return desired
    return min(allowed, key=lambda x: abs(x - desired))


def distribute_scene_durations(model: str, scene_duration: int, shot_count: int) -> List[int]:
    """Create per-shot generation durations that best match the scene duration."""
    allowed = MODEL_FEATURES.get(model, {}).get("durations", [4, 6, 8])
    if shot_count <= 0:
        return []
    target_avg = max(min(int(scene_duration / shot_count), max(allowed)), min(allowed))
    base = min(allowed, key=lambda x: abs(x - target_avg))
    durations = [base for _ in range(shot_count)]
    # Adjust lightly toward requested scene duration while staying valid.
    total = sum(durations)
    for i in range(shot_count):
        if abs(total - scene_duration) <= min(allowed):
            break
        if total < scene_duration:
            larger = [d for d in allowed if d > durations[i]]
            if larger:
                new = larger[0]
                total += new - durations[i]
                durations[i] = new
        elif total > scene_duration:
            smaller = [d for d in allowed if d < durations[i]]
            if smaller:
                new = smaller[-1]
                total += new - durations[i]
                durations[i] = new
    return durations


def save_video_to_library(scene_key: str, shot_number: int, item: Dict[str, Any]) -> None:
    """Save every generated video/mock card in one shared scene video library."""
    if "videos" not in st.session_state:
        st.session_state.videos = {}
    video_key = f"{scene_key}_shot_{shot_number}"
    st.session_state.videos[video_key] = item


def create_runway_task(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not RUNWAY_API_KEY:
        raise RuntimeError("لا يوجد مفتاح RUNWAYML_API_SECRET داخل Render Environment Variables")
    r = requests.post(f"{RUNWAY_BASE_URL}/text_to_video", headers=runway_headers(), json=payload, timeout=120)
    if r.status_code >= 400:
        raise RuntimeError(f"Runway error {r.status_code}: {r.json() if r.text else r.text}")
    return r.json()


def poll_task(task_id: str, max_wait: int = 420) -> Dict[str, Any]:
    start = time.time()
    while time.time() - start < max_wait:
        r = requests.get(f"{RUNWAY_BASE_URL}/tasks/{task_id}", headers=runway_headers(), timeout=60)
        data = r.json()
        status = data.get("status", "")
        if status in ["SUCCEEDED", "FAILED", "CANCELLED"]:
            return data
        time.sleep(5)
    raise TimeoutError("انتهى وقت الانتظار ولم يكتمل التوليد")


def display_upload_grid(files, label: str):
    st.caption(label)
    if not files:
        st.caption("لا توجد صور مرفوعة")
        return
    cols = st.columns(min(5, max(1, len(files))))
    for i, f in enumerate(files[:20]):
        with cols[i % len(cols)]:
            try:
                st.image(f, caption=f.name[:18], use_container_width=True)
            except Exception:
                st.caption(f.name)


def default_shots(n: int) -> List[Dict[str, Any]]:
    pattern = ["Wide", "Medium", "Close-up", "Reaction Shot", "Over Shoulder", "Insert"]
    return [
        {
            "title": f"لقطة {i+1}",
            "description": "",
            "duration": 6,
            "lens": LENSES[min(i, len(LENSES)-1)],
            "type": pattern[i % len(pattern)],
            "movement": MOVEMENTS[i % len(MOVEMENTS)],
            "dialogue": "",
            "music": "",
            "sfx": "",
            "transition": TRANSITIONS[i % len(TRANSITIONS)],
            "filter": "No Filter",
            "status": STATUSES[0],
        }
        for i in range(n)
    ]


def split_storyboard_to_count(text: str) -> int:
    if not text.strip():
        return 4
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if len(lines) >= 2:
        return min(20, max(2, len(lines)))
    # approximate by length
    return min(12, max(3, len(text) // 140 + 1))


def build_shot_prompt(global_settings: Dict[str, Any], scene: Dict[str, Any], shot: Dict[str, Any]) -> str:
    parts = [
        f"Cinematic shot for scene {scene.get('number')}: {scene.get('title')}",
        f"Overall scene: {scene.get('description')}",
        f"Project type: {global_settings.get('project_type')}, directing style: {global_settings.get('style')}",
        f"Shot description: {shot.get('description')}",
        f"Shot type: {shot.get('type')}, lens: {shot.get('lens')}, camera movement: {shot.get('movement')}",
        f"Camera: {global_settings.get('camera')}",
        f"Scene lighting: {scene.get('lighting')}",
        f"Wardrobe: {scene.get('clothing')}",
        f"Characters: {scene.get('characters_text')}",
        f"Environment: {scene.get('environment')}",
        f"Dialogue: {shot.get('dialogue')}",
        f"Music: {shot.get('music')}",
        f"Sound effects: {shot.get('sfx')}",
        f"Transition: {shot.get('transition')}",
        f"Diffusion filter: {shot.get('filter')}",
        f"Shot duration planning: {shot.get('duration')} seconds",
    ]
    if scene.get("flat"):
        parts.append("Flat log cinematic profile, neutral saturation, low contrast, preserved highlights and shadows, ready for manual color grading.")
    if scene.get("color_ref"):
        parts.append("Match cinematic color palette from uploaded color reference image.")
    parts.extend([
        "Maintain cinematic continuity.",
        "Strictly follow provided references and scene direction.",
        "Ultra realistic cinematic image, natural skin texture, no AI plastic skin, no distorted anatomy, no extra people or locations.",
    ])
    return trim_prompt(". ".join([p for p in parts if p and str(p).strip()]), 1800)


def ensure_state():
    if "videos" not in st.session_state:
        st.session_state.videos = {}
    if "scene_shots" not in st.session_state:
        st.session_state.scene_shots = {}

ensure_state()

# =============================
# Header
# =============================
left, mid, right = st.columns([1, 5, 2])
with left:
    try:
        st.image("assets/logo.png", use_container_width=True)
    except Exception:
        st.markdown("🎬")
with mid:
    st.markdown('<div class="hero-title">محترف الإخراج</div><div class="muted">AI Drama Director Studio — نسخة Render الموحدة</div>', unsafe_allow_html=True)
with right:
    safe_mode = st.toggle("🛡️ الوضع الآمن", value=False, help="بدون استهلاك رصيد Runway")
    st.caption("✅ Render Ready" if RUNWAY_API_KEY else "⚠️ RUNWAYML_API_SECRET غير موجود")

# =============================
# Sidebar / Film Identity
# =============================
with st.sidebar:
    st.markdown("## 🎞️ هوية الفيلم")
    project_type = st.selectbox("🎬 نوع المشروع", PROJECT_TYPES)
    style = st.selectbox("🎭 أسلوب الإخراج", DIRECTING_STYLES)
    camera = st.selectbox("🎥 نوع الكاميرا", CAMERAS)
    model = st.selectbox("🧠 نوع الأداة / الموديل", list(MODEL_FEATURES.keys()), index=0)
    features = MODEL_FEATURES[model]
    ratio = st.selectbox("📐 الاتجاه / المقاس", features["ratios"])
    runway_duration = st.selectbox("⏱️ مدة Runway", features["durations"], index=min(2, len(features["durations"])-1))
    st.success(f"أقصى مدة لهذا الموديل: {max(features['durations'])} ثانية")

    if model == "seedance2":
        st.info("seedance2 داخل Runway: يدعم مدة 5–15 ثانية ومراجع متقدمة عند استخدام روابط عامة أو Upload API لاحقًا.")
        generation_mode = st.selectbox("🎬 نمط التوليد", ["Text to Video", "Image to Video", "Video to Video"])
    else:
        generation_mode = "Text to Video"

    st.markdown("---")
    st.markdown("### 🎯 الحماية والواقعية")
    strict_mode = st.toggle("🎯 الالتزام الكامل", value=True)
    realism = st.toggle("📸 الواقعية القصوى", value=True)
    face_protect = st.toggle("👤 حماية الوجه", value=True)
    scene_lock = st.toggle("🔒 قفل المشهد", value=True)

    global_settings = {
        "project_type": project_type,
        "style": style,
        "camera": camera,
        "model": model,
        "ratio": ratio,
        "runway_duration": int(runway_duration),
        "strict": strict_mode,
        "realism": realism,
        "face_protect": face_protect,
        "scene_lock": scene_lock,
    }

# =============================
# Main Tabs
# =============================
tab_scenes, tab_library, tab_export = st.tabs(["🎬 المشاهد واللقطات", "📚 مكتبة عامة", "📦 التصدير"])

with tab_scenes:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    num_scenes = st.number_input("🎬 عدد المشاهد", min_value=1, max_value=20, value=1, step=1)
    st.markdown("</div>", unsafe_allow_html=True)

    for s in range(int(num_scenes)):
        scene_key = f"scene_{s+1}"
        st.markdown(f'<div class="card"><h2>🎬 المشهد رقم {s+1}</h2>', unsafe_allow_html=True)
        c1, c2 = st.columns([2, 1])
        with c1:
            title = st.text_input("عنوان المشهد", value=f"المشهد {s+1}", key=f"title_{s}")
            description = st.text_area("الوصف العام للمشهد", height=130, key=f"desc_{s}", placeholder="اكتب وصف المشهد كاملًا أو الفكرة العامة...")
        with c2:
            scene_duration = st.selectbox("⏱️ مدة المشهد", [15, 30, 45, 60, 90, 120], index=1, key=f"scene_dur_{s}")
            lighting = st.selectbox("💡 إضاءة المشهد", LIGHTS, key=f"light_{s}")
            clothing = st.text_input("👕 اللبس", key=f"cloth_{s}", placeholder="مثال: ثوب يمني، عمامة حضرمية...")
            environment = st.text_input("🏛️ البيئة", key=f"env_{s}", placeholder="مثال: بيت طيني، متحف، وادي دوعن...")

        st.markdown("### 🎞️ Storyboard")
        sb1, sb2 = st.columns([2, 1])
        with sb1:
            storyboard_text = st.text_area("نص الاستوري بورد / تسلسل اللقطات", height=120, key=f"story_text_{s}")
        with sb2:
            storyboard_img = st.file_uploader("رفع صورة Storyboard", type=["jpg", "jpeg", "png", "webp"], key=f"story_img_{s}")
            if storyboard_img:
                st.image(storyboard_img, caption="Storyboard", use_container_width=True)

        st.markdown("### 👤 الشخصيات داخل المشهد")
        char_count = st.number_input("عدد الشخصيات", min_value=1, max_value=8, value=1, key=f"char_count_{s}")
        char_texts = []
        for ci in range(int(char_count)):
            with st.expander(f"شخصية {ci+1}", expanded=(ci == 0)):
                cc1, cc2 = st.columns(2)
                with cc1:
                    cname = st.text_input("اسم الشخصية", key=f"cname_{s}_{ci}")
                    cdesc = st.text_area("وصف الشخصية", height=80, key=f"cdesc_{s}_{ci}")
                with cc2:
                    cwear = st.text_input("اللبس الخاص بها", key=f"cwear_{s}_{ci}")
                    cref = st.file_uploader("صور مرجعية للشخصية", type=["jpg", "jpeg", "png", "webp"], accept_multiple_files=True, key=f"cref_{s}_{ci}")
                    display_upload_grid(cref, "معاينة الشخصية")
                char_texts.append(f"{cname}: {cdesc}, wardrobe: {cwear}")

        st.markdown("### 📚 مراجع المشهد")
        r1, r2, r3 = st.columns(3)
        with r1:
            wear_refs = st.file_uploader("مراجع اللبس", type=["jpg", "jpeg", "png", "webp"], accept_multiple_files=True, key=f"wear_refs_{s}")
            display_upload_grid(wear_refs, "👕")
        with r2:
            char_refs = st.file_uploader("مراجع الشخصيات", type=["jpg", "jpeg", "png", "webp"], accept_multiple_files=True, key=f"char_refs_{s}")
            display_upload_grid(char_refs, "👤")
        with r3:
            env_refs = st.file_uploader("مراجع البيئة", type=["jpg", "jpeg", "png", "webp"], accept_multiple_files=True, key=f"env_refs_{s}")
            display_upload_grid(env_refs, "🏛️")

        st.markdown("### 🎨 اللون / LUT")
        color_cols = st.columns([1, 1, 2])
        with color_cols[0]:
            flat = st.checkbox("Flat / Log", key=f"flat_{s}")
        with color_cols[1]:
            color_ref = st.file_uploader("صورة لون", type=["jpg", "jpeg", "png", "webp"], key=f"color_ref_{s}")
        with color_cols[2]:
            if color_ref:
                st.image(color_ref, caption="مرجع اللون", width=220)

        if scene_key not in st.session_state.scene_shots:
            st.session_state.scene_shots[scene_key] = default_shots(max(2, int(scene_duration) // 8))

        col_a, col_b, col_c = st.columns([1, 1, 1])
        with col_a:
            if st.button("🎞️ تقسيم المشهد إلى لقطات", key=f"split_{s}"):
                count = split_storyboard_to_count(storyboard_text or description)
                st.session_state.scene_shots[scene_key] = default_shots(count)
                st.success(f"تم إنشاء {count} لقطات")
        with col_b:
            if st.button("➕ إضافة لقطة جديدة", key=f"add_shot_{s}"):
                shots = st.session_state.scene_shots[scene_key]
                shots.append(default_shots(1)[0] | {"title": f"لقطة {len(shots)+1}"})
                st.rerun()
        with col_c:
            st.metric("عدد اللقطات", len(st.session_state.scene_shots[scene_key]))

        scene_data = {
            "number": s + 1,
            "title": title,
            "description": description,
            "duration": scene_duration,
            "lighting": lighting,
            "clothing": clothing,
            "environment": environment,
            "characters_text": " | ".join(char_texts),
            "flat": flat,
            "color_ref": bool(color_ref),
        }

        st.markdown("### 🎥 اللقطات")
        shots = st.session_state.scene_shots[scene_key]
        for i, shot in enumerate(list(shots)):
            with st.expander(f"🎥 لقطة {i+1} — {shot.get('title','')}", expanded=(i == 0)):
                q1, q2, q3, q4 = st.columns(4)
                shot["title"] = q1.text_input("عنوان اللقطة", value=shot.get("title", f"لقطة {i+1}"), key=f"shot_title_{s}_{i}")
                shot["duration"] = q2.selectbox("⏱️ الزمن", list(range(1, 11)), index=max(0, int(shot.get("duration", 6))-1), key=f"shot_dur_{s}_{i}")
                shot["lens"] = q3.selectbox("🔭 العدسة", LENSES, index=LENSES.index(shot.get("lens", "50mm")) if shot.get("lens") in LENSES else 3, key=f"lens_{s}_{i}")
                shot["type"] = q4.selectbox("📷 نوع اللقطة", SHOT_TYPES, index=SHOT_TYPES.index(shot.get("type", "Medium")) if shot.get("type") in SHOT_TYPES else 1, key=f"stype_{s}_{i}")

                shot["description"] = st.text_area("📝 وصف اللقطة", value=shot.get("description", ""), height=80, key=f"shot_desc_{s}_{i}", placeholder="اكتب وصفًا دقيقًا لما يحدث داخل هذه اللقطة...")

                q5, q6, q7 = st.columns(3)
                shot["movement"] = q5.selectbox("🎥 حركة الكاميرا", MOVEMENTS, index=MOVEMENTS.index(shot.get("movement", "Static")) if shot.get("movement") in MOVEMENTS else 0, key=f"mov_{s}_{i}")
                shot["transition"] = q6.selectbox("🎞️ الانتقال", TRANSITIONS, index=TRANSITIONS.index(shot.get("transition", "Cut")) if shot.get("transition") in TRANSITIONS else 0, key=f"trans_{s}_{i}")
                shot["filter"] = q7.selectbox("✨ فلتر النعومة", FILTERS, index=FILTERS.index(shot.get("filter", "No Filter")) if shot.get("filter") in FILTERS else 0, key=f"filter_{s}_{i}")

                shot["dialogue"] = st.text_area("💬 الحوار", value=shot.get("dialogue", ""), height=70, key=f"dialogue_{s}_{i}")
                a1, a2 = st.columns(2)
                shot["music"] = a1.text_input("🎵 الموسيقى", value=shot.get("music", ""), key=f"music_{s}_{i}")
                shot["sfx"] = a2.text_input("🔊 المؤثرات", value=shot.get("sfx", ""), key=f"sfx_{s}_{i}")

                prompt = build_shot_prompt(global_settings, scene_data, shot)
                st.text_area("✍️ البرومبت النهائي", value=prompt, height=140, key=f"prompt_{s}_{i}")
                st.caption(f"Runway prompt length: {len(trim_prompt(prompt))}/1000")

                b1, b2, b3, b4 = st.columns(4)
                if b1.button("🎥 توليد هذه اللقطة فقط", key=f"gen_shot_{s}_{i}"):
                    video_key = f"{scene_key}_shot_{i+1}"
                    shot_generation_duration = supported_duration(model, int(shot.get("duration", runway_duration)))
                    if shot_generation_duration != int(shot.get("duration", shot_generation_duration)):
                        st.warning(f"مدة اللقطة المحددة غير مدعومة لهذا الموديل، سيتم استخدام أقرب مدة مدعومة: {shot_generation_duration} ثانية")
                    payload = build_payload(model, prompt, shot_generation_duration, ratio)
                    st.json(payload)
                    if safe_mode:
                        st.session_state.videos[video_key] = {"url": None, "prompt": prompt, "status": "mock", "time": str(datetime.now()), "model": model, "duration": shot_generation_duration, "ratio": ratio}
                        st.info("الوضع الآمن مفعل: تم إنشاء بطاقة بدون استهلاك رصيد")
                    else:
                        try:
                            with st.spinner("جاري التوليد عبر Runway..."):
                                task = create_runway_task(payload)
                                task_id = task.get("id")
                                result = poll_task(task_id) if task_id else task
                                output = result.get("output") or []
                                url = output[0] if isinstance(output, list) and output else None
                                st.session_state.videos[video_key] = {"url": url, "prompt": prompt, "status": result.get("status", "done"), "time": str(datetime.now()), "model": model, "duration": shot_generation_duration, "ratio": ratio}
                                st.success("تم توليد اللقطة")
                        except Exception as e:
                            st.error(str(e))
                            st.session_state.videos[video_key] = {"url": None, "prompt": prompt, "status": "failed", "error": str(e), "time": str(datetime.now()), "model": model, "duration": shot_generation_duration, "ratio": ratio}

                if b2.button("➕ إضافة لقطة بعد هذه", key=f"insert_{s}_{i}"):
                    shots.insert(i+1, default_shots(1)[0] | {"title": f"لقطة {i+2}"})
                    st.rerun()
                if b3.button("📑 نسخ اللقطة", key=f"dup_{s}_{i}"):
                    shots.insert(i+1, dict(shot))
                    st.rerun()
                if b4.button("🗑️ حذف", key=f"del_{s}_{i}"):
                    if len(shots) > 1:
                        shots.pop(i)
                        st.rerun()
                    else:
                        st.warning("لا يمكن حذف آخر لقطة")

        st.markdown("### 🎬 توليد المشهد كامل")
        if st.button(f"🎬 توليد المشهد رقم {s+1} كامل", key=f"gen_scene_{s}"):
            progress = st.progress(0)
            scene_duration_plan = distribute_scene_durations(model, int(scene_duration), len(st.session_state.scene_shots[scene_key]))
            st.caption(f"خطة مدد لقطات المشهد حسب مدة المشهد {scene_duration} ثانية: {scene_duration_plan}")
            for i, shot in enumerate(st.session_state.scene_shots[scene_key]):
                st.write(f"جاري توليد لقطة {i+1} من {len(st.session_state.scene_shots[scene_key])}")
                prompt = build_shot_prompt(global_settings, scene_data, shot)
                current_scene_clip_duration = scene_duration_plan[i] if i < len(scene_duration_plan) else supported_duration(model, int(runway_duration))
                payload = build_payload(model, prompt, current_scene_clip_duration, ratio)
                st.json(payload)
                video_key = f"{scene_key}_shot_{i+1}"
                if safe_mode:
                    st.session_state.videos[video_key] = {"url": None, "prompt": prompt, "status": "mock", "time": str(datetime.now()), "model": model, "duration": current_scene_clip_duration, "ratio": ratio}
                else:
                    try:
                        task = create_runway_task(payload)
                        task_id = task.get("id")
                        result = poll_task(task_id) if task_id else task
                        output = result.get("output") or []
                        url = output[0] if isinstance(output, list) and output else None
                        st.session_state.videos[video_key] = {"url": url, "prompt": prompt, "status": result.get("status", "done"), "time": str(datetime.now()), "model": model, "duration": current_scene_clip_duration, "ratio": ratio}
                    except Exception as e:
                        st.error(f"فشل توليد لقطة {i+1}: {e}")
                        st.session_state.videos[video_key] = {"url": None, "prompt": prompt, "status": "failed", "error": str(e), "time": str(datetime.now()), "model": model, "duration": current_scene_clip_duration, "ratio": ratio}
                progress.progress((i + 1) / len(st.session_state.scene_shots[scene_key]))
            st.success("انتهى توليد المشهد")

        st.markdown("### 📚 مكتبة فيديوهات المشهد")
        found = False
        for key, item in list(st.session_state.videos.items()):
            if key.startswith(scene_key):
                found = True
                with st.container(border=True):
                    st.markdown(f"**{key.replace(scene_key+'_','').replace('_',' ')}** — {item.get('status')}")
                    st.caption(f"{item.get('model')} | {item.get('duration')}s | {item.get('ratio')} | {item.get('time')}")
                    if item.get("url"):
                        st.video(item["url"])
                    else:
                        st.info("بطاقة Mock أو لم يرجع رابط فيديو")
                    with st.expander("البرومبت المستخدم"):
                        st.code(item.get("prompt", ""))
        if not found:
            st.caption("لا توجد فيديوهات بعد في مكتبة هذا المشهد")

        st.markdown("</div>", unsafe_allow_html=True)

with tab_library:
    st.markdown('<div class="card"><h2>📚 مكتبة عامة للمشروع</h2><p class="muted">هذه مكتبة مساعدة عامة. المراجع الأساسية الآن داخل كل مشهد.</p>', unsafe_allow_html=True)
    lib_files = st.file_uploader("ارفع مراجع عامة", type=["jpg", "jpeg", "png", "webp"], accept_multiple_files=True)
    display_upload_grid(lib_files, "المراجع العامة")
    st.markdown("</div>", unsafe_allow_html=True)

with tab_export:
    st.markdown('<div class="card"><h2>📦 التصدير</h2>', unsafe_allow_html=True)
    export_text = ["محترف الإخراج — Export", f"Model: {model}", f"Ratio: {ratio}", f"Runway Duration: {runway_duration}", ""]
    for scene_key, shots in st.session_state.scene_shots.items():
        export_text.append(f"## {scene_key}")
        for i, shot in enumerate(shots):
            export_text.append(f"### Shot {i+1}: {shot.get('title')}")
            export_text.append(str(shot))
            export_text.append("")
    export_content = "\n".join(export_text)
    st.download_button("تحميل TXT", export_content, file_name="mohtaref_export.txt")
    st.markdown("</div>", unsafe_allow_html=True)
