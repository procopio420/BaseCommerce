/**
 * BaseCommerce - App JavaScript
 * Minimal JS for micro-interactions (toast, drawer, helpers)
 * Note: Tenant theming is now handled server-side via template context
 */

(function() {
    'use strict';

    // =============================================================================
    // Toast Notifications
    // =============================================================================

    /**
     * Show toast notification
     * @param {string} message - Message to display
     * @param {string} type - Type: 'success', 'error', 'warning', 'info'
     * @param {number} duration - Duration in ms (default: 5000)
     */
    function showToast(message, type = 'info', duration = 5000) {
        const container = document.getElementById('flash-container') || createToastContainer();
        
        const toast = document.createElement('div');
        toast.className = `flash flash-${type}`;
        toast.innerHTML = `
            ${message}
            <button onclick="this.parentElement.remove()" class="flash-close">&times;</button>
        `;
        
        container.appendChild(toast);
        
        // Auto remove after duration
        if (duration > 0) {
            setTimeout(() => {
                if (toast.parentElement) {
                    toast.remove();
                }
            }, duration);
        }
        
        return toast;
    }

    function createToastContainer() {
        const container = document.createElement('div');
        container.id = 'flash-container';
        container.className = 'flash-container';
        document.body.appendChild(container);
        return container;
    }

    // =============================================================================
    // Sidebar Toggle (Mobile)
    // =============================================================================

    function toggleSidebar() {
        const sidebar = document.getElementById('sidebar');
        if (sidebar) {
            sidebar.classList.toggle('hidden');
            sidebar.classList.toggle('md:block');
        }
    }

    // =============================================================================
    // Helpers
    // =============================================================================

    /**
     * Format currency value
     */
    function formatCurrency(value) {
        return new Intl.NumberFormat('pt-BR', {
            style: 'currency',
            currency: 'BRL'
        }).format(value);
    }

    /**
     * Format date
     */
    function formatDate(date, format = 'short') {
        const d = new Date(date);
        const options = format === 'short' 
            ? { day: '2-digit', month: '2-digit', year: 'numeric' }
            : { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' };
        return new Intl.DateTimeFormat('pt-BR', options).format(d);
    }

    // =============================================================================
    // HTMX Event Handlers
    // =============================================================================

    // Show toast on HTMX response with flash message
    document.body.addEventListener('htmx:afterSwap', function(event) {
        // Check if response has flash message
        const flashEl = event.detail.target.querySelector('.flash');
        if (flashEl) {
            const message = flashEl.textContent.trim();
            const type = flashEl.className.includes('flash-success') ? 'success' :
                        flashEl.className.includes('flash-error') ? 'error' :
                        flashEl.className.includes('flash-warning') ? 'warning' : 'info';
            showToast(message, type);
        }
    });

    // Handle HTMX errors
    document.body.addEventListener('htmx:responseError', function(event) {
        showToast('Erro ao processar requisição. Tente novamente.', 'error');
    });

    // =============================================================================
    // Drawer Management
    // =============================================================================

    function openDrawer(drawerId) {
        const drawer = document.getElementById(drawerId);
        const overlay = document.getElementById('pedido-drawer-overlay');
        
        if (drawer && overlay) {
            drawer.classList.add('open');
            overlay.classList.add('show');
            
            // Prevent body scroll
            document.body.style.overflow = 'hidden';
        }
    }

    function closeDrawer(drawerId) {
        const drawer = document.getElementById(drawerId);
        const overlay = document.getElementById('pedido-drawer-overlay');
        
        if (drawer && overlay) {
            drawer.classList.remove('open');
            overlay.classList.remove('show');
            
            // Restore body scroll
            document.body.style.overflow = '';
        }
    }

    function setupDrawer() {
        // Close drawer when clicking overlay
        const overlay = document.getElementById('pedido-drawer-overlay');
        if (overlay) {
            overlay.addEventListener('click', (e) => {
                if (e.target === overlay) {
                    closeDrawer('pedido-details-drawer');
                }
            });
        }
        
        // Close drawer on Escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                const drawer = document.getElementById('pedido-details-drawer');
                if (drawer && drawer.classList.contains('open')) {
                    closeDrawer('pedido-details-drawer');
                }
            }
        });
        
        // HTMX: Open drawer after loading content
        document.body.addEventListener('htmx:afterSwap', (event) => {
            if (event.detail.target.id === 'pedido-details-content') {
                openDrawer('pedido-details-drawer');
            }
        });
    }

    // =============================================================================
    // Initialization
    // =============================================================================

    // Setup drawer on page load
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            setupDrawer();
        });
    } else {
        setupDrawer();
    }

    // Expose functions globally
    window.BaseCommerce = {
        showToast,
        toggleSidebar,
        formatCurrency,
        formatDate,
        openDrawer,
        closeDrawer
    };

})();


