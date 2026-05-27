import streamlit as st
import time
from client import gem3
from roadmap import roadmap_generator
import urllib.parse
import os
from googleapiclient.discovery import build
import json
from dotenv import load_dotenv
import streamlit.components.v1 as components
from duckduckgo_search import DDGS

# Load the summer programs database once
with open("ivy_scholars_db.json", "r", encoding="utf-8") as f:
    summer_programs = json.load(f)

load_dotenv()

# --- Free DuckDuckGo Search Function with Caching ---
# --- Free DuckDuckGo Search Function with Caching ---
@st.cache_data(show_spinner=False)
def free_web_search(query, num_results=2):
    """Perform free web search via DuckDuckGo and return a list of links."""
    links = []
    try:
        with DDGS() as ddgs:
            results = ddgs.text(query, max_results=num_results)
            if results:
                for item in results:
                    link = item.get("href")
                    # Strict validation to block weird ad redirects or trash domains
                    if link and not any(bad in link for bad in ["adclix", "clickserve", "doubleclick"]):
                        links.append(link)
    except Exception:
        pass
    return links

# --- Clean, targeted resource linking ---
def fetch_resource_links(skill, week_num, mini_title):
    # Appending massive platforms to keywords to force clean domain matches
    articles = free_web_search(f"{skill} {mini_title} documentation guide site:medium.com OR site:dev.to", num_results=2)
    courses = free_web_search(f"{skill} {mini_title} course site:coursera.org OR site:edx.org OR site:udemy.com", num_results=2)
    videos = free_web_search(f"{skill} {mini_title} video tutorial site:youtube.com", num_results=2)
    
    return {"articles": articles, "courses": courses, "videos": videos}


# --- APP CONFIGURATION ---
st.set_page_config(page_title="Career Granny", layout="wide", page_icon="🚀")

# --- PROFESSIONAL STYLING ---
st.markdown("""
    <style>
    .main { background-color: #f4f7f9; }
    div.stButton > button:first-child {
        background-color: #007bff; color: white; border-radius: 8px; border: none; transition: 0.3s;
    }
    div.stButton > button:hover { background-color: #0056b3; border: none; }
    
    /* Clickable Card Styling */
    .career-card {
        background-color: black; padding: 20px; border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1); border-left: 5px solid #007bff;
        margin-bottom: 15px; cursor: pointer; transition: transform 0.2s;
    }
    .career-card:hover { transform: translateY(-5px); border-left: 5px solid #28a745; }
    </style>
    """, unsafe_allow_html=True)


# --- SESSION STATE INITIALIZATION ---
if 'step' not in st.session_state:
    st.session_state.step = 1
    st.session_state.user_data = {}
    st.session_state.profiles = []
    st.session_state.target = ""
    st.session_state.recommendations = None


# --- SHARED FUNCTIONS ---
def multi_step_loader(messages):
    container = st.empty()
    progress_bar = st.progress(0)
    for i, msg in enumerate(messages):
        container.info(f"⏳ {msg}...")
        progress_bar.progress((i + 1) / len(messages))
        time.sleep(0.8)
    container.empty()
    progress_bar.empty()


def save_profile():
    if st.session_state.user_data:
        profile = {
            "name": f"Analysis {len(st.session_state.profiles) + 1}",
            "data": st.session_state.user_data,
            "target": st.session_state.target
        }
        st.session_state.profiles.append(profile)
        st.toast("✅ Profile saved to sidebar!")


# --- SIDEBAR: PROFILE MANAGEMENT ---
with st.sidebar:
    st.title("👤 Student Portal")
    if st.button("➕ New Analysis"):
        st.session_state.step = 1
        st.session_state.target = ""
        st.session_state.recommendations = None
        st.rerun()
    
    st.divider()
    st.subheader("Saved Profiles")
    if not st.session_state.profiles:
        st.caption("No profiles saved yet.")
    for idx, p in enumerate(st.session_state.profiles):
        path_label = p['data'].get('chosen_path', 'New')
        if st.sidebar.button(f"📂 {p['name']}: {p['target'] if p['target'] else path_label}", key=f"prof_{idx}"):
            st.session_state.user_data = p['data']
            st.session_state.target = p['target']
            st.session_state.step = 3 if p['target'] else 2
            st.rerun()


