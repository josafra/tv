// Configuración de países y categorías
const paises = {
    // PAÍSES
    'mexico': { nombre: 'México', url: 'https://raw.githubusercontent.com/josafra/tv/main/mexico.m3u' },
    'guatemala': { nombre: 'Guatemala', url: 'https://raw.githubusercontent.com/josafra/tv/main/guatemala.m3u' },
    'elsalvador': { nombre: 'El Salvador', url: 'https://raw.githubusercontent.com/josafra/tv/main/elsalvador.m3u' },
    'honduras': { nombre: 'Honduras', url: 'https://raw.githubusercontent.com/josafra/tv/main/honduras.m3u' },
    'nicaragua': { nombre: 'Nicaragua', url: 'https://raw.githubusercontent.com/josafra/tv/main/nicaragua.m3u' },
    'costarica': { nombre: 'Costa Rica', url: 'https://raw.githubusercontent.com/josafra/tv/main/costarica.m3u' },
    'panama': { nombre: 'Panamá', url: 'https://raw.githubusercontent.com/josafra/tv/main/panama.m3u' },
    'cuba': { nombre: 'Cuba', url: 'https://raw.githubusercontent.com/josafra/tv/main/cuba.m3u' },
    'republicadominicana': { nombre: 'República Dominicana', url: 'https://raw.githubusercontent.com/josafra/tv/main/republicadominicana.m3u' },
    'puertorico': { nombre: 'Puerto Rico', url: 'https://raw.githubusercontent.com/josafra/tv/main/puertorico.m3u' },
    'venezuela': { nombre: 'Venezuela', url: 'https://raw.githubusercontent.com/josafra/tv/main/venezuela.m3u' },
    'colombia': { nombre: 'Colombia', url: 'https://raw.githubusercontent.com/josafra/tv/main/colombia.m3u' },
    'ecuador': { nombre: 'Ecuador', url: 'https://raw.githubusercontent.com/josafra/tv/main/ecuador.m3u' },
    'peru': { nombre: 'Perú', url: 'https://raw.githubusercontent.com/josafra/tv/main/peru.m3u' },
    'bolivia': { nombre: 'Bolivia', url: 'https://raw.githubusercontent.com/josafra/tv/main/bolivia.m3u' },
    'paraguay': { nombre: 'Paraguay', url: 'https://raw.githubusercontent.com/josafra/tv/main/paraguay.m3u' },
    'chile': { nombre: 'Chile', url: 'https://raw.githubusercontent.com/josafra/tv/main/chile.m3u' },
    'argentina': { nombre: 'Argentina', url: 'https://raw.githubusercontent.com/josafra/tv/main/Argentina.m3u' },
    'uruguay': { nombre: 'Uruguay', url: 'https://raw.githubusercontent.com/josafra/tv/main/uruguay.m3u' },
    'espana': { nombre: 'España', url: 'https://raw.githubusercontent.com/josafra/tv/main/espana.m3u' },
    // CATEGORÍAS
    'deportes': { nombre: 'Deportes', url: 'https://raw.githubusercontent.com/josafra/tv/main/deportes.m3u' },
    'noticias': { nombre: 'Noticias', url: 'https://raw.githubusercontent.com/josafra/tv/main/noticias.m3u' },
    'musica': { nombre: 'Música', url: 'https://raw.githubusercontent.com/josafra/tv/main/musica.m3u' },
    'peliculas': { nombre: 'Películas', url: 'https://raw.githubusercontent.com/josafra/tv/main/peliculas.m3u' },
    'series': { nombre: 'Series', url: 'https://raw.githubusercontent.com/josafra/tv/main/series.m3u' },
    'infantil': { nombre: 'Infantil', url: 'https://raw.githubusercontent.com/josafra/tv/main/infantil.m3u' },
    'documentales': { nombre: 'Documentales', url: 'https://raw.githubusercontent.com/josafra/tv/main/documentales.m3u' },
    'entretenimiento': { nombre: 'Entretenimiento', url: 'https://raw.githubusercontent.com/josafra/tv/main/entretenimiento.m3u' },
    'cultura': { nombre: 'Cultura', url: 'https://raw.githubusercontent.com/josafra/tv/main/cultura.m3u' },
    'religion': { nombre: 'Religión', url: 'https://raw.githubusercontent.com/josafra/tv/main/religion.m3u' },
    'cocina': { nombre: 'Cocina', url: 'https://raw.githubusercontent.com/josafra/tv/main/cocina.m3u' },
    'viajes': { nombre: 'Viajes', url: 'https://raw.githubusercontent.com/josafra/tv/main/viajes.m3u' },
    'tecnologia': { nombre: 'Tecnología', url: 'https://raw.githubusercontent.com/josafra/tv/main/tecnologia.m3u' },
    'salud': { nombre: 'Salud', url: 'https://raw.githubusercontent.com/josafra/tv/main/salud.m3u' },
    'naturaleza': { nombre: 'Naturaleza', url: 'https://raw.githubusercontent.com/josafra/tv/main/naturaleza.m3u' },
    'ciencia': { nombre: 'Ciencia', url: 'https://raw.githubusercontent.com/josafra/tv/main/ciencia.m3u' },
    'historia': { nombre: 'Historia', url: 'https://raw.githubusercontent.com/josafra/tv/main/historia.m3u' },
    'educacion': { nombre: 'Educación', url: 'https://raw.githubusercontent.com/josafra/tv/main/educacion.m3u' },
    'variedades': { nombre: 'Variedades', url: 'https://raw.githubusercontent.com/josafra/tv/main/variedades.m3u' }
};

// Elementos del DOM
const video = document.getElementById('video');
video.controls = false;
const overlay = document.getElementById('videoOverlay');
const welcomeOverlay = document.getElementById('welcomeOverlay');
const loadingChannelName = document.getElementById('loadingChannelName');
const playlistDiv = document.getElementById('playlist');
const currentChannelLabel = document.getElementById('currentChannel');
const initialMessage = document.getElementById('initialMessage');
const countryTitle = document.getElementById('countryTitle');
const welcomeText = document.getElementById('welcomeText');

// Variables globales
let hls;
let currentSelectedIndex = 0;
let channelButtons = [];
let currentPlayingIndex = -1;
let currentCountry = '';
let allChannels = []; // Array con todos los canales
let showingFavorites = false; // Indica si estamos viendo favoritos

// ======================================
// SISTEMA DE FAVORITOS
// ======================================

function getFavorites() {
    const favs = localStorage.getItem('tv_favorites');
    return favs ? JSON.parse(favs) : [];
}

function saveFavorites(favorites) {
    localStorage.setItem('tv_favorites', JSON.stringify(favorites));
}

function isFavorite(channelName, channelUrl) {
    const favorites = getFavorites();
    return favorites.some(fav => fav.name === channelName && fav.url === channelUrl);
}

function toggleFavorite(channelName, channelUrl) {
    let favorites = getFavorites();
    const index = favorites.findIndex(fav => fav.name === channelName && fav.url === channelUrl);
    
    if (index >= 0) {
        // Quitar de favoritos
        favorites.splice(index, 1);
    } else {
        // Añadir a favoritos
        favorites.push({
            name: channelName,
            url: channelUrl,
            country: currentCountry
        });
    }
    
    saveFavorites(favorites);
    
    // Actualizar UI
    if (showingFavorites) {
        displayFavorites();
    } else {
        updateFavoriteIcons();
    }
}

function updateFavoriteIcons() {
    channelButtons.forEach(btn => {
        const name = btn.textContent.replace('⭐ ', '').trim();
        const url = btn.getAttribute('data-url');
        
        if (isFavorite(name, url)) {
            if (!btn.textContent.startsWith('⭐')) {
                btn.textContent = '⭐ ' + name;
            }
        } else {
            btn.textContent = btn.textContent.replace('⭐ ', '');
        }
    });
}

function displayFavorites() {
    const favorites = getFavorites();
    
    playlistDiv.innerHTML = '<div class="section-title">⭐ Favoritos</div>';
    
    if (favorites.length === 0) {
        playlistDiv.innerHTML += '<p style="color: #ff6b6b; text-align: center; padding: 20px;">No tienes favoritos<br><br>Presiona "F" en cualquier canal para agregarlo</p>';
        channelButtons = [];
        return;
    }
    
    channelButtons = [];
    
    favorites.forEach((fav, index) => {
        const btn = document.createElement('button');
        btn.textContent = '⭐ ' + fav.name;
        btn.className = 'channel';
        btn.setAttribute('tabindex', '0');
        btn.setAttribute('data-url', fav.url);
        btn.onclick = () => {
            handleChannelAction(channelButtons.indexOf(btn));
        };
        playlistDiv.appendChild(btn);
        channelButtons.push(btn);
    });
    
    if (channelButtons.length > 0) {
        currentSelectedIndex = 0;
        channelButtons[0].classList.add('selected');
        channelButtons[0].focus();
    }
    
    showingFavorites = true;
    countryTitle.textContent = '⭐ Favoritos';
}

// ======================================
// FUNCIONES ORIGINALES
// ======================================

function getCurrentCountry() {
    const urlParams = new URLSearchParams(window.location.search);
    const pais = urlParams.get('pais');
    return pais ? pais.toLowerCase() : 'mexico';
}

