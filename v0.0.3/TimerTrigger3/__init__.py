import logging
import azure.functions as func
import requests
import tweepy
import pytz
from urllib3.exceptions import InsecureRequestWarning
from datetime import datetime
from ..shared import api
from ..shared.linenoti import line_notify

def main() -> None:
    # Setting Time&Date
    bangkok_tz = pytz.timezone("Asia/Bangkok")
    th_time = datetime.now(bangkok_tz)
    date_now = th_time.strftime("%Y-%m-%d")
        
    # Twiiter Auth
    auth = tweepy.OAuthHandler(api.API_KEY, api.API_SECRET_KEY)
    auth.set_access_token(api.ACCESS_TOKEN, api.SECRET_ACCESS_TOKEN)
    logging.info("[TWEEPY] Connecting to Twiiter API >> @covidth_alert")
    API = tweepy.API(auth)
    logging.info("[TWEEPY] Connected!!")

    # Fecth Tweeted Timeline
    logging.info("[TWEEPY] Fecthing Tweeted Timeline")
    data_tweets = API.user_timeline(user_id=api.TWITTER_ID, count=1)
    for tweet in data_tweets:
        date_tweeted_fecth = str(tweet.created_at)[:-15]
    
    # Get Data From MOPH API
    url = "https://covid19.ddc.moph.go.th/api/Cases/today-cases-all"
    try: # Check The APIs is accessible or not.
        try:
            data = requests.get(url).json()[0]
            logging.info("[REQUESTS] Data received.")
        except KeyError:
            data = requests.get(url).json()
            logging.info("[REQUESTS] not the required information.")
            line_notify(f"🚨[ERROR] Pls Check APIs -> {str(data)}", stickerPackageId=11539, stickerId=52114142)
        except Exception:
            requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)
            data = requests.get(url, verify=False).json()[0]
            logging.warning("[REQUESTS] Data (not verify SSL) received")
            if data['txn_date'] == date_now and date_tweeted_fecth != date_now:
                line_notify("🚩[WARNING] Unverified HTTPS request to host 'covid19.ddc.moph.go.th' [SSLCert not verify]", stickerPackageId=789, stickerId=10877)
    except Exception as exc:
        logging.error(f"[REQUESTS] Unable to connect DDC MOPH APIs | Error >> {type(exc)} {exc}")
        line_notify("🚨[ALERT] Unable to connect DDC MOPH APIs")
        line_notify(f"🚨[ERROR] {type(exc)} {exc}", stickerPackageId=11539, stickerId=52114142)
    else:
        # Work process
        if data['txn_date'] == date_now and date_tweeted_fecth != date_now:

            # Get Tranding Hasttag
            logging.info("[TWEEPY] Get Tranding Hasttag")
            woeid = 23424960
            trends = API.get_place_trends(id = woeid)
            result_trends = trends[0]["trends"]
            hashtags = [trend['name'] for trend in result_trends if "#" in trend['name']]

            # TwitterUpdateStatus
            show_date = th_time.strftime("%d/%m/%Y")
            daily_case = str(("🚨 ติดเชื้อใหม่ " + str(data["new_case"]) + " คน ❗\n")*3)
            daily_deaths = str(("⚠ เสียชีวิต " + str(data["new_death"]) + " คน\n")*3)
            timeline = str("📅 ณ วันที่ " + show_date + " 📅\n \n" + daily_case + daily_deaths + "#โควิดวันนี้ #โควิด19 " + hashtags[0] + " " + hashtags[1] + "\n \n" + "ddc.moph.go.th/covid19-dashboard")
            API.update_status(timeline)
            logging.info(f"[TWEEPY] Twitter tweeted status at {show_date}")
            
            # line notify
            line_info_datetime = th_time.strftime("%d-%m-%y" + '@' + "%H:%M")
            line_notify("✅[INFO] Tweeted !! at " + line_info_datetime, stickerPackageId=11539, stickerId=52114117)
        elif date_tweeted_fecth != date_now:
            logging.info("[IDLE] Wait for new data from API.")
        else:
            logging.info("[IDLE] Today has already tweeted data.")

if __name__ == '__main__':
    main()