'use strict';

// Difficulty index → color (matches template difficulty values 1-4)
const DIFF_COLORS = ['#e8c84a', '#6aaa64', '#4a90d9', '#9b59b6'];
const DIFF_EMOJIS = ['🟡', '🟢', '🔵', '🟣'];

// --- Game state ---
let tiles = [];            // [{id, title, author, groupIndex}, ...]
let selected = new Set();  // Set of tile IDs currently selected
let solvedGroups = new Set();       // groupIndex values solved by any means
let playerSolvedGroups = new Set(); // groupIndex values the player guessed correctly
let mistakes = 4;
let isGameOver = false;
let countdownInterval = null;

// --- Boot ---

document.addEventListener('DOMContentLoaded', () => {
    buildTiles();
    shuffleArray(tiles);
    renderGrid();
    renderMistakes();
    bindControls();
    checkFirstVisit();
});

function buildTiles() {
    PUZZLE_DATA.groups.forEach((group, gIdx) => {
        group.books.forEach((book, bIdx) => {
            tiles.push({
                id: `${gIdx}_${bIdx}`,
                title: book.title,
                author: book.author,
                groupIndex: gIdx,
            });
        });
    });
}

function shuffleArray(arr) {
    for (let i = arr.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [arr[i], arr[j]] = [arr[j], arr[i]];
    }
}

// --- Render ---

function renderGrid() {
    const grid = document.getElementById('connections-grid');
    grid.innerHTML = '';

    tiles
        .filter(t => !solvedGroups.has(t.groupIndex))
        .forEach(tile => {
            const el = document.createElement('div');
            el.className = 'connection-tile';
            if (selected.has(tile.id)) el.classList.add('selected');
            el.dataset.id = tile.id;
            el.innerHTML = `
                <span class="tile-title">${tile.title}</span>
                <span class="tile-author">${tile.author}</span>
            `;
            el.addEventListener('click', () => onTileClick(tile.id));
            grid.appendChild(el);
        });

    updateControls();
}

function renderMistakes() {
    document.querySelectorAll('.mistake-pip').forEach((pip, idx) => {
        pip.classList.toggle('used', idx >= mistakes);
    });
}

function updateControls() {
    document.getElementById('submit-btn').disabled = selected.size !== 4;
    document.getElementById('deselect-btn').disabled = selected.size === 0;
}

// --- Tile interaction ---

function onTileClick(id) {
    if (isGameOver) return;
    if (selected.has(id)) {
        selected.delete(id);
    } else if (selected.size < 4) {
        selected.add(id);
    }
    renderGrid();
}

// --- Controls ---

function bindControls() {
    document.getElementById('shuffle-btn').addEventListener('click', onShuffle);

    document.getElementById('deselect-btn').addEventListener('click', () => {
        selected.clear();
        renderGrid();
    });

    document.getElementById('submit-btn').addEventListener('click', onSubmit);

    // Help modal
    document.getElementById('help-trigger-btn').addEventListener('click', showHelp);
    document.getElementById('start-game-btn').addEventListener('click', hideHelp);
    document.getElementById('help-modal-backdrop').addEventListener('click', e => {
        if (e.target.id === 'help-modal-backdrop') hideHelp();
    });

    // End modal
    document.getElementById('close-end-modal-btn').addEventListener('click', hideEndModal);
    document.getElementById('back-to-puzzle-btn').addEventListener('click', hideEndModal);
    document.getElementById('share-btn').addEventListener('click', shareResult);
    document.getElementById('end-modal-backdrop').addEventListener('click', e => {
        if (e.target.id === 'end-modal-backdrop') hideEndModal();
    });
}

function onShuffle() {
    if (isGameOver) return;
    // Shuffle only the unsolved portion, keep solved tiles out of the render anyway
    const unsolved = tiles.filter(t => !solvedGroups.has(t.groupIndex));
    shuffleArray(unsolved);
    let ui = 0;
    tiles = tiles.map(t => {
        if (solvedGroups.has(t.groupIndex)) return t;
        return unsolved[ui++];
    });
    renderGrid();
}

// --- Submit logic ---

function onSubmit() {
    if (selected.size !== 4 || isGameOver) return;

    const selectedTiles = Array.from(selected).map(id => tiles.find(t => t.id === id));
    const groupIndices = selectedTiles.map(t => t.groupIndex);
    const allSame = groupIndices.every(g => g === groupIndices[0]);

    if (allSame) {
        const groupIdx = groupIndices[0];
        playerSolvedGroups.add(groupIdx);
        solvedGroups.add(groupIdx);
        selected.clear();
        revealSolvedGroup(groupIdx);
        renderGrid();

        if (solvedGroups.size === PUZZLE_DATA.groups.length) {
            setTimeout(() => gameOver(true), 500);
        }
    } else {
        // Check "one away"
        const counts = {};
        groupIndices.forEach(g => { counts[g] = (counts[g] || 0) + 1; });
        if (Math.max(...Object.values(counts)) === 3) {
            showToast('One away...');
        }

        // Shake the selected tiles
        document.querySelectorAll('.connection-tile.selected').forEach(el => {
            el.classList.add('shake');
            el.addEventListener('animationend', () => el.classList.remove('shake'), { once: true });
        });

        mistakes--;
        renderMistakes();

        setTimeout(() => {
            selected.clear();
            renderGrid();
            if (mistakes <= 0) {
                setTimeout(() => gameOver(false), 500);
            }
        }, 580);
    }
}

