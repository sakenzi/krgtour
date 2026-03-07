/**
 * КарагандаТур — Leaflet Map Module
 * Handles interactive maps for routes, places, admin editing
 */

const KGDMap = (function() {

    // ============ MAP ICONS ============
    const DIFFICULTY_COLORS = {
        easy: '#10B981',
        medium: '#F59E0B',
        hard: '#EF4444',
        expert: '#7C3AED',
    };

    function createRouteIcon(difficulty = 'medium') {
        const color = DIFFICULTY_COLORS[difficulty] || '#7C3AED';
        return L.divIcon({
            className: '',
            html: `<div style="
                width: 36px; height: 36px;
                background: ${color};
                border-radius: 50% 50% 50% 0;
                transform: rotate(-45deg);
                border: 3px solid white;
                box-shadow: 0 2px 8px rgba(0,0,0,0.3);
                display: flex; align-items: center; justify-content: center;
            "><span style="transform: rotate(45deg); color: white; font-size: 14px; display: block;">🏔</span></div>`,
            iconSize: [36, 36],
            iconAnchor: [18, 36],
            popupAnchor: [0, -36],
        });
    }

    function createPlaceIcon(emoji = '📍', color = '#7C3AED') {
        return L.divIcon({
            className: '',
            html: `<div style="
                width: 32px; height: 32px;
                background: white;
                border-radius: 50%;
                border: 2px solid ${color};
                box-shadow: 0 2px 6px rgba(0,0,0,0.2);
                display: flex; align-items: center; justify-content: center;
                font-size: 15px;
            ">${emoji}</div>`,
            iconSize: [32, 32],
            iconAnchor: [16, 32],
            popupAnchor: [0, -32],
        });
    }

    function createWaypointIcon(type = 'waypoint', order = 0) {
        const icons = { start: '🟢', end: '🔴', waypoint: '🔵', attraction: '⭐', rest: '🏕' };
        const icon = icons[type] || '📍';
        return L.divIcon({
            className: '',
            html: `<div style="
                background: white;
                border: 2px solid #7C3AED;
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 11px;
                font-weight: 700;
                white-space: nowrap;
                box-shadow: 0 2px 6px rgba(0,0,0,0.2);
                font-family: 'Manrope', sans-serif;
            ">${icon} ${order > 0 ? order : ''}</div>`,
            iconSize: 'auto',
            iconAnchor: [20, 28],
            popupAnchor: [0, -28],
        });
    }

    // ============ BASE MAP INIT ============
    function initMap(containerId, options = {}) {
        const defaults = {
            center: [49.8047, 73.1094], // Karaganda
            zoom: 11,
            zoomControl: true,
        };
        const opts = { ...defaults, ...options };

        const map = L.map(containerId, {
            center: opts.center,
            zoom: opts.zoom,
            zoomControl: opts.zoomControl,
        });

        // Tile layers
        const osmLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© <a href="https://openstreetmap.org">OpenStreetMap</a>',
            maxZoom: 19,
        });

        const satelliteLayer = L.tileLayer(
            'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            { attribution: 'Tiles © Esri', maxZoom: 19 }
        );

        osmLayer.addTo(map);

        // Layer control
        L.control.layers({
            '🗺 Карта': osmLayer,
            '🛰 Спутник': satelliteLayer,
        }).addTo(map);

        return map;
    }

    // ============ ADD ROUTES TO MAP ============
    function addRoutesToMap(map, routes, options = {}) {
        const { onClick, cluster = false } = options;
        const markers = [];
        const routeLines = [];

        routes.forEach(route => {
            if (!route.start_lat || !route.start_lng) return;

            const marker = L.marker(
                [route.start_lat, route.start_lng],
                { icon: createRouteIcon(route.difficulty) }
            );

            // Popup HTML
            const diffLabels = { easy: 'Лёгкий', medium: 'Средний', hard: 'Сложный', expert: 'Экстрим' };
            const popupHtml = `
                <div class="map-popup">
                    <div class="map-popup-title">${route.title}</div>
                    <div class="map-popup-meta">
                        <span>📏 ${route.distance_km} км</span>
                        <span>⏱ ${route.duration_hours} ч</span>
                        ${route.avg_rating ? `<span>⭐ ${route.avg_rating}</span>` : ''}
                    </div>
                    <a href="/routes/${route.slug}/" class="map-popup-link">Открыть маршрут →</a>
                </div>
            `;

            marker.bindPopup(popupHtml, { closeButton: false, className: 'custom-popup' });

            if (onClick) {
                marker.on('click', () => onClick(route));
            }

            marker.addTo(map);
            markers.push(marker);

            // Draw route line if GeoJSON available
            if (route.route_geojson) {
                const line = L.geoJSON(route.route_geojson, {
                    style: {
                        color: DIFFICULTY_COLORS[route.difficulty] || '#7C3AED',
                        weight: 4,
                        opacity: 0.8,
                    }
                }).addTo(map);
                routeLines.push(line);
            }
        });

        return { markers, routeLines };
    }

    // ============ ADD PLACES TO MAP ============
    function addPlacesToMap(map, places) {
        const markers = [];
        places.forEach(place => {
            if (!place.lat || !place.lng) return;

            const marker = L.marker(
                [place.lat, place.lng],
                { icon: createPlaceIcon(place.icon || '📍') }
            );

            const popupHtml = `
                <div class="map-popup">
                    <div class="map-popup-title">${place.name}</div>
                    <div class="map-popup-meta">
                        <span>${place.category || ''}</span>
                        ${place.avg_rating ? `<span>⭐ ${place.avg_rating}</span>` : ''}
                    </div>
                    <a href="/places/${place.slug}/" class="map-popup-link">Подробнее →</a>
                </div>
            `;

            marker.bindPopup(popupHtml, { closeButton: false });
            marker.addTo(map);
            markers.push(marker);
        });
        return markers;
    }

    // ============ DRAW ROUTE DETAIL MAP ============
    function initRouteDetailMap(containerId, routeData) {
        const { points, geojson, title, difficulty } = routeData;

        if (!points || !points.length) return;

        const center = [points[0].lat, points[0].lng];
        const map = initMap(containerId, { center, zoom: 13 });

        // Add all waypoints
        points.forEach((point, i) => {
            const marker = L.marker(
                [point.lat, point.lng],
                { icon: createWaypointIcon(point.point_type, i + 1) }
            );
            marker.bindPopup(`<div class="map-popup"><div class="map-popup-title">${point.name}</div></div>`);
            marker.addTo(map);
        });

        // Draw line between points
        if (points.length >= 2) {
            const coords = points.map(p => [p.lat, p.lng]);
            const line = L.polyline(coords, {
                color: DIFFICULTY_COLORS[difficulty] || '#7C3AED',
                weight: 5,
                opacity: 0.9,
                dashArray: null,
            }).addTo(map);

            map.fitBounds(line.getBounds(), { padding: [40, 40] });
        }

        return map;
    }

    // ============ ADMIN MAP EDITOR ============
    function initAdminMapEditor(containerId, options = {}) {
        const { existingPoints = [], onPointsChange } = options;

        const map = initMap(containerId, { zoom: 12 });
        let points = [...existingPoints];
        let markers = [];
        let polyline = null;

        // Render existing points
        function renderPoints() {
            markers.forEach(m => map.removeLayer(m));
            markers = [];
            if (polyline) map.removeLayer(polyline);

            points.forEach((point, i) => {
                const marker = L.marker([point.lat, point.lng], {
                    icon: createWaypointIcon(point.type, i + 1),
                    draggable: true,
                });

                marker.on('drag', (e) => {
                    const latlng = e.target.getLatLng();
                    points[i].lat = latlng.lat;
                    points[i].lng = latlng.lng;
                    drawLine();
                    onPointsChange?.(points);
                });

                marker.on('dblclick', () => {
                    points.splice(i, 1);
                    renderPoints();
                    onPointsChange?.(points);
                });

                const popupHtml = `
                    <div style="padding: 8px; min-width: 160px;">
                        <b>${i + 1}. ${point.name || 'Точка'}</b><br>
                        <small style="color: #6B7280;">${point.lat.toFixed(5)}, ${point.lng.toFixed(5)}</small><br>
                        <button onclick="this.closest('.leaflet-popup').dispatchEvent(new Event('deletepoint'))"
                            style="margin-top: 6px; padding: 3px 10px; background: #EF4444; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 12px;">
                            🗑 Удалить
                        </button>
                    </div>
                `;
                marker.bindPopup(popupHtml);
                marker.addTo(map);
                markers.push(marker);
            });

            drawLine();
        }

        function drawLine() {
            if (polyline) map.removeLayer(polyline);
            if (points.length >= 2) {
                polyline = L.polyline(points.map(p => [p.lat, p.lng]), {
                    color: '#7C3AED', weight: 4, opacity: 0.8,
                }).addTo(map);
            }
        }

        // Click to add point
        map.on('click', (e) => {
            const name = prompt(`Название точки #${points.length + 1}:`, `Точка ${points.length + 1}`);
            if (name !== null) {
                points.push({
                    lat: e.latlng.lat,
                    lng: e.latlng.lng,
                    name: name || `Точка ${points.length + 1}`,
                    type: points.length === 0 ? 'start' : 'waypoint',
                });
                renderPoints();
                onPointsChange?.(points);
                updateHiddenFields(points);
            }
        });

        // Update start/end hidden inputs
        function updateHiddenFields(pts) {
            if (pts.length > 0) {
                const startLatEl = document.getElementById('id_start_lat');
                const startLngEl = document.getElementById('id_start_lng');
                if (startLatEl) startLatEl.value = pts[0].lat;
                if (startLngEl) startLngEl.value = pts[0].lng;
            }
            if (pts.length > 1) {
                const endLatEl = document.getElementById('id_end_lat');
                const endLngEl = document.getElementById('id_end_lng');
                const last = pts[pts.length - 1];
                if (endLatEl) endLatEl.value = last.lat;
                if (endLngEl) endLngEl.value = last.lng;
            }

            // Update route_points_json hidden field
            const pointsJson = document.getElementById('routePointsJson');
            if (pointsJson) pointsJson.value = JSON.stringify(pts);
        }

        renderPoints();
        if (existingPoints.length >= 2) {
            const coords = existingPoints.map(p => [p.lat, p.lng]);
            map.fitBounds(L.latLngBounds(coords), { padding: [40, 40] });
        }

        return { map, getPoints: () => points };
    }

    // ============ FULL PAGE MAP ============
    function initFullMap(containerId, { routes = [], places = [] }) {
        const map = initMap(containerId, { zoom: 10 });

        // Layer groups
        const routesLayer = L.layerGroup();
        const placesLayer = L.layerGroup();

        addRoutesToMap(map, routes).markers.forEach(m => routesLayer.addLayer(m));
        addPlacesToMap(map, places).forEach(m => placesLayer.addLayer(m));

        routesLayer.addTo(map);
        placesLayer.addTo(map);

        L.control.layers({}, {
            '🏔 Маршруты': routesLayer,
            '📍 Места': placesLayer,
        }).addTo(map);

        return map;
    }

    return {
        initMap,
        initRouteDetailMap,
        initAdminMapEditor,
        initFullMap,
        addRoutesToMap,
        addPlacesToMap,
    };

})();

