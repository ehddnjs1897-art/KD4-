// ============================================================
// 넘버블럭스 테트리스 (Numberblocks Tetris)
// ============================================================

const COLS = 10;
const ROWS = 20;
let BLOCK_SIZE = 30;

const canvas = document.getElementById('game-board');
const ctx = canvas.getContext('2d');

const nextCanvas = document.getElementById('next-canvas');
const nextCtx = nextCanvas.getContext('2d');

const holdCanvas = document.getElementById('hold-canvas');
const holdCtx = holdCanvas.getContext('2d');

// Responsive sizing
function resizeCanvas() {
    const isMobile = window.innerWidth <= 768;
    if (isMobile) {
        const maxW = window.innerWidth - 20;
        const maxH = window.innerHeight * 0.55;
        BLOCK_SIZE = Math.floor(Math.min(maxW / COLS, maxH / ROWS));
        BLOCK_SIZE = Math.max(16, Math.min(BLOCK_SIZE, 28));
    } else {
        BLOCK_SIZE = 30;
    }
    canvas.width = COLS * BLOCK_SIZE;
    canvas.height = ROWS * BLOCK_SIZE;
}
resizeCanvas();
window.addEventListener('resize', resizeCanvas);

// Numberblocks character colors
const NUMBERBLOCK_COLORS = {
    1: { bg: '#E74C3C', face: '#C0392B', name: 'One' },
    2: { bg: '#E67E22', face: '#D35400', name: 'Two' },
    3: { bg: '#F1C40F', face: '#F39C12', name: 'Three' },
    4: { bg: '#2ECC71', face: '#27AE60', name: 'Four' },
    5: { bg: '#3498DB', face: '#2980B9', name: 'Five' },
    6: { bg: '#9B59B6', face: '#8E44AD', name: 'Six' },
    7: { bg: '#E91E90', face: '#C2185B', name: 'Seven' },
};

// Tetromino shapes mapped to Numberblock characters
const PIECES = [
    { number: 1, shape: [[1, 1, 1, 1]], name: 'I' },
    { number: 2, shape: [[1, 1], [1, 1]], name: 'O' },
    { number: 3, shape: [[0, 1, 0], [1, 1, 1]], name: 'T' },
    { number: 4, shape: [[1, 0], [1, 0], [1, 1]], name: 'L' },
    { number: 5, shape: [[0, 1], [0, 1], [1, 1]], name: 'J' },
    { number: 6, shape: [[0, 1, 1], [1, 1, 0]], name: 'S' },
    { number: 7, shape: [[1, 1, 0], [0, 1, 1]], name: 'Z' },
];

// Game state
let board = [];
let currentPiece = null;
let nextPieces = [];
let holdPiece = null;
let canHold = true;
let score = 0;
let level = 1;
let lines = 0;
let gameOver = false;
let gameStarted = false;
let dropInterval = 1000;
let lastDrop = 0;
let animationId = null;

// Scoring
const LINE_SCORES = [0, 100, 300, 500, 800];

// ============================================================
// Sound & Music (Web Audio API)
// ============================================================

let audioCtx = null;
let bgmPlaying = false;
let bgmGain = null;
let bgmTimeout = null;
let musicEnabled = true;
let sfxEnabled = true;

function initAudio() {
    if (audioCtx) return;
    audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    bgmGain = audioCtx.createGain();
    bgmGain.gain.value = 0.18;
    bgmGain.connect(audioCtx.destination);
}

function playNote(freq, duration, startTime, gain, type, dest) {
    const osc = audioCtx.createOscillator();
    const g = audioCtx.createGain();
    osc.type = type || 'square';
    osc.frequency.value = freq;
    g.gain.setValueAtTime(gain || 0.15, startTime);
    g.gain.exponentialRampToValueAtTime(0.001, startTime + duration);
    osc.connect(g);
    g.connect(dest || audioCtx.destination);
    osc.start(startTime);
    osc.stop(startTime + duration);
}

