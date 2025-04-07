function verLotes(insumoId) {
    // Cerrar cualquier modal abierto
    const modalesAbiertos = document.querySelectorAll('.modal.show');
    modalesAbiertos.forEach(modalElement => {
        const modalInstance = bootstrap.Modal.getInstance(modalElement);
        if (modalInstance) {
            modalInstance.hide();
        }
    });
    
    // Obtener los lotes del insumo
    fetch(`/inventario/insumo/${insumoId}/lotes`)
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                throw new Error(data.error);
            }
            
            const tbody = document.getElementById('lotesTableBody');
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
                
                // Validar que insumo_id esté presente
                if (!lote.insumo_id) {
                    console.error('Error: insumo_id no encontrado para el lote:', lote.lote_id);
                    return;
                }
                
                tr.innerHTML = `
                    <td>${lote.lote_id}</td>
                    <td>${lote.cantidad} ${lote.unidad}</td>
                    <td>${lote.proveedor || 'Sin proveedor'}</td>
                    <td>${lote.fecha_registro || 'N/A'}</td>
                    <td>${lote.fecha_caducidad || 'N/A'}</td>
                    <td>${estadoBadge}</td>
                    <td>
                        <button class="btn btn-sm btn-info me-1" 
                                onclick="verLoteEspecifico('${lote.lote_id}')"
                                title="Ver detalles">
                            <i class="bi bi-eye"></i>
                        </button>
                        <button class="btn btn-sm btn-warning" 
                                onclick="declararMerma(${lote.insumo_id}, '${lote.lote_id}', ${lote.cantidad}, '${lote.unidad}')"
                                ${lote.cantidad <= 0 ? 'disabled' : ''}
                                title="Declarar merma">
                            <i class="bi bi-exclamation-triangle"></i>
                        </button>
                    </td>
                `;
                tbody.appendChild(tr);
            });

            // Mostrar el modal de Bootstrap
            const modal = new bootstrap.Modal(document.getElementById('lotesModal'));
            modal.show();
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error al cargar los lotes');
        });
}

