
import json
import sys
from pathlib import Path

# ==========================================
# PROJECT CONFIGURATION
# ==========================================

# Get the project root directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Add project root to Python import path
sys.path.insert(0, str(PROJECT_ROOT))

from config.database import get_connection


TOTAL_EXPECTED_REPORTS = 10000

# Output directory for JSON reports
REPORTS_DIR = PROJECT_ROOT / "synthetic" / "reports"


# ==========================================
# GENERATE JSON REPORT FILES
# ==========================================

def generate_report_files():

    connection = None
    cursor = None

    try:

        # Connect to MySQL
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        # Create output directory
        REPORTS_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

        print("\n===================================")
        print("SIMILARITY REPORT FILE GENERATOR")
        print("===================================")

        print("\nReading similarity reports from MySQL...")

        # Fetch existing database records
        cursor.execute("""
            SELECT
                sr.similarity_id,
                sr.similarity_score,
                sr.similarity_category,
                sr.generated_at,

                sub.submission_id,
                sub.file_reference,
                sub.submission_date,
                sub.submission_status,

                l.learner_id,
                l.full_name,
                l.department,

                ir.rule_id,
                ir.rule_name,
                ir.review_threshold,
                ir.high_priority_threshold

            FROM similarity_reports sr

            INNER JOIN submissions sub
                ON sr.submission_pk = sub.submission_pk

            INNER JOIN learners l
                ON sub.learner_pk = l.learner_pk

            INNER JOIN integrity_rules ir
                ON sr.rule_pk = ir.rule_pk

            ORDER BY sr.similarity_pk
        """)

        reports = cursor.fetchall()

        total_reports = len(reports)

        print("Reports found:", total_reports)

        # Verify expected record count
        if total_reports != TOTAL_EXPECTED_REPORTS:

            raise ValueError(
                f"Expected {TOTAL_EXPECTED_REPORTS} reports, "
                f"but found {total_reports}."
            )

        generated_count = 0

        # ==========================================
        # GENERATE INDIVIDUAL JSON FILES
        # ==========================================

        for report in reports:

            similarity_id = report["similarity_id"]

            report_data = {

                "report_id": similarity_id,

                "submission": {

                    "submission_id": report["submission_id"],

                    "file_reference": report["file_reference"],

                    "submission_date": str(
                        report["submission_date"]
                    ),

                    "submission_status": report[
                        "submission_status"
                    ]
                },

                "learner": {

                    "learner_id": report["learner_id"],

                    "full_name": report["full_name"],

                    "department": report["department"]
                },

                "similarity_analysis": {

                    "similarity_score": float(
                        report["similarity_score"]
                    ),

                    "similarity_category": report[
                        "similarity_category"
                    ],

                    "analysis_type": "synthetic_score",

                    "matching_passages": [],

                    "comparison_details": None,

                    "evidence_available": False
                },

                "integrity_rule": {

                    "rule_id": report["rule_id"],

                    "rule_name": report["rule_name"],

                    "review_threshold": float(
                        report["review_threshold"]
                    ),

                    "high_priority_threshold": float(
                        report["high_priority_threshold"]
                    )
                },

                "generated_at": str(
                    report["generated_at"]
                ),

                "report_metadata": {

                    "data_source": "synthetic_dataset",

                    "report_status": "synthetic_record",

                    "note": (
                        "This report contains a synthetically "
                        "generated similarity score. Actual text "
                        "comparison and matching passages are "
                        "not available. The score is not proof "
                        "of academic misconduct."
                    )
                }
            }

            # Generate JSON filename
            filename = f"{similarity_id}.json"

            file_path = REPORTS_DIR / filename

            # Write JSON file
            with open(
                file_path,
                "w",
                encoding="utf-8"
            ) as json_file:

                json.dump(
                    report_data,
                    json_file,
                    indent=4,
                    ensure_ascii=False
                )

            generated_count += 1

            # Display progress
            if generated_count % 1000 == 0:

                print(
                    f"Generated {generated_count} "
                    f"of {total_reports} reports..."
                )

        # ==========================================
        # FINAL VERIFICATION
        # ==========================================

        json_files = list(
            REPORTS_DIR.glob("*.json")
        )

        print("\n===================================")
        print("REPORT GENERATION COMPLETED")
        print("===================================")

        print(
            "Total database records:",
            total_reports
        )

        print(
            "Newly generated reports:",
            generated_count
        )

        print(
            "JSON files present:",
            len(json_files)
        )

        print(
            "Output directory:",
            REPORTS_DIR
        )

        if len(json_files) != TOTAL_EXPECTED_REPORTS:

            print(
                "WARNING: JSON file count does not "
                "match the expected count."
            )

        else:

            print(
                "SUCCESS: All 10,000 JSON report files "
                "are present."
            )

    except Exception as error:

        print("\nREPORT GENERATION FAILED")
        print("Error:", error)

        raise

    finally:

        if cursor is not None:
            cursor.close()

        if connection is not None:
            connection.close()


# ==========================================
# MAIN
# ==========================================

if __name__ == "__main__":

    generate_report_files()
