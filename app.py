import streamlit as st
import pandas as pd
import plotly.express as px
import re
from pathlib import Path

from config.database import get_connection
from modules.evidence_management import add_evidence
from modules.decision_management import (
    make_decision,
    get_case_decisions,
    get_decision_audit
)
from modules.appeal_management import (
    submit_appeal,
    assign_independent_reviewer,
    get_appeal_history
)


# =====================================================
# 1. PAGE CONFIGURATION
# =====================================================

st.set_page_config(
    page_title="Academic Integrity Management System",
    page_icon="🎓",
    layout="wide"
)


# =====================================================
# 2. APPLICATION TITLE
# =====================================================

st.title("🎓 Academic Integrity Management System")

st.write(
    "A centralized platform to manage student submissions, "
    "similarity reports, investigations, evidence, decisions, "
    "and appeals."
)

st.divider()


# =====================================================
# 3. DASHBOARD DATA
# =====================================================

def get_dashboard_data():

    connection = get_connection()
    cursor = connection.cursor()

    try:

        queries = {
            "learners": "SELECT COUNT(*) FROM learners",
            "submissions": "SELECT COUNT(*) FROM submissions",
            "similarity_reports": "SELECT COUNT(*) FROM similarity_reports",
            "cases": "SELECT COUNT(*) FROM cases",
            "open_cases": """
                SELECT COUNT(*)
                FROM cases
                WHERE case_status <> 'closed'
            """,
            "appeals": "SELECT COUNT(*) FROM appeals"
        }

        results = {}

        for key, query in queries.items():

            cursor.execute(query)
            results[key] = cursor.fetchone()[0]

        return results

    finally:

        cursor.close()
        connection.close()


# =====================================================
# 4. STUDENT SUBMISSIONS
# =====================================================

def get_student_submissions():

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:

        cursor.execute("""
            SELECT
                s.submission_id,
                l.learner_id,
                l.full_name,
                l.department,
                a.assessment_name,
                s.submission_date,
                s.submission_status,
                s.file_reference

            FROM submissions s

            JOIN learners l
                ON s.learner_pk = l.learner_pk

            JOIN assessments a
                ON s.assessment_pk = a.assessment_pk

            ORDER BY s.submission_date DESC
        """)

        return pd.DataFrame(cursor.fetchall())

    finally:

        cursor.close()
        connection.close()


# =====================================================
# 5. SIMILARITY REPORTS
# =====================================================

def get_similarity_reports():

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:

        cursor.execute("""
            SELECT
                sr.similarity_id,
                s.submission_id,
                l.learner_id,
                l.full_name,
                a.assessment_name,
                sr.similarity_score,
                sr.similarity_category,
                sr.report_reference,
                sr.generated_at

            FROM similarity_reports sr

            JOIN submissions s
                ON sr.submission_pk = s.submission_pk

            JOIN learners l
                ON s.learner_pk = l.learner_pk

            JOIN assessments a
                ON s.assessment_pk = a.assessment_pk

            ORDER BY sr.generated_at DESC
        """)

        return pd.DataFrame(cursor.fetchall())

    finally:

        cursor.close()
        connection.close()


# =====================================================
# 6. INVESTIGATION CASES
# =====================================================

def get_investigation_cases():

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:

        cursor.execute("""
            SELECT
                c.case_pk,
                c.case_id,
                c.case_status,
                sr.similarity_id,
                sr.similarity_score,
                sr.similarity_category,
                s.submission_id,
                l.learner_id,
                l.full_name,
                l.department,

                COALESCE(
                    GROUP_CONCAT(
                        DISTINCT CONCAT(
                            r.reviewer_name,
                            ' (',
                            cr.assignment_role,
                            ', ',
                            COALESCE(cr.assignment_status, 'assigned'),
                            ')'
                        )
                        ORDER BY cr.assignment_pk
                        SEPARATOR ', '
                    ),
                    'Not assigned'
                ) AS assigned_reviewers

            FROM cases c

            JOIN similarity_reports sr
                ON c.similarity_pk = sr.similarity_pk

            JOIN submissions s
                ON sr.submission_pk = s.submission_pk

            JOIN learners l
                ON s.learner_pk = l.learner_pk

            LEFT JOIN case_reviewers cr
                ON c.case_pk = cr.case_pk

            LEFT JOIN reviewers r
                ON cr.reviewer_pk = r.reviewer_pk

            GROUP BY
                c.case_pk,
                c.case_id,
                c.case_status,
                sr.similarity_id,
                sr.similarity_score,
                sr.similarity_category,
                s.submission_id,
                l.learner_id,
                l.full_name,
                l.department

            ORDER BY c.case_pk DESC
        """)

        return pd.DataFrame(cursor.fetchall())

    finally:

        cursor.close()
        connection.close()


# =====================================================
# 7. REVIEWER ASSIGNMENTS
# =====================================================

def get_reviewer_assignments():

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:

        cursor.execute("""
            SELECT
                cr.assignment_pk,
                c.case_id,
                r.reviewer_pk,
                r.reviewer_name,
                cr.assignment_role,
                cr.assignment_status,
                cr.assigned_at,
                cr.completed_at

            FROM case_reviewers cr

            JOIN cases c
                ON cr.case_pk = c.case_pk

            JOIN reviewers r
                ON cr.reviewer_pk = r.reviewer_pk

            ORDER BY cr.assigned_at DESC, cr.assignment_pk DESC
        """)

        return pd.DataFrame(cursor.fetchall())

    finally:

        cursor.close()
        connection.close()


# =====================================================
# 8. SIDEBAR NAVIGATION
# =====================================================

st.sidebar.title("Navigation")

page = st.sidebar.radio(
    "Select a section",
    [
        "Dashboard",
        "Student Submissions",
        "Similarity Reports",
        "Investigation Cases",
        "Reviewer Assignments",
        "Evidence Management",
        "Decision Management",
        "Appeals",
        "Audit History",
        "Data Validation"
    ]
)


# =====================================================
# 9. DASHBOARD
# =====================================================

