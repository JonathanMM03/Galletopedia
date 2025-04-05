# Don Galleto - Sistema de Gestión para Panadería

## Descripción General
Don Galleto es un sistema de gestión integral para una panadería que maneja inventario, producción, ventas y administración de usuarios. El sistema está diseñado para facilitar la gestión de insumos, recetas, pedidos y ventas, proporcionando una interfaz intuitiva para diferentes tipos de usuarios.

## Blueprints (Módulos)

### 1. Autenticación (`auth`)
- **Rutas principales**: `/auth/login`, `/auth/registro`, `/auth/logout`, `/auth/perfil`, `/auth/detalles`, `/auth/eliminar-cuenta`
- **Características**:
  - Registro de usuarios con validación de correo electrónico
  - Inicio de sesión con captcha para prevenir ataques automatizados
  - Gestión de perfiles de usuario
  - Cambio de contraseña
  - Eliminación de cuenta
- **Seguridad**:
  - Encriptación de contraseñas con Werkzeug
  - Protección CSRF en formularios
  - Validación de captcha en login y registro
  - Sesiones seguras con Flask-Login

### 2. Inventario (`inventario`)
- **Rutas principales**: `/inventario/`, `/inventario/insumos`, `/inventario/proveedores`, `/inventario/pedidos`, `/inventario/mermas`
- **Características**:
  - Gestión de insumos y categorías
  - Control de stock y caducidad
  - Registro de mermas
  - Gestión de proveedores
  - Pedidos de insumos
- **Seguridad**:
  - Validación de permisos por rol
  - Registro de acciones en el inventario
  - Validación de datos en formularios

### 3. Producción (`produccion`)
- **Rutas principales**: `/produccion/`, `/produccion/pedidos`, `/produccion/galletas`
- **Características**:
  - Gestión de pedidos de galletas
  - Control de producción
  - Seguimiento de lotes
  - Registro de mermas en producción
- **Seguridad**:
  - Validación de permisos por rol
  - Registro de acciones en producción
  - Validación de datos en formularios

### 4. Ventas (`ventas`)
- **Rutas principales**: `/ventas/`, `/ventas/registro`, `/ventas/historial`
- **Características**:
  - Registro de ventas
  - Historial de transacciones
  - Control de inventario post-venta
  - Reportes de ventas
- **Seguridad**:
  - Validación de permisos por rol
  - Registro de transacciones
  - Validación de datos en formularios

### 5. Cliente (`cliente`)
- **Rutas principales**: `/cliente/`, `/cliente/pedidos`, `/cliente/historial`
- **Características**:
  - Gestión de pedidos de clientes
  - Historial de compras
  - Perfil de cliente
- **Seguridad**:
  - Validación de permisos por rol
  - Registro de acciones de clientes
  - Validación de datos en formularios

### 6. Proveedores (`proveedores`)
- **Rutas principales**: `/proveedores/`, `/proveedores/registro`, `/proveedores/insumos`
- **Características**:
  - Gestión de proveedores
  - Registro de insumos por proveedor
  - Historial de pedidos a proveedores
- **Seguridad**:
  - Validación de permisos por rol
  - Registro de acciones con proveedores
  - Validación de datos en formularios

### 7. Recetas (`recetas`)
- **Rutas principales**: `/recetas/`, `/recetas/crear`, `/recetas/editar`
- **Características**:
  - Gestión de recetas de galletas
  - Cálculo de costos y precios
  - Control de ingredientes
- **Seguridad**:
  - Validación de permisos por rol
  - Registro de acciones en recetas
  - Validación de datos en formularios

### 8. Pedidos (`pedidos`)
- **Rutas principales**: `/pedidos/`, `/pedidos/crear`, `/pedidos/estado`
- **Características**:
  - Gestión de pedidos de galletas
  - Seguimiento de estado de pedidos
  - Notificaciones de pedidos
- **Seguridad**:
  - Validación de permisos por rol
  - Registro de acciones en pedidos
  - Validación de datos en formularios

### 9. Informe (`informe`)
- **Rutas principales**: `/informe/`, `/informe/ventas`, `/informe/produccion`
- **Características**:
  - Generación de informes de ventas
  - Informes de producción
  - Estadísticas de inventario
- **Seguridad**:
  - Validación de permisos por rol
  - Registro de acceso a informes
  - Validación de datos en formularios

### 10. Principal (`main`)
- **Rutas principales**: `/`, `/intranet`
- **Características**:
  - Página principal
  - Panel de intranet
  - Redirección según tipo de usuario
