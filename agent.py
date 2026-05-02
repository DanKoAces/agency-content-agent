import os, json, datetime, requests
from google.oauth2 import service_account
from googleapiclient.discovery import build
import anthropic

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
GOOGLE_SERVICE_ACCOUNT_JSON = os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]
DRIVE_FOLDER_ID = os.environ["DRIVE_FOLDER_ID"]

SCOPES = [
    "https://www.googleapis.com/auth/webmasters.readonly",
    "https://www.googleapis.com/auth/drive.file",
]

CLIENTS = [
    {"site": "https://www.adrtrading.co.il/",   "niche": "יבוא ומסחר",               "type": "trade"},
    {"site": "https://www.bubybloom.co.il/",     "niche": "תינוקות וילדים",           "type": "parenting"},
    {"site": "https://www.cover.co.il/",         "niche": "שירותים פיננסיים",         "type": "finance"},
    {"site": "https://www.dreamzone.co.il/",     "niche": "מתחם אירועים",             "type": "events"},
    {"site": "https://www.dubnovgallery.co.il/", "niche": "אולם אירועים תל אביב",    "type": "events"},
    {"site": "https://www.gotawatch.com/",       "niche": "שעונים ואקססוריז",        "type": "retail"},
    {"site": "https://www.highand.co.il/",       "niche": "אולם אירועים תל אביב",    "type": "events"},
    {"site": "https://www.landers.co.il/",       "niche": "נדלן ומשרדים",             "type": "realestate"},
    {"site": "https://www.lawrence.co.il/",      "niche": "אולם אירועים תל אביב",    "type": "events"},
    {"site": "https://www.mivoleti.co.il/",      "niche": "שירותי מוטב",             "type": "services"},
    {"site": "https://www.mivoleti.com/",        "niche": "שירותי מוטב",             "type": "services"},
    {"site": "https://www.niskoelec.com/",       "niche": "חשמלאים ותשתיות",        "type": "electrical"},
    {"site": "https://www.ranshapira.co.il/",    "niche": "יועץ עסקי",               "type": "consulting"},
    {"site": "https://www.riverside.co.il/",     "niche": "אולם אירועים תל אביב",    "type": "events"},
    {"site": "https://www.soragdoor.com/",       "niche": "סורגים ואבטחה",           "type": "security"},
    {"site": "https://www.stork-service.com/",   "niche": "שירותי אחסנה ולוגיסטיקה","type": "logistics"},
    {"site": "https://surmom.co.il/",            "niche": "אמהות ותינוקות",          "type": "parenting"},
    {"site": "https://tlv2go.com/",              "niche": "תיירות ומסעדות תל אביב",  "type": "tourism"},
    {"site": "https://www.uriel-shay.com/",      "niche": "אמנות ועיצוב",            "type": "art"},
]

TYPE_CTX = {
    "events":     ["עונת חתונות שיא", "זוגות שדחו אירועים"],
    "finance":    ["ריבית מתייצבת - זמן לתכנון"],
    "parenting":  ["קיץ - פעילויות לילדים"],
    "tourism":    ["תיירות פנים גואה"],
    "retail":     ["קניות קיץ"],
    "logistics":  ["גידול בסחר"],
    "realestate": ["שוק נדלן - שינויי ריבית"],
    "art":        ["עונת תרבות"],
    "security":   ["מודעות ביטחונית גבוהה"],
    "electrical": ["בנייה ושיפוץ בקיץ"],
    "consulting": ["עסקים מתאוששים"],
    "trade":      ["יבוא מתאושש"],
    "services":   ["שגרה חוזרת"],
    "default":    ["קיץ 2026"],
}

BASE_CTX = ["קיץ 2026 עונת שיא", "חזרה לשגרה ולפנאי", "אינפלציה מתייצבת", "AI וקיימות"]


def get_creds():
    sa = json.loads(GOOGLE_SERVICE_ACCOUNT_JSON)
    return service_account.Credentials.from_service_account_info(sa, scopes=SCOPES)


def fetch_sc(creds, site, days=90):
    svc = build("searchconsole", "v1", credentials=creds)
    today = datetime.date.today()
    start = (today - datetime.timedelta(days=days)).isoformat()
    end = today.isoformat()
    try:
        r = svc.searchanalytics().query(siteUrl=site, body={
            "startDate": start, "endDate": end,
            "dimensions": ["query"], "rowLimit": 50,
            "orderBy": [{"fieldName": "impressions", "sortOrder": "DESCENDING"}]
        }).execute()
        return r.get("rows", [])
    except Exception as e:
        print(f"  SC error {site}: {e}")
        return []


def write_post(client, rows):
    claude = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    ctx = " - ".join(BASE_CTX + TYPE_CTX.get(client["type"], ["קיץ 2026"]))
    top_q = "\n".join([f"{r['keys'][0]} ({round(r['impressions'])} חשיפות, {r['ctr']*100:.1f}% CTR)" for r in rows[:10]])
    links = ", ".join([r["keys"][0] for r in rows if r.get("impressions",0)>=50 and r.get("ctr",1)<0.05][:6])
    
    # First get topic suggestion
    topic_msg = claude.messages.create(
        model="claude-sonnet-4-20250514", max_tokens=100,
        messages=[{"role":"user","content":f"יועץ SEO. הצע נושא בלוג אחד.\nתחום: {client['niche']}\nשאילתות: {', '.join([r['keys'][0] for r in rows[:5]])}\nהקשר: {ctx}\nנושא אחד בלבד."}]
    )
    topic = topic_msg.content[0].text.strip()
    
    # Then write the post
    msg = claude.messages.create(
        model="claude-sonnet-4-20250514", max_tokens=2000,
        messages=[{"role":"user","content":f"כותב SEO מקצועי בעברית.\n\nלקוח: {client['site']}\nתחום: {client['niche']}\nנושא: {topic}\nהקשר: {ctx}\n\nשאילתות SC:\n{top_q}\n\nקישורים פנימיים: {links}\n\nכתוב 800 מילים, H2, קישורים [טקסט](URL), ובסוף:\n**כותרת SEO:** ...\n**תיאור מטא:** ...\n**מילות מפתח:** ...\n\nישירות ללא הקדמה."}]
    )
    return topic, msg.content[0].text.strip()


def save_to_drive(creds, title, content):
    import io
    from googleapiclient.http import MediaIoBaseUpload
    drive = build("drive", "v3", credentials=creds)
    meta = {"name": title, "mimeType": "application/vnd.google-apps.document", "parents": [DRIVE_FOLDER_ID]}
    media = MediaIoBaseUpload(io.BytesIO(content.encode("utf-8")), mimetype="text/plain")
    return drive.files().create(body=meta, media_body=media, fields="id,name,webViewLink").execute()


def run_agent():
    creds = get_creds()
    results = []
    print(f"Agency Content Agent - {datetime.datetime.now()}")
    for client in CLIENTS:
        domain = client["site"].replace("https://","").rstrip("/")
        print(f"Processing: {domain}")
        try:
            rows = fetch_sc(creds, client["site"])
            if not rows:
                print(f"  No SC data, skipping")
                continue
            topic, post = write_post(client, rows)
            doc = save_to_drive(creds, topic, post)
            print(f"  Done: {doc.get('webViewLink')}")
            results.append({"site": client["site"], "topic": topic, "url": doc.get("webViewLink")})
        except Exception as e:
            print(f"  Error: {e}")
            results.append({"site": client["site"], "error": str(e)})
    print(f"Done: {len([r for r in results if 'url' in r])}/{len(CLIENTS)} succeeded")
    return results

if __name__ == "__main__":
    run_agent()