if page == "Dashboard":

    st.title("🎓 Academic Integrity Dashboard")
    st.caption(
        "Institutional overview of submissions, similarity screening, "
        "investigations and academic review activity."
    )

    try:

        data = get_dashboard_data()

        # -------------------------------------------------
        # KEY PERFORMANCE INDICATORS
        # -------------------------------------------------

        st.subheader("System at a glance")

        metric_rows = [
            (
                ("👩‍🎓 Total Learners", data["learners"]),
                ("📄 Submissions", data["submissions"]),
                ("🔎 Similarity Reports", data["similarity_reports"]),
            ),
            (
                ("⚖️ Investigation Cases", data["cases"]),
                ("🕒 Open Cases", data["open_cases"]),
                ("📨 Appeals", data["appeals"]),
            ),
        ]

        for metric_row in metric_rows:
            columns = st.columns(3, gap="medium")
            for column, (label, value) in zip(columns, metric_row):
                with column:
                    with st.container(border=True):
                        st.metric(label, f"{value:,}")

        st.divider()

        # -------------------------------------------------
        # READ-ONLY ANALYTICS FOR DASHBOARD CHARTS
        # -------------------------------------------------

        analytics_connection = get_connection()
        analytics_cursor = analytics_connection.cursor(dictionary=True)

        try:
            analytics_cursor.execute("""
                SELECT
                    similarity_category AS category,
                    COUNT(*) AS total
                FROM similarity_reports
                GROUP BY similarity_category
                ORDER BY total DESC
            """)
            similarity_category_df = pd.DataFrame(analytics_cursor.fetchall())

            analytics_cursor.execute("""
                SELECT
                    case_status AS status,
                    COUNT(*) AS total
                FROM cases
                GROUP BY case_status
                ORDER BY total DESC
            """)
            case_status_df = pd.DataFrame(analytics_cursor.fetchall())

            analytics_cursor.execute("""
                SELECT
                    r.reviewer_name,
                    COUNT(*) AS total_assignments,
                    SUM(
                        CASE
                            WHEN cr.assignment_status IN ('assigned', 'accepted')
                            THEN 1 ELSE 0
                        END
                    ) AS active_assignments
                FROM case_reviewers cr
                JOIN reviewers r
                    ON cr.reviewer_pk = r.reviewer_pk
                GROUP BY r.reviewer_pk, r.reviewer_name
                ORDER BY total_assignments DESC, r.reviewer_name
                LIMIT 10
            """)
            reviewer_workload_df = pd.DataFrame(analytics_cursor.fetchall())

            analytics_cursor.execute("""
                SELECT
                    entity_type,
                    entity_id,
                    action_type,
                    action_timestamp
                FROM audit_logs
                ORDER BY action_timestamp DESC
                LIMIT 8
            """)
            recent_activity_df = pd.DataFrame(analytics_cursor.fetchall())

        finally:
            analytics_cursor.close()
            analytics_connection.close()

        # -------------------------------------------------
        # DATABASE RECORD VOLUME
        # -------------------------------------------------

        st.subheader("Database overview")

        records_df = pd.DataFrame({
            "Record type": [
                "Learners",
                "Submissions",
                "Similarity reports",
                "Investigation cases",
                "Appeals",
            ],
            "Records": [
                data["learners"],
                data["submissions"],
                data["similarity_reports"],
                data["cases"],
                data["appeals"],
            ],
        })

        records_chart = px.bar(
            records_df,
            x="Record type",
            y="Records",
            text="Records",
            color="Record type",
            title="Records across the AIMS platform",
            color_discrete_sequence=["#38BDF8", "#8B5CF6", "#2DD4BF", "#F59E0B", "#F472B6"],
        )
        records_chart.update_traces(textposition="outside", cliponaxis=False)
        records_chart.update_layout(
            template="plotly_dark",
            paper_bgcolor="#0E1117",
            plot_bgcolor="#0E1117",
            font=dict(color="#E6EDF3"),
            showlegend=False,
            height=390,
            margin=dict(l=20, r=20, t=65, b=20),
            xaxis_title=None,
            yaxis_title="Number of records",
        )
        st.plotly_chart(records_chart, use_container_width=True)

        # -------------------------------------------------
        # INVESTIGATION AND SIMILARITY INSIGHTS
        # -------------------------------------------------

        left_chart_col, right_chart_col = st.columns(2, gap="large")

        with left_chart_col:
            st.subheader("Similarity report categories")
            if not similarity_category_df.empty:
                similarity_chart = px.pie(
                    similarity_category_df,
                    names="category",
                    values="total",
                    hole=0.58,
                    color_discrete_sequence=["#38BDF8", "#F59E0B", "#2DD4BF", "#A78BFA", "#F472B6"],
                )
                similarity_chart.update_layout(
                    template="plotly_dark",
                    paper_bgcolor="#0E1117",
                    plot_bgcolor="#0E1117",
                    font=dict(color="#E6EDF3"),
                    height=340,
                    margin=dict(l=10, r=10, t=25, b=10),
                    legend_title_text="Category",
                )
                st.plotly_chart(similarity_chart, use_container_width=True)
            else:
                st.info("No similarity report category data is available.")

        with right_chart_col:
            st.subheader("Investigation case status")
            if not case_status_df.empty:
                case_chart = px.bar(
                    case_status_df,
                    x="total",
                    y="status",
                    orientation="h",
                    text="total",
                    color="status",
                    color_discrete_sequence=["#38BDF8", "#8B5CF6", "#F59E0B", "#2DD4BF", "#F472B6"],
                )
                case_chart.update_traces(textposition="outside", cliponaxis=False)
                case_chart.update_layout(
                    template="plotly_dark",
                    paper_bgcolor="#0E1117",
                    plot_bgcolor="#0E1117",
                    font=dict(color="#E6EDF3"),
                    showlegend=False,
                    height=340,
                    margin=dict(l=10, r=25, t=25, b=10),
                    xaxis_title="Number of cases",
                    yaxis_title=None,
                )
                st.plotly_chart(case_chart, use_container_width=True)
            else:
                st.info("No investigation case status data is available.")

        # -------------------------------------------------
        # REVIEWER WORKLOAD AND AUDIT ACTIVITY
        # -------------------------------------------------

        st.divider()
        workload_col, activity_col = st.columns([1.1, 1], gap="large")

        with workload_col:
            st.subheader("Reviewer workload")
            if not reviewer_workload_df.empty:
                workload_chart = px.bar(
                    reviewer_workload_df.sort_values("total_assignments"),
                    x="total_assignments",
                    y="reviewer_name",
                    orientation="h",
                    text="total_assignments",
                    color_discrete_sequence=["#38BDF8"],
                )
                workload_chart.update_traces(textposition="outside", cliponaxis=False)
                workload_chart.update_layout(
                    template="plotly_dark",
                    paper_bgcolor="#0E1117",
                    plot_bgcolor="#0E1117",
                    font=dict(color="#E6EDF3"),
                    height=390,
                    margin=dict(l=10, r=25, t=20, b=10),
                    xaxis_title="Total assignments",
                    yaxis_title=None,
                )
                st.plotly_chart(workload_chart, use_container_width=True)
                st.caption(
                    "Shows the ten reviewers with the highest total assignment counts. "
                    "Active assignments include assigned and accepted work."
                )
            else:
                st.info("No reviewer assignment data is available.")

        with activity_col:
            st.subheader("Recent audit activity")
            if not recent_activity_df.empty:
                recent_activity_df = recent_activity_df.rename(columns={
                    "entity_type": "Entity",
                    "entity_id": "Record ID",
                    "action_type": "Action",
                    "action_timestamp": "Timestamp",
                })
                st.dataframe(
                    recent_activity_df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Entity": st.column_config.TextColumn("Entity"),
                        "Record ID": st.column_config.TextColumn("Record ID"),
                        "Action": st.column_config.TextColumn("Action"),
                        "Timestamp": st.column_config.DatetimeColumn("Timestamp"),
                    },
                )
            else:
                st.info("No audit activity is available yet.")

        st.info(
            "Similarity scores and flags are indicators for human review; "
            "they do not independently establish academic misconduct. "
            "All academic decisions should be based on reviewed evidence "
            "and documented reasoning."
        )

    except Exception as error:
        st.error(f"Dashboard could not be loaded: {error}")


# =====================================================
# 10. STUDENT SUBMISSIONS
# =====================================================


elif page == "Student Submissions":

    st.header("📄 Student Submissions")

    st.write(
        "View, search and filter student submission records."
    )

    try:

        df = get_student_submissions()

        if not df.empty:

            st.metric(
                "Total Submission Records",
                f"{len(df):,}"
            )

            st.divider()

            search_col, filter_col = st.columns(2)

            with search_col:

                search_value = st.text_input(
                    "Search by Submission ID, Learner ID or Name",
                    key="submission_search"
                )

            with filter_col:

                statuses = (
                    ["All"]
                    + sorted(
                        df["submission_status"]
                        .dropna()
                        .unique()
                        .tolist()
                    )
                )

                selected_status = st.selectbox(
                    "Filter by Submission Status",
                    statuses,
                    key="submission_status_filter"
                )

            filtered_df = df.copy()

            if search_value:

                mask = (
                    filtered_df["submission_id"].astype(str).str.contains(
                        search_value,
                        case=False,
                        na=False
                    )
                    |
                    filtered_df["learner_id"].astype(str).str.contains(
                        search_value,
                        case=False,
                        na=False
                    )
                    |
                    filtered_df["full_name"].astype(str).str.contains(
                        search_value,
                        case=False,
                        na=False
                    )
                )

                filtered_df = filtered_df[mask]

            if selected_status != "All":

                filtered_df = filtered_df[
                    filtered_df["submission_status"] == selected_status
                ]

            st.subheader("Submission Records")

            st.metric(
                "Matching Submissions",
                f"{len(filtered_df):,}"
            )

            if not filtered_df.empty:

                st.dataframe(
                    filtered_df,
                    use_container_width=True,
                    hide_index=True
                )

                st.download_button(
                    "📥 Download Submissions CSV",
                    filtered_df.to_csv(index=False).encode("utf-8"),
                    "student_submissions.csv",
                    "text/csv"
                )

            else:

                st.warning("No matching submissions found.")

        else:

            st.info("No student submissions found.")

    except Exception as error:

        st.error(f"Unable to retrieve submissions: {error}")


# =====================================================
# 11. SIMILARITY REPORTS
# =====================================================

elif page == "Similarity Reports":

    st.header("🔍 Similarity Reports")

    st.write(
        "Review similarity scores and identify submissions "
        "requiring human investigation."
    )

    try:

        df = get_similarity_reports()

        if not df.empty:

            category_counts = df["similarity_category"].value_counts()

            normal_reports = int(category_counts.get("normal", 0))
            review_required = int(
                category_counts.get("review_required", 0)
            )
            high_priority = int(
                category_counts.get("high_priority", 0)
            )

            flagged_reports = review_required + high_priority

            st.subheader("Similarity Report Overview")

            col1, col2, col3 = st.columns(3)

            col1.metric("Total Reports", f"{len(df):,}")
            col2.metric("Total Flagged Reports", f"{flagged_reports:,}")
            col3.metric("High Priority Reports", f"{high_priority:,}")

            col4, col5 = st.columns(2)

            col4.metric("Review Required", f"{review_required:,}")
            col5.metric("Normal Reports", f"{normal_reports:,}")

            st.divider()

            search_col, category_col = st.columns(2)

            with search_col:

                search_value = st.text_input(
                    "Search Report ID, Submission ID or Student Name",
                    key="similarity_search"
                )

            with category_col:

                categories = (
                    ["All"]
                    + sorted(
                        df["similarity_category"]
                        .dropna()
                        .unique()
                        .tolist()
                    )
                )

                selected_category = st.selectbox(
                    "Similarity Category",
                    categories,
                    key="similarity_category_filter"
                )

            score_range = st.slider(
                "Similarity Score Range (%)",
                0.0,
                100.0,
                (0.0, 100.0),
                1.0,
                key="similarity_score_range"
            )

            filtered_df = df.copy()

            if search_value:

                mask = (
                    filtered_df["similarity_id"].astype(str).str.contains(
                        search_value,
                        case=False,
                        na=False
                    )
                    |
                    filtered_df["submission_id"].astype(str).str.contains(
                        search_value,
                        case=False,
                        na=False
                    )
                    |
                    filtered_df["full_name"].astype(str).str.contains(
                        search_value,
                        case=False,
                        na=False
                    )
                )

                filtered_df = filtered_df[mask]

            if selected_category != "All":

                filtered_df = filtered_df[
                    filtered_df["similarity_category"] == selected_category
                ]

            filtered_df = filtered_df[
                filtered_df["similarity_score"].between(
                    score_range[0],
                    score_range[1]
                )
            ]

            st.subheader("Similarity Report Records")

            st.metric(
                "Matching Reports",
                f"{len(filtered_df):,}"
            )

            if not filtered_df.empty:

                st.dataframe(
                    filtered_df,
                    use_container_width=True,
                    hide_index=True
                )

                st.download_button(
                    "📥 Download Similarity Reports CSV",
                    filtered_df.to_csv(index=False).encode("utf-8"),
                    "similarity_reports.csv",
                    "text/csv"
                )

                st.divider()
                st.subheader("Download Individual Similarity Report")

                report_ids = (
                    filtered_df["similarity_id"]
                    .dropna()
                    .astype(str)
                    .tolist()
                )

                selected_report_id = st.selectbox(
                    "Select a Similarity Report",
                    report_ids,
                    key="individual_similarity_report"
                )

                selected_report = filtered_df[
                    filtered_df["similarity_id"].astype(str)
                    == selected_report_id
                ].iloc[0]

                report_reference = selected_report["report_reference"]

                if pd.isna(report_reference) or not str(report_reference).strip():
                    st.warning(
                        "No JSON report reference is available for this record."
                    )
                else:
                    project_root = Path(__file__).resolve().parent
                    report_path = (
                        project_root / str(report_reference).replace("/", "\\")
                    ).resolve()

                    try:
                        report_path.relative_to(project_root.resolve())
                        report_is_inside_project = True
                    except ValueError:
                        report_is_inside_project = False

                    if not report_is_inside_project:
                        st.error(
                            "The report reference points outside the project folder. "
                            "The file will not be opened."
                        )
                    elif not report_path.is_file():
                        st.warning(
                            f"JSON report file was not found: {report_reference}"
                        )
                    else:
                        report_bytes = report_path.read_bytes()

                        st.caption(
                            f"Report file: {report_reference}"
                        )

                        st.download_button(
                            "📥 Download Selected Report JSON",
                            data=report_bytes,
                            file_name=f"{selected_report_id}.json",
                            mime="application/json",
                            key="download_selected_similarity_json"
                        )

            else:

                st.warning("No reports match the selected filters.")

            st.divider()

            st.subheader("Similarity Score Distribution")

            score_chart = px.histogram(
                df,
                x="similarity_score",
                nbins=20,
                title="Distribution of Similarity Scores"
            )

            score_chart.update_layout(
                template="plotly_dark"
            )

            st.plotly_chart(
                score_chart,
                use_container_width=True
            )

            st.subheader("Similarity Category Distribution")

            category_chart = px.pie(
                df,
                names="similarity_category",
                hole=0.35,
                title="Similarity Report Categories"
            )

            category_chart.update_layout(
                template="plotly_dark"
            )

            st.plotly_chart(
                category_chart,
                use_container_width=True
            )

            st.info(
                "Similarity scores are indicators for human review. "
                "A similarity flag alone does not establish misconduct."
            )

        else:

            st.info("No similarity reports found.")

    except Exception as error:

        st.error(f"Unable to retrieve similarity reports: {error}")


