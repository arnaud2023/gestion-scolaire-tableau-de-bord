from __future__ import annotations

import sqlite3
from datetime import date, datetime, time, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

from planning import has_time_conflict


DB_PATH = Path(__file__).with_name("emploi_du_temps.db")
DAYS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi"]
DAY_INDEX = {day: index for index, day in enumerate(DAYS)}
RESOURCES = {
    "Classes": ("classes", "nom", "Niveau / groupe", "classe"),
    "Enseignants": ("enseignants", "nom", "Matières enseignées", "enseignant"),
    "Salles": ("salles", "nom", "Type / capacité", "salle"),
    "Matières": ("matieres", "nom", "Couleur", "matiere"),
}


def connect() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database() -> None:
    with connect() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS classes (
                id INTEGER PRIMARY KEY, nom TEXT NOT NULL UNIQUE, detail TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS enseignants (
                id INTEGER PRIMARY KEY, nom TEXT NOT NULL UNIQUE, detail TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS salles (
                id INTEGER PRIMARY KEY, nom TEXT NOT NULL UNIQUE, detail TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS matieres (
                id INTEGER PRIMARY KEY, nom TEXT NOT NULL UNIQUE, detail TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS seances (
                id INTEGER PRIMARY KEY,
                jour TEXT NOT NULL,
                heure_debut TEXT NOT NULL,
                heure_fin TEXT NOT NULL,
                classe_id INTEGER NOT NULL REFERENCES classes(id) ON DELETE RESTRICT,
                enseignant_id INTEGER NOT NULL REFERENCES enseignants(id) ON DELETE RESTRICT,
                salle_id INTEGER NOT NULL REFERENCES salles(id) ON DELETE RESTRICT,
                matiere_id INTEGER NOT NULL REFERENCES matieres(id) ON DELETE RESTRICT,
                note TEXT NOT NULL DEFAULT ''
            );
            """
        )
        if db.execute("SELECT COUNT(*) FROM classes").fetchone()[0] == 0:
            db.executemany("INSERT INTO classes (nom, detail) VALUES (?, ?)", [
                ("6e A", "Collège"), ("5e A", "Collège"), ("Seconde C", "Lycée"),
            ])
            db.executemany("INSERT INTO enseignants (nom, detail) VALUES (?, ?)", [
                ("A. Mensah", "Mathématiques"), ("K. Amavi", "Français"), ("S. Tchalla", "Sciences"),
            ])
            db.executemany("INSERT INTO salles (nom, detail) VALUES (?, ?)", [
                ("Salle 01", "Cours"), ("Salle 02", "Cours"), ("Laboratoire", "Sciences"),
            ])
            db.executemany("INSERT INTO matieres (nom, detail) VALUES (?, ?)", [
                ("Mathématiques", "#227c70"), ("Français", "#c66b3d"),
                ("Sciences", "#4779a8"), ("Histoire-Géographie", "#93783d"),
            ])
            db.execute("""
                INSERT INTO seances (jour, heure_debut, heure_fin, classe_id, enseignant_id, salle_id, matiere_id)
                SELECT 'Lundi', '08:00', '09:00', c.id, e.id, s.id, m.id
                FROM classes c, enseignants e, salles s, matieres m
                WHERE c.nom = '6e A' AND e.nom = 'A. Mensah' AND s.nom = 'Salle 01' AND m.nom = 'Mathématiques'
            """)
            db.execute("""
                INSERT INTO seances (jour, heure_debut, heure_fin, classe_id, enseignant_id, salle_id, matiere_id)
                SELECT 'Lundi', '09:00', '10:00', c.id, e.id, s.id, m.id
                FROM classes c, enseignants e, salles s, matieres m
                WHERE c.nom = '6e A' AND e.nom = 'K. Amavi' AND s.nom = 'Salle 02' AND m.nom = 'Français'
            """)
            db.execute("""
                INSERT INTO seances (jour, heure_debut, heure_fin, classe_id, enseignant_id, salle_id, matiere_id)
                SELECT 'Mardi', '10:00', '12:00', c.id, e.id, s.id, m.id
                FROM classes c, enseignants e, salles s, matieres m
                WHERE c.nom = 'Seconde C' AND e.nom = 'S. Tchalla' AND s.nom = 'Laboratoire' AND m.nom = 'Sciences'
            """)


def load_sessions() -> list[dict]:
    with connect() as db:
        rows = db.execute("SELECT * FROM seances").fetchall()
    return [dict(row) for row in rows]


def load_schedule() -> pd.DataFrame:
    with connect() as db:
        return pd.read_sql_query("""
            SELECT s.id, s.jour, s.heure_debut, s.heure_fin,
                   c.nom AS classe, e.nom AS enseignant, sa.nom AS salle,
                   m.nom AS matiere, s.note, c.id AS classe_id,
                   e.id AS enseignant_id, sa.id AS salle_id, m.id AS matiere_id
            FROM seances s
            JOIN classes c ON c.id = s.classe_id
            JOIN enseignants e ON e.id = s.enseignant_id
            JOIN salles sa ON sa.id = s.salle_id
            JOIN matieres m ON m.id = s.matiere_id
        """, db)


def resource_options(table: str) -> list[tuple[int, str]]:
    with connect() as db:
        return [(row["id"], row["nom"]) for row in db.execute(f"SELECT id, nom FROM {table} ORDER BY nom")]


def render_timetable(data: pd.DataFrame) -> None:
    if data.empty:
        st.info("Aucune séance ne correspond à ces filtres.")
        return
    data = data.copy()
    data["jour_ordre"] = data["jour"].map(DAY_INDEX)
    data = data.sort_values(["jour_ordre", "heure_debut"])
    for day in DAYS:
        day_data = data[data["jour"] == day]
        if day_data.empty:
            continue
        st.markdown(f"<div class='day-heading'><span class='badge rounded-pill text-bg-success'>{day}</span></div>", unsafe_allow_html=True)
        for _, session in day_data.iterrows():
            st.markdown(
                f"""<div class='lesson d-flex align-items-center shadow-sm'>
                <div class='lesson-time badge text-bg-light'>{session['heure_debut']}<br><span>{session['heure_fin']}</span></div>
                <div class='lesson-main'><strong>{session['matiere']}</strong>
                <span>{session['classe']} · {session['enseignant']}</span></div>
                <div class='lesson-room badge rounded-pill text-bg-success-subtle'>{session['salle']}</div></div>""",
                unsafe_allow_html=True,
            )


st.set_page_config(page_title="Tempo | Emplois du temps", page_icon="📚", layout="wide")
initialize_database()
st.markdown("""
<style>
@import url('https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css');
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@600;700;800&display=swap');
:root { --ink:#1e302d; --muted:#74817d; --paper:#f5f7f3; --green:#227c70; --line:#e5eae5; }
html, body, [class*="css"] { font-family:'DM Sans',sans-serif; color:var(--ink); }
.stApp { background:var(--paper); }
.block-container { max-width:1320px; padding-top:2rem; padding-bottom:3rem; }
h1,h2,h3 { font-family:'Manrope',sans-serif !important; color:var(--ink); letter-spacing:0 !important; }
h1 { font-size:2rem !important; }
.eyebrow { color:var(--green); text-transform:uppercase; font-size:.75rem; font-weight:700; letter-spacing:1.2px; }
.metric { background:white; border:1px solid var(--line); border-radius:7px; padding:18px 20px; min-height:112px; }
.metric-label { color:var(--muted); font-size:.82rem; }
.metric-value { font-family:'Manrope',sans-serif; font-size:1.85rem; font-weight:800; margin-top:6px; }
.metric-foot { color:var(--muted); font-size:.75rem; margin-top:2px; }
.day-heading { border-bottom:1px solid var(--line); padding:13px 0 8px; margin-top:4px; color:var(--green); font-size:.78rem; font-weight:700; text-transform:uppercase; letter-spacing:1px; }
.lesson { display:flex; align-items:center; gap:16px; background:white; border:1px solid var(--line); border-left:3px solid var(--green); border-radius:5px; padding:12px 14px; margin:8px 0; }
.lesson-time { min-width:54px; font-weight:700; font-size:.83rem; line-height:1.5; }
.lesson-time span { color:var(--muted); font-weight:400; }
.lesson-main { flex:1; display:flex; flex-direction:column; gap:3px; }
.lesson-main strong { font-size:.93rem; }
.lesson-main span,.lesson-room { color:var(--muted); font-size:.78rem; }
div[data-testid="stMetric"] { background:white; border:1px solid var(--line); border-radius:7px; padding:16px; }
div[data-testid="stTabs"] button { font-weight:600; }
@media(max-width:640px) { .block-container { padding:1rem; } .lesson { gap:10px; padding:10px; } .lesson-room { max-width:70px; text-align:right; } }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("<div class='eyebrow'>TEMPO · SCOLAIRE</div>", unsafe_allow_html=True)
    st.title("Emploi du temps")
    page = st.radio("Navigation", ["Tableau de bord", "Séances", "Ressources"], label_visibility="collapsed")
    st.divider()
    st.caption("Gestion locale · Données enregistrées automatiquement")

schedule = load_schedule()
today_name = DAYS[date.today().weekday()] if date.today().weekday() < len(DAYS) else "Lundi"

if page == "Tableau de bord":
    st.markdown("<div class='eyebrow'>Vue d'ensemble</div>", unsafe_allow_html=True)
    st.title("Votre semaine, en un regard")
    st.caption(f"Organisation des cours · {date.today().strftime('%d/%m/%Y')}")
    total_sessions = len(schedule)
    hours = sum((datetime.strptime(end, "%H:%M") - datetime.strptime(start, "%H:%M")).seconds / 3600
                for start, end in zip(schedule["heure_debut"], schedule["heure_fin"])) if total_sessions else 0
    metrics = st.columns(4)
    metric_items = [
        ("Séances planifiées", total_sessions, "sur la semaine"),
        ("Classes", schedule["classe"].nunique() if total_sessions else 0, "avec cours inscrits"),
        ("Enseignants", schedule["enseignant"].nunique() if total_sessions else 0, "mobilisés cette semaine"),
        ("Heures de cours", f"{hours:g} h", "volume hebdomadaire"),
    ]
    accents = ["success", "primary", "warning", "danger"]
    for index, (column, (label, value, foot)) in enumerate(zip(metrics, metric_items)):
        column.markdown(f"<div class='metric card shadow-sm border-top border-4 border-{accents[index]}'><div class='metric-label'>{label}</div><div class='metric-value'>{value}</div><div class='metric-foot'>{foot}</div></div>", unsafe_allow_html=True)

    st.write("")
    st.subheader("Planning hebdomadaire")
    filters = st.columns([1, 1, 1, 1.4])
    class_filter = filters[0].selectbox("Classe", ["Toutes"] + sorted(schedule["classe"].unique().tolist()) if total_sessions else ["Toutes"])
    teacher_filter = filters[1].selectbox("Enseignant", ["Tous"] + sorted(schedule["enseignant"].unique().tolist()) if total_sessions else ["Tous"])
    room_filter = filters[2].selectbox("Salle", ["Toutes"] + sorted(schedule["salle"].unique().tolist()) if total_sessions else ["Toutes"])
    day_filter = filters[3].selectbox("Jour", ["Toute la semaine"] + DAYS)
    filtered = schedule.copy()
    if class_filter != "Toutes":
        filtered = filtered[filtered["classe"] == class_filter]
    if teacher_filter != "Tous":
        filtered = filtered[filtered["enseignant"] == teacher_filter]
    if room_filter != "Toutes":
        filtered = filtered[filtered["salle"] == room_filter]
    if day_filter != "Toute la semaine":
        filtered = filtered[filtered["jour"] == day_filter]
    render_timetable(filtered)
    st.write("")
    csv = filtered[["jour", "heure_debut", "heure_fin", "classe", "matiere", "enseignant", "salle"]].to_csv(index=False).encode("utf-8-sig")
    st.download_button("Télécharger la sélection en CSV", csv, "emploi_du_temps.csv", "text/csv", icon="⬇️")

elif page == "Séances":
    st.markdown("<div class='eyebrow'>Organisation</div>", unsafe_allow_html=True)
    st.title("Gestion des séances")
    options = {name: resource_options(table) for name, (table, *_rest) in RESOURCES.items()}
    missing = [name for name, values in options.items() if not values]
    if missing:
        st.warning("Ajoutez d'abord au moins une ressource dans : " + ", ".join(missing) + ".")
    else:
        with st.form("session_form", clear_on_submit=True):
            st.subheader("Ajouter une séance")
            top = st.columns(4)
            day = top[0].selectbox("Jour", DAYS)
            start_time = top[1].time_input("Début", time(8, 0), step=timedelta(minutes=15))
            end_time = top[2].time_input("Fin", time(9, 0), step=timedelta(minutes=15))
            note = top[3].text_input("Note (facultatif)")
            choices = st.columns(4)
            selected = {}
            for col, key in zip(choices, ["Classes", "Enseignants", "Salles", "Matières"]):
                selected[key] = col.selectbox(key[:-1] if key != "Matières" else "Matière", options[key], format_func=lambda item: item[1], key=f"pick_{key}")
            submitted = st.form_submit_button("Ajouter au planning", type="primary")
        if submitted:
            candidate = {
                "jour": day, "heure_debut": start_time.strftime("%H:%M"), "heure_fin": end_time.strftime("%H:%M"),
                "classe_id": selected["Classes"][0], "enseignant_id": selected["Enseignants"][0],
                "salle_id": selected["Salles"][0],
            }
            conflict = has_time_conflict(candidate, load_sessions())
            if conflict:
                st.error(conflict)
            else:
                with connect() as db:
                    db.execute("INSERT INTO seances (jour, heure_debut, heure_fin, classe_id, enseignant_id, salle_id, matiere_id, note) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                               (day, candidate["heure_debut"], candidate["heure_fin"], candidate["classe_id"], candidate["enseignant_id"], candidate["salle_id"], selected["Matières"][0], note.strip()))
                st.success("Séance ajoutée au planning.")
                st.rerun()

    st.divider()
    st.subheader("Séances enregistrées")
    schedule = load_schedule()
    if schedule.empty:
        st.info("Aucune séance enregistrée pour le moment.")
    else:
        display = schedule[["jour", "heure_debut", "heure_fin", "classe", "matiere", "enseignant", "salle"]].copy()
        st.dataframe(display, use_container_width=True, hide_index=True)
        session_ids = schedule["id"].tolist()
        labels = {row.id: f"{row.jour} · {row.heure_debut} · {row.classe} · {row.matiere}" for row in schedule.itertuples()}
        with st.form("delete_session"):
            delete_id = st.selectbox("Supprimer une séance", session_ids, format_func=lambda item: labels[item])
            delete_confirm = st.checkbox("Je confirme la suppression")
            delete_submitted = st.form_submit_button("Supprimer", type="secondary")
        if delete_submitted:
            if delete_confirm:
                with connect() as db:
                    db.execute("DELETE FROM seances WHERE id = ?", (delete_id,))
                st.success("Séance supprimée.")
                st.rerun()
            else:
                st.warning("Cochez la confirmation avant de supprimer.")

        with st.expander("Modifier une séance"):
            edit_id = st.selectbox("Séance à modifier", session_ids, format_func=lambda item: labels[item], key="edit_session_id")
            current = schedule.loc[schedule["id"] == edit_id].iloc[0]
            with st.form("edit_session_form"):
                edit_cols = st.columns(4)
                edit_day = edit_cols[0].selectbox("Jour", DAYS, index=DAYS.index(current["jour"]), key="edit_day")
                edit_start = edit_cols[1].time_input("Début", time.fromisoformat(current["heure_debut"]), step=timedelta(minutes=15), key="edit_start")
                edit_end = edit_cols[2].time_input("Fin", time.fromisoformat(current["heure_fin"]), step=timedelta(minutes=15), key="edit_end")
                edit_note = edit_cols[3].text_input("Note", value=current["note"], key="edit_note")
                edit_selections = {}
                edit_fields = [("Classes", "classe_id"), ("Enseignants", "enseignant_id"), ("Salles", "salle_id"), ("Matières", "matiere_id")]
                edit_cols = st.columns(4)
                for column, (resource, field) in zip(edit_cols, edit_fields):
                    resource_values = options[resource]
                    current_id = int(current[field])
                    current_index = next(index for index, item in enumerate(resource_values) if item[0] == current_id)
                    edit_selections[field] = column.selectbox(
                        resource[:-1] if resource not in ("Matières",) else "Matière",
                        resource_values,
                        index=current_index,
                        format_func=lambda item: item[1],
                        key=f"edit_{field}",
                    )[0]
                edit_submitted = st.form_submit_button("Enregistrer les modifications", type="primary")
            if edit_submitted:
                candidate = {
                    "jour": edit_day,
                    "heure_debut": edit_start.strftime("%H:%M"),
                    "heure_fin": edit_end.strftime("%H:%M"),
                    "classe_id": edit_selections["classe_id"],
                    "enseignant_id": edit_selections["enseignant_id"],
                    "salle_id": edit_selections["salle_id"],
                }
                conflict = has_time_conflict(candidate, load_sessions(), ignore_id=int(edit_id))
                if conflict:
                    st.error(conflict)
                else:
                    with connect() as db:
                        db.execute(
                            "UPDATE seances SET jour = ?, heure_debut = ?, heure_fin = ?, classe_id = ?, enseignant_id = ?, salle_id = ?, matiere_id = ?, note = ? WHERE id = ?",
                            (candidate["jour"], candidate["heure_debut"], candidate["heure_fin"], candidate["classe_id"], candidate["enseignant_id"], candidate["salle_id"], edit_selections["matiere_id"], edit_note.strip(), edit_id),
                        )
                    st.success("Séance modifiée.")
                    st.rerun()

else:
    st.markdown("<div class='eyebrow'>Établissement</div>", unsafe_allow_html=True)
    st.title("Ressources de l'établissement")
    tabs = st.tabs(list(RESOURCES.keys()))
    for tab, (label, (table, name_field, detail_label, _singular)) in zip(tabs, RESOURCES.items()):
        with tab:
            left, right = st.columns([1, 1.5])
            with left:
                with st.form(f"add_{table}", clear_on_submit=True):
                    st.subheader(f"Ajouter {label.lower()[:-1] if label != 'Matières' else 'une matière'}")
                    new_name = st.text_input("Nom")
                    new_detail = st.text_input(detail_label)
                    add_submitted = st.form_submit_button("Ajouter", type="primary")
                if add_submitted:
                    if not new_name.strip():
                        st.warning("Le nom est obligatoire.")
                    else:
                        try:
                            with connect() as db:
                                db.execute(f"INSERT INTO {table} (nom, detail) VALUES (?, ?)", (new_name.strip(), new_detail.strip()))
                            st.success("Ressource ajoutée.")
                            st.rerun()
                        except sqlite3.IntegrityError:
                            st.error("Ce nom existe déjà.")
            with right:
                st.subheader("Liste")
                with connect() as db:
                    records = pd.read_sql_query(f"SELECT id, nom, detail FROM {table} ORDER BY nom", db)
                if records.empty:
                    st.caption("Aucune ressource enregistrée.")
                else:
                    st.dataframe(records[["nom", "detail"]].rename(columns={"nom": "Nom", "detail": detail_label}), use_container_width=True, hide_index=True)
                    selected_id = st.selectbox("Ressource à supprimer", records["id"].tolist(), format_func=lambda item: records.loc[records.id == item, "nom"].iloc[0], key=f"delete_{table}")
                    if st.button("Supprimer la ressource", key=f"delete_button_{table}"):
                        try:
                            with connect() as db:
                                db.execute(f"DELETE FROM {table} WHERE id = ?", (selected_id,))
                            st.success("Ressource supprimée.")
                            st.rerun()
                        except sqlite3.IntegrityError:
                            st.error("Cette ressource est utilisée dans une séance. Supprimez d'abord la séance concernée.")