import logging
import os
import time
from http import HTTPStatus
from logging import StreamHandler
from typing import Optional, Union

import requests
import telegram
from dotenv import load_dotenv

from exceptions import HwStatusError

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

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot: telegram.Bot, message: str) -> None:
    """Send message by telegram bot."""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=str(message)
        )
    except telegram.error.TelegramError:
        logger.error('Ошибка при отправке сообщения в telegram')
    else:
        logger.info('Сообщение успешно отправлено в telegram')


def get_api_answer(current_timestamp) -> dict:
    """Get answer from API, using timestamp."""
    timestamp: int = current_timestamp or int(time.time())
    params: dict = {'from_date': timestamp}
    hw_status: requests.Response = requests.get(
        ENDPOINT, headers=HEADERS, params=params
    )
    if hw_status.status_code != 200:
        if hw_status.status_code == HTTPStatus.NOT_FOUND:
            err_message = (
                f'Не  найден endpoint адрес {ENDPOINT}. '
                f'Код ответа API: {hw_status.status_code}'
            )
            logger.error(err_message)
            raise HwStatusError(err_message)
        elif 400 <= hw_status.status_code < 500:
            err_message = (
                f'Ошибка в клиентской части при запросе к {ENDPOINT}, '
                f'код: {hw_status.status_code}'
            )
            logger.error(err_message)
            raise HwStatusError(err_message)
        elif hw_status.status_code >= 500:
            err_message = (
                f'Ошибка на сервере при запросе к {ENDPOINT}, '
                f'код: {hw_status.status_code}'
            )
            logger.error(err_message)
            raise HwStatusError(err_message)
        raise requests.RequestException
    return hw_status.json()


def check_response(response) -> list:
    """Validate response."""
    if type(response) != dict:
        logger.error(f'Неверный формат ответа от API: {type(response)}')
        raise TypeError
    hw_list: Union[list, str] = response.get('homeworks', 'no_key')
    if hw_list == 'no_key':
        logger.error(
            f'В ответе API отсутствует ожидаемый ключ. response = {response}'
        )
        raise KeyError
    if type(hw_list) != list:
        logger.error(
            f'Неверный формат данных в ответе от API: {type(hw_list)}'
        )
        raise TypeError
    return hw_list


def parse_status(homework) -> str:
    """Parsing results."""
    homework_name: str = homework.get('homework_name')
    if 'homework_name' not in homework.keys():
        logger.error('Отсутствует имя работы.')
        raise KeyError
    homework_status: str = homework.get('status')
    if homework_status not in HOMEWORK_STATUSES.keys():
        logger.error('Недокументированный статус работы.')
        raise HwStatusError
    else:
        logger.debug('Новые статусы в ответе отсутствуют.')
    verdict: Optional[str] = HOMEWORK_STATUSES.get(homework_status)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens() -> bool:
    """Checking that all tokens are allowed."""
    tokens_status: bool = bool(
        PRACTICUM_TOKEN and TELEGRAM_CHAT_ID and TELEGRAM_TOKEN
    )
    token_dict = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID
    }
    for token_name, token_value in token_dict.items():
        if not token_value:
            logger.critical(
                f'Отсутствует обязательная переменная окружения: {token_name}'
            )
    return tokens_status


def main():
    """Main logic."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    last_error = ''
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
                else:
                    logger.debug('Новых сообщений нет.')
                current_timestamp: int = int(time.time())
                time.sleep(RETRY_TIME)

            except Exception as error:
                message: str = f'Сбой в работе программы: {error}'
                if last_error != error:
                    send_message(bot, message)
                last_error = error
                logger.error(message)
                time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