# =====================================================
# 12. INVESTIGATION CASES
# =====================================================

elif page == "Investigation Cases":

    st.header("⚖️ Investigation Cases")

    st.write(
        "Monitor investigation cases, assigned reviewers, "
        "similarity indicators and case lifecycle status."
    )

    try:

        df = get_investigation_cases()

        if not df.empty:

            total_cases = len(df)

            closed_cases = int(
                (df["case_status"] == "closed").sum()
            )

            open_cases = total_cases - closed_cases

            st.subheader("Investigation Overview")

            col1, col2, col3 = st.columns(3)

            col1.metric("Total Cases", f"{total_cases:,}")
            col2.metric("Open Cases", f"{open_cases:,}")
            col3.metric("Closed Cases", f"{closed_cases:,}")

            st.divider()

            st.subheader("Case Status Distribution")

            status_counts = (
                df["case_status"]
                .value_counts()
                .reset_index()
            )

            status_counts.columns = [
                "Case Status",
                "Total Cases"
            ]

            status_chart = px.bar(
                status_counts,
                x="Case Status",
                y="Total Cases",
                text="Total Cases",
                title="Investigation Cases by Status"
            )

            status_chart.update_layout(
                template="plotly_dark"
            )

            st.plotly_chart(
                status_chart,
                use_container_width=True
            )

            st.divider()

            st.subheader("Search and Filter Cases")

            search_col, status_col = st.columns(2)

            with search_col:

                search_value = st.text_input(
                    "Search Case ID, Submission ID or Student Name",
                    key="case_search"
                )

            with status_col:

                statuses = (
                    ["All"]
                    + sorted(
                        df["case_status"]
                        .dropna()
                        .unique()
                        .tolist()
                    )
                )

                selected_status = st.selectbox(
                    "Filter by Case Status",
                    statuses,
                    key="case_status_filter"
                )

            filtered_df = df.copy()

            if search_value:

                mask = (
                    filtered_df["case_id"].astype(str).str.contains(
                        search_value,
                        case=False,
                        na=False
                    )
                    |
                    filtered_df["submission_id"].astype(str).str.contains(
                        search_value,
                        case=False,
                        na=False
                    )
                    |
                    filtered_df["learner_id"].astype(str).str.contains(
                        search_value,
                        case=False,
                        na=False
                    )
                    |
                    filtered_df["full_name"].astype(str).str.contains(
                        search_value,
                        case=False,
                        na=False
                    )
                )

                filtered_df = filtered_df[mask]

            if selected_status != "All":

                filtered_df = filtered_df[
                    filtered_df["case_status"] == selected_status
                ]

            st.divider()

            st.subheader("Investigation Case Records")

            st.metric(
                "Matching Cases",
                f"{len(filtered_df):,}"
            )

            display_columns = [
                "case_id",
                "submission_id",
                "learner_id",
                "full_name",
                "department",
                "similarity_score",
                "similarity_category",
                "case_status",
                "assigned_reviewers"
            ]

            if not filtered_df.empty:

                st.dataframe(
                    filtered_df[display_columns],
                    use_container_width=True,
                    hide_index=True
                )

                st.download_button(
                    "📥 Download Investigation Cases CSV",
                    filtered_df[display_columns].to_csv(
                        index=False
                    ).encode("utf-8"),
                    "investigation_cases.csv",
                    "text/csv"
                )

                st.divider()

                st.subheader("View Individual Case")

                selected_case_id = st.selectbox(
                    "Select a Case",
                    filtered_df["case_id"].tolist(),
                    key="individual_case"
                )

                selected_case = filtered_df[
                    filtered_df["case_id"] == selected_case_id
                ].iloc[0]

                detail_col1, detail_col2 = st.columns(2)

                with detail_col1:

                    st.write(
                        "**Case ID:**",
                        selected_case["case_id"]
                    )

                    st.write(
                        "**Student:**",
                        selected_case["full_name"]
                    )

                    st.write(
                        "**Learner ID:**",
                        selected_case["learner_id"]
                    )

                    st.write(
                        "**Department:**",
                        selected_case["department"]
                    )

                with detail_col2:

                    st.write(
                        "**Submission ID:**",
                        selected_case["submission_id"]
                    )

                    st.write(
                        "**Similarity Score:**",
                        f"{selected_case['similarity_score']:.2f}%"
                    )

                    st.write(
                        "**Similarity Category:**",
                        selected_case["similarity_category"]
                    )

                    st.write(
                        "**Case Status:**",
                        selected_case["case_status"]
                    )

                st.write(
                    "**Assigned Reviewers:**",
                    selected_case["assigned_reviewers"]
                )

            else:

                st.warning("No matching investigation cases found.")

        else:

            st.info("No investigation cases found.")

    except Exception as error:

        st.error(f"Unable to retrieve investigation cases: {error}")


# =====================================================
# 13. REVIEWER ASSIGNMENTS
# =====================================================

elif page == "Reviewer Assignments":

    st.header("👥 Reviewer Assignments")

    st.write(
        "Monitor reviewer allocations, assignment roles, "
        "workload and assignment progress."
    )

    try:

        df = get_reviewer_assignments()

        if not df.empty:

            status_counts = df["assignment_status"].value_counts()

            total_assignments = len(df)

            assigned_count = int(status_counts.get("assigned", 0))
            accepted_count = int(status_counts.get("accepted", 0))
            completed_count = int(status_counts.get("completed", 0))
            reassigned_count = int(status_counts.get("reassigned", 0))
            rejected_count = int(status_counts.get("rejected", 0))

            st.subheader("Assignment Overview")

            col1, col2, col3 = st.columns(3)

            col1.metric(
                "Total Assignments",
                f"{total_assignments:,}"
            )

            col2.metric(
                "Assigned",
                f"{assigned_count:,}"
            )

            col3.metric(
                "Completed",
                f"{completed_count:,}"
            )

            col4, col5, col6 = st.columns(3)

            col4.metric(
                "Accepted",
                f"{accepted_count:,}"
            )

            col5.metric(
                "Reassigned",
                f"{reassigned_count:,}"
            )

            col6.metric(
                "Rejected",
                f"{rejected_count:,}"
            )

            st.divider()

            st.subheader("Reviewer Workload")

            workload_df = (
                df.groupby(
                    ["reviewer_pk", "reviewer_name"],
                    as_index=False
                )
                .agg(
                    total_assignments=("assignment_pk", "count"),
                    completed_assignments=(
                        "assignment_status",
                        lambda values: (values == "completed").sum()
                    ),
                    active_assignments=(
                        "assignment_status",
                        lambda values: values.isin(
                            ["assigned", "accepted"]
                        ).sum()
                    )
                )
                .sort_values(
                    "total_assignments",
                    ascending=False
                )
            )

            st.dataframe(
                workload_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "reviewer_pk": "Reviewer ID",
                    "reviewer_name": "Reviewer Name",
                    "total_assignments": "Total Assignments",
                    "completed_assignments": "Completed",
                    "active_assignments": "Active Assignments"
                }
            )

            workload_chart = px.bar(
                workload_df.head(15),
                x="reviewer_name",
                y="total_assignments",
                text="total_assignments",
                title="Top 15 Reviewers by Assignment Count"
            )

            workload_chart.update_layout(
                template="plotly_dark",
                xaxis_title="Reviewer",
                yaxis_title="Total Assignments",
                xaxis_tickangle=-35
            )

            st.plotly_chart(
                workload_chart,
                use_container_width=True
            )

            st.divider()

            st.subheader("Assignment Status Distribution")

            status_chart = px.pie(
                df,
                names="assignment_status",
                title="Reviewer Assignment Status",
                hole=0.35
            )

            status_chart.update_layout(
                template="plotly_dark"
            )

            st.plotly_chart(
                status_chart,
                use_container_width=True
            )

            st.divider()

            st.subheader("Search and Filter Assignments")

            search_col, role_col = st.columns(2)

            with search_col:

                search_value = st.text_input(
                    "Search Reviewer Name, Reviewer ID or Case ID",
                    placeholder="Enter reviewer or case details...",
                    key="reviewer_search"
                )

            with role_col:

                roles = (
                    ["All"]
                    + sorted(
                        df["assignment_role"]
                        .dropna()
                        .unique()
                        .tolist()
                    )
                )

                selected_role = st.selectbox(
                    "Filter by Assignment Role",
                    roles,
                    key="assignment_role_filter"
                )

            statuses = (
                ["All"]
                + sorted(
                    df["assignment_status"]
                    .dropna()
                    .unique()
                    .tolist()
                )
            )

            selected_assignment_status = st.selectbox(
                "Filter by Assignment Status",
                statuses,
                key="assignment_status_filter"
            )

            filtered_df = df.copy()

            if search_value:

                search_mask = (
                    filtered_df["reviewer_name"].astype(str).str.contains(
                        search_value,
                        case=False,
                        na=False
                    )
                    |
                    filtered_df["reviewer_pk"].astype(str).str.contains(
                        search_value,
                        case=False,
                        na=False
                    )
                    |
                    filtered_df["case_id"].astype(str).str.contains(
                        search_value,
                        case=False,
                        na=False
                    )
                )

                filtered_df = filtered_df[search_mask]

            if selected_role != "All":

                filtered_df = filtered_df[
                    filtered_df["assignment_role"] == selected_role
                ]

            if selected_assignment_status != "All":

                filtered_df = filtered_df[
                    filtered_df["assignment_status"]
                    == selected_assignment_status
                ]

            st.divider()

            st.subheader("Reviewer Assignment Records")

            st.metric(
                "Matching Assignments",
                f"{len(filtered_df):,}"
            )

            display_columns = [
                "assignment_pk",
                "case_id",
                "reviewer_pk",
                "reviewer_name",
                "assignment_role",
                "assignment_status",
                "assigned_at",
                "completed_at"
            ]

            if not filtered_df.empty:

                st.dataframe(
                    filtered_df[display_columns],
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "assignment_pk": "Assignment ID",
                        "case_id": "Case ID",
                        "reviewer_pk": "Reviewer ID",
                        "reviewer_name": "Reviewer Name",
                        "assignment_role": "Assignment Role",
                        "assignment_status": "Assignment Status",
                        "assigned_at": "Assigned At",
                        "completed_at": "Completed At"
                    }
                )

                st.download_button(
                    "📥 Download Reviewer Assignments CSV",
                    filtered_df[display_columns].to_csv(
                        index=False
                    ).encode("utf-8"),
                    "reviewer_assignments.csv",
                    "text/csv"
                )

            else:

                st.warning(
                    "No reviewer assignments match your filters."
                )

            st.info(
                "This page is read-only. Assignment changes must "
                "go through the validated reviewer assignment workflow, "
                "including conflict-of-interest checks."
            )

        else:

            st.info("No reviewer assignments found.")

    except Exception as error:

        st.error(
            f"Unable to retrieve reviewer assignments: {error}"
        )


