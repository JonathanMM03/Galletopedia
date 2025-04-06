from flask import render_template, request, redirect, url_for, flash, jsonify, current_app
from . import inventario_bp
from models import (
    db, AdministracionInsumos, TipoInsumo, Proveedores,
    InsumoProveedor, PedidosInsumos, InsumosRecibidos,
    MermaInsumos, Recetas, PedidoGalletas, InformeProduccion,
    EstadoPedido
)
from forms import (
    InsumoForm, ProveedorForm, PedidoInsumoForm,
    InsumoRecibidoForm, MermaInsumoForm, SolicitarLoteForm,
    CategoriaInsumoForm, NuevoInsumoForm, AsignarProveedorInsumoForm,
    NuevoLoteForm
)
from datetime import datetime, date, timedelta
from sqlalchemy import func, case
from . import utils as u
from flask_login import login_required, current_user
import uuid
import re
from decorators import rol_requerido
from services.logger_service import log_user_action, log_error, log_performance

@inventario_bp.route('/')
@login_required
@rol_requerido(1, 2)
def index():
    print("\n=== INICIO index ===")
    # Obtener todos los tipos de insumo con sus totales
    totales_por_tipo = u.calcular_totales_por_tipo()

    # Convertir los resultados a un diccionario para fácil acceso
    totales_dict = {tipo.id: {'nombre': tipo.nombre, 'total': float(tipo.total)} for tipo in totales_por_tipo}

    # Obtener parámetros de filtrado y paginación
    page = request.args.get('page', 1, type=int)
    categoria_id = request.args.get('categoria', type=int)
    nombre = request.args.get('nombre', type=str)
    per_page = 10  # Número de insumos por página

    # Obtener todos los insumos con sus tipos y aplicar paginación
    query = u.obtener_insumos_query()

    # Aplicar filtros si están presentes
    if categoria_id:
        query = query.filter(AdministracionInsumos.tipo_insumo_id == categoria_id)
    if nombre:
        query = query.filter(AdministracionInsumos.insumo_nombre.ilike(f'%{nombre}%'))

    # Aplicar paginación
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    # Procesar los resultados para el template
    insumos_procesados = [u.procesar_insumo(insumo) for insumo in pagination.items]

    # Obtener pedidos pendientes
    pedidos_pendientes = u.obtener_pedidos_pendientes()

    # Procesar los pedidos pendientes
    pedidos_procesados = [u.procesar_pedido(pedido) for pedido in pedidos_pendientes]
    
    # Contar pedidos pendientes
    total_pedidos_pendientes = len(pedidos_pendientes)
    
    # Contar mermas del mes actual
    mermas_mes = u.obtener_mermas_mes()
    
    # Obtener la fecha actual para comparaciones en la plantilla
    now = date.today()
    
    return render_template('inventario/index.html',
                         insumos=insumos_procesados,
                         tipos_insumo=totales_por_tipo,
                         totales=totales_dict,
                         pedidos_pendientes=pedidos_procesados,
                         total_pedidos_pendientes=total_pedidos_pendientes,
                         mermas_mes=mermas_mes,
                         now=now,
                         pagination=pagination,
                         categoria_actual=categoria_id,
                         nombre_filtro=nombre)

@inventario_bp.route('/insumos')
def insumos():
    # Obtener todos los insumos con sus tipos
    insumos = u.obtener_insumos()

    # Procesar los resultados para el template
    insumos_procesados = []
    for insumo in insumos:
        # Obtener el proveedor más reciente para este insumo
        insumo_proveedor = InsumoProveedor.query.filter_by(insumo_id=insumo.id).first()
        proveedor = Proveedores.query.get(insumo_proveedor.proveedor_id) if insumo_proveedor else None
        
        insumo_dict = {
            'id': insumo.id,
            'insumo_nombre': insumo.insumo_nombre,
            'tipo_insumo': insumo.TipoInsumo,
            'cantidad_existente': insumo.cantidad_existente,
            'unidad': insumo.unidad,
            'lote_id': insumo.lote_id,
            'fecha_registro': insumo.fecha_registro,
            'fecha_caducidad': insumo.fecha_caducidad,
            'proveedor': proveedor.nombre_empresa if proveedor else 'Sin proveedor'
        }
        insumos_procesados.append(insumo_dict)

    tipos_insumo = TipoInsumo.query.all()
    return render_template('inventario/insumos.html', insumos=insumos_procesados, tipos_insumo=tipos_insumo)

@inventario_bp.route('/insumos/agregar', methods=['GET'])
def agregar_insumo():
    print("\n=== INICIO agregar_insumo ===")
    # Redirigir a la página principal donde está el modal
    return redirect(url_for('inventario.index'))

@inventario_bp.route('/insumos/eliminar/<nombre_insumo>', methods=['POST'])
@login_required
def eliminar_insumo(nombre_insumo):
    try:
        # Buscar todos los insumos con el nombre especificado
        insumos = AdministracionInsumos.query.filter_by(insumo_nombre=nombre_insumo).all()
        
        if not insumos:
            return jsonify({
                'success': False,
                'message': 'No se encontró el insumo especificado'
            }), 404
        
        # Eliminar cada insumo encontrado
        for insumo in insumos:
            # Primero eliminar las relaciones con proveedores
            InsumoProveedor.query.filter_by(insumo_id=insumo.id).delete()
            # Luego eliminar el insumo
            db.session.delete(insumo)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Se eliminaron {len(insumos)} registro(s) del insumo {nombre_insumo}'
        })
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Error al eliminar insumo {nombre_insumo}: {str(e)}')
        return jsonify({
            'success': False,
            'message': f'Error al eliminar el insumo: {str(e)}'
        }), 500

@inventario_bp.route('/editar-insumo/<nombre_insumo>', methods=['GET', 'POST'])
@login_required
def editar_insumo(nombre_insumo):
    try:
        # Buscar todos los insumos con el nombre especificado
        insumos = AdministracionInsumos.query.filter_by(insumo_nombre=nombre_insumo).all()
        
        if not insumos:
            flash('No se encontró el insumo especificado', 'danger')
            return redirect(url_for('inventario.gestion_insumos'))
        
        # Si hay múltiples registros, mostrar una lista para seleccionar cuál editar
        if len(insumos) > 1:
            return render_template('inventario/select_insumo.html', insumos=insumos)
        
        # Si solo hay un registro, proceder con la edición
        insumo = insumos[0]
        form = NuevoInsumoForm(obj=insumo)
        
        if form.validate_on_submit():
            insumo.insumo_nombre = form.nombre.data
            insumo.tipo_insumo_id = form.categoria_id.data
            insumo.unidad = form.unidad_medida.data
            insumo.fecha_caducidad = form.fecha_caducidad.data
            
            db.session.commit()
            flash('Insumo actualizado exitosamente', 'success')
            return redirect(url_for('inventario.gestion_insumos'))
        
        return render_template('inventario/editar_insumo.html', form=form, insumo=insumo)
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Error al editar insumo {nombre_insumo}: {str(e)}')
        flash(f'Error al editar el insumo: {str(e)}', 'danger')
        return redirect(url_for('inventario.gestion_insumos'))

