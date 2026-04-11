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
    clearLines();
    spawnPiece();
}

function clearLines() {
    let cleared = 0;
    for (let r = ROWS - 1; r >= 0; r--) {
        if (board[r].every(cell => cell !== 0)) {
            board.splice(r, 1);
            board.unshift(new Array(COLS).fill(0));
            cleared++;
            r++;
        }
    }
    if (cleared > 0) {
        score += LINE_SCORES[cleared] * level;
        lines += cleared;
        level = Math.floor(lines / 10) + 1;
        dropInterval = Math.max(100, 1000 - (level - 1) * 80);
        updateUI();
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
            return;
        }
    }
}

function movePiece(dx, dy) {
    if (!currentPiece) return false;
    if (!collides(currentPiece.shape, currentPiece.x + dx, currentPiece.y + dy)) {
        currentPiece.x += dx;
        currentPiece.y += dy;
        return true;
    }
    return false;
}

function hardDrop() {
    if (!gameStarted || gameOver || !currentPiece) return;
    while (movePiece(0, 1)) {
        score += 2;
    }
    lockPiece();
    updateUI();
}

function holdCurrentPiece() {
    if (!gameStarted || gameOver || !canHold) return;
    canHold = false;

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

    drawBoard();
    drawNextPieces();
    drawHoldPiece();

    animationId = requestAnimationFrame(gameLoop);
}

function showGameOver() {
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
    resizeCanvas();
    initGame();
}

function restartGame() {
    document.getElementById('game-over-screen').classList.remove('active');
    initGame();
}

function initGame() {
    if (animationId) cancelAnimationFrame(animationId);

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

    updateUI();
    fillNextQueue();
    spawnPiece();
    animationId = requestAnimationFrame(gameLoop);
}