// Auto-initialize maps with data attributes
document.addEventListener('DOMContentLoaded', () => {
    // Route detail map
    const routeMapEl = document.getElementById('routeDetailMap');
    if (routeMapEl) {
        const pointsData = routeMapEl.dataset.points;
        const difficulty = routeMapEl.dataset.difficulty;
        if (pointsData) {
            try {
                const points = JSON.parse(pointsData);
                if (points.length > 0) {
                    KGDMap.initRouteDetailMap('routeDetailMap', { points, difficulty });
                }
            } catch (e) { console.error('Map init error:', e); }
        }
    }

    // Full map page
    const fullMapEl = document.getElementById('fullPageMap');
    if (fullMapEl) {
        try {
            const routes = JSON.parse(fullMapEl.dataset.routes || '[]');
            const places = JSON.parse(fullMapEl.dataset.places || '[]');
            KGDMap.initFullMap('fullPageMap', { routes, places });
        } catch (e) { console.error('Map init error:', e); }
    }

    // Admin editor map
    const adminMapEl = document.getElementById('adminEditorMap');
    if (adminMapEl) {
        try {
            const existingPoints = JSON.parse(adminMapEl.dataset.points || '[]');
            const editor = KGDMap.initAdminMapEditor('adminEditorMap', {
                existingPoints,
                onPointsChange: (pts) => {
                    const el = document.getElementById('routePointsJson');
                    if (el) el.value = JSON.stringify(pts);
                }
            });
        } catch (e) { console.error('Admin map init error:', e); }
    }
});