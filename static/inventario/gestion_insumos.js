document.addEventListener('DOMContentLoaded', function() {
    // Elementos del formulario
    const modal = document.getElementById('nuevoInsumoModal');
    const form = document.getElementById('formNuevoInsumo');
    const categoriaSelect = form.querySelector('[name="categoria_id"]');
    const proveedorSelect = form.querySelector('[name="proveedor_id"]');
    const precioInput = form.querySelector('[name="precio_unitario"]');
    const cantidadInput = form.querySelector('[name="cantidad"]');
    const totalInput = form.querySelector('[name="total_pagar"]');
    const loteInput = form.querySelector('[name="lote_id"]');

    // Establecer el campo de lote como de solo lectura
    if (loteInput) {
        loteInput.readOnly = true;
    }

    // Manejo del formulario de nuevo insumo
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const formData = new FormData(form);
        
        fetch("/inventario/gestion-insumos", {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`Error del servidor: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                alert(data.message);
                window.location.reload();
            } else {
                alert(data.message || 'Error al procesar la solicitud');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error al procesar la solicitud: ' + error.message);
        });
    });

    // Cargar siguiente lote al abrir el modal
    modal.addEventListener('show.bs.modal', async function() {
        try {
            const response = await fetch('/inventario/obtener-siguiente-lote');
            if (!response.ok) {
                throw new Error(`Error del servidor: ${response.status}`);
            }
            const data = await response.json();
            if (data.success && loteInput) {
                loteInput.value = data.lote;
            } else {
                console.error('Error al obtener lote:', data.message || 'Error desconocido');
            }
        } catch (error) {
            console.error('Error al obtener siguiente lote:', error);
        }
    });

    // Cargar insumos y proveedores cuando se selecciona una categoría
    if (categoriaSelect) {
        categoriaSelect.addEventListener('change', function() {
            const categoriaId = this.value;
            if (!categoriaId) return;

            // Limpiar selects
            if (proveedorSelect) {
                proveedorSelect.innerHTML = '<option value="">Seleccione un proveedor</option>';
            }

            // Obtener datos de la categoría
            cargarInsumosPorTipo(categoriaId);
        });
    }

    // Actualizar precio cuando se selecciona un proveedor
    if (proveedorSelect) {
        proveedorSelect.addEventListener('change', function() {
            const selectedOption = this.options[this.selectedIndex];
            if (selectedOption && selectedOption.dataset.precio) {
                precioInput.value = selectedOption.dataset.precio;
                calcularTotal();
            }
        });
    }

    // Calcular total cuando cambia el precio o la cantidad
    if (precioInput && cantidadInput && totalInput) {
        precioInput.addEventListener('input', calcularTotal);
        cantidadInput.addEventListener('input', calcularTotal);
    }

    // Función para calcular el total
    function calcularTotal() {
        const precio = parseFloat(precioInput.value) || 0;
        const cantidad = parseFloat(cantidadInput.value) || 0;
        
        if (precio > 0 && cantidad > 0) {
            const total = precio * cantidad;
            totalInput.value = total.toFixed(2);
        } else {
            totalInput.value = '';
        }
    }
});

// Función para editar un insumo
function editarInsumo(nombreInsumo) {
    // Aquí iría la lógica para editar el insumo
    console.log('Editando insumo:', nombreInsumo);
    window.location.href = `/inventario/editar-insumo/${encodeURIComponent(nombreInsumo)}`;
}

// Función para eliminar un insumo
function eliminarInsumo(nombreInsumo) {
    if (confirm('¿Está seguro de que desea eliminar el insumo ' + nombreInsumo + '?')) {
        // Aquí iría la lógica para eliminar el insumo
        console.log('Eliminando insumo:', nombreInsumo);
        
        fetch(`/inventario/insumos/eliminar/${encodeURIComponent(nombreInsumo)}`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`Error del servidor: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                alert(data.message);
                window.location.reload();
            } else {
                alert(data.message || 'Error al eliminar el insumo');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error al eliminar el insumo: ' + error.message);
        });
    }
}

// Función para cargar insumos por tipo
async function cargarInsumosPorTipo(tipoId) {
    try {
        const response = await fetch(`/inventario/insumos-stock?categoria=${tipoId}`);
        const data = await response.json();
        
        console.log('Datos recibidos del servidor:', data);
        
        if (data.success) {
            const selectInsumo = document.getElementById('insumo_nombre');
            selectInsumo.innerHTML = '<option value="">Seleccione un insumo</option>';
            
            if (data.insumos && data.insumos.length > 0) {
                console.log('Insumos disponibles:', data.insumos);
                data.insumos.forEach(insumo => {
                    const option = document.createElement('option');
                    option.value = insumo.nombre;
                    option.textContent = `${insumo.nombre} (${insumo.cantidad} ${insumo.unidad})`;
                    selectInsumo.appendChild(option);
                });
            } else {
                console.log('No hay insumos disponibles para esta categoría');
            }
            
            // Actualizar el lote
            if (data.nuevo_lote) {
                console.log('Nuevo lote generado:', data.nuevo_lote);
                document.getElementById('lote').value = data.nuevo_lote;
            }
            
            // Actualizar proveedores
            const selectProveedor = document.getElementById('proveedor_id');
            selectProveedor.innerHTML = '<option value="">Seleccione un proveedor</option>';
            
            if (data.proveedores && data.proveedores.length > 0) {
                console.log('Proveedores disponibles:', data.proveedores);
                data.proveedores.forEach(proveedor => {
                    const option = document.createElement('option');
                    option.value = proveedor.id;
                    option.textContent = `${proveedor.nombre} - $${proveedor.precio}`;
                    option.dataset.precio = proveedor.precio;
                    selectProveedor.appendChild(option);
                });
            } else {
                console.log('No hay proveedores disponibles para esta categoría');
            }
        } else {
            console.error('Error al cargar insumos:', data.message);
        }
    } catch (error) {
        console.error('Error al cargar insumos:', error);
    }
} 