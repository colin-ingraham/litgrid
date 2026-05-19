'use strict';

// ── State ────────────────────────────────────────────────────────────────────
const state = {
    // groups[i].books[j] is either null (empty) or a book object
    groups: [
        { category: '', books: [null, null, null, null] },
        { category: '', books: [null, null, null, null] },
        { category: '', books: [null, null, null, null] },
        { category: '', books: [null, null, null, null] },
    ],
    activeSlot: null,   // { groupIdx, slotIdx } — which slot opened the modal
    usedIds: new Set(), // google_book_ids already placed on the board
};

// ── DOM refs ─────────────────────────────────────────────────────────────────
const searchBackdrop = document.getElementById('search-backdrop');
const searchModal    = document.getElementById('search-modal');
const searchInput    = document.getElementById('search-input');
const searchResults  = document.getElementById('search-results');
const searchHint     = document.getElementById('search-hint');
const searchCloseBtn = document.getElementById('search-close-btn');
const saveBtn        = document.getElementById('save-btn');
const saveStatus     = document.getElementById('save-status');

// ── Boot ─────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    renderAllSlots();
    bindCategoryInputs();
    bindSearchModal();
    bindSaveButton();
});

// ── Render ───────────────────────────────────────────────────────────────────

function renderAllSlots() {
    document.querySelectorAll('.book-slot').forEach(el => {
        const g = parseInt(el.dataset.group);
        const s = parseInt(el.dataset.slot);
        renderSlot(el, g, s);
    });
    updateProgress();
    updateSaveButton();
}

function renderSlot(el, groupIdx, slotIdx) {
    const book = state.groups[groupIdx].books[slotIdx];

    if (!book) {
        // ── Empty ──
        el.className = 'book-slot empty';
        el.innerHTML = `
            <div class="slot-empty-inner">
                <span class="slot-plus">+</span>
                <span class="slot-hint">Add Book</span>
            </div>
        `;
        if (el._slotClickHandler) el.removeEventListener('click', el._slotClickHandler);
        el._slotClickHandler = () => openSearch(groupIdx, slotIdx);
        el.addEventListener('click', el._slotClickHandler);
    } else {
        // ── Filled ──
        el.className = 'book-slot filled';
        el.innerHTML = `
            <button class="slot-clear-btn" aria-label="Remove ${book.title}" data-group="${groupIdx}" data-slot="${slotIdx}">×</button>
            <div class="slot-filled-inner">
                <img
                    class="slot-cover"
                    src="${book.cover}"
                    alt="${book.title}"
                    draggable="false"
                    onerror="this.classList.add('missing')"
                />
                <span class="slot-title">${book.title}</span>
                <span class="slot-author">${book.author}</span>
            </div>
        `;
        el.querySelector('.slot-clear-btn').addEventListener('click', e => {
            e.stopPropagation();
            clearSlot(groupIdx, slotIdx);
        });
    }
}

function getSlotEl(groupIdx, slotIdx) {
    return document.querySelector(`.book-slot[data-group="${groupIdx}"][data-slot="${slotIdx}"]`);
}

// ── Category inputs ───────────────────────────────────────────────────────────

function bindCategoryInputs() {
    document.querySelectorAll('.category-input').forEach(input => {
        const g = parseInt(input.dataset.group);
        input.addEventListener('input', () => {
            state.groups[g].category = input.value;
            updateSaveButton();
        });
    });
}

// ── Progress counters ─────────────────────────────────────────────────────────

function updateProgress() {
    state.groups.forEach((group, i) => {
        const filled = group.books.filter(Boolean).length;
        const el     = document.getElementById(`progress-${i}`);
        if (el) el.textContent = `${filled} / 4`;
    });
}

// ── Save button state ─────────────────────────────────────────────────────────

function updateSaveButton() {
    const allFilled    = state.groups.every(g => g.books.every(Boolean));
    const allNamed     = state.groups.every(g => g.category.trim().length > 0);
    saveBtn.disabled   = !(allFilled && allNamed);
}

// ── Slot clear ────────────────────────────────────────────────────────────────

function clearSlot(groupIdx, slotIdx) {
    const book = state.groups[groupIdx].books[slotIdx];
    if (book) {
        state.usedIds.delete(book.id);
        state.groups[groupIdx].books[slotIdx] = null;
    }
    const el = getSlotEl(groupIdx, slotIdx);
    if (el) renderSlot(el, groupIdx, slotIdx);
    updateProgress();
    updateSaveButton();
}

// ── Search modal ──────────────────────────────────────────────────────────────

function openSearch(groupIdx, slotIdx) {
    const DIFF_NAMES = ['Easy', 'Medium', 'Hard', 'Expert'];
    state.activeSlot = { groupIdx, slotIdx };
    searchHint.textContent = `${DIFF_NAMES[groupIdx]} — Slot ${slotIdx + 1}`;
    searchInput.value = '';
    searchResults.innerHTML = '<p class="search-placeholder">Start typing to search books…</p>';

    searchBackdrop.classList.remove('hidden');
    requestAnimationFrame(() => searchBackdrop.classList.add('visible'));
    setTimeout(() => searchInput.focus(), 50);
}

