import streamlit as st
from sqlalchemy import distinct, extract, text, insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.schema import CreateTable
from sqlalchemy.orm import joinedload
from sqlalchemy.engine import Engine
from db import SessionLocal, engine
from utils import login
from models1 import CoreValue, Programs, PlayerAssessments
from models import Players, Users
import datetime
from datetime import date

##Creación de Forms de Evaluación para DEMO con base en INFO SOCCER CENTRAL
##Falta actualización de tabla player_assessments para incluir los nuevos campos.
#Se utiliza un duplicado de models.py (models1.py) para evitar conflictos con la app principal
#y las llamadas actuales del form demo . 


def calc_age(birthdate: date) -> int:
    today = date.today()
    return (today.year - birthdate.year) - (
        (today.month, today.day) < (birthdate.month, birthdate.day)
    )
@st.cache_resource
def init_temp_tables() -> None:
    """Crea las tablas temporales core_values y programs en MySQL."""
    with engine.begin() as conn:
        # Core values
        conn.execute(text("DROP TEMPORARY TABLE IF EXISTS core_values"))
        conn.execute(text("""
            CREATE TEMPORARY TABLE core_values (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                description TEXT
            ) ENGINE=InnoDB;
        """))
        for name, desc in [
            ("Discipline", "Daily excellence through intentional action. Punctuality, preparation, focus during training, and consistent effort in all activities."),
            ("Wellbeing", "Holistic care of body and mind. Physical conditioning, injury prevention, nutrition awareness, and overall health management."),
            ("Resilience", "Strength through adversity. Ability to bounce back from setbacks, handle pressure, and maintain performance under stress."),
            ("Growth Mindset", "Learning through effort, curiosity, and feedback. Openness to instruction, willingness to try new things, and continuous improvement."),
            ("Teamwork", "Unity, trust, and shared purpose. Collaboration with teammates, leadership qualities, and positive team dynamics.")
        ]:
            conn.execute(
                text("INSERT INTO core_values (name, description) VALUES (:n, :d)"),
                {"n": name, "d": desc}
            )

        # Programs
        conn.execute(text("DROP TEMPORARY TABLE IF EXISTS programs"))
        conn.execute(text("""
            CREATE TEMPORARY TABLE programs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL
            ) ENGINE=InnoDB;
        """))
        for prog in [
            "AC RIVER HIGH PERFORMANCE ACADEMY",
            "SA ATHENIANS HIGH PERFORMANCE ACADEMY",
            "AC RIVER YOUTH ACADEMY",
            "SA ATHENIANS YOUTH ACADEMY",
            "MLS GO",
            "SKILLS ACADEMY"
        ]:
            conn.execute(
                text("INSERT INTO programs (name) VALUES (:n)"),
                {"n": prog}
            )
#L&F
BRAND_COLORS = ['#d4bc64', '#84ccb4', '#5c74b4', '#6c6c84', '#504f8f', '#83c3d4', '#646c84', '#646c7c', '#588898', '#586c9c']
def color_html(text: str, color: str, bold: bool = True):
    weight = 'bold' if bold else 'normal'
    return f"<span style='color:{color}; font-weight:{weight}'>{text}</span>"

