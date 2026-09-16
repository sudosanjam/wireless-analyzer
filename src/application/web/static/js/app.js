/**
 * Main Frontend Application Controller.
 * Handles WebSocket telemetry stream, DOM rendering, sorting, filtering, and tab navigation.
 */

document.addEventListener('DOMContentLoaded', () => {
    // Initialize Radar
    const radar = new TacticalRadar('radar-canvas', 'radar-tooltip');

    // State Store
    let contacts = [];
    let analytics = null;
    let events = [];
    let sessionMeta = null;
    let sortColumn = 'latest_rssi';
    let sortDirection = 'desc';
    let currentFilterType = 'ALL';
    let currentFilterState = 'ALL';
    let currentSearchTerm = '';
    let ws = null;
    let sessionStartTime = null;

    // UI Elements
    const contactsTbody = document.getElementById('contacts-tbody');
    const searchInput = document.getElementById('contact-search');
    const filterTypeSelect = document.getElementById('filter-type');
    const filterStateSelect = document.getElementById('filter-state');
    const audioToggleBtn = document.getElementById('audio-toggle-btn');
    const audioIcon = document.getElementById('audio-icon');
    const radarSweepToggle = document.getElementById('radar-sweep-toggle');
    const contactModal = document.getElementById('contact-modal');
    const modalCloseBtn = document.getElementById('modal-close-btn');
    const modalContent = document.getElementById('modal-content');

    // Ticker Elements
    const statSessionId = document.getElementById('stat-session-id');
    const statRuntime = document.getElementById('stat-runtime');
    const statTotalContacts = document.getElementById('stat-total-contacts');
    const statActiveContacts = document.getElementById('stat-active-contacts');
    const statWifiBleRatio = document.getElementById('stat-wifi-ble-ratio');
    const statWatchlistAlerts = document.getElementById('stat-watchlist-alerts');
    const backendStatusBadge = document.getElementById('backend-status-badge');
    const tabContactCount = document.getElementById('tab-contact-count');
    const tabEventCount = document.getElementById('tab-event-count');

    // ----------------- WebSocket Connection -----------------
    function connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;
        
        ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            console.log('[WS] Connected to live observation telemetry stream');
            document.getElementById('system-status-indicator').classList.add('active');
        };

        ws.onmessage = (event) => {
            try {
                const msg = JSON.parse(event.data);
                handleStreamMessage(msg);
            } catch (e) {
                console.error('[WS] Parse error', e);
            }
        };

        ws.onclose = () => {
            console.log('[WS] Connection closed, retrying in 2s...');
            document.getElementById('system-status-indicator').classList.remove('active');
            setTimeout(connectWebSocket, 2000);
        };

        ws.onerror = (err) => {
            console.error('[WS] Error', err);
            ws.close();
        };
    }

    function handleStreamMessage(msg) {
        if (msg.type === 'FULL_STATE' || msg.type === 'SYNC') {
            contacts = msg.contacts || [];
            analytics = msg.analytics || null;
            sessionMeta = msg.session || null;
            if (sessionMeta && sessionMeta.start_time) {
                sessionStartTime = sessionMeta.start_time;
            }
            radar.setContacts(contacts);
            renderTable();
            renderAnalytics();
            renderSessionStats();
        } else if (msg.type === 'STATE_DELTA') {
            contacts = msg.contacts || [];
            analytics = msg.analytics || null;
            radar.setContacts(contacts);
            renderTable();
            renderAnalytics();
            renderSessionStats();
        } else if (msg.type === 'NEW_EVENT') {
            const ev = msg.event;
            events.unshift(ev);
            if (events.length > 200) events.pop();
            renderEvents();

            if (ev.event_type === 'WATCHLIST_MATCH') {
                window.tacticalAudio.playAlertTone();
            } else if (ev.event_type === 'NEW_CONTACT') {
                window.tacticalAudio.playChirp();
            }
        }
    }

    // ----------------- Table Rendering -----------------
    function renderTable() {
        tabContactCount.innerText = contacts.length;

        const filtered = contacts.filter(c => {
            if (currentFilterType !== 'ALL' && c.signal_type !== currentFilterType) return false;
            if (currentFilterState !== 'ALL' && c.state !== currentFilterState) return false;
            if (currentSearchTerm) {
                const term = currentSearchTerm.toLowerCase();
                const ssid = (c.ssid || '').toLowerCase();
                const name = (c.device_name || '').toLowerCase();
                const mac = (c.mac_address || '').toLowerCase();
                const mfg = (c.manufacturer || '').toLowerCase();
                const cat = (c.device_category || '').toLowerCase();
                if (!ssid.includes(term) && !name.includes(term) && !mac.includes(term) && !mfg.includes(term) && !cat.includes(term)) {
                    return false;
                }
            }
            return true;
        });

        // Sort
        filtered.sort((a, b) => {
            let valA = a[sortColumn];
            let valB = b[sortColumn];

            if (sortColumn === 'label') {
                valA = (a.ssid || a.device_name || '').toLowerCase();
                valB = (b.ssid || b.device_name || '').toLowerCase();
            }

            if (valA === undefined || valA === null) valA = '';
            if (valB === undefined || valB === null) valB = '';

            if (typeof valA === 'number') {
                return sortDirection === 'asc' ? valA - valB : valB - valA;
            }
            return sortDirection === 'asc' ? String(valA).localeCompare(String(valB)) : String(valB).localeCompare(String(valA));
        });

        if (filtered.length === 0) {
            contactsTbody.innerHTML = `
                <tr class="empty-row">
                    <td colspan="10">No contacts matching the current filter criteria.</td>
                </tr>
            `;
            return;
        }

        contactsTbody.innerHTML = filtered.map(c => {
            const label = escapeHtml(c.ssid || c.device_name || '*(Hidden/Unadvertised)*');
            const stateClass = `badge-${c.state.toLowerCase()}`;
            const typeClass = `badge-${c.signal_type}`;
            const isWatchlist = c.watchlist_matched;

            const rssiPct = Math.max(0, Math.min(100, Math.round(((c.latest_rssi + 95) / 65) * 100)));
            const rssiMeterClass = c.latest_rssi >= -55 ? 'rssi-strong' : (c.latest_rssi >= -75 ? 'rssi-medium' : 'rssi-weak');

            return `
                <tr data-id="${c.normalized_identifier}">
                    <td>
                        <span class="badge ${stateClass}">${c.state}</span>
                        ${isWatchlist ? '<span class="badge badge-alert">WATCHLIST</span>' : ''}
                    </td>
                    <td><span class="badge ${typeClass}">${c.signal_type.toUpperCase()}</span></td>
                    <td style="font-weight: 600; color: #f1f5f9;">${label}</td>
                    <td style="font-family: monospace; color: #94a3b8;">${c.mac_address}</td>
                    <td>
                        <div class="rssi-cell">
                            <div class="rssi-meter">
                                <div class="rssi-fill ${rssiMeterClass}" style="width: ${rssiPct}%"></div>
                            </div>
                            <span>${c.latest_rssi} dBm</span>
                        </div>
                    </td>
                    <td>${c.channel !== null ? `Ch ${c.channel}` : '-'}</td>
                    <td>${escapeHtml(c.manufacturer || 'Unknown')}</td>
                    <td><span class="badge" style="background: rgba(255,255,255,0.06);">${escapeHtml(c.device_category || 'UNKNOWN')}</span></td>
                    <td>${c.observation_count}</td>
                    <td style="color: #64748b; font-size: 10px;">${formatTimestamp(c.last_seen)}</td>
                </tr>
            `;
        }).join('');

        // Row Click listener
        contactsTbody.querySelectorAll('tr[data-id]').forEach(row => {
            row.addEventListener('click', () => {
                const id = row.getAttribute('data-id');
                const target = contacts.find(x => x.normalized_identifier === id);
                if (target) showContactDetails(target);
            });
        });
    }

    // ----------------- Analytics Rendering -----------------
    function renderAnalytics() {
        if (!analytics) return;

        // RSSI Bars
        const rssiBars = document.getElementById('rssi-bars');
        const dist = analytics.rssi_stats ? analytics.rssi_stats.distribution : {};
        const total = analytics.total_contacts || 1;

        rssiBars.innerHTML = ['STRONG', 'MEDIUM', 'WEAK'].map(cat => {
            const count = dist[cat] || 0;
            const pct = Math.round((count / total) * 100);
            const color = cat === 'STRONG' ? 'var(--neon-green)' : (cat === 'MEDIUM' ? 'var(--neon-amber)' : 'var(--neon-red)');
            return `
                <div class="stat-bar-item">
                    <div class="stat-bar-label">
                        <span>${cat} (${cat === 'STRONG' ? '>= -55' : (cat === 'MEDIUM' ? '-55 to -75' : '< -75')} dBm)</span>
                        <span>${count} (${pct}%)</span>
                    </div>
                    <div class="stat-bar-track">
                        <div class="stat-bar-value" style="width: ${pct}%; background-color: ${color};"></div>
                    </div>
                </div>
            `;
        }).join('');

        // Channel Density Chart
        const channelChart = document.getElementById('channel-density-chart');
        const chanDist = analytics.channel_distribution || {};
        const maxChanCount = Math.max(...Object.values(chanDist), 1);

        channelChart.innerHTML = Object.entries(chanDist).map(([chan, count]) => {
            const heightPct = Math.max(8, Math.round((count / maxChanCount) * 100));
            return `
                <div class="channel-col" title="Channel ${chan}: ${count} observations">
                    <div class="channel-col-bar" style="height: ${heightPct}%;"></div>
                    <span class="channel-col-num">${chan}</span>
                </div>
            `;
        }).join('');

        // Vendor Bars
        const vendorBars = document.getElementById('vendor-bars');
        const mfgDist = analytics.manufacturer_distribution || {};
        vendorBars.innerHTML = Object.entries(mfgDist).slice(0, 6).map(([mfg, count]) => {
            const pct = Math.round((count / total) * 100);
            return `
                <div class="stat-bar-item">
                    <div class="stat-bar-label">
                        <span>${escapeHtml(mfg)}</span>
                        <span>${count}</span>
                    </div>
                    <div class="stat-bar-track">
                        <div class="stat-bar-value" style="width: ${pct}%;"></div>
                    </div>
                </div>
            `;
        }).join('');

        // Category Bars
        const categoryBars = document.getElementById('category-bars');
        const catDist = analytics.category_distribution || {};
        categoryBars.innerHTML = Object.entries(catDist).slice(0, 6).map(([cat, count]) => {
            const pct = Math.round((count / total) * 100);
            return `
                <div class="stat-bar-item">
                    <div class="stat-bar-label">
                        <span>${escapeHtml(cat)}</span>
                        <span>${count}</span>
                    </div>
                    <div class="stat-bar-track">
                        <div class="stat-bar-value" style="width: ${pct}%; background-color: var(--neon-purple);"></div>
                    </div>
                </div>
            `;
        }).join('');
    }

    // ----------------- Events Feed -----------------
    function renderEvents() {
        tabEventCount.innerText = events.length;
        const list = document.getElementById('events-log-list');
        if (events.length === 0) return;

        list.innerHTML = events.slice(0, 50).map(ev => {
            const sev = ev.severity || 'INFO';
            return `
                <div class="event-item ${sev}">
                    <span class="event-time">${formatTimestamp(ev.timestamp)}</span>
                    <span class="badge badge-${sev.toLowerCase()}">${sev}</span>
                    <span class="event-msg">${escapeHtml(ev.message)}</span>
                </div>
            `;
        }).join('');
    }

    // ----------------- Session Stats -----------------
    function renderSessionStats() {
        if (!sessionMeta) return;
        statSessionId.innerText = sessionMeta.session_id ? sessionMeta.session_id.substring(0, 8) + '…' : 'ACTIVE';
        statTotalContacts.innerText = contacts.length;
        
        const activeCount = contacts.filter(c => c.state === 'ACTIVE' || c.state === 'NEW').length;
        const newCount = contacts.filter(c => c.state === 'NEW').length;
        statActiveContacts.innerText = `${activeCount} / ${newCount}`;

        const wifiCount = contacts.filter(c => c.signal_type === 'wifi').length;
        const bleCount = contacts.filter(c => c.signal_type === 'ble').length;
        statWifiBleRatio.innerText = `${wifiCount} / ${bleCount}`;

        const alertsCount = contacts.filter(c => c.watchlist_matched).length;
        statWatchlistAlerts.innerText = alertsCount;

        if (sessionMeta.scanner_backend) {
            backendStatusBadge.innerText = `BACKEND: ${sessionMeta.scanner_backend.toUpperCase()} | IFACE: ${sessionMeta.interface}`;
        }
    }

    // ----------------- Runtime Timer -----------------
    setInterval(() => {
        if (sessionStartTime) {
            const elapsed = Math.max(0, Math.floor((Date.now() / 1000) - sessionStartTime));
            const hrs = String(Math.floor(elapsed / 3600)).padStart(2, '0');
            const mins = String(Math.floor((elapsed % 3600) / 60)).padStart(2, '0');
            const secs = String(elapsed % 60).padStart(2, '0');
            statRuntime.innerText = `${hrs}:${mins}:${secs}`;
        }
    }, 1000);

    // ----------------- Detail Modal -----------------
    window.showContactDetails = function(contact) {
        modalContent.innerHTML = `
            <div class="detail-grid">
                <span class="detail-label">IDENTIFIER / MAC</span>
                <span class="detail-val" style="color: var(--neon-cyan);">${contact.mac_address}</span>

                <span class="detail-label">SSID / NAME</span>
                <span class="detail-val" style="font-weight: bold;">${escapeHtml(contact.ssid || contact.device_name || '*(Hidden/Unadvertised)*')}</span>

                <span class="detail-label">STATE / TYPE</span>
                <span class="detail-val">${contact.state} / ${contact.signal_type.toUpperCase()}</span>

                <span class="detail-label">SIGNAL (RSSI)</span>
                <span class="detail-val">${contact.latest_rssi} dBm (Smoothed: ${contact.smoothed_rssi} dBm) [Min: ${contact.min_rssi} / Max: ${contact.max_rssi}]</span>

                <span class="detail-label">SPECTRUM / BAND</span>
                <span class="detail-val">${contact.channel ? `Channel ${contact.channel}` : 'N/A'} (${contact.frequency ? `${contact.frequency} MHz` : 'N/A'}) - ${contact.band || 'N/A'}</span>

                <span class="detail-label">MANUFACTURER</span>
                <span class="detail-val">${escapeHtml(contact.manufacturer || 'Unknown')} ${contact.oui ? `(OUI: ${contact.oui})` : ''}</span>

                <span class="detail-label">RANDOMIZED MAC</span>
                <span class="detail-val">${contact.is_randomized ? 'YES (Locally Administered Bit Set)' : 'NO (Universally Administered)'}</span>

                <span class="detail-label">CLASSIFICATION</span>
                <span class="detail-val"><b>${contact.device_category}</b> (Confidence: ${Math.round(contact.classification_confidence * 100)}%)</span>

                <span class="detail-label">REASONING</span>
                <span class="detail-val" style="font-size: 11px; color: #94a3b8;">${escapeHtml(contact.classification_reason || 'N/A')}</span>

                <span class="detail-label">EVIDENCE</span>
                <span class="detail-val" style="font-size: 11px; color: #94a3b8;">${(contact.classification_evidence || []).map(e => `• ${escapeHtml(e)}`).join('<br>')}</span>

                <span class="detail-label">FIRST / LAST SEEN</span>
                <span class="detail-val">${formatTimestamp(contact.first_seen)} / ${formatTimestamp(contact.last_seen)} (${contact.observation_count} observations)</span>

                <span class="detail-label">WATCHLIST</span>
                <span class="detail-val" style="color: ${contact.watchlist_matched ? 'var(--neon-red)' : 'var(--text-dim)'};">${contact.watchlist_matched ? (contact.watchlist_notes || ['Match']).join(', ') : 'No Match'}</span>
            </div>
        `;
        contactModal.style.display = 'flex';
    };

    modalCloseBtn.addEventListener('click', () => {
        contactModal.style.display = 'none';
    });

    window.addEventListener('click', (e) => {
        if (e.target === contactModal) {
            contactModal.style.display = 'none';
        }
    });

    // ----------------- Tab Navigation -----------------
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

            btn.classList.add('active');
            const targetId = btn.getAttribute('data-tab');
            document.getElementById(targetId).classList.add('active');

            // Toggle table search visibility
            document.getElementById('table-search-bar').style.display = (targetId === 'tab-contacts') ? 'flex' : 'none';

            if (targetId === 'tab-diagnostics') {
                loadDiagnostics();
            }
        });
    });

    function loadDiagnostics() {
        fetch('/api/diagnostics')
            .then(res => res.json())
            .then(data => {
                document.getElementById('diag-terminal-output').innerText = data.table || JSON.stringify(data, null, 2);
            })
            .catch(err => {
                document.getElementById('diag-terminal-output').innerText = 'Failed to fetch diagnostics: ' + err;
            });
    }

    // ----------------- Filter & Search Handlers -----------------
    searchInput.addEventListener('input', (e) => {
        currentSearchTerm = e.target.value;
        renderTable();
    });

    filterTypeSelect.addEventListener('change', (e) => {
        currentFilterType = e.target.value;
        renderTable();
    });

    filterStateSelect.addEventListener('change', (e) => {
        currentFilterState = e.target.value;
        renderTable();
    });

    // Table Header Sorting
    document.querySelectorAll('#contacts-table th[data-sort]').forEach(th => {
        th.addEventListener('click', () => {
            const col = th.getAttribute('data-sort');
            if (sortColumn === col) {
                sortDirection = (sortDirection === 'asc') ? 'desc' : 'asc';
            } else {
                sortColumn = col;
                sortDirection = 'desc';
            }
            renderTable();
        });
    });

    // Audio Alert Toggle
    audioToggleBtn.addEventListener('click', () => {
        const isEnabled = window.tacticalAudio.toggle();
        audioIcon.innerText = isEnabled ? '🔊 AUDIO: ON' : '🔇 AUDIO: OFF';
        audioToggleBtn.classList.toggle('btn-primary', isEnabled);
        audioToggleBtn.classList.toggle('btn-secondary', !isEnabled);
    });

    // Radar Sweep Toggle
    radarSweepToggle.addEventListener('click', () => {
        const enabled = radar.toggleSweep();
        radarSweepToggle.innerText = enabled ? 'SWEEP: ON' : 'SWEEP: OFF';
        radarSweepToggle.classList.toggle('active', enabled);
    });

    // Helper functions
    function escapeHtml(str) {
        if (!str) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    function formatTimestamp(epoch) {
        if (!epoch) return '-';
        const d = new Date(epoch * 1000);
        return d.toTimeString().split(' ')[0];
    }

    // Start WebSocket
    connectWebSocket();
});