- **Seguridad**:
  - Validación de permisos por rol
  - Registro de acceso a páginas principales
  - Redirección segura según autenticación

## Tecnologías y Librerías
- **Backend**: Flask (Python)
- **Base de datos**: SQLite con SQLAlchemy ORM
- **Frontend**: Bootstrap, HTML, CSS, JavaScript
- **Autenticación**: Flask-Login
- **Formularios**: Flask-WTF
- **Seguridad**: Werkzeug, CSRF Protection
- **Logging**: Sistema de logging personalizado

## Sistema de Logging
El sistema implementa un sistema de logging completo para rastrear todas las acciones de los usuarios y eventos del sistema:

### Tipos de Logs
1. **Logs de Usuario**:
   - Registro de inicio y cierre de sesión
   - Acciones realizadas por usuarios (crear, editar, eliminar)
   - Accesos a diferentes secciones del sistema
   - Cambios en perfiles y configuraciones

2. **Logs de Seguridad**:
   - Intentos fallidos de inicio de sesión
   - Creación de nuevos usuarios
   - Cambios de contraseña
   - Eliminación de cuentas
   - Accesos a áreas restringidas

3. **Logs de Errores**:
   - Errores de base de datos
   - Errores de validación
   - Excepciones no manejadas
   - Problemas de rendimiento

4. **Logs de Rendimiento**:
   - Tiempo de ejecución de operaciones
   - Uso de recursos
   - Latencia en consultas a la base de datos

### Implementación
- Los logs se almacenan en archivos separados por tipo
- Cada log incluye timestamp, usuario, acción, detalles y resultado
- Los logs de seguridad se almacenan en un archivo separado con mayor nivel de protección
- Implementación mediante decoradores para facilitar su uso en las rutas

## Seguridad
- **Autenticación y Autorización**:
  - Sistema de roles (admin, staff, cliente)
  - Encriptación de contraseñas
  - Sesiones seguras
  - Protección contra CSRF

- **Protección de Datos**:
  - Validación de entrada de datos
  - Sanitización de datos
  - Prevención de inyección SQL
  - Encriptación de datos sensibles

- **Seguridad en Formularios**:
  - Tokens CSRF en todos los formularios
  - Validación de datos en servidor y cliente
  - Captchas en formularios críticos (login y registro)
  - Límites de intentos para prevenir ataques de fuerza bruta

- **Captchas**:
  - Implementación de captchas en formularios de login y registro
  - Generación aleatoria de códigos captcha
  - Validación en servidor para prevenir bypass
  - Actualización de captchas en cada intento fallido

- **Logging y Auditoría**:
  - Registro de todas las acciones de usuarios
  - Registro de intentos de acceso
  - Registro de errores y excepciones
  - Historial de cambios en datos críticos

## Estructura del Proyecto
```
don_galleto/
├── app.py                  # Aplicación principal
├── models.py               # Modelos de base de datos
├── forms.py                # Formularios WTForms
├── auth/                   # Blueprint de autenticación
├── inventario/             # Blueprint de inventario
├── produccion/             # Blueprint de producción
├── ventas/                 # Blueprint de ventas
├── cliente/                # Blueprint de cliente
├── proveedores/            # Blueprint de proveedores
├── recetas/                # Blueprint de recetas
├── pedidos/                # Blueprint de pedidos
├── informe/                # Blueprint de informes
├── main/                   # Blueprint principal
├── services/               # Servicios (logger, etc.)
├── static/                 # Archivos estáticos
├── templates/              # Plantillas HTML
└── logs/                   # Archivos de logs
```

## Requisitos del Sistema
- Python 3.8+
- Flask 2.0+
- SQLAlchemy 1.4+
- Flask-Login 0.5+
- Flask-WTF 0.15+
- Werkzeug 2.0+
- Bootstrap 5.0+

## Instalación
1. Clonar el repositorio
2. Crear un entorno virtual: `python -m venv venv`
3. Activar el entorno virtual: `venv\Scripts\activate` (Windows) o `source venv/bin/activate` (Linux/Mac)
4. Instalar dependencias: `pip install -r requirements.txt`
5. Inicializar la base de datos: `flask db upgrade`
6. Ejecutar la aplicación: `python app.py`

## Mantenimiento
- Realizar copias de seguridad regulares de la base de datos
- Revisar los logs periódicamente para detectar problemas
- Actualizar las dependencias para corregir vulnerabilidades
- Monitorear el rendimiento del sistema

## Contacto y Soporte
Para reportar problemas o solicitar soporte, contactar al administrador del sistema. 