function closeSearch() {
    const wasActive = state.activeSlot;
    searchBackdrop.classList.remove('visible');
    setTimeout(() => {
        searchBackdrop.classList.add('hidden');
        // Re-render the slot so its click listener is restored
        if (wasActive && !state.groups[wasActive.groupIdx].books[wasActive.slotIdx]) {
            const el = getSlotEl(wasActive.groupIdx, wasActive.slotIdx);
            if (el) renderSlot(el, wasActive.groupIdx, wasActive.slotIdx);
        }
        state.activeSlot = null;
    }, 220);
}

function bindSearchModal() {
    searchCloseBtn.addEventListener('click', closeSearch);

    searchBackdrop.addEventListener('click', e => {
        if (e.target === searchBackdrop) closeSearch();
    });

    searchInput.addEventListener('keydown', e => {
        if (e.key === 'Escape') closeSearch();
    });

    // Debounced search
    let debounceTimer;
    searchInput.addEventListener('input', () => {
        clearTimeout(debounceTimer);
        const q = searchInput.value.trim();
        if (q.length < 2) {
            searchResults.innerHTML = '<p class="search-placeholder">Start typing to search books…</p>';
            return;
        }
        searchResults.innerHTML = '<p class="search-placeholder">Searching…</p>';
        debounceTimer = setTimeout(() => fetchResults(q), 320);
    });
}

async function fetchResults(query) {
    try {
        const url  = `${BOOK_SEARCH_URL}?q=${encodeURIComponent(query)}`;
        const resp = await fetch(url);
        if (!resp.ok) throw new Error('Search failed');
        const books = await resp.json();
        renderResults(books);
    } catch {
        searchResults.innerHTML = '<p class="search-empty">Search failed — please try again.</p>';
    }
}

function renderResults(books) {
    if (!books.length) {
        searchResults.innerHTML = '<p class="search-empty">No results found.</p>';
        return;
    }

    searchResults.innerHTML = '';
    books.forEach(book => {
        const isUsed = state.usedIds.has(book.id);
        const item   = document.createElement('div');
        item.className = `search-result-item${isUsed ? ' used' : ''}`;
        item.innerHTML = `
            <img class="result-cover" src="${book.cover}" alt="${book.title}" onerror="this.src='https://placehold.co/40x58/2d2d2d/888?text=?'" />
            <div class="result-info">
                <p class="result-title">${book.title}</p>
                <p class="result-author">${book.author}</p>
            </div>
            ${isUsed ? '<span class="result-used-label">In use</span>' : ''}
        `;
        if (!isUsed) {
            item.addEventListener('click', () => selectBook(book));
        }
        searchResults.appendChild(item);
    });
}

function selectBook(book) {
    if (!state.activeSlot) return;
    const { groupIdx, slotIdx } = state.activeSlot;

    state.groups[groupIdx].books[slotIdx] = book;
    state.usedIds.add(book.id);

    const el = getSlotEl(groupIdx, slotIdx);
    if (el) renderSlot(el, groupIdx, slotIdx);
    updateProgress();
    updateSaveButton();
    closeSearch();
}

// ── Save ──────────────────────────────────────────────────────────────────────

function bindSaveButton() {
    saveBtn.addEventListener('click', savePuzzle);
}

async function savePuzzle() {
    saveBtn.disabled = true;
    setStatus('saving', 'Saving…');

    const payload = {
        date:   PUZZLE_DATE,
        groups: state.groups.map(g => ({
            category: g.category.trim(),
            books:    g.books.map(b => ({
                id:     b.id,
                title:  b.title,
                author: b.author,
            })),
        })),
    };

    try {
        const resp = await fetch(SAVE_URL, {
            method:  'POST',
            headers: {
                'Content-Type':    'application/json',
                'X-CSRFToken':     CSRF_TOKEN,
            },
            body: JSON.stringify(payload),
        });

        const data = await resp.json();

        if (data.success) {
            setStatus('success', '✓ Saved!');
            setTimeout(() => {
                window.location.href = '/dashboard/';
            }, 900);
        } else {
            setStatus('error', 'Error');
            showError(data.error || 'Something went wrong.');
            saveBtn.disabled = false;
        }
    } catch {
        setStatus('error', 'Error');
        showError('Network error — please try again.');
        saveBtn.disabled = false;
    }
}

function setStatus(type, message) {
    saveStatus.textContent  = message;
    saveStatus.className    = `save-status ${type}`;
}

function showError(message) {
    // Simple inline toast — we can make this nicer later
    const existing = document.querySelector('.editor-error-toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.className = 'editor-error-toast';
    toast.style.cssText = `
        position: fixed; bottom: 28px; left: 50%; transform: translateX(-50%);
        background: #2a1010; border: 1px solid var(--dash-danger); color: var(--dash-danger);
        padding: 12px 24px; border-radius: 8px; font-size: 0.85rem; z-index: 9999;
        box-shadow: 0 8px 24px rgba(0,0,0,0.6); max-width: 440px; text-align: center;
        font-family: var(--font-body);
    `;
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 4500);
}