@inventario_bp.route('/proveedores', methods=['GET', 'POST'])
@login_required
def proveedores():
    form = ProveedorForm()
    
    # Obtener parámetros de filtrado y paginación
    filtro_nombre = request.args.get('filtro_nombre', '')
    page = request.args.get('page', 1, type=int)
    per_page = 10  # Número de proveedores por página
    
    # Consulta base
    query = Proveedores.query
    
    # Aplicar filtro si se proporciona
    if filtro_nombre:
        query = query.filter(Proveedores.nombre_empresa.ilike(f'%{filtro_nombre}%'))
    
    # Aplicar paginación
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    proveedores = pagination.items
    
    if request.method == 'POST':
        if form.validate_on_submit():
            try:
                # Crear nuevo proveedor
                nuevo_proveedor = Proveedores(
                    nombre_empresa=form.nombre_empresa.data,
                    nombre_promotor=form.nombre_promotor.data,
                    telefono=form.telefono.data,
                    correo_electronico=form.correo_electronico.data
                )
                db.session.add(nuevo_proveedor)
                db.session.commit()
                
                return jsonify({
                    'success': True,
                    'message': 'Proveedor registrado exitosamente'
                })
            except Exception as e:
                db.session.rollback()
                return jsonify({
                    'success': False,
                    'message': f'Error al registrar el proveedor: {str(e)}'
                }), 500
        else:
            return jsonify({
                'success': False,
                'message': 'Por favor, corrija los errores en el formulario'
            }), 400
    
    return render_template('inventario/proveedores.html', 
                         form=form,
                         proveedores=proveedores, 
                         filtro_nombre=filtro_nombre,
                         pagination=pagination)

@inventario_bp.route('/pedidos')
def pedidos():
    # Obtener todos los pedidos con sus relaciones
    pedidos = u.obtener_pedidos_pendientes()

    # Procesar los resultados para el template
    pedidos_procesados = [u.procesar_pedido(pedido) for pedido in pedidos]

    return render_template('inventario/pedidos.html', pedidos=pedidos_procesados)

@inventario_bp.route('/pedidos/agregar', methods=['GET', 'POST'])
def agregar_pedido():
    if request.method == 'POST':
        try:
            # Obtener datos del formulario
            insumo_id = request.form.get('insumo_id')
            proveedor_id = request.form.get('proveedor_id')
            cantidad_solicitada = request.form.get('cantidad_solicitada')
            fecha_pedido = request.form.get('fecha_pedido')
            estatus = request.form.get('estatus', 'pedido')

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
                estatus=estatus
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

    return render_template('inventario/agregar_pedido.html')

@inventario_bp.route('/pedidos/recibir/<int:id>', methods=['GET', 'POST'])
def recibir_pedido(id):
    pedido = PedidosInsumos.query.get_or_404(id)
    form = InsumoRecibidoForm()
    if request.method == 'POST' and form.validate():
        # Crear registro de insumo recibido
        insumo_recibido = InsumosRecibidos(
            lote_id=form.lote_id.data,
            fecha_recepcion=form.fecha_recepcion.data,
            fecha_caducidad=form.fecha_caducidad.data,
            cantidad=form.cantidad.data,
            precio_unitario=form.precio_unitario.data,
            insumo_id=pedido.insumo_id,
            proveedor_id=pedido.proveedor_id
        )
        db.session.add(insumo_recibido)
        
        # Actualizar cantidad existente y proveedor del insumo
        insumo = AdministracionInsumos.query.get(pedido.insumo_id)
        insumo.cantidad_existente += form.cantidad.data
        insumo.proveedor_id = pedido.proveedor_id  # Actualizar el proveedor_id
        insumo.lote_id = form.lote_id.data  # Actualizar el lote_id
        insumo.fecha_registro = form.fecha_recepcion.data  # Actualizar la fecha de registro
        insumo.fecha_caducidad = form.fecha_caducidad.data  # Actualizar la fecha de caducidad
        
        # Actualizar estado del pedido
        pedido.estatus = "recibido"
        
        db.session.commit()
        flash('Pedido recibido exitosamente', 'success')
        return redirect(url_for('inventario.pedidos'))
    return render_template('inventario/recibir_pedido.html', form=form, pedido=pedido)

@inventario_bp.route('/agregar_merma', methods=['GET', 'POST'])
def agregar_merma():
    form = MermaInsumoForm()
    if form.validate_on_submit():
        merma = MermaInsumos(
            insumo_id=form.insumo_id.data,
            cantidad_danada=form.cantidad_danada.data,
            motivo_merma=form.motivo_merma.data
        )
        db.session.add(merma)
        db.session.commit()
        flash('Merma registrada exitosamente', 'success')
        return redirect(url_for('inventario.mermas'))
    return render_template('inventario/agregar_merma.html', form=form)

# Rutas API para AJAX
@inventario_bp.route('/insumos/listar')
def listar_insumos():
    try:
        # Obtener todos los tipos de insumo
        tipos_insumo = TipoInsumo.query.all()
        
        # Para cada tipo, obtener sus insumos
        resultado = {}
        for tipo in tipos_insumo:
            insumos = u.obtener_insumos_por_tipo(tipo.id)
            if insumos:  # Solo incluir tipos que tengan insumos
                resultado[tipo.nombre] = insumos
                
        return jsonify(resultado)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@inventario_bp.route('/proveedores/listar')
def listar_proveedores():
    proveedores = Proveedores.query.all()
    return jsonify([{
        'id': p.id,
        'nombre': p.nombre_empresa,
        'contacto': p.nombre_promotor
    } for p in proveedores])

