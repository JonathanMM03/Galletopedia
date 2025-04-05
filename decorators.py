from functools import wraps
from flask import redirect, url_for, flash
from flask_login import current_user

def rol_requerido(*roles):
    """
    Decorador para controlar el acceso a las rutas según el rol del usuario.
    
    Args:
        *roles: Lista de roles permitidos para acceder a la ruta.
        
    Returns:
        function: Decorador que verifica si el usuario tiene el rol requerido.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            
            # Verificar si el rol del usuario está en los roles permitidos
            if current_user.tipo_usuario_id not in roles:
                flash('No tienes permiso para acceder a esta página.', 'error')
                return redirect(url_for('index'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator 