## Установка
## Рекомендовано устанавливать зависимости с использованием виртуального окружения

_pip install -r wiki_requirements.txt_


## Использование
```bash
python3 six_hanshackes.py "<url1>" "<url2>" <rate_limit>
_
```

### Параметры, к передаче, не рекомендовано превышать 500 запросов в час с IP-адреса. 

- `url1` - первая статья Википедии (полный URL с указанием протокола)
- `url2` - вторая статья Википедии (полный URL)  
- `rate_limit` - максимальное количество запросов к API в минуту

### Примеры

```bash

python3 six_handshackes.py "https://en.wikipedia.org/wiki/American_logistics_in_the_Northern_France_campaign" "https://en.wikipedia.org/wiki/John_C._Raaen_Jr" 20

python3 six_handshackes.py "https://en.wikipedia.org/wiki/Lee_Jae-myung" "https://en.wikipedia.org/wiki/Shivaji" 10

python3 six_handshackes.py "https://en.wikipedia.org/wiki/Sudanese_civil_war_(2023–present" "https://en.wikipedia.org/wiki/Rapid_Support_Forces" 100

```

### Скриншоты работы скрипта

![image](https://github.com/user-attachments/assets/a6475539-730b-4ba9-b33b-0e25cabcc224)

![image](https://github.com/user-attachments/assets/273d7c48-7e94-4583-9c63-226aecc9409b)


python3 six_handshackes.py "https://en.wikipedia.org/wiki/Sudanese_civil_war_(2023–present" "https://en.wikipedia.org/wiki/Rapid_Support_Forces" 100