@inventario_bp.route('/insumo/<string:nombre>')
def get_insumo_unidad(nombre):
    try:
        insumo = AdministracionInsumos.query.filter_by(insumo_nombre=nombre).first()
        if insumo:
            return jsonify({
                'unidad': insumo.unidad
            })
        return jsonify({'error': 'Insumo no encontrado'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@inventario_bp.route('/lotes/<int:tipo_insumo_id>')
def get_lotes(tipo_insumo_id):
    try:
        # Obtener todos los lotes del tipo especificado
        lotes = u.obtener_lotes_por_tipo(tipo_insumo_id)
            
        # Formatear los datos de los lotes
        lotes_procesados = []
        for insumo in lotes:
            esta_caducado, dias_restantes = u.calcular_estado_caducidad(insumo.fecha_caducidad)
            
            # Determinar el estado y mensaje basado primero en la cantidad
            if insumo.cantidad_existente <= 0:
                estado = 'terminado'
                mensaje = 'Terminado'
                icono = '<i class="fas fa-check-circle"></i>'
            # Solo si hay cantidad verificamos caducidad
            elif esta_caducado:
                estado = 'caduco'
                mensaje = f'Caducado hace {abs(dias_restantes)} días'
                icono = '<i class="fas fa-exclamation-triangle"></i>'
            elif dias_restantes is not None and dias_restantes <= 30:
                estado = 'proximo_caducar'
                mensaje = f'Caduca en {dias_restantes} días'
                icono = '<i class="fas fa-exclamation-circle"></i>'
            else:
                estado = 'vigente'
                mensaje = 'Vigente'
                icono = '<i class="fas fa-check"></i>'
            
            lote = {
                'insumo_id': insumo.id,
                'lote_id': insumo.lote_id,
                'cantidad': insumo.cantidad_existente,
                'unidad': insumo.unidad,
                'proveedor': insumo.proveedor_nombre if insumo.proveedor_nombre else 'Sin proveedor',
                'fecha_registro': insumo.fecha_registro.strftime('%d/%m/%Y') if insumo.fecha_registro else None,
                'fecha_caducidad': insumo.fecha_caducidad.strftime('%d/%m/%Y') if insumo.fecha_caducidad else None,
                'estado': estado,
                'mensaje': mensaje,
                'icono': icono,
                'esta_caducado': esta_caducado,
                'dias_restantes': dias_restantes
            }
            lotes_procesados.append(lote)
        
        return jsonify({'lotes': lotes_procesados})
    except Exception as e:
        print(f"Error en get_lotes: {str(e)}")
        return jsonify({'error': 'Error al obtener los lotes'}), 500

@inventario_bp.route('/lote/<string:lote_id>')
def get_lote(lote_id):
    try:
        # Obtener el lote específico
        insumo = u.obtener_lote_por_id(lote_id)

        if not insumo:
            return jsonify({
                'error': 'Lote no encontrado'
            }), 404
        
        # Asegurarnos de que la fecha de caducidad sea un objeto date
        fecha_caducidad = insumo.fecha_caducidad
        if isinstance(fecha_caducidad, datetime):
            fecha_caducidad = fecha_caducidad.date()
        
        # Calcular estado de caducidad
        esta_caducado, dias_restantes = u.calcular_estado_caducidad(fecha_caducidad)
        
        # Formatear los datos del lote
        lote = {
            'insumo_id': insumo.id,
            'lote_id': insumo.lote_id,
            'insumo_nombre': insumo.insumo_nombre,
            'tipo_insumo': insumo.tipo_insumo_nombre,
            'cantidad': insumo.cantidad_existente,
            'unidad': insumo.unidad,
            'proveedor': insumo.proveedor_nombre if insumo.proveedor_nombre else 'Sin proveedor',
            'proveedor_contacto': insumo.proveedor_contacto if insumo.proveedor_contacto else 'N/A',
            'proveedor_telefono': insumo.proveedor_telefono if insumo.proveedor_telefono else 'N/A',
            'fecha_registro': insumo.fecha_registro.strftime('%d/%m/%Y') if insumo.fecha_registro else None,
            'fecha_caducidad': fecha_caducidad.strftime('%d/%m/%Y') if fecha_caducidad else None,
            'esta_caducado': esta_caducado,
            'dias_restantes': dias_restantes,
            'modal_attrs': {
                'role': 'dialog',
                'aria-labelledby': 'loteModalLabel',
                'aria-modal': 'true',
                'tabindex': '-1'
            },
            'title_attrs': {
                'id': 'loteModalLabel'
            }
        }
        
        return jsonify({'lote': lote})
    except Exception as e:
        print(f"Error en get_lote: {str(e)}")
        db.session.rollback()
        return jsonify({
            'error': 'Error al obtener el lote',
            'detalle': str(e)
        }), 500

@inventario_bp.route('/mermas/agregar', methods=['POST'])
def agregar_merma_ajax():
    print("\n=== INICIO agregar_merma_ajax ===")
    try:
        print("1. Verificando si es una solicitud JSON...")
        if not request.is_json:
            print("ERROR: No es una solicitud JSON")
            return jsonify({
                'success': False,
                'message': 'Se requiere JSON'
            }), 400

        print("2. Obteniendo datos JSON...")
        data = request.get_json()
        print(f"Datos recibidos: {data}")

        print("3. Validando campos requeridos...")
        # Validar datos requeridos
        required_fields = ['insumo_id', 'cantidad_danada', 'motivo_merma']
        for field in required_fields:
            if field not in data:
                print(f"ERROR: Falta campo requerido: {field}")
                return jsonify({
                    'success': False,
                    'message': f'Falta el campo requerido: {field}'
                }), 400

        print("4. Registrando merma...")
        tipo_insumo_id, cantidad_restante = u.registrar_merma(
            data['insumo_id'],
            data['cantidad_danada'],
            data['motivo_merma']
        )

        return jsonify({
            'success': True,
            'message': 'Merma registrada exitosamente',
            'tipo_insumo_id': tipo_insumo_id,
            'cantidad_restante': cantidad_restante
        })
        
    except ValueError as e:
        print(f"ERROR DE VALIDACIÓN: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400
    except Exception as e:
        print(f"ERROR INESPERADO: {str(e)}")
        print(f"Tipo de error: {type(e).__name__}")
        import traceback
        print(f"Traceback completo: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'message': f'Error al registrar la merma: {str(e)}'
        }), 500
    finally:
        print("=== FIN agregar_merma_ajax ===\n")

@inventario_bp.route('/mermas/listar', methods=['GET'])
def listar_mermas():
    """
    Endpoint para obtener la lista de mermas registradas
    """
    try:
        # Obtener los datos de mermas usando la función de utils
        mermas = u.obtener_datos_mermas()
        
        # Formatear los datos para la respuesta
        mermas_formateadas = []
        for merma in mermas:
            mermas_formateadas.append({
                'id': merma['id'],
                'insumo_nombre': merma['insumo_nombre'],
                'tipo_insumo': merma['tipo_insumo'],
                'cantidad_danada': merma['cantidad_danada'],
                'unidad': merma['unidad'],
                'motivo_merma': merma['motivo_merma'],
                'fecha_merma': datetime.now().strftime('%Y-%m-%d')  # Usar fecha actual como fecha de merma
            })
        
        return jsonify({
            'success': True,
            'mermas': mermas_formateadas
        })
    except Exception as e:
        print(f"ERROR al listar mermas: {str(e)}")
        import traceback
        print(f"Traceback completo: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'message': f'Error al obtener las mermas: {str(e)}'
        }), 500

@inventario_bp.route('/insumos/agregar/ajax', methods=['POST'])
def agregar_insumo_ajax():
    print("\n=== INICIO agregar_insumo_ajax ===")
    print("1. Verificando si es una solicitud JSON...")
    try:
        if not request.is_json:
            print("ERROR: No es una solicitud JSON")
            return jsonify({
                'success': False,
                'error': 'Se requiere JSON'
            }), 400

        print("2. Verificando token CSRF...")
        # Verificar token CSRF
        csrf_token = request.headers.get('X-CSRFToken')
        print(f"Token CSRF recibido: {csrf_token}")
        print(f"Headers completos: {dict(request.headers)}")
        if not csrf_token:
            print("ERROR: Token CSRF no encontrado")
            return jsonify({
                'success': False,
                'error': 'Token CSRF no encontrado'
            }), 400

        print("3. Obteniendo datos JSON...")
        data = request.get_json()
        print(f"Datos recibidos: {data}")
        
        print("4. Validando campos requeridos...")
        # Validar campos requeridos
        required_fields = ['insumo_nombre', 'tipo_insumo_id', 'cantidad', 'unidad', 'lote_id', 'fecha_caducidad']
        for field in required_fields:
            print(f"Verificando campo: {field}")
            if field not in data:
                print(f"ERROR: Falta campo requerido: {field}")
                return jsonify({
                    'success': False,
                    'error': f'Falta el campo requerido: {field}'
                }), 400

        print("5. Validando cantidad...")
        # Validar que la cantidad no exceda 100 unidades
        try:
            cantidad = float(data['cantidad'])
            print(f"Cantidad recibida: {cantidad}")
            if cantidad <= 0:
                print("ERROR: Cantidad menor o igual a 0")
                return jsonify({
                    'success': False,
                    'error': 'La cantidad debe ser mayor a 0'
                }), 400
            if cantidad > 100:
                print("ERROR: Cantidad excede 100 unidades")
                return jsonify({
                    'success': False,
                    'error': 'La cantidad máxima por lote es de 100 unidades'
                }), 400
        except ValueError as e:
            print(f"ERROR: Cantidad no es un número válido: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'La cantidad debe ser un número válido'
            }), 400

        print("6. Validando fecha de caducidad...")
        # Validar que la fecha de caducidad sea futura
        try:
            fecha_caducidad = datetime.strptime(data['fecha_caducidad'], '%Y-%m-%d').date()
            print(f"Fecha caducidad: {fecha_caducidad}")
            if fecha_caducidad <= date.today():
                print("ERROR: Fecha de caducidad no es futura")
                return jsonify({
                    'success': False,
                    'error': 'La fecha de caducidad debe ser futura'
                }), 400
        except ValueError as e:
            print(f"ERROR: Formato de fecha inválido: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'Formato de fecha inválido. Use YYYY-MM-DD'
            }), 400
        
        print("7. Creando nuevo insumo...")
        # Crear nuevo insumo
        # Generar lote automáticamente si no se proporciona
        lote_id = data['lote_id']
        if not lote_id:
            # Obtener el último lote registrado
            ultimo_insumo = AdministracionInsumos.query.order_by(
                AdministracionInsumos.lote_id.desc()
            ).first()

            if ultimo_insumo and ultimo_insumo.lote_id:
                # Si existe un lote previo, extraer el número y aumentarlo
                try:
                    ultimo_numero = int(ultimo_insumo.lote_id[1:])  # Quitar la 'L' y convertir a número
                    siguiente_numero = ultimo_numero + 1
                except ValueError:
                    siguiente_numero = 1
            else:
                # Si no hay lotes previos, empezar desde 1
                siguiente_numero = 1

            # Formatear el nuevo número de lote (L001, L002, etc.)
            lote_id = f"L{siguiente_numero:03d}"
            print(f"Lote generado automáticamente: {lote_id}")
        
        nuevo_insumo = AdministracionInsumos(
            insumo_nombre=data['insumo_nombre'],
            tipo_insumo_id=data['tipo_insumo_id'],
            cantidad_existente=cantidad,
            unidad=data['unidad'],
            lote_id=lote_id,  # Usamos el lote_id generado o proporcionado
            fecha_registro=datetime.now(),
            fecha_caducidad=data['fecha_caducidad'] if data['fecha_caducidad'] else None
        )
        print(f"Insumo a crear: {nuevo_insumo.__dict__}")
        
        print("8. Agregando insumo a la base de datos...")
        db.session.add(nuevo_insumo)
        print("9. Confirmando cambios en la base de datos...")
        db.session.commit()
        print("10. Insumo agregado exitosamente")
        
        return jsonify({
            'success': True,
            'message': 'Insumo agregado exitosamente'
        })
    except Exception as e:
        print(f"ERROR INESPERADO: {str(e)}")
        print(f"Tipo de error: {type(e).__name__}")
        import traceback
        print(f"Traceback completo: {traceback.format_exc()}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Error al agregar el insumo: {str(e)}'
        }), 500
    finally:
        print("=== FIN agregar_insumo_ajax ===\n")

