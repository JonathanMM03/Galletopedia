from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_required, current_user
from models import db, Recetas, PedidoGalletas, InformeVentas, DetalleVenta, IngredientesReceta, PedidoGalletasClientes, EstadoPedido
from sqlalchemy import func
from datetime import datetime, timedelta
from forms import SolicitarLoteForm, FlaskForm
from sqlalchemy.orm import joinedload
from datetime import datetime
import math
from models import Usuarios, TipoUsuario
from . import cliente_bp
from decorators import rol_requerido

@cliente_bp.route('/')
@login_required
@rol_requerido(1, 2)
def index():
    # Obtener el número de página de los parámetros de la URL
    page = request.args.get('page', 1, type=int)
    per_page = 10  # Número de usuarios por página
    
    # Consulta base con paginación
    pagination = Usuarios.query.join(TipoUsuario).add_columns(
        Usuarios.id,
        Usuarios.nombre,
        Usuarios.email,
        TipoUsuario.nombre.label('tipo_usuario')
    ).order_by(Usuarios.nombre.asc()).paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('cliente/index.html', 
                         usuarios=pagination.items,
                         pagination=pagination)

@cliente_bp.route('/usuarios/editar/<int:id>', methods=['GET', 'POST'])
@login_required
@rol_requerido(1, 2)
def editar_usuario(id):
    usuario = Usuarios.query.get_or_404(id)
    tipos_usuario = TipoUsuario.query.all()  # Para el select de tipos de usuario
    
    # Proteger al usuario administrador de cambios de rol
    if usuario.email == 'admin@dongalleto.com':
        flash('No se puede modificar el rol del administrador principal.', 'error')
        return redirect(url_for('cliente.index'))
    
    if request.method == 'POST':
        try:
            usuario.nombre = request.form['nombre']
            usuario.email = request.form['email']
            usuario.tipo_usuario_id = request.form['tipo_usuario']
            
            # Si se proporcionó una nueva contraseña
            if request.form['password']:
                usuario.set_password(request.form['password'])
            
            db.session.commit()
            flash('Usuario actualizado correctamente', 'success')
            return redirect(url_for('cliente.index'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar usuario: {str(e)}', 'danger')
    
    return render_template('cliente/editar_usuario.html', 
                         usuario=usuario,
                         tipos_usuario=tipos_usuario)
    

@cliente_bp.route('/usuarios/eliminar/<int:id>', methods=['POST'])
@login_required
@rol_requerido(1, 2)
def eliminar_usuario(id):
    usuario = Usuarios.query.get_or_404(id)
    
    try:
        # Eliminación lógica
        usuario.activo = False
        usuario.fecha_eliminacion = datetime.now()
        db.session.commit()
        flash('Usuario desactivado correctamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al desactivar usuario: {str(e)}', 'danger')
    
    return redirect(url_for('cliente.index'))

@cliente_bp.route('/registrar', methods=['GET', 'POST'])
@login_required
@rol_requerido(1, 2)
def registrar_usuario():
    if request.method == 'POST':
        nombre = request.form['nombre']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        tipo_usuario_id = request.form['tipo_usuario']

        # Verifica si las contraseñas coinciden
        if password != confirm_password:
            flash('Las contraseñas no coinciden. Intenta de nuevo.', 'danger')
            return redirect(url_for('registrar_usuario'))

        # Verifica si el email ya está registrado
        if Usuarios.query.filter_by(email=email).first():
            flash('El correo electrónico ya está registrado. Intenta con otro.', 'danger')
            return redirect(url_for('registrar_usuario'))

        # Crear nuevo usuario
        nuevo_usuario = Usuarios(
            nombre=nombre,
            email=email,
            tipo_usuario_id=tipo_usuario_id
        )
        nuevo_usuario.set_password(password)  # Hashea la contraseña

        db.session.add(nuevo_usuario)
        db.session.commit()

        flash('Usuario registrado con éxito.', 'success')
        return redirect(url_for('cliente.index'))  # O la ruta que corresponda

    # Obtener tipos de usuario para el select
    tipos_usuario = TipoUsuario.query.all()
    return render_template('cliente/agregar_usuario.html', tipos_usuario=tipos_usuario)