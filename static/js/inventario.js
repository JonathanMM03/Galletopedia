document.addEventListener('DOMContentLoaded', function() {
    // Elementos del formulario
    const formAgregarInsumo = document.getElementById('formAgregarInsumo');
    const categoriaSelect = document.getElementById('categoriaInsumo');
    const nombreInsumoInput = document.getElementById('nombreInsumo');
    const proveedorSelect = document.getElementById('proveedorInsumo');
    const cantidadInput = document.getElementById('cantidadInsumo');
    const precioInput = document.getElementById('precioInsumo');
    const totalInput = document.getElementById('totalPagar');
    const unidadSelect = document.getElementById('unidadInsumo');
    const loteInput = document.getElementById('loteInsumo');

    // Cargar todos los proveedores al iniciar
    function cargarProveedores() {
        fetch('/inventario/proveedores/listar')
            .then(response => response.json())
            .then(data => {
                proveedorSelect.innerHTML = '<option value="">Seleccione un proveedor</option>';
                data.forEach(proveedor => {
                    const option = document.createElement('option');
                    option.value = proveedor.id;
                    const nombreProveedor = proveedor.nombre_empresa || proveedor.nombre || proveedor.razon_social || 'Proveedor sin nombre';
                    option.textContent = nombreProveedor;
                    proveedorSelect.appendChild(option);
                });
            })
            .catch(error => {
                console.error('Error al cargar proveedores:', error);
            });
    }

    // Cargar proveedores al iniciar la página
    cargarProveedores();

    // Cargar proveedores cuando se selecciona una categoría
    categoriaSelect.addEventListener('change', function() {
        const categoriaId = this.value;
        if (categoriaId) {
            // Recargar proveedores
            cargarProveedores();
            
            // Obtener siguiente lote del servidor
            fetch('/inventario/obtener-siguiente-lote')
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        loteInput.value = data.lote;
                    } else {
                        console.error('Error al obtener el lote:', data.message);
                    }
                })
                .catch(error => {
                    console.error('Error al obtener el lote:', error);
                });
        } else {
            proveedorSelect.innerHTML = '<option value="">Seleccione un proveedor</option>';
            loteInput.value = '';
        }
    });

    // Validar nombre de insumo (solo letras y espacios)
    nombreInsumoInput.addEventListener('input', function() {
        this.value = this.value.replace(/[^A-Za-zÁáÉéÍíÓóÚúÑñ\s]/g, '');
    });

    // Calcular total cuando cambia cantidad o precio
    function calcularTotal() {
        const cantidad = parseFloat(cantidadInput.value) || 0;
        const precio = parseFloat(precioInput.value) || 0;
        totalInput.value = (cantidad * precio).toFixed(2);
    }

    cantidadInput.addEventListener('input', calcularTotal);
    precioInput.addEventListener('input', calcularTotal);

    // Manejar envío del formulario
    formAgregarInsumo.addEventListener('submit', function(e) {
        e.preventDefault();
        
        // Validar que el nombre solo contenga letras y espacios
        const nombreRegex = /^[A-Za-zÁáÉéÍíÓóÚúÑñ\s]+$/;
        if (!nombreRegex.test(nombreInsumoInput.value)) {
            alert('El nombre del insumo solo puede contener letras y espacios.');
            return;
        }

        // Validar que se haya seleccionado una categoría
        if (!categoriaSelect.value) {
            alert('Debe seleccionar una categoría');
            return;
        }

        // Validar que se haya seleccionado un proveedor
        if (!proveedorSelect.value) {
            alert('Debe seleccionar un proveedor');
            return;
        }

        // Validar que se haya ingresado una cantidad
        if (!cantidadInput.value || cantidadInput.value <= 0) {
            alert('Debe ingresar una cantidad válida');
            return;
        }

        // Validar que se haya seleccionado una unidad
        if (!unidadSelect.value) {
            alert('Debe seleccionar una unidad');
            return;
        }

        // Validar que se haya ingresado un precio
        if (!precioInput.value || precioInput.value <= 0) {
            alert('Debe ingresar un precio válido');
            return;
        }

        // Validar que se haya ingresado una fecha de caducidad
        const fechaCaducidad = document.getElementById('fechaCaducidad').value;
        if (!fechaCaducidad) {
            alert('Debe ingresar una fecha de caducidad');
            return;
        }
        
        const formData = {
            tipo_insumo_id: parseInt(categoriaSelect.value),
            insumo_nombre: nombreInsumoInput.value.trim(),
            proveedor_id: parseInt(proveedorSelect.value),
            cantidad: parseFloat(cantidadInput.value),
            unidad: unidadSelect.value,
            precio_unitario: parseFloat(precioInput.value),
            fecha_caducidad: fechaCaducidad,
            lote_id: loteInput.value
        };

        console.log('Enviando datos:', formData);

        fetch('/inventario/insumos/agregar/ajax', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
            },
            body: JSON.stringify(formData)
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Insumo agregado exitosamente');
                window.location.reload();
            } else {
                alert(data.message || 'Error al agregar el insumo');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error al procesar la solicitud');
        });
    });
});