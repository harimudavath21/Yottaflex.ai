from config.database import get_connection

def validate_foreign_keys():

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT
                TABLE_NAME,
                COLUMN_NAME,
                REFERENCED_TABLE_NAME,
                REFERENCED_COLUMN_NAME
            FROM information_schema.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = 'yottaflex'
              AND REFERENCED_TABLE_NAME IS NOT NULL
            ORDER BY TABLE_NAME, COLUMN_NAME
        """)

        foreign_keys = cursor.fetchall()

        print("\nFOREIGN KEY VALIDATION")
        print("=" * 50)

        if foreign_keys:
            print("Foreign-key constraints found:", len(foreign_keys))

            for fk in foreign_keys:
                print(
                    f"{fk[0]}.{fk[1]} -> "
                    f"{fk[2]}.{fk[3]}"
                )
        else:
            print("No foreign-key constraints found.")

        print("\nForeign-key validation completed.")

    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    validate_foreign_keys()
