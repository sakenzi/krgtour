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
        const el = document.getElementById(containerId);
        if (!el) {
            console.warn('Map container not found:', containerId);
            return null;
        }

        // Prevent double initialization
        if (el._leaflet_id) {
            console.warn('Map already initialized:', containerId);
            return null;
        }

        const defaults = {
            center: [49.8047, 73.1094], // Karaganda
            zoom: 11,
            zoomControl: true,
        };
        const opts = { ...defaults, ...options };

        // Validate center coordinates
        if (!opts.center || opts.center[0] == null || opts.center[1] == null ||
            isNaN(opts.center[0]) || isNaN(opts.center[1])) {
            console.warn('Invalid map center coordinates:', opts.center, '— using Karaganda default');
            opts.center = defaults.center;
        }

        const map = L.map(containerId, {
            center: opts.center,
            zoom: opts.zoom,
            zoomControl: opts.zoomControl,
        });

        // Tile layers. Some public tile providers can temporarily answer with
        // "access blocked", so the base map has a fallback source.
        const primaryLayer = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
            maxZoom: 19,
            crossOrigin: true,
        });

        const fallbackLayer = L.tileLayer('https://{s}.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png', {
            attribution: '&copy; OpenStreetMap contributors, Tiles style by HOT',
            maxZoom: 19,
            crossOrigin: true,
        });

        const topoLayer = L.tileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; OpenStreetMap contributors, SRTM | OpenTopoMap',
            maxZoom: 17,
            crossOrigin: true,
        });

        let fallbackEnabled = false;
        primaryLayer.on('tileerror', () => {
            if (fallbackEnabled) return;
            fallbackEnabled = true;
            if (map.hasLayer(primaryLayer)) {
                map.removeLayer(primaryLayer);
                fallbackLayer.addTo(map);
            }
        });

        primaryLayer.addTo(map);

        // Layer control
        L.control.layers({
            'Карта': primaryLayer,
            'Карта резерв': fallbackLayer,
            'Рельеф': topoLayer,
        }).addTo(map);

        return map;
    }

    // ============ ADD ROUTES TO MAP ============
    function addRoutesToMap(map, routes, options = {}) {
        if (!map) return { markers: [], routeLines: [] };
        const { onClick } = options;
        const markers = [];
        const routeLines = [];

        routes.forEach(route => {
            if (!route.start_lat || !route.start_lng ||
                isNaN(route.start_lat) || isNaN(route.start_lng)) return;

            const marker = L.marker(
                [parseFloat(route.start_lat), parseFloat(route.start_lng)],
                { icon: createRouteIcon(route.difficulty) }
            );

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

            if (route.route_geojson) {
                try {
                    const line = L.geoJSON(route.route_geojson, {
                        style: {
                            color: DIFFICULTY_COLORS[route.difficulty] || '#7C3AED',
                            weight: 4,
                            opacity: 0.8,
                        }
                    }).addTo(map);
                    routeLines.push(line);
                } catch (e) {
                    console.warn('Invalid GeoJSON for route:', route.slug, e);
                }
            }
        });

        return { markers, routeLines };
    }

    // ============ ADD PLACES TO MAP ============
    function addPlacesToMap(map, places) {
        if (!map) return [];
        const markers = [];
        places.forEach(place => {
            if (!place.lat || !place.lng ||
                isNaN(place.lat) || isNaN(place.lng)) return;

            const marker = L.marker(
                [parseFloat(place.lat), parseFloat(place.lng)],
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
        const el = document.getElementById(containerId);
        if (!el) return null;

        // Prevent double initialization
        if (el._leaflet_id) return null;

        const { points, geojson, title, difficulty } = routeData;

        if (!points || !points.length) {
            console.warn('No points provided for route detail map');
            return null;
        }

        // Filter only valid points
        const validPoints = points.filter(p =>
            p && p.lat != null && p.lng != null &&
            !isNaN(parseFloat(p.lat)) && !isNaN(parseFloat(p.lng))
        );

        if (!validPoints.length) {
            console.warn('No valid coordinates in route points');
            el.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100%;color:#6B7280;font-size:0.9rem;">📍 Координаты маршрута не заданы</div>';
            return null;
        }

        const firstPoint = validPoints[0];
        const center = [parseFloat(firstPoint.lat), parseFloat(firstPoint.lng)];
        const map = initMap(containerId, { center, zoom: 13 });
        if (!map) return null;

        // Add markers for all valid points
        validPoints.forEach((point, i) => {
            const marker = L.marker(
                [parseFloat(point.lat), parseFloat(point.lng)],
                { icon: createWaypointIcon(point.point_type || 'waypoint', i + 1) }
            );
            const name = point.name || `Точка ${i + 1}`;
            marker.bindPopup(`<div class="map-popup"><div class="map-popup-title">${name}</div></div>`);
            marker.addTo(map);
        });

        // Draw polyline between points
        if (validPoints.length >= 2) {
            const coords = validPoints.map(p => [parseFloat(p.lat), parseFloat(p.lng)]);
            const line = L.polyline(coords, {
                color: DIFFICULTY_COLORS[difficulty] || '#7C3AED',
                weight: 5,
                opacity: 0.9,
                dashArray: null,
            }).addTo(map);

            try {
                map.fitBounds(line.getBounds(), { padding: [40, 40] });
            } catch (e) {
                console.warn('fitBounds error:', e);
            }
        }

        return map;
    }

    // ============ PLACE MAP ============
    function initPlaceMap(containerId, lat, lng, name) {
        const el = document.getElementById(containerId);
        if (!el) return null;

        if (el._leaflet_id) return null;

        const parsedLat = parseFloat(lat);
        const parsedLng = parseFloat(lng);

        if (isNaN(parsedLat) || isNaN(parsedLng)) {
            console.warn('Invalid place coordinates:', lat, lng);
            el.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100%;color:#6B7280;font-size:0.9rem;">📍 Координаты места не заданы</div>';
            return null;
        }

        const map = initMap(containerId, { center: [parsedLat, parsedLng], zoom: 14 });
        if (!map) return null;

        L.marker([parsedLat, parsedLng])
            .addTo(map)
            .bindPopup(`<div class="map-popup"><div class="map-popup-title">${name || ''}</div></div>`);

        return map;
    }

    // ============ ADMIN MAP EDITOR ============
    function initAdminMapEditor(containerId, options = {}) {
        const el = document.getElementById(containerId);
        if (!el || el._leaflet_id) return null;

        const { existingPoints = [], onPointsChange } = options;

        const map = initMap(containerId, { zoom: 12 });
        if (!map) return null;

        let points = [...existingPoints];
        let markers = [];
        let polyline = null;

        function renderPoints() {
            markers.forEach(m => map.removeLayer(m));
            markers = [];
            if (polyline) map.removeLayer(polyline);

            points.forEach((point, i) => {
                if (!point || point.lat == null || point.lng == null) return;

                const marker = L.marker([parseFloat(point.lat), parseFloat(point.lng)], {
                    icon: createWaypointIcon(point.type || 'waypoint', i + 1),
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
                        <small style="color: #6B7280;">${parseFloat(point.lat).toFixed(5)}, ${parseFloat(point.lng).toFixed(5)}</small>
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
            const validPts = points.filter(p => p && p.lat != null && p.lng != null);
            if (validPts.length >= 2) {
                polyline = L.polyline(validPts.map(p => [parseFloat(p.lat), parseFloat(p.lng)]), {
                    color: '#7C3AED', weight: 4, opacity: 0.8,
                }).addTo(map);
            }
        }

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

            const pointsJson = document.getElementById('routePointsJson');
            if (pointsJson) pointsJson.value = JSON.stringify(pts);
        }

        renderPoints();

        const validExisting = existingPoints.filter(p => p && p.lat != null && p.lng != null);
        if (validExisting.length >= 2) {
            const coords = validExisting.map(p => [parseFloat(p.lat), parseFloat(p.lng)]);
            try {
                map.fitBounds(L.latLngBounds(coords), { padding: [40, 40] });
            } catch (e) {
                console.warn('fitBounds error:', e);
            }
        }

        return { map, getPoints: () => points };
    }

    // ============ FULL PAGE MAP ============
    function initFullMap(containerId, { routes = [], places = [] }) {
        const el = document.getElementById(containerId);
        if (!el || el._leaflet_id) return null;

        const map = initMap(containerId, { zoom: 10 });
        if (!map) return null;

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
        initPlaceMap,
        initAdminMapEditor,
        initFullMap,
        addRoutesToMap,
        addPlacesToMap,
    };

})();

// ============ AUTO-INITIALIZE ============
document.addEventListener('DOMContentLoaded', () => {

    // Route detail map (only if not already initialized by inline script)
    const routeMapEl = document.getElementById('routeDetailMap');
    if (routeMapEl && !routeMapEl._leaflet_id) {
        const pointsData = routeMapEl.dataset.points;
        const difficulty = routeMapEl.dataset.difficulty;
        if (pointsData) {
            try {
                const points = JSON.parse(pointsData);
                if (points.length > 0) {
                    KGDMap.initRouteDetailMap('routeDetailMap', { points, difficulty });
                }
            } catch (e) {
                console.error('Route map init error:', e);
            }
        }
    }

    // Full map page
    const fullMapEl = document.getElementById('fullPageMap');
    if (fullMapEl && !fullMapEl._leaflet_id) {
        try {
            const routes = JSON.parse(fullMapEl.dataset.routes || '[]');
            const places = JSON.parse(fullMapEl.dataset.places || '[]');
            KGDMap.initFullMap('fullPageMap', { routes, places });
        } catch (e) {
            console.error('Full map init error:', e);
        }
    }

    // Admin editor map
    const adminMapEl = document.getElementById('adminEditorMap');
    if (adminMapEl && !adminMapEl._leaflet_id) {
        try {
            const existingPoints = JSON.parse(adminMapEl.dataset.points || '[]');
            KGDMap.initAdminMapEditor('adminEditorMap', {
                existingPoints,
                onPointsChange: (pts) => {
                    const el = document.getElementById('routePointsJson');
                    if (el) el.value = JSON.stringify(pts);
                }
            });
        } catch (e) {
            console.error('Admin map init error:', e);
        }
    }
});