# =====================================================
# 14. EVIDENCE MANAGEMENT
# =====================================================

elif page == "Evidence Management":

    st.header("📁 Evidence Management")

    st.write(
        "Register supporting evidence, review evidence linked to an "
        "investigation case, and inspect the audit trail. Evidence "
        "records are append-only through the validated evidence workflow."
    )

    try:

        # ---------------------------------------------
        # LOAD CASES, REVIEWERS AND EVIDENCE TYPES
        # ---------------------------------------------

        cases_df = get_investigation_cases()

        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        try:

            cursor.execute("""
                SELECT
                    reviewer_id,
                    reviewer_name
                FROM reviewers
                WHERE reviewer_status = 'active'
                ORDER BY reviewer_name
            """)

            reviewers_df = pd.DataFrame(cursor.fetchall())

            cursor.execute("""
                SELECT COLUMN_TYPE
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'evidence_items'
                  AND COLUMN_NAME = 'evidence_type'
            """)

            enum_row = cursor.fetchone()

        finally:

            cursor.close()
            connection.close()

        evidence_types = []

        if enum_row and enum_row.get("COLUMN_TYPE"):

            evidence_types = re.findall(
                r"'((?:[^'\\\\]|\\\\.)*)'",
                enum_row["COLUMN_TYPE"]
            )

        if not evidence_types:

            st.warning(
                "Could not read evidence_type options from MySQL. "
                "Please verify the evidence_items table definition."
            )

        if cases_df.empty:

            st.warning("There are no investigation cases available.")

        elif reviewers_df.empty:

            st.warning("There are no active reviewers available.")

        else:

            case_options = (
                cases_df["case_id"]
                .astype(str)
                .tolist()
            )

            reviewer_options = (
                reviewers_df["reviewer_id"]
                .astype(str)
                .tolist()
            )

            st.subheader("Add Evidence")

            with st.form(
                "add_evidence_form",
                clear_on_submit=True
            ):

                selected_case = st.selectbox(
                    "Investigation Case",
                    case_options,
                    key="evidence_case_select"
                )

                selected_reviewer = st.selectbox(
                    "Uploaded By (Active Reviewer)",
                    reviewer_options,
                    format_func=lambda value: (
                        f"{value} — "
                        + reviewers_df.loc[
                            reviewers_df["reviewer_id"].astype(str) == value,
                            "reviewer_name"
                        ].iloc[0]
                    ),
                    key="evidence_reviewer_select"
                )

                if evidence_types:

                    selected_evidence_type = st.selectbox(
                        "Evidence Type",
                        evidence_types,
                        key="evidence_type_select"
                    )

                else:

                    selected_evidence_type = None

                    st.text_input(
                        "Evidence Type",
                        disabled=True
                    )

                evidence_description = st.text_area(
                    "Evidence Description",
                    placeholder=(
                        "Describe what this evidence contains "
                        "and why it is relevant."
                    ),
                    key="evidence_description"
                )

                evidence_reference = st.text_input(
                    "Evidence Reference",
                    placeholder=(
                        "Example: synthetic/evidence/case_document_001.pdf"
                    ),
                    key="evidence_reference"
                )

                submitted = st.form_submit_button(
                    "Add Evidence",
                    type="primary",
                    disabled=not evidence_types
                )

            # -----------------------------------------
            # PROCESS EVIDENCE SUBMISSION
            # -----------------------------------------

            if submitted:

                if not evidence_description.strip():

                    st.error("Evidence description is required.")

                elif not evidence_reference.strip():

                    st.error("Evidence reference is required.")

                else:

                    try:

                        # Insert evidence through the existing module.
                        # This module performs validation, duplicate checking,
                        # database insertion and audit logging.

                        add_evidence(
                            selected_case,
                            selected_reviewer,
                            selected_evidence_type,
                            evidence_description.strip(),
                            evidence_reference.strip()
                        )

                        # Verify that the evidence record was saved.

                        verify_connection = get_connection()

                        verify_cursor = verify_connection.cursor(
                            dictionary=True
                        )

                        try:

                            verify_cursor.execute("""
                                SELECT
                                    ei.evidence_id,
                                    ei.evidence_type,
                                    ei.evidence_reference,
                                    ei.uploaded_at

                                FROM evidence_items ei

                                JOIN case_evidence ce
                                    ON ei.evidence_pk = ce.evidence_pk

                                JOIN cases c
                                    ON ce.case_pk = c.case_pk

                                WHERE c.case_id = %s
                                  AND ei.evidence_reference = %s

                                ORDER BY ei.evidence_pk DESC

                                LIMIT 1
                            """, (
                                selected_case,
                                evidence_reference.strip()
                            ))

                            saved_record = verify_cursor.fetchone()

                        finally:

                            verify_cursor.close()
                            verify_connection.close()

                        if saved_record:

                            st.success(
                                "Evidence saved successfully!"
                            )

                            st.success(
                                f"Evidence ID: {saved_record['evidence_id']}"
                            )

                            st.info(
                                "The evidence record and audit entry "
                                "have been saved in MySQL."
                            )

                        else:

                            st.warning(
                                "Evidence submission completed, but "
                                "the saved record could not be retrieved. "
                                "Please verify it in MySQL."
                            )

                    except Exception as error:

                        st.error(
                            f"Unable to add evidence: {error}"
                        )

            st.divider()

        # ---------------------------------------------
        # EVIDENCE RECORDS
        # ---------------------------------------------

        st.subheader("Evidence Records")

        evidence_connection = get_connection()

        evidence_cursor = evidence_connection.cursor(
            dictionary=True
        )

        try:

            evidence_cursor.execute("""
                SELECT
                    c.case_id,
                    ei.evidence_id,
                    ei.evidence_type,
                    ei.evidence_description,
                    ei.evidence_reference,
                    ei.content_hash,
                    uploader.reviewer_name AS uploaded_by,
                    ei.uploaded_at,
                    ce.linked_at,
                    linker.reviewer_name AS linked_by

                FROM case_evidence ce

                JOIN cases c
                    ON ce.case_pk = c.case_pk

                JOIN evidence_items ei
                    ON ce.evidence_pk = ei.evidence_pk

                JOIN reviewers uploader
                    ON ei.uploaded_by = uploader.reviewer_pk

                JOIN reviewers linker
                    ON ce.linked_by = linker.reviewer_pk

                ORDER BY ei.uploaded_at DESC, ei.evidence_pk DESC
            """)

            evidence_df = pd.DataFrame(
                evidence_cursor.fetchall()
            )

        finally:

            evidence_cursor.close()
            evidence_connection.close()

        if not evidence_df.empty:

            # -----------------------------------------
            # SEARCH AND FILTER
            # -----------------------------------------

            evidence_search_col, evidence_case_col = st.columns(2)

            with evidence_search_col:

                evidence_search = st.text_input(
                    "Search Evidence ID, Reference or Description",
                    key="evidence_search"
                )

            with evidence_case_col:

                evidence_case_filter = st.selectbox(
                    "Filter by Case",
                    ["All"] + sorted(
                        evidence_df["case_id"]
                        .dropna()
                        .astype(str)
                        .unique()
                        .tolist()
                    ),
                    key="evidence_case_filter"
                )

            filtered_evidence = evidence_df.copy()

            if evidence_search:

                evidence_mask = (
                    filtered_evidence["evidence_id"].astype(str).str.contains(
                        evidence_search,
                        case=False,
                        na=False
                    )
                    |
                    filtered_evidence["evidence_reference"].astype(str).str.contains(
                        evidence_search,
                        case=False,
                        na=False
                    )
                    |
                    filtered_evidence["evidence_description"].astype(str).str.contains(
                        evidence_search,
                        case=False,
                        na=False
                    )
                )

                filtered_evidence = filtered_evidence[evidence_mask]

            if evidence_case_filter != "All":

                filtered_evidence = filtered_evidence[
                    filtered_evidence["case_id"] == evidence_case_filter
                ]

            st.metric(
                "Matching Evidence Records",
                f"{len(filtered_evidence):,}"
            )

            st.dataframe(
                filtered_evidence,
                use_container_width=True,
                hide_index=True
            )

            st.download_button(
                "📥 Download Evidence CSV",
                filtered_evidence.to_csv(
                    index=False
                ).encode("utf-8"),
                "evidence_records.csv",
                "text/csv"
            )

            st.divider()

            # -----------------------------------------
            # EVIDENCE AUDIT HISTORY
            # -----------------------------------------

            st.subheader("Evidence Audit History")

            evidence_ids = (
                filtered_evidence["evidence_id"]
                .dropna()
                .astype(str)
                .tolist()
            )

            if evidence_ids:

                selected_evidence_id = st.selectbox(
                    "Select Evidence ID",
                    evidence_ids,
                    key="evidence_audit_select"
                )

                audit_connection = get_connection()

                audit_cursor = audit_connection.cursor(
                    dictionary=True
                )

                try:

                    audit_cursor.execute("""
                        SELECT
                            al.entity_id AS evidence_id,
                            al.action_type,
                            al.old_values,
                            al.new_values,
                            al.action_reason,
                            al.action_timestamp,
                            r.reviewer_name AS actor

                        FROM audit_logs al

                        LEFT JOIN reviewers r
                            ON al.actor_reviewer_pk = r.reviewer_pk

                        WHERE al.entity_type = 'evidence'
                          AND al.entity_id = %s

                        ORDER BY al.action_timestamp
                    """, (selected_evidence_id,))

                    audit_df = pd.DataFrame(
                        audit_cursor.fetchall()
                    )

                finally:

                    audit_cursor.close()
                    audit_connection.close()

                if not audit_df.empty:

                    st.dataframe(
                        audit_df,
                        use_container_width=True,
                        hide_index=True
                    )

                    st.download_button(
                        "📥 Download Selected Evidence Audit CSV",
                        audit_df.to_csv(
                            index=False
                        ).encode("utf-8"),
                        f"{selected_evidence_id}_audit.csv",
                        "text/csv"
                    )

                else:

                    st.info(
                        "No audit entries were found for this evidence record."
                    )

        else:

            st.info(
                "No evidence records have been registered yet."
            )

        st.info(
            "Evidence is supporting material, not an automatic finding "
            "of misconduct. All evidence additions are recorded "
            "in the audit history."
        )

    except Exception as error:

        st.error(
            f"Evidence Management error: {error}"
        )