@inventario_bp.route('/galletas')
@login_required
def galletas():
    recetas = Recetas.query.filter_by(estatus=1).all()
    
    # Procesar cada receta para obtener la cantidad disponible
    recetas_procesadas = []
    for receta in recetas:
        # Obtener la cantidad disponible de galletas
        cantidad_disponible = db.session.query(
            func.sum(InformeProduccion.cantidad_disponible)
        ).filter(
            InformeProduccion.receta_id == receta.id
        ).scalar() or 0
        
        # Agregar la cantidad disponible a la receta
        receta.cantidad_disponible = cantidad_disponible
        recetas_procesadas.append(receta)
    
    form = SolicitarLoteForm()
    return render_template('inventario/galletas.html', recetas=recetas_procesadas, form=form)

@inventario_bp.route('/galletas/solicitar', methods=['POST'])
@login_required
def solicitar_galletas():
    try:
        receta_id = request.form.get('receta_id')
        cantidad = int(request.form.get('cantidad', 100))  # Por defecto 100 galletas

        if not receta_id:
            return jsonify({
                'success': False,
                'message': 'La receta es requerida'
            }), 400

        # Verificar que la receta existe
        receta = Recetas.query.get_or_404(receta_id)
        
        # Crear el pedido de galletas sin verificar insumos
        pedido = PedidoGalletas(
            usuario_id=current_user.id,
            receta_id=receta_id,
            cantidad=cantidad,
            estado_pedido_id=1,
            fecha_pedido=datetime.now(),
            estatus='Pedido'
        )
        
        db.session.add(pedido)
        db.session.commit()
        
        flash(f'Lote de {cantidad} galletas solicitado correctamente', 'success')
        
        # Redirigir a la página de galletas
        return redirect(url_for('inventario.galletas'))

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error al registrar el pedido: {str(e)}'
        }), 500