// --- Group reveal ---

function revealSolvedGroup(groupIdx) {
    const group = PUZZLE_DATA.groups[groupIdx];
    const container = document.getElementById('solved-groups-container');

    const row = document.createElement('div');
    row.className = 'solved-group-row';
    row.style.backgroundColor = DIFF_COLORS[group.difficulty - 1];
    row.innerHTML = `
        <div class="solved-group-category">${group.category}</div>
        <div class="solved-group-books">${group.books.map(b => b.title).join(' · ')}</div>
    `;
    container.appendChild(row);
}

// --- Game over ---

function gameOver(won) {
    isGameOver = true;

    if (!won) {
        // Reveal any unsolved groups
        PUZZLE_DATA.groups.forEach((_, idx) => {
            if (!solvedGroups.has(idx)) {
                solvedGroups.add(idx);
                revealSolvedGroup(idx);
            }
        });
        renderGrid();
    }

    setTimeout(() => {
        document.getElementById('end-title').textContent = won ? 'Well Read!' : 'Better Luck Next Time';
        buildEndSummary();
        const backdrop = document.getElementById('end-modal-backdrop');
        backdrop.classList.remove('hidden');
        requestAnimationFrame(() => backdrop.classList.add('visible'));
        startCountdown();
    }, won ? 500 : 1000);
}

function buildEndSummary() {
    const container = document.getElementById('end-group-summary');
    container.innerHTML = '';

    PUZZLE_DATA.groups.forEach((group, idx) => {
        const solvedByPlayer = playerSolvedGroups.has(idx);
        const row = document.createElement('div');
        row.className = 'end-summary-row' + (solvedByPlayer ? '' : ' not-solved');
        row.style.backgroundColor = DIFF_COLORS[group.difficulty - 1];
        row.innerHTML = `<span class="end-summary-category">${group.category}</span>`;
        container.appendChild(row);
    });
}

function hideEndModal() {
    const backdrop = document.getElementById('end-modal-backdrop');
    backdrop.classList.remove('visible');
    setTimeout(() => backdrop.classList.add('hidden'), 300);
    if (countdownInterval) {
        clearInterval(countdownInterval);
        countdownInterval = null;
    }
}

// --- Help modal ---

function checkFirstVisit() {
    if (!localStorage.getItem('connections_help_seen')) {
        showHelp();
        localStorage.setItem('connections_help_seen', 'true');
    }
}

function showHelp() {
    const backdrop = document.getElementById('help-modal-backdrop');
    backdrop.classList.remove('hidden');
    requestAnimationFrame(() => backdrop.classList.add('visible'));
}

function hideHelp() {
    const backdrop = document.getElementById('help-modal-backdrop');
    backdrop.classList.remove('visible');
    setTimeout(() => backdrop.classList.add('hidden'), 300);
}

// --- Toast ---

function showToast(message) {
    document.querySelector('.toast')?.remove();
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 1800);
}

// --- Countdown ---

function startCountdown() {
    const el = document.getElementById('countdown-timer');
    if (!el) return;

    function tick() {
        const now = new Date();
        const midnight = new Date(now);
        midnight.setHours(24, 0, 0, 0);
        const diff = midnight - now;
        const h = String(Math.floor(diff / 3600000)).padStart(2, '0');
        const m = String(Math.floor((diff % 3600000) / 60000)).padStart(2, '0');
        const s = String(Math.floor((diff % 60000) / 1000)).padStart(2, '0');
        el.textContent = `${h}:${m}:${s}`;
    }

    tick();
    countdownInterval = setInterval(tick, 1000);
}

// --- Share ---

function shareResult() {
    const lines = PUZZLE_DATA.groups.map((group, idx) => {
        const emoji = DIFF_EMOJIS[group.difficulty - 1];
        const check = playerSolvedGroups.has(idx) ? '✅' : '❌';
        return `${emoji} ${check} ${group.category}`;
    });

    const text = [
        'Litgrid: Connections',
        `📅 ${DISPLAY_DATE}`,
        `Mistakes: ${4 - mistakes}/4`,
        '',
        ...lines,
    ].join('\n');

    if (navigator.clipboard) {
        navigator.clipboard.writeText(text).then(() => showToast('Copied to clipboard!'));
    } else {
        showToast('Result copied!');
    }
}
