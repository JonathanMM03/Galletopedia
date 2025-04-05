from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, Recetas, InformeProduccion, InformeVentas, DetalleVenta, TipoVenta, PedidoGalletas, TipoInsumo, Proveedores, AdministracionInsumos, InsumoProveedor
from datetime import datetime, timedelta
from . import ventas_bp  # Importamos el blueprint desde __init__.py
import base64
from sqlalchemy import func, extract
from forms import VentaForm, DetalleVentaForm
from decorators import rol_requerido

ventas_bp = Blueprint('ventas', __name__, url_prefix='/ventas')

def procesar_imagen(imagen):
    """Procesa la imagen de la receta para mostrarla en el frontend"""
    try:
        if imagen:
            if isinstance(imagen, bytes):
                # Si es bytes, convertir a base64
                imagen_base64 = base64.b64encode(imagen).decode('utf-8')
                return f"data:image/jpeg;base64,{imagen_base64}"
            elif isinstance(imagen, str):
                # Si ya es string, verificar si ya tiene el prefijo
                if not imagen.startswith('data:image'):
                    return f"data:image/jpeg;base64,{imagen}"
                return imagen
    except Exception as e:
        print(f"Error procesando imagen: {str(e)}")
    return None

@ventas_bp.route('/punto-venta')
@login_required
def punto_venta():
    try:
        # Obtener recetas disponibles
        recetas_disponibles = Recetas.query.all()
        productos = []
        stock_dict = {}

        for receta in recetas_disponibles:
            # Calcular stock desde informe_produccion
            stock_total = db.session.query(
                func.coalesce(
                    func.sum(InformeProduccion.cantidad_disponible), 0
                )
            ).filter(
                InformeProduccion.receta_id == receta.id
            ).group_by(
                InformeProduccion.receta_id
            ).scalar() or 0

            print(f"Receta: {receta.nombre}, Stock calculado: {stock_total}")
            
            # Procesar imagen
            imagen_base64 = None
            try:
                if receta.imagen:
                    if isinstance(receta.imagen, bytes):
                        imagen_base64 = base64.b64encode(receta.imagen).decode('utf-8')
                        imagen_base64 = f"data:image/jpeg;base64,{imagen_base64}"
                    elif isinstance(receta.imagen, str):
                        if not receta.imagen.startswith('data:image'):
                            imagen_base64 = f"data:image/jpeg;base64,{receta.imagen}"
                        else:
                            imagen_base64 = receta.imagen
            except Exception as img_error:
                print(f"Error procesando imagen de {receta.nombre}: {str(img_error)}")
                imagen_base64 = None

            producto = {
                'id': receta.id,
                'nombre': receta.nombre,
                'precio_venta': float(receta.precio_venta),
                'stock': int(stock_total),
                'gramaje_por_galleta': float(receta.gramaje_por_galleta),
                'imagen_base64': imagen_base64
            }
            productos.append(producto)
            stock_dict[receta.id] = int(stock_total)

        print(f"Stock final calculado: {stock_dict}")
        print(f"Total de productos cargados: {len(productos)}")

        return render_template(
            'ventas/intraPVenta.html',
            productos=productos,
            stock_dict=stock_dict
        )

    except Exception as e:
        print(f"Error en punto_venta: {str(e)}")
        return str(e), 500