// Numberblocks-style happy melody (loops)
const BGM_MELODY = [
    // Bar 1: C major happy intro
    { n: 523, d: 0.2 },  // C5
    { n: 587, d: 0.2 },  // D5
    { n: 659, d: 0.2 },  // E5
    { n: 698, d: 0.4 },  // F5
    { n: 659, d: 0.2 },  // E5
    { n: 587, d: 0.2 },  // D5
    // Bar 2
    { n: 523, d: 0.4 },  // C5
    { n: 440, d: 0.2 },  // A4
    { n: 494, d: 0.2 },  // B4
    { n: 523, d: 0.4 },  // C5
    { n: 0, d: 0.2 },    // rest
    // Bar 3: ascending fun
    { n: 392, d: 0.2 },  // G4
    { n: 440, d: 0.2 },  // A4
    { n: 494, d: 0.2 },  // B4
    { n: 523, d: 0.3 },  // C5
    { n: 587, d: 0.3 },  // D5
    { n: 659, d: 0.4 },  // E5
    // Bar 4
    { n: 698, d: 0.3 },  // F5
    { n: 659, d: 0.2 },  // E5
    { n: 587, d: 0.2 },  // D5
    { n: 523, d: 0.4 },  // C5
    { n: 0, d: 0.3 },    // rest
    // Bar 5: bouncy section
    { n: 523, d: 0.15 }, // C5
    { n: 523, d: 0.15 }, // C5
    { n: 659, d: 0.3 },  // E5
    { n: 587, d: 0.15 }, // D5
    { n: 587, d: 0.15 }, // D5
    { n: 698, d: 0.3 },  // F5
    { n: 659, d: 0.3 },  // E5
    { n: 523, d: 0.3 },  // C5
    // Bar 6
    { n: 440, d: 0.2 },  // A4
    { n: 494, d: 0.2 },  // B4
    { n: 523, d: 0.3 },  // C5
    { n: 392, d: 0.3 },  // G4
    { n: 440, d: 0.4 },  // A4
    { n: 0, d: 0.3 },    // rest
    // Bar 7: high energy
    { n: 784, d: 0.2 },  // G5
    { n: 698, d: 0.2 },  // F5
    { n: 659, d: 0.2 },  // E5
    { n: 587, d: 0.2 },  // D5
    { n: 523, d: 0.4 },  // C5
    { n: 587, d: 0.2 },  // D5
    { n: 659, d: 0.4 },  // E5
    // Bar 8: ending phrase
    { n: 523, d: 0.3 },  // C5
    { n: 440, d: 0.2 },  // A4
    { n: 392, d: 0.2 },  // G4
    { n: 440, d: 0.3 },  // A4
    { n: 523, d: 0.5 },  // C5
    { n: 0, d: 0.4 },    // rest
];

function startBGM() {
    if (!audioCtx || !musicEnabled) return;
    bgmPlaying = true;
    playBGMLoop();
}

function playBGMLoop() {
    if (!bgmPlaying || !musicEnabled) return;
    const now = audioCtx.currentTime;
    let t = now + 0.05;
    for (const note of BGM_MELODY) {
        if (note.n > 0) {
            playNote(note.n, note.d * 0.9, t, 0.12, 'square', bgmGain);
            playNote(note.n * 0.5, note.d * 0.9, t, 0.06, 'triangle', bgmGain);
        }
        t += note.d;
    }
    const loopDuration = (t - now) * 1000;
    bgmTimeout = setTimeout(() => {
        if (bgmPlaying && musicEnabled) playBGMLoop();
    }, loopDuration - 50);
}

function stopBGM() {
    bgmPlaying = false;
    if (bgmTimeout) {
        clearTimeout(bgmTimeout);
        bgmTimeout = null;
    }
}

// Sound effects
function sfxMove() {
    if (!audioCtx || !sfxEnabled) return;
    const now = audioCtx.currentTime;
    playNote(400, 0.06, now, 0.08, 'sine');
}