@inventario_bp.route('/atender', methods=['GET', 'POST'])
def atender_pedidos():
    print("\n=== INICIO atender_pedidos ===")
    print(f"Método de la solicitud: {request.method}")
    
    if request.method == 'GET':
        print("1. Procesando solicitud GET")
        # -----------------------------------------
        # MÉTODO GET - OBTENCIÓN DE PEDIDOS PENDIENTES
        # -----------------------------------------
        
        # 1. Consulta para obtener pedidos pendientes con sus relaciones
        pedidos_pendientes = u.obtener_pedidos_pendientes()
        
        # 2. Obtención de proveedores para el modal
        proveedores = Proveedores.query.all()

        # 3. Procesamiento de resultados para el template
        pedidos_procesados = [u.procesar_pedido(pedido) for pedido in pedidos_pendientes]

        # 4. Obtención de fecha actual para el template
        now = date.today()

        # 5. Contar pedidos pendientes
        total_pedidos_pendientes = len(pedidos_pendientes)

        return render_template('inventario/atender.html', 
                             pedidos_pendientes=pedidos_procesados,
                             proveedores=proveedores,
                             now=now,
                             total_pedidos_pendientes=total_pedidos_pendientes)

    elif request.method == 'POST':
        print("1. Procesando solicitud POST")
        try:
            print("2. Verificando token CSRF")
            csrf_token = request.headers.get('X-CSRFToken')
            print(f"Token CSRF recibido: {csrf_token}")
            print(f"Headers completos: {dict(request.headers)}")
            
            if not csrf_token:
                print("ERROR: Token CSRF no encontrado")
                return jsonify({
                    'success': False,
                    'message': 'Token CSRF no encontrado'
                }), 400

            print("3. Obteniendo datos del formulario")
            pedido_id = request.form.get('pedido_id')
            accion = request.form.get('accion')
            print(f"pedido_id: {pedido_id}")
            print(f"accion: {accion}")
            print(f"Datos completos del formulario: {dict(request.form)}")

            if not pedido_id or not accion:
                print("ERROR: Faltan datos requeridos")
                return jsonify({
                    'success': False,
                    'message': 'Faltan datos requeridos'
                }), 400

            print("4. Procesando pedido...")
            cantidad_recibida = request.form.get('cantidad_recibida') if accion == 'recibir' else None
            fecha_caducidad = request.form.get('fecha_caducidad') if accion == 'recibir' else None
            
            if accion == 'atender':
                # Obtener el pedido
                pedido = PedidoGalletas.query.get_or_404(pedido_id)
                
                # Calcular fecha de caducidad (7 semanas desde hoy)
                fecha_produccion = date.today()
                fecha_caducidad = fecha_produccion + timedelta(weeks=7)
                
                # Obtener la cantidad de merma del formulario
                merma = int(request.form.get('merma', 0))
                motivo_merma = request.form.get('motivo_merma', '')
                
                # Calcular cantidad disponible (cantidad producida - merma)
                cantidad_disponible = pedido.cantidad - merma
                
                # Crear registro en informe_produccion
                informe = InformeProduccion(
                    receta_id=pedido.receta_id,
                    cantidad_producida=pedido.cantidad,
                    fecha_produccion=fecha_produccion,
                    caducidad=fecha_caducidad,
                    merma=merma,
                    motivo_merma=motivo_merma,
                    cantidad_disponible=cantidad_disponible
                )
                db.session.add(informe)
                
                # Actualizar estado del pedido a "Atendido" (estado_pedido_id = 2)
                pedido.estado_pedido_id = 2
                pedido.fecha_atencion = datetime.now()
                
                db.session.commit()
                
                return jsonify({
                    'success': True,
                    'message': f'Pedido atendido correctamente. Se produjeron {pedido.cantidad} galletas con {merma} de merma. Caducidad: {fecha_caducidad.strftime("%d/%m/%Y")}'
                })
            else:
                mensaje = u.procesar_pedido_insumo(pedido_id, accion, cantidad_recibida, fecha_caducidad)
                return jsonify({
                    'success': True,
                    'message': mensaje
                })

        except ValueError as e:
            print(f"ERROR DE VALIDACIÓN: {str(e)}")
            return jsonify({
                'success': False,
                'message': str(e)
            }), 400
        except Exception as e:
            print(f"ERROR INESPERADO: {str(e)}")
            print(f"Tipo de error: {type(e).__name__}")
            import traceback
            print(f"Traceback completo: {traceback.format_exc()}")
            return jsonify({
                'success': False,
                'message': f'Error al procesar el pedido: {str(e)}'
            }), 500

    print("=== FIN atender_pedidos ===\n")

@inventario_bp.route('/atender/ultimo-lote')
def obtener_ultimo_lote():
    try:
        nuevo_lote = u.generar_nuevo_lote()
        return jsonify({
            'success': True,
            'nuevo_lote': nuevo_lote
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error al obtener el último lote: {str(e)}'
        }), 500

@inventario_bp.route('/insumos/caducados')
def get_insumos_caducados():
    try:
        # Obtener todos los insumos caducados
        insumos_caducados = u.obtener_insumos_caducados()
        
        insumos_procesados = []
        for insumo in insumos_caducados:
            esta_caducado, dias_restantes = u.calcular_estado_caducidad(insumo.fecha_caducidad)
            if esta_caducado and insumo.cantidad_existente > 0:
                insumos_procesados.append({
                    'insumo_id': insumo.id,
                    'lote_id': insumo.lote_id,
                    'nombre': insumo.insumo_nombre,
                    'cantidad': insumo.cantidad_existente,
                    'unidad': insumo.unidad,
                    'dias_caducado': abs(dias_restantes),
                    'fecha_caducidad': insumo.fecha_caducidad.strftime('%d/%m/%Y')
                })
        
        return jsonify({'insumos_caducados': insumos_procesados})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@inventario_bp.route('/merma/multiple', methods=['POST'])
