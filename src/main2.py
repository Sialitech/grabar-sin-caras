import requests
import cv2
import threading
import time
from model import Model
from datetime import datetime
import os
import logging
import numpy as np
import json

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Leer configuración directamente del archivo JSON
try:
    with open('/cfgs/cfg.json', 'r') as f:
        config = json.load(f)
        cameras = config.get('cameras', [])
        # Obtener FPS del tracker_config, o usar 20 como valor por defecto
        fps = 20
        frame_delay = 1.0 / fps  # Calcular el delay entre frames
        logger.info(f"Cámaras cargadas del archivo de configuración: {[cam['name'] for cam in cameras]}")
        logger.info(f"FPS configurados: {fps}")
except Exception as e:
    logger.error(f"Error al cargar el archivo de configuración: {e}")
    cameras = []
    fps = 20
    frame_delay = 1.0 / fps

# Inicializar el modelo
model = Model("http://api-yolo:3002", "../cfgs/cfg.json")
model.load_cameras_and_models()
model.start_process()
time.sleep(2)

# Configuración de la grabación
dur_min = 15
duration = dur_min * 60 # Duración del video en segundos

# Crear directorio para los videos
current_time = datetime.now()
output_dir = f"../files/{current_time.strftime('%Y-%m-%d_%H-%M-%S')}"
try:
    os.makedirs(output_dir, exist_ok=True)
    logger.info(f"Directorio creado: {output_dir}")
except Exception as e:
    logger.error(f"Error al crear directorio: {e}")

def record_camera(camera_name):
    # Obtener primer frame para configurar el video
    try:
        image_bytes = model.get_image(camera_name, processed=False)
        nparr = np.frombuffer(image_bytes, np.uint8)
        first_frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        height, width = first_frame.shape[:2]
        logger.info(f"Dimensiones del video {camera_name}: {width}x{height}")
    except Exception as e:
        logger.error(f"Error al obtener el primer frame de {camera_name}: {e}")
        return
    
    # Define el codec y crea el objeto VideoWriter
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    output_path = os.path.join(output_dir, f'{camera_name}.avi')
    out = cv2.VideoWriter(output_path, fourcc, 20.0, (width, height))
    
    if not out.isOpened():
        logger.error(f"No se pudo crear el archivo de salida para {camera_name}")
        return
    
    logger.info(f"Iniciando grabación de {camera_name} en {output_path}")
    start_time = time.time()
    frames_written = 0
    next_frame_time = start_time
    
    try:
        while int(time.time() - start_time) < duration:
            current_time = time.time()
            
            # # Esperar hasta que sea el momento del siguiente frame
            # if current_time < next_frame_time:
            #     time.sleep(next_frame_time - current_time)
            #     continue
                
            try:
                # Obtener frame usando get_image
                image_bytes = model.get_image(camera_name, processed=False)
                nparr = np.frombuffer(image_bytes, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                
                if frame is not None:
                    out.write(frame)
                    frames_written += 1
                    # Calcular el tiempo para el siguiente frame
                    next_frame_time = start_time + (frames_written + 1) * frame_delay
                else:
                    logger.warning(f"Frame nulo recibido de {camera_name}")
            except Exception as e:
                logger.error(f"Error al obtener frame de {camera_name}: {e}")
                break
            
    except Exception as e:
        logger.error(f"Error durante la grabación de {camera_name}: {e}")
    finally:
        out.release()
        actual_fps = frames_written / (time.time() - start_time)
        logger.info(f"Video de {camera_name} finalizado. Frames escritos: {frames_written}, FPS promedio: {actual_fps:.2f}")

# Crear y empezar un hilo para cada cámara
threads = []
for camera in cameras:
    camera_name = camera.get('name', '')
    if camera_name:
        thread = threading.Thread(target=record_camera, args=(camera_name,))
        threads.append(thread)
        thread.start()
        logger.info(f"Hilo iniciado para {camera_name}")

# Esperar a que todos los hilos terminen
for thread in threads:
    thread.join()

logger.info("Grabación completada en todos los hilos")