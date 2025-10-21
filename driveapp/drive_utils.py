from google.oauth2 import service_account
from googleapiclient.discovery import build
from django.conf import settings
from googleapiclient.http import MediaIoBaseDownload
from io import BytesIO
from django.http import JsonResponse
from PIL import Image
import fitz  # PyMuPDF
import re
from django.core.cache import cache
from concurrent.futures import ThreadPoolExecutor
import time
import os
SCOPES = ['https://www.googleapis.com/auth/drive']
SERVICE_ACCOUNT_FILE = settings.GOOGLE_CREDENTIALS_FILE

# Bengali to English digit map
bengali_to_english = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")

def get_drive_service():
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    return build('drive', 'v3', credentials=credentials)

def extract_sort_keys(name):
    # Caches values internally for speed
    parts = name.split("_")
    try:
        first = int(parts[0].translate(bengali_to_english))
    except:
        first = float('inf')
    try:
        third = int(parts[2].translate(bengali_to_english))
    except:
        third = float('inf')
    return (first, third)


def traverse_drive_path(path):
    service = get_drive_service()
    folders = path.split('/') if path else ['মৌজা ম্যাপ ফাইল']

    current_folder_id = None

    for folder_name in folders:
        query = f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}' and trashed=false"
        if current_folder_id:
            query += f" and '{current_folder_id}' in parents"

        results = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        folder_list = results.get('files', [])
        if not folder_list:
            raise Exception(f"Folder '{folder_name}' not found.")

        # Use the first folder match for traversal
        current_folder_id = folder_list[0]['id']

    # Get all items (files, folders, shortcuts) in this folder
    query = f"'{current_folder_id}' in parents and trashed=false"
    results = service.files().list(
        q=query,
        spaces='drive',
        fields='files(id, name, mimeType, shortcutDetails)',
        pageSize=1000
    ).execute()

    folders = []
    files = []

    for item in results.get('files', []):
        mime_type = item['mimeType']

        if mime_type == 'application/vnd.google-apps.folder':
            folders.append(item['name'])

        elif mime_type == 'application/vnd.google-apps.shortcut':
            shortcut = item.get('shortcutDetails', {})
            target_id = shortcut.get('targetId')
            target_mime = shortcut.get('targetMimeType')

            if target_id and target_mime == 'application/vnd.google-apps.folder':
                # 🔁 Get all files inside this shortcut folder
                shortcut_query = f"'{target_id}' in parents and trashed=false"
                shortcut_results = service.files().list(
                    q=shortcut_query,
                    spaces='drive',
                    fields='files(id, name, mimeType)',
                    pageSize=1000
                ).execute()
                for sub_item in shortcut_results.get('files', []):
                    if sub_item['mimeType'] != 'application/vnd.google-apps.folder':
                        files.append({'name': sub_item['name'], 'id': sub_item['id']})

            elif target_id:
                files.append({'name': item['name'], 'id': target_id})

        else:
            files.append({'name': item['name'], 'id': item['id']})

    # 📦 Sort
    files.sort(key=lambda f: extract_sort_keys(f['name']))

    if folders:
        return {'folders': folders}
    else:
        return {'files': files}

def get_full_path(service, file):
    """Recursively get full path of a file/folder."""
    path_parts = [file['name']]
    parent_ids = file.get('parents', [])
    visited = set()

    while parent_ids:
        parent_id = parent_ids[0]

        if parent_id in visited:
            break
        visited.add(parent_id)

        parent = service.files().get(
            fileId=parent_id,
            fields='id, name, parents'
        ).execute()

        path_parts.insert(0, parent['name'])

        # stop if this parent has no more parents
        if not parent.get('parents'):
            break

        parent_ids = parent.get('parents', [])

    return "/".join(path_parts)


def search_file_by_name(file_name):
    service = get_drive_service()
    safe_name = file_name.replace("'", "\\'")
    
    # Filter only JPG or PDF files (case-insensitive)
    query = (
        f"(name contains '{safe_name}') and "
        f"(mimeType='application/pdf' or mimeType='image/jpeg' or mimeType='image/jpg') and "
        f"trashed = false"
    )

    results = service.files().list(
        q=query,
        spaces='drive',
        fields='files(id, name, mimeType, parents)',
        pageSize=10,        # Limit results to 10
        orderBy='modifiedTime desc'  # Optional: sort by most recent
    ).execute()

    files = results.get('files', [])
    
    # Add full path for each file
    for file in files:
        file['fullPath'] = get_full_path(service, file)

    return files

def search_file_by_name_with_timeout(file_name, timeout=5):
    """
    Search for a file with timeout protection
    """
    import signal
    
    def timeout_handler(signum, frame):
        raise TimeoutError(f"Search timeout for file: {file_name}")
    
    # Set up timeout
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(timeout)
    
    try:
        result = search_file_by_name(file_name)
        signal.alarm(0)  # Cancel timeout
        return result
    except TimeoutError:
        signal.alarm(0)  # Cancel timeout
        raise
    except Exception as e:
        signal.alarm(0)  # Cancel timeout
        raise e
    
    
