import datetime
import time
import http.client
import json
import logging
from configparser import ConfigParser
import requests
import pyttsx3

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

# Load configurations
config = ConfigParser()
config.read('config.ini')
telegram_bot_token = config['telegram']['bot_token']
telegram_chat_id = config['telegram']['chat_id']
day_sleep_time = int(config['app_constants'].get('day_sleep_time', '60'))
night_sleep_time = int(config['app_constants'].get('night_sleep_time', '1200'))
minimum_age = int(config['preferences'].get('age', '44'))
minimum_slots = int(config['preferences'].get('minimum_slots', '1'))
district_ids = json.loads(config['preferences'].get('district_ids'))
nearest_district = int(config['preferences'].get('nearest_district', '0'))

speech_engine = pyttsx3.init()

center_ids = []
pin_codes = []


def get_slots_by_district(district_id: int, start_date: str) -> dict:
    conn = http.client.HTTPSConnection("cdn-api.co-vin.in")
    payload = ''
    headers = {
        'Accept-Language': 'hi_IN'
    }
    conn.request("GET", "/api/v2/appointment/sessions/public/calendarByDistrict?district_id=%s&date=%s"
                 % (district_id, start_date),
                 payload, headers)
    res = conn.getresponse()
    data = res.read()
    return json.loads(data.decode("utf-8"))


def send_telegram_notification(notification: str) -> None:
    requests.post('https://api.telegram.org/bot%s/sendMessage?chat_id=%s&text=%s'
                  % (telegram_bot_token, telegram_chat_id, notification))


def announce_notification(notification: str) -> None:
    speech_engine.say(notification)
    speech_engine.runAndWait()


def get_slots_by_pin():
    pass


def get_slots_by_center():
    pass


def process_slot_information(info: dict):
    for center in info['centers']:
        for session in center['sessions']:
            if session['available_capacity'] >= minimum_slots and session['min_age_limit'] <= minimum_age:
                announcement = ("%s slots available at %s on %s for %s+."
                                % (
                                    session['available_capacity'], center['name'], session['date'],
                                    session['min_age_limit']))
                info_string = "{age} plus Slots Found!\n" \
                              "- Date: {date}\n" \
                              "- Age Group: {age} plus\n" \
                              "- Vaccine: {vaccine_name}\n" \
                              "- Available Slots: {available_slots}\n\n" \
                              "- Price: {price}\n\n" \
                              "- Center Name: {center_name}\n" \
                              "- Address: {center_address}\n" \
                              "- Block Name: {block_name}\n" \
                              "- District: {district_name}\n" \
                              "- State: {state_name}\n" \
                              "- PIN Code: {pin_code}".format(
                                    age=session['min_age_limit'],
                                    date=session['date'],
                                    vaccine_name=session['vaccine'],
                                    available_slots=session['available_capacity'],
                                    center_name=center['name'],
                                    center_address=center['address'],
                                    block_name=center['block_name'],
                                    district_name=center['district_name'],
                                    state_name=center['state_name'],
                                    pin_code=center['pincode'],
                                    price=center['fee_type']
                                )
                logger.info(info_string)
                send_telegram_notification(info_string)
                announce_notification(announcement)
            else:
                logger.debug("No slots at %s on %s" % (center['name'], session['date']))


if __name__ == "__main__":
    speech_engine.say('Initiating CoWin monitoring.')
    speech_engine.runAndWait()
    sleep_time = day_sleep_time
    while True:
        if datetime.datetime.today().replace(hour=6) > \
                datetime.datetime.now() or \
                datetime.datetime.today().replace(hour=20) < datetime.datetime.now():
            sleep_time = night_sleep_time
        else:
            sleep_time = day_sleep_time
        this_week = datetime.datetime.today().strftime('%d-%m-%Y')
        next_week = (datetime.datetime.today() + datetime.timedelta(days=7)).strftime('%d-%m-%Y')
        for district in district_ids:
            if datetime.datetime.today().replace(hour=13) > datetime.datetime.now() and district != nearest_district:
                this_week = (datetime.datetime.today() + datetime.timedelta(days=1)).strftime('%d-%m-%Y')
            try:
                process_slot_information(get_slots_by_district(district, this_week))
                time.sleep(2)
                process_slot_information(get_slots_by_district(district, next_week))
            except Exception:
                speech_engine.say('Something went wrong. Going into sleep mode for 60 seconds. Please ensure you are '
                                  'connected to the internet')
                speech_engine.runAndWait()
                logger.info("Looks like something went wrong. Sleeping 60 seconds.")
                time.sleep(60)
        logger.info("Sleeping for %s seconds..." % sleep_time)
        time.sleep(sleep_time)