// Función para ver detalles de un lote específico
function verLoteEspecifico(loteId) {
    // Cerrar cualquier modal abierto
    const modalesAbiertos = document.querySelectorAll('.modal.show');
    modalesAbiertos.forEach(modalElement => {
        const modalInstance = bootstrap.Modal.getInstance(modalElement);
        if (modalInstance) {
            modalInstance.hide();
        }
    });
    
    // Obtener los detalles del lote
    fetch(`/inventario/lote/${loteId}`)
        .then(response => {
            if (!response.ok) {
                throw new Error(`Error del servidor: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('Datos del lote recibidos:', data);
            
            if (data.error) {
                throw new Error(data.error);
            }
            
            // Verificar que data.lote existe
            if (!data.lote) {
                throw new Error('No se encontraron datos del lote');
            }
            
            const lote = data.lote;
            
            // Llenar los datos del modal
            document.getElementById('insumoNombre').textContent = lote.insumo_nombre || 'N/A';
            document.getElementById('tipoInsumo').textContent = lote.tipo_insumo || 'N/A';
            document.getElementById('loteId').textContent = lote.lote_id || 'N/A';
            document.getElementById('cantidad').textContent = lote.cantidad && lote.unidad ? 
                `${lote.cantidad} ${lote.unidad}` : 'N/A';
            document.getElementById('fechaRegistro').textContent = lote.fecha_registro || 'N/A';
            document.getElementById('fechaCaducidad').textContent = lote.fecha_caducidad || 'N/A';
            document.getElementById('proveedorNombre').textContent = lote.proveedor || 'Sin proveedor';
            document.getElementById('proveedorContacto').textContent = lote.proveedor_contacto || 'N/A';
            document.getElementById('proveedorTelefono').textContent = lote.proveedor_telefono || 'N/A';
            
            // Configurar el estado del lote
            const estadoLote = document.getElementById('estadoLote');
            const estadoClase = {
                'terminado': 'bg-secondary',
                'caduco': 'bg-danger',
                'proximo_caducar': 'bg-warning',
                'vigente': 'bg-success'
            }[lote.estado] || 'bg-secondary';
            
            estadoLote.className = `badge ${estadoClase}`;
            estadoLote.textContent = lote.mensaje || 'Estado desconocido';
            
            // Mostrar alerta de caducidad si es necesario
            const alertaCaducidad = document.getElementById('alertaCaducidad');
            if (lote.esta_caducado) {
                alertaCaducidad.classList.remove('d-none');
            } else {
                alertaCaducidad.classList.add('d-none');
            }
            
            // Configurar el botón de declarar merma
            const btnDeclararMerma = document.getElementById('btnDeclararMerma');
            if (lote.cantidad <= 0) {
                btnDeclararMerma.disabled = true;
            } else {
                btnDeclararMerma.disabled = false;
            }
            
            // Guardar el ID del insumo para el formulario de merma
            document.getElementById('mermaInsumoId').value = lote.insumo_id || '';
            document.getElementById('cantidadDisponible').value = lote.cantidad && lote.unidad ? 
                `${lote.cantidad} ${lote.unidad}` : 'N/A';
            document.getElementById('cantidadMerma').max = lote.cantidad || 0;
            
            // Cerrar el modal de lotes y mostrar el modal de detalle
            const lotesModal = document.getElementById('lotesModal');
            if (lotesModal && lotesModal.classList.contains('show')) {
                const modalInstance = bootstrap.Modal.getInstance(lotesModal);
                if (modalInstance) {
                    modalInstance.hide();
                }
            }
            
            const modal = new bootstrap.Modal(document.getElementById('loteModal'));
            modal.show();
        })
        .catch(error => {
            console.error('Error al cargar los detalles del lote:', error);
            alert(`Error al cargar los detalles del lote: ${error.message}`);
        });
}

// Alias para verLoteEspecifico para mantener compatibilidad
window.verDetalleLote = function(loteId) {
    verLoteEspecifico(loteId);
};

// Función para declarar merma
function declararMerma(insumoId, loteId, cantidad, unidad) {
    // Cerrar cualquier modal abierto
    const modalesAbiertos = document.querySelectorAll('.modal.show');
    modalesAbiertos.forEach(modalElement => {
        const modalInstance = bootstrap.Modal.getInstance(modalElement);
        if (modalInstance) {
            modalInstance.hide();
        }
    });
    
    // Guardar los datos para el formulario de merma
    document.getElementById('mermaInsumoId').value = insumoId;
    document.getElementById('cantidadDisponible').value = `${cantidad} ${unidad}`;
    document.getElementById('cantidadMerma').max = cantidad;
    
    // Mostrar el modal de merma
    const modal = new bootstrap.Modal(document.getElementById('declararMermaModal'));
    modal.show();
}

// Función para mostrar el modal de merma
function mostrarModalMerma() {
    // Cerrar el modal de detalles del lote
    const loteModal = document.getElementById('loteModal');
    if (loteModal && loteModal.classList.contains('show')) {
        const modalInstance = bootstrap.Modal.getInstance(loteModal);
        if (modalInstance) {
            modalInstance.hide();
        }
    }
    
    // Mostrar el modal de merma
    const modal = new bootstrap.Modal(document.getElementById('declararMermaModal'));
    modal.show();
}

// Función para mostrar el modal de mermas
function mostrarMermas() {
    fetch('/inventario/mermas')
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                throw new Error(data.error);
            }
            
            const tbody = document.getElementById('mermasTableBody');
            tbody.innerHTML = '';
            
            data.mermas.forEach(merma => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td class="ps-4 fw-semibold">${merma.insumo_nombre}</td>
                    <td>
                        <span class="badge" style="background-color: var(--color-beige); color: var(--color-marron-oscuro);">
                            ${merma.tipo_insumo}
                        </span>
                    </td>
                    <td class="cantidad-mermada">${merma.cantidad_mermada} ${merma.unidad}</td>
                    <td>${merma.fecha_merma}</td>
                    <td class="pe-4">${merma.motivo_merma}</td>
                `;
                tbody.appendChild(tr);
            });
            
            // Mostrar el modal de Bootstrap
            const modal = new bootstrap.Modal(document.getElementById('mermasModal'));
            modal.show();
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error al cargar las mermas');
        });
} 