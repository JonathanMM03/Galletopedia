from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_required, current_user
from models import db, Recetas, PedidoGalletasClientes, EstadoPedido, Usuarios, InformeVentas, DetalleVenta, TipoVenta, InformeProduccion
from sqlalchemy import func
from datetime import datetime, timedelta
from forms import SolicitarLoteForm, FlaskForm
from sqlalchemy.orm import joinedload
import math
from . import pedidos_bp


def crear_venta(usuario_id, items, total, descuento=0, pago=None, cambio=None):

    try:
        venta = InformeVentas(
            usuario_id=usuario_id,
            total_venta=total,
            descuento_aplicado=descuento,
            cliente_pago=pago if pago is not None else total,
            cambio=cambio if cambio is not None else 0,
            fecha_venta=datetime.now()
        )
        db.session.add(venta)
        db.session.flush()  # Para obtener el ID

        for item in items:
            # Obtener el lote más antiguo disponible
            lote = InformeProduccion.query.filter_by(
                receta_id=item['producto_id']
            ).filter(
                InformeProduccion.cantidad_disponible > 0
            ).order_by(
                InformeProduccion.fecha_produccion.asc()
            ).first()

            if not lote or lote.cantidad_disponible < item['cantidad']:
                raise Exception(f"No hay suficiente stock disponible para {item['nombre']}")

            detalle = DetalleVenta(
                venta_id=venta.id,
                receta_id=item['producto_id'],
                cantidad=item['cantidad'],
                precio_unitario=item['precio_unitario'],
                tipo_venta=item.get('tipo', 'Unidad')
            )
            db.session.add(detalle)

            # Descontar del lote
            lote.cantidad_disponible -= item['cantidad']

        db.session.commit()
        return True, venta.id

    except Exception as e:
        db.session.rollback()
        print(f"[crear_venta] Error: {str(e)}")
        return False, str(e)


def registrar_venta(pedido):

    item = {
        'producto_id': pedido.receta_id,
        'nombre': pedido.receta.nombre,
        'cantidad': pedido.cantidad,
        'precio_unitario': pedido.receta.precio_venta,
        'tipo': 'Unidad'  # O ajusta según el caso
    }

    total = pedido.cantidad * pedido.receta.precio_venta

    success, result = crear_venta(pedido.usuario_id, [item], total)

    if not success:
        flash(f"Error al registrar la venta: {result}", "danger")
    else:
        print(f"Venta registrada exitosamente con ID: {result}")

