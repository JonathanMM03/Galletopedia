// Funciones globales para filtrado
window.filtrarPorNombre = function() {
    const nombreFiltro = document.getElementById('filtroNombre').value.trim();
    const categoriaFiltro = document.getElementById('filtroCategoria').value;
    
    // Construir la URL con los filtros
    let url = '/inventario/';
    const params = new URLSearchParams();
    
    if (nombreFiltro) {
        params.append('nombre', nombreFiltro);
    }
    
    if (categoriaFiltro) {
        params.append('categoria', categoriaFiltro);
    }
    
    if (params.toString()) {
        url += '?' + params.toString();
    }
    
    // Redirigir a la URL con los filtros
    window.location.href = url;
};

window.filtrarPorCategoria = function() {
    const nombreFiltro = document.getElementById('filtroNombre').value.trim();
    const categoriaFiltro = document.getElementById('filtroCategoria').value;
    
    // Construir la URL con los filtros
    let url = '/inventario/';
    const params = new URLSearchParams();
    
    if (nombreFiltro) {
        params.append('nombre', nombreFiltro);
    }
    
    if (categoriaFiltro) {
        params.append('categoria', categoriaFiltro);
    }
    
    if (params.toString()) {
        url += '?' + params.toString();
    }
    
    // Redirigir a la URL con los filtros
    window.location.href = url;
};

// Función para construir la URL con los filtros actuales
window.construirUrlFiltrado = function() {
    const nombreFiltro = document.getElementById('filtroNombre').value.trim();
    const categoriaFiltro = document.getElementById('filtroCategoria').value;
    
    // Construir la URL con los filtros
    let url = '/inventario/';
    const params = new URLSearchParams();
    
    if (nombreFiltro) {
        params.append('nombre', nombreFiltro);
    }
    
    if (categoriaFiltro) {
        params.append('categoria', categoriaFiltro);
    }
    
    if (params.toString()) {
        url += '?' + params.toString();
    }
    
    return url;
};

// Función global para cargar datos del inventario
window.cargarDatosInventario = function() {
    // Verificar si los elementos del DOM existen
    const cardsContainer = document.getElementById('cards-insumos');
    const tablaInsumos = document.getElementById('tablaInsumos');
    
    if (!cardsContainer || !tablaInsumos) {
        console.error('No se encontraron los elementos necesarios en el DOM');
        return;
    }

    console.log('Elementos del DOM encontrados:', { 
        cardsContainer: !!cardsContainer, 
        tablaInsumos: !!tablaInsumos 
    });

    // Mostrar indicador de carga
    cardsContainer.innerHTML = '<div class="text-center"><div class="spinner-border" role="status"><span class="visually-hidden">Cargando...</span></div></div>';
    tablaInsumos.innerHTML = '<tr><td colspan="5" class="text-center"><div class="spinner-border" role="status"><span class="visually-hidden">Cargando...</span></div></td></tr>';

    // Obtener los parámetros de la URL actual
    const urlParams = new URLSearchParams(window.location.search);
    const nombreFiltro = urlParams.get('nombre') || '';
    const categoriaFiltro = urlParams.get('categoria_id') || '';
    
    // Construir la URL para la petición
    let url = '/inventario/insumos-stock';
    const params = new URLSearchParams();
    
    if (nombreFiltro) {
        params.append('nombre', nombreFiltro);
    }
    
    if (categoriaFiltro) {
        params.append('categoria_id', categoriaFiltro);
    }
    
    if (params.toString()) {
        url += '?' + params.toString();
    }

    console.log('URL de la petición:', url);

    // Realizar la petición
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
        console.log('Respuesta del servidor:', data);
        
        if (data.success) {
            // Verificar que los datos estén completos
            if (data.insumos_detalle) {
                console.log('Número de insumos en detalle:', data.insumos_detalle.length);
                console.log('Insumos en detalle:', data.insumos_detalle);
                
                // Verificar la estructura de cada insumo
                data.insumos_detalle.forEach((insumo, index) => {
                    console.log(`Insumo ${index + 1}:`, {
                        nombre: insumo.nombre,
                        categoria: insumo.categoria,
                        cantidad: insumo.cantidad,
                        unidad: insumo.unidad,
                        fecha_caducidad: insumo.fecha_caducidad
                    });
                });
            } else {
                console.error('No hay insumos en detalle en la respuesta');
                data.insumos_detalle = [];
            }
            
            if (data.insumos_agrupados) {
                console.log('Número de insumos agrupados:', data.insumos_agrupados.length);
                console.log('Insumos agrupados:', data.insumos_agrupados);
            } else {
                console.error('No hay insumos agrupados en la respuesta');
                data.insumos_agrupados = [];
            }
            
            if (data.totales_por_categoria) {
                console.log('Totales por categoría:', data.totales_por_categoria);
            } else {
                console.error('No hay totales por categoría en la respuesta');
                data.totales_por_categoria = {};
            }
            
            // Actualizar las cards de insumos
            actualizarCardsInsumos(data.insumos_agrupados);
            
            // Actualizar la tabla de insumos
            console.log('Llamando a actualizarTablaInsumos con', data.insumos_detalle.length, 'insumos');
            actualizarTablaInsumos(data.insumos_detalle);
            
            // Actualizar los totales por categoría
            actualizarTotalesCategoria(data.totales_por_categoria);
            
            // Actualizar la paginación
            actualizarPaginacion(data.pagination, url);
        } else {
            if (typeof window.mostrarError === 'function') {
                window.mostrarError(data.error || 'Error al cargar los datos');
            } else {
                console.error(data.error || 'Error al cargar los datos');
            }
        }
    })
    .catch(error => {
        console.error('Error al cargar datos:', error);
        if (typeof window.mostrarError === 'function') {
            window.mostrarError(`Error al cargar los datos: ${error.message}`);
        } else {
            console.error(`Error al cargar los datos: ${error.message}`);
        }
    });
};

