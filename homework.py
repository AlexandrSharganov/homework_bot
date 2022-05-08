import os
import sys
import time
import requests
import logging
import telegram
from dotenv import load_dotenv


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
    except Exception:
        logging.error('Сбой отправки сообщения!')


def get_api_answer(current_timestamp):
    """Запрос данных с API."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=params
        )
        if response.status_code != 200:
            print('if working!')
            print(response.status_code)
            raise ConnectionError
    except ConnectionError as error:
        logging.error(f'Ошибка при запросе к основному API: {error}')
        raise ConnectionError(f'Ошибка при запросе к основному API: {error}')
    else:
        return response.json()


def check_response(response):
    """Проверка данных от API."""
    try:
        list_hw = response['homeworks']
        list_hw[0]
    except IndexError:
        logging.error('Список пуст')
        raise IndexError('Список пуст')
    if type(response) is not dict:
        logging.error('Неверный формат')
        raise TypeError('Неверный формат')
    if list_hw is None:
        logging.error('Отсутствует ключ: homeworks')
    return list_hw


def parse_status(homework):
    """Формирование статуса."""
    if 'homework_name' not in homework:
        logging.error('не обнаружен ключ homework_name')
        raise KeyError
    if 'status' not in homework:
        logging.error('не обнаружен ключ status')
        raise KeyError
    if homework['status'] is None:
        logging.error('не обнаружен статус домашней работы')
        raise ValueError
    homework_name = homework['homework_name']
    homework_status = homework['status']
    last_status = ''
    if homework_status != last_status:
        verdict = HOMEWORK_STATUSES[homework_status]
        last_status = HOMEWORK_STATUSES[homework_status]
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка токенов."""
    if (PRACTICUM_TOKEN
        and TELEGRAM_TOKEN
            and TELEGRAM_CHAT_ID):
        return True
    else:
        logging.critical('Отсутствие обязательных переменных окружения')
        return False


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if len(homeworks):
                last_homework = homeworks[0]
                message = parse_status(last_homework)
                send_message(bot, message)
                current_timestamp = response['current_date'] + 1
            else:
                logging.debug('отсутствие в ответе новых статусов')
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            logging.error(message)
            time.sleep(RETRY_TIME)
        else:
            pass


if __name__ == '__main__':
    main()
