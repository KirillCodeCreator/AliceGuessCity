import logging
import os
import random

from flask import Flask, request, jsonify

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)

cities = {
    'москва': ['1030494/25d28b22b2f6e19b5e99', '965417/4433c8931df3e3b60d9e'],
    'нью-йорк': ['997614/100444a6154021c20d8b', '1521359/f5131da7ed5d9a538b9c'],
    'париж': ["965417/ce23e89068b25f2691ec", '965417/fc166dffd087545cbe7a']
}
coutries = {
    'москва': ['Россия', 'россия', "РФ", 'рф', 'Российская Федерация'],
    'нью-йорк': ['США','Сша', 'сша', "Соединенные Штаты Америки"],
    'париж': ['Франция', 'франция']
}

sessionStorage = {}


@app.route('/post', methods=['POST'])
def main():
    logging.info('Request: %r', request.json)
    response = {
        'session': request.json['session'],
        'version': request.json['version'],
        'response': {
            'end_session': False
        }
    }
    handle_dialog(response, request.json)
    logging.info('Response: %r', response)
    return jsonify(response)


def handle_dialog(res, req):
    user_id = req['session']['user_id']

    if help_needed(req, res):
        return

    if url_redirect(req, res):
        return

    if req['session']['new']:
        res['response']['text'] = 'Привет! Назови своё имя!'
        res["response"]["buttons"] = [{"title": "Помощь", "hide": True}]
        sessionStorage[user_id] = {
            'first_name': None,  # здесь будет храниться имя
            'game_started': False  # здесь информация о том, что пользователь начал игру. По умолчанию False
        }
        return

    if sessionStorage[user_id]['first_name'] is None:
        first_name = get_first_name(req)
        if first_name is None:
            res['response']['text'] = 'Не расслышала имя. Повтори, пожалуйста!'
            res["response"]["buttons"] = [{"title": "Помощь", "hide": True}]
        else:
            sessionStorage[user_id]['first_name'] = first_name
            # создаём пустой массив, в который будем записывать города, которые пользователь уже отгадал
            sessionStorage[user_id]['guessed_cities'] = []
            # как видно из предыдущего навыка, сюда мы попали, потому что пользователь написал своем имя.
            # Предлагаем ему сыграть и два варианта ответа "Да" и "Нет".
            res['response']['text'] = f'Приятно познакомиться, {first_name.title()}. Я Алиса. Отгадаешь город по фото?'
            res['response']['buttons'] = [
                {
                    'title': 'Да',
                    'hide': True
                },
                {
                    'title': 'Нет',
                    'hide': True
                },
                {"title": "Помощь", "hide": True}
            ]
    else:
        # У нас уже есть имя, и теперь мы ожидаем ответ на предложение сыграть.
        # В sessionStorage[user_id]['game_started'] хранится True или False в зависимости от того,
        # начал пользователь игру или нет.
        if not sessionStorage[user_id]['game_started']:
            # игра не начата, значит мы ожидаем ответ на предложение сыграть.
            if 'да' in req['request']['nlu']['tokens']:
                # если пользователь согласен, то проверяем не отгадал ли он уже все города.
                # По схеме можно увидеть, что здесь окажутся и пользователи, которые уже отгадывали города
                if len(sessionStorage[user_id]['guessed_cities']) == 3:
                    # если все три города отгаданы, то заканчиваем игру
                    res['response']['text'] = 'Ты отгадал все города!'
                    res["response"]["end_session"] = True
                else:
                    # если есть неотгаданные города, то продолжаем игру
                    sessionStorage[user_id]['game_started'] = True
                    # номер попытки, чтобы показывать фото по порядку
                    sessionStorage[user_id]['attempt'] = 1
                    sessionStorage[user_id]['countryattempt'] = 1
                    # функция, которая выбирает город для игры и показывает фото
                    play_game(res, req)
            elif 'нет' in req['request']['nlu']['tokens']:
                res['response']['text'] = 'Ну и ладно!'
                res["response"]["end_session"] = True
            else:
                res['response']['text'] = 'Не поняла ответа! Так да или нет?'
                res['response']['buttons'] = [
                    {
                        'title': 'Да',
                        'hide': True
                    },
                    {
                        'title': 'Нет',
                        'hide': True
                    },
                    {"title": "Помощь", "hide": True}
                ]
        else:
            play_game(res, req)


