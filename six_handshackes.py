#!/usr/bin/env python3

import requests
import time
import json
import re
from collections import deque
from urllib.parse import quote
import sys
import pickle
import os
from concurrent.futures import ThreadPoolExecutor, as_completed


class ImprovedWikipediaChecker:
    def __init__(self, rate_limit=50, cache_file="wiki_cache.pkl", max_workers=3):
        self.rate_limit = rate_limit
        self.request_count = 0
        self.last_request_reset = time.time()
        self.cache_file = cache_file
        self.max_workers = max_workers
        self.cache = self._load_cache()
        
        # На всякий случай сделал два эндпоинта для русского и английского, хотя в основном тестил на английской вики
        self.api_endpoints = {
            'en': 'https://en.wikipedia.org/api/rest_v1/',
            'ru': 'https://ru.wikipedia.org/api/rest_v1/'
        }
    
    def _load_cache(self):
        """Загрузить кэш из файла"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'rb') as f:
                    return pickle.load(f)
            except:
                pass
        return {}
    
    def _save_cache(self):
        """Сохранить кэш в файл"""
        try:
            with open(self.cache_file, 'wb') as f:
                pickle.dump(self.cache, f)
        except:
            pass
    
    def _rate_limit_check(self):
        """Умная проверка rate limit"""
        current_time = time.time()
        
        if current_time - self.last_request_reset >= 60:
            self.request_count = 0
            self.last_request_reset = current_time
        
        if self.request_count >= self.rate_limit:
            sleep_time = 60 - (current_time - self.last_request_reset) + 1
            print(f"Rate limit ({self.rate_limit}/мин), ожидание {sleep_time:.1f}с...")
            time.sleep(sleep_time)
            self.request_count = 0
            self.last_request_reset = time.time()
        
        self.request_count += 1
    
    def _extract_page_title(self, url):
        """Извлечь название страницы из URL"""
        if '/wiki/' in url:
            return url.split('/wiki/')[-1]
        return url
    
    def _get_language_from_url(self, url):
        """Получить язык из URL"""
        if 'wikipedia.org' in url:
            # Ищем паттерн https://xx.wikipedia.org
            match = re.search(r'https?://([a-z]{2,3})\.wikipedia\.org', url)
            if match:
                return match.group(1)
        return 'en'
    
    def _get_page_links_api(self, page_title, language='en'):
        """Получить ссылки страницы через Wikipedia Action API"""
        cache_key = f"{language}:{page_title}"
        
        # Проверяем кэш
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        self._rate_limit_check()
        
        try:
            # Используем правильный MediaWiki Action API для получения ссылок
            api_url = f"https://{language}.wikipedia.org/w/api.php"
            
            params = {
                'action': 'query',
                'format': 'json',
                'titles': page_title,
                'prop': 'links',
                'pllimit': 'max',  # Максимум ссылок
                'plnamespace': '0'  # Только основное пространство имен (статьи)
            }
            
            headers = {
                'User-Agent': 'WikipediaDegreesChecker/1.0 (Educational Purpose)',
                'Accept': 'application/json'
            }
            
            print(f"Запрос к Action API: {api_url} для {page_title}")
            response = requests.get(api_url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if 'query' in data and 'pages' in data['query']:
                    pages = data['query']['pages']
                    page_data = list(pages.values())[0]  # Берем первую (и единственную) страницу
                    
                    if 'links' in page_data:
                        links = [link['title'] for link in page_data['links']]
                        # Ограничиваем до 100 ссылок для производительности
                        links = links[:100]
                        
                        # Кэшируем результат
                        self.cache[cache_key] = links
                        print(f"Найдено {len(links)} ссылок для {page_title}")
                        return links
                    else:
                        print(f"Нет ссылок на странице {page_title}")
                        return []
            else:
                print(f"API вернул статус {response.status_code} для {page_title}")
            
        except Exception as e:
            print(f"Ошибка API для {page_title}: {e}")
        
        return []
    
    def _bidirectional_bfs(self, start_title, target_title, language='en', max_depth=5):
        """Двунаправленный BFS поиск"""
        if start_title == target_title:
            return [start_title]
        
        # Очереди для прямого и обратного поиска
        forward_queue = deque([(start_title, [start_title])])
        backward_queue = deque([(target_title, [target_title])])
        
        # Множества посещенных узлов
        forward_visited = {start_title: [start_title]}
        backward_visited = {target_title: [target_title]}
        
        level = 0
        
        while forward_queue and backward_queue and level < max_depth:
            level += 1
            print(f"Уровень {level}: forward={len(forward_queue)}, backward={len(backward_queue)}")
            
            # Поиск вперед
            if self._expand_level(forward_queue, forward_visited, backward_visited, language, True):
                return self._reconstruct_path(forward_visited, backward_visited)
            
            # Поиск назад
            if self._expand_level(backward_queue, backward_visited, forward_visited, language, False):
                return self._reconstruct_path(forward_visited, backward_visited)
        
        return None
    
    def _expand_level(self, queue, current_visited, other_visited, language, is_forward):
        """Расширить один уровень поиска"""
        next_level = []
        
        # Ограничиваем количество узлов на уровне для производительности
        level_size = min(len(queue), 50)
        
        for _ in range(level_size):
            if not queue:
                break
                
            current_title, path = queue.popleft()
            
            # Получаем ссылки для текущей страницы
            links = self._get_page_links_api(current_title, language)
            
            for link in links[:30]:  # Ограничиваем до 30 ссылок на страницу
                if link not in current_visited:
                    new_path = path + [link] if is_forward else [link] + path
                    current_visited[link] = new_path
                    next_level.append((link, new_path))
                    
                    # Проверяем пересечение
                    if link in other_visited:
                        return True
        
        # Добавляем следующий уровень в очередь
        queue.extend(next_level)
        return False
    
    def _reconstruct_path(self, forward_visited, backward_visited):
        """Восстановить путь при пересечении"""
        # Находим точку пересечения
        intersection = set(forward_visited.keys()) & set(backward_visited.keys())
        
        if intersection:
            meeting_point = list(intersection)[0]
            forward_path = forward_visited[meeting_point]
            backward_path = backward_visited[meeting_point]
            
            # Объединяем пути (убираем дублирование точки пересечения)
            full_path = forward_path + backward_path[1:][::-1]
            return full_path
        
        return None
    
    def find_path(self, start_url, target_url, max_depth=5):
        """Найти путь между двумя Wikipedia статьями"""
        start_title = self._extract_page_title(start_url)
        target_title = self._extract_page_title(target_url)
        language = self._get_language_from_url(start_url)
        
        print(f"Поиск пути: {start_title} -> {target_title} (язык: {language})")
        
        # Используем двунаправленный BFS
        path = self._bidirectional_bfs(start_title, target_title, language, max_depth)
        
        if path:
            # Конвертируем обратно в URLs
            base_url = f"https://{language}.wikipedia.org/wiki/"
            return [base_url + quote(title) for title in path]
        
        return None
    
    def check_degrees(self, url1, url2):
        """Проверить связь между двумя URL (только в одну сторону для экономии)"""
        print(f"Проверка связи между статьями...")
        
        # Ищем путь в обе стороны параллельно
        with ThreadPoolExecutor(max_workers=2) as executor:
            future1 = executor.submit(self.find_path, url1, url2)
            future2 = executor.submit(self.find_path, url2, url1)
            
            path1to2 = None
            path2to1 = None
            
            for future in as_completed([future1, future2]):
                try:
                    result = future.result()
                    if future == future1:
                        path1to2 = result
                    else:
                        path2to1 = result
                except Exception as e:
                    print(f"Ошибка в потоке: {e}")
        
        # Сохраняем кэш
        self._save_cache()
        
        return path1to2, path2to1
    
    def format_path(self, path):
        """Форматировать путь для вывода"""
        if not path:
            return "Путь не найден за 5 переходов"
        
        formatted = []
        for i, url in enumerate(path):
            title = url.split('/')[-1].replace('_', ' ')
            # Декодируем URL
            try:
                from urllib.parse import unquote
                title = unquote(title)
            except:
                pass
            
            if i == 0 or i == len(path) - 1:
                formatted.append(title)
            else:
                formatted.append(f"[{title}]")
        
        return " => ".join(formatted)


def main():
    if len(sys.argv) != 4:
        print("Использование: python wikipedia_degrees_improved.py <url1> <url2> <rate_limit>")
        print("Пример: python wikipedia_degrees_improved.py 'https://en.wikipedia.org/wiki/Six_degrees_of_separation' 'https://en.wikipedia.org/wiki/American_Broadcasting_Company' 50")
        sys.exit(1)
    
    url1 = sys.argv[1]
    url2 = sys.argv[2]
    
    try:
        rate_limit = int(sys.argv[3])
    except ValueError:
        print("Rate limit должен быть числом")
        sys.exit(1)
    
    checker = ImprovedWikipediaChecker(rate_limit=rate_limit)
    
    print(f"Улучшенная проверка теории 6 рукопожатий")
    print(f"URL1: {url1}")
    print(f"URL2: {url2}")
    print(f"Rate limit: {rate_limit} запросов/мин")
    print(f"Кэш: {len(checker.cache)} записей")
    print("-" * 60)
    
    start_time = time.time()
    
    try:
        path1to2, path2to1 = checker.check_degrees(url1, url2)
        
        elapsed_time = time.time() - start_time
        
        print(f"\nРезультаты (выполнено за {elapsed_time:.1f}с):")
        print(f"url1 => url2: {checker.format_path(path1to2)}")
        print(f"url2 => url1: {checker.format_path(path2to1)}")
        
        if path1to2:
            print(f"Длина пути 1->2: {len(path1to2)} переходов")
        if path2to1:
            print(f"Длина пути 2->1: {len(path2to1)} переходов")
            
    except KeyboardInterrupt:
        print("\nПрервано пользователем")
    except Exception as e:
        print(f"Произошла ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main() 