# =====================================================
# 15. DECISION MANAGEMENT
# =====================================================

elif page == "Decision Management":

    st.header("⚖️ Decision Management")

    st.write(
        "Record investigation decisions, validate reviewer "
        "assignments, and maintain a transparent decision history."
    )

    try:

        # Select the type of decision to record.
        decision_stage = st.radio(
            "Decision Stage",
            ["initial", "appeal"],
            format_func=lambda value: (
                "Initial Decision" if value == "initial"
                else "Appeal Decision"
            ),
            horizontal=True,
            key="decision_stage"
        )

        # Load only active assignments that are eligible for this stage.
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        try:
            cursor.execute("""
                SELECT
                    c.case_id,
                    c.case_status,
                    r.reviewer_id,
                    r.reviewer_name,
                    cr.assignment_pk,
                    cr.assignment_role,
                    cr.assignment_status
                FROM case_reviewers cr
                JOIN cases c
                    ON cr.case_pk = c.case_pk
                JOIN reviewers r
                    ON cr.reviewer_pk = r.reviewer_pk
                WHERE r.reviewer_status = 'active'
                  AND cr.assignment_status IN ('assigned', 'accepted')
                  AND (
                      (
                          %s = 'initial'
                          AND cr.assignment_role = 'primary'
                          AND c.case_status IN ('open', 'decision_pending')
                      )
                      OR
                      (
                          %s = 'appeal'
                          AND cr.assignment_role = 'independent_appeal'
                          AND c.case_status = 'appeal_pending'
                          AND EXISTS (
                              SELECT 1
                              FROM appeals a
                              WHERE a.case_pk = c.case_pk
                                AND a.independent_assignment_pk = cr.assignment_pk
                                AND a.appeal_status = 'under_review'
                          )
                      )
                  )
                ORDER BY c.case_id
            """, (decision_stage, decision_stage))

            assignments_df = pd.DataFrame(cursor.fetchall())

        finally:
            cursor.close()
            connection.close()

        st.divider()
        st.subheader("Record a Decision")

        if not assignments_df.empty:

            assignment_options = list(range(len(assignments_df)))

            with st.form("decision_form", clear_on_submit=True):

                selected_assignment_index = st.selectbox(
                    "Select Case and Assigned Reviewer",
                    assignment_options,
                    format_func=lambda index: (
                        f"{assignments_df.iloc[index]['case_id']} | "
                        f"{assignments_df.iloc[index]['reviewer_name']} | "
                        f"{assignments_df.iloc[index]['assignment_role']}"
                    )
                )

                selected_assignment = assignments_df.iloc[
                    selected_assignment_index
                ]

                st.caption(
                    f"Case Status: {selected_assignment['case_status']} | "
                    f"Assignment Status: {selected_assignment['assignment_status']}"
                )

                if decision_stage == "initial":
                    decision_outcomes = [
                        "no_violation",
                        "violation",
                        "inconclusive",
                        "more_evidence_required"
                    ]
                else:
                    decision_outcomes = [
                        "no_violation",
                        "violation",
                        "inconclusive",
                        "more_evidence_required",
                        "reversed"
                    ]

                selected_outcome = st.selectbox(
                    "Decision Outcome",
                    decision_outcomes,
                    format_func=lambda value: value.replace("_", " ").title()
                )

                decision_rationale = st.text_area(
                    "Decision Rationale",
                    placeholder=(
                        "Explain the evidence reviewed, the reasoning behind "
                        "the decision, and the justification for the outcome."
                    ),
                    height=150
                )

                submit_decision = st.form_submit_button(
                    "Submit Decision",
                    type="primary"
                )

            if submit_decision:
                if not decision_rationale.strip():
                    st.error("Please provide a decision rationale.")
                else:
                    try:
                        decision_id = make_decision(
                            case_id=selected_assignment["case_id"],
                            reviewer_id=selected_assignment["reviewer_id"],
                            decision_outcome=selected_outcome,
                            decision_rationale=decision_rationale,
                            decision_stage=decision_stage
                        )

                        st.success("Decision recorded successfully!")
                        st.success(f"Decision ID: {decision_id}")
                        st.info(
                            "The reviewer assignment, case status, and audit "
                            "history have been updated."
                        )
                    except Exception as error:
                        st.error(f"Unable to record decision: {error}")

        else:
            st.info(
                "No eligible reviewer assignments are available for the "
                "selected decision stage."
            )

        st.divider()
        st.subheader("Decision History")

        cases_df = get_investigation_cases()

        if not cases_df.empty:
            history_case_options = sorted(
                cases_df["case_id"].dropna().unique().tolist()
            )

            selected_history_case = st.selectbox(
                "Select Case to View Decision History",
                history_case_options,
                key="decision_history_case"
            )

            decisions = get_case_decisions(selected_history_case)

            if decisions:
                decisions_df = pd.DataFrame(
                    decisions,
                    columns=[
                        "Case ID",
                        "Decision ID",
                        "Decision Stage",
                        "Decision Outcome",
                        "Decision Rationale",
                        "Decided At",
                        "Reviewer Name"
                    ]
                )

                st.dataframe(
                    decisions_df,
                    use_container_width=True,
                    hide_index=True
                )

                st.download_button(
                    "📥 Download Decision History CSV",
                    decisions_df.to_csv(index=False).encode("utf-8"),
                    "decision_history.csv",
                    "text/csv"
                )

                st.divider()
                st.subheader("Decision Audit History")

                selected_decision_id = st.selectbox(
                    "Select Decision ID",
                    decisions_df["Decision ID"].tolist(),
                    key="decision_audit_select"
                )

                audit_records = get_decision_audit(selected_decision_id)

                if audit_records:
                    audit_df = pd.DataFrame(
                        audit_records,
                        columns=[
                            "Decision ID",
                            "Action Type",
                            "Old Values",
                            "New Values",
                            "Action Reason",
                            "Action Timestamp",
                            "Actor Reviewer ID"
                        ]
                    )

                    st.dataframe(
                        audit_df,
                        use_container_width=True,
                        hide_index=True
                    )

                    st.download_button(
                        "📥 Download Decision Audit CSV",
                        audit_df.to_csv(index=False).encode("utf-8"),
                        f"{selected_decision_id}_audit.csv",
                        "text/csv"
                    )
                else:
                    st.info("No audit records found for this decision.")
            else:
                st.info("No decisions have been recorded for this case.")
        else:
            st.info("No investigation cases are available.")

        st.divider()
        st.info(
            "A similarity score alone does not establish misconduct. "
            "Decisions must be based on reviewed evidence and a documented "
            "rationale. Appeal decisions require an independent reviewer."
        )

    except Exception as error:
        st.error(f"Decision Management error: {error}")