function sfxRotate() {
    if (!audioCtx || !sfxEnabled) return;
    const now = audioCtx.currentTime;
    playNote(600, 0.05, now, 0.1, 'sine');
    playNote(800, 0.05, now + 0.05, 0.1, 'sine');
}

function sfxDrop() {
    if (!audioCtx || !sfxEnabled) return;
    const now = audioCtx.currentTime;
    playNote(200, 0.15, now, 0.15, 'triangle');
    playNote(150, 0.1, now + 0.05, 0.1, 'triangle');
}

function sfxLock() {
    if (!audioCtx || !sfxEnabled) return;
    const now = audioCtx.currentTime;
    playNote(300, 0.1, now, 0.1, 'square');
}

function sfxLineClear(count) {
    if (!audioCtx || !sfxEnabled) return;
    const now = audioCtx.currentTime;
    const notes = [523, 659, 784, 1047];
    for (let i = 0; i < Math.min(count, 4); i++) {
        playNote(notes[i], 0.2, now + i * 0.1, 0.15, 'square');
        playNote(notes[i] * 1.5, 0.15, now + i * 0.1, 0.08, 'sine');
    }
}

function sfxGameOver() {
    if (!audioCtx || !sfxEnabled) return;
    const now = audioCtx.currentTime;
    playNote(400, 0.3, now, 0.15, 'sawtooth');
    playNote(350, 0.3, now + 0.3, 0.12, 'sawtooth');
    playNote(300, 0.3, now + 0.6, 0.1, 'sawtooth');
    playNote(200, 0.6, now + 0.9, 0.12, 'sawtooth');
}

function sfxHold() {
    if (!audioCtx || !sfxEnabled) return;
    const now = audioCtx.currentTime;
    playNote(500, 0.08, now, 0.08, 'sine');
    playNote(700, 0.08, now + 0.08, 0.08, 'sine');
}

function sfxLevelUp() {
    if (!audioCtx || !sfxEnabled) return;
    const now = audioCtx.currentTime;
    const notes = [523, 659, 784, 1047, 1319];
    for (let i = 0; i < notes.length; i++) {
        playNote(notes[i], 0.12, now + i * 0.08, 0.12, 'square');
    }
}

function createBoard() {
    board = [];
    for (let r = 0; r < ROWS; r++) {
        board.push(new Array(COLS).fill(0));
    }
}

function randomPiece() {
    const idx = Math.floor(Math.random() * PIECES.length);
    const piece = PIECES[idx];
    return {
        number: piece.number,
        shape: piece.shape.map(row => [...row]),
        name: piece.name,
        x: Math.floor((COLS - piece.shape[0].length) / 2),
        y: 0,
    };
}

function fillNextQueue() {
    while (nextPieces.length < 3) {
        nextPieces.push(randomPiece());
    }
}

function spawnPiece() {
    fillNextQueue();
    currentPiece = nextPieces.shift();
    currentPiece.x = Math.floor((COLS - currentPiece.shape[0].length) / 2);
    currentPiece.y = 0;
    fillNextQueue();
    canHold = true;

    if (collides(currentPiece.shape, currentPiece.x, currentPiece.y)) {
        gameOver = true;
    }
}

function collides(shape, px, py) {
    for (let r = 0; r < shape.length; r++) {
        for (let c = 0; c < shape[r].length; c++) {
            if (shape[r][c]) {
                const newX = px + c;
                const newY = py + r;
                if (newX < 0 || newX >= COLS || newY >= ROWS) return true;
                if (newY >= 0 && board[newY][newX]) return true;
            }
        }
    }
    return false;
}

function lockPiece() {
    for (let r = 0; r < currentPiece.shape.length; r++) {
        for (let c = 0; c < currentPiece.shape[r].length; c++) {
            if (currentPiece.shape[r][c]) {
                const boardY = currentPiece.y + r;
                const boardX = currentPiece.x + c;
                if (boardY >= 0) {
                    board[boardY][boardX] = currentPiece.number;
                }
            }
        }
    }
    sfxLock();
    clearLines();
    spawnPiece();
}

