from datetime import timedelta
import os
from sqlalchemy import create_engine
import urllib

class Config(object):
    SECRET_KEY = 'Clave nueva'
    SESSION_COOKIE_SECURE = False
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    password = urllib.parse.quote_plus("password")
    SQLALCHEMY_DATABASE_URI = f'mysql+pymysql://root:{password}@localhost/don_galleto?charset=utf8mb4'

    DATABASE_URIS = {
        "admin": "mysql+pymysql://dongalleto_admin:Admin_Galletopedia@localhost/don_galleto",
        "cliente": "mysql+pymysql://dongalleto_cliente:Cliente_Galletopedia@localhost/don_galleto",
        "produccion": "mysql+pymysql://dongalleto_produccion:Produccion_Galletopedia@localhost/don_galleto",
        "ventas": "mysql+pymysql://dongalleto_ventas:Ventas_Galletopedia@localhost/don_galleto"
    }

    # Configuración de URIs dinámicas por rol
    # Define las rutas a las que cada tipo de usuario tiene acceso
    ROLE_URIS = {
        "admin": {
            "dashboard": "/admin/dashboard",
            "usuarios": "/admin/usuarios",
            "configuracion": "/admin/configuracion",
            "reportes": "/admin/reportes",
            "inventario": "/inventario/gestion-insumos",
            "produccion": "/produccion",
            "ventas": "/ventas",
            "clientes": "/clientes"
        },
        "cliente": {
            "dashboard": "/cliente/dashboard",
            "pedidos": "/cliente/pedidos",
            "historial": "/cliente/historial",
            "perfil": "/cliente/perfil"
        },
        "produccion": {
            "dashboard": "/produccion",
            "recetas": "/produccion/recetas",
            "pedidos": "/produccion/pedidos",
            "inventario": "/inventario/gestion-insumos"
        },
        "ventas": {
            "dashboard": "/ventas",
            "pedidos": "/ventas/pedidos",
            "clientes": "/ventas/clientes",
            "reportes": "/ventas/reportes"
        }
    }

    # Configuración de permisos por ruta
    # Define qué roles tienen acceso a cada ruta
    ROUTE_PERMISSIONS = {
        "/admin/dashboard": ["admin"],
        "/admin/usuarios": ["admin"],
        "/admin/configuracion": ["admin"],
        "/admin/reportes": ["admin"],
        "/inventario/gestion-insumos": ["admin", "produccion"],
        "/produccion": ["admin", "produccion"],
        "/produccion/recetas": ["admin", "produccion"],
        "/produccion/pedidos": ["admin", "produccion"],
        "/ventas": ["admin", "ventas"],
        "/ventas/pedidos": ["admin", "ventas"],
        "/ventas/clientes": ["admin", "ventas"],
        "/ventas/reportes": ["admin", "ventas"],
        "/cliente/dashboard": ["cliente"],
        "/cliente/pedidos": ["cliente"],
        "/cliente/historial": ["cliente"],
        "/cliente/perfil": ["cliente"]
    }

    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)

class DevelopmentConfig(Config):
    DEBUG = True 