# =====================================================
# 16. APPEALS
# =====================================================

elif page == "Appeals":

    st.header("⚖️ Appeals Management")

    st.write(
        "Submit appeals against closed initial decisions, assign an "
        "independent academic administrator, and review appeal history."
    )

    st.info(
        "Appeals must be reviewed independently. The reviewer who made "
        "the original decision cannot review its appeal."
    )

    try:

        # -------------------------------------------------
        # LOAD ELIGIBLE DECISIONS FOR APPEAL
        # -------------------------------------------------

        appeal_connection = get_connection()
        appeal_cursor = appeal_connection.cursor(dictionary=True)

        try:

            appeal_cursor.execute("""
                SELECT
                    c.case_id,
                    d.decision_id,
                    d.decision_outcome,
                    d.decided_at,
                    original_reviewer.reviewer_name

                FROM cases c

                JOIN decisions d
                    ON c.case_pk = d.case_pk

                LEFT JOIN case_reviewers original_assignment
                    ON d.assignment_pk = original_assignment.assignment_pk

                LEFT JOIN reviewers original_reviewer
                    ON original_assignment.reviewer_pk = original_reviewer.reviewer_pk

                WHERE c.case_status = 'closed'
                  AND d.decision_stage = 'initial'
                  AND NOT EXISTS (
                      SELECT 1
                      FROM appeals a
                      WHERE a.case_pk = c.case_pk
                        AND a.original_decision_pk = d.decision_pk
                        AND a.appeal_status IN (
                            'submitted',
                            'under_review',
                            'awaiting_information',
                            'accepted',
                            'rejected'
                        )
                  )

                ORDER BY d.decided_at DESC
            """)

            eligible_decisions_df = pd.DataFrame(appeal_cursor.fetchall())

            appeal_cursor.execute("""
                SELECT
                    a.appeal_id,
                    c.case_id,
                    a.appeal_reason,
                    a.appeal_status,
                    a.submitted_at,
                    a.resolved_at,
                    r.reviewer_name AS independent_reviewer

                FROM appeals a

                JOIN cases c
                    ON a.case_pk = c.case_pk

                LEFT JOIN case_reviewers cr
                    ON a.independent_assignment_pk = cr.assignment_pk

                LEFT JOIN reviewers r
                    ON cr.reviewer_pk = r.reviewer_pk

                ORDER BY a.submitted_at DESC
            """)

            appeals_df = pd.DataFrame(appeal_cursor.fetchall())

            appeal_cursor.execute("""
                SELECT
                    reviewer_id,
                    reviewer_name
                FROM reviewers
                WHERE reviewer_status = 'active'
                  AND reviewer_role = 'academic_admin'
                ORDER BY reviewer_name
            """)

            independent_reviewers_df = pd.DataFrame(appeal_cursor.fetchall())

        finally:

            appeal_cursor.close()
            appeal_connection.close()

        # -------------------------------------------------
        # SUBMIT AN APPEAL
        # -------------------------------------------------

        st.subheader("Submit an Appeal")

        if not eligible_decisions_df.empty:

            appeal_options = list(range(len(eligible_decisions_df)))

            with st.form("submit_appeal_form", clear_on_submit=True):

                selected_appeal_index = st.selectbox(
                    "Select Closed Case and Original Decision",
                    appeal_options,
                    format_func=lambda index: (
                        f"{eligible_decisions_df.iloc[index]['case_id']} | "
                        f"{eligible_decisions_df.iloc[index]['decision_id']} | "
                        f"{eligible_decisions_df.iloc[index]['decision_outcome']}"
                    )
                )

                selected_appeal_decision = eligible_decisions_df.iloc[
                    selected_appeal_index
                ]

                st.caption(
                    f"Original reviewer: "
                    f"{selected_appeal_decision['reviewer_name'] or 'Not available'} | "
                    f"Decision date: {selected_appeal_decision['decided_at']}"
                )

                appeal_reason = st.text_area(
                    "Reason for Appeal",
                    placeholder=(
                        "Explain why the original decision should be reviewed. "
                        "Include relevant facts or procedural concerns."
                    ),
                    height=130
                )

                submit_appeal_button = st.form_submit_button(
                    "Submit Appeal",
                    type="primary"
                )

            if submit_appeal_button:

                if not appeal_reason.strip():

                    st.error("Please provide a reason for the appeal.")

                else:

                    try:

                        new_appeal_id = submit_appeal(
                            case_id=selected_appeal_decision["case_id"],
                            original_decision_id=selected_appeal_decision["decision_id"],
                            appeal_reason=appeal_reason.strip()
                        )

                        st.success("Appeal submitted successfully.")
                        st.success(f"Appeal ID: {new_appeal_id}")
                        st.info(
                            "The case has been moved to appeal_pending. "
                            "Refresh the page to see the updated appeal."
                        )

                        st.rerun()

                    except Exception as error:

                        st.error(f"Unable to submit appeal: {error}")

        else:

            st.info(
                "There are no eligible closed initial decisions available "
                "for a new appeal."
            )

        st.divider()

        # -------------------------------------------------
        # ASSIGN AN INDEPENDENT REVIEWER
        # -------------------------------------------------

        st.subheader("Assign an Independent Reviewer")

        if not appeals_df.empty:

            assignable_appeals_df = appeals_df[
                appeals_df["appeal_status"] == "submitted"
            ].copy()

        else:

            assignable_appeals_df = pd.DataFrame()

        if not assignable_appeals_df.empty:

            if not independent_reviewers_df.empty:

                appeal_assignment_options = list(range(len(assignable_appeals_df)))

                with st.form("assign_independent_reviewer_form"):

                    selected_assignment_index = st.selectbox(
                        "Select Submitted Appeal",
                        appeal_assignment_options,
                        format_func=lambda index: (
                            f"{assignable_appeals_df.iloc[index]['appeal_id']} | "
                            f"{assignable_appeals_df.iloc[index]['case_id']}"
                        )
                    )

                    selected_assignment_appeal = assignable_appeals_df.iloc[
                        selected_assignment_index
                    ]

                    reviewer_options = independent_reviewers_df[
                        "reviewer_id"
                    ].astype(str).tolist()

                    selected_independent_reviewer = st.selectbox(
                        "Select Active Academic Administrator",
                        reviewer_options,
                        format_func=lambda value: (
                            f"{value} — "
                            + independent_reviewers_df.loc[
                                independent_reviewers_df["reviewer_id"].astype(str) == value,
                                "reviewer_name"
                            ].iloc[0]
                        )
                    )

                    assign_reviewer_button = st.form_submit_button(
                        "Assign Independent Reviewer",
                        type="primary"
                    )

                if assign_reviewer_button:

                    try:

                        assignment_pk = assign_independent_reviewer(
                            appeal_id=selected_assignment_appeal["appeal_id"],
                            reviewer_id=selected_independent_reviewer
                        )

                        st.success("Independent reviewer assigned successfully.")
                        st.success(f"Assignment ID: {assignment_pk}")
                        st.info(
                            "The appeal status is now under_review. "
                            "The independent reviewer can record the appeal decision "
                            "from the Decision Management page."
                        )

                    except Exception as error:

                        st.error(f"Unable to assign independent reviewer: {error}")

            else:

                st.warning(
                    "No active academic administrators are available "
                    "for independent appeal review."
                )

        else:

            st.info("There are no submitted appeals awaiting reviewer assignment.")

        st.divider()

        # -------------------------------------------------
        # APPEAL RECORDS
        # -------------------------------------------------

        st.subheader("Appeal Records")

        if not appeals_df.empty:

            st.metric("Total Appeals", f"{len(appeals_df):,}")

            st.dataframe(
                appeals_df,
                use_container_width=True,
                hide_index=True
            )

            st.download_button(
                "📥 Download Appeals CSV",
                appeals_df.to_csv(index=False).encode("utf-8"),
                "appeal_records.csv",
                "text/csv"
            )

            st.divider()

            # -------------------------------------------------
            # CASE APPEAL HISTORY
            # -------------------------------------------------

            st.subheader("Appeal History by Case")

            case_options = sorted(
                appeals_df["case_id"].dropna().astype(str).unique().tolist()
            )

            selected_history_case = st.selectbox(
                "Select Case to View Appeal History",
                case_options,
                key="appeal_history_case"
            )

            appeal_history = get_appeal_history(selected_history_case)

            if appeal_history:

                appeal_history_df = pd.DataFrame(
                    appeal_history,
                    columns=[
                        "Appeal ID",
                        "Case ID",
                        "Appeal Reason",
                        "Appeal Status",
                        "Submitted At",
                        "Resolved At",
                        "Independent Reviewer",
                        "Appeal Decision PK"
                    ]
                )

                st.dataframe(
                    appeal_history_df,
                    use_container_width=True,
                    hide_index=True
                )

                st.download_button(
                    "📥 Download Selected Case Appeal History CSV",
                    appeal_history_df.to_csv(index=False).encode("utf-8"),
                    f"{selected_history_case}_appeal_history.csv",
                    "text/csv"
                )

            else:

                st.info("No appeal history was found for this case.")

            st.divider()

            # -------------------------------------------------
            # APPEAL AUDIT HISTORY
            # -------------------------------------------------

            st.subheader("Appeal Audit History")

            selected_audit_appeal = st.selectbox(
                "Select Appeal ID",
                appeals_df["appeal_id"].astype(str).tolist(),
                key="appeal_audit_select"
            )

            audit_connection = get_connection()
            audit_cursor = audit_connection.cursor(dictionary=True)

            try:

                audit_cursor.execute("""
                    SELECT
                        al.entity_id AS appeal_id,
                        al.action_type,
                        al.old_values,
                        al.new_values,
                        al.action_reason,
                        al.action_timestamp,
                        r.reviewer_name AS actor

                    FROM audit_logs al

                    LEFT JOIN reviewers r
                        ON al.actor_reviewer_pk = r.reviewer_pk

                    WHERE al.entity_type = 'appeal'
                      AND al.entity_id = %s

                    ORDER BY al.action_timestamp
                """, (selected_audit_appeal,))

                appeal_audit_df = pd.DataFrame(audit_cursor.fetchall())

            finally:

                audit_cursor.close()
                audit_connection.close()

            if not appeal_audit_df.empty:

                st.dataframe(
                    appeal_audit_df,
                    use_container_width=True,
                    hide_index=True
                )

                st.download_button(
                    "📥 Download Appeal Audit CSV",
                    appeal_audit_df.to_csv(index=False).encode("utf-8"),
                    f"{selected_audit_appeal}_audit.csv",
                    "text/csv"
                )

            else:

                st.info("No audit entries were found for this appeal.")

        else:

            st.info("No appeals have been submitted yet.")

        st.divider()

        st.info(
            "An appeal is a separate review process, not an automatic reversal. "
            "The independent reviewer must assess the appeal evidence and "
            "document a reasoned outcome."
        )

    except Exception as error:

        st.error(f"Appeals Management error: {error}")


