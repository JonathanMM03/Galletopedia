/**
 * Funciones para la gestión de solicitudes de galletas
 */

// Función para verificar los insumos disponibles para una receta
async function verificarInsumosReceta(recetaId, cantidad = 100) {
    try {
        const response = await fetch('/produccion/verificar_insumos_receta', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({
                receta_id: recetaId,
                cantidad: cantidad
            })
        });

        const data = await response.json();
        
        if (data.success) {
            Swal.fire({
                icon: 'success',
                title: '¡Insumos Disponibles!',
                text: data.message
            });
            return true;
        } else {
            Swal.fire({
                icon: 'error',
                title: 'Insumos Insuficientes',
                text: data.message
            });
            return false;
        }
    } catch (error) {
        console.error('Error al verificar insumos:', error);
        Swal.fire({
            icon: 'error',
            title: 'Error',
            text: 'Ocurrió un error al verificar los insumos disponibles.'
        });
        return false;
    }
}

// Función para obtener el token CSRF
function getCsrfToken() {
    return document.querySelector('meta[name="csrf-token"]').getAttribute('content');
}

// Función para manejar el envío del formulario
async function solicitarGalletas(event) {
    event.preventDefault();
    
    const recetaId = document.getElementById('receta_id').value;
    const cantidad = document.getElementById('cantidad').value;
    
    if (!recetaId) {
        Swal.fire({
            icon: 'error',
            title: 'Error',
            text: 'Por favor seleccione una receta.'
        });
        return;
    }
    
    // Mostrar indicador de carga
    Swal.fire({
        title: 'Procesando solicitud',
        text: 'Por favor espere...',
        allowOutsideClick: false,
        didOpen: () => {
            Swal.showLoading();
        }
    });
    
    // Enviar el formulario usando fetch
    const form = document.getElementById('formSolicitarGalletas');
    const formData = new FormData(form);
    
    try {
        const response = await fetch(form.action, {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': getCsrfToken()
            }
        });
        
        if (response.redirected) {
            window.location.href = response.url;
            return;
        }
        
        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
            const data = await response.json();
            if (data.success) {
                Swal.fire({
                    icon: 'success',
                    title: '¡Éxito!',
                    text: data.message || 'Solicitud enviada correctamente'
                }).then(() => {
                    window.location.reload();
                });
            } else {
                Swal.fire({
                    icon: 'error',
                    title: 'Error',
                    text: data.message || 'Error al procesar la solicitud'
                });
            }
        } else {
            // Si la respuesta no es JSON, asumimos que es una redirección
            window.location.href = response.url;
        }
    } catch (error) {
        console.error('Error al enviar la solicitud:', error);
        Swal.fire({
            icon: 'error',
            title: 'Error',
            text: 'Ocurrió un error al enviar la solicitud'
        });
    }
}

// Función para actualizar la cantidad de galletas
function actualizarCantidadGalletas() {
    const recetaId = document.getElementById('receta_id').value;
    const cantidad = document.getElementById('cantidad').value;
    const submitBtn = document.querySelector('#formSolicitarGalletas button[type="submit"]');
    
    if (recetaId && cantidad) {
        verificarInsumosReceta(recetaId, cantidad);
    }
}

// Event Listeners
document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('formSolicitarGalletas');
    const cantidadInput = document.getElementById('cantidad');
    const recetaSelect = document.getElementById('receta_id');
    const btnVerificar = document.getElementById('btnVerificarInsumos');
    
    if (form) {
        form.addEventListener('submit', solicitarGalletas);
    }
    
    if (cantidadInput) {
        cantidadInput.addEventListener('change', actualizarCantidadGalletas);
    }
    
    if (recetaSelect) {
        recetaSelect.addEventListener('change', actualizarCantidadGalletas);
    }
    
    if (btnVerificar) {
        btnVerificar.addEventListener('click', function() {
            const recetaId = document.getElementById('receta_id').value;
            const cantidad = document.getElementById('cantidad').value;
            verificarInsumosReceta(recetaId, cantidad);
        });
    }
}); 