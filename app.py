
import os, time, json
from datetime import datetime
import requests
import streamlit as st

st.set_page_config(page_title="محترف الإخراج | Mohtaref Al Ekhraj", page_icon="🎬", layout="wide", initial_sidebar_state="expanded")
RUNWAY_API_KEY = os.getenv("RUNWAYML_API_SECRET", "")
RUNWAY_BASE_URL = "https://api.dev.runwayml.com/v1"
RUNWAY_VERSION = "2024-11-06"

MODELS = ["veo3.1_fast", "veo3.1", "seedance2", "kling3.0_standard"]
MODEL_FEATURES = {
    "veo3.1_fast": {"durations": [4,6,8], "ratios": ["1920:1080","1080:1920","1440:1440"]},
    "veo3.1": {"durations": [4,6,8], "ratios": ["1920:1080","1080:1920","1440:1440"]},
    "kling3.0_standard": {"durations": [4,6,8], "ratios": ["1920:1080","1080:1920","1440:1440"]},
    "seedance2": {"durations": list(range(5,16)), "ratios": ["1280:720","720:1280","960:960","640:640","992:432","864:496","752:560","560:752","496:864","1470:630","1112:834","834:1112"]},
}
SHOT_TYPES = ["Wide","Medium","Close-up","Extreme Close-up","Two Shot","Over Shoulder","POV","Insert","Reaction Shot"]
ANGLES = ["Eye Level","Low Angle","High Angle","Dutch Angle","Top Shot","Over Shoulder"]
MOVEMENTS = ["Static","Dolly In","Dolly Out","Pan","Tilt","Handheld","Crane","Drone","Slow Push-in","Tracking"]
LENSES = ["16mm","24mm","35mm","50mm","85mm","100mm Macro","70-200mm","Anamorphic","Vintage Lens"]
CAMERAS = ["ARRI Alexa Mini LF","RED Komodo","RED V-Raptor","Sony Venice","Sony FX3","Blackmagic URSA","Canon C70","Phantom Flex"]
LIGHTING = ["Soft Cinematic Key Light","Golden Hour","Window Light","Diffused Studio Light","Warm Yemeni Indoor","Documentary Natural","Moody Drama","Commercial Beauty Light","Soft Interview Lighting","Lantern Night Light"]
FILTERS = ["No Filter","Black Pro Mist 1/8","Black Pro Mist 1/4","Black Pro Mist 1/2","Hollywood Black Magic","Soft FX","Glimmerglass","Natural Skin Softening"]
COLOR_MODES = ["Cinematic LUT","Flat / Log","Natural Rec709","Warm Yemeni Earthy","Documentary Neutral","Dark Dramatic","Luxury Gold"]

def init_state():
    st.session_state.setdefault("scenes", [])
    st.session_state.setdefault("project_name", "محترف الإخراج")
    st.session_state.setdefault("last_clip_url", "")

def css():
    st.markdown("""
    <style>
    .stApp{background:radial-gradient(circle at top left,#17122e 0%,#080911 45%,#050509 100%);color:#f8f8ff;direction:rtl}.block-container{padding-top:1.2rem}
    [data-testid="stSidebar"]{background:linear-gradient(180deg,#0b0b16,#121026);border-left:1px solid #2f2a6b}.hero{border:1px solid rgba(142,98,255,.35);border-radius:24px;padding:24px;background:linear-gradient(135deg,rgba(94,44,255,.22),rgba(7,10,18,.65));box-shadow:0 20px 60px rgba(0,0,0,.28)}
    .badge{display:inline-block;padding:6px 10px;border-radius:999px;margin:3px;background:rgba(115,80,255,.18);border:1px solid rgba(137,105,255,.38);color:#f3efff;font-size:13px}.ok{background:rgba(30,170,105,.16);border-color:rgba(30,170,105,.4)}
    </style>
    """, unsafe_allow_html=True)

def trim_prompt(prompt, max_chars=950):
    prompt=(prompt or "").strip()
    return prompt if len(prompt)<=max_chars else prompt[:max_chars].rsplit(" ",1)[0]+"..."

