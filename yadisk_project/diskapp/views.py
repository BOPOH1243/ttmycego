# diskapp/views.py
import io
import zipfile
import requests
from typing import Any, Dict, List, Optional
from django.shortcuts import render, redirect
from django.http import HttpRequest, HttpResponse, StreamingHttpResponse
from django.core.cache import cache
from django.urls import reverse
from .forms import PublicKeyForm

YANDEX_API_BASE_URL = "https://cloud-api.yandex.net/v1/disk/public/resources"
CACHE_TIMEOUT = 300  # 5 минут


def get_file_list(public_key: str, path: Optional[str] = None) -> Dict[str, Any]:
    """
    Получает список файлов и папок по публичной ссылке с Яндекс.Диска.
    
    :param public_key: публичная ссылка Яндекс.Диска
    :param path: путь внутри публичного ресурса (если нужен)
    :return: словарь с данными из API
    """
    params = {"public_key": public_key}
    if path:
        params["path"] = path
    response = requests.get(YANDEX_API_BASE_URL, params=params)
    response.raise_for_status()
    return response.json()


def index(request: HttpRequest) -> HttpResponse:
    """
    Отображает форму для ввода публичной ссылки.
    """
    if request.method == "POST":
        form = PublicKeyForm(request.POST)
        if form.is_valid():
            public_key = form.cleaned_data["public_key"]
            # Сохраним public_key в сессии для дальнейшего использования
            request.session["public_key"] = public_key
            return redirect(reverse("diskapp:file_list"))
    else:
        form = PublicKeyForm()
    return render(request, "diskapp/index.html", {"form": form})


def file_list(request: HttpRequest) -> HttpResponse:
    """
    Отображает список файлов с возможностью фильтрации.
    Использует кэш для сохранения результата запроса.
    """
    public_key: Optional[str] = request.session.get("public_key")
    if not public_key:
        return redirect(reverse("diskapp:index"))
    
    filter_type: Optional[str] = request.GET.get("filter")
    cache_key = f"file_list_{public_key}"
    data = cache.get(cache_key)
    if not data:
        try:
            data = get_file_list(public_key)
            cache.set(cache_key, data, CACHE_TIMEOUT)
        except requests.HTTPError as e:
            return HttpResponse(f"Ошибка получения списка файлов: {str(e)}", status=500)
    
    items: List[Dict[str, Any]] = data.get("_embedded", {}).get("items", [])

    # Фильтрация по типу файла (например, изображения или документы)
    if filter_type:
        if filter_type == "images":
            allowed_ext = (".jpg", ".jpeg", ".png", ".gif", ".bmp")
        elif filter_type == "documents":
            allowed_ext = (".pdf", ".doc", ".docx", ".txt")
        else:
            allowed_ext = None

        if allowed_ext:
            items = [item for item in items if any(item.get("name", "").lower().endswith(ext) for ext in allowed_ext)]
    
    return render(request, "diskapp/file_list.html", {"items": items, "public_key": public_key})


def download_files(request: HttpRequest) -> HttpResponse:
    """
    Скачивание выбранных пользователем файлов.
    Если выбран один файл – скачивается напрямую, если несколько – архивируется в ZIP.
    """
    public_key: Optional[str] = request.session.get("public_key")
    if request.method != "POST" or not public_key:
        return redirect(reverse("diskapp:index"))
    
    file_paths: List[str] = request.POST.getlist("file_paths")
    if not file_paths:
        return HttpResponse("Не выбраны файлы для скачивания", status=400)
    
    # Если выбран один файл – можно сделать прямой редирект к ссылке скачивания,
    # но здесь реализуем общий случай (для одного и нескольких файлов) с архивированием.
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for path in file_paths:
            try:
                # Получаем ссылку для скачивания файла
                download_link_response = requests.get(
                    f"{YANDEX_API_BASE_URL}/download",
                    params={"public_key": public_key, "path": path}
                )
                download_link_response.raise_for_status()
                download_data = download_link_response.json()
                href = download_data.get("href")
                if not href:
                    continue
                file_response = requests.get(href)
                file_response.raise_for_status()
                # Добавляем файл в ZIP (используем имя файла из пути)
                filename = path.split("/")[-1]
                zip_file.writestr(filename, file_response.content)
            except requests.HTTPError:
                continue  # Можно логировать ошибку для отдельного файла
    zip_buffer.seek(0)
    response = StreamingHttpResponse(
        zip_buffer,
        content_type="application/zip"
    )
    response["Content-Disposition"] = 'attachment; filename="files.zip"'
    return response
