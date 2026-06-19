from datetime import datetime, timedelta
from random import randint


MAX_TIME = timedelta(hours = 1)


class BoTracker:
    def __init__(self, bot_id):
        self.bot_id = bot_id
        self.last_reply = None
        self.reply_count = 0

    def check_skip(self):
        time_now = datetime.now()

        if self.last_reply is None or time_now - self.last_reply > MAX_TIME:
            self.last_reply = time_now
            self.reply_count = 1
            
            return False

        if randint(0, 99) < 100 / self.reply_count:
            self.last_reply = time_now
            self.reply_count += 1

            return False

        return True
