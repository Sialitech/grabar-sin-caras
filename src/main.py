import os
import cv2
import time
from datetime import datetime
import numpy as np
from model import Model
import json
import logging
from pathlib import Path
import requests
import threading
import concurrent.futures
import subprocess

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def validate_config(cfg):
    """Valida que la configuración cargada sea correcta."""
    required_keys = ["cameras"]
    for key in required_keys:
        if key not in cfg:
            raise ValueError(f"La configuración está incompleta. Falta la clave: {key}")

class VideoRecorder:
    def __init__(self, cfg_path="../cfgs/cfg.json", video_duration_minutes=1, fixed_fps=30):
        self.model = Model("http://api-yolo:3002", cfg_path)
        self.video_duration = video_duration_minutes * 60
        self.target_fps = int(fixed_fps)
        self.cfg_path = cfg_path
        self.stop_event = threading.Event()

        with open(cfg_path, 'r') as f:
            self.cfg = json.load(f)
        validate_config(self.cfg)

    def record_camera(self, camera_name):
        try:
            print(f"Iniciando grabación para {camera_name}...")
            frame_data = self.model.get_image(camera_name, processed=False)
            if not frame_data:
                logger.error(f"No se recibieron datos de la cámara {camera_name}.")
                return

            frame = cv2.imdecode(np.frombuffer(frame_data, np.uint8), cv2.IMREAD_COLOR)
            if frame is None:
                logger.error(f"No se pudo decodificar la imagen de la cámara {camera_name}.")
                return

            height, width = frame.shape[:2]
            output_path = self.current_output_dir / f"{camera_name}.mp4"
            writer = cv2.VideoWriter(
                str(output_path),
                cv2.VideoWriter_fourcc(*'mp4v'),
                self.target_fps,
                (width, height)
            )

            print(f"Grabando en {camera_name}, guardando en {output_path}...")
            url = f"{self.model.uri}/stream"
            params = {'camera_name': camera_name, 'processed': False}
            
            with requests.get(url, params=params, stream=True, timeout=self.model.timeout) as response:
                response.raise_for_status()
                buffer = b''
                start_time = time.time()
                frame_count = 0

                while not self.stop_event.is_set():
                    elapsed_time = time.time() - start_time
                    if elapsed_time >= self.video_duration:
                        print(f"{camera_name}: Tiempo límite alcanzado ({elapsed_time:.2f}s). Deteniendo grabación.")
                        break

                    for chunk in response.iter_content(chunk_size=8192):
                        if self.stop_event.is_set():
                            break
                        
                        elapsed_time = time.time() - start_time
                        if elapsed_time >= self.video_duration:
                            print(f"{camera_name}: Tiempo límite alcanzado ({elapsed_time:.2f}s). Deteniendo grabación.")
                            break

                        buffer += chunk
                        while b'\xff\xd9' in buffer:
                            start = buffer.find(b'\xff\xd8')
                            end = buffer.find(b'\xff\xd9') + 2
                            if start != -1:
                                frame_data = buffer[start:end]
                                buffer = buffer[end:]

                                frame = cv2.imdecode(np.frombuffer(frame_data, np.uint8), cv2.IMREAD_COLOR)
                                if frame is not None:
                                    writer.write(frame)
                                    frame_count += 1
                                    if frame_count % 100 == 0:
                                        print(f"{camera_name}: {frame_count} frames capturados")

                writer.release()
                print(f"Finalizada grabación de {camera_name}, total frames: {frame_count}")
                average_fps = frame_count / (time.time() - start_time)
                logger.info(f"{camera_name}: Grabación finalizada. FPS promedio: {average_fps:.2f}")

                # Re-codificar el video para ajustar los FPS
                self.adjust_video_fps(output_path, average_fps)
            
            cv2.destroyAllWindows()
        except Exception as e:
            logger.error(f"Error en la grabación de {camera_name}: {e}")
        finally:
            self.stop_event.set()
            self.model.stop_process()
            print("Proceso finalizado correctamente.")

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
            print(f"Video de {video_path} ajustado a {target_fps:.2f} FPS.")
        except subprocess.CalledProcessError as e:
            logger.error(f"Error al ajustar FPS del video {video_path}: {e}")

    def record(self):
        try:
            print("Iniciando sistema...")
            self.model.load_cameras_and_models()
            self.model.start_process()
            time.sleep(2)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.current_output_dir = Path("../files") / timestamp
            self.current_output_dir.mkdir(parents=True, exist_ok=True)

            self.stop_event.clear()

            with concurrent.futures.ThreadPoolExecutor(max_workers=len(self.cfg['cameras'])) as executor:
                futures = [executor.submit(self.record_camera, camera['name']) for camera in self.cfg['cameras']]
                print(f"Iniciando grabación en {len(futures)} cámaras...")
                concurrent.futures.wait(futures)

            print("Grabación completada correctamente.")
            logger.info("Grabación completada correctamente.")
        except Exception as e:
            logger.error(f"Error general: {e}")
        finally:
            self.stop_event.set()
            self.model.stop_process()
            print("Proceso finalizado correctamente.")

if __name__ == "__main__":
    recorder = VideoRecorder(video_duration_minutes=0.5, fixed_fps=25)
    recorder.record()
    print("Ejecución finalizada.")
