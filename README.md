# Yandex.Disk Downloader

**Описание проекта:**

Это Django-приложение позволяет взаимодействовать с API Яндекс.Диска по публичной ссылке. Проект предоставляет веб-интерфейс для:
- Просмотра списка файлов и папок с возможностью навигации по директориям и подпапкам.
- Фильтрации файлов по типу (например, изображения или документы).
- Выбора отдельных файлов или целых папок для скачивания. При скачивании выбранные ресурсы архивируются в ZIP с сохранением структуры директорий.

**Как работает:**

1. **Начало работы:**  
   Пользователь переходит по пути `/` и видит форму для ввода публичной ссылки Яндекс.Диска.

2. **Навигация:**  
   После ввода ссылки приложение выводит список файлов и папок. Пользователь может переходить в папки, возвращаться на уровень выше и применять фильтры для удобства поиска.

3. **Скачивание:**  
   Выбирая нужные файлы и/или папки, пользователь может скачать их в виде ZIP-архива, где содержится вся выбранная структура.

**Запуск проекта:**

1. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```

2. Примените миграции (если требуется):
   ```bash
   python manage.py migrate
   ```

3. Запустите сервер разработки:
   ```bash
   python manage.py runserver
   ```

4. Откройте браузер и перейдите по адресу: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)

---

