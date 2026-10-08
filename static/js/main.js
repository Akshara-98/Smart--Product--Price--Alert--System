document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('addAlertForm');
    const submitBtn = document.getElementById('submitBtn');
    const btnText = submitBtn.querySelector('span');
    const btnIcon = submitBtn.querySelector('i');
    const alertsGrid = document.getElementById('alertsGrid');
    const refreshBtn = document.getElementById('refreshBtn');
    const toast = document.getElementById('toast');
    const toastIcon = toast.querySelector('i');
    const toastMessage = document.getElementById('toastMessage');

    // Initial load
    fetchAlerts();

    // Supported domains for client-side validation
    const SUPPORTED_DOMAINS = [
        'amazon.in', 'amazon.com', 'amazon.co.uk', 'amazon.de', 'amazon.fr', 'amazon.it', 'amazon.es',
        'amzn.to', 'amzn.eu',
        'flipkart.com', 'shopsy.in',
        'myntra.com',
        'meesho.com',
        'ajio.com',
        'nykaa.com',
        'snapdeal.com',
        'tatacliq.com',
        'reliancedigital.in',
        'croma.com',
    ];

    function isSupportedUrl(url) {
        try {
            const hostname = new URL(url).hostname.replace('www.', '').toLowerCase();
            // Check broad amazon match
            if (hostname.includes('amazon') || hostname === 'amzn.to' || hostname === 'amzn.eu') {
                return true;
            }
            return SUPPORTED_DOMAINS.some(d => hostname === d || hostname.endsWith('.' + d));
        } catch { return false; }
    }

    // Show platform hint under URL input
    const urlInput = document.getElementById('url');
    const urlHint = document.createElement('p');
    urlHint.className = 'url-hint';
    urlHint.innerHTML = '✅ Supported: Amazon, Flipkart, Myntra, Meesho, AJIO, Nykaa, Snapdeal, Tata CLiQ';
    urlInput && urlInput.parentNode.appendChild(urlHint);

    if (urlInput) {
        urlInput.addEventListener('input', () => {
            const val = urlInput.value.trim();
            if (!val) {
                urlHint.className = 'url-hint';
                urlHint.textContent = '✅ Supported: Amazon, Flipkart, Myntra, Meesho, AJIO, Nykaa, Snapdeal, Tata CLiQ';
            } else if (isSupportedUrl(val)) {
                urlHint.className = 'url-hint valid';
                urlHint.textContent = '✅ Supported site detected!';
            } else {
                urlHint.className = 'url-hint invalid';
                urlHint.textContent = '❌ Unsupported site. Please use Amazon, Flipkart, Myntra, Meesho, etc.';
            }
        });
    }

    // Setup event listeners
    form.addEventListener('submit', handleAddAlert);
    refreshBtn.addEventListener('click', fetchAlerts);

    async function handleAddAlert(e) {
        e.preventDefault();

        // Get form data
        const formData = new FormData(form);
        const url = formData.get('url').trim();
        const target_price = formData.get('target_price');
        const payload = { url, target_price };

        // Client-side validation
        if (!isSupportedUrl(url)) {
            showToast('❌ Unsupported site. Use Amazon, Flipkart, Myntra, Meesho, AJIO, etc.', 'error');
            return;
        }

        // UI Loading State
        setLoadingState(true);

        try {
            const response = await fetch('/api/alerts', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            const data = await response.json();

            if (response.ok) {
                showToast(data.message, 'success');
                form.reset();
                urlHint.className = 'url-hint';
                urlHint.textContent = '✅ Supported: Amazon, Flipkart, Myntra, Meesho, AJIO, Nykaa, Snapdeal, Tata CLiQ';
                fetchAlerts();
            } else {
                showToast(data.message || 'Failed to add alert', 'error');
            }
        } catch (error) {
            console.error('Error adding alert:', error);
            showToast('Network error occurred.', 'error');
        } finally {
            setLoadingState(false);
        }
    }

    async function fetchAlerts() {
        alertsGrid.innerHTML = `
            <div class="loading-state">
                <div class="spinner"></div>
                <p>Loading your alerts...</p>
            </div>
        `;

        try {
            const response = await fetch('/api/alerts');
            if (response.status === 401) {
                window.location.href = '/login';
                return;
            }
            const alerts = await response.json();

            if (alerts.length === 0) {
                alertsGrid.innerHTML = `
                    <div class="empty-state">
                        <i class="fa-regular fa-bell-slash"></i>
                        <h3>No Active Alerts</h3>
                        <p>Add a product URL above to start tracking prices.</p>
                    </div>
                `;
                return;
            }

            // Render alerts
            alertsGrid.innerHTML = alerts.map(alert => createAlertCard(alert)).join('');

            // Attach delete listeners to new cards
            document.querySelectorAll('.btn-delete').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const id = e.currentTarget.dataset.id;
                    deleteAlert(id);
                });
            });

        } catch (error) {
            console.error('Error fetching alerts:', error);
            alertsGrid.innerHTML = `
                <div class="empty-state">
                    <i class="fa-solid fa-triangle-exclamation" style="color: var(--danger)"></i>
                    <h3>Error Loading Alerts</h3>
                    <p>Could not connect to the server. Please try refreshing.</p>
                </div>
            `;
        }
    }

    async function deleteAlert(id) {
        if (!confirm('Are you sure you want to stop tracking this product?')) {
            return;
        }

        try {
            const response = await fetch(`/api/alerts/${id}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                showToast('Alert removed successfully', 'success');
                fetchAlerts(); // Refresh list
            } else {
                showToast('Failed to delete alert', 'error');
            }
        } catch (error) {
            console.error('Error deleting alert:', error);
            showToast('Network error occurred.', 'error');
        }
    }

    function createAlertCard(alert) {
        const statusClass = alert.is_notified ? 'status-notified' : 'status-tracking';
        const statusIcon = alert.is_notified ? '<i class="fa-solid fa-check"></i>' : '<div class="pulse-dot"></div>';
        const statusText = alert.is_notified ? 'Target Reached' : 'Tracking';
        
        // Show price in INR (₹) since all supported sites are Indian
        const currentPriceFormat = alert.current_price !== null
            ? `₹${alert.current_price.toLocaleString('en-IN')}`
            : 'Checking...';
        const targetPriceFormat = `₹${alert.target_price.toLocaleString('en-IN')}`;

        return `
            <div class="alert-card ${statusClass}">
                <div class="card-header">
                    <a href="${alert.product_url}" target="_blank" class="product-title" title="${alert.product_name}">
                        ${alert.product_name}
                    </a>
                    <button class="btn-delete" data-id="${alert.id}" title="Remove Alert">
                        <i class="fa-solid fa-trash-can"></i>
                    </button>
                </div>

                <div class="price-container">
                    <div class="price-box current-price">
                        <span class="price-label">Current</span>
                        <span class="price-value">${currentPriceFormat}</span>
                    </div>
                    
                    <div class="price-arrow">
                        <i class="fa-solid fa-arrow-right-long"></i>
                    </div>

                    <div class="price-box target-price">
                        <span class="price-label">Target</span>
                        <span class="price-value">${targetPriceFormat}</span>
                    </div>
                </div>

                <div class="card-footer">
                    <div class="status-badge">
                        ${statusIcon}
                        <span>${statusText}</span>
                    </div>
                    <div class="date-text">
                        <i class="fa-regular fa-clock"></i>
                        <span>${new Date(alert.created_at).toLocaleDateString()}</span>
                    </div>
                </div>
            </div>
        `;
    }

    // Utilities
    function setLoadingState(isLoading) {
        submitBtn.disabled = isLoading;
        if (isLoading) {
            btnText.textContent = 'Processing...';
            btnIcon.className = 'fa-solid fa-circle-notch spinner-icon';
        } else {
            btnText.textContent = 'Start Tracking';
            btnIcon.className = 'fa-solid fa-paper-plane';
        }
    }

    function showToast(message, type = 'success') {
        toastMessage.textContent = message;
        
        // Setup icon and classes
        toast.className = `toast ${type}`;
        if (type === 'success') {
            toastIcon.className = 'fa-solid fa-circle-check toast-icon';
        } else {
            toastIcon.className = 'fa-solid fa-circle-exclamation toast-icon';
        }

        // Show
        setTimeout(() => toast.classList.remove('hidden'), 10);
        
        // Hide after 4 seconds
        setTimeout(() => {
            toast.classList.add('hidden');
        }, 4000);
    }
});