def ensure_scene(idx):
    while len(st.session_state.scenes)<=idx:
        n=len(st.session_state.scenes)+1
        st.session_state.scenes.append({"title":f"المشهد {n}","description":"","camera":"ARRI Alexa Mini LF","lighting":"Golden Hour","emotion":"توتر هادئ","fps":25,"max_duration":60,"start_state":"","end_state":"","storyboard_mode":"Text Storyboard","storyboard_text":"","storyboard_active":False,"color_mode":"Cinematic LUT","flat_log":False,"shots":[],"videos":{},"previews":{},"characters_refs_count":0,"clothing_refs_count":0,"environment_refs_count":0,"color_refs_count":0})

def build_protection_text(flags):
    parts=[]
    if flags.get("strict"): parts += ["Strictly follow the provided direction and references.","Do not invent or add new visual elements.","Preserve exact framing, wardrobe, environment, and cinematic direction."]
    if flags.get("realism"): parts += ["Ultra realistic cinematic image.","Natural skin texture, photorealistic lighting, natural imperfections.","No AI plastic skin, no CGI look, no stylized rendering."]
    if flags.get("face"): parts += ["Maintain identical facial identity across all shots.","Do not alter facial structure, face shape, eyes, beard, hair, skin tone, age, or expression."]
    if flags.get("scene_lock"): parts += ["Do not add new people, locations, or background elements.","Preserve original environment exactly."]
    if flags.get("anatomy"): parts += ["Correct human anatomy, natural hands with five fingers only.","No extra limbs, no distorted fingers, realistic ears and eyes."]
    if flags.get("camera_expand"): parts += ["When camera expands or moves, do not invent new places, objects, people, or buildings.","Extend only what matches the original image."]
    if flags.get("anti_deform"): parts += ["No warped faces, melted skin, distorted hands, duplicated body parts, or AI artifacts."]
    return " ".join(parts)

def refs_text(scene):
    parts=[]
    if scene.get("characters_refs_count",0): parts.append("Match uploaded character references and preserve identity.")
    if scene.get("clothing_refs_count",0): parts.append("Match uploaded clothing references, wardrobe textures, and colors.")
    if scene.get("environment_refs_count",0): parts.append("Match uploaded environment references, architecture, location, and atmosphere.")
    if scene.get("color_refs_count",0): parts.append("Match cinematic grading and color palette from uploaded reference images.")
    if scene.get("storyboard_active"): parts.append("Follow uploaded or written storyboard composition exactly.")
    return " ".join(parts)

def build_prompt(scene, shot, flags):
    lines = [
        f'Cinematic shot for project "{st.session_state.project_name}".',
        f"Overall scene: {scene.get('description','')}",
        f"Shot: {shot.get('title','')}. Type: {shot.get('type','')}, angle: {shot.get('angle','')}, movement: {shot.get('movement','')}.",
        f"Camera: {scene.get('camera','')}. Lens: {shot.get('lens','')}.",
        f"Lighting: {shot.get('lighting','')}. Emotion: {shot.get('emotion','')}. Notes: {shot.get('emotion_notes','')}.",
        f"Dialogue: {shot.get('dialogue','')}. Voice over: {shot.get('voiceover','')}.",
        f"Shot duration planning: {shot.get('duration',6)} seconds.",
        f"Continuity: starts with {scene.get('start_state','')}, ends with {scene.get('end_state','')}. Continue directly from previous shot when applicable.",
        f"Storyboard: {scene.get('storyboard_text','')}",
        f"{refs_text(scene)} {build_protection_text(flags)}"
    ]
    p = "\n".join(lines)
    if scene.get('flat_log') or scene.get('color_mode')=='Flat / Log':
        p += " Flat log cinematic profile, low contrast, neutral saturation, preserved highlights and shadows, grade-ready, do not bake strong LUT."
    else:
        p += f" Color mode: {scene.get('color_mode','Cinematic LUT')}, professional cinematic grading."
    if shot.get('type') in ['Close-up','Extreme Close-up']:
        p += " Natural facial skin texture, professional beauty lighting, soft cinematic diffusion, natural eye reflections."
    return p.strip()

