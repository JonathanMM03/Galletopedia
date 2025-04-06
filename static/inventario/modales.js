/**
 * Módulo de modales para el inventario
 * Contiene la lógica para mostrar los modales de "Ver Lotes" y "Detalles del Lote"
 */

document.addEventListener('DOMContentLoaded', function() {
    // Función para mostrar errores
    window.mostrarError = function(mensaje) {
        // Implementar según el sistema de notificaciones de la aplicación
        alert(mensaje);
    };
    
    // Función para obtener la clase CSS según el estado del stock
    window.getStatusClass = function(status) {
        if (!status) return 'bg-secondary';
        
        switch (status.toLowerCase()) {
            case 'sin stock':
                return 'bg-danger';
            case 'poco':
                return 'bg-warning';
            case 'disponible':
                return 'bg-success';
            default:
                return 'bg-secondary';
        }
    };
});

// Función para mostrar detalles de un insumo
window.mostrarDetallesInsumo = function(nombre) {
    if (!nombre) {
        window.mostrarError('No se especificó un nombre de insumo');
        return;
    }
    
    // Mostrar indicador de carga
    const modalElement = document.getElementById('modal-lotes');
    if (!modalElement) {
        console.error('No se encontró el modal de detalles');
        return;
    }
    
    const modalBody = document.getElementById('modal-lotes-body');
    if (!modalBody) {
        console.error('No se encontró el cuerpo del modal de detalles');
        return;
    }
    
    modalBody.innerHTML = '<div class="text-center"><div class="spinner-border" role="status"><span class="visually-hidden">Cargando...</span></div></div>';
    
    const modal = new bootstrap.Modal(modalElement);
    modal.show();
    
    // Cargar datos específicos del insumo
    const url = `/inventario/insumos-stock/${encodeURIComponent(nombre)}`;
    console.log('URL para detalles del insumo:', url);
    
    fetch(url, {
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`Error HTTP: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        console.log('Respuesta del servidor para detalles:', data);
        
        // Verificar si insumos_agrupados es un objeto con una propiedad insumos_agrupados
        if (data.insumos_agrupados && typeof data.insumos_agrupados === 'object' && !Array.isArray(data.insumos_agrupados) && data.insumos_agrupados.insumos_agrupados) {
            console.log('Insumos agrupados está anidado, extrayendo...');
            data.insumos_agrupados = data.insumos_agrupados.insumos_agrupados;
            console.log('Insumos agrupados extraídos:', data.insumos_agrupados);
        }
        
        if (data && data.insumos_agrupados && data.insumos_agrupados.length > 0) {
            const insumo = data.insumos_agrupados.find(i => i.nombre === nombre);
            console.log('Insumo seleccionado:', insumo);
            
            // Verificar si hay lotes disponibles
            let lotesHTML = '<p>No hay lotes disponibles para este insumo.</p>';
            
            if (insumo.lotes && insumo.lotes.length > 0) {
                console.log('Número de lotes:', insumo.lotes.length);
                console.log('Lotes:', insumo.lotes);
                
                lotesHTML = `
                    <div class="table-responsive">
                        <table class="table table-striped">
                            <thead>
                                <tr>
                                    <th>ID</th>
                                    <th>Lote</th>
                                    <th>Cantidad</th>
                                    <th>Unidad</th>
                                    <th>Precio</th>
                                    <th>Proveedor</th>
                                    <th>Caducidad</th>
                                </tr>
                            </thead>
                            <tbody>
                `;
                
                // Asegurarse de que se muestren todos los lotes
                insumo.lotes.forEach((lote, index) => {
                    console.log(`Procesando lote ${index + 1}/${insumo.lotes.length}:`, lote);
                    
                    // Calcular días hasta caducidad
                    let diasCaducidad = 'N/A';
                    if (lote.caducidad) {
                        const fechaCaducidad = new Date(lote.caducidad);
                        const hoy = new Date();
                        const diferenciaDias = Math.ceil((fechaCaducidad - hoy) / (1000 * 60 * 60 * 24));
                        
                        if (diferenciaDias < 0) {
                            diasCaducidad = 'Caducado';
                        } else if (diferenciaDias === 0) {
                            diasCaducidad = 'Caduca hoy';
                        } else if (diferenciaDias <= 7) {
                            diasCaducidad = `Caduca en ${diferenciaDias} días`;
                        } else {
                            diasCaducidad = `Caduca en ${diferenciaDias} días`;
                        }
                    }
                    
                    lotesHTML += `
                        <tr>
                            <td>${lote.id || 'N/A'}</td>
                            <td>${lote.lote_id || 'N/A'}</td>
                            <td>${lote.cantidad || '0'}</td>
                            <td>${lote.unidad || 'N/A'}</td>
                            <td>${lote.precio ? `$${lote.precio.toFixed(2)}` : 'N/A'}</td>
                            <td>${lote.proveedor || 'N/A'}</td>
                            <td>${diasCaducidad}</td>
                        </tr>
                    `;
                });
                
                lotesHTML += `
                            </tbody>
                        </table>
                    </div>
                `;
            } else {
                console.log('No hay lotes disponibles para este insumo');
            }
            
            // Construir el HTML para el modal
            const modalContent = `
                <div class="container">
                    <h4>${insumo.nombre}</h4>
                    <div class="row mb-3">
                        <div class="col-md-6">
                            <p><strong>Categoría:</strong> ${insumo.categoria || 'No especificada'}</p>
                            <p><strong>Stock Total:</strong> ${insumo.stock || 0} ${insumo.unidad || ''}</p>
                            <p><strong>Estado:</strong> 
                                <span class="badge ${window.getStatusClass(insumo.estado)}">
                                    ${insumo.estado || 'Desconocido'}
                                </span>
                            </p>
                        </div>
                    </div>
                    <h5>Lotes Disponibles (${insumo.lotes ? insumo.lotes.length : 0})</h5>
                    ${lotesHTML}
                </div>
            `;
            
            modalBody.innerHTML = modalContent;
        } else {
            modalBody.innerHTML = '<div class="alert alert-warning">No se encontraron datos para este insumo.</div>';
        }
    })
    .catch(error => {
        console.error('Error al cargar detalles del insumo:', error);
        modalBody.innerHTML = `<div class="alert alert-danger">Error al cargar los detalles: ${error.message}</div>`;
    });
};

// Función para editar un insumo
window.editarInsumo = function(nombre, loteId) {
    if (!nombre || !loteId) {
        window.mostrarError('Faltan datos para editar el insumo');
        return;
    }
    
    // Implementar lógica para editar insumo
    console.log('Editar insumo:', nombre, 'lote:', loteId);
};

// Función para eliminar un insumo
window.eliminarInsumo = function(nombre, loteId) {
    if (!nombre || !loteId) {
        window.mostrarError('Faltan datos para eliminar el insumo');
        return;
    }
    
    if (confirm(`¿Está seguro de eliminar el insumo ${nombre} del lote ${loteId}?`)) {
        // Implementar lógica para eliminar insumo
        console.log('Eliminar insumo:', nombre, 'lote:', loteId);
    }
}; 