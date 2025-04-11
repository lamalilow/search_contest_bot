import os
import io
from PIL import Image
from config import logger

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def save_file(file_path, file_name):
    with open(os.path.join(UPLOAD_FOLDER, file_name), 'wb') as new_file:
        new_file.write(file_path.read())

def compress_and_save_image(source_path, target_path, max_size=(1200, 1200), quality=85):
    """
    Сжимает изображение и сохраняет его с указанным качеством.
    
    Args:
        source_path (str): Путь к исходному изображению
        target_path (str): Путь для сохранения сжатого изображения
        max_size (tuple): Максимальный размер изображения (ширина, высота)
        quality (int): Качество изображения (1-95), для JPEG и подобных форматов
    
    Returns:
        bool: True если операция выполнена успешно, False в случае ошибки
    """
    try:
        # Получаем расширение файла
        file_ext = os.path.splitext(target_path)[1].lower()
        
        # Открываем изображение
        with Image.open(source_path) as img:
            # Получаем размеры изображения
            width, height = img.size
            logger.info(f"Исходные размеры изображения: {width}x{height}")
            
            # Изменяем размер изображения, если он превышает максимальный
            if width > max_size[0] or height > max_size[1]:
                # Вычисляем соотношение сторон для сохранения пропорций
                ratio = min(max_size[0] / width, max_size[1] / height)
                new_size = (int(width * ratio), int(height * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
                logger.info(f"Новые размеры изображения после изменения: {new_size[0]}x{new_size[1]}")
            
            # Сохраняем изображение с указанным качеством
            if file_ext in ['.jpg', '.jpeg']:
                img.save(target_path, 'JPEG', quality=quality, optimize=True)
            elif file_ext == '.png':
                img.save(target_path, 'PNG', optimize=True)
            else:
                # Для других форматов просто сохраняем
                img.save(target_path)
            
            logger.info(f"Изображение успешно сжато и сохранено: {target_path}")
            return True
    except Exception as e:
        logger.error(f"Ошибка при сжатии изображения: {str(e)}")
        return False