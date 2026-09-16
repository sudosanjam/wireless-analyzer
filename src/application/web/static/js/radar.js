/**
 * Tactical HTML5 Canvas Signal Radar.
 * Maps relative RSSI strength and deterministic angle without false directionality claims.
 */

class TacticalRadar {
    constructor(canvasId, tooltipId) {
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas.getContext('2d');
        this.tooltip = document.getElementById(tooltipId);
        
        this.contacts = [];
        this.sweepAngle = 0;
        this.sweepEnabled = true;
        this.hoveredContact = null;

        this.initCanvas();
        this.setupEventListeners();
        this.animate = this.animate.bind(this);
        requestAnimationFrame(this.animate);
    }

    initCanvas() {
        const dpr = window.devicePixelRatio || 1;
        const rect = this.canvas.getBoundingClientRect();
        const size = Math.min(rect.width || 440, rect.height || 440);
        
        this.canvas.width = size * dpr;
        this.canvas.height = size * dpr;
        this.ctx.scale(dpr, dpr);
        this.size = size;
        this.center = size / 2;
        this.radius = (size / 2) - 20;
    }

    setContacts(contactsList) {
        this.contacts = contactsList;
    }

    toggleSweep() {
        this.sweepEnabled = !this.sweepEnabled;
        return this.sweepEnabled;
    }

    setupEventListeners() {
        window.addEventListener('resize', () => this.initCanvas());

        this.canvas.addEventListener('mousemove', (e) => {
            const rect = this.canvas.getBoundingClientRect();
            const mouseX = e.clientX - rect.left;
            const mouseY = e.clientY - rect.top;

            let found = null;
            for (const c of this.contacts) {
                const pt = this.getContactCoords(c);
                const dist = Math.hypot(mouseX - pt.x, mouseY - pt.y);
                if (dist <= 8) {
                    found = c;
                    break;
                }
            }

            this.hoveredContact = found;
            if (found) {
                this.tooltip.style.display = 'block';
                this.tooltip.style.left = `${e.clientX + 12}px`;
                this.tooltip.style.top = `${e.clientY + 12}px`;
                const label = found.ssid || found.device_name || '*(Hidden/Unknown)*';
                this.tooltip.innerHTML = `
                    <div style="font-weight: bold; color: #00d4ff;">${label}</div>
                    <div>MAC: ${found.mac_address}</div>
                    <div>RSSI: ${found.latest_rssi} dBm (${found.rssi_category})</div>
                    <div>VENDOR: ${found.manufacturer}</div>
                `;
            } else {
                this.tooltip.style.display = 'none';
            }
        });

        this.canvas.addEventListener('click', () => {
            if (this.hoveredContact && window.showContactDetails) {
                window.showContactDetails(this.hoveredContact);
            }
        });

        this.canvas.addEventListener('mouseleave', () => {
            this.hoveredContact = null;
            this.tooltip.style.display = 'none';
        });
    }

    getContactCoords(contact) {
        const angleRad = (contact.radar_angle_degrees * Math.PI) / 180.0;
        const r = contact.radar_distance_ratio * this.radius;
        return {
            x: this.center + (r * Math.cos(angleRad)),
            y: this.center + (r * Math.sin(angleRad)),
        };
    }

    animate() {
        if (this.sweepEnabled) {
            this.sweepAngle = (this.sweepAngle + 0.02) % (Math.PI * 2);
        }
        this.render();
        requestAnimationFrame(this.animate);
    }

