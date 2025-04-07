// Función auxiliar para cerrar todos los modales abiertos
function cerrarModalesAbiertos() {
    const modalesAbiertos = document.querySelectorAll('.modal.show');
    modalesAbiertos.forEach(modalElement => {
        const modalInstance = bootstrap.Modal.getInstance(modalElement);
        if (modalInstance) {
            modalInstance.hide();
        }
    });
}

// Función para declarar merma
window.declararMerma = function(insumoId, loteId, cantidadDisponible, unidad) {
    // Cerrar cualquier modal abierto
    cerrarModalesAbiertos();
    
    // Configurar el modal de merma
    document.getElementById('mermaInsumoId').value = insumoId;
    document.getElementById('cantidadDisponible').value = `${cantidadDisponible} ${unidad}`;
    document.getElementById('cantidadMerma').max = cantidadDisponible;
    
    // Mostrar el modal
    const modal = new bootstrap.Modal(document.getElementById('declararMermaModal'));
    modal.show();
};

// Función para mostrar mermas
window.mostrarMermas = function() {
    // Cerrar cualquier modal abierto
    cerrarModalesAbiertos();
    
    // Obtener las mermas del servidor
    fetch('/inventario/mermas/listar')
        .then(response => {
            if (!response.ok) {
                throw new Error('Error al obtener las mermas');
            }
            return response.json();
        })
        .then(data => {
            if (data.success && data.mermas) {
                const tbody = document.getElementById('mermasTableBody');
                tbody.innerHTML = '';
                
                data.mermas.forEach(merma => {
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td class="ps-4">${merma.insumo_nombre}</td>
                        <td>${merma.tipo_insumo}</td>
                        <td class="cantidad-mermada">${merma.cantidad_danada} ${merma.unidad}</td>
                        <td>${merma.fecha_merma}</td>
                        <td class="pe-4">${merma.motivo_merma}</td>
                    `;
                    tbody.appendChild(tr);
                });
                
                // Mostrar el modal
                const modal = new bootstrap.Modal(document.getElementById('mermasModal'));
                modal.show();
            } else {
                throw new Error(data.message || 'Error al obtener las mermas');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            Swal.fire({
                icon: 'error',
                title: 'Error',
                text: error.message || 'Error al cargar las mermas'
            });
        });
};

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

    // Función para ver detalles de un lote específico
    window.verDetalleLote = function(loteId) {
        console.log('Viendo detalle del lote:', loteId);
        
        // Cerrar cualquier modal abierto
        cerrarModalesAbiertos();
        
        fetch(`/inventario/lote/${loteId}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Error al obtener detalles del lote');
                }
                return response.json();
            })
            .then(data => {
                if (data.lote) {
                    // Actualizar los campos del modal
                    document.getElementById('insumoNombre').textContent = data.lote.insumo_nombre;
                    document.getElementById('tipoInsumo').textContent = data.lote.tipo_insumo;
                    document.getElementById('loteId').textContent = data.lote.lote_id;
                    document.getElementById('cantidad').textContent = `${data.lote.cantidad} ${data.lote.unidad}`;
                    document.getElementById('fechaRegistro').textContent = data.lote.fecha_registro;
                    document.getElementById('fechaCaducidad').textContent = data.lote.fecha_caducidad;
                    document.getElementById('proveedorNombre').textContent = data.lote.proveedor;
                    document.getElementById('proveedorContacto').textContent = data.lote.proveedor_contacto;
                    document.getElementById('proveedorTelefono').textContent = data.lote.proveedor_telefono;

                    // Mostrar/ocultar alerta de caducidad
                    const alertaCaducidad = document.getElementById('alertaCaducidad');
                    if (data.lote.esta_caducado) {
                        alertaCaducidad.classList.remove('d-none');
                    } else {
                        alertaCaducidad.classList.add('d-none');
                    }

                    // Actualizar estado del lote
                    const estadoLote = document.getElementById('estadoLote');
                    estadoLote.className = 'badge';
                    if (data.lote.esta_caducado) {
                        estadoLote.classList.add('bg-danger');
                        estadoLote.innerHTML = '<i class="bi bi-x-circle me-1"></i>Caducado';
                    } else if (data.lote.dias_restantes <= 30) {
                        estadoLote.classList.add('bg-warning', 'text-dark');
                        estadoLote.innerHTML = '<i class="bi bi-exclamation-circle me-1"></i>Próximo a caducar';
                    } else {
                        estadoLote.classList.add('bg-success');
                        estadoLote.innerHTML = '<i class="bi bi-check-circle me-1"></i>Vigente';
                    }

                    // Mostrar el modal
                    const loteModal = new bootstrap.Modal(document.getElementById('loteModal'));
                    loteModal.show();
                } else {
                    throw new Error('No se encontró el lote');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Error al obtener detalles del lote');
            });
    };

    // Función para ver todos los lotes de un tipo de insumo
    window.verLotes = function(tipoInsumoId) {
        console.log('Viendo lotes del tipo:', tipoInsumoId);
        
        // Cerrar cualquier modal abierto
        cerrarModalesAbiertos();
        
        // Primero obtener el nombre de la categoría
        fetch(`/inventario/insumos/tipo/${tipoInsumoId}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Error al obtener la categoría');
                }
                return response.json();
            })
            .then(categoriaData => {
                // Actualizar el título del modal con el nombre de la categoría
                const modalTitle = document.querySelector('#lotesModal .modal-title');
                if (modalTitle && categoriaData.tipo) {
                    modalTitle.innerHTML = `<i class="bi bi-box-seam me-2"></i>Lotes de ${categoriaData.tipo}`;
                }
                
                // Ahora obtener los lotes
                return fetch(`/inventario/lotes/${tipoInsumoId}`);
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Error al obtener lotes');
                }
                return response.json();
            })
            .then(data => {
                if (data.lotes) {
                    const tbody = document.getElementById('lotesTableBody');
                    if (!tbody) {
                        console.error('No se encontró el elemento tbody para los lotes');
                        return;
                    }
                    tbody.innerHTML = '';

                    data.lotes.forEach(lote => {
                        const tr = document.createElement('tr');
                        const estadoClase = {
                            'terminado': 'bg-secondary',
                            'caduco': 'bg-danger',
                            'proximo_caducar': 'bg-warning',
                            'vigente': 'bg-success'
                        }[lote.estado] || 'bg-secondary';
                        
                        const estadoBadge = `<span class="badge ${estadoClase}">${lote.mensaje}</span>`;
                        
                        tr.innerHTML = `
                            <td class="ps-4">${lote.lote_id}</td>
                            <td>${lote.cantidad} ${lote.unidad}</td>
                            <td>${lote.proveedor || 'Sin proveedor'}</td>
                            <td>${lote.fecha_registro || 'N/A'}</td>
                            <td>${lote.fecha_caducidad || 'N/A'}</td>
                            <td>${estadoBadge}</td>
                            <td class="pe-4 text-end">
                                <button class="btn btn-sm" 
                                    style="background-color: var(--color-marron); color: white;"
                                    onclick="verDetalleLote('${lote.lote_id}')"
                                    title="Ver detalle del lote">
                                    <i class="bi bi-eye"></i>
                                </button>
                            </td>
                        `;
                        tbody.appendChild(tr);
                    });

                    // Mostrar el modal de Bootstrap
                    const modalElement = document.getElementById('lotesModal');
                    if (!modalElement) {
                        console.error('No se encontró el elemento modal de lotes');
                        return;
                    }
                    const modal = new bootstrap.Modal(modalElement);
                    modal.show();
                } else {
                    throw new Error('No se encontraron lotes');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Error al obtener lotes');
            });
    };
});