def auto_generate_shots(scene_idx):
    scene=st.session_state.scenes[scene_idx]
    storyboard=scene.get('storyboard_text','').strip()
    if storyboard:
        lines=[l.strip('-•0123456789. )(').strip() for l in storyboard.splitlines() if l.strip()] or [storyboard]
    else:
        lines=[f"Beat {i+1}: cinematic continuation of the scene" for i in range(max(1, round(int(scene.get('max_duration',60))/6)))]
    scene['shots']=[]
    for i,line in enumerate(lines[:30]):
        scene['shots'].append({"title":f"Shot {i+1}","type":SHOT_TYPES[i%len(SHOT_TYPES)],"angle":ANGLES[i%len(ANGLES)],"movement":MOVEMENTS[i%len(MOVEMENTS)],"lens":LENSES[i%len(LENSES)],"lighting":scene.get('lighting','Golden Hour'),"emotion":scene.get('emotion',''),"emotion_notes":line,"duration":6,"dialogue":"","voiceover":"","transition":["Cut","Match Cut","Fade","Motion Cut","Sound Bridge"][i%5]})

def headers():
    return {"Authorization":f"Bearer {RUNWAY_API_KEY}","Content-Type":"application/json","X-Runway-Version":RUNWAY_VERSION}

def build_runway_payload(model, mode, prompt, duration, ratio, refs=None):
    refs=refs or {}
    payload={"model":model,"promptText":trim_prompt(prompt,950),"duration":int(duration),"ratio":ratio}
    if model=="seedance2":
        if refs.get('references'): payload['references']=refs['references'][:9]
        if refs.get('referenceVideos'): payload['referenceVideos']=refs['referenceVideos'][:3]
        if refs.get('referenceAudio'): payload['referenceAudio']=refs['referenceAudio'][:3]
        if mode=='Image to Video' and refs.get('promptImage'): payload['promptImage']=refs['promptImage']
        if mode=='Video to Video' and refs.get('promptVideo'): payload['promptVideo']=refs['promptVideo']
    return payload

def runway_create_task(payload, mode='Text to Video'):
    if not RUNWAY_API_KEY: raise RuntimeError('لم يتم العثور على RUNWAYML_API_SECRET داخل Environment Variables.')
    endpoint='text_to_video'
    if payload.get('model')=='seedance2':
        endpoint = 'image_to_video' if mode=='Image to Video' else 'video_to_video' if mode=='Video to Video' else 'text_to_video'
    r=requests.post(f"{RUNWAY_BASE_URL}/{endpoint}", headers=headers(), json=payload, timeout=60)
    if r.status_code>=400: raise RuntimeError(f"Runway error {r.status_code}: {r.json() if r.text else r.text}")
    return r.json()

def runway_poll(task_id, max_wait=240):
    start=time.time()
    while time.time()-start<max_wait:
        r=requests.get(f"{RUNWAY_BASE_URL}/tasks/{task_id}", headers=headers(), timeout=60)
        if r.status_code>=400: raise RuntimeError(f"Runway polling error {r.status_code}: {r.text}")
        data=r.json(); status=data.get('status','').upper()
        if status in ['SUCCEEDED','FAILED','CANCELED']: return data
        time.sleep(4)
    raise TimeoutError('انتهى وقت الانتظار قبل اكتمال الفيديو.')

def gallery(files, title):
    st.caption(title)
    if not files: st.info('لا توجد صور مرفوعة بعد.'); return
    cols=st.columns(min(5,max(1,len(files))))
    for i,f in enumerate(files[:15]):
        with cols[i%len(cols)]: st.image(f, use_container_width=True, caption=str(i+1))

def export_project():
    return json.dumps({"project_name":st.session_state.project_name,"scenes":st.session_state.scenes,"exported_at":datetime.utcnow().isoformat()}, ensure_ascii=False, indent=2)

