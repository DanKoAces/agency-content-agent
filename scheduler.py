import schedule,time,datetime,pytz
from agent import run_agent
TZ=pytz.timezone("Asia/Jerusalem")
def job():
  print(f"[{datetime.datetime.now(TZ).strftime('%Y-%m-%d %H:%M')}] Running...")
  run_agent()
print("Scheduler started - 02:00 Israel time nightly")
job()
schedule.every().day.at("02:00").do(job)
while True:schedule.run_pending();time.sleep(60)
