import os
from datetime import time

import requests
import streamlit as st

try:
    API_URL = st.secrets["API_URL"]
except (KeyError, FileNotFoundError, st.errors.StreamlitSecretNotFoundError):
    API_URL = os.environ.get("API_URL", "http://localhost:8000")


def fmt(t_str: str) -> str:
    # "14:30:00" -> "02:30 PM"
    return time.fromisoformat(t_str).strftime("%I:%M %p")


st.set_page_config(page_title="Energy-Aware Planner", page_icon="🔋")
st.title("🔋 Energy-Aware Daily Planner")
st.caption("Schedules your tasks into the times of day you actually have the energy for them.")

st.header("1. Fixed Commitments")
st.caption("Class, gym, commute — anything locked in that can't move.")

with st.form("commitment_form", clear_on_submit=True):
    col1, col2, col3 = st.columns([2, 1, 1])
    name = col1.text_input("Name")
    start = col2.time_input("Start")
    end = col3.time_input("End")
    if st.form_submit_button("Add Commitment"):
        resp = requests.post(
            f"{API_URL}/commitments",
            json={"name": name, "start": str(start), "end": str(end)},
            timeout=10,
        )
        if resp.status_code != 200:
            st.error(resp.json().get("detail", "Something went wrong"))
        else:
            st.rerun()

try:
    commitments = requests.get(f"{API_URL}/commitments", timeout=10).json()
except requests.exceptions.RequestException:
    st.error("Can't reach the backend right now. If it's been idle a while, give it a minute and refresh.")
    st.stop()

if commitments:
    st.table(
        [
            {"Name": c["name"], "Start": fmt(c["start"]), "End": fmt(c["end"])}
            for c in commitments
        ]
    )
    to_delete = st.selectbox(
        "Delete a commitment",
        options=commitments,
        format_func=lambda c: f"{c['name']} ({fmt(c['start'])}\u2013{fmt(c['end'])})",
        key="del_commitment",
    )
    if st.button("Delete Commitment"):
        requests.delete(f"{API_URL}/commitments/{to_delete['id']}", timeout=10)
        st.rerun()

st.divider()

st.header("2. Flexible Tasks")
st.caption("Things you need to get done today, tagged by how much energy they take.")

with st.form("task_form", clear_on_submit=True):
    col1, col2, col3 = st.columns([2, 1, 1])
    task_name = col1.text_input("Task name")
    duration = col2.number_input("Minutes", min_value=1, value=30)
    energy_cost = col3.selectbox("Energy cost", ["Low", "Medium", "High"])
    if st.form_submit_button("Add Task"):
        resp = requests.post(
            f"{API_URL}/tasks",
            json={"name": task_name, "duration_minutes": duration, "energy_cost": energy_cost},
            timeout=10,
        )
        if resp.status_code != 200:
            st.error(resp.json().get("detail", "Something went wrong"))
        else:
            st.rerun()

try:
    tasks = requests.get(f"{API_URL}/tasks", timeout=10).json()
except requests.exceptions.RequestException:
    st.error("Can't reach the backend right now. If it's been idle a while, give it a minute and refresh.")
    st.stop()

if tasks:
    st.table(
        [
            {
                "Name": t["name"],
                "Duration (min)": int(t["duration_minutes"]),
                "Energy Cost": t["energy_cost"],
            }
            for t in tasks
        ]
    )
    to_delete_task = st.selectbox(
        "Delete a task",
        options=tasks,
        format_func=lambda t: f"{t['name']} ({int(t['duration_minutes'])} min, {t['energy_cost']})",
        key="del_task",
    )
    if st.button("Delete Task"):
        requests.delete(f"{API_URL}/tasks/{to_delete_task['id']}", timeout=10)
        st.rerun()

st.divider()

st.header("3. Your Energy Curve")
st.caption("When are you actually sharp vs. drained? Map out your day.")

with st.form("energy_form", clear_on_submit=True):
    col1, col2, col3 = st.columns([1, 1, 1])
    e_start = col1.time_input("Start", key="e_start")
    e_end = col2.time_input("End", key="e_end")
    level = col3.selectbox("Energy level", ["Low", "Medium", "High"], key="e_level")
    if st.form_submit_button("Add Energy Window"):
        resp = requests.post(
            f"{API_URL}/energy-windows",
            json={"start": str(e_start), "end": str(e_end), "level": level},
            timeout=10,
        )
        if resp.status_code != 200:
            st.error(resp.json().get("detail", "Something went wrong"))
        else:
            st.rerun()

try:
    energy_windows = requests.get(f"{API_URL}/energy-windows", timeout=10).json()
except requests.exceptions.RequestException:
    st.error("Can't reach the backend right now. If it's been idle a while, give it a minute and refresh.")
    st.stop()

if energy_windows:
    st.table(
        [
            {"Start": fmt(w["start"]), "End": fmt(w["end"]), "Level": w["level"]}
            for w in energy_windows
        ]
    )
    to_delete_window = st.selectbox(
        "Delete an energy window",
        options=energy_windows,
        format_func=lambda w: f"{w['level']} ({fmt(w['start'])}\u2013{fmt(w['end'])})",
        key="del_window",
    )
    if st.button("Delete Energy Window"):
        requests.delete(f"{API_URL}/energy-windows/{to_delete_window['id']}")
        st.rerun()

st.divider()

st.header("4. Your Schedule")

if st.button("Generate Schedule", type="primary"):
    try:
        result = requests.post(f"{API_URL}/schedule", timeout=10).json()
    except requests.exceptions.RequestException:
        st.error("Can't reach the backend right now. If it's been idle a while, give it a minute and try again.")
        st.stop()

    if result["scheduled"]:
        st.subheader("Scheduled")
        st.table(
            [
                {
                    "Task": s["name"],
                    "Start": fmt(s["start"]),
                    "End": fmt(s["end"]),
                    "Energy Level": s["level"],
                }
                for s in result["scheduled"]
            ]
        )
    else:
        st.write("Nothing scheduled yet — add some tasks and energy windows above.")

    if result["uncovered_windows"]:
        st.warning("Parts of your free time aren't covered by any energy window:")
        for gap_start, gap_end in result["uncovered_windows"]:
            st.markdown(f"- {fmt(gap_start)} to {fmt(gap_end)}")

    if result["unscheduled"]:
        st.warning("These tasks couldn't fit anywhere today:")
        for task_name in result["unscheduled"]:
            st.markdown(f"- {task_name}")
