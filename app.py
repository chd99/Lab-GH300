from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_FILE = DATA_DIR / "exercise_log.csv"
DEFAULT_USER = "default"
DEFAULT_COLUMNS = [
    "user",
    "date",
    "sport",
    "duration_minutes",
    "calories",
    "intensity",
    "notes",
]


def ensure_data_file() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not DATA_FILE.exists():
        empty_df = pd.DataFrame(columns=DEFAULT_COLUMNS)
        empty_df.to_csv(DATA_FILE, index=False)


@st.cache_data
def load_records() -> pd.DataFrame:
    ensure_data_file()
    df = pd.read_csv(DATA_FILE, parse_dates=["date"])
    if df.empty:
        return pd.DataFrame(columns=DEFAULT_COLUMNS)

    if "user" not in df.columns:
        df["user"] = DEFAULT_USER
    df = df[DEFAULT_COLUMNS].copy()
    df["user"] = df["user"].fillna(DEFAULT_USER)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["duration_minutes"] = pd.to_numeric(df["duration_minutes"], errors="coerce").fillna(0).astype(int)
    df["calories"] = pd.to_numeric(df["calories"], errors="coerce").fillna(0).astype(int)
    df["sport"] = df["sport"].fillna("Other")
    df["intensity"] = df["intensity"].fillna("Moderate")
    df["notes"] = df["notes"].fillna("")
    return df


def save_records(df: pd.DataFrame) -> None:
    ensure_data_file()
    record_df = df.copy()
    if record_df.empty:
        record_df = pd.DataFrame(columns=DEFAULT_COLUMNS)
    else:
        record_df["user"] = record_df["user"].fillna(DEFAULT_USER)
        record_df["date"] = pd.to_datetime(record_df["date"], errors="coerce")
        record_df["duration_minutes"] = pd.to_numeric(record_df["duration_minutes"], errors="coerce").fillna(0).astype(int)
        record_df["calories"] = pd.to_numeric(record_df["calories"], errors="coerce").fillna(0).astype(int)
        record_df["sport"] = record_df["sport"].fillna("Other")
        record_df["intensity"] = record_df["intensity"].fillna("Moderate")
        record_df["notes"] = record_df["notes"].fillna("")
    record_df = record_df[DEFAULT_COLUMNS]
    record_df.to_csv(DATA_FILE, index=False)
    load_records.clear()


def get_dashboard_summary(df: pd.DataFrame) -> dict:
    if df.empty:
        return {
            "sessions": 0,
            "total_minutes": 0,
            "avg_minutes": 0,
            "total_calories": 0,
        }

    total_minutes = int(df["duration_minutes"].sum())
    total_calories = int(df["calories"].sum())
    avg_minutes = round(float(df["duration_minutes"].mean()), 1)
    return {
        "sessions": int(len(df)),
        "total_minutes": total_minutes,
        "avg_minutes": avg_minutes,
        "total_calories": total_calories,
    }


def main() -> None:
    st.set_page_config(page_title="Exercise Tracker Dashboard", layout="wide")
    st.title("Daily Sport Exercise Dashboard")
    st.caption("Track your workouts, time spent, calories burned, and fitness progress over time.")

    records = load_records()

    with st.sidebar:
        st.header("User")
        existing_users = sorted(records["user"].unique()) or [DEFAULT_USER]
        selected_user = st.selectbox("Select user", existing_users)
        new_user = st.text_input("Or add a new user").strip()
        active_user = new_user or selected_user
        st.caption(f"Active user: {active_user}")

        st.header("Add a workout")
        with st.form("exercise_form", clear_on_submit=True):
            workout_date = st.date_input("Date", value=pd.Timestamp.today().date())
            workout_type = st.selectbox(
                "Sport",
                ["Running", "Cycling", "Swimming", "Gym", "Yoga", "Hiking", "Basketball", "Other"],
            )
            duration = st.number_input("Duration (minutes)", min_value=5, max_value=600, value=30, step=5)
            calories = st.number_input("Calories burned", min_value=0, max_value=4000, value=250, step=10)
            intensity = st.select_slider("Intensity", options=["Light", "Moderate", "High"], value="Moderate")
            notes = st.text_area("Notes", placeholder="How did it feel?", height=100)

            if st.form_submit_button("Save workout"):
                new_record = pd.DataFrame(
                    [{
                        "user": active_user,
                        "date": workout_date,
                        "sport": workout_type,
                        "duration_minutes": int(duration),
                        "calories": int(calories),
                        "intensity": intensity,
                        "notes": notes,
                    }]
                )
                updated_records = pd.concat([records, new_record], ignore_index=True)
                save_records(updated_records)
                st.success("Workout saved successfully.")
                st.rerun()

    records = records[records["user"] == active_user]

    if records.empty:
        st.info("No exercise data yet. Add your first workout from the sidebar to get started.")
        return

    min_date = records["date"].min().date()
    max_date = records["date"].max().date()
    start_date, end_date = st.columns(2)
    with start_date:
        selected_start = st.date_input("Start date", value=min_date, min_value=min_date, max_value=max_date)
    with end_date:
        selected_end = st.date_input("End date", value=max_date, min_value=min_date, max_value=max_date)

    filtered = records[
        (records["date"] >= pd.Timestamp(selected_start)) & (records["date"] <= pd.Timestamp(selected_end))
    ].copy()

    summary = get_dashboard_summary(filtered)
    total_sessions, total_minutes, avg_minutes, total_calories = (
        summary["sessions"],
        summary["total_minutes"],
        summary["avg_minutes"],
        summary["total_calories"],
    )

    stats_columns = st.columns(4)
    stats_columns[0].metric("Workouts", total_sessions)
    stats_columns[1].metric("Minutes", total_minutes)
    stats_columns[2].metric("Avg. duration", f"{avg_minutes} min")
    stats_columns[3].metric("Calories", total_calories)

    daily_minutes = (
        filtered.groupby("date", as_index=False)["duration_minutes"].sum().sort_values("date").rename(columns={"duration_minutes": "minutes"})
    )
    daily_minutes["date"] = pd.to_datetime(daily_minutes["date"]).dt.strftime("%Y-%m-%d")

    chart_columns = st.columns(2)
    with chart_columns[0]:
        st.subheader("Workout minutes by day")
        if not daily_minutes.empty:
            st.line_chart(daily_minutes.set_index("date")["minutes"])
        else:
            st.info("No data for the selected period.")

    with chart_columns[1]:
        st.subheader("Workout type totals")
        sport_totals = filtered.groupby("sport")["duration_minutes"].sum().sort_values(ascending=False)
        if not sport_totals.empty:
            st.bar_chart(sport_totals)
        else:
            st.info("No activity types for the selected period.")

    st.subheader("Recent workouts")
    table_data = filtered.sort_values("date", ascending=False).reset_index(drop=True)
    table_data["date"] = table_data["date"].dt.strftime("%Y-%m-%d")
    st.dataframe(table_data, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