def show_filters():
    
    login.generarLogin()
    st.title("**Soccer Central Player Performance Evaluation**")
    # Enhanced sidebar with brand styling
    logo = "./assets/images/soccer-central.png"
    st.sidebar.image(logo, width=350)

    # 1) Inicializar tablas temporales
    init_temp_tables()

    # 2) Cargar datos desde MySQL
    with SessionLocal() as session:
        players = (
            session
            .query(Players)
            .join(Players.user)                 
            .options(joinedload(Players.user))
            .filter(Users.role_id == 4)
            .all()
        )
        posiciones = [
            row[0] for row in session
                .query(distinct(Players.primary_position))
                .filter(Players.primary_position.isnot(None))
                .all() if row[0]
        ]
        coaches = session.query(Users).filter(Users.role_id == 2).all()
        core_vals = session.query(CoreValue.id, CoreValue.name).all()
        programs = session.execute(text("SELECT id, name FROM programs")).fetchall()

    if not players:
        st.warning("No se encontraron jugadores en la base de datos.")
        return

    # 3) Selector de jugador (nombre + edad)
    def fmt_player(i):
        p = players[i]
        bd = p.user.birth_date
        age = calc_age(bd) if bd else "N/A"
        return f"{p.user.first_name} {p.user.last_name} ({age} years)"

    idx = st.selectbox(
        "Player Name",
        range(len(players)),
        format_func=fmt_player
    )
    selected = players[idx]
    age = calc_age(selected.user.birth_date)

    # 4) Age group predeterminado
    if age <= 8:
        default_group = "U6-U8"
    elif age <= 10:
        default_group = "U9-U10"
    elif age <= 12:
        default_group = "U11-U12"
    elif age <= 15:
        default_group = "U13-U15"
    else:
        default_group = "U16-U19"
    age_groups = ["U6-U8", "U9-U10", "U11-U12", "U13-U15", "U16-U19"]

    # 5) Mapas para selectboxes
    coach_map   = {f"{c.first_name} {c.last_name}": c.user_id for c in coaches}
    program_map = {row.id: row.name for row in programs}
    prog_inv = {name: pid for pid, name in programs}
    program_opts= [""] + [row.name for row in programs]
    position_opts = [""] + sorted(posiciones)

    #Render de filtros
    st.subheader("Setting Filters", divider= "blue")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.text_input(
            "Player Name",
            value=f"{selected.user.first_name} {selected.user.last_name} ({age} years)",
            disabled=True
        )
        age_group = st.selectbox(
            "Age Group",
            age_groups,
            index=age_groups.index(default_group)
        )
    with col2:
        position = st.selectbox(
            "Position",
            position_opts,
            index=position_opts.index(selected.primary_position)
            if selected.primary_position in position_opts else 0
        )
        evaluation_date = st.date_input("Evaluation Date", value=date.today())
    with col3:
        evaluator = st.selectbox("Coach/Evaluator", list(coach_map.keys()))
        program   = st.selectbox("Program", program_opts)

    # Mostrar selección
    st.markdown("---")
    st.write("**Filtros seleccionados:**")
    st.write(f"- Player Name: {selected.user.first_name} {selected.user.last_name}")
    st.write(f"- Age Group: {age_group}")
    st.write(f"- Position: {position}")
    st.write(f"- Evaluation Date: {evaluation_date}")
    st.write(f"- Coach/Evaluator: {evaluator}")
    st.write(f"- Program: {program}")
     
    # 2) Creamos las 6 pestañas
    tab_labels = [
        "1. Core Values",
        "2. Technical Skills (Ball Mastery)",
        "3. Tactical Understanding (Game Model)",
        "4. Physical Performance (High Performance Model)",
        "5. Match Performance & Consistency",
        "6. Leadership & Character Development"
    ]
    tabs = st.tabs(tab_labels)

    #Pestaña 1: Core Values
    with tabs[0]:
        st.subheader("Core Values")

        core_vals_details = [
            ("DISCIPLINE",
            "Daily excellence through intentional action. Punctuality, preparation, focus during training, and consistent effort in all activities.",
            "Specific observations about discipline and consistency..."),
            ("WELLBEING",
            "Holistic care of body and mind. Physical conditioning, injury prevention, nutrition awareness, and overall health management.",
            "Physical condition, fitness level, health habits..."),
            ("RESILIENCE",
            "Strength through adversity. Ability to bounce back from setbacks, handle pressure, and maintain performance under stress.",
            "Response to challenges,pressure situations, mental toughness."),
            ("GROWTH MINDSET",
            "Learning through effort, curiosity, and feedback. Openness to instruction, willingness to try new things, and continuous improvement.",
            "Receptiveness to feedback, learning attitude, improvement rate..."),
            ("TEAMWORK",
            "Unity, trust, and shared purpose. Collaboration with teammates, leadership qualities, and positive team dynamics.",
            "Team iteraction, communication, leadership, support of teammates..."),
        ]

        ratings_cv  = {}
        comments_cv = {}

        # 1) Generar sliders + text_areas FUERA de cualquier form
        for idx, (label, desc, help_txt) in enumerate(core_vals_details):
            c = BRAND_COLORS[idx % len(BRAND_COLORS)]
            st.markdown(color_html(label, c), unsafe_allow_html=True)
            ratings_cv[label] = st.slider(
                label,
                1, 10, 5,
                help=help_txt,
                key=f"cv_{idx}"
            )
            st.caption(desc)
            comments_cv[label] = st.text_area(
                f"Comments for {label}",
                placeholder="Your observations here...!",
                key=f"comment_{idx}",
                height=80
            )
            st.write("---")

        # 2) Botón de guardado (puedes envolver sólo el add/commit en un with st.form si prefieres)
        if st.button("Save Core Values", key="save_core"):
            """with SessionLocal() as session:
                for label, score in ratings_cv.items():
                    session.add(PlayerAssessments(
                        player_id     = selected.player_id,
                        coach_id      = coach_map[evaluator],
                        category      = "Valores",
                        core_value_id = None,
                        program_id    = prog_inv.get(program),
                        item          = label,
                        value         = score,
                        notes         = comments_cv[label]
                    ))
                session.commit() """
            st.success("¡Core Values saved!")

    #Pestaña 2: Technical Skills
    with tabs[1]:
        st.subheader("Technical Skills (Ball Mastery)")

        tech_items   = ["First touch", "Dribbling", "Passing accuracy", "Shooting technique", "Overall ball control"]
        ratings_tech = {}
        for item in tech_items:
            ratings_tech[item] = st.slider(
                item, 1, 5, 3,
                key=f"tech_{item}"
                
            )
        comments_tech = st.text_area(
            "technical skills comments",
            key="comments_tech",
            height=100
        )

        if st.button("Save Technical", key="save_tech"):
            """"
            with SessionLocal() as session:
                for item, score in ratings_tech.items():
                    session.add(PlayerAssessments(
                        player_id     = selected.player_id,
                        coach_id      = coach_map[evaluator],
                        category      = "Técnico",
                        core_value_id = None,
                        program_id    = prog_inv.get(program),
                        item          = item,
                        value         = score,
                        notes         = comments_tech
                    ))
                session.commit() """
            st.success("Technical Skills saved ✅")

    #Pestaña 3: Tactical Understanding
    with tabs[2]:
        st.subheader("Tactical Understanding (Game Model)")

        tactical_items = [
            "Understanding of MWB", "Understanding of MNB",
            "Understanding of transition principles", "Decision-making in different game moments"
        ]
        ratings_tac = {}
        for item in tactical_items:
            ratings_tac[item] = st.slider(
                item, 1, 5, 3,
                key=f"tac_{item}"
                # opcional: on_change=_rerun para rerun automático
            )
        comments_tac = st.text_area(
            "Tactical Comments",
            key="comments_tac",
            height=100
        )

        if st.button("Save Tactical", key="save_tac"):
            """with SessionLocal() as session:
                for item, score in ratings_tac.items():
                    session.add(PlayerAssessments(
                        player_id     = selected.player_id,
                        coach_id      = coach_map[evaluator],
                        category      = "Táctico",
                        core_value_id = None,
                        program_id    = prog_inv.get(program),
                        item          = item,
                        value         = score,
                        notes         = comments_tac
                    ))
                session.commit()"""
            st.success("Tactical Understanding guardada ✅")

    #Pestaña 4: Physical Performance
    with tabs[3]:
        st.subheader("Physical Performance (High Performance Model)")

        phys_items = ["Speed", "Agility", "Strength", "Endurance", "Movement quality"]
        ratings_phys = {}
        for item in phys_items:
            ratings_phys[item] = st.slider(
                item, 1, 5, 3,
                key=f"phys_{item}"
            )
        comments_phys = st.text_area(
            "Physical Performance Comments",
            key="comments_phys",
            height=100
        )

        if st.button("Save Physical", key="save_phys"):
            """with SessionLocal() as session:
                for item, score in ratings_phys.items():
                    session.add(PlayerAssessments(
                        player_id     = selected.player_id,
                        coach_id      = coach_map[evaluator],
                        category      = "Físico",
                        core_value_id = None,
                        program_id    = prog_inv.get(program),
                        item          = item,
                        value         = score,
                        notes         = comments_phys
                    ))
                session.commit()"""
            st.success("Physical Performance guardada ✅")

    #Pestaña 5: Match Performance & Consistency
    with tabs[4]:
        st.subheader("Match Performance & Consistency")

        match_items = [
            "Ability to transfer training to match situations", 
            "Consistency in performance, Impact on team success"
        ]
        ratings_match = {}
        for item in match_items:
            ratings_match[item] = st.slider(
                item, 1, 5, 3,
                key=f"match_{item}"
            )
        comments_match = st.text_area(
            "Match Performance Comments",
            key="comments_match",
            height=100
        )

        if st.button("Save Match Perf & Cons.", key="save_match"):
            """with SessionLocal() as session:
                for item, score in ratings_match.items():
                    session.add(PlayerAssessments(
                        player_id     = selected.player_id,
                        coach_id      = coach_map[evaluator],
                        category      = "Colectivo",
                        core_value_id = None,
                        program_id    = prog_inv.get(program),
                        item          = item,
                        value         = score,
                        notes         = comments_match
                    ))
                session.commit()"""
            st.success("Match Performance guardada ✅")

    # Pestaña 6: Leadership & Character Development
    with tabs[5]:
        st.subheader("Leadership & Character Development")

        lead_items = [
            "Embodiment of all five core values",
            "Positive influence on others",
            "Character development beyond soccer"
        ]
        ratings_lead = {}
        for item in lead_items:
            ratings_lead[item] = st.slider(
                item, 
                min_value=1, 
                max_value=5, 
                value=3, 
                key=f"lead_{item}",
                # opcional: on_change=_rerun
            )
        comments_lead = st.text_area(
            "Leadership Comments",
            placeholder="Your comments here…!",
            key="comments_lead",
            height=100
        )

        if st.button("Save Leadership & Character", key="save_lead"):
            """with SessionLocal() as session:
                for item, score in ratings_lead.items():
                    session.add(PlayerAssessments(
                        player_id     = selected.player_id,
                        coach_id      = coach_map[evaluator],
                        category      = "Valores",        # o "Mental" según tu esquema
                        core_value_id = None,
                        program_id    = prog_inv.get(program),
                        item          = item,
                        value         = score,
                        notes         = comments_lead
                    ))
                session.commit()"""
            st.success("Leadership & Character guardada ✅")

    #**********Mostrando Resultados***************************************************************
    #Performance Summary ─────────────────────────────────────────
    st.markdown("## Performance Summary")
    c1, c2, c3 = st.columns(3)

    # 1) Extraemos scores de session_state
    overall_scores = [
        v for k, v in st.session_state.items()
        if k.startswith(("cv_","tech_","tac_","phys_","match_","lead_"))
    ]
    core_scores = [
        v for k, v in st.session_state.items()
        if k.startswith("cv_")
    ]
    # PERFORMANCE = Tabs 1–5 → cv_, tech_, tac_, phys_, match_
    perf_scores = [
        v for k, v in st.session_state.items()
        if any(k.startswith(pref) for pref in ("tech_","tac_","phys_","match_","lead_"))
    ]

    # 2) Cálculo de promedios (evita división por cero)
    def avg(lst):
        return sum(lst)/len(lst) if lst else 0

    overall_avg = avg(overall_scores)
    core_avg    = avg(core_scores)
    perf_avg    = avg(perf_scores)

    # 3) Mostramos con st.metric
    c1.metric("Overall Average",      f"{overall_avg:.2f}")
    c2.metric("Core Value Average",   f"{core_avg:.2f}")
    c3.metric("Performance Average",  f"{perf_avg:.2f}")

def main():
    show_filters()

if __name__ == "__main__":
    main()