init_state(); css()
with st.sidebar:
    st.markdown('## 🎬 محترف الإخراج')
    st.caption('Mohtaref Al Ekhraj — Unified Runway')
    st.session_state.project_name=st.text_input('اسم المشروع', st.session_state.project_name)
    safe_mode=st.toggle('🛡️ الوضع الآمن', value=True)
    strict_mode=st.toggle('🎯 وضع الالتزام الكامل', value=True)
    realism_mode=st.toggle('📸 الواقعية القصوى', value=True)
    face_mode=st.toggle('👤 حماية ملامح الشخصية', value=True)
    scene_lock=st.toggle('🔒 قفل المشهد الأصلي', value=True)
    anatomy=st.toggle('✋ حماية الجسم والأطراف', value=True)
    camera_expand=st.toggle('🖼️ حماية توسعة الكادر', value=True)
    anti_deform=st.toggle('🚫 منع التشوهات', value=True)
    st.caption('RUNWAYML_API_SECRET')
    st.success('موجود ✅' if RUNWAY_API_KEY else 'غير موجود ⚠️')
flags={"strict":strict_mode,"realism":realism_mode,"face":face_mode,"scene_lock":scene_lock,"anatomy":anatomy,"camera_expand":camera_expand,"anti_deform":anti_deform}

st.markdown('<div class="hero"><h1>🎬 محترف الإخراج</h1><p>منصة إخراج سينمائي بالذكاء الاصطناعي — مشاهد، لقطات، مراجع، استوري بورد، واستمرارية عبر Runway.</p><span class="badge ok">Unified Runway Engine</span><span class="badge">Seedance 2 داخل Runway</span><span class="badge">Storyboard Driven</span><span class="badge">Ultra Realism</span></div>', unsafe_allow_html=True)

tabs=st.tabs(['🎞️ هوية الفيلم','🎬 المشاهد واللقطات','🎬 Runway','📂 حفظ وتصدير'])
with tabs[0]:
    c1,c2,c3=st.columns(3)
    with c1:
        st.selectbox('نوع المشروع',['Drama','Commercial','Documentary','Music Video','Film'])
        st.selectbox('أسلوب الإخراج',['Hollywood','Netflix','Documentary','Arabic Drama','Yemeni Heritage','Dark Thriller','Sports','Luxury Commercial'])
    with c2:
        st.selectbox('الكاميرا العامة',CAMERAS)
        st.selectbox('الإضاءة العامة',LIGHTING)
    with c3:
        st.selectbox('نظام اللون',COLOR_MODES)
        st.selectbox('فلتر النعومة',FILTERS)
    st.subheader('🇾🇪 مكتبة الهوية اليمنية')
    y1,y2,y3=st.columns(3)
    with y1: st.selectbox('البيئة',['بدون','حضرموت - وادي دوعن','سيئون - شوارع طينية','شبام','تريم','المكلا','سوق شعبي','متحف تراثي','بيت طيني'])
    with y2: st.selectbox('اللبس',['بدون','ثوب يمني','عمامة حضرمية','معوز','جنبية','ملابس ريفية','ملابس حضرمية قديمة'])
    with y3: st.selectbox('اللهجة',['فصحى','يمنية','حضرمية','بدون كلام'])

