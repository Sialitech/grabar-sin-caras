import os
import cv2
import time
from datetime import datetime
import numpy as np
from model import Model
import json
import logging
from pathlib import Path
from collections import deque
import requests
import threading
from queue import Queue
import concurrent.futures

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VideoRecorder:
    def __init__(self, cfg_path="../cfgs/cfg.json", video_duration_minutes=1, fixed_fps=30):
        """
        Inicializa el grabador de videos.
        
        Args:
            cfg_path (str): Ruta al archivo de configuración
            video_duration_minutes (int): Duración de cada video en minutos
            fixed_fps (int): FPS para la reproducción del video final
        """
        self.model = Model("http://api-yolo:3002", cfg_path)
        self.video_duration = video_duration_minutes * 60  # Convertir minutos a segundos
        self.target_fps = int(fixed_fps)  # FPS para la reproducción del video
        self.cfg_path = cfg_path
        self.stop_event = threading.Event()
        
        # Cargar configuración
        with open(cfg_path, 'r') as f:
            self.cfg = json.load(f)

    def record_camera(self, camera_name):
        """Graba el video de una cámara específica en un hilo separado"""
        try:
            # Obtener el primer frame usando get_image para configurar el writer
            frame_data = self.model.get_image(camera_name, processed=False)
            
            if not frame_data:
                logger.error(f"No se recibieron datos de la cámara {camera_name}.")
                return
            
            frame = cv2.imdecode(np.frombuffer(frame_data, np.uint8), cv2.IMREAD_COLOR)
            if frame is None:
                logger.error(f"No se pudo decodificar la imagen de la cámara {camera_name}.")
                return
            
            # Almacenar frames en memoria
            frames = []
            start_time = time.time()
            
            height, width = frame.shape[:2]
            frames.append(frame)
            
            url = f"{self.model.uri}/stream"
            params = {
                'camera_name': camera_name,
                'processed': False
            }
            
            with requests.get(url, params=params, stream=True, timeout=self.model.timeout) as response:
                response.raise_for_status()
                buffer = b''
                
                while not self.stop_event.is_set() and (time.time() - start_time) < self.video_duration:
                    for chunk in response.iter_content(chunk_size=8192):
                        if self.stop_event.is_set():
                            break
                            
                        if chunk:
                            buffer += chunk
                            while b'\xff\xd9' in buffer:
                                start = buffer.find(b'\xff\xd8')
                                end = buffer.find(b'\xff\xd9') + 2
                                if start != -1:
                                    frame_data = buffer[start:end]
                                    buffer = buffer[end:]
                                    
                                    frame = cv2.imdecode(np.frombuffer(frame_data, np.uint8), cv2.IMREAD_COLOR)
                                    if frame is not None:
                                        frames.append(frame)
                                        
                                        if len(frames) % 100 == 0:
                                            logger.info(f"{camera_name}: {len(frames)} frames capturados")

            # Calcular FPS real de captura
            elapsed_time = time.time() - start_time
            actual_fps = len(frames) / elapsed_time
            logger.info(f"{camera_name}: FPS de captura real: {actual_fps:.2f}")

            # Guardar video
            output_path = self.current_output_dir / f"{camera_name}.mp4"
            writer = cv2.VideoWriter(
                str(output_path),
                cv2.VideoWriter_fourcc(*'mp4v'),
                self.target_fps,
                (width, height)
            )
            
            # Escribir frames al video
            for frame in frames:
                writer.write(frame)
            
            writer.release()
            logger.info(f"Video de {camera_name} finalizado con {len(frames)} frames")
            
        except Exception as e:
            logger.error(f"Error en la grabación de {camera_name}: {e}")

    def record(self):
        """Proceso principal de grabación usando hilos"""
        try:
            logger.info("Iniciando sistema...")
            self.model.load_cameras_and_models()
            self.model.start_process()
            time.sleep(2)  # Dar tiempo a que el sistema se inicialice
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.current_output_dir = Path("../files") / timestamp
            self.current_output_dir.mkdir(parents=True, exist_ok=True)
            
            self.stop_event.clear()
            
            logger.info("Preparando hilos de grabación...")
            # Crear y ejecutar hilos para cada cámara
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(self.cfg['cameras'])) as executor:
                # Crear todos los futures primero
                futures = [
                    executor.submit(self.record_camera, camera['name'])
                    for camera in self.cfg['cameras']
                ]
                
                logger.info(f"Iniciando grabación simultánea en {len(futures)} cámaras...")
                # Esperar a que todos los hilos terminen
                concurrent.futures.wait(futures)
            
            logger.info("Grabación completada")
            
        except Exception as e:
            logger.error(f"Error general: {e}")
        finally:
            self.stop_event.set()
            self.model.stop_process()

    def record_camera_2(self, camera_name, total_frames_needed):
        """Graba el video de una cámara específica usando el método alternativo"""
        try:
            url = f"{self.model.uri}/stream"
            params = {
                'camera_name': camera_name,
                'processed': False
            }
            response = requests.get(url, params=params, stream=True, timeout=self.model.timeout)
            
            # Leer el primer frame para configurar el writer
            first_frame = None
            for chunk in response.iter_content(chunk_size=1024):
                if chunk and not self.stop_event.is_set():
                    frame_array = np.frombuffer(chunk, dtype=np.uint8)
                    first_frame = cv2.imdecode(frame_array, cv2.IMREAD_COLOR)
                    if first_frame is not None:
                        break
            
            if first_frame is not None:
                height, width = first_frame.shape[:2]
                output_path = self.current_output_dir / f"{camera_name}.mp4"
                writer = cv2.VideoWriter(
                    str(output_path),
                    cv2.VideoWriter_fourcc(*'mp4v'),
                    self.target_fps,
                    (width, height)
                )
                frame_count = 0
                
                # Escribir el primer frame
                writer.write(first_frame)
                frame_count += 1
                logger.info(f"Iniciado grabación para {camera_name}")

                # Continuar con el stream y grabación
                while not self.stop_event.is_set() and frame_count < total_frames_needed:
                    for chunk in response.iter_content(chunk_size=1024):
                        if self.stop_event.is_set():
                            break
                            
                        if chunk:
                            frame_array = np.frombuffer(chunk, dtype=np.uint8)
                            frame = cv2.imdecode(frame_array, cv2.IMREAD_COLOR)
                            if frame is not None:
                                writer.write(frame)
                                frame_count += 1
                                
                                if frame_count % 30 == 0:
                                    logger.info(f"{camera_name}: {frame_count}/{total_frames_needed} frames")
                                
                                if frame_count >= total_frames_needed:
                                    break
                    
                    if frame_count >= total_frames_needed:
                        break

                writer.release()
                avg_fps = frame_count / self.video_duration
                logger.info(f"Video de {camera_name} finalizado con {frame_count} frames (FPS promedio: {avg_fps:.2f})")
            else:
                logger.error(f"No se pudo obtener el primer frame para {camera_name}")
                
        except Exception as e:
            logger.error(f"Error en la grabación de {camera_name}: {e}")

    def record_2(self):
        """Proceso principal de grabación alternativo usando hilos"""
        try:
            logger.info("Iniciando sistema...")
            self.model.load_cameras_and_models()
            self.model.start_process()
            time.sleep(2)  # Dar tiempo a que el sistema se inicialice
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.current_output_dir = Path("../files") / timestamp
            self.current_output_dir.mkdir(parents=True, exist_ok=True)
            
            total_frames_needed = self.target_fps * self.video_duration
            self.stop_event.clear()
            
            logger.info("Preparando hilos de grabación...")
            # Crear y ejecutar hilos para cada cámara
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(self.cfg['cameras'])) as executor:
                # Crear todos los futures primero
                futures = [
                    executor.submit(self.record_camera_2, camera['name'], total_frames_needed)
                    for camera in self.cfg['cameras']
                ]
                
                logger.info(f"Iniciando grabación simultánea en {len(futures)} cámaras...")
                # Esperar a que todos los hilos terminen
                concurrent.futures.wait(futures)
            
            logger.info("Grabación completada")
            
        except Exception as e:
            logger.error(f"Error general: {e}")
        finally:
            self.stop_event.set()
            self.model.stop_process()

if __name__ == "__main__":
    # Crear instancia del grabador (1 minuto por video, FPS fijo de 20)
    recorder = VideoRecorder(video_duration_minutes=1, fixed_fps=20)
    
    # Iniciar grabación
    recorder.record()