@pedidos_bp.route('/pedidos', methods=['GET', 'POST'])
@login_required
def pedidos():
    form = FlaskForm()
    usuario_id = session["_user_id"]
    user_type = session.get("_user_type")
    
    # Obtener el número de página de los parámetros de la URL
    page = request.args.get('page', 1, type=int)
    per_page = 10  # Número de pedidos por página

    # Construir la consulta base
    query = (
        PedidoGalletasClientes.query
        .join(Recetas, PedidoGalletasClientes.receta)
        .join(EstadoPedido, PedidoGalletasClientes.estado_pedido)
        .join(Usuarios, PedidoGalletasClientes.usuario)
    )

    # Si es cliente (tipo 3), filtrar solo sus pedidos
    if user_type == 3:
        query = query.filter_by(usuario_id=usuario_id)

    # Aplicar paginación a la consulta
    pagination = (
        query
        .add_columns(
            PedidoGalletasClientes.id,
            PedidoGalletasClientes.fecha_pedido,
            PedidoGalletasClientes.cantidad,
            PedidoGalletasClientes.tipo_venta,
            PedidoGalletasClientes.fecha_entrega,
            PedidoGalletasClientes.estatus,
            Recetas.nombre.label('nombre_receta'),
            EstadoPedido.nombre.label('estado_pedido'),
            Recetas.gramaje_por_galleta,
            Usuarios.nombre.label('nombre_usuario')
        )
        .order_by(PedidoGalletasClientes.fecha_pedido.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )

    pedidos_modificados = []
    for p in pagination.items:
        if p.tipo_venta == 2:
            galletas_por_caja = math.floor(400 / p.gramaje_por_galleta)
            cantidad = p.cantidad // galletas_por_caja if galletas_por_caja else 0
        else:
            cantidad = p.cantidad

        pedido_dict = {
            'id': p.id,
            'fecha_pedido': p.fecha_pedido,
            'nombre_usuario': p.nombre_usuario,
            'nombre_receta': p.nombre_receta,
            'cantidad': cantidad,
            'tipo_venta': p.tipo_venta,
            'estado_pedido': p.estado_pedido,
            'estatus': p.estatus,
            'fecha_entrega': p.fecha_entrega
        }

        pedidos_modificados.append(pedido_dict)

    return render_template("pedidos/pedidos.html", 
                         pedidos=pedidos_modificados, 
                         form=form,
                         pagination=pagination)


@pedidos_bp.route('/actualizar_pedido', methods=['POST'])
@login_required
def actualizar_pedido():
    pedido_id = request.form.get('pedido_id')
    fecha_entrega = request.form.get('fecha_entrega')

    if not pedido_id:
        flash("Error: No se proporcionó un ID de pedido.", "danger")
        return redirect(url_for('pedidos.pedidos'))

    pedido = PedidoGalletasClientes.query.get(pedido_id)

    if not pedido:
        flash("Error: Pedido no encontrado.", "danger")
        return redirect(url_for('pedidos.pedidos'))

    # Si el pedido está en preparación y se quiere marcar como listo, verificar fecha de entrega
    if pedido.estatus == 'preparacion' and not fecha_entrega:
        flash("Error: Debe asignar una fecha de entrega antes de marcar el pedido como listo.", "warning")
        return redirect(url_for('pedidos.pedidos'))

    # Actualizar la fecha de entrega si se proporciona
    if fecha_entrega:
        try:
            pedido.fecha_entrega = datetime.strptime(fecha_entrega, '%Y-%m-%d')
        except ValueError:
            flash("Error: Formato de fecha inválido.", "danger")
            return redirect(url_for('pedidos.pedidos'))

    if pedido.estatus == 'pedido':
        pedido.estatus = 'preparacion'
    elif pedido.estatus == 'preparacion':
        pedido.estatus = 'listo'
    elif pedido.estatus == 'listo':
        pedido.estatus = 'entregado'
        registrar_venta(pedido)  # Función para guardar la venta

    db.session.commit()
    flash("El estado del pedido ha sido actualizado correctamente.", "success")
    return redirect(url_for('pedidos.pedidos'))


@pedidos_bp.route('/cancelar_pedido', methods=['POST'])
@login_required
def cancelar_pedido():
    pedido_id = request.form.get('pedido_id')

    if not pedido_id:
        flash("Error: No se proporcionó un ID de pedido.", "danger")
        return redirect(url_for('pedidos.pedidos'))

    pedido = PedidoGalletasClientes.query.get(pedido_id)

    if not pedido:
        flash("Error: Pedido no encontrado.", "danger")
        return redirect(url_for('pedidos.pedidos'))

    # Verificar si el pedido ya está entregado o cancelado
    if pedido.estatus in ['entregado', 'cancelado']:
        flash("Error: No se puede cancelar un pedido ya entregado o cancelado.", "danger")
        return redirect(url_for('pedidos.pedidos'))

    # Actualizar el estado del pedido a cancelado
    pedido.estatus = 'cancelado'
    db.session.commit()
    
    flash("El pedido ha sido cancelado correctamente.", "success")
    return redirect(url_for('pedidos.pedidos'))


@pedidos_bp.route('/asignar_fecha_entrega', methods=['POST'])
@login_required
def asignar_fecha_entrega():
    pedido_id = request.form.get('pedido_id')
    fecha_entrega = request.form.get('fecha_entrega')
    marcar_listo = request.form.get('marcar_listo')

    if not pedido_id:
        flash("Error: No se proporcionó un ID de pedido.", "danger")
        return redirect(url_for('pedidos.pedidos'))

    pedido = PedidoGalletasClientes.query.get(pedido_id)

    if not pedido:
        flash("Error: Pedido no encontrado.", "danger")
        return redirect(url_for('pedidos.pedidos'))

    # Verificar si el pedido ya está entregado o cancelado
    if pedido.estatus in ['entregado', 'cancelado']:
        flash("Error: No se puede modificar un pedido ya entregado o cancelado.", "danger")
        return redirect(url_for('pedidos.pedidos'))

    # Actualizar la fecha de entrega si se proporciona
    if fecha_entrega:
        try:
            pedido.fecha_entrega = datetime.strptime(fecha_entrega, '%Y-%m-%d')
            # Si se debe marcar como listo
            if marcar_listo:
                pedido.estatus = 'listo'
            db.session.commit()
            flash("La fecha de entrega ha sido actualizada correctamente.", "success")
        except ValueError:
            flash("Error: Formato de fecha inválido.", "danger")
    else:
        flash("Error: No se proporcionó una fecha de entrega.", "danger")

    return redirect(url_for('pedidos.pedidos'))



