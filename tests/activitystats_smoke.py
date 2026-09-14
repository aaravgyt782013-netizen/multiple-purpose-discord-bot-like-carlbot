from database import connect, init_db


def main():
    init_db()
    guild_id = 999999999999991
    user_id = 999999999999992
    with connect() as db:
        db.execute("DELETE FROM activity_stats WHERE guild_id=?", (guild_id,))
        db.execute("DELETE FROM activity_buckets WHERE guild_id=?", (guild_id,))
        db.execute("INSERT INTO activity_stats(guild_id,user_id,message_count,voice_seconds) VALUES(?,?,?,?)", (guild_id, user_id, 7, 125))
        db.execute("INSERT INTO activity_buckets(guild_id,user_id,bucket_start,message_count,voice_seconds) VALUES(?,?,?,?,?)", (guild_id, user_id, "2099-01-01 00:00:00", 7, 125))
        stats = db.execute("SELECT message_count,voice_seconds FROM activity_stats WHERE guild_id=? AND user_id=?", (guild_id, user_id)).fetchone()
        bucket = db.execute("SELECT message_count,voice_seconds FROM activity_buckets WHERE guild_id=? AND user_id=?", (guild_id, user_id)).fetchone()
        assert (stats["message_count"], stats["voice_seconds"]) == (7, 125)
        assert (bucket["message_count"], bucket["voice_seconds"]) == (7, 125)
        db.execute("DELETE FROM activity_stats WHERE guild_id=?", (guild_id,))
        db.execute("DELETE FROM activity_buckets WHERE guild_id=?", (guild_id,))
    print("Activity statistics persistence smoke test passed")


if __name__ == "__main__":
    main()
