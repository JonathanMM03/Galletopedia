from flask import render_template, request, redirect, url_for, flash, jsonify, current_app, make_response
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from models import db, InformeProduccion, AdministracionInsumos, Recetas, PedidoGalletas, EstadoPedido, PedidosInsumos, TipoInsumo, Proveedores, InsumoProveedor
from forms import ProduccionForm, SolicitudProduccionForm
from . import produccion_bp
from sqlalchemy import func, and_, or_, text
from functools import wraps
import math
import json

@produccion_bp.route('/')
@login_required
def index():
    # Obtener todas las recetas
    recetas = Recetas.query.all()
    
    # Obtener estados de pedido
    estados_pedido = EstadoPedido.query.all()
    
    # Obtener la fecha de hoy
    hoy = datetime.now().date()
    
    # Obtener pedidos por estado
    # Para pedidos pendientes, solo mostrar los de hoy
    pedidos_pendientes = PedidoGalletas.query.options(
        db.joinedload(PedidoGalletas.receta),
        db.joinedload(PedidoGalletas.estado_pedido)
    ).filter(
        PedidoGalletas.estado_pedido_id == 1,
        func.date(PedidoGalletas.fecha_pedido) == hoy
    ).order_by(PedidoGalletas.fecha_pedido.asc()).all()

    # Para pedidos en proceso, mostrar todos
    pedidos_en_proceso = PedidoGalletas.query.options(
        db.joinedload(PedidoGalletas.receta),
        db.joinedload(PedidoGalletas.estado_pedido)
    ).filter_by(estado_pedido_id=3).order_by(PedidoGalletas.fecha_pedido.asc()).all()

    # Para pedidos completados, solo mostrar los de hoy
    pedidos_completados = PedidoGalletas.query.options(
        db.joinedload(PedidoGalletas.receta),
        db.joinedload(PedidoGalletas.estado_pedido)
    ).filter(
        PedidoGalletas.estado_pedido_id == 4,
        func.date(PedidoGalletas.fecha_actualizacion) == hoy
    ).order_by(PedidoGalletas.fecha_pedido.asc()).all()

    # Para pedidos cancelados, solo mostrar los de hoy
    pedidos_cancelados = PedidoGalletas.query.options(
        db.joinedload(PedidoGalletas.receta),
        db.joinedload(PedidoGalletas.estado_pedido)
    ).filter(
        PedidoGalletas.estado_pedido_id == 5,
        func.date(PedidoGalletas.fecha_actualizacion) == hoy
    ).order_by(PedidoGalletas.fecha_pedido.asc()).all()
    
    # Obtener existencias de galletas por receta
    existencias_galletas = {}
    for receta in recetas:
        # Sumar la cantidad_disponible de todos los informes de producción para esta receta
        cantidad_disponible = db.session.query(func.sum(InformeProduccion.cantidad_disponible)).filter(
            InformeProduccion.receta_id == receta.id
        ).scalar() or 0
        
        existencias_galletas[receta.id] = cantidad_disponible

    return render_template('produccion/index.html', 
                         recetas=recetas, 
                         pedidos_pendientes=pedidos_pendientes,
                         pedidos_en_proceso=pedidos_en_proceso,
                         pedidos_completados=pedidos_completados,
                         pedidos_cancelados=pedidos_cancelados,
                         estados_pedido=estados_pedido,
                         existencias_galletas=existencias_galletas)

def verificar_insumos_suficientes(receta, cantidad_necesaria):
    """Verifica si hay insumos suficientes para producir la cantidad necesaria"""
    insumos_requeridos = receta.obtener_insumos_necesarios(cantidad_necesaria)
    
    print("\n=== Verificación de Insumos ===")
    print(f"Receta: {receta.nombre}")
    print(f"Cantidad necesaria: {cantidad_necesaria}")
    print("\nInsumos requeridos:")
    for insumo_id, cantidad in insumos_requeridos.items():
        insumo = AdministracionInsumos.query.get(insumo_id)
        print(f"- {insumo.insumo_nombre}: {cantidad} {insumo.unidad}")
    
    # Obtener la fecha actual
    fecha_actual = datetime.now().date()
    
    # Verificar cada insumo individualmente
    for insumo_id, cantidad in insumos_requeridos.items():
        # Obtener el insumo
        insumo = AdministracionInsumos.query.get(insumo_id)
        if not insumo:
            print(f"\nError: Insumo {insumo_id} no encontrado")
            return False
            
        # Obtener todos los lotes del insumo que no estén caducados, ordenados por fecha de caducidad
        lotes = AdministracionInsumos.query.filter(
            AdministracionInsumos.id == insumo_id,
            AdministracionInsumos.fecha_caducidad >= fecha_actual
        ).order_by(AdministracionInsumos.fecha_caducidad).all()
        
        cantidad_disponible = sum(lote.cantidad_existente for lote in lotes)
        
        print(f"\nInsumo: {insumo.insumo_nombre}")
        print(f"Tipo: {insumo.tipo_insumo.nombre}")
        print(f"Necesario: {cantidad} {insumo.unidad}")
        print(f"Disponible: {cantidad_disponible} {insumo.unidad}")
        print("Lotes disponibles:")
        for lote in lotes:
            print(f"  * Lote {lote.id}: {lote.cantidad_existente} {insumo.unidad} (Caduca: {lote.fecha_caducidad})")
        
        if cantidad_disponible < cantidad:
            print(f"❌ No hay suficiente {insumo.insumo_nombre}")
            return False
        else:
            print(f"✅ Hay suficiente {insumo.insumo_nombre}")
    
    print("\n✅ Hay suficientes insumos para producir")
    return True

def obtener_lotes_insumos(insumo_id, cantidad_necesaria):
    """Obtiene los lotes de insumos necesarios, priorizando los de menor caducidad"""
    # Obtener la fecha actual
    fecha_actual = datetime.now().date()
    
    # Obtener todos los lotes del insumo que no estén caducados, ordenados por fecha de caducidad
    lotes = AdministracionInsumos.query.filter(
        AdministracionInsumos.id == insumo_id,
        AdministracionInsumos.fecha_caducidad >= fecha_actual
    ).order_by(AdministracionInsumos.fecha_caducidad).all()
    
    lotes_seleccionados = []
    cantidad_restante = cantidad_necesaria
    
    for lote in lotes:
        if cantidad_restante <= 0:
            break
            
        cantidad_a_usar = min(lote.cantidad_existente, cantidad_restante)
        lotes_seleccionados.append({
            'lote': lote,
            'cantidad': cantidad_a_usar
        })
        cantidad_restante -= cantidad_a_usar
    
    return lotes_seleccionados

