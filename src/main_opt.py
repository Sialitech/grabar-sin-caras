import os
import cv2
import time
from datetime import datetime
import numpy as np
import json
import logging
from pathlib import Path
import requests
from concurrent.futures import ThreadPoolExecutor
import subprocess
from requests.exceptions import ChunkedEncodingError
from model import Model  # Asegúrate de importar el modelo

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("OptimizedRecorder")

class OptimizedVideoRecorder:
    def __init__(self, cfg_path="../cfgs/cfg.json", video_duration_minutes=1, fixed_fps=30):
        """
        Inicializa el grabador de video optimizado.
        
        Args:
            cfg_path (str): Ruta al archivo de configuración.
            video_duration_minutes (int): Duración de cada video en minutos.
            fixed_fps (int): FPS fijo para los videos guardados.
        """
        self.video_duration = video_duration_minutes * 60  # Convertir minutos a segundos
        self.fixed_fps = fixed_fps
        self.cfg_path = cfg_path
        self.stop_event = False

        # Cargar configuración
        with open(cfg_path, "r") as f:
            self.cfg = json.load(f)

        # Validar configuración
        if "cameras" not in self.cfg or not isinstance(self.cfg["cameras"], list):
            raise ValueError("La configuración debe contener una lista de cámaras bajo la clave 'cameras'.")

        # Inicializar el modelo
        self.model = Model("http://api-yolo:3002", cfg_path)

    def load_cameras_and_models(self):
        logger.info("Cargando cámaras y modelos...")
        self.model.load_cameras_and_models()
        self.model.start_process()

    def record_camera(self, camera_name, output_dir):
        """
        Graba el video de una cámara específica y guarda directamente al archivo.

        Args:
            camera_name (str): Nombre de la cámara.
            output_dir (Path): Directorio de salida para guardar el video.
        """
        logger.info(f"Iniciando grabación para la cámara: {camera_name}")
        try:
            video_path = output_dir / f"{camera_name}.mp4"
            url = f"{self.model.uri}/stream"
            params = {"camera_name": camera_name, "processed": False}

            response = requests.get(url, params=params, stream=True, timeout=10)
            response.raise_for_status()

            buffer = b""
            frame_count = 0
            start_time = time.time()
            writer = None

            for chunk in response.iter_content(chunk_size=8192):
                if self.stop_event:
                    break

                if not chunk:
                    logger.error(f"Error: Chunk vacío recibido para la cámara {camera_name}.")
                    break

                buffer += chunk
                while b"\xff\xd9" in buffer:
                    start = buffer.find(b"\xff\xd8")
                    end = buffer.find(b"\xff\xd9") + 2

                    if start != -1 and end > start:
                        frame_data = buffer[start:end]
                        buffer = buffer[end:]

                        frame = cv2.imdecode(np.frombuffer(frame_data, np.uint8), cv2.IMREAD_COLOR)
                        if frame is not None:
                            if writer is None:
                                height, width = frame.shape[:2]
                                writer = cv2.VideoWriter(
                                    str(video_path),
                                    cv2.VideoWriter_fourcc(*"mp4v"),
                                    self.fixed_fps,
                                    (width, height)
                                )

                            writer.write(frame)
                            frame_count += 1

                            if frame_count % 30 == 0:
                                logger.info(f"{camera_name}: {frame_count} frames capturados.")

                elapsed_time = time.time() - start_time
                if elapsed_time >= self.video_duration:
                    logger.info(f"{camera_name}: Tiempo límite alcanzado ({elapsed_time:.2f}s). Deteniendo grabación.")
                    break

            if writer:
                writer.release()

            average_fps = frame_count / (time.time() - start_time)
            logger.info(f"{camera_name}: Grabación finalizada. FPS promedio: {average_fps:.2f}")

            self.adjust_video_fps(video_path, average_fps)

        except ChunkedEncodingError as e:
            logger.error(f"Error de codificación de chunk en la cámara {camera_name}: {e}")
        except Exception as e:
            logger.error(f"Error en la grabación de la cámara {camera_name}: {e}")

    def adjust_video_fps(self, video_path, target_fps):
        try:
            temp_path = str(video_path).replace(".mp4", "_temp.mp4")
            command = [
                "ffmpeg", "-i", str(video_path), "-filter:v", f"fps=fps={target_fps}",
                "-c:a", "copy", temp_path
            ]
            # Redirigir la salida a DEVNULL para suprimir los mensajes
            subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            os.replace(temp_path, video_path)
            logger.info(f"Video de {video_path} ajustado a {target_fps:.2f} FPS.")
        except subprocess.CalledProcessError as e:
            logger.error(f"Error al ajustar FPS del video {video_path}: {e}")

    def record_all(self):
        """
        Graba videos de todas las cámaras simultáneamente utilizando hilos.
        """
        self.load_cameras_and_models()

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path("../files") / timestamp
        output_dir.mkdir(parents=True, exist_ok=True)

        logger.info("Iniciando grabación para todas las cámaras...")

        self.stop_event = False
        with ThreadPoolExecutor(max_workers=len(self.cfg["cameras"])) as executor:
            futures = [
                executor.submit(self.record_camera, camera["name"], output_dir)
                for camera in self.cfg["cameras"]
            ]

            # Esperar a que todos los procesos terminen
            for future in futures:
                future.result()

        logger.info("Grabación completada para todas las cámaras.")

    def stop(self):
        """Detiene el proceso de grabación."""
        self.stop_event = True
        logger.info("Grabación detenida.")

if __name__ == "__main__":
    recorder = OptimizedVideoRecorder(video_duration_minutes=1, fixed_fps=30)
    try:
        recorder.record_all()
    except KeyboardInterrupt:
        recorder.stop()