async function loadM3U() {
    currentCountry = getCurrentCountry();
    const paisData = paises[currentCountry];
    
    if (!paisData) {
        playlistDiv.innerHTML = '<p style="color: #ff6b6b;">País/Categoría no encontrado</p>';
        welcomeOverlay.classList.add('hidden');
        return;
    }

    countryTitle.textContent = paisData.nombre;
    welcomeText.textContent = 'TV ' + paisData.nombre;
    document.title = 'Reproductor M3U8 - ' + paisData.nombre;

    try {
        const cacheBuster = '?t=' + Date.now();
        const response = await fetch(paisData.url + cacheBuster);
        
        if (!response.ok) throw new Error('Error al cargar el archivo M3U');
        
        const text = await response.text();
        const m3uData = text.trim().split('\n');
        
        playlistDiv.innerHTML = '<div class="section-title">' + paisData.nombre + '</div>';
        
        allChannels = [];
        channelButtons = [];
        
        for (let i = 0; i < m3uData.length; i++) {
            if (m3uData[i].startsWith('#EXTINF')) {
                const name = m3uData[i].split(',')[1].trim();
                const url = m3uData[i + 1].trim();

                if (url && !url.startsWith('#')) {
                    allChannels.push({ name, url });
                    
                    const btn = document.createElement('button');
                    const displayName = isFavorite(name, url) ? '⭐ ' + name : name;
                    btn.textContent = displayName;
                    btn.className = 'channel';
                    btn.setAttribute('tabindex', '0');
                    btn.setAttribute('data-url', url);
                    btn.onclick = () => {
                        handleChannelAction(channelButtons.indexOf(btn));
                    };
                    playlistDiv.appendChild(btn);
                    channelButtons.push(btn);
                }
            }
        }

        if (channelButtons.length > 0) {
            channelButtons[0].classList.add('selected');
            channelButtons[0].focus();
        } else {
            playlistDiv.innerHTML += '<p style="color: #ff6b6b;">No se encontraron canales</p>';
        }

        showingFavorites = false;

        setTimeout(() => {
            welcomeOverlay.classList.add('hidden');
        }, 2000);

    } catch (error) {
        console.error('Error:', error);
        playlistDiv.innerHTML += '<p style="color: #ff6b6b;">Error: ' + error.message + '</p>';
        welcomeOverlay.classList.add('hidden');
    }
}

function playStream(url, name, index) {
    if (hls) hls.destroy();

    // Limpiar nombre de estrella para mostrar
    const cleanName = name.replace('⭐ ', '');
    loadingChannelName.textContent = cleanName;
    overlay.style.opacity = '1';
    overlay.style.pointerEvents = 'auto';
    welcomeOverlay.classList.add('hidden');

    if (Hls.isSupported()) {
        hls = new Hls();
        hls.loadSource(url);
        hls.attachMedia(video);
        hls.on(Hls.Events.MANIFEST_PARSED, function () {
            video.play();
        });
    } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
        video.src = url;
        video.addEventListener('loadedmetadata', function () {
            video.play();
        });
    } else {
        alert('Tu navegador no soporta HLS.');
        overlay.style.opacity = '0';
        overlay.style.pointerEvents = 'none';
        return;
    }

    video.addEventListener('playing', () => {
        overlay.style.opacity = '0';
        overlay.style.pointerEvents = 'none';
    }, { once: true });

    currentChannelLabel.textContent = cleanName;
    initialMessage.style.display = 'none';

    if (currentPlayingIndex >= 0) {
        channelButtons[currentPlayingIndex].classList.remove('playing');
    }
    currentPlayingIndex = index;
    channelButtons[currentPlayingIndex].classList.add('playing');
}

function toggleFullscreen() {
    if (video.requestFullscreen) {
        video.requestFullscreen();
    } else if (video.webkitRequestFullscreen) {
        video.webkitRequestFullscreen();
    } else if (video.msRequestFullscreen) {
        video.msRequestFullscreen();
    }
}

function selectChannel(index) {
    if (index < 0 || index >= channelButtons.length) return;

    channelButtons[currentSelectedIndex].classList.remove('selected');
    currentSelectedIndex = index;
    const selectedBtn = channelButtons[currentSelectedIndex];
    selectedBtn.classList.add('selected');
    selectedBtn.focus();
    selectedBtn.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

function handleChannelAction(index) {
    if (index < 0 || index >= channelButtons.length) return;

    selectChannel(index);

    if (currentPlayingIndex === index) {
        toggleFullscreen();
    } else {
        const selectedBtn = channelButtons[currentSelectedIndex];
        const url = selectedBtn.getAttribute('data-url');
        const name = selectedBtn.textContent;
        playStream(url, name, index);
    }
}

// ======================================
// EVENTOS DE TECLADO
// ======================================

document.addEventListener('keydown', function(e) {
    switch(e.key) {
        case 'ArrowUp':
            e.preventDefault();
            selectChannel(currentSelectedIndex - 1);
            break;
        case 'ArrowDown':
            e.preventDefault();
            selectChannel(currentSelectedIndex + 1);
            break;
        case 'Enter':
        case ' ':
            e.preventDefault();
            handleChannelAction(currentSelectedIndex);
            break;
        case 'f':
        case 'F':
            // Añadir/quitar favorito
            e.preventDefault();
            if (channelButtons.length > 0 && currentSelectedIndex >= 0) {
                const btn = channelButtons[currentSelectedIndex];
                const cleanName = btn.textContent.replace('⭐ ', '').trim();
                const url = btn.getAttribute('data-url');
                toggleFavorite(cleanName, url);
            }
            break;
        case 's':
        case 'S':
            // Mostrar favoritos
            e.preventDefault();
            if (showingFavorites) {
                loadM3U(); // Volver a la lista normal
            } else {
                displayFavorites();
            }
            break;
    }
});

channelButtons.forEach((btn, index) => {
    btn.addEventListener('focus', () => {
        selectChannel(index);
    });
});

// Inicializar
loadM3U();