function clearLines() {
    let clearedRows = [];
    for (let r = ROWS - 1; r >= 0; r--) {
        if (board[r].every(cell => cell !== 0)) {
            clearedRows.push(r);
        }
    }
    if (clearedRows.length > 0) {
        sfxLineClear(clearedRows.length);
        // Spawn dancing numberblocks and particles from cleared rows
        for (const row of clearedRows) {
            for (let c = 0; c < COLS; c++) {
                const num = board[row][c];
                if (num) {
                    spawnDancingBlock(c, row, num);
                    for (let p = 0; p < 3; p++) {
                        spawnParticle(c * BLOCK_SIZE + BLOCK_SIZE / 2, row * BLOCK_SIZE + BLOCK_SIZE / 2, num);
                    }
                }
            }
        }
        // Flash effect
        screenFlash = 8;
        // Remove rows
        for (const row of clearedRows.sort((a, b) => b - a)) {
            board.splice(row, 1);
            board.unshift(new Array(COLS).fill(0));
        }
        const oldLevel = level;
        score += LINE_SCORES[clearedRows.length] * level;
        lines += clearedRows.length;
        level = Math.floor(lines / 10) + 1;
        dropInterval = Math.max(100, 1000 - (level - 1) * 80);
        if (level > oldLevel) sfxLevelUp();
        updateUI();
    }
}

// ============================================================
// Line Clear Effects: Dancing Numberblocks + Particles
// ============================================================

let dancingBlocks = [];
let particles = [];
let screenFlash = 0;

function spawnDancingBlock(col, row, number) {
    dancingBlocks.push({
        x: col * BLOCK_SIZE + BLOCK_SIZE / 2,
        y: row * BLOCK_SIZE,
        number: number,
        vy: -(3 + Math.random() * 4),
        vx: (Math.random() - 0.5) * 4,
        rotation: 0,
        rotSpeed: (Math.random() - 0.5) * 0.3,
        life: 60,
        maxLife: 60,
        size: BLOCK_SIZE,
        bouncePhase: Math.random() * Math.PI * 2,
    });
}

function spawnParticle(x, y, number) {
    const color = NUMBERBLOCK_COLORS[number];
    const angle = Math.random() * Math.PI * 2;
    const speed = 2 + Math.random() * 5;
    particles.push({
        x: x,
        y: y,
        vx: Math.cos(angle) * speed,
        vy: Math.sin(angle) * speed - 2,
        color: color.bg,
        size: 3 + Math.random() * 5,
        life: 30 + Math.random() * 20,
        maxLife: 50,
    });
}

function updateEffects() {
    // Update dancing blocks
    for (let i = dancingBlocks.length - 1; i >= 0; i--) {
        const b = dancingBlocks[i];
        b.x += b.vx;
        b.y += b.vy;
        b.vy += 0.15;
        b.rotation += b.rotSpeed;
        b.life--;
        if (b.life <= 0) dancingBlocks.splice(i, 1);
    }
    // Update particles
    for (let i = particles.length - 1; i >= 0; i--) {
        const p = particles[i];
        p.x += p.vx;
        p.y += p.vy;
        p.vy += 0.1;
        p.size *= 0.97;
        p.life--;
        if (p.life <= 0) particles.splice(i, 1);
    }
    // Screen flash
    if (screenFlash > 0) screenFlash--;
}

