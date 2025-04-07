import socket
import threading
import time
import urllib.request
import ssl
from queue import Queue

class ProxyChecker:
    def __init__(self, rotation_interval=150):
        self.proxies = []
        self.working_proxies = []
        self.proxy_queue = Queue()
        self.rotation_interval = rotation_interval
        self.lock = threading.Lock()
        self.check_timeout = 10
        self.running = True

    def fetch_proxies(self):
        """Скачивает список прокси из указанных онлайн-источников."""
        urls = [
            "https://raw.githubusercontent.com/Anonym0usWork1221/Free-Proxies/refs/heads/main/proxy_files/https_proxies.txt",
            "https://raw.githubusercontent.com/dinoz0rg/proxy-list/refs/heads/main/checked_proxies/http.txt"
        ]
        proxies = []
        for url in urls:
            try:
                context = ssl._create_unverified_context()
                with urllib.request.urlopen(url, context=context, timeout=10) as response:
                    proxy_list = response.read().decode('utf-8').strip().split('\n')
                    proxies.extend([proxy.strip() for proxy in proxy_list if proxy.strip()])
            except Exception as e:
                print(f"Ошибка загрузки прокси из {url}: {str(e)}")
        return list(set(proxies))  # Удаляем дубликаты

    def check_proxy(self, proxy):
        try:
            ip, port = proxy.split(':')
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.check_timeout)
            sock.connect((ip, int(port)))

            request = "GET http://www.google.com/ HTTP/1.1\r\nHost: www.google.com\r\n\r\n"
            sock.sendall(request.encode('utf-8'))
            response = sock.recv(4096).decode('utf-8', errors='ignore')
            sock.close()

            return "200 OK" in response
        except Exception:
            return False

    def check_proxy_worker(self):
        while self.running:
            proxy = self.proxy_queue.get()
            if proxy is None:
                self.proxy_queue.task_done()
                break

            if self.check_proxy(proxy):
                with self.lock:
                    if proxy not in self.working_proxies:
                        self.working_proxies.append(proxy)
                        print(f"Найден работающий прокси: {proxy}")
            self.proxy_queue.task_done()

    def start_check_threads(self, num_threads=10):
        threads = []
        for _ in range(num_threads):
            t = threading.Thread(target=self.check_proxy_worker)
            t.daemon = True
            t.start()
            threads.append(t)
        return threads

    def update_proxies(self):
        while self.running:
            new_proxies = self.fetch_proxies()
            if new_proxies:
                with self.lock:
                    self.proxies = new_proxies
                    self.working_proxies.clear()  # Очищаем предыдущие рабочие прокси
                    print(f"Обновлён список прокси: {len(self.proxies)}")
                    
                for proxy in self.proxies:
                    self.proxy_queue.put(proxy)

                # Ждем, пока все прокси проверятся
                self.proxy_queue.join()
                
                # Сохраняем рабочие прокси в файл
                with open('working_proxies.txt', 'w') as f:
                    for proxy in self.working_proxies:
                        f.write(f"{proxy}\n")
                print(f"Сохранено {len(self.working_proxies)} работающих прокси в working_proxies.txt")

            time.sleep(self.rotation_interval)

    def run(self):
        self.start_check_threads()
        self.update_proxies()

    def stop(self):
        self.running = False

if __name__ == '__main__':
    proxy_checker = ProxyChecker(rotation_interval=150)
    try:
        print("Запуск проверки прокси...")
        proxy_checker.run()
    except KeyboardInterrupt:
        proxy_checker.stop()
        print("Остановка проверки прокси...")
