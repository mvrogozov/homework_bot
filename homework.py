import logging
import os
import time
import telegram
import requests
from exceptions import HwStatusError
from telegram import Bot
from http  import HTTPStatus
from dotenv import load_dotenv
from logging import StreamHandler


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = StreamHandler()
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)
logger.addHandler(handler)

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

def send_message(bot, message):
    try:
        bot.send_message(
        chat_id=TELEGRAM_CHAT_ID,
        text=str(message)
    )
    except telegram.error.TelegramError:
        logger.error('Ошибка при отправке сообщения в telegram')
    else:
        logger.info('Сообщение успешно отправлено в telegram')

def get_api_answer(current_timestamp):
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    hw_status = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if hw_status.status_code != 200:
        if hw_status.status_code == HTTPStatus.NOT_FOUND:
            logger.error(f'Не  найден endpoint адрес {ENDPOINT}. Код ответа API: {hw_status.status_code}')
        elif 400 <= hw_status.status_code < 500:
            logger.error('Ошибка в клиентской части при запросе к {ENDPOINT}, код: {hw_status.status_code}')
        elif hw_status.status_code >= 500:
            logger.error('Ошибка на сервере при запросе к {ENDPOINT}, код: {response.status_code}')
        raise requests.RequestException
    return hw_status.json()


def check_response(response):
    if type(response) != dict:
        logger.error(f'Неверный формат ответа от API: {type(response)}')
        raise TypeError
    hw_list = response.get('homeworks', 'no_key')
    if hw_list == 'no_key':
        logger.error(f'В ответе API отсутствует ожидаемый ключ. response = {response}')
        raise KeyError
    
    if type(hw_list) != list:
        logger.error(f'Неверный формат данных в ответе от API: {type(hw_list)}')
        raise TypeError
    return hw_list


def parse_status(homework):
    homework_name = homework.get('homework_name')
    if 'homework_name' not in homework.keys():
        logger.error('Отсутствует имя работы.')
        raise KeyError
    homework_status = homework.get('status')
    if homework_status not in HOMEWORK_STATUSES.keys():
        logger.error('Недокументированный статус работы.')
        raise HwStatusError
    else:
        logger.debug('Новые статусы в ответе отсутствуют.')
    verdict = HOMEWORK_STATUSES.get(homework_status)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    tokens_status = bool(PRACTICUM_TOKEN and TELEGRAM_CHAT_ID and TELEGRAM_TOKEN)
    token_dict = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID
    }
    for token_name, token_value  in token_dict.items():
        if not token_value:
            logger.critical(f'Отсутствует обязательная переменная окружения: {token_name}')
    return tokens_status

def main():
    """Основная логика работы бота."""

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time()) - 60 * 60 * 24 * 40

    if check_tokens():
        while True:
            try:
                response = get_api_answer(current_timestamp)
                hw_list = check_response(response)
                if hw_list:
                    message = ''
                    for elem in hw_list:
                        message += '\n' + parse_status(elem)
                    send_message(bot, message)
                current_timestamp = int(time.time())
                logger.debug('Новых сообщений нет.')
                time.sleep(RETRY_TIME)

            except Exception as error:
                message = f'Сбой в работе программы: {error}'
                logger.error(message)
                break
                time.sleep(RETRY_TIME)

if __name__ == '__main__':
    main()