function drawEffects() {
    // Screen flash
    if (screenFlash > 0) {
        ctx.globalAlpha = screenFlash / 12;
        ctx.fillStyle = '#fff';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.globalAlpha = 1;
    }

    // Draw dancing blocks
    for (const b of dancingBlocks) {
        const alpha = b.life / b.maxLife;
        const wobble = Math.sin(b.bouncePhase + (b.maxLife - b.life) * 0.3) * 5;
        ctx.save();
        ctx.globalAlpha = alpha;
        ctx.translate(b.x, b.y + wobble);
        ctx.rotate(b.rotation);
        const s = b.size * (0.8 + alpha * 0.4);
        const color = NUMBERBLOCK_COLORS[b.number];
        // Block body
        ctx.fillStyle = color.bg;
        ctx.fillRect(-s / 2, -s / 2, s, s);
        // Highlight
        ctx.fillStyle = 'rgba(255,255,255,0.4)';
        ctx.fillRect(-s / 2, -s / 2, s, 3);
        // Number
        ctx.fillStyle = '#fff';
        ctx.font = `bold ${Math.floor(s * 0.5)}px 'Jua', sans-serif`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(b.number, 0, 2);
        // Happy face (smile!)
        ctx.fillStyle = '#fff';
        ctx.beginPath();
        ctx.arc(-s * 0.15, -s * 0.1, s * 0.07, 0, Math.PI * 2);
        ctx.fill();
        ctx.beginPath();
        ctx.arc(s * 0.15, -s * 0.1, s * 0.07, 0, Math.PI * 2);
        ctx.fill();
        ctx.fillStyle = '#333';
        ctx.beginPath();
        ctx.arc(-s * 0.15, -s * 0.1, s * 0.05, 0, Math.PI * 2);
        ctx.fill();
        ctx.beginPath();
        ctx.arc(s * 0.15, -s * 0.1, s * 0.05, 0, Math.PI * 2);
        ctx.fill();
        // Smile
        ctx.strokeStyle = '#fff';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(0, s * 0.1, s * 0.12, 0, Math.PI);
        ctx.stroke();
        ctx.restore();
    }

    // Draw particles (sparkles)
    for (const p of particles) {
        const alpha = p.life / p.maxLife;
        ctx.globalAlpha = alpha;
        ctx.fillStyle = p.color;
        ctx.beginPath();
        // Star shape
        const spikes = 4;
        const outerR = p.size;
        const innerR = p.size * 0.4;
        for (let i = 0; i < spikes * 2; i++) {
            const r = i % 2 === 0 ? outerR : innerR;
            const angle = (i * Math.PI) / spikes - Math.PI / 2;
            if (i === 0) ctx.moveTo(p.x + r * Math.cos(angle), p.y + r * Math.sin(angle));
            else ctx.lineTo(p.x + r * Math.cos(angle), p.y + r * Math.sin(angle));
        }
        ctx.closePath();
        ctx.fill();
        ctx.globalAlpha = 1;
    }
}

function rotate(shape) {
    const rows = shape.length;
    const cols = shape[0].length;
    const rotated = [];
    for (let c = 0; c < cols; c++) {
        rotated.push([]);
        for (let r = rows - 1; r >= 0; r--) {
            rotated[c].push(shape[r][c]);
        }
    }
    return rotated;
}

function tryRotate() {
    if (!gameStarted || gameOver || !currentPiece) return;
    const rotated = rotate(currentPiece.shape);
    const kicks = [0, -1, 1, -2, 2];
    for (const kick of kicks) {
        if (!collides(rotated, currentPiece.x + kick, currentPiece.y)) {
            currentPiece.shape = rotated;
            currentPiece.x += kick;
            sfxRotate();
            return;
        }
    }
}

function movePiece(dx, dy) {
    if (!currentPiece) return false;
    if (!collides(currentPiece.shape, currentPiece.x + dx, currentPiece.y + dy)) {
        currentPiece.x += dx;
        currentPiece.y += dy;
        if (dx !== 0) sfxMove();
        return true;
    }
    return false;
}

function hardDrop() {
    if (!gameStarted || gameOver || !currentPiece) return;
    sfxDrop();
    while (movePiece(0, 1)) {
        score += 2;
    }
    lockPiece();
    updateUI();
}