#@login_required
def registrar_mermas_multiple():
    try:
        data = request.get_json()
        mermas = data.get('mermas', [])
        
        for merma in mermas:
            u.registrar_merma(
                insumo_id=merma['insumo_id'],
                lote_id=merma['lote_id'],
                cantidad=merma['cantidad'],
                motivo="Caducidad del producto"
            )
        
        return jsonify({'message': 'Mermas registradas exitosamente'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@inventario_bp.route('/gestion-insumos', methods=['GET', 'POST'])
@login_required
def gestion_insumos():
    try:
        # Obtener parámetros de filtrado
        page = request.args.get('page', 1, type=int)
        filtro_nombre = request.args.get('filtro_nombre', '')
        filtro_categoria = request.args.get('filtro_categoria', '')
        filtro_lote = request.args.get('filtro_lote', '')
        
        # Construir la consulta base
        query = db.session.query(
            AdministracionInsumos, 
            TipoInsumo, 
            InsumoProveedor, 
            Proveedores
        ).join(
            TipoInsumo, 
            AdministracionInsumos.tipo_insumo_id == TipoInsumo.id
        ).outerjoin(
            InsumoProveedor, 
            AdministracionInsumos.id == InsumoProveedor.insumo_id
        ).outerjoin(
            Proveedores, 
            InsumoProveedor.proveedor_id == Proveedores.id
        )
        
        # Aplicar filtros
        if filtro_nombre:
            query = query.filter(AdministracionInsumos.insumo_nombre.ilike(f'%{filtro_nombre}%'))
        if filtro_categoria:
            # Corregir: Filtrar por nombre de categoría en lugar de ID
            query = query.filter(TipoInsumo.nombre == filtro_categoria)
        if filtro_lote:
            query = query.filter(AdministracionInsumos.lote_id.ilike(f'%{filtro_lote}%'))
        
        # Ordenar por ID de forma descendente
        query = query.order_by(AdministracionInsumos.id.desc())
        
        # Paginación
        pagination = query.paginate(page=page, per_page=10, error_out=False)
        insumos = pagination.items
        
        # Calcular totales por categoría
        totales_por_categoria = {}
        
        # Obtener todos los insumos para calcular totales (sin paginación)
        todos_insumos = db.session.query(
            AdministracionInsumos, 
            TipoInsumo
        ).join(
            TipoInsumo, 
            AdministracionInsumos.tipo_insumo_id == TipoInsumo.id
        ).all()
        
        for insumo, tipo in todos_insumos:
            categoria_id = tipo.id
            cantidad = insumo.cantidad_existente or 0
            unidad = insumo.unidad
            
            if categoria_id not in totales_por_categoria:
                totales_por_categoria[categoria_id] = {
                    'nombre': tipo.nombre,
                    'total': 0,
                    'unidad': unidad
                }
            
            # Convertir unidades si es necesario
            if unidad == 'g' and totales_por_categoria[categoria_id]['unidad'] == 'kg':
                cantidad = cantidad / 1000
            elif unidad == 'ml' and totales_por_categoria[categoria_id]['unidad'] == 'l':
                cantidad = cantidad / 1000
                
            totales_por_categoria[categoria_id]['total'] += cantidad
        
        # Obtener todas las categorías para el filtro
        categorias = TipoInsumo.query.all()
        
        # Formularios
        form_insumo = NuevoInsumoForm()
        form_categoria = CategoriaInsumoForm()
        
        # Cargar opciones para los selectores
        form_insumo.categoria_id.choices = [(0, 'Seleccione una categoría')] + [(c.id, c.nombre) for c in categorias]
        form_insumo.proveedor_id.choices = [(0, 'Seleccione un proveedor')]
        form_insumo.unidad_medida.choices = [
            (0, 'Seleccione una unidad'),
            ('kg', 'Kilogramos'),
            ('g', 'Gramos'),
            ('l', 'Litros'),
            ('ml', 'Mililitros'),
            ('unidad', 'Unidad'),
            ('paquete', 'Paquete'),
            ('caja', 'Caja')
        ]
        
        if request.method == 'POST':
            form_type = request.form.get('form_type')
            
            if form_type == 'insumo' and form_insumo.validate_on_submit():
                try:
                    # Obtener el siguiente lote si no se proporciona uno
                    lote_id = form_insumo.lote_id.data
                    if not lote_id:
                        lote_id = u.generar_nuevo_lote()
                    
                    # Crear el insumo
                    nuevo_insumo = AdministracionInsumos(
                        insumo_nombre=form_insumo.nombre.data,
                        tipo_insumo_id=form_insumo.categoria_id.data,
                        unidad=form_insumo.unidad_medida.data,
                        lote_id=lote_id,
                        fecha_caducidad=form_insumo.fecha_caducidad.data,
                        cantidad_existente=form_insumo.cantidad.data
                    )
                    db.session.add(nuevo_insumo)
                    db.session.flush()  # Para obtener el ID del insumo
                    
                    # Crear la relación con el proveedor
                    rel_proveedor = InsumoProveedor(
                        insumo_id=nuevo_insumo.id,
                        proveedor_id=form_insumo.proveedor_id.data,
                        precio=form_insumo.precio_unitario.data,
                        unidad=form_insumo.unidad_medida.data
                    )
                    db.session.add(rel_proveedor)
                    
                    db.session.commit()
                    flash('Insumo agregado exitosamente', 'success')
                    return redirect(url_for('inventario.gestion_insumos'))
                    
                except Exception as e:
                    db.session.rollback()
                    flash(f'Error al agregar el insumo: {str(e)}', 'danger')
                    app.logger.error(f'Error al agregar insumo: {str(e)}')
            
            elif form_type == 'categoria' and form_categoria.validate_on_submit():
                try:
                    nueva_categoria = TipoInsumo(nombre=form_categoria.nombre.data)
                    db.session.add(nueva_categoria)
                    db.session.commit()
                    flash('Categoría agregada exitosamente', 'success')
                    return redirect(url_for('inventario.gestion_insumos'))
                    
                except Exception as e:
                    db.session.rollback()
                    flash(f'Error al agregar la categoría: {str(e)}', 'danger')
                    app.logger.error(f'Error al agregar categoría: {str(e)}')
        
        return render_template('inventario/gestion_insumos.html',
                             form_insumo=form_insumo,
                             form_categoria=form_categoria,
                             insumos=insumos,
                             categorias=categorias,
                             totales_por_categoria=totales_por_categoria,
                             pagination=pagination,
                             filtro_nombre=filtro_nombre,
                             filtro_categoria=filtro_categoria,
                             filtro_lote=filtro_lote)
    except Exception as e:
        app.logger.error(f'Error en gestion_insumos: {str(e)}')
        flash(f'Error al cargar la página: {str(e)}', 'danger')
        return redirect(url_for('inventario.index'))

@inventario_bp.route('/obtener-siguiente-lote')
@login_required
def obtener_siguiente_lote():
    try:
        # Obtener el último lote registrado
        ultimo_insumo = AdministracionInsumos.query.order_by(
            AdministracionInsumos.lote_id.desc()
        ).first()

        if ultimo_insumo and ultimo_insumo.lote_id:
            # Si existe un lote previo, extraer el número y aumentarlo
            try:
                ultimo_numero = int(ultimo_insumo.lote_id[1:])  # Quitar la 'L' y convertir a número
                siguiente_numero = ultimo_numero + 1
            except ValueError:
                siguiente_numero = 1
        else:
            # Si no hay lotes previos, empezar desde 1
            siguiente_numero = 1

        # Formatear el nuevo número de lote (L001, L002, etc.)
        nuevo_lote = f"L{siguiente_numero:03d}"
        
        print(f"Generando nuevo lote: {nuevo_lote}")  # Debug print
        
        return jsonify({
            'success': True,
            'lote': nuevo_lote
        })
    except Exception as e:
        print(f"Error al generar lote: {str(e)}")  # Debug print
        return jsonify({
            'success': False,
            'message': str(e)
        })

@inventario_bp.route('/categorias/listar')
@login_required
def listar_categorias():
    """
    Endpoint para obtener la lista de categorías de insumos
    """
    try:
        # Obtener todas las categorías ordenadas por nombre
        categorias = TipoInsumo.query.order_by(TipoInsumo.nombre).all()
        
        # Formatear los datos para la respuesta
        categorias_formateadas = [{
            'id': categoria.id,
            'nombre': categoria.nombre
        } for categoria in categorias]
        
        return jsonify({
            'success': True,
            'categorias': categorias_formateadas
        })
    except Exception as e:
        print(f"ERROR al listar categorías: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error al obtener las categorías: {str(e)}'
        }), 500

@inventario_bp.route('/insumos/tipo/<int:tipo_id>', methods=['GET'])
@login_required
@rol_requerido(1, 2)  # Admin y Producción
def insumos_por_tipo(tipo_id):
    """
    Endpoint para obtener los insumos de un tipo específico
    """
    try:
        # Verificar si el tipo existe
        tipo = TipoInsumo.query.get_or_404(tipo_id)
        
        # Obtener los insumos del tipo agrupados por nombre
        insumos = db.session.query(
            AdministracionInsumos.insumo_nombre,
            AdministracionInsumos.unidad,
            func.sum(AdministracionInsumos.cantidad_existente).label('cantidad_total')
        ).filter(
            AdministracionInsumos.tipo_insumo_id == tipo_id
        ).group_by(
            AdministracionInsumos.insumo_nombre,
            AdministracionInsumos.unidad
        ).all()
        
        # Formatear los datos para la respuesta
        insumos_formateados = [{
            'nombre': insumo[0],
            'unidad': insumo[1],
            'cantidad': float(insumo[2] or 0)
        } for insumo in insumos]
        
        # Obtener proveedores únicos para este tipo de insumo
        proveedores = db.session.query(
            Proveedores.id,
            Proveedores.nombre_empresa,
            func.min(InsumoProveedor.precio).label('precio_min')
        ).join(
            InsumoProveedor,
            Proveedores.id == InsumoProveedor.proveedor_id
        ).join(
            AdministracionInsumos,
            InsumoProveedor.insumo_id == AdministracionInsumos.id
        ).filter(
            AdministracionInsumos.tipo_insumo_id == tipo_id
        ).group_by(
            Proveedores.id,
            Proveedores.nombre_empresa
        ).distinct(Proveedores.id).all()
        
        # Formatear proveedores
        proveedores_formateados = [{
            'id': p[0],
            'nombre': p[1],
            'precio': float(p[2]) if p[2] else 0
        } for p in proveedores]
        
        # Generar nuevo lote
        nuevo_lote = u.generar_nuevo_lote()
        
        # Preparar la respuesta
        respuesta = {
            'success': True,
            'tipo': tipo.nombre,
            'insumos': insumos_formateados,
            'proveedores': proveedores_formateados,
            'nuevo_lote': nuevo_lote
        }
        
        # Registrar la respuesta en el log
        app.logger.info(f"Respuesta de insumos_por_tipo: {respuesta}")
        
        return jsonify(respuesta)
    except Exception as e:
        app.logger.error(f"Error al obtener insumos por tipo: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error al obtener los insumos: {str(e)}'
        }), 500