def search_file_by_name_with_cache(file_name):
    """
    Search for a file with caching
    """
    # Check cache first
    cache_key = f"file_search_{file_name}"
    cached_result = cache.get(cache_key)
    if cached_result:
        return cached_result
    
    try:
        result = search_file_by_name(file_name)
        # Cache successful results for 10 minutes
        if result:
            cache.set(cache_key, result, 600)
        return result
    except Exception as e:
        # Cache failed results for 2 minutes to avoid repeated failures
        cache.set(cache_key, [], 120)
        raise e


def batch_search_files(file_names, max_workers=3):
    """
    Search multiple files in parallel with caching and error handling
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from django.core.cache import cache
    
    results = {}
    failed_files = []
    
    # Remove duplicates while preserving order
    unique_files = list(dict.fromkeys(file_names))
    
    # Use ThreadPoolExecutor with limited workers
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks using the cached search function
        future_to_filename = {
            executor.submit(search_file_by_name_with_cache, file_name): file_name 
            for file_name in unique_files
        }
        
        # Collect results with timeout
        for future in as_completed(future_to_filename, timeout=60):
            file_name = future_to_filename[future]
            try:
                files = future.result(timeout=5)
                results[file_name] = files or []
                    
            except Exception as e:
                failed_files.append({
                    'file_name': file_name,
                    'error': str(e)
                })
    
    return {
        'results': results,
        'failed_files': failed_files,
        'total_files': len(unique_files),
        'successful_files': len(results)
    }


def compress_to_jpeg(img, target_kb=200, max_size=(800, 800)):
    img = img.convert("RGB")
    
    # Get original size in bytes to dynamically adjust
    raw_buf = BytesIO()
    img.save(raw_buf, format='JPEG')
    original_kb = raw_buf.tell() / 1024

    # 🔁 Adjust compression settings based on original size
    if original_kb > 4000:  # If image > 4MB
        max_size = (600, 600)
        target_kb = min(target_kb, 150)
        start_quality = 70
    elif original_kb > 2000:  # If image > 2MB
        max_size = (700, 700)
        target_kb = min(target_kb, 180)
        start_quality = 75
    else:
        start_quality = 85

    img.thumbnail(max_size, Image.LANCZOS)

    output = BytesIO()
    quality = start_quality

    while quality >= 10:
        output.seek(0)
        output.truncate()
        img.save(output, format='JPEG', quality=quality, optimize=True)
        size_kb = output.tell() / 1024
        if size_kb <= target_kb:
            break
        quality -= 5

    output.seek(0)
    return output



def download_file_by_id(file_id, compress=True, target_kb=200):
    service = get_drive_service()

    # Get metadata with shortcut details
    metadata = service.files().get(
        fileId=file_id,
        fields='name, mimeType, shortcutDetails'
    ).execute()

    file_name = metadata['name']
    ext = os.path.splitext(file_name)[1].lower()
    mime_type = metadata['mimeType']

    # Handle shortcut pointing to actual file
    if mime_type == 'application/vnd.google-apps.shortcut':
        target_id = metadata.get('shortcutDetails', {}).get('targetId')
        file_id = target_id
        mime_type = metadata.get('shortcutDetails', {}).get('targetMimeType', mime_type)

    # Download file content
    request_drive = service.files().get_media(fileId=file_id)
    raw = BytesIO()
    downloader = MediaIoBaseDownload(raw, request_drive)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    raw.seek(0)

    # 🔥 EXTENSION-BASED COMPRESSION ONLY
    if compress:
        try:
            if ext in ['.jpg', '.jpeg', '.png']:
                raw.seek(0)
                image = Image.open(raw)
                image.load()
                compressed = compress_to_jpeg(image, target_kb=target_kb)
                return compressed, 'image/jpeg', f"preview_{file_name}.jpg"

            elif ext == '.pdf':
                doc = fitz.open(stream=raw.getvalue(), filetype="pdf")
                if len(doc) == 0:
                    raise Exception("Empty PDF")
                page = doc.load_page(0)
                pix = page.get_pixmap(dpi=100)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                compressed = compress_to_jpeg(img, target_kb=target_kb)
                return compressed, 'image/jpeg', f"preview_{file_name}.jpg"

        except Exception as e:
            print(f"[❌ Compression failed] {str(e)}")

    # Fallback to original
    raw.seek(0)
    return raw, mime_type, file_name
def convert_file_format(stream, source_mime, target_format):
    output = BytesIO()

    if target_format == "jpg":
        if source_mime == "application/pdf":
            doc = fitz.open(stream=stream.getvalue(), filetype="pdf")
            page = doc.load_page(0)
            pix = page.get_pixmap(dpi=150)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        else:
            img = Image.open(stream)

        img = img.convert("RGB")
        img.save(output, format="JPEG")
        output.seek(0)
        return output, "image/jpeg", "converted.jpg"

    elif target_format == "pdf":
        if source_mime == "application/pdf":
            return stream, "application/pdf", "original.pdf"

        img = Image.open(stream).convert("RGB")
        img.save(output, format="PDF")
        output.seek(0)
        return output, "application/pdf", "converted.pdf"

    raise ValueError("Unsupported format")