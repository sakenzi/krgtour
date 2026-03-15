{% load humanize %}
<article class="card route-card">
    <a href="{{ route.get_absolute_url }}" class="card-image-link">
        <div class="card-image">
            {% if route.cover_image %}
                <img src="{{ route.cover_image.url }}" alt="{{ route.title }}" loading="lazy">
            {% else %}
                <div style="background: linear-gradient(135deg, var(--purple-800), var(--purple-600)); width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; font-size: 3rem;">🏔</div>
            {% endif %}

            <span class="card-badge badge-{{ route.difficulty }}">{{ route.difficulty_label }}</span>

            {% if user.is_authenticated %}
            <button
                class="card-favorite-btn {% if route.id in user_favorites %}active{% endif %}"
                data-favorite-url="{% url 'routes:toggle_favorite' route.slug %}"
                title="{% if route.id in user_favorites %}Убрать из избранного{% else %}Добавить в избранное{% endif %}"
                aria-label="Избранное"
            >
                <span class="fav-icon">{% if route.id in user_favorites %}❤️{% else %}🤍{% endif %}</span>
            </button>
            {% endif %}
        </div>
    </a>

    <div class="card-body">
        {% if route.category %}
        <div style="margin-bottom: 6px;">
            <span class="tag" style="background: {{ route.category.color }}15; color: {{ route.category.color }}; font-size: 0.72rem;">
                {{ route.category.name }}
            </span>
        </div>
        {% endif %}

        <h3 class="card-title">
            <a href="{{ route.get_absolute_url }}" style="color: inherit;">{{ route.title }}</a>
        </h3>

        {% if route.short_description %}
        <p class="card-desc">{{ route.short_description }}</p>
        {% elif route.description %}
        <p class="card-desc">{{ route.description|truncatewords:20 }}</p>
        {% endif %}

        <div class="card-meta">
            <span class="card-meta-item">
                📏 {{ route.distance_km }} км
            </span>
            <span class="card-meta-item">
                ⏱ {{ route.duration_hours }} ч
            </span>
            {% if route.avg_rating > 0 %}
            <span class="card-meta-item card-rating">
                ⭐ {{ route.avg_rating }}
                <span style="color: var(--text-muted);">({{ route.review_count }})</span>
            </span>
            {% endif %}
        </div>
    </div>

    <div class="card-footer">
        <div>
            <div class="card-price {% if not route.price %}card-price-free{% endif %}">
                {{ route.price_display }}
            </div>
            {% if route.price %}
            <div style="font-size: 0.72rem; color: var(--text-muted);">за человека</div>
            {% endif %}
        </div>
        <a href="{{ route.get_absolute_url }}" class="btn btn-primary btn-sm">
            Подробнее →
        </a>
    </div>
</article>
