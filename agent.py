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
  {"site":"https://tlv2go.com/","niche":"תיירות ומסעדות תל אביב"},
  {"site":"https://www.uriel-shay.com/","niche":"אמנות ועיצוב"},
  {"site":"https://www.adrtrading.co.il/","niche":"יבוא ומסחר"},
]

WRITING_RULES = (
    "כללי כתיבה חובה:\n"
    "- עברית תקנית, ישירה ושוטפת. לא תרגום מאנגלית.\n"
    "- אסור בהחלט להשתמש בסימן - (מקף ארוך) בשום מקום.\n"
    "- משפטים קצרים וברורים.\n"
    "- לא לכתוב ביטויים מתורגמים כמו: תשאלו לראות, לפגוש צוות.\n"
    "- במקום זאת: בקשו לראות, הכירו את הצוות, צרו קשר.\n"
    "- 800 מילים בדיוק.\n"
)

def get_token():
    r = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": CID, "client_secret": CS,
        "refresh_token": RT, "grant_type": "refresh_token"
    })
    d = r.json()
    if "access_token" not in d:
        raise Exception("Token error: " + str(d))
    return d["access_token"]

def fetch_sc(token, site):
    today = datetime.date.today()
    s = (today - datetime.timedelta(days=90)).isoformat()
    e = today.isoformat()
    encoded_site = requests.utils.quote(site, safe="")
    url = "https://searchconsole.googleapis.com/webmasters/v3/sites/" + encoded_site + "/searchAnalytics/query"
    r = requests.post(url,
        headers={"Authorization": "Bearer " + token},
        json={"startDate": s, "endDate": e, "dimensions": ["query"], "rowLimit": 50,
              "orderBy": [{"fieldName": "impressions", "sortOrder": "DESCENDING"}]})
    d = r.json()
    if "error" in d:
        raise Exception("SC error: " + d["error"]["message"])
    return d.get("rows", [])

def write_post(client, rows):
    c = anthropic.Anthropic(api_key=AK)
    tq = "\n".join([
        r["keys"][0] + " (" + str(round(r["impressions"])) + " חשיפות, " + str(round(r["ctr"]*100, 1)) + "% CTR)"
        for r in rows[:10]
    ])
    lnk = ", ".join([
        r["keys"][0] for r in rows
        if r.get("impressions", 0) >= 50 and r.get("ctr", 1) < 0.05
    ][:6])

    tm = c.messages.create(model="claude-sonnet-4-20250514", max_tokens=80,
        messages=[{"role": "user", "content":
            "נושא בלוג SEO אחד לתחום " + client["niche"] +
            ". שאילתות: " + ",".join([r["keys"][0] for r in rows[:5]]) +
            ". נושא אחד בלבד ללא הסבר."}])
    topic = tm.content[0].text.strip()

    prompt = (
        "כותב תוכן שיווקי בכיר בעברית תקנית.\n\n" +
        WRITING_RULES + "\n" +
        "לקוח: " + client["site"] + "\n" +
        "תחום: " + client["niche"] + "\n" +
        "נושא: " + topic + "\n" +
        "הקשר עכשווי: קיץ 2026, חזרה לשגרה, עונת חתונות\n\n" +
        "שאילתות Search Console:\n" + tq + "\n\n" +
        "הזדמנויות לקישורים פנימיים: " + lnk + "\n\n" +
        "מבנה:\n" +
        "- כותרת H1\n" +
        "- 5 כותרות H2\n" +
        "- 800 מילים\n" +
        "- קישורים פנימיים בפורמט [טקסט](URL)\n" +
        "- בסוף בלבד:\n" +
        "**כותרת SEO:** ...\n" +
        "**תיאור מטא:** ...\n" +
        "**מילות מפתח:** ...\n\n" +
        "כתוב ישירות ללא הקדמה."
    )

    m = c.messages.create(model="claude-sonnet-4-20250514", max_tokens=2500,
        messages=[{"role": "user", "content": prompt}])
    return topic, m.content[0].text.strip()

def save_drive(token, title, content):
    bd = "-------314159265358979323846"
    meta = json.dumps({"title": title, "mimeType": "application/vnd.google-apps.document", "parents": [{"id": FLD}]})
    clean = content.replace("**", "").replace("##", "").replace("#", "")
    body = "--" + bd + "\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n" + meta + "\r\n--" + bd + "\r\nContent-Type: text/plain; charset=UTF-8\r\n\r\n" + clean + "\r\n--" + bd + "--"
    r = requests.post(
        "https://www.googleapis.com/upload/drive/v2/files?uploadType=multipart&convert=true",
        headers={"Authorization": "Bearer " + token, "Content-Type": 'multipart/related; boundary="' + bd + '"'},
        data=body.encode("utf-8")
    )
    d = r.json()
    if "id" not in d:
        raise Exception("Drive error: " + str(d))
    return d

def run_agent():
    print("Starting " + str(datetime.datetime.now()))
    token = get_token()
    print("Token OK")
    results = []
    for client in CLIENTS:
        domain = client["site"].replace("https://", "").rstrip("/")
        print("Processing: " + domain)
        try:
            rows = fetch_sc(token, client["site"])
            if not rows:
                print("  no data")
                continue
            print("  " + str(len(rows)) + " queries")
            topic, post = write_post(client, rows)
            print("  topic: " + topic[:60])
            doc = save_drive(token, topic, post)
            print("  saved: " + str(doc.get("id")))
            results.append({"site": client["site"], "topic": topic})
        except Exception as e:
            print("  error: " + str(e))
    print("Done: " + str(len(results)) + "/" + str(len(CLIENTS)))
    return results

if __name__ == "__main__":
    run_agent()