document.addEventListener('DOMContentLoaded', function() {
    // Elementos del DOM
    const cardsContainer = document.getElementById('cards-insumos');
    const tablaInsumos = document.getElementById('tablaInsumos');
    
    // Cargar datos iniciales
    window.cargarDatosInventario();

    // Función para actualizar la paginación
    function actualizarPaginacion(pagination, baseUrl) {
        const paginationContainer = document.getElementById('pagination-container');
        if (!paginationContainer) return;
        
        if (!pagination || pagination.pages <= 1) {
            paginationContainer.innerHTML = '';
            return;
        }
        
        // Extraer los parámetros de la URL base
        const urlParams = new URLSearchParams(baseUrl.split('?')[1] || '');
        const nombre = urlParams.get('nombre');
        const categoria = urlParams.get('categoria');
        
        let html = '<nav aria-label="Navegación de páginas"><ul class="pagination justify-content-center">';
        
        // Botón anterior
        if (pagination.page > 1) {
            html += `
                <li class="page-item">
                    <a class="page-link" href="#" data-page="${pagination.page - 1}" aria-label="Anterior">
                        <span aria-hidden="true">&laquo;</span>
                    </a>
                </li>
            `;
        } else {
            html += `
                <li class="page-item disabled">
                    <a class="page-link" href="#" aria-label="Anterior">
                        <span aria-hidden="true">&laquo;</span>
                    </a>
                </li>
            `;
        }
        
        // Páginas
        for (let i = 1; i <= pagination.pages; i++) {
            if (i === pagination.page) {
                html += `<li class="page-item active"><a class="page-link" href="#">${i}</a></li>`;
            } else {
                html += `<li class="page-item"><a class="page-link" href="#" data-page="${i}">${i}</a></li>`;
            }
        }
        
        // Botón siguiente
        if (pagination.page < pagination.pages) {
            html += `
                <li class="page-item">
                    <a class="page-link" href="#" data-page="${pagination.page + 1}" aria-label="Siguiente">
                        <span aria-hidden="true">&raquo;</span>
                    </a>
                </li>
            `;
        } else {
            html += `
                <li class="page-item disabled">
                    <a class="page-link" href="#" aria-label="Siguiente">
                        <span aria-hidden="true">&raquo;</span>
                    </a>
                </li>
            `;
        }
        
        html += '</ul></nav>';
        paginationContainer.innerHTML = html;
        
        // Agregar event listeners a los enlaces de paginación
        const paginationLinks = paginationContainer.querySelectorAll('a[data-page]');
        paginationLinks.forEach(link => {
            link.addEventListener('click', function(e) {
                e.preventDefault();
                const page = this.getAttribute('data-page');
                
                // Actualizar la URL sin recargar la página
                const url = new URL(window.location.href);
                url.searchParams.set('page', page);
                window.history.pushState({}, '', url);
                
                // Cargar solo los datos de la tabla
                cargarDatosTabla(page);
            });
        });
    }

    // Nueva función para cargar solo los datos de la tabla
    function cargarDatosTabla(page) {
        // Verificar si los elementos del DOM existen
        if (!tablaInsumos) {
            console.error('No se encontró el elemento de la tabla en el DOM');
            return;
        }

        // Mostrar indicador de carga
        tablaInsumos.innerHTML = '<tr><td colspan="9" class="text-center"><div class="spinner-border" role="status"><span class="visually-hidden">Cargando...</span></div></td></tr>';

        // Construir la URL para la petición
        let url;
        if (typeof window.construirUrlFiltrado === 'function') {
            url = window.construirUrlFiltrado();
        } else {
            console.error('La función construirUrlFiltrado no está disponible');
            url = '/inventario/insumos-stock/';
        }

        console.log('URL de la petición para la tabla:', url);

        // Realizar la petición
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
            console.log('Respuesta del servidor para la tabla:', data);
            
            if (data.success) {
                // Verificar que los datos estén completos
                if (data.insumos_detalle) {
                    console.log('Número de insumos en detalle:', data.insumos_detalle.length);
                    console.log('Insumos en detalle:', data.insumos_detalle);
                } else {
                    console.error('No hay insumos en detalle en la respuesta');
                    data.insumos_detalle = [];
                }
                
                // Actualizar solo la tabla de insumos
                actualizarTablaInsumos(data.insumos_detalle);
                
                // Actualizar la paginación
                actualizarPaginacion(data.pagination, url);
            } else {
                if (typeof window.mostrarError === 'function') {
                    window.mostrarError(data.error || 'Error al cargar los datos');
                } else {
                    console.error(data.error || 'Error al cargar los datos');
                }
            }
        })
        .catch(error => {
            console.error('Error al cargar datos de la tabla:', error);
            if (typeof window.mostrarError === 'function') {
                window.mostrarError(`Error al cargar los datos: ${error.message}`);
            } else {
                console.error(`Error al cargar los datos: ${error.message}`);
            }
        });
    }

    // Función para actualizar las cards de insumos
    function actualizarCardsInsumos(insumos) {
        if (!cardsContainer) return;
        
        cardsContainer.innerHTML = '';
        
        if (!insumos || insumos.length === 0) {
            cardsContainer.innerHTML = '<div class="alert alert-info">No se encontraron insumos</div>';
            return;
        }
        
        let html = '<div class="row">';
        
        // Asegurarse de que se muestren todos los insumos
        insumos.forEach((insumo, index) => {
            console.log(`Procesando card ${index + 1}/${insumos.length}:`, insumo);
            
            const statusClass = typeof window.getStatusClass === 'function' ? 
                window.getStatusClass(insumo.estado) : 'bg-secondary';
            const numLotes = insumo.lotes ? insumo.lotes.length : 0;
            
            html += `
                <div class="col-md-4 mb-4">
                    <div class="card h-100">
                        <div class="card-header d-flex justify-content-between align-items-center">
                            <h5 class="card-title mb-0">${insumo.nombre}</h5>
                            <span class="badge ${statusClass}">${insumo.estado}</span>
                        </div>
                        <div class="card-body">
                            <p class="card-text"><strong>Categoría:</strong> ${insumo.categoria || 'No especificada'}</p>
                            <p class="card-text"><strong>Stock:</strong> ${insumo.stock || 0} ${insumo.unidad || ''}</p>
                            <p class="card-text"><strong>Lotes:</strong> ${numLotes}</p>
                        </div>
                        <div class="card-footer">
                            <button class="btn btn-primary btn-sm" onclick="mostrarDetallesInsumo('${insumo.nombre}')">
                                Ver Lotes
                            </button>
                        </div>
                    </div>
                </div>
            `;
        });
        
        html += '</div>';
        cardsContainer.innerHTML = html;
    }

    // Función para actualizar la tabla de insumos
    function actualizarTablaInsumos(insumos) {
        if (!tablaInsumos) {
            console.error('No se encontró el elemento de la tabla en el DOM');
            return;
        }
        
        tablaInsumos.innerHTML = '';
        
        if (!insumos || insumos.length === 0) {
            tablaInsumos.innerHTML = '<tr><td colspan="5" class="text-center">No se encontraron insumos</td></tr>';
            return;
        }

        // Verificar que los insumos sean un array
        if (!Array.isArray(insumos)) {
            console.error('Los insumos no son un array:', insumos);
            tablaInsumos.innerHTML = '<tr><td colspan="5" class="text-center text-danger">Error al procesar los datos</td></tr>';
            return;
        }

        console.log('Procesando tabla con', insumos.length, 'insumos');

        // Crear la tabla
        let html = '';
        
        // Asegurarse de que se muestren todos los insumos
        insumos.forEach((insumo, index) => {
            // Verificar que todos los campos estén presentes
            console.log(`Procesando insumo ${index + 1}/${insumos.length}:`, insumo);
            
            // Calcular días hasta caducidad
            let diasCaducidad = 'N/A';
            let badgeClass = 'bg-secondary';
            let iconClass = 'bi bi-question-circle';
            let mensajeCaducidad = '';
            
            if (insumo.fecha_caducidad) {
                const fechaCaducidad = new Date(insumo.fecha_caducidad);
                const hoy = new Date();
                const diferenciaDias = Math.ceil((fechaCaducidad - hoy) / (1000 * 60 * 60 * 24));
                
                if (diferenciaDias < 0) {
                    diasCaducidad = 'Caducado';
                    badgeClass = 'bg-danger';
                    iconClass = 'bi bi-exclamation-triangle';
                    mensajeCaducidad = 'Caducado';
                } else if (diferenciaDias === 0) {
                    diasCaducidad = 'Caduca hoy';
                    badgeClass = 'bg-warning text-dark';
                    iconClass = 'bi bi-clock';
                    mensajeCaducidad = 'Caduca hoy';
                } else if (diferenciaDias <= 7) {
                    diasCaducidad = `Caduca en ${diferenciaDias} días`;
                    badgeClass = 'bg-warning text-dark';
                    iconClass = 'bi bi-clock';
                    mensajeCaducidad = `Caduca en ${diferenciaDias} días`;
                } else {
                    diasCaducidad = `Caduca en ${diferenciaDias} días`;
                    badgeClass = 'bg-success';
                    iconClass = 'bi bi-check-circle';
                    mensajeCaducidad = `Caduca en ${diferenciaDias} días`;
                }
            }
            
            // Asegurarse de que la categoría esté presente
            const categoria = insumo.categoria || 'N/A';
            console.log(`Categoría para ${insumo.nombre}:`, categoria);
            
            html += `
                <tr data-categoria="${insumo.tipo_insumo_id || ''}" data-nombre="${insumo.nombre || ''}" class="">
                    <td class="ps-4 fw-semibold">${insumo.nombre || 'N/A'}</td>
                    <td>
                        <span class="badge" style="background-color: var(--color-beige); color: var(--color-marron-oscuro);">
                            ${categoria}
                        </span>
                    </td>
                    <td class="fw-semibold">${insumo.cantidad || '0'} ${insumo.unidad || ''}</td>
                    <td>
                        <span class="badge ${badgeClass}">
                            <i class="${iconClass} me-1"></i>${mensajeCaducidad}
                        </span>
                    </td>
                    <td class="pe-4 text-end">
                        <button class="btn btn-sm" 
                            style="background-color: var(--color-marron); color: white;"
                            onclick="verDetalleLote('${insumo.lote_id || ''}')"
                            title="Ver detalle del lote">
                            <i class="bi bi-box-seam"></i> Detalle
                        </button>
                    </td>
                </tr>
            `;
        });
        
        tablaInsumos.innerHTML = html;
        console.log('Tabla actualizada con éxito');
    }

    // Función para actualizar los totales por categoría
    function actualizarTotalesCategoria(totales) {
        const totalesContainer = document.getElementById('totales-container');
        if (!totalesContainer) return;
        
        totalesContainer.innerHTML = '';
        
        if (!totales || Object.keys(totales).length === 0) {
            totalesContainer.innerHTML = '<div class="alert alert-info">No hay totales disponibles</div>';
            return;
        }
        
        let html = '<div class="row">';
        
        // Asegurarse de que se muestren todos los totales por categoría
        for (const categoriaId in totales) {
            const categoria = totales[categoriaId];
            console.log(`Procesando total para categoría ${categoriaId}:`, categoria);
            
            html += `
                <div class="col-md-4 mb-3">
                    <div class="card">
                        <div class="card-body">
                            <h5 class="card-title">${categoria.nombre || 'Categoría sin nombre'}</h5>
                            <p class="card-text"><strong>Total:</strong> ${categoria.total || 0} ${categoria.unidad || ''}</p>
                        </div>
                    </div>
                </div>
            `;
        }
        
        html += '</div>';
        totalesContainer.innerHTML = html;
    }
});

// Funciones globales para acciones de insumos
function mostrarDetallesInsumo(nombre) {
    if (!nombre) {
        mostrarError('No se especificó un nombre de insumo');
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
            const insumo = data.insumos_agrupados[0];
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
                                <span class="badge ${getStatusClass(insumo.estado)}">
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
}

function editarInsumo(nombre, loteId) {
    if (!nombre || !loteId) {
        mostrarError('Faltan datos para editar el insumo');
        return;
    }
    
    // Implementar lógica para editar insumo
    console.log('Editar insumo:', nombre, 'lote:', loteId);
}

function eliminarInsumo(nombre, loteId) {
    if (!nombre || !loteId) {
        mostrarError('Faltan datos para eliminar el insumo');
        return;
    }
    
    if (confirm(`¿Está seguro de eliminar el insumo ${nombre} del lote ${loteId}?`)) {
        // Implementar lógica para eliminar insumo
        console.log('Eliminar insumo:', nombre, 'lote:', loteId);
    }
}

function mostrarError(mensaje) {
    // Implementar según el sistema de notificaciones de la aplicación
    alert(mensaje);
} 