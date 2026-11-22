import asyncio

from sqlalchemy import text

from database.session import engine


async def main():

    try:

        async with engine.connect() as connection:

            result = await connection.execute(
                text("""
                    SELECT
                        current_database(),
                        current_user,
                        version()
                """)
            )

            database, user, version = result.one()

            print("\n==============================")

            print("NR SHOP DATABASE CONNECTED!")

            print("==============================")

            print(f"Database: {database}")

            print(f"User: {user}")

            print(f"PostgreSQL: {version}")

            print("==============================\n")

    except Exception as error:

        print("DATABASE CONNECTION FAILED")

        print(error)

    finally:

        await engine.dispose()


if __name__ == "__main__":

    asyncio.run(main())