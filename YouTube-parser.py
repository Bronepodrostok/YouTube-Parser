import socketserver
import json
import traceback
import config
from googleapiclient.discovery import build

# Конфиг сокет-сервера
HOST = "127.0.0.1"  
PORT = 65433  

# Создание объекта YouTube Data API
youtube = build('youtube', 'v3', developerKey=config.ACCESS_TOKEN)

def recvall(sock):
    """Функция для получения всего сообщения целиком из сокета
    Args:
        sock (socket.socket): сокет
    Returns:
        bytes: Цельное сообщение из сокета
    """
    BUFF_SIZE = 4096  # Размер буфера для чтения данных
    data = b""
    while True:
        part = sock.recv(BUFF_SIZE)
        data += part
        if len(part) < BUFF_SIZE:
            break  # Если полученное сообщение меньше размера буфера, значит, все данные получены
    return data

def getChannelID(channel_url):
    """Функция получения ID канала
    Args:
        channel_url (str): url канала
    Returns:
        str: id канала
    """
    channel_name = channel_url.split('/')[-1] #Откидываем лишнее
    search_response = youtube.search().list(
        q=channel_name,
        type='channel',
        part='id'
    ).execute() #Хаваем инфу по названию канала
    channel_id =search_response['items'][0]['id']['channelId'] #Хаваем id из названия канала
    return  {'channel_id': channel_id}


def getChannelSubscribers(channel_id):
    """Функция получения количества подписчиков канала
    Args:
        channel_id (str): ID канала
    Returns:
        int: Число подписчиков
    """
    response = youtube.channels().list(
        part='statistics',
        id=channel_id
    ).execute() #Хаваем стату по id канала
    subscribers = int(response['items'][0]['statistics']['subscriberCount'])
    return {'subscribers': subscribers}


def getChannelVideos(channel_id, count=10):
    """Получение информации о последних видео канала
    Args:
        channel_id (str): ID канала
        count (int, optional): Количество последних видео, которые нужно получить. По умолчанию 10.
    Returns:
        list: Список словарей с информацией о видео, ключи: title, description, views, likes, comments
    """
    response = youtube.search().list(
        part='snippet',
        channelId=channel_id,
        maxResults=count,
        order='date',
        type='video'
    ).execute()
    
    video_data = []
    for item in response['items']:
        video_id = item['id']['videoId']
        video_info = youtube.videos().list(
            part='statistics',
            id=video_id
        ).execute()
        
        video_data.append({
            'title': item['snippet']['title'],
            'description': item['snippet']['description'],
            'views': int(video_info['items'][0]['statistics'].get('viewCount', 0)),
            'likes': int(video_info['items'][0]['statistics'].get('likeCount', 0)),
            'comments': int(video_info['items'][0]['statistics'].get('commentCount', 0))
        })
    return {'videos': video_data}

class MyTCPHandler(socketserver.BaseRequestHandler):
    """Класс сокет-сервера
    Args:
        socketserver (_type_): Родительский класс из библиотеки
    """

    def handle(self):
        """Обработчик соединения
        """
        # Читаем реквест целиком
        task = dict(json.loads(recvall(self.request)))

        # По умолчанию отправляем ошибку
        res = {"type": "error", "data": {"error": "method not found"}}
        try:
            # Разбор вариантов
            if task["method"] == "channel":
                # Меняем тип колбека на успешный
                res["type"] = "success"
                # Вызываем нужную функцию
                res["data"] = getChannelID(task["channel_url"])
            elif task["method"] == "subs":
                res["type"] = "success"
                res["data"] = getChannelSubscribers(task["channel_id"])
            elif task["method"] == "videos":
                res["type"] = "success"
                res["data"] = getChannelVideos(task["channel_id"], int(task.get("count", 10)))

        except KeyError:
            res = {"type": "error", "data":{"error":"Wrong args"}}
        except Exception as e:
            res = {"type": "error", "data":{"error": traceback.format_exc()}}
        # Отправляем результат
        self.request.sendall(str.encode(json.dumps(res)))


# Поднимаем сокет-сервер
if __name__ == "__main__":
    with socketserver.TCPServer((HOST, PORT), MyTCPHandler) as server:
        server.serve_forever()
