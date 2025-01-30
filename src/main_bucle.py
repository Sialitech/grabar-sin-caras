import os
import cv2
import time
from datetime import datetime
import numpy as np
from model import Model
import json
import logging
from pathlib import Path

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VideoRecorder:
    def __init__(self, cfg_path="../cfgs/cfg.json", video_duration_minutes=1):
        """
        Inicializa el grabador de videos.
        
        Args:
            cfg_path (str): Ruta al archivo de configuración
            video_duration_minutes (int): Duración de cada video en minutos
        """
        self.model = Model("http://api-yolo:3002", cfg_path)
        self.video_duration = video_duration_minutes # * 60  # Convertir minutos a segundos
        self.cfg_path = cfg_path
        self.writers = {}
        self.frame_counts = {}
        self.current_output_dir = None
        self.camera_fps = {}  # Diccionario para almacenar los FPS de cada cámara
        
        # Cargar configuración para obtener información de cámaras
        with open(cfg_path, 'r') as f:
            self.cfg = json.load(f)

    def initialize_recording_session(self):
        """Inicializa una nueva sesión de grabación"""
        # Crear directorio con timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current_output_dir = Path("../files") / timestamp
        self.current_output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Iniciando nueva sesión de grabación en: {self.current_output_dir}")
        
        # Inicializar writers para cada cámara
        self.writers = {}
        self.frame_counts = {}
        self.camera_fps = {}
        self.start_time = time.time()

    def get_camera_fps(self, camera_name):
        """Obtiene los FPS actuales de la cámara desde la API"""
        try:
            status = self.model.check_status()
            return status['cameras'][camera_name]['fps_camera']
        except Exception as e:
            logger.warning(f"Error al obtener FPS de {camera_name}: {e}")
            return 30  # valor por defecto si hay error
            
    def initialize_video_writers(self, first_frames):
        """Inicializa los video writers con el tamaño correcto de los frames"""
        for camera_name, frame_data in first_frames.items():
            frame = cv2.imdecode(np.frombuffer(frame_data, np.uint8), cv2.IMREAD_COLOR)
            height, width = frame.shape[:2]
            
            # Obtener FPS inicial de la API
            fps = self.get_camera_fps(camera_name)
            self.camera_fps[camera_name] = fps
            
            output_path = self.current_output_dir / f"{camera_name}.mp4"
            self.writers[camera_name] = cv2.VideoWriter(
                str(output_path),
                cv2.VideoWriter_fourcc(*'mp4v'),  # Codec compatible con MP4
                fps,
                (width, height)
            )
            self.frame_counts[camera_name] = 0
            logger.info(f"Iniciado writer para {camera_name}: {output_path} con {fps} FPS")
            
    def record(self):
        """Proceso principal de grabación - una sola sesión"""
        try:
            # Cargar cámaras y modelos
            logger.info("Cargando cámaras y modelos...")
            self.model.load_cameras_and_models()
            
            # Iniciar procesamiento
            logger.info("Iniciando procesamiento...")
            self.model.start_process()
            
            # Iniciar sesión de grabación
            self.initialize_recording_session()
            first_frames = {}
            
            # Obtener primer frame de cada cámara
            for camera in self.cfg['cameras']:
                camera_name = camera['name']
                frame_data = self.model.get_image(camera_name, processed=False)
                first_frames[camera_name] = frame_data
            
            # Inicializar video writers
            self.initialize_video_writers(first_frames)
            
            # Loop de grabación por la duración especificada
            while time.time() - self.start_time < self.video_duration:
                for camera in self.cfg['cameras']:
                    camera_name = camera['name']
                    try:
                        frame_data = self.model.get_image(camera_name, processed=False)
                        if camera_name == 'cam4':
                            cv2.imshow(frame_data)
                        self.write_frame(camera_name, frame_data)
                    except Exception as e:
                        logger.error(f"Error al obtener frame de {camera_name}: {e}")
            
            logger.info(f"Grabación completada después de {self.video_duration/60:.1f} minutos")
            
        except KeyboardInterrupt:
            logger.info("Grabación interrumpida por el usuario")
        except Exception as e:
            logger.error(f"Error en el proceso de grabación: {e}")
        finally:
            # Asegurar que se cierren los writers y se detenga el proceso
            self.close_current_writers()
            self.model.stop_process()
            
    def write_frame(self, camera_name, frame_data):
        """Escribe un frame al video correspondiente"""
        frame = cv2.imdecode(np.frombuffer(frame_data, np.uint8), cv2.IMREAD_COLOR)
        if frame is None:
            logger.error(f"Error decodificando frame para {camera_name}")
            return
            
        # Escribir el frame directamente
        self.writers[camera_name].write(frame)
        self.frame_counts[camera_name] += 1
        
    def close_current_writers(self):
        """Cierra los writers actuales"""
        for camera_name, writer in self.writers.items():
            writer.release()
            avg_fps = self.camera_fps.get(camera_name, 30)
            logger.info(f"Video de {camera_name} finalizado con {self.frame_counts[camera_name]} frames (FPS promedio: {avg_fps:.2f})")
        self.writers.clear()
        self.frame_counts.clear()

if __name__ == "__main__":
    # Crear instancia del grabador (1 minuto por video)
    recorder = VideoRecorder(video_duration_minutes=1)
    
    # Iniciar grabación
    recorder.record()