@inventario_bp.route('/registrar-merma/<int:insumo_id>', methods=['GET', 'POST'])
@login_required
def registrar_merma(insumo_id):
    insumo = AdministracionInsumos.query.get_or_404(insumo_id)
    form = MermaInsumoForm()
    form.insumo_id.data = insumo_id
    
    if form.validate_on_submit():
        try:
            # Crear nueva merma sin el campo fecha_registro
            nueva_merma = MermaInsumos(
                insumo_id=form.insumo_id.data,
                cantidad_danada=form.cantidad_danada.data,
                motivo_merma=form.motivo_merma.data
            )
            
            # Actualizar cantidad existente del insumo
            insumo.cantidad_existente -= form.cantidad_danada.data
            
            # Registrar la acción
            log_user_action('merma_registrada')(lambda: None)()
            
            db.session.add(nueva_merma)
            db.session.commit()
            
            flash('Merma registrada exitosamente.', 'success')
            return redirect(url_for('inventario.gestion_insumos'))
            
        except Exception as e:
            # Registrar el error
            log_error('database')(lambda: None)()
            
            db.session.rollback()
            flash('Error al registrar la merma. Por favor, intente nuevamente.', 'error')
            return redirect(url_for('inventario.gestion_insumos'))
    
    return render_template('inventario/registrar_merma.html', form=form, insumo=insumo)