@ventas_bp.route('/registrar', methods=['POST'])
@login_required
def registrar_venta():
    try:
        data = request.get_json()
        
        # Crear venta
        venta = InformeVentas(
            usuario_id=current_user.id,
            total_venta=data['total'],
            descuento_aplicado=data['descuento_porcentaje'],
            cliente_pago=data['pago'],
            cambio=data['cambio'],
            fecha_venta=datetime.now()
        )
        db.session.add(venta)
        db.session.flush()

        # Procesar items
        for item in data['items']:
            # Obtener el lote más antiguo que tenga cantidad disponible
            lote = InformeProduccion.query.filter_by(
                receta_id=item['producto_id']
            ).filter(
                InformeProduccion.cantidad_disponible > 0
            ).order_by(
                InformeProduccion.fecha_produccion.asc()
            ).first()

            if not lote or lote.cantidad_disponible < item['cantidad']:
                return jsonify({
                    'success': False,
                    'message': f'No hay suficiente stock disponible para {item["nombre"]}'
                }), 400

            # Crear detalle de venta
            detalle = DetalleVenta(
                venta_id=venta.id,
                receta_id=item['producto_id'],
                cantidad=item['cantidad'],
                precio_unitario=item['precio_unitario'],
                tipo_venta=item['tipo']
            )
            db.session.add(detalle)

            # Actualizar cantidad disponible en el lote
            lote.cantidad_disponible -= item['cantidad']
            print(f"Detalle de venta creado para receta {item['producto_id']}, cantidad: {item['cantidad']}, tipo: {item['tipo']}")

        db.session.commit()
        return jsonify({
            'success': True,
            'message': 'Venta registrada correctamente',
            'folio': venta.id
        })

    except Exception as e:
        db.session.rollback()
        print(f"Error al registrar venta: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400

@ventas_bp.route('/')
@login_required
@rol_requerido(1, 4)  # Admin y Ventas
def index():
    try:
        # Obtener el primer día del mes actual
        primer_dia_mes = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        print(f"Primer día del mes: {primer_dia_mes}")
        
        # Calcular el total de ventas del mes
        total_ventas_mes = db.session.query(
            func.coalesce(func.sum(InformeVentas.total_venta), 0)
        ).filter(
            InformeVentas.fecha_venta >= primer_dia_mes
        ).scalar() or 0.0
        print(f"Total ventas mes: {total_ventas_mes}")
        
        # Obtener el total de galletas vendidas del mes
        total_galletas_mes = db.session.query(
            func.coalesce(func.sum(DetalleVenta.cantidad), 0)
        ).join(InformeVentas, DetalleVenta.venta_id == InformeVentas.id
        ).filter(
            InformeVentas.fecha_venta >= primer_dia_mes
        ).scalar() or 0
        print(f"Total galletas vendidas: {total_galletas_mes}")
        
        # Obtener el total de galletas producidas del mes
        total_galletas_producidas_mes = db.session.query(
            func.coalesce(func.sum(InformeProduccion.cantidad_producida), 0)
        ).filter(
            InformeProduccion.fecha_produccion >= primer_dia_mes
        ).scalar() or 0
        print(f"Total galletas producidas: {total_galletas_producidas_mes}")
        
        # Calcular la eficiencia (galletas vendidas / galletas producidas * 100)
        eficiencia = 0
        if total_galletas_producidas_mes > 0:
            # Convertir ambos valores a float para evitar problemas de tipos
            eficiencia = round((float(total_galletas_mes) / float(total_galletas_producidas_mes)) * 100, 2)
        print(f"Eficiencia: {eficiencia}%")
        
        # Obtener datos para el gráfico de ingresos diarios (últimos 30 días)
    fecha_fin = datetime.now()
    fecha_inicio = fecha_fin - timedelta(days=30)
        print(f"Rango de fechas para ventas diarias: {fecha_inicio} a {fecha_fin}")
    
    ventas_diarias = db.session.query(
        func.date(InformeVentas.fecha_venta).label('fecha'),
        func.sum(InformeVentas.total_venta).label('total')
    ).filter(
        InformeVentas.fecha_venta.between(fecha_inicio, fecha_fin)
    ).group_by(
            func.date(InformeVentas.fecha_venta)
        ).order_by(
        func.date(InformeVentas.fecha_venta)
    ).all()
    
        fechas = [venta.fecha.strftime('%Y-%m-%d') for venta in ventas_diarias]
        totales = [float(venta.total) for venta in ventas_diarias]
        print(f"Ventas diarias - Fechas: {fechas}")
        print(f"Ventas diarias - Totales: {totales}")
        
        # Obtener datos para el gráfico de galletas más vendidas
    galletas_vendidas = db.session.query(
        Recetas.nombre,
            func.sum(DetalleVenta.cantidad).label('cantidad_total')
        ).join(DetalleVenta, Recetas.id == DetalleVenta.receta_id
        ).join(InformeVentas, DetalleVenta.venta_id == InformeVentas.id
    ).filter(
            InformeVentas.fecha_venta >= primer_dia_mes
    ).group_by(
            Recetas.id
    ).order_by(
        func.sum(DetalleVenta.cantidad).desc()
    ).limit(5).all()
    
        galletas_vendidas_nombres = [g.nombre for g in galletas_vendidas]
        galletas_vendidas_cantidades = [int(g.cantidad_total) for g in galletas_vendidas]
        print(f"Galletas más vendidas - Nombres: {galletas_vendidas_nombres}")
        print(f"Galletas más vendidas - Cantidades: {galletas_vendidas_cantidades}")
        
        # Obtener datos para el gráfico de galletas más producidas
    galletas_producidas = db.session.query(
        Recetas.nombre,
            func.sum(InformeProduccion.cantidad_producida).label('cantidad_total')
        ).join(InformeProduccion, Recetas.id == InformeProduccion.receta_id
    ).filter(
            InformeProduccion.fecha_produccion >= primer_dia_mes
    ).group_by(
            Recetas.id
    ).order_by(
        func.sum(InformeProduccion.cantidad_producida).desc()
    ).limit(5).all()
    
    galletas_producidas_nombres = [g.nombre for g in galletas_producidas]
        galletas_producidas_cantidades = [int(g.cantidad_total) for g in galletas_producidas]
        print(f"Galletas más producidas - Nombres: {galletas_producidas_nombres}")
        print(f"Galletas más producidas - Cantidades: {galletas_producidas_cantidades}")
    
    return render_template('ventas/index.html',
            total_ventas_mes=total_ventas_mes,
            total_galletas_mes=total_galletas_mes,
            total_galletas_producidas_mes=total_galletas_producidas_mes,
            eficiencia=eficiencia,
                          fechas=fechas,
                          totales=totales,
                          galletas_vendidas_nombres=galletas_vendidas_nombres,
                          galletas_vendidas_cantidades=galletas_vendidas_cantidades,
                          galletas_producidas_nombres=galletas_producidas_nombres,
            galletas_producidas_cantidades=galletas_producidas_cantidades
        )
    except Exception as e:
        print(f"Error en index de ventas: {str(e)}")
        return render_template('ventas/index.html',
            total_ventas_mes=0,
            total_galletas_mes=0,
            total_galletas_producidas_mes=0,
            eficiencia=0,
            fechas=[],
            totales=[],
            galletas_vendidas_nombres=[],
            galletas_vendidas_cantidades=[],
            galletas_producidas_nombres=[],
            galletas_producidas_cantidades=[]
        )

@ventas_bp.route('/nueva', methods=['GET', 'POST'])
@login_required
@rol_requerido(1, 4)  # Admin y Ventas
def nueva():
    form = VentaForm()
    if form.validate_on_submit():
        venta = InformeVentas(
            usuario_id=current_user.id,
            total_venta=form.total_venta.data,
            descuento_aplicado=form.descuento_aplicado.data,
            cliente_pago=form.cliente_pago.data,
            cambio=form.cambio.data
        )
        db.session.add(venta)
        db.session.commit()
        flash('Venta registrada correctamente', 'success')
        return redirect(url_for('ventas.index'))
    return render_template("ventas/nueva.html", form=form)

@ventas_bp.route('/detalle/<int:id>')
@login_required
@rol_requerido(1, 4)  # Admin y Ventas
def detalle(id):
    venta = InformeVentas.query.get_or_404(id)
    return render_template("ventas/detalle.html", venta=venta)

@ventas_bp.route('/agregar_detalle/<int:venta_id>', methods=['GET', 'POST'])
@login_required
@rol_requerido(1, 4)  # Admin y Ventas
def agregar_detalle(venta_id):
    venta = InformeVentas.query.get_or_404(venta_id)
    form = DetalleVentaForm()
    if form.validate_on_submit():
        detalle = DetalleVenta(
            venta_id=venta_id,
            receta_id=form.receta_id.data,
            tipo_venta=form.tipo_venta.data,
            cantidad=form.cantidad.data,
            precio_unitario=form.precio_unitario.data
        )
        db.session.add(detalle)
        db.session.commit()
        flash('Detalle agregado correctamente', 'success')
        return redirect(url_for('ventas.detalle', id=venta_id))
    return render_template("ventas/agregar_detalle.html", form=form, venta=venta)

@ventas_bp.route('/solicitar-produccion', methods=['POST'])
@login_required
def solicitar_produccion():
    try:
        data = request.get_json()
        
        # Crear nuevo pedido de producción
        nuevo_pedido = PedidoGalletas(
            usuario_id=current_user.id,
            receta_id=data['receta_id'],
            cantidad=data['cantidad'],
            cantidad_producida=0,  # Inicia en 0
            estado_pedido_id=1,    # Estado pendiente
            fecha_pedido=datetime.now(),
            estatus='Pendiente',
            fecha_actualizacion=datetime.now()
        )
        
        db.session.add(nuevo_pedido)
        db.session.commit()

        print(f"Pedido de producción creado: ID {nuevo_pedido.id}")
        
        return jsonify({
            'success': True,
            'message': 'Solicitud de producción registrada correctamente'
        })

    except Exception as e:
        db.session.rollback()
        print(f"Error al solicitar producción: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400

@ventas_bp.route('/gestion-insumos', methods=['GET', 'POST'])
@login_required
def gestion_insumos():
    print("\n=== INICIO gestion_insumos ===")
    try:
        form_insumo = NuevoInsumoForm()
        form_categoria = CategoriaInsumoForm()

        # Cargar las opciones para los SelectField
        # Categorías
        categorias = TipoInsumo.query.order_by(TipoInsumo.nombre).all()
        form_insumo.categoria_id.choices = [(c.id, c.nombre) for c in categorias]

        # Proveedores
        proveedores = Proveedores.query.order_by(Proveedores.nombre_empresa).all()
        form_insumo.proveedor_id.choices = [(p.id, p.nombre_empresa) for p in proveedores]

        print(f"Categorías cargadas: {len(form_insumo.categoria_id.choices)}")
        print(f"Proveedores cargados: {len(form_insumo.proveedor_id.choices)}")

        if request.method == 'POST':
            if form_insumo.validate_on_submit():
                try:
                    # Crear nuevo insumo
                    nuevo_insumo = AdministracionInsumos(
                        nombre=form_insumo.nombre.data,
                        descripcion=form_insumo.descripcion.data,
                        cantidad=form_insumo.cantidad.data,
                        unidad_medida=form_insumo.unidad_medida.data,
                        tipo_insumo_id=form_insumo.categoria_id.data,
                        precio_unitario=form_insumo.precio_unitario.data,
                        stock_minimo=form_insumo.stock_minimo.data,
                        fecha_registro=datetime.now()
                    )
                    db.session.add(nuevo_insumo)
                    db.session.flush()  # Para obtener el ID del nuevo insumo

                    # Crear relación con proveedor
                    insumo_proveedor = InsumoProveedor(
                        insumo_id=nuevo_insumo.id,
                        proveedor_id=form_insumo.proveedor_id.data,
                        fecha_registro=datetime.now()
                    )
                    db.session.add(insumo_proveedor)
                    db.session.commit()

                    flash('Insumo registrado correctamente', 'success')
                    return redirect(url_for('ventas.gestion_insumos'))

                except Exception as e:
                    db.session.rollback()
                    print(f"Error al registrar insumo: {str(e)}")
                    flash('Error al registrar el insumo', 'error')

            else:
                for field, errors in form_insumo.errors.items():
                    for error in errors:
                        flash(f'Error en {field}: {error}', 'error')

        # Obtener insumos existentes para la tabla
        insumos = db.session.query(
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
        ).all()

        return render_template('inventario/gestion_insumos.html',
                             form_insumo=form_insumo,
                             form_categoria=form_categoria,
                             insumos=insumos)

    except Exception as e:
        print(f"Error general: {str(e)}")
        db.session.rollback()
        flash('Error al procesar la solicitud', 'error')
        return redirect(url_for('inventario.index')), 400

@ventas_bp.route('/informes')
@login_required
def informes():
    try:
        # Obtener fecha actual y fecha hace 30 días
        fecha_fin = datetime.now()
        fecha_inicio = fecha_fin - timedelta(days=30)

        # 1. Ventas totales por día (últimos 30 días)
        ventas_diarias = db.session.query(
            func.date(InformeVentas.fecha_venta).label('fecha'),
            func.sum(InformeVentas.total_venta).label('total')
        ).filter(
            InformeVentas.fecha_venta.between(fecha_inicio, fecha_fin)
        ).group_by(
            func.date(InformeVentas.fecha_venta)
        ).all()

        # 2. Productos más vendidos
        productos_populares = db.session.query(
            Recetas.nombre,
            func.sum(DetalleVenta.cantidad).label('cantidad_total'),
            func.sum(DetalleVenta.cantidad * DetalleVenta.precio_unitario).label('ingresos_total')
        ).join(
            DetalleVenta, Recetas.id == DetalleVenta.receta_id
        ).join(
            InformeVentas, DetalleVenta.venta_id == InformeVentas.id
        ).filter(
            InformeVentas.fecha_venta.between(fecha_inicio, fecha_fin)
        ).group_by(
            Recetas.id
        ).order_by(
            func.sum(DetalleVenta.cantidad).desc()
        ).limit(5).all()

        # 3. Ventas por tipo (Por Pieza, Suelta, Por Kilo)
        ventas_por_tipo = db.session.query(
            DetalleVenta.tipo_venta,
            func.sum(DetalleVenta.cantidad * DetalleVenta.precio_unitario).label('total')
        ).join(
            InformeVentas, DetalleVenta.venta_id == InformeVentas.id
        ).filter(
            InformeVentas.fecha_venta.between(fecha_inicio, fecha_fin)
        ).group_by(
            DetalleVenta.tipo_venta
        ).all()

        # 4. Estadísticas generales
        stats = db.session.query(
            func.count(InformeVentas.id).label('total_ventas'),
            func.sum(InformeVentas.total_venta).label('ingresos_totales'),
            func.avg(InformeVentas.total_venta).label('ticket_promedio'),
            func.sum(InformeVentas.descuento_aplicado).label('descuentos_totales')
        ).filter(
            InformeVentas.fecha_venta.between(fecha_inicio, fecha_fin)
        ).first()

        # Formatear datos para los gráficos
        datos_ventas_diarias = {
            'fechas': [str(venta.fecha) for venta in ventas_diarias],
            'totales': [float(venta.total) for venta in ventas_diarias]
        }

        datos_productos_populares = {
            'nombres': [prod.nombre for prod in productos_populares],
            'cantidades': [int(prod.cantidad_total) for prod in productos_populares],
            'ingresos': [float(prod.ingresos_total) for prod in productos_populares]
        }

        datos_ventas_tipo = {
            'tipos': [tipo.tipo_venta.name for tipo in ventas_por_tipo],
            'totales': [float(tipo.total) for tipo in ventas_por_tipo]
        }

        return render_template('ventas/informes.html',
                             ventas_diarias=datos_ventas_diarias,
                             productos_populares=datos_productos_populares,
                             ventas_tipo=datos_ventas_tipo,
                             stats=stats)

    except Exception as e:
        print(f"Error en informes: {str(e)}")
        flash('Error al generar los informes', 'error')
        return redirect(url_for('ventas.index')) 
        return redirect(url_for('inventario.index')), 400 