# =====================================================
# 17. AUDIT HISTORY
# =====================================================

elif page == "Audit History":

    st.header("📜 Audit History")
    st.write(
        "Inspect recorded actions across evidence, decisions, appeals and "
        "reviewer assignments. Audit records are displayed read-only."
    )

    try:
        audit_connection = get_connection()
        audit_cursor = audit_connection.cursor(dictionary=True)

        try:
            audit_cursor.execute("""
                SELECT
                    al.audit_pk,
                    al.entity_type,
                    al.entity_id,
                    al.action_type,
                    al.old_values,
                    al.new_values,
                    al.action_reason,
                    al.action_timestamp,
                    al.actor_reviewer_pk,
                    r.reviewer_id,
                    r.reviewer_name
                FROM audit_logs al
                LEFT JOIN reviewers r
                    ON al.actor_reviewer_pk = r.reviewer_pk
                ORDER BY al.action_timestamp DESC, al.audit_pk DESC
            """)
            all_audits_df = pd.DataFrame(audit_cursor.fetchall())

        finally:
            audit_cursor.close()
            audit_connection.close()

        if all_audits_df.empty:
            st.info("No audit records have been recorded yet.")

        else:
            st.subheader("Audit Overview")
            metric1, metric2, metric3 = st.columns(3)
            metric1.metric("Total Audit Events", f"{len(all_audits_df):,}")
            metric2.metric(
                "Entity Types", f"{all_audits_df['entity_type'].nunique():,}"
            )
            metric3.metric(
                "Action Types", f"{all_audits_df['action_type'].nunique():,}"
            )

            st.divider()
            st.subheader("Search and Filter Audit Events")
            search_col, entity_col, action_col = st.columns(3)

            with search_col:
                audit_search = st.text_input(
                    "Search ID, reviewer or reason",
                    placeholder="Case, decision, appeal or evidence ID...",
                    key="global_audit_search"
                )

            with entity_col:
                entity_types = ["All"] + sorted(
                    all_audits_df["entity_type"].dropna().astype(str).unique().tolist()
                )
                audit_entity_filter = st.selectbox(
                    "Entity Type", entity_types, key="global_audit_entity"
                )

            with action_col:
                action_types = ["All"] + sorted(
                    all_audits_df["action_type"].dropna().astype(str).unique().tolist()
                )
                audit_action_filter = st.selectbox(
                    "Action Type", action_types, key="global_audit_action"
                )

            dated_events = pd.to_datetime(
                all_audits_df["action_timestamp"], errors="coerce"
            )
            valid_dates = dated_events.dropna()
            filtered_audits_df = all_audits_df.copy()

            if not valid_dates.empty:
                min_date = valid_dates.min().date()
                max_date = valid_dates.max().date()
                selected_dates = st.date_input(
                    "Action Date Range",
                    value=(min_date, max_date),
                    min_value=min_date,
                    max_value=max_date,
                    key="global_audit_dates"
                )
                if isinstance(selected_dates, (tuple, list)) and len(selected_dates) == 2:
                    start_date, end_date = selected_dates
                    event_dates = pd.to_datetime(
                        filtered_audits_df["action_timestamp"], errors="coerce"
                    ).dt.date
                    filtered_audits_df = filtered_audits_df[
                        event_dates.between(start_date, end_date)
                    ]

            if audit_entity_filter != "All":
                filtered_audits_df = filtered_audits_df[
                    filtered_audits_df["entity_type"] == audit_entity_filter
                ]

            if audit_action_filter != "All":
                filtered_audits_df = filtered_audits_df[
                    filtered_audits_df["action_type"] == audit_action_filter
                ]

            if audit_search.strip():
                searchable_columns = [
                    "entity_id", "entity_type", "action_type",
                    "action_reason", "reviewer_id", "reviewer_name",
                    "new_values", "old_values"
                ]
                matching = pd.Series(False, index=filtered_audits_df.index)
                for column in searchable_columns:
                    matching = matching | filtered_audits_df[column].astype(str).str.contains(
                        audit_search.strip(), case=False, na=False, regex=False
                    )
                filtered_audits_df = filtered_audits_df[matching]

            st.divider()
            st.subheader("Audit Event Records")
            st.metric("Matching Audit Events", f"{len(filtered_audits_df):,}")

            if not filtered_audits_df.empty:
                display_columns = [
                    "audit_pk", "action_timestamp", "entity_type", "entity_id",
                    "action_type", "reviewer_id", "reviewer_name", "action_reason"
                ]
                st.dataframe(
                    filtered_audits_df[display_columns],
                    use_container_width=True,
                    hide_index=True
                )

                st.download_button(
                    "📥 Download Filtered Audit CSV",
                    data=filtered_audits_df.to_csv(index=False).encode("utf-8"),
                    file_name="audit_history_filtered.csv",
                    mime="text/csv",
                    key="global_audit_csv"
                )

                st.divider()
                st.subheader("Inspect an Audit Event")
                selected_audit_pk = st.selectbox(
                    "Select Audit Event",
                    filtered_audits_df["audit_pk"].tolist(),
                    format_func=lambda pk: (
                        f"#{pk} | "
                        f"{filtered_audits_df.loc[filtered_audits_df['audit_pk'] == pk, 'entity_type'].iloc[0]} | "
                        f"{filtered_audits_df.loc[filtered_audits_df['audit_pk'] == pk, 'entity_id'].iloc[0]}"
                    ),
                    key="global_audit_detail_select"
                )
                selected_event = filtered_audits_df.loc[
                    filtered_audits_df["audit_pk"] == selected_audit_pk
                ].iloc[0]

                st.write("**Entity:**", selected_event["entity_type"])
                st.write("**Entity ID:**", selected_event["entity_id"])
                st.write("**Action:**", selected_event["action_type"])
                st.write("**Timestamp:**", selected_event["action_timestamp"])
                st.write(
                    "**Reviewer:**",
                    selected_event["reviewer_name"]
                    if pd.notna(selected_event["reviewer_name"])
                    else "Not recorded"
                )
                st.write("**Reason:**", selected_event["action_reason"])

                import json

                for label, column in [
                    ("Previous Values", "old_values"),
                    ("New Values", "new_values")
                ]:
                    with st.expander(label, expanded=(column == "new_values")):
                        raw_value = selected_event[column]
                        if raw_value is None or (isinstance(raw_value, float) and pd.isna(raw_value)):
                            st.info("No values recorded.")
                        else:
                            try:
                                parsed = json.loads(raw_value) if isinstance(raw_value, str) else raw_value
                                st.json(parsed)
                            except (ValueError, TypeError):
                                st.code(str(raw_value))
            else:
                st.info("No audit records match the selected filters.")

            st.info(
                "Audit entries document system activity; they do not by themselves "
                "establish academic misconduct."
            )

    except Exception as error:
        st.error(f"Audit History error: {error}")


# =====================================================
# 18. DATA VALIDATION
# =====================================================