function holdCurrentPiece() {
    if (!gameStarted || gameOver || !canHold) return;
    canHold = false;
    sfxHold();

    if (holdPiece) {
        const temp = holdPiece;
        holdPiece = {
            number: currentPiece.number,
            shape: PIECES.find(p => p.number === currentPiece.number).shape.map(r => [...r]),
            name: currentPiece.name,
            x: 0,
            y: 0,
        };
        currentPiece = temp;
        currentPiece.x = Math.floor((COLS - currentPiece.shape[0].length) / 2);
        currentPiece.y = 0;
    } else {
        holdPiece = {
            number: currentPiece.number,
            shape: PIECES.find(p => p.number === currentPiece.number).shape.map(r => [...r]),
            name: currentPiece.name,
            x: 0,
            y: 0,
        };
        spawnPiece();
    }
}

function getGhostY() {
    let ghostY = currentPiece.y;
    while (!collides(currentPiece.shape, currentPiece.x, ghostY + 1)) {
        ghostY++;
    }
    return ghostY;
}

// ============================================================
// Drawing
// ============================================================

function drawBlock(context, x, y, number, size, alpha) {
    const color = NUMBERBLOCK_COLORS[number];
    if (!color) return;

    const px = x * size;
    const py = y * size;
    const padding = 1;

    context.globalAlpha = alpha || 1;

    context.fillStyle = color.bg;
    context.fillRect(px + padding, py + padding, size - padding * 2, size - padding * 2);

    context.fillStyle = 'rgba(255, 255, 255, 0.3)';
    context.fillRect(px + padding, py + padding, size - padding * 2, 3);
    context.fillRect(px + padding, py + padding, 3, size - padding * 2);

    context.fillStyle = 'rgba(0, 0, 0, 0.2)';
    context.fillRect(px + padding, py + size - padding - 3, size - padding * 2, 3);
    context.fillRect(px + size - padding - 3, py + padding, 3, size - padding * 2);

    context.fillStyle = '#fff';
    context.font = `bold ${Math.floor(size * 0.5)}px 'Jua', sans-serif`;
    context.textAlign = 'center';
    context.textBaseline = 'middle';
    context.fillText(number, px + size / 2, py + size / 2 + 1);

    if (size >= 20) {
        const eyeSize = size * 0.06;
        const eyeY = py + size * 0.35;
        context.fillStyle = '#fff';
        context.beginPath();
        context.arc(px + size * 0.35, eyeY, eyeSize + 1, 0, Math.PI * 2);
        context.fill();
        context.beginPath();
        context.arc(px + size * 0.65, eyeY, eyeSize + 1, 0, Math.PI * 2);
        context.fill();
        context.fillStyle = '#333';
        context.beginPath();
        context.arc(px + size * 0.35, eyeY, eyeSize, 0, Math.PI * 2);
        context.fill();
        context.beginPath();
        context.arc(px + size * 0.65, eyeY, eyeSize, 0, Math.PI * 2);
        context.fill();
    }

    context.globalAlpha = 1;
}

function drawBoard() {
    ctx.fillStyle = '#0a0a1a';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    ctx.strokeStyle = 'rgba(255, 255, 255, 0.03)';
    ctx.lineWidth = 1;
    for (let r = 0; r < ROWS; r++) {
        for (let c = 0; c < COLS; c++) {
            ctx.strokeRect(c * BLOCK_SIZE, r * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE);
        }
    }

    for (let r = 0; r < ROWS; r++) {
        for (let c = 0; c < COLS; c++) {
            if (board[r][c]) {
                drawBlock(ctx, c, r, board[r][c], BLOCK_SIZE);
            }
        }
    }

    if (currentPiece && !gameOver) {
        const ghostY = getGhostY();
        for (let r = 0; r < currentPiece.shape.length; r++) {
            for (let c = 0; c < currentPiece.shape[r].length; c++) {
                if (currentPiece.shape[r][c]) {
                    drawBlock(ctx, currentPiece.x + c, ghostY + r, currentPiece.number, BLOCK_SIZE, 0.2);
                }
            }
        }

        for (let r = 0; r < currentPiece.shape.length; r++) {
            for (let c = 0; c < currentPiece.shape[r].length; c++) {
                if (currentPiece.shape[r][c]) {
                    drawBlock(ctx, currentPiece.x + c, currentPiece.y + r, currentPiece.number, BLOCK_SIZE);
                }
            }
        }
    }
}

