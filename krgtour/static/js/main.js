/**
 * КарагандаТур — Main JavaScript
 * Pure vanilla JS, AJAX, UI interactions
 */

// ============ CSRF TOKEN ============
function getCsrfToken() {
    return document.cookie.split('; ')
        .find(row => row.startsWith('csrftoken='))
        ?.split('=')[1] || '';
}

// Fetch with CSRF
async function fetchJSON(url, options = {}) {
    const defaults = {
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken(),
            'X-Requested-With': 'XMLHttpRequest',
        },
        credentials: 'same-origin',
    };
    const response = await fetch(url, { ...defaults, ...options, headers: { ...defaults.headers, ...(options.headers || {}) } });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
}

// ============ NAVBAR ============
(function initNavbar() {
    const navbar = document.getElementById('navbar');
    const navToggle = document.getElementById('navToggle');
    const navLinks = document.getElementById('navLinks');
    const userMenuBtn = document.getElementById('userMenuBtn');
    const userDropdown = document.getElementById('userDropdown');

    // Scroll effect
    window.addEventListener('scroll', () => {
        navbar?.classList.toggle('scrolled', window.scrollY > 20);
    }, { passive: true });

    // Mobile toggle
    navToggle?.addEventListener('click', () => {
        navLinks?.classList.toggle('open');
        const spans = navToggle.querySelectorAll('span');
        spans[0].style.transform = navLinks.classList.contains('open') ? 'rotate(45deg) translate(5px, 5px)' : '';
        spans[1].style.opacity = navLinks.classList.contains('open') ? '0' : '1';
        spans[2].style.transform = navLinks.classList.contains('open') ? 'rotate(-45deg) translate(5px, -5px)' : '';
    });

    // User dropdown
    userMenuBtn?.addEventListener('click', (e) => {
        e.stopPropagation();
        userDropdown?.classList.toggle('show');
    });

    document.addEventListener('click', () => {
        userDropdown?.classList.remove('show');
    });
})();

// ============ MESSAGES AUTO-DISMISS ============
(function initMessages() {
    document.querySelectorAll('[data-auto-dismiss]').forEach(msg => {
        setTimeout(() => {
            msg.style.transition = 'opacity 0.4s, transform 0.4s';
            msg.style.opacity = '0';
            msg.style.transform = 'translateX(20px)';
            setTimeout(() => msg.remove(), 400);
        }, 4000);
    });
})();

// ============ FAVORITE BUTTON ============
function initFavoriteButtons() {
    document.querySelectorAll('[data-favorite-url]').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            e.preventDefault();
            e.stopPropagation();

            if (!document.querySelector('meta[name="user-authenticated"]')) {
                window.location.href = '/users/login/?next=' + window.location.pathname;
                return;
            }

            const url = btn.dataset.favoriteUrl;
            const icon = btn.querySelector('.fav-icon');

            try {
                btn.disabled = true;
                const data = await fetchJSON(url, { method: 'POST' });
                if (data.success) {
                    btn.classList.toggle('active', data.is_favorite);
                    if (icon) icon.textContent = data.is_favorite ? '❤️' : '🤍';
                    showToast(data.is_favorite ? 'Добавлено в избранное' : 'Удалено из избранного', 'success');
                }
            } catch (err) {
                showToast('Ошибка. Попробуйте снова.', 'error');
            } finally {
                btn.disabled = false;
            }
        });
    });
}

// ============ STAR RATING ============
function initStarRating() {
    document.querySelectorAll('.star-rating').forEach(container => {
        const labels = container.querySelectorAll('label');
        const inputs = container.querySelectorAll('input[type="radio"]');

        labels.forEach((label, i) => {
            label.addEventListener('mouseenter', () => {
                labels.forEach((l, j) => {
                    l.style.color = j <= i ? 'var(--accent)' : 'var(--border)';
                });
            });
            label.addEventListener('mouseleave', () => {
                const checked = container.querySelector('input:checked');
                const checkedIdx = checked ? parseInt(checked.value) - 1 : -1;
                labels.forEach((l, j) => {
                    l.style.color = j <= checkedIdx ? 'var(--accent)' : 'var(--border)';
                });
            });
        });
    });
}

// ============ REVIEW FORM AJAX ============
function initReviewForm() {
    const form = document.getElementById('reviewForm');
    if (!form) return;

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const submitBtn = form.querySelector('[type="submit"]');
        const originalText = submitBtn.textContent;
        submitBtn.textContent = 'Отправка...';
        submitBtn.disabled = true;

        try {
            const formData = new FormData(form);
            const response = await fetch(form.action, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCsrfToken(),
                    'X-Requested-With': 'XMLHttpRequest',
                },
                body: formData,
            });
            const data = await response.json();

            if (data.success) {
                showToast('Ваш отзыв отправлен!', 'success');
                form.closest('.review-form-section')?.remove();
                prependReview(data.review);
            } else {
                showFormErrors(form, data.errors);
                showToast('Проверьте заполнение формы.', 'error');
            }
        } catch (err) {
            showToast('Ошибка отправки. Попробуйте снова.', 'error');
        } finally {
            submitBtn.textContent = originalText;
            submitBtn.disabled = false;
        }
    });
}

