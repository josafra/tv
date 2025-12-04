const links = document.querySelectorAll('.grid a');
let selectedImageIndex = 0;
let isAnimating = false;

function updateSelection() {
    // Prevenir múltiples animaciones simultáneas pero con tiempo muy corto
    if (isAnimating) return;
    isAnimating = true;

    // Quitar selección de todos los elementos
    links.forEach(link => {
        link.classList.remove('selected');
    });
    
    // Aplicar selección al elemento actual
    links[selectedImageIndex].classList.add('selected');
    
    // Actualizar el foco
    links[selectedImageIndex].focus();
    
    // Scroll inmediato al elemento seleccionado
    const selectedElement = links[selectedImageIndex];
    
    // Usamos scrollIntoView con comportamiento "auto" para que sea más rápido
    selectedElement.scrollIntoView({
        behavior: 'auto',
        block: 'center',
        inline: 'center'
    });
    
    // Permitir nueva animación después de un tiempo muy corto
    setTimeout(() => {
        isAnimating = false;
    }, 100); // Tiempo reducido para mayor velocidad
}

function openImage() {
    links[selectedImageIndex].click();
}

function handleKeydown(event) {
    // Permitir procesar teclas incluso durante animaciones para mayor rapidez
    const columnCount = 5; // Número de columnas en la cuadrícula
    const rowCount = Math.ceil(links.length / columnCount);
    const currentRow = Math.floor(selectedImageIndex / columnCount);
    const currentCol = selectedImageIndex % columnCount;
    
    switch (event.key) {
        case 'ArrowUp':
            if (currentRow > 0) {
                selectedImageIndex -= columnCount;
            }
            break;
        case 'ArrowDown':
            if (currentRow < rowCount - 1 && (selectedImageIndex + columnCount) < links.length) {
                selectedImageIndex += columnCount;
            }
            break;
        case 'ArrowLeft':
            if (currentCol > 0) {
                selectedImageIndex -= 1;
            }
            break;
        case 'ArrowRight':
            if (currentCol < columnCount - 1 && (selectedImageIndex + 1) < links.length) {
                selectedImageIndex += 1;
            }
            break;
        case 'Enter':
            openImage();
            return; // No continuar para evitar scroll innecesario
        default:
            return; // No hacer nada para otras teclas
    }
    
    event.preventDefault(); // Prevenir comportamiento predeterminado
    localStorage.setItem('lastSelectedIndex', selectedImageIndex);
    updateSelection();
}

// Manejar el foco cuando se usa el tab
links.forEach((link, index) => {
    link.addEventListener('focus', () => {
        selectedImageIndex = index;
        updateSelection();
    });
    
    // Añadir manejo de hover con mouse
    link.addEventListener('mouseenter', () => {
        selectedImageIndex = index;
        updateSelection();
    });
});

// Inicializar la selección al cargar la página
window.addEventListener('load', () => {
    const lastSelectedIndex = localStorage.getItem('lastSelectedIndex');
    if (lastSelectedIndex !== null) {
        selectedImageIndex = parseInt(lastSelectedIndex, 10);
        // Comprobar si el índice es válido
        if (selectedImageIndex >= links.length) {
            selectedImageIndex = 0;
        }
    }
    updateSelection();
});

document.addEventListener('keydown', handleKeydown);