function drawPreview(context, piece, canvasWidth, canvasHeight) {
    context.fillStyle = 'rgba(0, 0, 0, 0.3)';
    context.fillRect(0, 0, canvasWidth, canvasHeight);

    if (!piece) return;

    const previewSize = 24;
    const shape = piece.shape || PIECES.find(p => p.number === piece.number).shape;
    const shapeW = shape[0].length * previewSize;
    const shapeH = shape.length * previewSize;
    const offsetX = (canvasWidth - shapeW) / 2;
    const offsetY = (canvasHeight - shapeH) / 2;

    for (let r = 0; r < shape.length; r++) {
        for (let c = 0; c < shape[r].length; c++) {
            if (shape[r][c]) {
                const px = offsetX + c * previewSize;
                const py = offsetY + r * previewSize;

                const color = NUMBERBLOCK_COLORS[piece.number];
                context.fillStyle = color.bg;
                context.fillRect(px + 1, py + 1, previewSize - 2, previewSize - 2);

                context.fillStyle = 'rgba(255,255,255,0.3)';
                context.fillRect(px + 1, py + 1, previewSize - 2, 2);

                context.fillStyle = '#fff';
                context.font = `bold ${previewSize * 0.45}px 'Jua', sans-serif`;
                context.textAlign = 'center';
                context.textBaseline = 'middle';
                context.fillText(piece.number, px + previewSize / 2, py + previewSize / 2 + 1);
            }
        }
    }
}

function drawNextPieces() {
    nextCtx.clearRect(0, 0, nextCanvas.width, nextCanvas.height);
    const sliceH = nextCanvas.height / 3;
    for (let i = 0; i < Math.min(3, nextPieces.length); i++) {
        nextCtx.save();
        nextCtx.translate(0, i * sliceH);
        drawPreview(nextCtx, nextPieces[i], nextCanvas.width, sliceH);
        nextCtx.restore();
    }
}

function drawHoldPiece() {
    holdCtx.clearRect(0, 0, holdCanvas.width, holdCanvas.height);
    drawPreview(holdCtx, holdPiece, holdCanvas.width, holdCanvas.height);
}

function updateUI() {
    document.getElementById('score').textContent = score.toLocaleString();
    document.getElementById('level').textContent = level;
    document.getElementById('lines').textContent = lines;
}

// ============================================================
// Game Loop
// ============================================================

function gameLoop(timestamp) {
    if (gameOver) {
        showGameOver();
        return;
    }

    if (timestamp - lastDrop > dropInterval) {
        if (!movePiece(0, 1)) {
            lockPiece();
            updateUI();
        }
        lastDrop = timestamp;
    }

    updateEffects();
    drawBoard();
    drawEffects();
    drawNextPieces();
    drawHoldPiece();

    animationId = requestAnimationFrame(gameLoop);
}

function showGameOver() {
    stopBGM();
    sfxGameOver();
    drawBoard();
    document.getElementById('final-score').textContent = score.toLocaleString();
    document.getElementById('final-level').textContent = level;
    document.getElementById('game-over-screen').classList.add('active');
}

// ============================================================
// Keyboard Controls
// ============================================================

document.addEventListener('keydown', (e) => {
    if (!gameStarted || gameOver) return;

    switch (e.key) {
        case 'ArrowLeft':
            e.preventDefault();
            movePiece(-1, 0);
            break;
        case 'ArrowRight':
            e.preventDefault();
            movePiece(1, 0);
            break;
        case 'ArrowDown':
            e.preventDefault();
            if (movePiece(0, 1)) {
                score += 1;
                updateUI();
            }
            break;
        case 'ArrowUp':
            e.preventDefault();
            tryRotate();
            break;
        case ' ':
            e.preventDefault();
            hardDrop();
            break;
        case 'c':
        case 'C':
            e.preventDefault();
            holdCurrentPiece();
            break;
    }
});