with tabs[1]:
    top=st.columns([1,1,1,2])
    with top[0]: num_scenes=st.number_input('عدد المشاهد',1,20,max(1,len(st.session_state.scenes) or 1))
    if len(st.session_state.scenes)<num_scenes: ensure_scene(num_scenes-1)
    elif len(st.session_state.scenes)>num_scenes: st.session_state.scenes=st.session_state.scenes[:num_scenes]
    with top[1]: scene_idx=st.selectbox('اختر المشهد', list(range(num_scenes)), format_func=lambda i: st.session_state.scenes[i]['title'])
    with top[2]:
        if st.button('➕ توليد لقطات من الاستوري بورد'):
            auto_generate_shots(scene_idx); st.success('تم تقسيم المشهد إلى لقطات.')
    ensure_scene(scene_idx); scene=st.session_state.scenes[scene_idx]
    st.subheader('🎬 إعدادات المشهد')
    a,b,c=st.columns(3)
    with a:
        scene['title']=st.text_input('عنوان المشهد',scene.get('title',''),key=f'title_{scene_idx}')
        scene['camera']=st.selectbox('🎥 نوع الكاميرا للمشهد',CAMERAS,index=CAMERAS.index(scene.get('camera',CAMERAS[0])) if scene.get('camera') in CAMERAS else 0,key=f'cam_{scene_idx}')
        scene['max_duration']=st.selectbox('⏳ المدة القصوى للمشهد',[15,30,45,60,90,120],index=[15,30,45,60,90,120].index(scene.get('max_duration',60)),key=f'maxdur_{scene_idx}')
        st.caption(f"عدد اللقطات المقترح: {max(1, round(int(scene['max_duration'])/6))}")
    with b:
        scene['lighting']=st.selectbox('💡 إضاءة المشهد',LIGHTING,index=LIGHTING.index(scene.get('lighting',LIGHTING[0])) if scene.get('lighting') in LIGHTING else 0,key=f'light_{scene_idx}')
        scene['color_mode']=st.selectbox('🎨 نظام اللون',COLOR_MODES,index=COLOR_MODES.index(scene.get('color_mode',COLOR_MODES[0])) if scene.get('color_mode') in COLOR_MODES else 0,key=f'colormode_{scene_idx}')
        scene['flat_log']=st.checkbox('🎨 تصوير فلات للتلوين اليدوي',value=scene.get('flat_log',False),key=f'flat_{scene_idx}')
    with c:
        scene['fps']=st.selectbox('🎞️ FPS',[24,25,30,50,60],index=[24,25,30,50,60].index(scene.get('fps',25)),key=f'fps_{scene_idx}')
        scene['emotion']=st.text_input('🎭 إحساس المشهد',scene.get('emotion',''),key=f'emo_{scene_idx}')
    scene['description']=st.text_area('📝 الوصف العام للمشهد',scene.get('description',''),height=100,key=f'desc_{scene_idx}')
    s1,s2=st.columns([1,2])
    with s1:
        scene['storyboard_active']=st.checkbox('تفعيل الاستوري بورد',scene.get('storyboard_active',False),key=f'storyactive_{scene_idx}')
        scene['storyboard_mode']=st.radio('نوع الاستوري بورد',['Text Storyboard','Image Storyboard'],key=f'storymode_{scene_idx}')
    with s2:
        if scene['storyboard_mode']=='Text Storyboard': scene['storyboard_text']=st.text_area('اكتب الاستوري بورد: كل سطر = لقطة',scene.get('storyboard_text',''),height=130,key=f'storytext_{scene_idx}')
        else: gallery(st.file_uploader('ارفع صور الاستوري بورد',type=['jpg','jpeg','png','webp'],accept_multiple_files=True,key=f'storyimgs_{scene_idx}'),'معرض الاستوري بورد')
    st.subheader('🖼️ مراجع المشهد')
    r1,r2,r3,r4=st.columns(4)
    with r1: f=st.file_uploader('👤 مراجع الشخصيات',type=['jpg','jpeg','png','webp'],accept_multiple_files=True,key=f'charrefs_{scene_idx}'); scene['characters_refs_count']=len(f or []); gallery(f,'شخصيات')
    with r2: f=st.file_uploader('👕 مراجع اللبس',type=['jpg','jpeg','png','webp'],accept_multiple_files=True,key=f'clothrefs_{scene_idx}'); scene['clothing_refs_count']=len(f or []); gallery(f,'لبس')
    with r3: f=st.file_uploader('🏛️ مراجع البيئة',type=['jpg','jpeg','png','webp'],accept_multiple_files=True,key=f'envrefs_{scene_idx}'); scene['environment_refs_count']=len(f or []); gallery(f,'بيئة')
    with r4: f=st.file_uploader('🎨 مراجع الألوان',type=['jpg','jpeg','png','webp'],accept_multiple_files=True,key=f'colorrefs_{scene_idx}'); scene['color_refs_count']=len(f or []); gallery(f,'ألوان')
    st.subheader('🎥 اللقطات')
    if not scene.get('shots') and st.button('🎞️ تقسيم المشهد تلقائيًا الآن',key=f'autosplit_{scene_idx}'):
        auto_generate_shots(scene_idx); st.rerun()
    for i,shot in enumerate(scene.get('shots',[])):
        with st.expander(f"🎥 {shot.get('title','Shot')} — {shot.get('type','')}", expanded=i==0):
            c1,c2,c3,c4=st.columns(4)
            with c1:
                shot['title']=st.text_input('عنوان اللقطة',shot.get('title',''),key=f'shtitle_{scene_idx}_{i}')
                shot['type']=st.selectbox('نوع اللقطة',SHOT_TYPES,index=SHOT_TYPES.index(shot.get('type',SHOT_TYPES[0])) if shot.get('type') in SHOT_TYPES else 0,key=f'shtype_{scene_idx}_{i}')
                shot['lens']=st.selectbox('🔭 العدسة الخاصة باللقطة',LENSES,index=LENSES.index(shot.get('lens',LENSES[0])) if shot.get('lens') in LENSES else 0,key=f'lens_{scene_idx}_{i}')
            with c2:
                shot['angle']=st.selectbox('زاوية الكاميرا',ANGLES,index=ANGLES.index(shot.get('angle',ANGLES[0])) if shot.get('angle') in ANGLES else 0,key=f'angle_{scene_idx}_{i}')
                shot['movement']=st.selectbox('حركة الكاميرا',MOVEMENTS,index=MOVEMENTS.index(shot.get('movement',MOVEMENTS[0])) if shot.get('movement') in MOVEMENTS else 0,key=f'move_{scene_idx}_{i}')
                shot['duration']=st.selectbox('⏱️ زمن اللقطة',list(range(1,11)),index=int(shot.get('duration',6))-1 if 1<=int(shot.get('duration',6))<=10 else 5,key=f'shdur_{scene_idx}_{i}')
            with c3:
                shot['lighting']=st.selectbox('إضاءة اللقطة',LIGHTING,index=LIGHTING.index(shot.get('lighting',LIGHTING[0])) if shot.get('lighting') in LIGHTING else 0,key=f'shlight_{scene_idx}_{i}')
                shot['emotion']=st.text_input('الإحساس',shot.get('emotion',''),key=f'shemotion_{scene_idx}_{i}')
                shot['transition']=st.selectbox('الانتقال',['Cut','Match Cut','Fade','Motion Cut','Sound Bridge','Reaction Cut'],key=f'trans_{scene_idx}_{i}')
            with c4:
                shot['dialogue']=st.text_area('💬 الحوار',shot.get('dialogue',''),height=80,key=f'dialog_{scene_idx}_{i}')
                shot['voiceover']=st.text_area('🎤 Voice Over',shot.get('voiceover',''),height=80,key=f'vo_{scene_idx}_{i}')
            shot['emotion_notes']=st.text_area('وصف الإحساس / الأداء',shot.get('emotion_notes',''),height=80,key=f'emnotes_{scene_idx}_{i}')
            full_prompt=build_prompt(scene,shot,flags); runway_prompt=trim_prompt(full_prompt,950)
            st.caption(f'Prompt length: {len(runway_prompt)} / 1000')
            st.code(runway_prompt,language='text')
            st.download_button('📥 تحميل برومنت اللقطة',full_prompt,file_name=f'scene{scene_idx+1}_shot{i+1}.txt',key=f'dlprompt_{scene_idx}_{i}')