def play_game(res, req):
    user_id = req['session']['user_id']
    attempt = sessionStorage[user_id]['attempt']
    countryattempt = sessionStorage[user_id]['countryattempt']
    if attempt == 1:
        # если попытка первая, то случайным образом выбираем город для гадания
        city = random.choice(list(cities))
        # выбираем его до тех пор пока не выбираем город, которого нет в sessionStorage[user_id]['guessed_cities']
        while city in sessionStorage[user_id]['guessed_cities']:
            city = random.choice(list(cities))
        # записываем город в информацию о пользователе
        sessionStorage[user_id]['city'] = city
        sessionStorage[user_id]['country'] = coutries[city]
        # добавляем в ответ картинку
        res['response']['card'] = {}
        res['response']['card']['type'] = 'BigImage'
        res['response']['card']['title'] = 'Что это за город?'
        res['response']['card']['image_id'] = cities[city][attempt - 1]
        res['response']['text'] = 'Тогда сыграем!'
        res['response']['buttons'] = [{"title": "Помощь", "hide": True}]
    else:
        # сюда попадаем, если попытка отгадать не первая
        city = sessionStorage[user_id]['city']
        countries = sessionStorage[user_id]['country']
        # проверяем есть ли правильный ответ в сообщение
        if has_city_answer(user_id, city):
            if get_country(req) in countries:
                res['response']['text'] = 'Правильно! Сыграем ещё?'
                res['response']['buttons'] = [
                    {
                        'title': 'Да',
                        'hide': True
                    },
                    {
                        'title': 'Нет',
                        'hide': True
                    },
                    {
                        "title": "Покажи город на карте",
                        "url": f"https://yandex.ru/maps/?mode=search&text={city}",
                        "hide": True
                    }
                ]
                sessionStorage[user_id]['game_started'] = False
                return
            elif countryattempt == 3:
                # если попытка третья, то значит, что все картинки мы показали.
                # В этом случае говорим ответ пользователю,
                # Обратите внимание на этот шаг на схеме.
                res['response']['text'] = f'Вы пытались. Это {countries[0]}. Сыграем ещё?'
                res['response']['buttons'] = [
                    {
                        'title': 'Да',
                        'hide': True
                    },
                    {
                        'title': 'Нет',
                        'hide': True
                    },
                    {"title": "Помощь", "hide": True}
                ]
                sessionStorage[user_id]['game_started'] = False
                return
            else:
                sessionStorage[user_id]['countryattempt'] += 1
                res['response']['text'] = 'А вот и не угадал! Попробуй еще раз'
                return
        elif get_city(req) == city: # если да, то добавляем город к sessionStorage[user_id]['guessed_cities'] и
            sessionStorage[user_id]['guessed_cities'].append(city)
            sessionStorage[user_id]['game_started'] = True
            # отправляем пользователя на второй круг. Обратите внимание на этот шаг на схеме.
            res['response']['text'] = 'Правильно! А в какой стране этот город?'
            return
        else:
            # если нет
            if attempt == 3:
                # если попытка третья, то значит, что все картинки мы показали.
                # В этом случае говорим ответ пользователю,
                # Обратите внимание на этот шаг на схеме.
                res['response']['text'] = f'Вы пытались. Это {city.title()}. Сыграем ещё?'
                res['response']['buttons'] = [
                    {
                        'title': 'Да',
                        'hide': True
                    },
                    {
                        'title': 'Нет',
                        'hide': True
                    },
                    {"title": "Помощь", "hide": True}
                ]
                sessionStorage[user_id]['game_started'] = False
                sessionStorage[user_id]['guessed_cities'].append(city)
                return
            else:
                # иначе показываем следующую картинку
                res['response']['card'] = {}
                res['response']['card']['type'] = 'BigImage'
                res['response']['card']['title'] = 'Неправильно. Вот тебе дополнительное фото'
                res['response']['card']['image_id'] = cities[city][attempt - 1]
                res['response']['text'] = 'А вот и не угадал!'
                res['response']['buttons'] = [{"title": "Помощь", "hide": True}]
    # увеличиваем номер попытки доля следующего шага
    sessionStorage[user_id]['attempt'] += 1


def get_city(req):
    # перебираем именованные сущности
    for entity in req['request']['nlu']['entities']:
        # если тип YANDEX.GEO, то пытаемся получить город(city), если нет, то возвращаем None
        if entity['type'] == 'YANDEX.GEO':
            # возвращаем None, если не нашли сущности с типом YANDEX.GEO
            return entity['value'].get('city', None)

def get_country(req):
    # перебираем именованные сущности
    for entity in req['request']['nlu']['entities']:
        # если тип YANDEX.GEO, то пытаемся получить страну(country), если нет, то возвращаем None
        if entity['type'] == 'YANDEX.GEO':
            # возвращаем None, если не нашли сущности с типом YANDEX.GEO
            return entity['value'].get('country', None)

def get_first_name(req):
    # перебираем сущности
    for entity in req['request']['nlu']['entities']:
        # находим сущность с типом 'YANDEX.FIO'
        if entity['type'] == 'YANDEX.FIO':
            # Если есть сущность с ключом 'first_name', то возвращаем её значение.
            # Во всех остальных случаях возвращаем None.
            return entity['value'].get('first_name', None)


def help_needed(req, res):
    if req['request']['original_utterance'] == 'Помощь':
        res["response"][
            "text"
        ] = "Эта игра про угадывание города! Алиса спрашивает  имя пользователя и просит ввести город, картинка которого впоследствии будет выведена пользователю!"
        return True

def has_needed(req, res):
    if req['request']['original_utterance'] == 'Помощь':
        res["response"][
            "text"
        ] = "Эта игра про угадывание города! Алиса спрашивает  имя пользователя и просит ввести город, картинка которого впоследствии будет выведена пользователю!"
        return True

def url_redirect(req, res):
    if req['request']['original_utterance'] == 'Покажи город на карте':
        res["response"][
            "text"
        ] = "Рада, что ты вернулся! Продолжаем?"
        res['response']['buttons'] = [
            {
                'title': 'Да',
                'hide': True
            },
            {
                'title': 'Нет',
                'hide': True
            },
            {"title": "Помощь", "hide": True}
        ]
        return True

def has_city_answer(user_id, city):
    return city in sessionStorage[user_id]['guessed_cities']


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
