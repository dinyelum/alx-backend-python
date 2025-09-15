import asyncio
import aiosqlite


async def async_fetch_users():
    """Fetch all users from the database"""
    async with aiosqlite.connect('users.db') as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT * FROM users') as cursor:
            users = await cursor.fetchall()
            return [dict(user) for user in users]


async def async_fetch_older_users():
    """Fetch users older than 40 from the database"""
    async with aiosqlite.connect('users.db') as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT * FROM users WHERE age > 40') as cursor:
            users = await cursor.fetchall()
            return [dict(user) for user in users]


async def fetch_concurrently():
    """Execute both queries concurrently using asyncio.gather"""
    return await asyncio.gather(
        async_fetch_users(),
        async_fetch_older_users()
    )

# Run the concurrent fetch
if __name__ == "__main__":
    # Note: You'll need to create the database and table first
    results = asyncio.run(fetch_concurrently())
    all_users, older_users = results

    print(f"All users: {len(all_users)}")
    print(f"Users older than 40: {len(older_users)}")
