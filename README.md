# Documentación del Proyecto Don Galleto

## Descripción General
Don Galleto es un sistema de gestión para una panadería/galletas que maneja inventario, producción, ventas y administración de usuarios.

## Blueprints (Módulos)

### 1. Autenticación (`auth`)
- **Rutas principales**: `/login`, `/logout`, `/register`
- **Características**:
  - Autenticación de usuarios
  - Registro de nuevos usuarios
  - Gestión de sesiones
  - Protección de rutas con `@login_required`
- **Seguridad**:
  - Encriptación de contraseñas con `werkzeug.security`
  - Tokens CSRF para formularios
  - Sesiones seguras

### 2. Inventario (`inventario`)
- **Rutas principales**: `/inventario`, `/gestion_insumos`, `/gestion_galletas`
- **Características**:
  - Gestión de insumos y galletas
  - Control de stock
  - Registro de lotes
  - Alertas de stock bajo
- **Seguridad**:
  - Validación de permisos por rol
  - Registro de auditoría de cambios

### 3. Producción (`produccion`)
- **Rutas principales**: `/produccion`, `/registrar`, `/solicitud`
- **Características**:
  - Gestión de pedidos
  - Control de producción
  - Verificación de insumos
  - Registro de mermas
- **Seguridad**:
  - Validación de disponibilidad de insumos
  - Control de estados de pedidos

### 4. Ventas (`ventas`)
- **Rutas principales**: `/ventas`, `/registrar_venta`
- **Características**:
  - Registro de ventas
  - Control de inventario
  - Historial de transacciones
- **Seguridad**:
  - Validación de stock disponible
  - Registro de transacciones

### 5. Cliente (`cliente`)
- **Rutas principales**: `/cliente`, `/registrar_cliente`
- **Características**:
  - Gestión de clientes
  - Historial de compras
  - Preferencias de cliente
- **Seguridad**:
  - Protección de datos personales
  - Validación de información

### 6. Proveedores (`proveedores`)
- **Rutas principales**: `/proveedores`, `/registrar_proveedor`
- **Características**:
  - Gestión de proveedores
  - Historial de compras
  - Contactos y ubicaciones
- **Seguridad**:
  - Validación de información de contacto
  - Registro de transacciones

### 7. Recetas (`recetas`)
- **Rutas principales**: `/recetas`, `/nueva_receta`
- **Características**:
  - Gestión de recetas
  - Cálculo de costos
  - Lista de ingredientes
- **Seguridad**:
  - Protección de fórmulas
  - Control de acceso

### 8. Pedidos (`pedidos`)
- **Rutas principales**: `/pedidos`, `/nuevo_pedido`
- **Características**:
  - Gestión de pedidos
  - Seguimiento de estado
  - Asignación de recursos
- **Seguridad**:
  - Validación de disponibilidad
  - Control de estados

### 9. Informe (`informe`)
- **Rutas principales**: `/informe`, `/generar_informe`
- **Características**:
  - Generación de informes
  - Estadísticas de ventas
  - Reportes de inventario
- **Seguridad**:
  - Control de acceso por tipo de informe
  - Registro de consultas

### 10. Principal (`main`)
- **Rutas principales**: `/`, `/dashboard`
- **Características**:
  - Página principal
  - Dashboard con resumen
  - Navegación principal
- **Seguridad**:
  - Redirección de usuarios no autenticados
  - Personalización por rol

## Tecnologías y Librerías

### Backend
- **Framework**: Flask
- **Base de datos**: SQLAlchemy
- **Autenticación**: Flask-Login
- **Formularios**: Flask-WTF
- **Mensajes**: Flask-Flash
- **Manejo de errores**: Flask-ErrorHandler

### Frontend
- **Framework CSS**: Bootstrap 5
- **Iconos**: Font Awesome
- **JavaScript**: 
  - SweetAlert2 para alertas
  - jQuery para manipulación DOM
  - Axios para peticiones AJAX

### Seguridad
- **Autenticación**: JWT (JSON Web Tokens)
- **Protección CSRF**: Flask-WTF
- **Encriptación**: Werkzeug Security
- **Validación de datos**: Marshmallow
- **Control de acceso**: Decoradores personalizados

## Características de Seguridad

### 1. Autenticación y Autorización
- Sistema de roles (admin, empleado, etc.)
- Tokens de sesión seguros
- Protección contra ataques de fuerza bruta
- Cierre de sesión automático

### 2. Protección de Datos
- Encriptación de datos sensibles
- Validación de entrada de datos
- Sanitización de datos
- Prevención de inyección SQL

### 3. Seguridad en Formularios
- Tokens CSRF
- Validación de campos
- Protección contra XSS
- Límites de tamaño de archivos

### 4. Registro y Auditoría
- Logs de actividad
- Registro de cambios
- Trazabilidad de operaciones
- Alertas de seguridad

## Estructura del Proyecto
```
don_galleto/
├── auth/
├── cliente/
├── informe/
├── inventario/
├── main/
├── pedidos/
├── produccion/
├── proveedores/
├── recetas/
├── services/
├── sql/
├── static/
├── templates/
├── ventas/
├── app.py
├── config.py
├── decorators.py
├── forms.py
├── models.py
├── requirements.txt
└── run.py
```

## Requisitos del Sistema
- Python 3.8+
- MySQL 5.7+
- Navegador web moderno
- 2GB RAM mínimo
- 1GB espacio en disco

## Instalación y Configuración
1. Clonar repositorio
2. Crear entorno virtual
3. Instalar dependencias: `pip install -r requirements.txt`
4. Configurar variables de entorno
5. Inicializar base de datos
6. Ejecutar aplicación: `python run.py`

## Mantenimiento
- Backups diarios de base de datos
- Actualización regular de dependencias
- Monitoreo de logs
- Revisión periódica de seguridad

## Contacto y Soporte
- Email: soporte@dongalleto.com
- Teléfono: +1234567890
- Horario de atención: Lunes a Viernes 9:00 - 18:00 
