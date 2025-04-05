import logging
import os
from datetime import datetime
from flask import request, session, g
from functools import wraps

# Configuración del logger
def setup_logger():
    # Crear directorio de logs si no existe
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # Configurar el logger principal
    logger = logging.getLogger('don_galleto')
    logger.setLevel(logging.INFO)
    
    # Crear un manejador para archivo
    file_handler = logging.FileHandler('logs/app.log')
    file_handler.setLevel(logging.INFO)
    
    # Crear un manejador para consola
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Crear un formato para los logs
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Agregar los manejadores al logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

# Logger para acciones de usuario
def log_user_action(action_type):
    """
    Decorador para registrar acciones de usuario
    
    Args:
        action_type (str): Tipo de acción (login, logout, create, update, delete, etc.)
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Obtener información del usuario
            user_id = session.get('user_id', 'anonymous')
            username = session.get('username', 'anonymous')
            
            # Obtener información de la petición
            endpoint = request.endpoint
            method = request.method
            ip = request.remote_addr
            
            # Registrar la acción antes de ejecutar la función
            logger = logging.getLogger('don_galleto')
            logger.info(f"USER_ACTION - User: {username} (ID: {user_id}) - Action: {action_type} - Endpoint: {endpoint} - Method: {method} - IP: {ip}")
            
            # Ejecutar la función original
            result = f(*args, **kwargs)
            
            # Registrar el resultado
            if hasattr(result, 'status_code'):
                logger.info(f"RESULT - User: {username} - Action: {action_type} - Status: {result.status_code}")
            else:
                logger.info(f"RESULT - User: {username} - Action: {action_type} - Completed")
            
            return result
        return decorated_function
    return decorator

# Logger para errores
def log_error(error_type):
    """
    Decorador para registrar errores
    
    Args:
        error_type (str): Tipo de error (validation, database, authentication, etc.)
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except Exception as e:
                # Obtener información del usuario
                user_id = session.get('user_id', 'anonymous')
                username = session.get('username', 'anonymous')
                
                # Obtener información de la petición
                endpoint = request.endpoint
                method = request.method
                ip = request.remote_addr
                
                # Registrar el error
                logger = logging.getLogger('don_galleto')
                logger.error(f"ERROR - Type: {error_type} - User: {username} (ID: {user_id}) - Endpoint: {endpoint} - Method: {method} - IP: {ip} - Message: {str(e)}")
                
                # Re-lanzar la excepción
                raise
        return decorated_function
    return decorator

# Logger para seguridad
def log_security_event(event_type, details=None):
    """
    Función para registrar eventos de seguridad
    
    Args:
        event_type (str): Tipo de evento (login_attempt, password_change, etc.)
        details (dict): Detalles adicionales del evento
    """
    # Obtener información del usuario
    user_id = session.get('user_id', 'anonymous')
    username = session.get('username', 'anonymous')
    
    # Obtener información de la petición
    endpoint = request.endpoint
    method = request.method
    ip = request.remote_addr
    
    # Registrar el evento
    logger = logging.getLogger('don_galleto')
    logger.warning(f"SECURITY - Event: {event_type} - User: {username} (ID: {user_id}) - Endpoint: {endpoint} - Method: {method} - IP: {ip} - Details: {details}")
    
    # Guardar en archivo separado para eventos de seguridad
    security_logger = logging.getLogger('security')
    security_logger.setLevel(logging.WARNING)
    
    # Crear un manejador para archivo de seguridad
    security_file_handler = logging.FileHandler('logs/security.log')
    security_file_handler.setLevel(logging.WARNING)
    
    # Crear un formato para los logs de seguridad
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    security_file_handler.setFormatter(formatter)
    
    # Agregar el manejador al logger de seguridad
    security_logger.addHandler(security_file_handler)
    
    # Registrar el evento
    security_logger.warning(f"Event: {event_type} - User: {username} (ID: {user_id}) - IP: {ip} - Details: {details}")

# Logger para rendimiento
def log_performance(operation_name):
    """
    Decorador para registrar el rendimiento de operaciones
    
    Args:
        operation_name (str): Nombre de la operación
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Registrar tiempo de inicio
            start_time = datetime.now()
            
            # Ejecutar la función original
            result = f(*args, **kwargs)
            
            # Calcular tiempo de ejecución
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            
            # Registrar el rendimiento
            logger = logging.getLogger('don_galleto')
            logger.info(f"PERFORMANCE - Operation: {operation_name} - Execution Time: {execution_time} seconds")
            
            return result
        return decorated_function
    return decorator

# Inicializar el logger al importar el módulo
logger = setup_logger() 