elif page == "Data Validation":

    st.header("✅ Data Validation")
    st.write(
        "Run read-only database integrity, data-quality and academic-integrity "
        "workflow checks. No records are modified by these checks."
    )

    if st.button("▶ Run Validation Checks", type="primary", key="run_data_validation"):
        connection = None
        cursor = None
        results = []
        table_counts = []
        foreign_key_rows = []

        def record_check(category, name, query, params=None):
            try:
                cursor.execute(query, params or ())
                row = cursor.fetchone()
                count = int(row[0] or 0) if row else 0
                results.append({
                    "Category": category,
                    "Validation Check": name,
                    "Issue Count": count,
                    "Status": "PASS" if count == 0 else "FAIL"
                })
            except Exception as exc:
                results.append({
                    "Category": category,
                    "Validation Check": name,
                    "Issue Count": None,
                    "Status": f"ERROR: {exc}"
                })

        try:
            connection = get_connection()
            cursor = connection.cursor()

            # Discover the actual schema rather than assuming a hard-coded table list.
            cursor.execute("SELECT DATABASE()")
            schema_name = cursor.fetchone()[0]
            cursor.execute("""
                SELECT TABLE_NAME
                FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = %s AND TABLE_TYPE = 'BASE TABLE'
                ORDER BY TABLE_NAME
            """, (schema_name,))
            tables = [row[0] for row in cursor.fetchall()]

            # Table counts and primary-key uniqueness/null checks.
            for table in tables:
                safe_table = table.replace('`', '``')
                cursor.execute(f"SELECT COUNT(*) FROM `{safe_table}`")
                table_counts.append({"Table": table, "Row Count": int(cursor.fetchone()[0])})

                cursor.execute("""
                    SELECT COLUMN_NAME
                    FROM information_schema.KEY_COLUMN_USAGE
                    WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                      AND CONSTRAINT_NAME = 'PRIMARY'
                    ORDER BY ORDINAL_POSITION
                """, (schema_name, table))
                pk_columns = [row[0] for row in cursor.fetchall()]
                if pk_columns:
                    pk_expr = ", ".join(f"`{c.replace('`', '``')}`" for c in pk_columns)
                    null_condition = " OR ".join(
                        f"`{c.replace('`', '``')}` IS NULL" for c in pk_columns
                    )
                    record_check(
                        "Primary Key Integrity",
                        f"NULL primary-key values: {table}",
                        f"SELECT COUNT(*) FROM `{safe_table}` WHERE {null_condition}"
                    )
                    record_check(
                        "Primary Key Integrity",
                        f"Duplicate primary-key combinations: {table}",
                        f"SELECT COUNT(*) FROM (SELECT {pk_expr} FROM `{safe_table}` "
                        f"GROUP BY {pk_expr} HAVING COUNT(*) > 1) duplicate_rows"
                    )

            # Check every declared foreign key for orphan references.
            cursor.execute("""
                SELECT TABLE_NAME, COLUMN_NAME, REFERENCED_TABLE_NAME,
                       REFERENCED_COLUMN_NAME, CONSTRAINT_NAME
                FROM information_schema.KEY_COLUMN_USAGE
                WHERE TABLE_SCHEMA = %s AND REFERENCED_TABLE_NAME IS NOT NULL
                ORDER BY TABLE_NAME, CONSTRAINT_NAME, ORDINAL_POSITION
            """, (schema_name,))
            fk_rows = cursor.fetchall()
            for child_table, child_col, parent_table, parent_col, constraint_name in fk_rows:
                foreign_key_rows.append({
                    "Table": child_table,
                    "Column": child_col,
                    "References Table": parent_table,
                    "References Column": parent_col,
                    "Constraint": constraint_name
                })
                ct = child_table.replace('`', '``')
                cc = child_col.replace('`', '``')
                pt = parent_table.replace('`', '``')
                pc = parent_col.replace('`', '``')
                record_check(
                    "Foreign Key Integrity",
                    f"Orphan references: {child_table}.{child_col} → {parent_table}.{parent_col}",
                    f"SELECT COUNT(*) FROM `{ct}` child "
                    f"LEFT JOIN `{pt}` parent ON child.`{cc}` = parent.`{pc}` "
                    f"WHERE child.`{cc}` IS NOT NULL AND parent.`{pc}` IS NULL"
                )

            # Domain-specific checks use known columns in this application schema.
            domain_checks = [
                ("Similarity Quality", "Similarity scores outside 0–100", """
                    SELECT COUNT(*) FROM similarity_reports
                    WHERE similarity_score < 0 OR similarity_score > 100
                       OR similarity_score IS NULL
                """),
                ("Similarity Quality", "Invalid similarity categories", """
                    SELECT COUNT(*) FROM similarity_reports
                    WHERE similarity_category IS NULL
                       OR similarity_category NOT IN ('normal', 'review_required', 'high_priority')
                """),
                ("Decision Quality", "Decisions without rationale", """
                    SELECT COUNT(*) FROM decisions
                    WHERE decision_rationale IS NULL OR TRIM(decision_rationale) = ''
                """),
                ("Evidence Quality", "Evidence without description or reference", """
                    SELECT COUNT(*) FROM evidence_items
                    WHERE evidence_description IS NULL OR TRIM(evidence_description) = ''
                       OR evidence_reference IS NULL OR TRIM(evidence_reference) = ''
                """),
                ("Appeal Quality", "Appeal resolution before submission", """
                    SELECT COUNT(*) FROM appeals
                    WHERE resolved_at IS NOT NULL AND resolved_at < submitted_at
                """),
                ("Assignment Quality", "Completed assignments without completion timestamp", """
                    SELECT COUNT(*) FROM case_reviewers
                    WHERE assignment_status = 'completed' AND completed_at IS NULL
                """),
                ("Due Process", "Violation decisions without completed assignment", """
                    SELECT COUNT(*) FROM decisions d
                    LEFT JOIN case_reviewers cr ON d.assignment_pk = cr.assignment_pk
                    WHERE d.decision_outcome = 'violation'
                      AND (cr.assignment_pk IS NULL OR cr.assignment_status <> 'completed')
                """),
                ("Due Process", "Resolved appeals without completed independent review", """
                    SELECT COUNT(*) FROM appeals a
                    LEFT JOIN decisions d ON a.appeal_decision_pk = d.decision_pk
                    LEFT JOIN case_reviewers cr ON a.independent_assignment_pk = cr.assignment_pk
                    WHERE a.appeal_status IN ('accepted', 'rejected')
                      AND (a.independent_assignment_pk IS NULL
                        OR a.appeal_decision_pk IS NULL
                        OR d.decision_stage <> 'appeal'
                        OR d.assignment_pk <> a.independent_assignment_pk
                        OR cr.assignment_role <> 'independent_appeal'
                        OR cr.assignment_status <> 'completed')
                """),
                ("Audit Completeness", "Evidence without INSERT audit event", """
                    SELECT COUNT(*)
                    FROM evidence_items ei
                    JOIN case_evidence ce ON ei.evidence_pk = ce.evidence_pk
                    JOIN cases c ON ce.case_pk = c.case_pk
                    JOIN decisions d ON d.case_pk = c.case_pk
                    WHERE ei.uploaded_at > d.decided_at
                      AND NOT EXISTS (
                        SELECT 1 FROM audit_logs al
                        WHERE al.entity_type = 'evidence'
                          AND al.entity_id = ei.evidence_id
                          AND al.action_type = 'INSERT'
                      )
                """)
            ]
            for category, name, query in domain_checks:
                record_check(category, name, query)

            # Conflict-of-interest check at the date of the recorded decision.
            record_check(
                "Due Process",
                "Decisions made by reviewers with an active learner conflict",
                """
                SELECT COUNT(*)
                FROM decisions d
                JOIN cases c ON d.case_pk = c.case_pk
                JOIN similarity_reports sr ON c.similarity_pk = sr.similarity_pk
                JOIN submissions s ON sr.submission_pk = s.submission_pk
                JOIN case_reviewers cr ON d.assignment_pk = cr.assignment_pk
                JOIN reviewer_conflicts rc
                  ON rc.reviewer_pk = cr.reviewer_pk
                 AND rc.learner_pk = s.learner_pk
                 AND rc.effective_from <= DATE(d.decided_at)
                 AND (rc.effective_to IS NULL OR rc.effective_to >= DATE(d.decided_at))
                """
            )

            st.session_state["validation_results"] = pd.DataFrame(results)
            st.session_state["validation_table_counts"] = pd.DataFrame(table_counts)
            st.session_state["validation_foreign_keys"] = pd.DataFrame(foreign_key_rows)
            st.session_state["validation_run_complete"] = True

        except Exception as exc:
            st.error(f"Unable to complete validation: {exc}")
        finally:
            if cursor is not None:
                cursor.close()
            if connection is not None:
                connection.close()

    if st.session_state.get("validation_run_complete", False):
        results_df = st.session_state["validation_results"]
        pass_count = int((results_df["Status"] == "PASS").sum())
        fail_count = int((results_df["Status"] == "FAIL").sum())
        error_count = int(results_df["Status"].astype(str).str.startswith("ERROR:").sum())

        st.divider()
        st.subheader("Validation Summary")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Checks", len(results_df))
        m2.metric("Passed", pass_count)
        m3.metric("Failed", fail_count)
        m4.metric("Execution Errors", error_count)

        if fail_count == 0 and error_count == 0:
            st.success("All executed validation checks passed.")
        else:
            st.warning("Review failed checks and execution errors below.")

        st.subheader("Detailed Validation Results")
        categories = ["All"] + sorted(results_df["Category"].unique().tolist())
        selected_category = st.selectbox(
            "Filter by category", categories, key="validation_category_filter"
        )
        shown_df = results_df if selected_category == "All" else results_df[
            results_df["Category"] == selected_category
        ]
        st.dataframe(shown_df, use_container_width=True, hide_index=True)
        st.download_button(
            "📥 Download Validation Results CSV",
            results_df.to_csv(index=False).encode("utf-8"),
            "data_validation_results.csv",
            "text/csv",
            key="validation_results_download"
        )

        st.divider()
        st.subheader("Database Table Counts")
        counts_df = st.session_state["validation_table_counts"]
        st.dataframe(counts_df, use_container_width=True, hide_index=True)
        st.download_button(
            "📥 Download Table Counts CSV",
            counts_df.to_csv(index=False).encode("utf-8"),
            "database_table_counts.csv",
            "text/csv",
            key="validation_counts_download"
        )

        st.divider()
        st.subheader("Foreign Key Constraint Inventory")
        fk_df = st.session_state["validation_foreign_keys"]
        st.metric("Foreign Key Constraints", len(fk_df))
        if not fk_df.empty:
            st.dataframe(fk_df, use_container_width=True, hide_index=True)
            st.download_button(
                "📥 Download Foreign Key Inventory CSV",
                fk_df.to_csv(index=False).encode("utf-8"),
                "foreign_key_inventory.csv",
                "text/csv",
                key="validation_fk_download"
            )
        else:
            st.warning("No foreign key constraints were found in the current database.")

        st.info(
            "A similarity flag is not proof of misconduct. These checks validate "
            "data integrity and workflow controls; academic decisions require "
            "human review and documented reasoning."
        )
    else:
        st.info("Click **Run Validation Checks** to execute read-only checks against MySQL.")


# =====================================================
# 19. FOOTER
# =====================================================

st.sidebar.divider()

st.sidebar.caption(
    "Academic Integrity Management System"
)

st.sidebar.caption(
    "Powered by Python, Streamlit and MySQL"
)