// ============================================================
// Mobile Button Controls
// ============================================================

function mobileLeft(e) {
    e.preventDefault();
    if (!gameStarted || gameOver) return;
    movePiece(-1, 0);
}

function mobileRight(e) {
    e.preventDefault();
    if (!gameStarted || gameOver) return;
    movePiece(1, 0);
}

function mobileDown(e) {
    e.preventDefault();
    if (!gameStarted || gameOver) return;
    if (movePiece(0, 1)) {
        score += 1;
        updateUI();
    }
}

function mobileRotate(e) {
    e.preventDefault();
    if (!gameStarted || gameOver) return;
    tryRotate();
}

function mobileHardDrop(e) {
    e.preventDefault();
    if (!gameStarted || gameOver) return;
    hardDrop();
}

function mobileHold(e) {
    e.preventDefault();
    if (!gameStarted || gameOver) return;
    holdCurrentPiece();
}

// Auto-repeat for mobile left/right buttons
let mobileRepeatTimer = null;
let mobileRepeatInterval = null;

function setupMobileRepeat(btnId, action) {
    const btn = document.getElementById(btnId);
    if (!btn) return;

    const startRepeat = (e) => {
        e.preventDefault();
        if (!gameStarted || gameOver) return;
        action();
        clearTimeout(mobileRepeatTimer);
        clearInterval(mobileRepeatInterval);
        mobileRepeatTimer = setTimeout(() => {
            mobileRepeatInterval = setInterval(() => {
                if (!gameStarted || gameOver) {
                    clearInterval(mobileRepeatInterval);
                    return;
                }
                action();
            }, 80);
        }, 200);
    };

    const stopRepeat = (e) => {
        e.preventDefault();
        clearTimeout(mobileRepeatTimer);
        clearInterval(mobileRepeatInterval);
    };

    btn.addEventListener('touchstart', startRepeat, { passive: false });
    btn.addEventListener('touchend', stopRepeat, { passive: false });
    btn.addEventListener('touchcancel', stopRepeat, { passive: false });
}

setupMobileRepeat('btn-left', () => movePiece(-1, 0));
setupMobileRepeat('btn-right', () => movePiece(1, 0));
setupMobileRepeat('btn-down', () => {
    if (movePiece(0, 1)) {
        score += 1;
        updateUI();
    }
});

// Prevent default touch behavior on game area to avoid scrolling
document.getElementById('game-container').addEventListener('touchmove', (e) => {
    e.preventDefault();
}, { passive: false });

// ============================================================
// Game Start / Restart
// ============================================================

function startGame() {
    document.getElementById('start-screen').style.display = 'none';
    initAudio();
    resizeCanvas();
    initGame();
}

function restartGame() {
    document.getElementById('game-over-screen').classList.remove('active');
    initAudio();
    initGame();
}

function initGame() {
    if (animationId) cancelAnimationFrame(animationId);
    stopBGM();

    createBoard();
    nextPieces = [];
    holdPiece = null;
    canHold = true;
    score = 0;
    level = 1;
    lines = 0;
    dropInterval = 1000;
    gameOver = false;
    gameStarted = true;
    lastDrop = 0;
    dancingBlocks = [];
    particles = [];
    screenFlash = 0;

    updateUI();
    fillNextQueue();
    spawnPiece();
    startBGM();
    animationId = requestAnimationFrame(gameLoop);
}

// Toggle music / sfx
function toggleMusic() {
    musicEnabled = !musicEnabled;
    if (!musicEnabled) {
        stopBGM();
    } else if (gameStarted && !gameOver) {
        startBGM();
    }
    const btn = document.getElementById('btn-music');
    if (btn) btn.textContent = musicEnabled ? '♫' : '♫✕';
}

function toggleSfx() {
    sfxEnabled = !sfxEnabled;
    const btn = document.getElementById('btn-sfx');
    if (btn) btn.textContent = sfxEnabled ? '🔊' : '🔇';
}
