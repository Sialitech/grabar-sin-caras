# Sistema de Grabación de Video

Este proyecto es un sistema de grabación de video que utiliza múltiples cámaras para capturar y almacenar videos en formato MP4.

## Requisitos

- Python 3.x
- OpenCV
- Requests
- FFMPEG

## Instalación

1. Clona este repositorio en tu máquina local.
2. Instala las dependencias necesarias ejecutando:
   ```bash
   pip install -r requirements.txt
   ```


## Uso

1. Configura las cámaras en el archivo `cfgs/cfg.json`.
2. Los videos grabados se almacenarán en el directorio `files`.
3. La duración de cada video se puede ajustar en el script `src/main.py`.
4. Al levantar el Docker, el sistema se ejecuta automáticamente en bucle.
5. El script `run_recording.sh` ejecuta la grabación una sola vez.

## Configuración

- El archivo `cfgs/cfg.json` contiene la configuración de las cámaras. Asegúrate de que las URLs y otros parámetros estén correctamente configurados.
- Puedes ajustar la duración de la grabación y los FPS en el script `src/main.py`.
- Es necesario tener un modelo de pose configurado para el borrado de caras.

## Problemas Comunes

- **Error de codificación de video**: Asegúrate de que el codec especificado esté soportado por tu instalación de OpenCV.
- **Permisos de archivo**: Si encuentras problemas de permisos, asegúrate de que los directorios y archivos tengan los permisos adecuados.

## Contribuciones

Las contribuciones son bienvenidas. Por favor, abre un issue o un pull request para discutir cambios potenciales.

## Licencia

Este proyecto está bajo la Licencia MIT. Consulta el archivo LICENSE para más detalles.
