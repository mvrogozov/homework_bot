import os
import time
import telegram
import requests
from telegram import Bot
from dotenv import load_dotenv


load_dotenv()


PRACTICUM_TOKEN = os.getenv('YAPR_TOKEN')
TELEGRAM_TOKEN = os.getenv('TLGRM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TLGRM_CHAT_ID')

RETRY_TIME = 6 #600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


bot = Bot(token=TELEGRAM_TOKEN)

def send_message(bot, message):
    bot.send_message(
        chat_id=TELEGRAM_CHAT_ID,
        text=str(message)
    )


def get_api_answer(current_timestamp):
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    hw_status = requests.get(ENDPOINT, HEADERS, params)
    return hw_status.json()


def check_response(response):
    return response.get('homeworks')# todo


def parse_status(homework):
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    tokens_status = bool(PRACTICUM_TOKEN and TELEGRAM_CHAT_ID and TELEGRAM_TOKEN)
    return tokens_status

def main():
    """Основная логика работы бота."""

    ...

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())

    ...

    while True:
        try:
            response = ...

            ...

            current_timestamp = ...
            print(check_tokens(), 'aaa')
            time.sleep(RETRY_TIME)
            break

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            ...
            time.sleep(RETRY_TIME)
        else:
            ...


if __name__ == '__main__':
    main()
