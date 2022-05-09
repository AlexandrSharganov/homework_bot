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
    # В этой функции у меня много вопросов.
    # Не только по самой функции, но и по логике написания всего проекта.
    # Главный вопрос в конце функции.
    try:
        # Скажи, пожалуйста, правильно ли я понимаю.
        # Можно вызвать исключение вот так.
        if type(response) is not dict:
            logging.error('Неверный формат данных от API')
            raise TypeError('Неверный формат данных от API')
        # Еще можно использовать isinstance
        # if not isinstance(response, dict):
        #     raise TypeError

        # Проверка ключа может быть такая
        # if 'homeworks' not in response:
        #     raise KeyError

        # Или исключение ключа само вызовется в процессе выполнения.
        # И мы должны ловить его в except.
        list_hw = response['homeworks']  # Проверка ключа 'homeworks'.
        # Вызовется KeyError в случае отсутствия 'homeworks'.
        # Тоже и с current_date.
        # Можно так.
        response['current_date']  # Проверка ключа 'current_date'.
        # Или лучше так?
        # if 'current_date' not in response:
        #     raise KeyError

        # Здесь проверяем что под 'homeworks' действительно list
        if not isinstance(response['homeworks'], list):
            raise TypeError
        # Но можно было использовать:
        # if type(response['homeworks']) is not list:
        #     logging.error('Неверный формат данных от API')
        #     raise TypeError('Неверный формат данных от API')
    except KeyError:
        logging.error('Ключ homeworks или current_date отсутствует.')
        raise KeyError('Ключ homeworks или current_date отсутствует.')
    except TypeError:
        logging.error('Неверный формат данных от API')
        raise TypeError('Неверный формат данных от API')
    else:
        return list_hw
    # Итого вопрос: Как лучше реализовать вызов исключения?
    # Как чаще делают в реальных проектах?
    # И если вариантов написания кода несколько то какой лучше выбрать?
    # А также что лучше if isinstance или if type(response) is not dict?
    # Спасибо.


def parse_status(homework):
    """Формирование статуса."""
    try:
        if not isinstance(homework, dict):
            logging.error('Неверный формат данных от API')
            raise TypeError('Неверный формат данных от API')
        if 'homework_name' not in homework:
            logging.error('не обнаружен ключ homework_name')
            raise KeyError
        if 'status' not in homework:
            logging.error('не обнаружен ключ status')
            raise KeyError
        homework_name = homework['homework_name']
        homework_status = homework['status']
        verdict = HOMEWORK_STATUSES[homework_status]
    except KeyError:
        logging.error('Неизвестный статус ДЗ от API.')
        raise KeyError('Неизвестный статус ДЗ от API.')
    else:
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
    current_timestamp = int(time.time()) - 5
    current_error = None
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if len(homeworks):
                for homework in homeworks:
                    message = parse_status(homework)
                    send_message(bot, message)
                # Проверку current_date вынес на уровень функции check_response
                current_timestamp = response['current_date']
            else:
                logging.debug('отсутствие в ответе новых статусов')
        except Exception as error:
            if error != current_error:
                current_error = error
                message = f'Сбой в работе программы: {error}'
                send_message(bot, message)
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
