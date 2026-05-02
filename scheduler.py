import schedule, time, datetime
import pytz
from agent import run_agent

TZ = pytz.timezone("Asia/Jerusalem")

def job():
    print(f"[{datetime.datetime.now(TZ).strftime('%Y-%m-%d %H:%M %Z')}] Running agent...")
    run_agent()

print("Agency Content Agent Scheduler started")
print("Runs every night at 02:00 Israel time")
job()  # run once on startup

schedule.every().day.at("02:00").do(job)

while True:
    schedule.run_pending()
    time.sleep(60)
