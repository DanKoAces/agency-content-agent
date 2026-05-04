import os,json,datetime,requests,anthropic
AK=os.environ["ANTHROPIC_API_KEY"]
RT=os.environ["GOOGLE_REFRESH_TOKEN"]
CID=os.environ["GOOGLE_CLIENT_ID"]
CS=os.environ["GOOGLE_CLIENT_SECRET"]
FLD=os.environ["DRIVE_FOLDER_ID"]
CLIENTS=[
  {"site":"https://www.cover.co.il/","niche":"שירותים פיננסיים"},
  {"site":"https://www.dubnovgallery.co.il/","niche":"אולם אירועים תל אביב"},
  {"site":"https://www.highand.co.il/","niche":"אולם אירועים תל אביב"},
  {"site":"https://www.riverside.co.il/","niche":"אולם אירועים תל אביב"},
  {"site":"https://www.lawrence.co.il/","niche":"אולם אירועים תל אביב"},
  {"site":"https://www.dreamzone.co.il/","niche":"מתחם אירועים"},
  {"site":"https://surmom.co.il/","niche":"אמהות ותינוקות"},
  {"site":"https://www.bubybloom.co.il/","niche":"תינוקות וילדים"},
  {"site":"https://www.gotawatch.com/","niche":"שעונים ואקססוריז"},
  {"site":"https://www.landers.co.il/","niche":"נדלן ומשרדים"},
  {"site":"https://www.stork-service.com/","niche":"שירותי אחסנה"},
  {"site":"https://www.soragdoor.com/","niche":"סורגים ואבטחה"},
  {"site":"https://www.niskoelec.com/","niche":"חשמלאים ותשתיות"},
  {"site":"https://www.ranshapira.co.il/","niche":"יועץ עסקי"},
  {"site":"https://www.mivoleti.co.il/","niche":"שירותי מוטב"},
  {"site":"https://www.mivoleti.com/","niche":"שירותי מוטב"},
  {"site":"https://tlv2go.com/","niche":"תיירות תל אביב"},
  {"site":"https://www.uriel-shay.com/","niche":"אמנות ועיצוב"},
  {"site":"https://www.adrtrading.co.il/","niche":"יבוא ומסחר"},
]
def get_token():
  r=requests.post("https://oauth2.googleapis.com/token",data={"client_id":CID,"client_secret":CS,"refresh_token":RT,"grant_type":"refresh_token"})
  return r.json()["access_token"]
def fetch_sc(token,site):
  today=datetime.date.today()
  s=(today-datetime.timedelta(days=90)).isoformat()
  e=today.isoformat()
  r=requests.post(f"https://searchconsole.googleapis.com/webmasters/v3/sites/{requests.utils.quote(site,safe='')}/searchAnalytics/query",
    headers={"Authorization":f"Bearer {token}"},
    json={"startDate":s,"endDate":e,"dimensions":["query"],"rowLimit":50,"orderBy":[{"fieldName":"impressions","sortOrder":"DESCENDING"}]})
  return r.json().get("rows",[])
def write_post(client,rows):
  c=anthropic.Anthropic(api_key=AK)
  tq="\n".join([f"{r['keys'][0]} ({round(r['impressions'])} חשיפות, {r['ctr']*100:.1f}% CTR)" for r in rows[:10]])
  lnk=", ".join([r["keys"][0] for r in rows if r.get("impressions",0)>=50 and r.get("ctr",1)<0.05][:6])
  tm=c.messages.create(model="claude-sonnet-4-20250514",max_tokens=80,
    messages=[{"role":"user","content":f"נושא בלוג SEO אחד לתחום {client['niche']}. שאילתות: {','.join([r['keys'][0] for r in rows[:5]])}. נושא אחד בלבד."}])
  topic=tm.content[0].text.strip()
  m=c.messages.create(model="claude-sonnet-4-20250514",max_tokens=2000,
    messages=[{"role":"user","content":f"כותב SEO מקצועי בעברית.\nלקוח: {client['site']}\nתחום: {client['niche']}\nנושא: {topic}\nקיץ 2026 חזרה לשגרה\nשאילתות:\n{tq}\nקישורים: {lnk}\n800 מילים, H2, ובסוף:**כותרת SEO:**...\n**תיאור מטא:**...\n**מילות מפתח:**...\nישירות."}])
  return topic,m.content[0].text.strip()
def save_drive(token,title,content):
  bd="-------314159265358979323846"
  meta=json.dumps({"title":title,"mimeType":"application/vnd.google-apps.document","parents":[{"id":FLD}]})
  clean=content.replace("**","").replace("##","").replace("#","")
  body=f"--{bd}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n{meta}\r\n--{bd}\r\nContent-Type: text/plain; charset=UTF-8\r\n\r\n{clean}\r\n--{bd}--"
  r=requests.post("https://www.googleapis.com/upload/drive/v2/files?uploadType=multipart&convert=true",
    headers={"Authorization":f"Bearer {token}","Content-Type":f'multipart/related; boundary="{bd}"'},
    data=body.encode("utf-8"))
  return r.json()
def run_agent():
  print(f"Starting {datetime.datetime.now()}")
  token=get_token()
  for client in CLIENTS:
    d=client["site"].replace("https://","").rstrip("/")
    print(f"Processing: {d}")
    try:
      rows=fetch_sc(token,client["site"])
      if not rows:print("  no data");continue
      topic,post=write_post(client,rows)
      doc=save_drive(token,topic,post)
      print(f"  Done: {doc.get('id','?')}")
    except Exception as e:print(f"  Error: {e}")
  print("All done")
if __name__=="__main__":run_agent()
