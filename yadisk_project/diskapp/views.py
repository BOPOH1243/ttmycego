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
    Получает информацию о ресурсе (файл или папка) или список файлов и папок по публичной ссылке с Яндекс.Диска.
    
    :param public_key: публичная ссылка Яндекс.Диска
    :param path: путь внутри публичного ресурса (если указан)
    :return: словарь с данными из API
    """
    params = {"public_key": public_key}
    if path:
        params["path"] = path
    response = requests.get(YANDEX_API_BASE_URL, params=params)
    response.raise_for_status()
    return response.json()

def add_resource_to_zip(public_key: str, resource_path: str, zip_file: zipfile.ZipFile, folder_prefix: str = "") -> None:
    """
    Рекурсивно добавляет ресурс (файл или папку) в архив.
    
    :param public_key: публичная ссылка Яндекс.Диска
    :param resource_path: путь к ресурсу (файл или папка)
    :param zip_file: объект архива
    :param folder_prefix: префикс для сохранения структуры папок в архиве
    """
    resource_info = get_file_list(public_key, path=resource_path)
    resource_type = resource_info.get("type")
    if resource_type == "file":
        # Получаем ссылку для скачивания файла
        download_link_response = requests.get(
            f"{YANDEX_API_BASE_URL}/download",
            params={"public_key": public_key, "path": resource_path}
        )
        download_link_response.raise_for_status()
        download_data = download_link_response.json()
        href = download_data.get("href")
        if href:
            file_response = requests.get(href)
            file_response.raise_for_status()
            filename = resource_info.get("name") or resource_path.split("/")[-1]
            zip_file.writestr(folder_prefix + filename, file_response.content)
    elif resource_type == "dir":
        # Получаем имя папки и формируем новый префикс
        folder_name = resource_info.get("name") or resource_path.split("/")[-1]
        new_prefix = folder_prefix + folder_name + "/"
        # Добавляем запись о папке (для пустых директорий)
        zip_file.writestr(new_prefix, "")
        # Рекурсивно обходим содержимое папки
        items = resource_info.get("_embedded", {}).get("items", [])
        for item in items:
            item_path = item.get("path")
            if item_path:
                add_resource_to_zip(public_key, item_path, zip_file, folder_prefix=new_prefix)

def index(request: HttpRequest) -> HttpResponse:
    """
    Отображает форму для ввода публичной ссылки.
    """
    if request.method == "POST":
        form = PublicKeyForm(request.POST)
        if form.is_valid():
            public_key = form.cleaned_data["public_key"]
            request.session["public_key"] = public_key
            return redirect(reverse("diskapp:file_list"))
    else:
        form = PublicKeyForm()
    return render(request, "diskapp/index.html", {"form": form})

def file_list(request: HttpRequest) -> HttpResponse:
    """
    Отображает список файлов и папок с возможностью фильтрации, навигации по директориям и выбора для скачивания.
    """
    public_key: Optional[str] = request.session.get("public_key")
    if not public_key:
        return redirect(reverse("diskapp:index"))
    
    filter_type: Optional[str] = request.GET.get("filter")
    current_path: str = request.GET.get("path", "")
    cache_key = f"file_list_{public_key}_{current_path}"
    data = cache.get(cache_key)
    if not data:
        try:
            data = get_file_list(public_key, path=current_path if current_path else None)
            cache.set(cache_key, data, CACHE_TIMEOUT)
        except requests.HTTPError as e:
            return HttpResponse(f"Ошибка получения списка файлов: {str(e)}", status=500)
    
    items: List[Dict[str, Any]] = data.get("_embedded", {}).get("items", [])
    
    # Применяем фильтрацию по типу файла, если задан фильтр
    if filter_type:
        if filter_type == "images":
            allowed_ext = (".jpg", ".jpeg", ".png", ".gif", ".bmp")
        elif filter_type == "documents":
            allowed_ext = (".pdf", ".doc", ".docx", ".txt")
        else:
            allowed_ext = None
        if allowed_ext:
            items = [item for item in items if any(item.get("name", "").lower().endswith(ext) for ext in allowed_ext)]
    
    # Вычисление пути для перехода на уровень вверх
    parent_path: Optional[str] = None
    if current_path:
        if "/" in current_path:
            parent_path = current_path.rsplit("/", 1)[0]
        else:
            parent_path = ""
    
    return render(request, "diskapp/file_list.html", {
        "items": items,
        "public_key": public_key,
        "current_path": current_path,
        "parent_path": parent_path,
        "filter": filter_type or ""
    })

def download_files(request: HttpRequest) -> HttpResponse:
    """
    Скачивание выбранных пользователем файлов и папок.
    Если выбрано несколько ресурсов, они архивируются в ZIP.
    """
    public_key: Optional[str] = request.session.get("public_key")
    if request.method != "POST" or not public_key:
        return redirect(reverse("diskapp:index"))
    
    resource_paths: List[str] = request.POST.getlist("file_paths")
    if not resource_paths:
        return HttpResponse("Не выбраны файлы для скачивания", status=400)
    
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for path in resource_paths:
            try:
                add_resource_to_zip(public_key, path, zip_file)
            except requests.HTTPError:
                continue  # Можно добавить логирование ошибок для отдельных ресурсов
    
    zip_buffer.seek(0)
    response = StreamingHttpResponse(
        zip_buffer,
        content_type="application/zip"
    )
    response["Content-Disposition"] = 'attachment; filename="resources.zip"'
    return response
