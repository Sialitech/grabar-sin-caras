import requests
import json


class Model:
    def __init__(self, uri_device, cfg_path, timeout=200):
        """Initialize the Model class to interact with the specified endpoints in the API.

        Args:
            uri_device (str): Base URL of the API. E.g., "http://api:5001".
            cfg_path (str): Path to the configuration file.
            timeout (int, optional): Timeout for API requests. Defaults to 200.
        """
        self.uri = uri_device
        self.cfg_path = cfg_path
        self.timeout = timeout

    def load_cameras_and_models(self):
        """Load cameras and models given the configuration path."""
        url = f"{self.uri}/load_cameras_and_models"
        response = requests.post(url, params={'cfg_path': self.cfg_path}, timeout=self.timeout)
        if not response.ok:
            raise Exception("Failed to load cameras and models")
        return response.json()

    def start_process(self):
        """Start the process for detection and inference."""
        url = f"{self.uri}/start_process"
        response = requests.post(url, timeout=self.timeout)
        if not response.ok:
            raise Exception("Failed to start the process")
        return response.json()

    def stop_process(self):
        """Stop the process for detection and inference."""
        url = f"{self.uri}/stop_process"
        response = requests.post(url, timeout=self.timeout)
        if not response.ok:
            raise Exception("Failed to stop the process")
        return response.json()

    def check_status(self):
        """Check the status of the process."""
        url = f"{self.uri}/check_status"
        response = requests.get(url, timeout=self.timeout)
        if not response.ok:
            raise Exception("Failed to check the status")
        return response.json()

    def get_results(self):
        """Get the results of the detection and inference process."""
        url = f"{self.uri}/get_results"
        response = requests.get(url, timeout=self.timeout)
        if not response.ok:
            raise Exception("Failed to get the results")
        return response.json()

    def get_image(self, camera_name, processed=True, font_size=1, show_confidence=True, show_id=True, show_speed=True, show_position=True, show_estela=True, show_keypoints=True, show_contours=True, show_only_segmentation=False):
        """Get an image from the specified camera.

        Args:
            camera_name (str): The name of the camera.
            processed (bool): Whether to return the processed image. Defaults to True.
            font_size (float): Font size for any annotations. Defaults to 1.
            show_confidence (bool): Whether to show confidence score of detections. Defaults to True.
            show_id (bool): Whether to show the ID of detections. Defaults to True.
            show_speed (bool): Whether to show the speed of detections. Defaults to True.
            show_position (bool): Whether to show the position of detections. Defaults to True.
            show_estela (bool): Whether to show the trail (estela) of the detections. Defaults to True.
            show_keypoints (bool): Whether to show keypoints of detections. Defaults to True.
            show_contours (bool): Whether to show contours of detections. Defaults to True.
            show_only_segmentation (bool): Whether to show only the segmentation masks. Defaults to False.
        """
        url = f"{self.uri}/get_image"
        params = {
            'camera_name': camera_name,
            'processed': processed,
            'font_size': font_size,
            'show_confidence': show_confidence,
            'show_id': show_id,
            'show_speed': show_speed,
            'show_position': show_position,
            'show_estela': show_estela,
            'show_keypoints': show_keypoints,
            'show_contours': show_contours,
            'show_only_segmentation': show_only_segmentation
        }
        response = requests.get(url, params=params, timeout=self.timeout)
        if not response.ok:
            raise Exception("Failed to get the image")
        return response.content

    def get_image_n_detections(self, camera_name, processed=True, font_size=1, show_confidence=True, show_id=True, show_speed=True, show_position=True, show_estela=True, show_keypoints=True, show_contours=True, show_only_segmentation=False):
        """Get an image and its detections from the specified camera.

        Args:
            camera_name (str): The name of the camera.
            processed (bool): Whether to return the processed image. Defaults to True.
            font_size (float): Font size for any annotations. Defaults to 1.
            show_confidence (bool): Whether to show confidence score of detections. Defaults to True.
            show_id (bool): Whether to show the ID of detections. Defaults to True.
            show_speed (bool): Whether to show the speed of detections. Defaults to True.
            show_position (bool): Whether to show the position of detections. Defaults to True.
            show_estela (bool): Whether to show the trail (estela) of the detections. Defaults to True.
            show_keypoints (bool): Whether to show keypoints of detections. Defaults to True.
            show_contours (bool): Whether to show contours of detections. Defaults to True.
            show_only_segmentation (bool): Whether to show only the segmentation masks. Defaults to False.
        """
        url = f"{self.uri}/get_image_n_detections"
        params = {
            'camera_name': camera_name,
            'processed': processed,
            'font_size': font_size,
            'show_confidence': show_confidence,
            'show_id': show_id,
            'show_speed': show_speed,
            'show_position': show_position,
            'show_estela': show_estela,
            'show_keypoints': show_keypoints,
            'show_contours': show_contours,
            'show_only_segmentation': show_only_segmentation
        }
        response = requests.get(url, params=params, timeout=self.timeout)
        if not response.ok:
            raise Exception("Failed to get the image and detections")
        return response.json()


    def get_calibration(self, camera_name):
        """Get the calibration plot for the specified camera.

        Args:
            camera_name (str): The name of the camera.
        """
        url = f"{self.uri}/get_calibration"
        params = {'camera_name': camera_name}
        response = requests.get(url, params=params, timeout=self.timeout)
        if not response.ok:
            raise Exception("Failed to get the calibration plot")
        return response.content

    def get_camera_properties(self, camera_name):
        """
        Obtiene las propiedades de la cámara utilizando el endpoint `get_camera_properties`.

        Args:
            camera_name (str): Nombre de la cámara.

        Returns:
            dict: Propiedades de la cámara.
        """
        url = f"{self.uri}/get_camera_properties"
        params = {'camera_name': camera_name}
        response = requests.get(url, params=params, timeout=self.timeout)
        if not response.ok:
            raise Exception("Failed to get camera properties")
        return response.json()

    def update_camera_calibration(self, camera_name, roi=None, target=None):
        """Update ROI and/or target points for a specific camera's calibration matrix.

        Args:
            camera_name (str): Name of the camera to update
            roi (list, optional): List of [x,y] coordinates for ROI points
            target (list, optional): List of [x,y] coordinates for target points

        Returns:
            dict: Response containing success/failure message and update details
        """
        url = f"{self.uri}/update_camera_calibration/{camera_name}"
        params = {}
        
        if roi is not None:
            params['roi'] = json.dumps(roi)
        if target is not None:
            params['target'] = json.dumps(target)
        
        response = requests.post(url, params=params, timeout=self.timeout)
        if not response.ok:
            raise Exception("Failed to update camera calibration")
        return response.json()