@inventario_bp.route('/insumos-stock/')
@inventario_bp.route('/insumos-stock/<nombre>')
@inventario_bp.route('/insumos-stock/categoria/<int:categoria_id>')
@inventario_bp.route('/insumos-stock/<nombre>/categoria/<int:categoria_id>')
def obtener_insumos_stock(nombre=None, categoria_id=None):
    """
    Endpoint para obtener información de stock de insumos.
    Permite filtrar por nombre, categoría o ambos.
    Siempre devuelve un JSON con los datos.
    """
    try:
        # Obtener parámetros de la URL
        page = request.args.get('page', 1, type=int)
        per_page = 10  # Elementos por página
        
        # Construir la consulta base
        query = db.session.query(
            AdministracionInsumos,
            TipoInsumo,
            InsumoProveedor,
            Proveedores
        ).join(
            TipoInsumo, AdministracionInsumos.tipo_insumo_id == TipoInsumo.id
        ).outerjoin(
            InsumoProveedor, AdministracionInsumos.id == InsumoProveedor.insumo_id
        ).outerjoin(
            Proveedores, InsumoProveedor.proveedor_id == Proveedores.id
        )
        
        # Aplicar filtros según los parámetros recibidos
        if nombre:
            query = query.filter(AdministracionInsumos.insumo_nombre.ilike(f'%{nombre}%'))
        
        if categoria_id:
            query = query.filter(AdministracionInsumos.tipo_insumo_id == categoria_id)
        
        # Aplicar paginación
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        # Procesar los resultados
        insumos_detalle = []
        insumos_agrupados = {}
        totales_por_categoria = {}
        
        for admin, tipo, insumo_prov, proveedor in pagination.items:
            # Crear objeto de detalle
            insumo_detalle = {
                'id': admin.id,
                'nombre': admin.insumo_nombre,
                'categoria': tipo.nombre,
                'lote_id': admin.lote_id,
                'cantidad': admin.cantidad_existente,
                'unidad': admin.unidad,
                'precio': insumo_prov.precio if insumo_prov else None,
                'proveedor': proveedor.nombre_empresa if proveedor else None,
                'fecha_caducidad': admin.fecha_caducidad.strftime('%Y-%m-%d') if admin.fecha_caducidad else None
            }
            insumos_detalle.append(insumo_detalle)
            
            # Agrupar por nombre para las cards
            if admin.insumo_nombre not in insumos_agrupados:
                insumos_agrupados[admin.insumo_nombre] = {
                    'nombre': admin.insumo_nombre,
                    'categoria': tipo.nombre,
                    'unidad': admin.unidad,
                    'stock': 0,
                    'estado': 'Sin stock',
                    'lotes': []
                }
            
            # Agregar lote al insumo agrupado
            lote = {
                'id': admin.id,
                'lote_id': admin.lote_id,
                'cantidad': admin.cantidad_existente,
                'unidad': admin.unidad,
                'precio': insumo_prov.precio if insumo_prov else None,
                'proveedor': proveedor.nombre_empresa if proveedor else None,
                'caducidad': admin.fecha_caducidad.strftime('%Y-%m-%d') if admin.fecha_caducidad else None
            }
            insumos_agrupados[admin.insumo_nombre]['lotes'].append(lote)
            
            # Actualizar stock total
            insumos_agrupados[admin.insumo_nombre]['stock'] += admin.cantidad_existente
            
            # Actualizar totales por categoría
            if tipo.id not in totales_por_categoria:
                totales_por_categoria[tipo.id] = {
                    'nombre': tipo.nombre,
                    'total': 0,
                    'unidad': admin.unidad
                }
            totales_por_categoria[tipo.id]['total'] += admin.cantidad_existente
        
        # Determinar estado de stock para cada insumo agrupado
        for nombre, insumo in insumos_agrupados.items():
            if insumo['stock'] <= 0:
                insumo['estado'] = 'Sin stock'
            elif insumo['stock'] < 10:
                insumo['estado'] = 'Poco'
            else:
                insumo['estado'] = 'Disponible'
        
        # Convertir el diccionario de insumos agrupados a lista
        insumos_agrupados_list = list(insumos_agrupados.values())
        
        # Preparar respuesta
        response_data = {
            'success': True,
            'insumos_agrupados': insumos_agrupados_list,
            'insumos_detalle': insumos_detalle,
            'totales_por_categoria': totales_por_categoria,
            'pagination': {
                'page': page,
                'pages': pagination.pages,
                'total': pagination.total,
                'per_page': per_page
            }
        }
        
        # Siempre devolver JSON
        return jsonify(response_data)
        
    except Exception as e:
        current_app.logger.error(f"Error al obtener insumos: {str(e)}")
        return jsonify({
            'success': False,
            'error': f"Error al obtener insumos: {str(e)}"
        }), 500

@inventario_bp.route('/lotes/categoria/<int:categoria_id>')
@login_required
@rol_requerido(1, 2)
def obtener_lotes_por_categoria(categoria_id):
    """
    Endpoint para obtener los lotes de una categoría específica
    """
    try:
        # Verificar si la categoría existe
        tipo = TipoInsumo.query.get_or_404(categoria_id)
        
        # Obtener todos los insumos de la categoría
        insumos = db.session.query(
            AdministracionInsumos
        ).filter(
            AdministracionInsumos.tipo_insumo_id == categoria_id
        ).all()
        
        # Procesar los lotes
        lotes_procesados = []
        for insumo in insumos:
            # Obtener el proveedor
            insumo_proveedor = InsumoProveedor.query.filter_by(insumo_id=insumo.id).first()
            proveedor = Proveedores.query.get(insumo_proveedor.proveedor_id) if insumo_proveedor else None
            
            # Calcular estado de caducidad
            esta_caducado, dias_restantes = u.calcular_estado_caducidad(insumo.fecha_caducidad)
            
            # Determinar el estado y mensaje
            if insumo.cantidad_existente <= 0:
                estado = 'terminado'
                mensaje = 'Terminado'
                icono = '<i class="fas fa-check-circle"></i>'
            elif esta_caducado:
                estado = 'caduco'
                mensaje = f'Caducado hace {abs(dias_restantes)} días'
                icono = '<i class="fas fa-exclamation-triangle"></i>'
            elif dias_restantes is not None and dias_restantes <= 30:
                estado = 'proximo_caducar'
                mensaje = f'Caduca en {dias_restantes} días'
                icono = '<i class="fas fa-exclamation-circle"></i>'
            else:
                estado = 'vigente'
                mensaje = 'Vigente'
                icono = '<i class="fas fa-check"></i>'
            
            lote = {
                'insumo_id': insumo.id,
                'insumo_nombre': insumo.insumo_nombre,
                'lote_id': insumo.lote_id,
                'cantidad': insumo.cantidad_existente,
                'unidad': insumo.unidad,
                'proveedor': proveedor.nombre_empresa if proveedor else 'Sin proveedor',
                'fecha_registro': insumo.fecha_registro.strftime('%d/%m/%Y') if insumo.fecha_registro else None,
                'fecha_caducidad': insumo.fecha_caducidad.strftime('%d/%m/%Y') if insumo.fecha_caducidad else None,
                'estado': estado,
                'mensaje': mensaje,
                'icono': icono,
                'esta_caducado': esta_caducado,
                'dias_restantes': dias_restantes
            }
            lotes_procesados.append(lote)
        
        # Ordenar los lotes por fecha de caducidad
        lotes_procesados.sort(key=lambda x: x['fecha_caducidad'] if x['fecha_caducidad'] else '9999/99/99')
        
        return jsonify({
            'success': True,
            'categoria': tipo.nombre,
            'lotes': lotes_procesados
        })
    except Exception as e:
        print(f"Error al obtener lotes por categoría: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error al obtener los lotes: {str(e)}'
        }), 500