function prependReview(review) {
    const container = document.getElementById('reviewsList');
    if (!container) return;

    const stars = '★'.repeat(review.rating) + '☆'.repeat(5 - review.rating);
    const html = `
        <div class="review-card" style="animation: msgFade 0.4s ease;">
            <div class="review-header">
                <img src="${review.avatar}" alt="${review.user}" class="review-avatar">
                <div class="review-meta">
                    <div class="review-user">${review.user}</div>
                    <div class="review-date">${review.created_at}</div>
                </div>
                <div class="review-stars">${stars}</div>
            </div>
            <p class="review-text">${review.comment}</p>
        </div>
    `;
    container.insertAdjacentHTML('afterbegin', html);
}

// ============ BOOKING PRICE CALCULATOR ============
function initBookingCalculator() {
    const numPeopleInput = document.getElementById('id_num_people');
    const priceDisplay = document.getElementById('bookingTotalPrice');
    const routeId = document.getElementById('routeId')?.value;

    if (!numPeopleInput || !priceDisplay || !routeId) return;

    let debounceTimer;
    numPeopleInput.addEventListener('input', () => {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(async () => {
            const n = parseInt(numPeopleInput.value) || 1;
            try {
                const data = await fetchJSON(`/bookings/api/price/?route_id=${routeId}&num_people=${n}`);
                if (data.total > 0) {
                    priceDisplay.textContent = `${data.total.toLocaleString('ru-RU')} ${data.currency}`;
                } else {
                    priceDisplay.textContent = 'Бесплатно';
                }
            } catch (e) {}
        }, 400);
    });
}

// ============ GALLERY LIGHTBOX ============
function initGallery() {
    const items = document.querySelectorAll('.gallery-item[data-src]');
    if (!items.length) return;

    let lightbox = document.getElementById('galleryLightbox');
    if (!lightbox) {
        lightbox = document.createElement('div');
        lightbox.id = 'galleryLightbox';
        lightbox.className = 'lightbox';
        lightbox.innerHTML = `
            <button class="lightbox-close" id="lightboxClose">×</button>
            <img id="lightboxImg" src="" alt="">
        `;
        document.body.appendChild(lightbox);
    }

    const lightboxImg = lightbox.querySelector('#lightboxImg');

    items.forEach(item => {
        item.addEventListener('click', () => {
            lightboxImg.src = item.dataset.src;
            lightbox.classList.add('active');
            document.body.style.overflow = 'hidden';
        });
    });

    lightbox.addEventListener('click', (e) => {
        if (e.target === lightbox || e.target.id === 'lightboxClose') {
            lightbox.classList.remove('active');
            document.body.style.overflow = '';
        }
    });
}

// ============ TOAST NOTIFICATIONS ============
function showToast(message, type = 'info') {
    const container = document.getElementById('messagesContainer') || (() => {
        const c = document.createElement('div');
        c.id = 'messagesContainer';
        c.className = 'messages-container';
        document.body.appendChild(c);
        return c;
    })();

    const icons = { success: '✅', error: '❌', warning: '⚠️', info: 'ℹ️' };
    const toast = document.createElement('div');
    toast.className = `message message-${type}`;
    toast.innerHTML = `
        <span class="message-icon">${icons[type] || 'ℹ️'}</span>
        ${message}
        <button class="message-close" onclick="this.parentElement.remove()">×</button>
    `;

    container.appendChild(toast);
    setTimeout(() => {
        toast.style.transition = 'opacity 0.4s, transform 0.4s';
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(20px)';
        setTimeout(() => toast.remove(), 400);
    }, 4000);
}

// ============ FORM ERRORS ============
function showFormErrors(form, errors) {
    // Clear previous
    form.querySelectorAll('.form-error').forEach(e => e.remove());

    Object.entries(errors).forEach(([field, errs]) => {
        const input = form.querySelector(`[name="${field}"]`);
        if (input) {
            const errorEl = document.createElement('div');
            errorEl.className = 'form-error';
            errorEl.textContent = errs.join(', ');
            input.parentNode.appendChild(errorEl);
        }
    });
}

// ============ SEARCH INPUT ============
function initSearchInput() {
    const searchInput = document.querySelector('.hero-search-input');
    if (!searchInput) return;

    searchInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            const query = searchInput.value.trim();
            if (query) {
                window.location.href = `/routes/?q=${encodeURIComponent(query)}`;
            }
        }
    });
}

// ============ LAZY IMAGES ============
function initLazyImages() {
    if ('IntersectionObserver' in window) {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    if (img.dataset.src) {
                        img.src = img.dataset.src;
                        img.removeAttribute('data-src');
                    }
                    observer.unobserve(img);
                }
            });
        }, { rootMargin: '200px' });

        document.querySelectorAll('img[data-src]').forEach(img => observer.observe(img));
    }
}

// ============ FILTERS AUTO-SUBMIT ============
function initFilters() {
    document.querySelectorAll('.filter-auto-submit').forEach(el => {
        el.addEventListener('change', () => {
            el.closest('form')?.submit();
        });
    });
}

// ============ ROUTE SORT ============
function initSortSelect() {
    const sortSelect = document.getElementById('sortSelect');
    if (!sortSelect) return;
    sortSelect.addEventListener('change', () => {
        const url = new URL(window.location.href);
        url.searchParams.set('sort', sortSelect.value);
        url.searchParams.delete('page');
        window.location.href = url.toString();
    });
}

// ============ INIT ALL ============
document.addEventListener('DOMContentLoaded', () => {
    initFavoriteButtons();
    initStarRating();
    initReviewForm();
    initBookingCalculator();
    initGallery();
    initSearchInput();
    initLazyImages();
    initFilters();
    initSortSelect();
});