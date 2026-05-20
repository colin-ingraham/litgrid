'use strict';

// Guard: nothing to do if no puzzle was loaded
if (!PUZZLE_DATA) {
    console.warn('No puzzle data — game inactive.');
}

const DIFF_COLORS = ['#e8c84a', '#6aaa64', '#4a90d9', '#9b59b6'];
const DIFF_EMOJIS = ['🟡', '🟢', '🔵', '🟣'];

// --- Game state ---
let tiles = [];
let selected = new Set();
let solvedGroups = new Set();
let playerSolvedGroups = new Set();
let mistakes = 4;
let isGameOver = false;

// --- Boot ---
document.addEventListener('DOMContentLoaded', () => {
    if (!PUZZLE_DATA) return;

    buildTiles();
    shuffleArray(tiles);
    renderGrid();
    renderMistakes();
    bindControls();
    checkFirstVisit();
    buildArchiveList();
});

function buildTiles() {
    PUZZLE_DATA.groups.forEach((group, gIdx) => {
        group.books.forEach((book, bIdx) => {
            tiles.push({
                id:         `${gIdx}_${bIdx}`,
                title:      book.title,
                author:     book.author,
                cover:      book.cover || '',
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
                <div class="tile-inner">
                    <img
                        class="tile-cover"
                        src="${tile.cover}"
                        alt="${tile.title}"
                        onerror="this.classList.add('cover-error')"
                        draggable="false"
                    />
                    <span class="tile-title">${tile.title}</span>
                    <span class="tile-author">${tile.author}</span>
                </div>
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
    document.getElementById('submit-btn').disabled   = selected.size !== 4;
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

    // Archive modal
    const archiveBtn = document.getElementById('archive-trigger-btn');
    if (archiveBtn) {
        archiveBtn.addEventListener('click', showArchive);
        document.getElementById('close-archive-btn').addEventListener('click', hideArchive);
        document.getElementById('archive-modal-backdrop').addEventListener('click', e => {
            if (e.target.id === 'archive-modal-backdrop') hideArchive();
        });
    }

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
    const unsolved = tiles.filter(t => !solvedGroups.has(t.groupIndex));
    shuffleArray(unsolved);
    let ui = 0;
    tiles = tiles.map(t => {
        if (solvedGroups.has(t.groupIndex)) return t;
        return unsolved[ui++];
    });
    renderGrid();
}

// --- Submit ---
function onSubmit() {
    if (selected.size !== 4 || isGameOver) return;

    const selectedTiles = Array.from(selected).map(id => tiles.find(t => t.id === id));
    const groupIndices  = selectedTiles.map(t => t.groupIndex);
    const allSame       = groupIndices.every(g => g === groupIndices[0]);

    if (allSame) {
        const groupIdx    = groupIndices[0];
        const correctEls  = Array.from(
            document.querySelectorAll('.connection-tile.selected')
        );

        // Staggered bounce + flash, then reveal
        correctEls.forEach((el, i) => {
            setTimeout(() => {
                el.classList.add('bounce', 'correct-flash');
                el.addEventListener('animationend', () => {
                    el.classList.remove('bounce', 'correct-flash');
                }, { once: true });
            }, i * 80);
        });

        const revealDelay = 80 * correctEls.length + 420;
        setTimeout(() => {
            playerSolvedGroups.add(groupIdx);
            solvedGroups.add(groupIdx);
            selected.clear();
            revealSolvedGroup(groupIdx);
            renderGrid();
            if (solvedGroups.size === PUZZLE_DATA.groups.length) {
                setTimeout(() => gameOver(true), 500);
            }
        }, revealDelay);
    } else {
        const counts = {};
        groupIndices.forEach(g => { counts[g] = (counts[g] || 0) + 1; });
        if (Math.max(...Object.values(counts)) === 3) showToast('One away...');

        document.querySelectorAll('.connection-tile.selected').forEach(el => {
            el.classList.add('shake');
            el.addEventListener('animationend', () => el.classList.remove('shake'), { once: true });
        });

        mistakes--;
        renderMistakes();

        setTimeout(() => {
            selected.clear();
            renderGrid();
            if (mistakes <= 0) setTimeout(() => gameOver(false), 500);
        }, 580);
    }
}

// --- Group reveal ---
function revealSolvedGroup(groupIdx) {
    const group     = PUZZLE_DATA.groups[groupIdx];
    const container = document.getElementById('solved-groups-container');
    const books     = group.books;

    // Split 4 books: left pair [0,1], right pair [2,3]
    const coverImg = (book) =>
        `<img class="solved-cover"
              src="${book.cover}"
              alt="${book.title}"
              title="${book.title}"
              onerror="this.classList.add('missing')"
              draggable="false" />`;

    const row = document.createElement('div');
    row.className = 'solved-group-row';
    row.style.backgroundColor = DIFF_COLORS[group.difficulty - 1];
    row.innerHTML = `
        <div class="solved-group-left-covers">
            ${coverImg(books[0])}
            ${coverImg(books[1])}
        </div>
        <div class="solved-group-center">
            <span class="solved-group-category">${group.category}</span>
            <span class="solved-group-books">${books.map(b => b.title).join(' · ')}</span>
        </div>
        <div class="solved-group-right-covers">
            ${coverImg(books[2])}
            ${coverImg(books[3])}
        </div>
    `;
    container.appendChild(row);
}

// --- Game over ---
function gameOver(won) {
    isGameOver = true;
    if (!won) {
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
        buildOtherPuzzleLinks();
        const backdrop = document.getElementById('end-modal-backdrop');
        backdrop.classList.remove('hidden');
        requestAnimationFrame(() => backdrop.classList.add('visible'));
    }, won ? 500 : 1000);
}

function buildEndSummary() {
    const container = document.getElementById('end-group-summary');
    container.innerHTML = '';
    PUZZLE_DATA.groups.forEach((group, idx) => {
        const solved = playerSolvedGroups.has(idx);
        const row    = document.createElement('div');
        row.className = `end-summary-row${solved ? '' : ' not-solved'}`;
        row.style.backgroundColor = DIFF_COLORS[group.difficulty - 1];
        row.innerHTML = `<span class="end-summary-category">${group.category}</span>`;
        container.appendChild(row);
    });
}

function buildOtherPuzzleLinks() {
    const container = document.getElementById('other-puzzles-links');
    if (!container || !ALL_PUZZLES.length) return;

    const others = ALL_PUZZLES.filter(p => p.id !== CURRENT_PUZZLE_ID);
    if (!others.length) {
        container.innerHTML = '<span style="font-size:0.8rem; opacity:0.5;">No other puzzles yet.</span>';
        return;
    }
    container.innerHTML = others.map(p =>
        `<a href="/connections/${p.id}/" class="other-puzzle-link">Puzzle #${p.rank}</a>`
    ).join('');
}

function hideEndModal() {
    const backdrop = document.getElementById('end-modal-backdrop');
    backdrop.classList.remove('visible');
    setTimeout(() => backdrop.classList.add('hidden'), 300);
}

// --- Archive modal ---
function buildArchiveList() {
    const container = document.getElementById('archive-list-container');
    if (!container || !ALL_PUZZLES.length) return;

    container.innerHTML = ALL_PUZZLES.map(p => {
        const isCurrent = p.id === CURRENT_PUZZLE_ID;
        return `
            <a href="/connections/${p.id}/" class="archive-item${isCurrent ? ' archive-item--current' : ''}">
                <span class="archive-date">Puzzle #${p.rank}</span>
                ${isCurrent ? '<span class="archive-status">Current</span>' : ''}
            </a>
        `;
    }).join('');
}

function showArchive() {
    const backdrop = document.getElementById('archive-modal-backdrop');
    backdrop.classList.remove('hidden');
    requestAnimationFrame(() => backdrop.classList.add('visible'));
}

function hideArchive() {
    const backdrop = document.getElementById('archive-modal-backdrop');
    backdrop.classList.remove('visible');
    setTimeout(() => backdrop.classList.add('hidden'), 300);
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
    toast.className   = 'toast';
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 1800);
}

// --- Share ---
function shareResult() {
    const lines = PUZZLE_DATA.groups.map((group, idx) => {
        const emoji = DIFF_EMOJIS[group.difficulty - 1];
        const check = playerSolvedGroups.has(idx) ? '✅' : '❌';
        return `${emoji} ${check} ${group.category}`;
    });
    const text = [
        `Litgrid: Connections — Puzzle #${CURRENT_RANK}`,
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