# --- MAIN APP FLOW ---
# STEP 1: SMART INPUT (WITH PATH SELECTION DROPDOWN)
if st.session_state.step == 1:
    st.title("🎓 Career Granny")
    st.markdown("#### *Let's build your personalized future roadmap.*")
    
    col1, col2 = st.columns([1, 1])
    with col1:
        with st.container(border=True):
            st.subheader("Select Your Target Pathway")
            chosen_path = st.selectbox(
                "What path are you considering after high school?",
                [
                    "Four-Year University",
                    "Community College",
                    "Trade School / Vocational",
                    "Directly joining the workforce",
                    "Undecided"
                ]
            )
            
            st.divider()
            st.subheader("Your Background")
            skills = st.text_area("Skills", placeholder="e.g. Python, Graphic Design, Public Speaking")
            courses = st.text_area("Advanced Courses & Electives", placeholder="e.g. AP Physics, IB English, Honors Math")
            enrichment = st.text_area("Extracurriculars & Hobbies", placeholder="e.g. Robotics Club, Volunteering, Blogging")

            if st.button("Generate My Path ➔"):
                if skills and courses:
                    st.session_state.user_data = {
                        "chosen_path": chosen_path,
                        "skills": skills,
                        "courses": courses,
                        "enrichment": enrichment
                    }
                    st.session_state.recommendations = None 
                    multi_step_loader(["Analyzing trajectory settings", "Matching skills with selected pathway", "Scanning industry trends"])
                    st.session_state.step = 2
                    st.rerun()
                else:
                    st.warning("Please fill in your background to proceed.")
    with col2:
        st.image("https://illustrations.popsy.co", width=True)


# --- STEP 2: LIST CAREER & COLLEGE PATHS ---
elif st.session_state.step == 2:
    data = st.session_state.user_data
    st.subheader(f"🎯 Recommended Options for Path: {data['chosen_path']}")
    st.caption("Click on the path name to explore more details.")

    if not st.session_state.recommendations:
        # Prompt explicitly optimized to request exactly 3 targeted paths total
        prompt = (f"Suggest EXACTLY 3 personalized, high-impact target paths (these can be specific job roles, vocational targets, certifications, or academic majors depending on what fits best) "
                  f"tailored for a student whose clear future objective track is '{data['chosen_path']}'. "
                  f"Do not assume a 4-year university context unless that option was selected. Take into account their current skills: {data['skills']}, "
                  f"courses: {data['courses']}, and hobbies: {data.get('enrichment', '')}. "
                  f"Return ONLY a comma-separated list of the 3 titles.")
        raw_rec = gem3(prompt)
        st.session_state.recommendations = [r.strip() for r in raw_rec.split(',')]

    for idx, rec in enumerate(st.session_state.recommendations):
        description_prompt = f"Provide a 2-3 sentence description explaining why the path '{rec}' perfectly aligns with someone balancing their background profile with the specific goal of a '{data['chosen_path']}' track."
        desc = gem3(description_prompt)

        st.markdown(f"[**{rec}**](#)", unsafe_allow_html=True)
        st.markdown(desc)

        if st.button(f"Explore {rec}", key=f"explore_{idx}"):
            st.session_state.target = rec
            st.session_state.step = 3
            st.rerun()