@produccion_bp.route('/registrar', methods=['GET', 'POST'])
@login_required
def registrar_produccion():
    form = ProduccionForm()
    if form.validate_on_submit():
        producto = Recetas.query.get(form.producto_id.data)
        if not producto:
            flash('Producto no encontrado', 'danger')
            return redirect(url_for('produccion.registrar_produccion'))

        # Ajustar la cantidad al múltiplo más cercano de galletas_por_lote
        cantidad_ajustada = (form.cantidad.data // producto.galletas_por_lote) * producto.galletas_por_lote
        if cantidad_ajustada < producto.galletas_por_lote:
            cantidad_ajustada = producto.galletas_por_lote
            
        # Verificar si hay insumos suficientes usando la función verificar_insumos_suficientes
        if not verificar_insumos_suficientes(producto, cantidad_ajustada):
            flash('No hay suficientes insumos para producir', 'warning')
            return redirect(url_for('produccion.index'))
        
        # Obtener y actualizar los lotes de insumos
        insumos_requeridos = producto.obtener_insumos_necesarios(cantidad_ajustada)
        for insumo_id, cantidad in insumos_requeridos.items():
            lotes_a_usar = obtener_lotes_insumos(insumo_id, cantidad)
            
            for lote_info in lotes_a_usar:
                lote = lote_info['lote']
                cantidad_a_restar = lote_info['cantidad']
                
                lote.cantidad_existente -= cantidad_a_restar
                
                # Marcar como terminado si no quedan unidades
                if lote.cantidad_existente <= 0:
                    lote.estado = 'Terminado'
        
        db.session.commit()
        
        nueva_produccion = InformeProduccion(
            receta_id=form.producto_id.data,
            cantidad_producida=cantidad_ajustada,
            fecha_produccion=datetime.utcnow(),
            caducidad=datetime.utcnow(),
            cantidad_disponible=cantidad_ajustada
        )
        db.session.add(nueva_produccion)
        db.session.commit()
        flash('Producción registrada correctamente', 'success')
        return redirect(url_for('produccion.index'))
    return render_template('produccion/registrar.html', form=form)

@produccion_bp.route('/solicitud', methods=['GET', 'POST'])
@login_required
def solicitar_produccion():
    form = SolicitudProduccionForm()
    if form.validate_on_submit():
        producto = Recetas.query.get(form.producto_id.data)
        if producto:
            # Ajustar la cantidad al múltiplo más cercano de galletas_por_lote
            cantidad_ajustada = (form.cantidad.data // producto.galletas_por_lote) * producto.galletas_por_lote
            if cantidad_ajustada < producto.galletas_por_lote:
                cantidad_ajustada = producto.galletas_por_lote
                
            # Verificar si hay insumos suficientes usando la función verificar_insumos_suficientes
            insumos_suficientes = verificar_insumos_suficientes(producto, cantidad_ajustada)
            
            if not insumos_suficientes:
                # Crear solicitud de producción
                nueva_solicitud = PedidoGalletas(
                    receta_id=form.producto_id.data,
                    cantidad=cantidad_ajustada,
                    estado_pedido_id=1  # Estado pendiente
                )
                db.session.add(nueva_solicitud)
                db.session.commit()
                flash('Solicitud de producción creada', 'success')
            else:
                flash('El stock es suficiente, no es necesaria la solicitud', 'info')
        return redirect(url_for('produccion.index'))
    return render_template('produccion/solicitud.html', form=form)

@produccion_bp.route('/solicitar_insumos', methods=['POST'])
@login_required
def solicitar_insumos():
    """Crea solicitudes de pedido para los insumos faltantes"""
    try:
        # Obtener datos del formulario
        receta_id = request.form.get('receta_id')
        pedido_id = request.form.get('pedido_id')
        
        # Convertir a enteros si no son None
        if receta_id:
            receta_id = int(receta_id)
        if pedido_id:
            pedido_id = int(pedido_id)
        
        # Verificar datos requeridos
        if not receta_id or not pedido_id:
            return jsonify({'error': 'Datos incompletos', 'receta_id': receta_id, 'pedido_id': pedido_id}), 400
        
        receta = Recetas.query.get(receta_id)
        pedido = PedidoGalletas.query.get(pedido_id)
        
        if not receta or not pedido:
            return jsonify({'error': 'Receta o pedido no encontrado'}), 404
        
        # Procesar los insumos faltantes
        insumos_procesados = 0
        insumos_data = []
        
        # Imprimir todos los datos del formulario para depuración
        current_app.logger.debug(f"Form data: {request.form}")
        
        # Recopilar todos los datos de insumos del formulario
        for key in request.form:
            if key.startswith('insumos[') and key.endswith('][id]'):
                index = key[8:-4]  # Extraer el índice
                insumo_id = request.form.get(f'insumos[{index}][id]')
                cantidad = request.form.get(f'insumos[{index}][cantidad]')
                
                current_app.logger.debug(f"Procesando insumo: id={insumo_id}, cantidad={cantidad}")
                
                if insumo_id and cantidad:
                    try:
                        insumos_data.append({
                            'id': int(insumo_id),
                            'cantidad': float(cantidad)
                        })
                    except (ValueError, TypeError) as e:
                        current_app.logger.error(f"Error al convertir datos: {str(e)}")
                        continue
        
        current_app.logger.debug(f"Insumos procesados: {insumos_data}")
        
        if not insumos_data:
            # Intentar un formato alternativo
            for key in request.form:
                if key.startswith('insumo_id_'):
                    index = key.replace('insumo_id_', '')
                    insumo_id = request.form.get(f'insumo_id_{index}')
                    cantidad = request.form.get(f'cantidad_{index}')
                    
                    current_app.logger.debug(f"Procesando insumo (formato alternativo): id={insumo_id}, cantidad={cantidad}")
                    
                    if insumo_id and cantidad:
                        try:
                            insumos_data.append({
                                'id': int(insumo_id),
                                'cantidad': float(cantidad)
                            })
                        except (ValueError, TypeError) as e:
                            current_app.logger.error(f"Error al convertir datos (formato alternativo): {str(e)}")
                            continue
        
        if not insumos_data:
            return jsonify({'error': 'No se encontraron insumos para procesar'}), 400
        
        # Procesar cada insumo
        for insumo_data in insumos_data:
            insumo = AdministracionInsumos.query.get(insumo_data['id'])
            if not insumo:
                current_app.logger.warning(f"Insumo no encontrado: {insumo_data['id']}")
                continue
                
            # Crear pedido de insumo
            nuevo_pedido = PedidosInsumos(
                insumo_id=insumo_data['id'],
                proveedor_id=1,  # Asignar un proveedor por defecto o manejarlo según tu lógica
                cantidad_solicitada=int(insumo_data['cantidad']),  # Convertir a int para cumplir con el tipo de columna
                fecha_pedido=datetime.now().date(),
                estatus='pedido'  # Usar 'pedido' en lugar de 'pendiente' para coincidir con el valor por defecto
            )
            
            db.session.add(nuevo_pedido)
            insumos_procesados += 1
        
        if insumos_procesados == 0:
            return jsonify({'error': 'No se pudo procesar ningún insumo'}), 400
            
        db.session.commit()
        return jsonify({'message': f'Se han creado {insumos_procesados} solicitudes de insumos correctamente'}), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error al solicitar insumos: {str(e)}")
        return jsonify({'error': str(e)}), 500

@produccion_bp.route('/producir', methods=['POST'])
@login_required
def producir():
    try:
        receta_id = request.form.get('receta_id')
        pedido_id = request.form.get('pedido_id')
        cantidad = request.form.get('cantidad')
        
        # Convertir a enteros si no son None
        if receta_id:
            receta_id = int(receta_id)
        if pedido_id:
            pedido_id = int(pedido_id)
        if cantidad:
            cantidad = int(cantidad)
        
        if not receta_id or not pedido_id or not cantidad:
            return jsonify({'error': 'Datos incompletos', 'receta_id': receta_id, 'pedido_id': pedido_id, 'cantidad': cantidad}), 400

        receta = Recetas.query.get(receta_id)
        pedido = PedidoGalletas.query.get(pedido_id)

        if not receta or not pedido:
            return jsonify({'error': 'Receta o pedido no encontrado'}), 404

        # Ajustar la cantidad al múltiplo más cercano de galletas_por_lote
        cantidad_ajustada = (cantidad // receta.galletas_por_lote) * receta.galletas_por_lote
        if cantidad_ajustada < receta.galletas_por_lote:
            cantidad_ajustada = receta.galletas_por_lote

        cantidad_producida = pedido.cantidad_producida if pedido.cantidad_producida is not None else 0
        max_permitido = pedido.cantidad - cantidad_producida
        
        if cantidad_ajustada > max_permitido:
            return jsonify({'error': f'No puede producir {cantidad_ajustada}. El máximo permitido es {max_permitido}'}), 400

        # Verificar si hay insumos suficientes usando la función verificar_insumos_suficientes
        if not verificar_insumos_suficientes(receta, cantidad_ajustada):
            return jsonify({'error': 'No hay suficientes insumos para producir'}), 400

        # Obtener y actualizar los lotes de insumos
        insumos_requeridos = receta.obtener_insumos_necesarios(cantidad_ajustada)
        for insumo_id, cantidad_necesaria in insumos_requeridos.items():
            lotes_a_usar = obtener_lotes_insumos(insumo_id, cantidad_necesaria)
            
            for lote_info in lotes_a_usar:
                lote = lote_info['lote']
                cantidad_a_restar = lote_info['cantidad']
                
                lote.cantidad_existente -= cantidad_a_restar
                
                # Marcar como terminado si no quedan unidades
                if lote.cantidad_existente <= 0:
                    lote.estado = 'Terminado'

        fecha_actual = datetime.utcnow()
        produccion = InformeProduccion(
            receta_id=receta.id,
            cantidad_producida=cantidad_ajustada,
            fecha_produccion=fecha_actual,
            caducidad=fecha_actual,
            cantidad_disponible=cantidad_ajustada
        )

        db.session.add(produccion)
        
        # Actualizar el pedido
        pedido.cantidad_producida = cantidad_producida + cantidad_ajustada
        if pedido.cantidad_producida >= pedido.cantidad:
            estado_completado = EstadoPedido.query.filter_by(nombre='completado').first()
            if estado_completado:
                pedido.estado_pedido_id = estado_completado.id

        db.session.commit()
        return jsonify({'message': f'Producción de {cantidad_ajustada} {receta.nombre} registrada correctamente'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@produccion_bp.route('/actualizar_pedido/<int:pedido_id>', methods=['POST'])
@login_required
def actualizar_pedido(pedido_id):
    pedido = PedidoGalletas.query.get(pedido_id)
    if not pedido:
        flash('Pedido no encontrado.', 'danger')
        return redirect(url_for('produccion.index'))

    # Verificar si el pedido está completado o cancelado
    if pedido.estado_pedido and pedido.estado_pedido.nombre in ['completado', 'cancelado']:
        flash('No se puede modificar un pedido completado o cancelado.', 'warning')
        return redirect(url_for('produccion.index'))

    nuevo_estado = request.form.get('estado_pedido_id', type=int)
    if not nuevo_estado:
        flash('Estado no proporcionado.', 'danger')
        return redirect(url_for('produccion.index'))

    estado = EstadoPedido.query.get(nuevo_estado)
    if not estado:
        flash('Estado no válido.', 'danger')
        return redirect(url_for('produccion.index'))

    pedido.estado_pedido_id = estado.id
    db.session.commit()
    flash('Estado de pedido actualizado.', 'success')
    
    return redirect(url_for('produccion.index'))

@produccion_bp.route('/actualizar_estado/<int:pedido_id>', methods=['POST'])
@login_required
def actualizar_estado(pedido_id):
    try:
        pedido = PedidoGalletas.query.get_or_404(pedido_id)
        nuevo_estado = request.form.get('estado_pedido_id', type=int)
        merma = request.form.get('merma', type=int, default=0)
        motivo_merma = request.form.get('motivo_merma', '')
        
        if not nuevo_estado:
            return jsonify({
                'success': False,
                'message': 'Estado no proporcionado'
            }), 400

        # Verificar que el nuevo estado sea válido
        estado = EstadoPedido.query.get(nuevo_estado)
        if not estado:
            return jsonify({
                'success': False,
                'message': 'Estado no válido'
            }), 400

        # Si el estado es completado (4), procesar la merma y actualizar inventario
        if nuevo_estado == 4:
            # Verificar que la merma no sea mayor que la cantidad del pedido
            if merma > pedido.cantidad:
                return jsonify({
                    'success': False,
                    'message': 'La merma no puede ser mayor que la cantidad del pedido'
                }), 400

            # Calcular cantidad disponible (cantidad producida - merma)
            cantidad_disponible = pedido.cantidad - merma

            # Crear registro en informe_produccion
            informe = InformeProduccion(
                receta_id=pedido.receta_id,
                cantidad_producida=pedido.cantidad,
                fecha_produccion=datetime.now(),
                caducidad=datetime.now() + timedelta(weeks=7),  # 7 semanas de caducidad
                merma=merma,
                motivo_merma=motivo_merma,
                cantidad_disponible=cantidad_disponible
            )
            db.session.add(informe)

            # Obtener los insumos necesarios para la receta
            insumos_requeridos = pedido.receta.obtener_insumos_necesarios(pedido.cantidad)
            
            # Para cada insumo requerido
            for insumo_id, cantidad_necesaria in insumos_requeridos.items():
                # Obtener los lotes del insumo ordenados por fecha de caducidad (menor a mayor)
                lotes = AdministracionInsumos.query.filter_by(id=insumo_id).order_by(AdministracionInsumos.fecha_caducidad.asc()).all()
                
                cantidad_restante = cantidad_necesaria
                
                # Descontar de los lotes en orden de caducidad
                for lote in lotes:
                    if cantidad_restante <= 0:
                        break
                        
                    cantidad_a_descontar = min(lote.cantidad_existente, cantidad_restante)
                    lote.cantidad_existente -= cantidad_a_descontar
                    cantidad_restante -= cantidad_a_descontar

        # Actualizar el estado del pedido
        pedido.estado_pedido_id = nuevo_estado
        pedido.fecha_actualizacion = datetime.now()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Estado actualizado correctamente',
            'nuevo_estado': estado.nombre
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

def handle_errors(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            current_app.logger.error(f"Error: {str(e)}")
            return jsonify({'error': str(e)}), 500
    return decorated_function

def json_response(data, status=200):
    """Helper function to create JSON responses with CORS headers"""
    response = make_response(jsonify(data), status)
    response.headers['Content-Type'] = 'application/json'
    return response

@produccion_bp.route('/cancelar_pedido/<int:pedido_id>', methods=['POST'])
@login_required
def cancelar_pedido(pedido_id):
    """Cancela un pedido de producción"""
    if not current_user.is_authenticated:
        return json_response({'error': 'Usuario no autenticado'}, 401)
        
    try:
        # Verificar si el pedido existe
        pedido = PedidoGalletas.query.get(pedido_id)
        if not pedido:
            return json_response({'error': 'Pedido no encontrado'}, 404)
        
        # Verificar si el pedido ya está cancelado o completado
        if pedido.estado_pedido and pedido.estado_pedido.nombre in ['cancelado', 'completado']:
            return json_response({
                'error': 'No se puede cancelar un pedido ya cancelado o completado',
                'estado_actual': pedido.estado_pedido.nombre
            }, 400)
            
        # Obtener el estado "cancelado"
        estado_cancelado = EstadoPedido.query.filter_by(nombre='cancelado').first()
        if not estado_cancelado:
            # Si no existe el estado, lo creamos
            estado_cancelado = EstadoPedido(nombre='cancelado')
            db.session.add(estado_cancelado)
            try:
                db.session.flush()  # Intentar guardar el nuevo estado
            except Exception as e:
                db.session.rollback()
                return json_response({'error': f'No se pudo crear el estado "cancelado": {str(e)}'}, 500)
            
        # Actualizar el estado del pedido
        pedido.estado_pedido_id = estado_cancelado.id
        pedido.fecha_actualizacion = datetime.utcnow()
        
        try:
            db.session.commit()
            return json_response({
                'message': 'Pedido cancelado correctamente',
                'pedido_id': pedido.id,
                'nuevo_estado': 'cancelado'
            }, 200)
            
        except Exception as e:
            db.session.rollback()
            return json_response({'error': f'Error al guardar los cambios: {str(e)}'}, 500)
            
    except Exception as e:
        current_app.logger.error(f"Error al cancelar pedido {pedido_id}: {str(e)}")
        return json_response({'error': f'Error al procesar la solicitud: {str(e)}'}, 500)

@produccion_bp.route('/insumos_faltantes/<int:receta_id>/<int:pedido_id>')
@login_required
def insumos_faltantes(receta_id, pedido_id):
    """Obtiene la lista de insumos faltantes para un pedido"""
    receta = Recetas.query.get(receta_id)
    pedido = PedidoGalletas.query.get(pedido_id)
    
    if not receta or not pedido:
        return jsonify({'error': 'Receta o pedido no encontrado'}), 404
    
    # Calcular cantidad pendiente a producir
    cantidad_pendiente = pedido.cantidad - (pedido.cantidad_producida or 0)
    
    # Obtener insumos necesarios
    insumos_requeridos = receta.obtener_insumos_necesarios(cantidad_pendiente)
    
    # Verificar disponibilidad de cada insumo
    insumos_faltantes = []
    for insumo_id, cantidad_necesaria in insumos_requeridos.items():
        insumo = AdministracionInsumos.query.get(insumo_id)
        if not insumo:
            continue
            
        # Obtener todos los lotes del insumo ordenados por fecha de caducidad
        lotes = AdministracionInsumos.query.filter_by(id=insumo_id).order_by(AdministracionInsumos.fecha_caducidad).all()
        cantidad_disponible = sum(lote.cantidad_existente for lote in lotes)
        
        if cantidad_disponible < cantidad_necesaria:
            insumos_faltantes.append({
                'id': insumo.id,
                'nombre': insumo.insumo_nombre,
                'cantidad_necesaria': cantidad_necesaria,
                'cantidad_disponible': cantidad_disponible,
                'unidad': insumo.unidad
            })
    
    return jsonify({'insumos_faltantes': insumos_faltantes})

def obtener_insumos_no_caducados():
    """
    Obtiene todos los insumos, incluyendo los que tienen cantidad 0
    """
    fecha_actual = datetime.now().date()
    
    insumos = db.session.query(
        AdministracionInsumos.id,
        AdministracionInsumos.insumo_nombre,
        TipoInsumo.nombre.label('tipo_nombre'),
        AdministracionInsumos.cantidad_existente,
        AdministracionInsumos.unidad,
        AdministracionInsumos.fecha_caducidad,
        AdministracionInsumos.lote_id,
        AdministracionInsumos.fecha_registro,
        Proveedores.nombre_empresa.label('proveedor_nombre')
    ).join(
        TipoInsumo,
        AdministracionInsumos.tipo_insumo_id == TipoInsumo.id
    ).outerjoin(
        Proveedores,
        AdministracionInsumos.proveedor_id == Proveedores.id
    ).order_by(
        AdministracionInsumos.insumo_nombre,
        AdministracionInsumos.fecha_caducidad
    ).all()
    
    return insumos

@produccion_bp.route('/insumos_disponibles')
@login_required
def insumos_disponibles():
    """Ruta para obtener todos los insumos"""
    try:
        insumos = obtener_insumos_no_caducados()
        return jsonify([{
            'id': insumo.id,
            'nombre': insumo.insumo_nombre,
            'categoria': insumo.tipo_nombre,
            'stock': float(insumo.cantidad_existente),
            'unidad': insumo.unidad,
            'lote': insumo.lote_id,
            'proveedor': insumo.proveedor_nombre,
            'fecha_registro': insumo.fecha_registro.strftime('%d/%m/%Y') if insumo.fecha_registro else None,
            'fecha_caducidad': insumo.fecha_caducidad.strftime('%d/%m/%Y') if insumo.fecha_caducidad else None,
            'estado': 'Caducado' if insumo.fecha_caducidad and insumo.fecha_caducidad < datetime.now().date() else 'Vigente'
        } for insumo in insumos])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def verificar_insumos_disponibles_receta(receta_id, cantidad_galletas):
    """
    Obtiene los insumos disponibles y necesarios para una receta
    """
    try:
        # Obtener la receta
        receta = Recetas.query.get(receta_id)
        if not receta:
            return {
                'success': False,
                'error': 'Receta no encontrada'
            }
        
        # Obtener los insumos necesarios para la receta
        insumos_necesarios = receta.obtener_insumos_necesarios(cantidad_galletas)
        
        # Consulta SQL usando la estructura de la vista proporcionada
        query = """
        WITH insumos_disponibles AS (
            SELECT
                ai.insumo_nombre,
                ai.unidad,
                SUM(ai.cantidad_existente) AS cantidad_total
            FROM administracion_insumos ai
            WHERE ai.fecha_caducidad IS NULL OR ai.fecha_caducidad > CURDATE()
            GROUP BY ai.insumo_nombre, ai.unidad
        ),
        insumos_necesarios AS (
            SELECT
                r.id AS receta_id,
                r.nombre AS receta_nombre,
                ai.id AS insumo_id,
                ai.insumo_nombre,
                ai.unidad,
                SUM(ir.cantidad_necesaria) AS cantidad_necesaria
            FROM ingredientes_receta ir
            JOIN administracion_insumos ai ON ir.insumo_id = ai.id
            JOIN recetas r ON ir.receta_id = r.id
            WHERE r.id = :receta_id
            GROUP BY r.id, r.nombre, ai.id, ai.insumo_nombre, ai.unidad
        ),
        lotes_disponibles AS (
            SELECT
                ai.insumo_nombre,
                ai.unidad,
                GROUP_CONCAT(DISTINCT CONCAT(ai.lote_id, '(', ai.cantidad_existente, ')') ORDER BY ai.fecha_caducidad ASC SEPARATOR ', ') AS lotes_disponibles
            FROM administracion_insumos ai
            WHERE ai.fecha_caducidad IS NULL OR ai.fecha_caducidad > CURDATE()
            GROUP BY ai.insumo_nombre, ai.unidad
        ),
        lotes_detalle AS (
            SELECT
                ai.insumo_nombre,
                ai.unidad,
                ai.lote_id,
                ai.cantidad_existente,
                ai.fecha_caducidad,
                inec.cantidad_necesaria
            FROM administracion_insumos ai
            JOIN insumos_necesarios inec ON ai.insumo_nombre = inec.insumo_nombre AND ai.unidad = inec.unidad
            WHERE ai.fecha_caducidad IS NULL OR ai.fecha_caducidad > CURDATE()
        )
        SELECT
            inec.receta_id,
            inec.receta_nombre,
            inec.insumo_id,
            inec.insumo_nombre,
            inec.unidad,
            inec.cantidad_necesaria,
            COALESCE(idisp.cantidad_total, 0) AS cantidad_disponible,
            CASE
                WHEN COALESCE(idisp.cantidad_total, 0) >= inec.cantidad_necesaria THEN 1
                ELSE 0
            END AS hay_suficientes,
            COALESCE(ld.lotes_disponibles, 'Sin lotes disponibles') AS lotes_info,
            (
                SELECT JSON_ARRAYAGG(
                    JSON_OBJECT(
                        'lote_id', lote.lote_id,
                        'cantidad_actual', lote.cantidad_existente,
                        'cantidad_a_usar',
                            CASE
                                WHEN lote.cantidad_existente >= inec.cantidad_necesaria
                                THEN inec.cantidad_necesaria
                                ELSE lote.cantidad_existente
                            END,
                        'cantidad_despues',
                            CASE
                                WHEN lote.cantidad_existente >= inec.cantidad_necesaria
                                THEN lote.cantidad_existente - inec.cantidad_necesaria
                                ELSE 0
                            END,
                        'fecha_caducidad', DATE_FORMAT(lote.fecha_caducidad, '%d/%m/%Y')
                    )
                )
                FROM lotes_detalle lote
                WHERE lote.insumo_nombre = inec.insumo_nombre
                AND lote.unidad = inec.unidad
                AND lote.cantidad_existente > 0
            ) AS lotes_seleccionados
        FROM insumos_necesarios inec
        LEFT JOIN insumos_disponibles idisp
            ON inec.insumo_nombre = idisp.insumo_nombre AND inec.unidad = idisp.unidad
        LEFT JOIN lotes_disponibles ld
            ON inec.insumo_nombre = ld.insumo_nombre AND inec.unidad = ld.unidad
        ORDER BY inec.insumo_nombre
        """
        
        # Ejecutar la consulta
        result = db.session.execute(text(query), {'receta_id': receta_id})
        
        # Procesar los resultados
        insumos = []
        hay_suficientes_insumos = True
        
        for row in result:
            insumo = {
                'id': row.insumo_id,
                'nombre': row.insumo_nombre,
                'tipo': row.unidad,
                'unidad': row.unidad,
                'cantidad_necesaria': float(row.cantidad_necesaria),
                'cantidad_disponible': float(row.cantidad_disponible),
                'hay_suficientes': bool(row.hay_suficientes),
                'lotes_info': row.lotes_info,
                'lotes_seleccionados': json.loads(row.lotes_seleccionados) if row.lotes_seleccionados else []
            }
            
            insumos.append(insumo)
            if not row.hay_suficientes:
                hay_suficientes_insumos = False
        
        return {
            'success': True,
            'receta': {
                'id': receta.id,
                'nombre': receta.nombre,
                'galletas_por_lote': receta.galletas_por_lote
            },
            'cantidad_solicitada': cantidad_galletas,
            'cantidad_ajustada': cantidad_galletas,
            'hay_suficientes_insumos': hay_suficientes_insumos,
            'insumos': insumos
        }
        
    except Exception as e:
        print(f"Error al verificar insumos disponibles: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }

@produccion_bp.route('/verificar_insumos_receta', methods=['GET','POST'])
@login_required
def verificar_insumos_receta_api():
    try:
        data = request.get_json()
        receta_id = data.get('receta_id')
        cantidad = data.get('cantidad', 100)  # Cantidad por defecto: 100 galletas
        
        print("\n=== Datos recibidos en verificar_insumos_receta_api ===")
        print(f"Receta ID: {receta_id}")
        print(f"Cantidad: {cantidad}")
        print("Datos completos:", data)
        print("==================================================\n")
        
        if not receta_id:
            return jsonify({
                'success': False,
                'message': 'No se proporcionó el ID de la receta'
            }), 400
            
        # Obtener los insumos disponibles y necesarios
        resultado = verificar_insumos_disponibles_receta(receta_id, cantidad)
        
        print("\n=== Resultado de verificar_insumos_disponibles_receta ===")
        print("Insumos disponibles:", resultado.get('insumos_disponibles'))
        print("Insumos necesarios:", resultado.get('insumos_necesarios'))
        print("==================================================\n")
        
        return jsonify(resultado)
        
    except Exception as e:
        print(f"Error al verificar insumos: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Ocurrió un error al verificar los insumos'
        }), 500

@produccion_bp.route('/verificar_receta/<int:receta_id>', methods=['GET'])
def verificar_receta(receta_id):
    try:
        # Obtener la receta
        receta = Recetas.query.get_or_404(receta_id)
        
        # Obtener los insumos necesarios para un lote (100 galletas por defecto)
        insumos_necesarios = receta.obtener_insumos_necesarios(100)
        
        # Obtener los insumos disponibles
        insumos_disponibles = {}
        query = text("""
            SELECT 
                ai.insumo_nombre,
                SUM(ai.cantidad_existente) as total_cantidad,
                ai.unidad,
                ti.nombre as tipo_insumo,
                COUNT(DISTINCT ai.lote_id) as total_lotes
            FROM administracion_insumos ai
            JOIN tipo_insumo ti ON ai.tipo_insumo_id = ti.id
            WHERE (ai.fecha_caducidad IS NULL OR ai.fecha_caducidad > CURRENT_DATE)
            AND ai.cantidad_existente > 0
            GROUP BY ai.insumo_nombre, ai.unidad, ti.nombre
        """)
        resultados = db.session.execute(query)
        
        for row in resultados:
            insumos_disponibles[row.insumo_nombre] = {
                'cantidad': float(row.total_cantidad),
                'unidad': row.unidad,
                'tipo': row.tipo_insumo,
                'total_lotes': row.total_lotes
            }
        
        # Verificar si hay suficientes insumos
        insumos_faltantes = []
        for insumo_id, cantidad_necesaria in insumos_necesarios.items():
            insumo = AdministracionInsumos.query.get(insumo_id)
            if not insumo:
                insumos_faltantes.append({
                    'nombre': f"Insumo ID {insumo_id}",
                    'cantidad_necesaria': cantidad_necesaria,
                    'cantidad_disponible': 0,
                    'unidad': 'N/A'
                })
            else:
                disponible = insumos_disponibles.get(insumo.insumo_nombre, {}).get('cantidad', 0)
                if disponible < cantidad_necesaria:
                    insumos_faltantes.append({
                        'nombre': insumo.insumo_nombre,
                        'cantidad_necesaria': cantidad_necesaria,
                        'cantidad_disponible': disponible,
                        'unidad': insumo.unidad
                    })
        
        # Preparar la respuesta
        respuesta = {
            'success': len(insumos_faltantes) == 0,
            'receta': {
                'id': receta.id,
                'nombre': receta.nombre,
                'galletas_por_lote': receta.galletas_por_lote
            },
            'insumos_disponibles': insumos_disponibles,
            'insumos_necesarios': insumos_necesarios,
            'insumos_faltantes': insumos_faltantes
        }
        
        return jsonify(respuesta)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@produccion_bp.route('/iniciar_receta_manual', methods=['POST'])
@login_required
def iniciar_receta_manual():
    try:
        receta_id = request.form.get('receta_id')
        cantidad = request.form.get('cantidad', type=int)
        
        print("\n=== Datos recibidos en iniciar_receta_manual ===")
        print(f"Receta ID: {receta_id}")
        print(f"Cantidad: {cantidad}")
        print("==================================================\n")
        
        if not receta_id or not cantidad:
            return jsonify({
                'success': False,
                'message': 'Faltan datos requeridos',
                'detalles': {
                    'receta_id': receta_id,
                    'cantidad': cantidad
                }
            }), 400
            
        # Verificar que la receta existe
        receta = Recetas.query.get_or_404(receta_id)
        print(f"\nReceta encontrada: {receta.nombre}")
        
        # Ajustar la cantidad al múltiplo más cercano de galletas_por_lote
        cantidad_ajustada = (cantidad // receta.galletas_por_lote) * receta.galletas_por_lote
        if cantidad_ajustada < receta.galletas_por_lote:
            cantidad_ajustada = receta.galletas_por_lote
        print(f"Cantidad ajustada: {cantidad_ajustada}")
            
        # Obtener los insumos necesarios para la receta
        insumos_requeridos = receta.obtener_insumos_necesarios(cantidad_ajustada)
        print("\nInsumos requeridos:")
        for insumo_id, cantidad_necesaria in insumos_requeridos.items():
            print(f"- Insumo ID {insumo_id}: {cantidad_necesaria}")
        
        # Obtener la fecha actual
        fecha_actual = datetime.now().date()
        
        # Verificar disponibilidad de insumos y preparar lotes a usar
        insumos_detalle = []
        hay_suficientes = True
        insumos_faltantes = []
        
        print("\nVerificando disponibilidad de insumos:")
        for insumo_id, cantidad_necesaria in insumos_requeridos.items():
            # Obtener el insumo
            insumo = AdministracionInsumos.query.get(insumo_id)
            if not insumo:
                print(f"- Insumo ID {insumo_id} no encontrado")
                continue
                
            print(f"\nVerificando insumo: {insumo.insumo_nombre}")
            print(f"Cantidad necesaria: {cantidad_necesaria} {insumo.unidad}")
                
            # Obtener todos los lotes del insumo que no estén caducados y tengan cantidad > 0
            lotes = AdministracionInsumos.query.filter(
                AdministracionInsumos.id == insumo_id,
                AdministracionInsumos.fecha_caducidad >= fecha_actual,
                AdministracionInsumos.cantidad_existente > 0
            ).order_by(AdministracionInsumos.fecha_caducidad.asc()).all()
            
            print("Lotes disponibles:")
            for lote in lotes:
                print(f"  * Lote {lote.lote_id}: {lote.cantidad_existente} {insumo.unidad} (Caduca: {lote.fecha_caducidad})")
            
            # Calcular cantidad disponible total
            cantidad_disponible = sum(lote.cantidad_existente for lote in lotes)
            print(f"Cantidad total disponible: {cantidad_disponible} {insumo.unidad}")
            
            # Verificar si hay suficientes insumos
            if cantidad_disponible < cantidad_necesaria:
                hay_suficientes = False
                insumos_faltantes.append({
                    'nombre': insumo.insumo_nombre,
                    'necesario': cantidad_necesaria,
                    'disponible': cantidad_disponible,
                    'unidad': insumo.unidad
                })
                print(f"❌ No hay suficiente {insumo.insumo_nombre}")
            else:
                print(f"✅ Hay suficiente {insumo.insumo_nombre}")
            
            # Simular la selección de lotes
            lotes_seleccionados = []
            cantidad_restante = cantidad_necesaria
            
            for lote in lotes:
                if cantidad_restante <= 0:
                    break
                    
                cantidad_a_usar = min(lote.cantidad_existente, cantidad_restante)
                cantidad_restante -= cantidad_a_usar
                
                lotes_seleccionados.append({
                    'lote': lote,
                    'cantidad_a_usar': cantidad_a_usar
                })
                print(f"  - Usando {cantidad_a_usar} {insumo.unidad} del lote {lote.lote_id}")
            
            insumos_detalle.append({
                'insumo_id': insumo_id,
                'cantidad_necesaria': cantidad_necesaria,
                'cantidad_disponible': cantidad_disponible,
                'lotes_seleccionados': lotes_seleccionados
            })
        
        # Si no hay suficientes insumos, retornar error con detalles
        if not hay_suficientes:
            print("\n❌ No hay suficientes insumos para producir")
            print("Insumos faltantes:")
            for insumo in insumos_faltantes:
                print(f"- {insumo['nombre']}: necesario {insumo['necesario']} {insumo['unidad']}, disponible {insumo['disponible']} {insumo['unidad']}")
            
            return jsonify({
                'success': False,
                'message': 'No hay suficientes insumos para producir',
                'detalles': {
                    'insumos_faltantes': insumos_faltantes,
                    'receta': receta.nombre,
                    'cantidad_solicitada': cantidad,
                    'cantidad_ajustada': cantidad_ajustada
                }
            }), 400
            
        print("\n✅ Hay suficientes insumos, procediendo a restar del inventario")
            
        # Restar los insumos de los lotes
        for insumo in insumos_detalle:
            for lote_info in insumo['lotes_seleccionados']:
                lote = lote_info['lote']
                cantidad_a_usar = lote_info['cantidad_a_usar']
                
                # Actualizar la cantidad del lote
                lote.cantidad_existente -= cantidad_a_usar
                
                # Marcar como terminado si no quedan unidades
                if lote.cantidad_existente <= 0:
                    lote.estado = 'Terminado'
                print(f"Restando {cantidad_a_usar} del lote {lote.lote_id}")
        
        # Crear el pedido directamente en estado "en proceso"
        nuevo_pedido = PedidoGalletas(
            usuario_id=current_user.id,
            receta_id=receta_id,
            cantidad=cantidad_ajustada,
            estado_pedido_id=3,  # Estado "en proceso"
            fecha_pedido=datetime.now()
        )
        
        # Crear el registro de producción
        nueva_produccion = InformeProduccion(
            receta_id=receta_id,
            cantidad_producida=cantidad_ajustada,
            fecha_produccion=datetime.now(),
            caducidad=datetime.now() + timedelta(weeks=7),  # 7 semanas de caducidad
            cantidad_disponible=cantidad_ajustada
        )
        
        db.session.add(nuevo_pedido)
        db.session.add(nueva_produccion)
        db.session.commit()
        
        print("\n✅ Producción registrada correctamente")
        
        return jsonify({
            'success': True,
            'message': 'Receta iniciada correctamente y se han restado los insumos del inventario',
            'pedido_id': nuevo_pedido.id
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"\n❌ Error al iniciar la receta: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error al iniciar la receta: {str(e)}'
        }), 500

@produccion_bp.route('/solicitar_insumo', methods=['GET', 'POST'])
def solicitar_insumo():
    if request.method == 'POST':
        try:
            # Obtener datos del formulario
            insumo_id = request.form.get('insumo_id')
            proveedor_id = request.form.get('proveedor_id')
            cantidad_solicitada = request.form.get('cantidad_solicitada')
            fecha_pedido = request.form.get('fecha_pedido')

            # Validar que todos los campos requeridos estén presentes
            if not all([insumo_id, proveedor_id, cantidad_solicitada, fecha_pedido]):
                return jsonify({
                    'success': False,
                    'message': 'Todos los campos son requeridos'
                }), 400

            # Validar que la cantidad no exceda 100
            try:
                cantidad = int(cantidad_solicitada)
                if cantidad <= 0 or cantidad > 100:
                    return jsonify({
                        'success': False,
                        'message': 'La cantidad debe estar entre 1 y 100'
                    }), 400
            except ValueError:
                return jsonify({
                    'success': False,
                    'message': 'La cantidad debe ser un número válido'
                }), 400

            # Validar que la fecha de pedido sea futura
            fecha_pedido = datetime.strptime(fecha_pedido, '%Y-%m-%d').date()
            if fecha_pedido < date.today():
                return jsonify({
                    'success': False,
                    'message': 'La fecha de pedido debe ser futura'
                }), 400

            # Crear el pedido
            pedido = PedidosInsumos(
                insumo_id=insumo_id,
                proveedor_id=proveedor_id,
                cantidad_solicitada=cantidad,
                fecha_pedido=fecha_pedido,
                estatus='pedido'
            )

            db.session.add(pedido)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Pedido registrado correctamente'
            })

        except Exception as e:
            db.session.rollback()
            return jsonify({
                'success': False,
                'message': f'Error al registrar el pedido: {str(e)}'
            }), 500

    # Para GET, obtener insumos agrupados por nombre
    insumos = db.session.query(
        AdministracionInsumos.insumo_nombre,
        func.count(AdministracionInsumos.id).label('total'),
        func.min(AdministracionInsumos.id).label('id'),
        func.min(AdministracionInsumos.unidad).label('unidad')
    ).group_by(AdministracionInsumos.insumo_nombre).limit(100).all()

    # Formatear los insumos para el template
    insumos_procesados = []
    for insumo in insumos:
        # Obtener los proveedores asociados a este insumo
        proveedores_insumo = db.session.query(
            Proveedores.id,
            Proveedores.nombre_empresa
        ).join(
            InsumoProveedor,
            Proveedores.id == InsumoProveedor.proveedor_id
        ).filter(
            InsumoProveedor.insumo_id == insumo.id
        ).all()
        
        # Convertir a formato JSON
        proveedores_json = [{'id': p.id, 'nombre': p.nombre_empresa} for p in proveedores_insumo]
        
        insumos_procesados.append({
            'id': insumo.id,
            'nombre': insumo.insumo_nombre,
            'unidad': insumo.unidad,
            'total': insumo.total,
            'proveedores': proveedores_json
        })

    return render_template('produccion/solicitar_insumo.html', 
                         insumos=insumos_procesados) 

@produccion_bp.route('/previsualizarProduccion/<int:receta_id>/<int:cantidad>', methods=['GET', 'POST'])
@login_required
def previsualizar_produccion(receta_id, cantidad):
    try:
        # Obtener la receta
        receta = Recetas.query.get_or_404(receta_id)
        
        # Ajustar la cantidad según el tamaño del lote
        cantidad_ajustada = math.ceil(cantidad / receta.galletas_por_lote) * receta.galletas_por_lote
        
        # Consulta SQL usando la estructura de la vista proporcionada
        query = """
        WITH insumos_disponibles AS (
            SELECT
                ai.insumo_nombre,
                ai.unidad,
                SUM(ai.cantidad_existente) AS cantidad_total
            FROM administracion_insumos ai
            WHERE ai.fecha_caducidad IS NULL OR ai.fecha_caducidad > CURDATE()
            GROUP BY ai.insumo_nombre, ai.unidad
        ),
        insumos_necesarios AS (
            SELECT
                r.id AS receta_id,
                r.nombre AS receta_nombre,
                ai.id AS insumo_id,
                ai.insumo_nombre,
                ai.unidad,
                SUM(ir.cantidad_necesaria) AS cantidad_necesaria
            FROM ingredientes_receta ir
            JOIN administracion_insumos ai ON ir.insumo_id = ai.id
            JOIN recetas r ON ir.receta_id = r.id
            WHERE r.id = :receta_id
            GROUP BY r.id, r.nombre, ai.id, ai.insumo_nombre, ai.unidad
        ),
        lotes_disponibles AS (
            SELECT
                ai.insumo_nombre,
                ai.unidad,
                GROUP_CONCAT(DISTINCT CONCAT(ai.lote_id, '(', ai.cantidad_existente, ')') ORDER BY ai.fecha_caducidad ASC SEPARATOR ', ') AS lotes_disponibles
            FROM administracion_insumos ai
            WHERE ai.fecha_caducidad IS NULL OR ai.fecha_caducidad > CURDATE()
            GROUP BY ai.insumo_nombre, ai.unidad
        )
        SELECT
            inec.receta_id,
            inec.receta_nombre,
            inec.insumo_nombre,
            inec.unidad,
            inec.cantidad_necesaria,
            COALESCE(idisp.cantidad_total, 0) AS cantidad_disponible,
            CASE
                WHEN COALESCE(idisp.cantidad_total, 0) >= inec.cantidad_necesaria THEN 'Suficiente'
                ELSE 'Insuficiente'
            END AS estado,
            COALESCE(ld.lotes_disponibles, 'Sin lotes disponibles') AS lotes
        FROM insumos_necesarios inec
        LEFT JOIN insumos_disponibles idisp
            ON inec.insumo_nombre = idisp.insumo_nombre AND inec.unidad = idisp.unidad
        LEFT JOIN lotes_disponibles ld
            ON inec.insumo_nombre = ld.insumo_nombre AND inec.unidad = ld.unidad
        ORDER BY inec.receta_id, inec.insumo_nombre
        """
        
        # Ejecutar la consulta
        result = db.session.execute(text(query), {'receta_id': receta_id})
        
        # Procesar los resultados
        insumos = []
        hay_suficientes_insumos = True
        
        for row in result:
            insumo = {
                'id': row.insumo_id if hasattr(row, 'insumo_id') else None,
                'nombre': row.insumo_nombre,
                'tipo': row.unidad,
                'unidad': row.unidad,
                'cantidad_necesaria': float(row.cantidad_necesaria),
                'cantidad_disponible': float(row.cantidad_disponible),
                'hay_suficientes': row.estado == 'Suficiente',
                'lotes_info': row.lotes,
                'lotes_seleccionados': []  # No tenemos esta información en la consulta original
            }
            
            insumos.append(insumo)
            if row.estado != 'Suficiente':
                hay_suficientes_insumos = False
        
        return jsonify({
            'success': True,
            'receta': {
                'id': receta.id,
                'nombre': receta.nombre,
                'galletas_por_lote': receta.galletas_por_lote
            },
            'cantidad_solicitada': cantidad,
            'cantidad_ajustada': cantidad_ajustada,
            'hay_suficientes_insumos': hay_suficientes_insumos,
            'insumos': insumos
        })
        
    except Exception as e:
        print(f"Error en previsualizar_produccion: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error al previsualizar la producción: {str(e)}'
        }), 500

@produccion_bp.route('/empezar_produccion/<int:receta_id>', methods=['POST'])
@login_required
def iniciar_produccion(receta_id):
    """
    Inicia la producción de una receta usando la cantidad de galletas por lote definida en la receta.
    Descuenta los insumos del inventario en orden de menor a mayor fecha de caducidad.
    """
    try:
        # Obtener la receta
        receta = Recetas.query.get_or_404(receta_id)
        current_app.logger.info(f"Iniciando producción para receta: {receta.nombre} (ID: {receta_id})")
        
        # Usar la cantidad de galletas por lote de la receta
        cantidad = receta.galletas_por_lote
        current_app.logger.info(f"Cantidad a producir: {cantidad} galletas")
        
        # Verificar si hay insumos suficientes usando la misma lógica que la previsualización
        current_app.logger.info("Verificando insumos suficientes...")
        resultado = verificar_insumos_disponibles_receta(receta_id, cantidad)
        
        if not resultado.get('hay_suficientes_insumos', False):
            current_app.logger.warning("No hay suficientes insumos para producir")
            return jsonify({
                'success': False,
                'message': 'No hay suficientes insumos para producir'
            }), 400
            
        # Obtener los insumos necesarios
        current_app.logger.info("Obteniendo insumos necesarios...")
        insumos_requeridos = receta.obtener_insumos_necesarios(cantidad)
        current_app.logger.info(f"Insumos requeridos: {insumos_requeridos}")
        
        # Descontar los insumos de los lotes
        current_app.logger.info("Descontando insumos de los lotes...")
        for insumo_id, cantidad_necesaria in insumos_requeridos.items():
            current_app.logger.info(f"Procesando insumo ID: {insumo_id}, cantidad necesaria: {cantidad_necesaria}")
            
            # Obtener los lotes ordenados por fecha de caducidad
            lotes = AdministracionInsumos.query.filter(
                AdministracionInsumos.id == insumo_id,
                AdministracionInsumos.cantidad_existente > 0,
                or_(
                    AdministracionInsumos.fecha_caducidad.is_(None),
                    AdministracionInsumos.fecha_caducidad > datetime.now().date()
                )
            ).order_by(AdministracionInsumos.fecha_caducidad.asc()).all()
            
            current_app.logger.info(f"Lotes encontrados para insumo {insumo_id}: {len(lotes)}")
            
            cantidad_restante = cantidad_necesaria
            
            # Descontar de cada lote
            for lote in lotes:
                if cantidad_restante <= 0:
                    break
                    
                cantidad_a_descontar = min(lote.cantidad_existente, cantidad_restante)
                lote.cantidad_existente -= cantidad_a_descontar
                cantidad_restante -= cantidad_a_descontar
                
                current_app.logger.info(f"Descontado {cantidad_a_descontar} del lote {lote.lote_id}")
                
                # Marcar como terminado si no quedan unidades
                if lote.cantidad_existente <= 0:
                    lote.estado = 'Terminado'
                    current_app.logger.info(f"Lote {lote.lote_id} marcado como terminado")
        
        # Crear el pedido en estado "en proceso"
        current_app.logger.info("Creando nuevo pedido...")
        nuevo_pedido = PedidoGalletas(
            usuario_id=current_user.id,
            receta_id=receta_id,
            cantidad=cantidad,
            estado_pedido_id=3,  # Estado "en proceso"
            fecha_pedido=datetime.now()
        )
        
        # Crear el registro de producción
        current_app.logger.info("Creando registro de producción...")
        nueva_produccion = InformeProduccion(
            receta_id=receta_id,
            cantidad_producida=cantidad,
            fecha_produccion=datetime.now(),
            caducidad=datetime.now() + timedelta(weeks=7),  # 7 semanas de caducidad
            cantidad_disponible=cantidad
        )
        
        db.session.add(nuevo_pedido)
        db.session.add(nueva_produccion)
        
        current_app.logger.info("Guardando cambios en la base de datos...")
        db.session.commit()
        
        current_app.logger.info("Producción iniciada correctamente")
        return jsonify({
            'success': True,
            'message': 'Producción iniciada correctamente',
            'pedido_id': nuevo_pedido.id,
            'cantidad': cantidad
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error al iniciar la producción: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error al iniciar la producción: {str(e)}'
        }), 500