with tabs[2]:
    st.subheader('🎬 Unified Runway Engine')
    r1,r2,r3,r4=st.columns(4)
    with r1: model=st.selectbox('الموديل',MODELS,index=0); features=MODEL_FEATURES[model]; st.caption(f"أقصى مدة لهذا الموديل: {max(features['durations'])} ثانية")
    with r2: runway_duration=st.selectbox('مدة Runway',features['durations'],index=len(features['durations'])-1)
    with r3: ratio=st.selectbox('اتجاه / Ratio',features['ratios'])
    with r4: mode=st.selectbox('Generation Mode',['Text to Video','Image to Video','Video to Video']) if model=='seedance2' else 'Text to Video'; st.info(mode)
    if model=='seedance2':
        st.subheader('🎬 Seedance 2 Advanced داخل Runway')
        seed_img_urls=st.text_area('🖼️ Image reference URLs — كل رابط في سطر','')
        seed_video_urls=st.text_area('🎞️ Video reference URLs — كل رابط في سطر','')
        seed_audio_urls=st.text_area('🎧 Audio reference URLs — كل رابط في سطر','')
        prompt_image_url=st.text_input('Image-to-Video promptImage URL')
        prompt_video_url=st.text_input('Video-to-Video promptVideo URL')
        use_previous=st.checkbox('🔁 استخدم اللقطة السابقة كمرجع استمرار',value=False)
    else:
        seed_img_urls=seed_video_urls=seed_audio_urls=prompt_image_url=prompt_video_url=''; use_previous=False
    if st.session_state.scenes:
        scene_for_gen=st.selectbox('اختر مشهد للتوليد',list(range(len(st.session_state.scenes))),format_func=lambda i:st.session_state.scenes[i]['title'])
        scene=st.session_state.scenes[scene_for_gen]
        if scene.get('shots'):
            shot_for_gen=st.selectbox('اختر لقطة',list(range(len(scene['shots']))),format_func=lambda i:scene['shots'][i]['title'])
            shot=scene['shots'][shot_for_gen]
            prompt=build_prompt(scene,shot,flags)
            refs={}
            if model=='seedance2':
                img_refs=[{'uri':u.strip()} for u in seed_img_urls.splitlines() if u.strip()][:9]
                vid_refs=[{'type':'video','uri':u.strip()} for u in seed_video_urls.splitlines() if u.strip()][:3]
                aud_refs=[{'type':'audio','uri':u.strip()} for u in seed_audio_urls.splitlines() if u.strip()][:3]
                if use_previous and st.session_state.last_clip_url: vid_refs.insert(0,{'type':'video','uri':st.session_state.last_clip_url})
                if img_refs: refs['references']=img_refs
                if vid_refs: refs['referenceVideos']=vid_refs[:3]
                if aud_refs: refs['referenceAudio']=aud_refs[:3]
                if mode=='Image to Video' and prompt_image_url: refs['promptImage']=[{'uri':prompt_image_url,'position':'first'}]
                if mode=='Video to Video' and prompt_video_url: refs['promptVideo']=prompt_video_url
            payload=build_runway_payload(model,mode,prompt,runway_duration,ratio,refs)
            st.json(payload)
            if st.button('🎬 توليد هذه اللقطة عبر Runway'):
                if safe_mode: st.warning('الوضع الآمن مفعل: لن يتم استهلاك رصيد Runway.')
                else:
                    try:
                        task=runway_create_task(payload,mode); st.write(task); tid=task.get('id')
                        if tid:
                            with st.spinner('جاري انتظار اكتمال الفيديو...'):
                                done=runway_poll(tid)
                            st.write(done); out=done.get('output',[])
                            if out:
                                url=out[0] if isinstance(out,list) else out; st.session_state.last_clip_url=url; scene.setdefault('videos',{})[str(shot_for_gen)]=url; st.video(url)
                    except Exception as e:
                        st.error(str(e))
        else: st.info('لا توجد لقطات داخل هذا المشهد. ارجع واضغط تقسيم المشهد تلقائيًا.')

with tabs[3]:
    st.subheader('📂 حفظ وتصدير')
    data=export_project()
    st.download_button('📥 تحميل المشروع JSON',data,file_name='mohtaref_al_ekhraj_project.json',mime='application/json')
    prompt_txt=[]
    for si,sc in enumerate(st.session_state.scenes):
        prompt_txt.append(f"SCENE {si+1}: {sc.get('title','')}\n{sc.get('description','')}\n")
        for hi,sh in enumerate(sc.get('shots',[])):
            prompt_txt.append(f"\n--- SHOT {hi+1}: {sh.get('title','')} ---\n{build_prompt(sc,sh,flags)}")
    st.download_button('📥 تحميل كل البرومنتات TXT','\n'.join(prompt_txt),file_name='all_prompts.txt')
    uploaded=st.file_uploader('📁 Load Project JSON',type=['json'])
    if uploaded and st.button('تحميل المشروع'):
        obj=json.load(uploaded); st.session_state.project_name=obj.get('project_name',st.session_state.project_name); st.session_state.scenes=obj.get('scenes',[]); st.success('تم تحميل المشروع.'); st.rerun()

st.caption('© Mohtaref Al Ekhraj — Render ready — RUNWAYML_API_SECRET from Environment Variables')
