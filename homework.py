import os
import sys
import time
import requests
import logging
import telegram
from dotenv import load_dotenv
from http import HTTPStatus
from json.decoder import JSONDecodeError


load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')


RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(name)s -  %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler(
            filename="main.log",
            encoding='utf-8', mode='w'
        )
    ],
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(stream=sys.stdout)
logger.addHandler(handler)


def send_message(bot, message):
    """Отправка сообщения в телеграмм."""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message,
        )
        logging.info('Сообщение отправлено!')
    except telegram.TelegramError:
        logging.error('Сбой отправки сообщения!')


def get_api_answer(current_timestamp):
    """Запрос данных с API."""
    timestamp = current_timestamp
    params = {'from_date': timestamp}
    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=params
        )
        if response.status_code != HTTPStatus.OK:
            raise ConnectionError('status code is not 200')
        return response.json()
    except ConnectionError as error:
        logging.error(f'Ошибка при запросе к основному API: {error}')
        raise ConnectionError(f'Ошибка при запросе к основному API: {error}')
    except JSONDecodeError:
        logging.error('Ошибка приведения к json')
        raise JSONDecodeError('Ошибка приведения к json')


def check_response(response):
    """Проверка данных от API."""
    try:
        if not isinstance(response, dict):
            raise TypeError('Ответ не содержит тип данных dict')
        homeworks = response.get('homeworks')
        if not homeworks:
            raise KeyError('Ключ homeworks отсутствует.')
        if not response.get('current_date'):
            raise KeyError('Ключ current_date отсутствует.')
        if not isinstance(homeworks, list):
            raise TypeError('Ответ не содержит тип данных list')
    except KeyError as error:
        logging.error(f'Ключ не обнаружен: {error}')
        raise KeyError(f'Ключ не обнаружен: {error}')
    except TypeError as error:
        logging.error(f'Неверный формат данных от API: {error}')
        raise TypeError(f'Неверный формат данных от API: {error}')
    else:
        return homeworks


def parse_status(homework):
    """Формирование статуса."""
    if not isinstance(homework, dict):
        logging.error('Неверный формат данных от API')
        raise TypeError('Неверный формат данных от API')
    if not homework.get('homework_name'):
        logging.error('В ответе API не обнаружен ключ homework_name')
        raise KeyError('В ответе API не обнаружен ключ homework_name')
    if not homework.get('status'):
        logging.error('В ответе API не обнаружен ключ status')
        raise KeyError('В ответе API не обнаружен ключ status')
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if not HOMEWORK_STATUSES.get(homework_status):
        logging.error(f'Неизвестный статус ДЗ от API: {homework_status}')
        raise KeyError(f'Неизвестный статус ДЗ от API: {homework_status}')
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка токенов."""
    token_list = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    if all(token_list):
        return True
    else:
        for token in token_list:
            if not token:
                logging.critical(f'Отсутствие переменной окружения {token}')
        return False


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time()) - RETRY_TIME
    current_error = None
    if check_tokens():
        while True:
            try:
                response = get_api_answer(current_timestamp)
                homeworks = check_response(response)
                if len(homeworks):
                    for homework in homeworks:
                        message = parse_status(homework)
                        send_message(bot, message)
                else:
                    logging.debug('отсутствие в ответе новых статусов')
                current_timestamp = response['current_date']
                current_error = None
            except Exception as error:
                if error != current_error:
                    current_error = error
                    message = f'Сбой в работе программы: {error}'
                    send_message(bot, message)
            finally:
                time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