    render() {
        const { ctx, center, radius, size } = this;
        ctx.clearRect(0, 0, size, size);

        // 1. Concentric RSSI Range Rings
        const rings = [
            { ratio: 0.25, label: '-45 dBm' },
            { ratio: 0.50, label: '-60 dBm' },
            { ratio: 0.75, label: '-75 dBm' },
            { ratio: 0.95, label: '-90 dBm' },
        ];

        ctx.lineWidth = 1;
        ctx.strokeStyle = 'rgba(0, 212, 255, 0.12)';
        ctx.fillStyle = 'rgba(100, 116, 139, 0.4)';
        ctx.font = '9px "JetBrains Mono", monospace';

        rings.forEach(ring => {
            const r = ring.ratio * radius;
            ctx.beginPath();
            ctx.arc(center, center, r, 0, Math.PI * 2);
            ctx.stroke();

            // Ring distance labels
            ctx.fillText(ring.label, center + 4, center - r + 10);
        });

        // 2. Crosshair Grid Lines
        ctx.strokeStyle = 'rgba(0, 212, 255, 0.1)';
        ctx.beginPath();
        ctx.moveTo(center - radius, center);
        ctx.lineTo(center + radius, center);
        ctx.moveTo(center, center - radius);
        ctx.lineTo(center, center + radius);
        ctx.stroke();

        // 3. Rotating Sweep Line & Gradient Beam
        if (this.sweepEnabled) {
            ctx.save();
            ctx.beginPath();
            ctx.moveTo(center, center);
            ctx.arc(center, center, radius, this.sweepAngle - 0.25, this.sweepAngle);
            ctx.closePath();
            
            const grad = ctx.createRadialGradient(center, center, 0, center, center, radius);
            grad.addColorStop(0, 'rgba(0, 255, 157, 0.0)');
            grad.addColorStop(1, 'rgba(0, 255, 157, 0.15)');
            ctx.fillStyle = grad;
            ctx.fill();

            // Leading Edge Line
            ctx.beginPath();
            ctx.moveTo(center, center);
            ctx.lineTo(
                center + (radius * Math.cos(this.sweepAngle)),
                center + (radius * Math.sin(this.sweepAngle))
            );
            ctx.strokeStyle = 'rgba(0, 255, 157, 0.6)';
            ctx.lineWidth = 1.5;
            ctx.stroke();
            ctx.restore();
        }

        // 4. Center Observer Beacon
        ctx.beginPath();
        ctx.arc(center, center, 3.5, 0, Math.PI * 2);
        ctx.fillStyle = '#00ff9d';
        ctx.shadowColor = '#00ff9d';
        ctx.shadowBlur = 8;
        ctx.fill();
        ctx.shadowBlur = 0;

        // 5. Render Contacts
        for (const c of this.contacts) {
            const pt = this.getContactCoords(c);
            const isHovered = (this.hoveredContact && this.hoveredContact.contact_id === c.contact_id);

            // Determine alpha based on contact state
            let alpha = 1.0;
            if (c.state === 'RECENT') alpha = 0.55;
            if (c.state === 'STALE') alpha = 0.2;

            ctx.save();
            ctx.globalAlpha = alpha;

            // Watchlist Pulsing Halo
            if (c.watchlist_matched) {
                ctx.beginPath();
                ctx.arc(pt.x, pt.y, isHovered ? 12 : 9, 0, Math.PI * 2);
                ctx.strokeStyle = 'rgba(255, 51, 102, 0.8)';
                ctx.lineWidth = 1.5;
                ctx.stroke();
            }

            // Blip Shape & Color
            ctx.beginPath();
            if (c.signal_type === 'ble') {
                // BLE: Triangle Blip
                ctx.moveTo(pt.x, pt.y - (isHovered ? 6 : 4));
                ctx.lineTo(pt.x - (isHovered ? 5 : 3.5), pt.y + (isHovered ? 5 : 3.5));
                ctx.lineTo(pt.x + (isHovered ? 5 : 3.5), pt.y + (isHovered ? 5 : 3.5));
                ctx.closePath();
                ctx.fillStyle = '#c084fc';
                ctx.shadowColor = '#c084fc';
            } else {
                // Wi-Fi: Diamond / Circle Blip
                ctx.arc(pt.x, pt.y, isHovered ? 5 : 3.5, 0, Math.PI * 2);
                ctx.fillStyle = '#00d4ff';
                ctx.shadowColor = '#00d4ff';
            }

            ctx.shadowBlur = isHovered ? 12 : 5;
            ctx.fill();
            ctx.restore();
        }
    }
}