# --- STEP 3: GROWTH OPPORTUNITIES ---
elif st.session_state.step == 3:
    target = st.session_state.target
    data = st.session_state.user_data
    st.title(f"🔍 Deep Dive: {target}")
    st.caption(f"Context Track: {data['chosen_path']}")

    # Helper link string builder
    import urllib.parse
    def make_search_link(q):
        return f"https://www.google.com/search?q={urllib.parse.quote_plus(q)}"

    with open("ivy_scholars_db.json", "r", encoding="utf-8") as f:
        summer_programs = json.load(f)

    program_summaries = [f"{p['name']}: {p['description'][:300]}" for p in summer_programs]
    
    program_prompt = f"""
    You are an expert career advisor. Select 3 fitting matching program names from the database below, and 2 additional existing external real world programs or bootcamps.
    For each, provide its exact 'name' and a single 1-sentence description.
    Return STRICT JSON ONLY.
    Format: {{"programs": [{{"name": "Program Name", "description": "One sentence description."}}]}}

    Database options:
    {chr(10).join(program_summaries)}
    """
    
    with st.spinner("Curating personalized development path structures..."):
        try:
            raw_p = gem3(program_prompt).strip().replace("```json", "").replace("```", "")
            prog_data = json.loads(raw_p).get("programs", [])
        except:
            prog_data = [{"name": "Google UX Design Professional Certificate", "description": "A comprehensive training framework for foundational layout design."}]

    skill_query = gem3(f"List the top 5 core technical or execution skills necessary to succeed in '{target}' within the realm of a '{data['chosen_path']}' execution plan. Return ONLY a comma-separated list.")
    skills_list = [s.strip() for s in skill_query.split(",")]
    st.session_state.skills_list = skills_list

    st.divider()
    st.subheader("Growth Opportunities")
    
    resource_prompt = (f"Act as an expert technical counselor. For a student breaking into '{target}', provide real online courses and competitions.\n"
                       f"For each item, return a distinct name and a 1-sentence description detailing what the user achieves.\n"
                       f"Return STRICT JSON format ONLY. No conversational text.\n"
                       f"Format exactly like this:\n"
                       f"{{\n"
                       f"  \"courses\": [{{\"name\": \"Coursera Python for Everybody Specialization\", \"description\": \"Master foundational coding workflows through structural execution exercises.\"}}],\n"
                       f"  \"competitions\": [{{\"name\": \"Kaggle Titanic Machine Learning from Disaster\", \"description\": \"Build predictive models to compete in a world-wide open dataset ranking.\"}}],\n"
                       f"  \"strategic_tip\": \"Focus heavily on project deployment.\"\n"
                       f"}}")

    try:
        raw_resources = gem3(resource_prompt).strip().replace("```json", "").replace("```", "")
        resource_data = json.loads(raw_resources)
    except:
        resource_data = {"courses": [], "competitions": [], "strategic_tip": "Build an open-source tool on GitHub to show capability."}

    # --- Render Courses ---
    st.markdown("### 📚 Online Courses & Certifications")
    for course in resource_data.get("courses", []):
        c_name = course.get("name")
        c_desc = course.get("description")
        st.markdown(f"- [{c_name}]({make_search_link(c_name)}) — *{c_desc}*")
    
    # --- Render Competitions ---
    st.markdown("### 🏆 Competitions")
    for comp in resource_data.get("competitions", []):
        comp_name = comp.get("name")
        comp_desc = comp.get("description")
        st.markdown(f"- [{comp_name}]({make_search_link(comp_name)}) — *{comp_desc}*")

    # --- Render Selected Programs ---
    st.markdown("### 🚀 Selected Programs & Bootcamps")
    for prog in prog_data:
        p_name = prog.get("name")
        p_desc = prog.get("description")
        st.markdown(f"- [{p_name}]({make_search_link(p_name)}) — *{p_desc}*")

    st.markdown("### 💡 Strategic Advancement Tip")
    st.info(resource_data.get("strategic_tip", "Build real-world portfolios match your chosen tracking path."))

    st.write("---")
    st.write("#### 🛠 Skill Mastery Roadmaps")
    for idx, skill in enumerate(st.session_state.skills_list[:5]):
        if st.button(f"💡 {skill}", key=f"skill_{idx}"):
            st.session_state.skill = skill
            st.session_state.step = 4
            st.rerun()

# --- STEP 4: VERIFIED ROADMAP ---
elif st.session_state.step == 4:
    skill = st.session_state.get("skill", None)
    if not skill:
        st.error("No skill selected. Returning to Strategy page...")
        st.session_state.step = 3
        st.rerun()

    st.title(f"📅 4-Week Mastery: {skill}")
    roadmap = roadmap_generator(skill)
    st.json(roadmap)

    if st.button("⬅️ Back to Insights"):
        st.session_state.step = 3
        st.rerun()
