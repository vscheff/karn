from dataclasses import dataclass
from dateparser import parse
from datetime import datetime, timezone
from discord import TextChannel, Thread
from discord.ext.commands import Cog, errors, hybrid_command
from discord.ext.tasks import loop
from zoneinfo import ZoneInfo

from src.utils import get_cursor


DEFAULT_TZ = "America/Detroit"
DEFAULT_REMIND_LIMIT = 50
DEFAULT_LIST_LIMIT = 10

@dataclass
class Reminder:
    id: int
    guild_id: int
    channel_id: int
    author_id: int
    remind_at_utc: datetime
    message: str

class Reminders(Cog):
    def __init__(self, bot, conn):
        self.bot = bot
        self.conn = conn

        cursor = get_cursor(self.conn)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Reminders (
                id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                guild_id BIGINT UNSIGNED NOT NULL,
                channel_id BIGINT UNSIGNED NOT NULL,
                author_id BIGINT UNSIGNED NOT NULL,
                remind_at_utc DATETIME(6) NOT NULL,
                message TEXT NOT NULL,
                created_at_utc TEXT NOT NULL,
                PRIMARY KEY (id),
                INDEX idx_remind_at (remind_at_utc)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;""")
        self.conn.commit()
        cursor.close()

        self.dispatch_due.start()

    # PLACEHOLDER
    def get_guild_tz(self, guild):
        return DEFAULT_TZ

    def parse_when(self, when_text, tz_name):
        tz = ZoneInfo(tz_name)
        now_local = datetime.now(tz)

        dt = parse(
                when_text,
                settings={"RELATIVE_BASE": now_local, "PREFER_DATES_FROM": "future", "RETURN_AS_TIMEZONE_AWARE": True, "TIMEZONE": tz_name})

        if dt is None:
            return None

        return dt.astimezone(timezone.utc)

    def insert_reminder(self, guild_id, channel_id, author_id, remind_at_utc, message):
        cursor = get_cursor(self.conn)
        cursor.execute("INSERT INTO Reminders"
                       "(guild_id, channel_id, author_id, remind_at_utc, message, created_at_utc)"
                       "VALUES (%s, %s, %s, %s, %s, %s)",
                       (guild_id, channel_id, author_id, remind_at_utc, message, datetime.now(timezone.utc)))
        self.conn.commit()
        lastrowid = cursor.lastrowid
        cursor.close()

        return lastrowid

    def fetch_due(self, limit=DEFAULT_REMIND_LIMIT):
        cursor = get_cursor(self.conn, dictionary=True)
        now_utc = datetime.now(timezone.utc)

        cursor.execute("SELECT * FROM Reminders WHERE remind_at_utc <= %s ORDER BY remind_at_utc ASC LIMIT %s", (now_utc, limit))
        rows = cursor.fetchall()
        cursor.close()
        out = []

        for row in rows:
            out.append(Reminder(
                id=row["id"],
                guild_id=row["guild_id"],
                channel_id=row["channel_id"],
                author_id=row["author_id"],
                remind_at_utc=row["remind_at_utc"],
                message=row["message"]))

        return out

    def delete_reminder(self, reminder_id):
        cursor = get_cursor(self.conn)
        cursor.execute("DELETE FROM Reminders WHERE id = %s", (reminder_id,))
        self.conn.commit()
        cursor.close()

    @loop(seconds=10)
    async def dispatch_due(self):
        if not (due := self.fetch_due()):
            return

        for reminder in due:
            try:
                channel = self.bot.get_channel(reminder.channel_id) or await self.bot.fetch_channel(reminder.channel_id)
                if not isinstance(channel, (TextChannel, Thread)):
                    self.delete_reminder(reminder.id)
                    continue

                author_mention = f"<@{reminder.author_id}>"
                await channel.send(f"Reminder for {author_mention}:\n{reminder.message}")
            except Exception:
                pass
            finally:
                self.delete_reminder(reminder.id)

    @dispatch_due.before_loop
    async def before_dispatch(self):
        await self.bot.wait_until_ready()

    def fetch_upcoming_for_user(self, guild_id, author_id, limit=DEFAULT_LIST_LIMIT):
        cursor = get_cursor(self.conn, dictionary=True)
        now_utc = datetime.now(timezone.utc)

        cursor.execute("SELECT id, channel_id, remind_at_utc, message "
                       "FROM Reminders "
                       "WHERE guild_id = %s AND author_id = %s AND remind_at_utc > %s "
                       "ORDER BY remind_at_utc ASC "
                       "LIMIT %s",
                       (guild_id, author_id, now_utc, limit))

        rows = cursor.fetchall()
        cursor.close()
        
        return rows

    @hybrid_command(help="Sets a reminder for a given time. You can specify an exact time, or a time relative to now. Examples:\n"
                    "\t`$remind in 1 hour | call mom`\n"
                    "\t`$remind tomorrow at this time | time to raid`\n"
                    "\t`$remind 2026-01-15 14:30 | party time!`\n\n"
                    "You can use `$remind list` to view your current reminders.",
                    brief="Sets a reminder for a given time",
                    aliases=["remindme", "reminder"])
    async def remind(self, ctx, *, args):
        if "|" not in args:
            if "list" in args.lower():
                return await self.remind_list(ctx)

            return await ctx.send("You must include a time to remind and a message to remind with, separated by the `|` character.\n"
                                  "Example: `$remind tomorrow at noon | watch fishtank`\n\n"
                                  "Please use `$help remind` for more information.")

        when_text, message = [i.strip() for i in args.split('|', 1)]
        
        if not when_text or not message:
            return await ctx.send("You must provide both a time and a message: `$remind <when> | <message>`\n\n"
                                  "Please use `$help remind` for more information")

        tz_name = self.get_guild_tz(ctx.guild)

        if (remind_at_utc := self.parse_when(when_text, tz_name)) is None:
            return await ctx.send("I couldn't understand that time.\n"
                                  "Try things like:\n"
                                  "* in 45 minutes\n"
                                  "* tomorrow at 9am\n"
                                  "* next friday at 5pm\n"
                                  "* 2026-01-15 14:30")

        if remind_at_utc <= datetime.now(timezone.utc):
            return await ctx.send("That time is in the past. Which is bold, but not useful.")

        r_id = self.insert_reminder(
                guild_id=ctx.guild.id if ctx.guild else 0,
                channel_id=ctx.channel.id,
                author_id=ctx.author.id,
                remind_at_utc=remind_at_utc,
                message=message)

        local = remind_at_utc.astimezone(ZoneInfo(tz_name))

        await ctx.send(f"Reminder #{r_id} set for **{local:%a, %b %d %Y %I:%M %p} ({tz_name})**")

    @remind.error
    async def remind_error(self, ctx, error):
        if isinstance(error, errors.MissingRequiredArgument):
            await ctx.send("Usage: `$remind <when> | <message>` or `$remind list`\n"
                           "Please use `$help remind` for more information.")
            error.handled = True

    async def remind_list(self, ctx, limit=DEFAULT_LIST_LIMIT):
        if not ctx.guild:
            return await ctx.send("Listing reminders only works in a server.")

        tz_name = self.get_guild_tz(ctx.guild)
        tz = ZoneInfo(tz_name)

        if not (rows := self.fetch_upcoming_for_user(ctx.guild.id, ctx.author.id, limit=limit)):
            return await ctx.send("You dont have any upcoming reminders here.")

        lines = []

        for row in rows:
            remind_local = row["remind_at_utc"].astimezone(tz)
            msg = (row["message"] or "").replace('\n', ' ')

            if len(msg) > 60:
                msg = msg[:57] + "..."

            lines.append(f"**#{row['id']}** • {remind_local:%b %d %Y %I:%M %p} • <#{row['channel_id']}> • {msg}")
        
        await ctx.send("**Your upcoming reminders:**\n" + '\n'.join(lines))
