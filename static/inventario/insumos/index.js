document.addEventListener('DOMContentLoaded', function() {
    console.log('Script cargado');
    
    // Elementos del formulario
    const formAgregarInsumo = document.getElementById('formAgregarInsumo');
    const categoriaSelect = document.getElementById('categoriaInsumo');
    const insumoSelect = document.getElementById('insumoSeleccionado');
    const proveedorSelect = document.getElementById('proveedorInsumo');
    const cantidadInput = document.getElementById('cantidadInsumo');
    const unidadInput = document.getElementById('unidadInsumo');
    const loteInput = document.getElementById('loteInsumo');
    const precioUnitarioInput = document.getElementById('precioUnitario');
    const totalPagarInput = document.getElementById('totalPagar');
    const fechaCaducidadInput = document.getElementById('fechaCaducidadInsumo');

    // Verificar que todos los elementos existan
    if (!formAgregarInsumo || !categoriaSelect || !insumoSelect || !proveedorSelect || 
        !cantidadInput || !unidadInput || !loteInput || !precioUnitarioInput || 
        !totalPagarInput || !fechaCaducidadInput) {
        console.error('No se encontraron todos los elementos del formulario');
        return;
    }

    console.log('Todos los elementos del formulario encontrados');

    // Cargar categorías al inicio
    fetch('/inventario/categorias/listar')
        .then(response => {
            if (!response.ok) {
                throw new Error('Error al cargar las categorías');
            }
            return response.json();
        })
        .then(data => {
            console.log('Categorías cargadas:', data);
            if (data.success && data.categorias && data.categorias.length > 0) {
                categoriaSelect.innerHTML = '<option value="" selected disabled>Seleccione una categoría</option>';
                data.categorias.forEach(categoria => {
                    const option = document.createElement('option');
                    option.value = categoria.id;
                    option.textContent = categoria.nombre;
                    categoriaSelect.appendChild(option);
                });
            }
        })
        .catch(error => {
            console.error('Error al cargar categorías:', error);
        });

    // Evento cambio de categoría
    categoriaSelect.addEventListener('change', function() {
        console.log('Cambio de categoría:', this.value);
        const categoriaId = this.value;
        if (!categoriaId) {
            // Limpiar campos si no hay categoría seleccionada
            insumoSelect.innerHTML = '<option value="" selected disabled>Seleccione un insumo</option>';
            proveedorSelect.innerHTML = '<option value="" selected disabled>Seleccione un proveedor</option>';
            unidadInput.value = '';
            loteInput.value = '';
            precioUnitarioInput.value = '';
            totalPagarInput.value = '';
            return;
        }

        // Obtener datos de la categoría
        fetch(`/inventario/insumos/tipo/${categoriaId}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Error en la respuesta del servidor');
                }
                return response.json();
            })
            .then(data => {
                console.log('Datos recibidos:', data);
                
                // Obtener el último lote
                fetch('/inventario/atender/ultimo-lote')
                    .then(response => {
                        if (!response.ok) {
                            throw new Error('Error al obtener el último lote');
                        }
                        return response.json();
                    })
                    .then(loteData => {
                        if (loteData.success && loteData.nuevo_lote) {
                            loteInput.value = loteData.nuevo_lote;
                        }
                    })
                    .catch(error => {
                        console.error('Error al obtener el último lote:', error);
                    });

                // Actualizar select de insumos
                insumoSelect.innerHTML = '<option value="" selected disabled>Seleccione un insumo</option>';
                
                // Procesar insumos para obtener los insumos únicos
                if (data.insumos && data.insumos.length > 0) {
                    data.insumos.forEach(insumo => {
                        const option = document.createElement('option');
                        option.value = insumo.nombre;
                        option.textContent = insumo.nombre;
                        option.dataset.unidad = insumo.unidad;
                        insumoSelect.appendChild(option);
                    });
                }

                // Actualizar select de proveedores con los proveedores de la categoría
                proveedorSelect.innerHTML = '<option value="" selected disabled>Seleccione un proveedor</option>';
                if (data.proveedores && data.proveedores.length > 0) {
                    data.proveedores.forEach(proveedor => {
                        const option = document.createElement('option');
                        option.value = proveedor.id;
                        option.textContent = `${proveedor.nombre} - $${proveedor.precio}`;
                        option.dataset.precio = proveedor.precio;
                        proveedorSelect.appendChild(option);
                    });
                }

                precioUnitarioInput.value = '';
                totalPagarInput.value = '';
            })
            .catch(error => {
                console.error('Error:', error);
                Swal.fire({
                    icon: 'error',
                    title: 'Error',
                    text: 'Error al cargar los datos de la categoría'
                });
            });
    });

    // Evento para cuando se selecciona un insumo
    insumoSelect.addEventListener('change', function() {
        const selectedOption = this.options[this.selectedIndex];
        if (selectedOption && selectedOption.dataset.unidad) {
            unidadInput.value = selectedOption.dataset.unidad;
        }
    });

    // Evento para cuando se selecciona un proveedor
    proveedorSelect.addEventListener('change', function() {
        const selectedOption = this.options[this.selectedIndex];
        if (selectedOption && selectedOption.dataset.precio) {
            precioUnitarioInput.value = selectedOption.dataset.precio;
            calcularTotal();
        }
    });

    // Calcular total cuando cambia la cantidad
    cantidadInput.addEventListener('input', calcularTotal);

    function calcularTotal() {
        const cantidad = parseFloat(cantidadInput.value) || 0;
        const precio = parseFloat(precioUnitarioInput.value) || 0;
        totalPagarInput.value = (cantidad * precio).toFixed(2);
    }

    // Validar fecha de caducidad
    fechaCaducidadInput.addEventListener('change', function() {
        console.log('Cambio de fecha:', this.value);
        const fecha = new Date(this.value);
        const hoy = new Date();
        hoy.setHours(0, 0, 0, 0);
        
        if (fecha <= hoy) {
            this.classList.add('is-invalid');
        } else {
            this.classList.remove('is-invalid');
        }
    });

    // Manejar envío del formulario
    formAgregarInsumo.addEventListener('submit', function(e) {
        e.preventDefault();
        console.log('Enviando formulario');
        
        // Validar que se haya seleccionado una categoría
        if (!categoriaSelect.value) {
            Swal.fire({
                icon: 'error',
                title: 'Error',
                text: 'Debe seleccionar una categoría'
            });
            return;
        }

        // Validar que se haya seleccionado un insumo
        if (!insumoSelect.value) {
            Swal.fire({
                icon: 'error',
                title: 'Error',
                text: 'Debe seleccionar un insumo'
            });
            return;
        }

        // Validar que se haya seleccionado un proveedor
        if (!proveedorSelect.value) {
            Swal.fire({
                icon: 'error',
                title: 'Error',
                text: 'Debe seleccionar un proveedor'
            });
            return;
        }

        // Validar que se haya ingresado una cantidad
        if (!cantidadInput.value || cantidadInput.value <= 0) {
            Swal.fire({
                icon: 'error',
                title: 'Error',
                text: 'Debe ingresar una cantidad válida'
            });
            return;
        }

        // Validar que se haya ingresado una fecha de caducidad
        if (!fechaCaducidadInput.value) {
            Swal.fire({
                icon: 'error',
                title: 'Error',
                text: 'Debe ingresar una fecha de caducidad'
            });
            return;
        }

        // Validar que la fecha de caducidad sea futura
        const fechaCaducidad = new Date(fechaCaducidadInput.value);
        const hoy = new Date();
        hoy.setHours(0, 0, 0, 0);
        if (fechaCaducidad <= hoy) {
            Swal.fire({
                icon: 'error',
                title: 'Error',
                text: 'La fecha de caducidad debe ser futura'
            });
            return;
        }

        // Obtener el token CSRF
        const csrfToken = document.querySelector('meta[name="csrf-token"]').content;
        if (!csrfToken) {
            console.error('No se encontró el token CSRF');
            Swal.fire({
                icon: 'error',
                title: 'Error',
                text: 'Error de seguridad: No se encontró el token CSRF'
            });
            return;
        }

        // Crear objeto con los datos del formulario
        const formData = {
            insumo_nombre: insumoSelect.value,
            tipo_insumo_id: parseInt(categoriaSelect.value),
            cantidad: parseFloat(cantidadInput.value),
            unidad: unidadInput.value,
            lote_id: loteInput.value,
            fecha_caducidad: fechaCaducidadInput.value,
            proveedor_id: parseInt(proveedorSelect.value),
            precio: parseFloat(precioUnitarioInput.value)
        };

        console.log('Enviando datos:', formData);

        // Enviar datos al servidor
        fetch('/inventario/insumos/agregar/ajax', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify(formData)
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Error en la respuesta del servidor');
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                // Cerrar el modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('agregarInsumoModal'));
                modal.hide();

                // Mostrar mensaje de éxito
                Swal.fire({
                    icon: 'success',
                    title: '¡Éxito!',
                    text: 'Insumo agregado correctamente',
                    timer: 2000,
                    showConfirmButton: false
                }).then(() => {
                    // Recargar la página
                    window.location.reload();
                });
            } else {
                Swal.fire({
                    icon: 'error',
                    title: 'Error',
                    text: data.error || 'Error al agregar el insumo'
                });
            }
        })
        .catch(error => {
            console.error('Error en la solicitud:', error);
            Swal.fire({
                icon: 'error',
                title: 'Error',
                text: 'Error al agregar el insumo'
            });
        });
    });

    // Inicializar el modal
    const agregarInsumoModal = document.getElementById('agregarInsumoModal');
    if (agregarInsumoModal) {
        agregarInsumoModal.addEventListener('shown.bs.modal', function() {
            console.log('Modal de agregar insumo abierto');
            // Limpiar el formulario cuando se abre el modal
            formAgregarInsumo.reset();
            insumoSelect.innerHTML = '<option value="" selected disabled>Seleccione un insumo</option>';
            proveedorSelect.innerHTML = '<option value="" selected disabled>Seleccione un proveedor</option>';
            unidadInput.value = '';
            loteInput.value = '';
            precioUnitarioInput.value = '';
            totalPagarInput.value = '';
        });
    }
});
