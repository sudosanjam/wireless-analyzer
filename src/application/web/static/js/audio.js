/**
 * Tactical Web Audio API sound synthesizer for local alerting.
 * 100% offline-capable, synthesized purely in browser memory.
 */

class TacticalAudioEngine {
    constructor() {
        this.ctx = null;
        this.enabled = false;
        this.lastAlertTime = 0;
        this.debounceMs = 3000;
    }

    init() {
        if (!this.ctx) {
            const AudioContext = window.AudioContext || window.webkitAudioContext;
            if (AudioContext) {
                this.ctx = new AudioContext();
            }
        }
        if (this.ctx && this.ctx.state === 'suspended') {
            this.ctx.resume();
        }
    }

    toggle() {
        this.init();
        this.enabled = !this.enabled;
        if (this.enabled) {
            this.playChirp(880, 0.08); // Feedback chime
        }
        return this.enabled;
    }

    playChirp(freq = 660, duration = 0.06) {
        if (!this.enabled || !this.ctx) return;
        try {
            const osc = this.ctx.createOscillator();
            const gain = this.ctx.createGain();
            
            osc.type = 'sine';
            osc.frequency.setValueAtTime(freq, this.ctx.currentTime);
            osc.frequency.exponentialRampToValueAtTime(freq * 1.5, this.ctx.currentTime + duration);

            gain.gain.setValueAtTime(0.08, this.ctx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.001, this.ctx.currentTime + duration);

            osc.connect(gain);
            gain.connect(this.ctx.destination);

            osc.start();
            osc.stop(this.ctx.currentTime + duration);
        } catch (e) {
            console.debug('Audio error', e);
        }
    }

    playAlertTone() {
        if (!this.enabled || !this.ctx) return;
        const now = Date.now();
        if (now - this.lastAlertTime < this.debounceMs) return;
        this.lastAlertTime = now;

        try {
            const osc1 = this.ctx.createOscillator();
            const osc2 = this.ctx.createOscillator();
            const gain = this.ctx.createGain();

            osc1.type = 'triangle';
            osc1.frequency.setValueAtTime(1174.66, this.ctx.currentTime); // D6

            osc2.type = 'sine';
            osc2.frequency.setValueAtTime(1760.00, this.ctx.currentTime); // A6

            gain.gain.setValueAtTime(0.15, this.ctx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.001, this.ctx.currentTime + 0.35);

            osc1.connect(gain);
            osc2.connect(gain);
            gain.connect(this.ctx.destination);

            osc1.start();
            osc2.start();
            osc1.stop(this.ctx.currentTime + 0.35);
            osc2.stop(this.ctx.currentTime + 0.35);
        } catch (e) {
            console.debug('Alert tone error', e);
        }
    }
}

window.tacticalAudio = new TacticalAudioEngine();
