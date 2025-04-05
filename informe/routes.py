from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from sqlalchemy import func
from models import db, InformeVentas, DetalleVenta, Usuarios, Recetas, InformeProduccion
from forms import CorteVentasForm
from decorators import rol_requerido
from . import informe_bp

@informe_bp.route('/', methods=['GET', 'POST'])
@login_required
@rol_requerido(1)  # Solo administradores
def index():
    form = CorteVentasForm()
    fecha_inicio = datetime.today().date()
    fecha_fin = datetime.today().date()
    
    if request.method == 'POST':
        if form.buscar.data:
            fecha_inicio = form.fecha_inicio.data
            fecha_fin = form.fecha_fin.data
        elif form.procesar.data:
            # Aquí iría la lógica para procesar el corte de ventas
            return redirect(url_for('informe.index'))
    
    # Asegurar que la fecha de fin incluya el día completo
    inicio_periodo = datetime.combine(fecha_inicio, datetime.min.time())
    fin_periodo = datetime.combine(fecha_fin, datetime.max.time())
    
    # Consulta para obtener el total de ventas del período
    ventas_hoy = db.session.query(
        func.coalesce(func.sum(InformeVentas.total_venta), 0)
    ).filter(
        InformeVentas.fecha_venta >= inicio_periodo,
        InformeVentas.fecha_venta <= fin_periodo
    ).scalar()
    
    # Consulta para obtener el número de ventas del período
    num_ventas = db.session.query(
        func.count(InformeVentas.id)
    ).filter(
        InformeVentas.fecha_venta >= inicio_periodo,
        InformeVentas.fecha_venta <= fin_periodo
    ).scalar()
    
    # Consulta para obtener el total de productos vendidos del período
    total_productos = db.session.query(
        func.coalesce(func.sum(DetalleVenta.cantidad), 0)
    ).join(InformeVentas, DetalleVenta.venta_id == InformeVentas.id
    ).filter(
        InformeVentas.fecha_venta >= inicio_periodo,
        InformeVentas.fecha_venta <= fin_periodo
    ).scalar()
    
    # Consulta para obtener las últimas ventas del período
    ultimas_ventas = db.session.query(
        InformeVentas.id,
        InformeVentas.fecha_venta,
        InformeVentas.total_venta,
        InformeVentas.descuento_aplicado,
        Usuarios.nombre.label('nombre_usuario')
    ).join(Usuarios, InformeVentas.usuario_id == Usuarios.id
    ).filter(
        InformeVentas.fecha_venta >= inicio_periodo,
        InformeVentas.fecha_venta <= fin_periodo
    ).order_by(
        InformeVentas.fecha_venta.desc()
    ).limit(10).all()
    
    # Imprimir los resultados para depuración
    print(f"Fecha inicio: {fecha_inicio}")
    print(f"Fecha fin: {fecha_fin}")
    print(f"Ventas del período: {ventas_hoy}")
    print(f"Número de ventas: {num_ventas}")
    print(f"Total de productos: {total_productos}")
    print(f"Últimas ventas: {ultimas_ventas}")
    
    return render_template("informe/index.html",
        form=form,
        ventas_hoy=ventas_hoy,
        num_ventas=num_ventas,
        total_productos=total_productos,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        ultimas_ventas=ultimas_ventas
    )

@informe_bp.route('/intraCorteVentas', methods=['GET', 'POST'])
@login_required
@rol_requerido(1, 4)  # Administradores y usuarios de ventas
def intraCorteVentas():
    form = CorteVentasForm()
    fecha_inicio = datetime.today().date()
    fecha_fin = datetime.today().date()

    if form.validate_on_submit():
        fecha_inicio = form.fecha_inicio.data
        fecha_fin = form.fecha_fin.data

    if request.method == 'POST':
        fecha_inicio_str = request.form.get('fecha_inicio')
        fecha_fin_str = request.form.get('fecha_fin')
        if fecha_inicio_str:
            fecha_inicio = datetime.strptime(fecha_inicio_str, '%Y-%m-%d').date()
        if fecha_fin_str:
            fecha_fin = datetime.strptime(fecha_fin_str, '%Y-%m-%d').date()

    # Asegurar que la fecha de fin incluya el día completo
    inicio_periodo = datetime.combine(fecha_inicio, datetime.min.time())
    fin_periodo = datetime.combine(fecha_fin, datetime.max.time())  # 23:59:59

    # Consulta para obtener el total de ventas del período
    ventas_periodo = db.session.query(
        func.coalesce(func.sum(InformeVentas.total_venta), 0)
    ).filter(
        InformeVentas.fecha_venta >= inicio_periodo,
        InformeVentas.fecha_venta <= fin_periodo  # Incluye el día completo
    ).scalar()

    # Consulta para obtener el número de ventas del período
    num_ventas = db.session.query(
        func.count(InformeVentas.id)
    ).filter(
        InformeVentas.fecha_venta >= inicio_periodo,
        InformeVentas.fecha_venta <= fin_periodo
    ).scalar()

    # Consulta para obtener el total de productos vendidos del período
    total_productos = db.session.query(
        func.coalesce(func.sum(DetalleVenta.cantidad), 0)
    ).join(InformeVentas, DetalleVenta.venta_id == InformeVentas.id
    ).filter(
        InformeVentas.fecha_venta >= inicio_periodo,
        InformeVentas.fecha_venta <= fin_periodo
    ).scalar()

    # Consulta para obtener las últimas ventas del período
    ultimas_ventas = db.session.query(
        InformeVentas.id,
        InformeVentas.fecha_venta,
        InformeVentas.total_venta,
        InformeVentas.descuento_aplicado,
        Usuarios.nombre.label('nombre_usuario')
    ).join(Usuarios, InformeVentas.usuario_id == Usuarios.id
    ).filter(
        InformeVentas.fecha_venta >= inicio_periodo,
        InformeVentas.fecha_venta <= fin_periodo
    ).order_by(
        InformeVentas.fecha_venta.desc()
    ).limit(10).all()

    # Imprimir los resultados para depuración
    print(f"Fecha inicio: {fecha_inicio}")
    print(f"Fecha fin: {fecha_fin}")
    print(f"Ventas del período: {ventas_periodo}")
    print(f"Número de ventas: {num_ventas}")
    print(f"Total de productos: {total_productos}")
    print(f"Últimas ventas: {ultimas_ventas}")

    return render_template("informe/intraCorteVentas.html",
        form=form,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        ventas_periodo=ventas_periodo,
        num_ventas=num_ventas,
        total_productos=total_productos,
        ultimas_ventas=ultimas_ventas,
    )