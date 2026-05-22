'use strict';

// ── State ─────────────────────────────────────────────────────────────────────
const state = {
    groups: [
        { category: '', books: [null, null, null, null] },
        { category: '', books: [null, null, null, null] },
        { category: '', books: [null, null, null, null] },
        { category: '', books: [null, null, null, null] },
    ],
    activeSlot: null,
    usedIds:    new Set(),
    draftId:    INITIAL_DRAFT_ID,   // null for new, integer for existing draft
};

// ── DOM refs ──────────────────────────────────────────────────────────────────
const searchBackdrop = document.getElementById('search-backdrop');
const searchInput    = document.getElementById('search-input');
const searchResults  = document.getElementById('search-results');
const searchHint     = document.getElementById('search-hint');
const searchCloseBtn = document.getElementById('search-close-btn');
const saveBtn        = document.getElementById('save-btn');
const saveStatus     = document.getElementById('save-status');

// ── Boot ──────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    if (INITIAL_DRAFT_DATA) {
        loadDraftData(INITIAL_DRAFT_DATA);
    }
    renderAllSlots();
    bindCategoryInputs();
    bindReorderButtons();
    bindSearchModal();
    bindSaveButton();
});

// ── Load draft data from server ───────────────────────────────────────────────

function loadDraftData(data) {
    const groups = data.groups || [];
    groups.forEach((g, i) => {
        if (!state.groups[i]) return;
        state.groups[i].category = g.category || '';
        state.groups[i].books    = (g.books || [null, null, null, null]).map(b => b || null);
    });
    // Rebuild usedIds
    state.usedIds = new Set(
        state.groups.flatMap(g => g.books.filter(Boolean).map(b => b.id))
    );
    // Populate category inputs
    document.querySelectorAll('.category-input').forEach(input => {
        const g = parseInt(input.dataset.group);
        input.value = state.groups[g].category;
    });
}

// ── Server auto-save (draft) ──────────────────────────────────────────────────

let draftSaveTimer = null;
let draftSaveInFlight = false;  // prevents duplicate creates on fast typing
let draftSavePending  = false;  // queues a save that arrived while one was in-flight

function scheduleDraftSave() {
    clearTimeout(draftSaveTimer);
    draftSaveTimer = setTimeout(persistDraft, 800);
}

async function persistDraft() {
    // If a save is already running, mark that another is needed and bail
    if (draftSaveInFlight) {
        draftSavePending = true;
        return;
    }

    draftSaveInFlight = true;
    draftSavePending  = false;

    const payload = {
        draft_id: state.draftId,
        data: {
            groups: state.groups.map(g => ({
                category: g.category,
                books:    g.books,
            })),
        },
    };

    try {
        const resp = await fetch(DRAFT_SAVE_URL, {
            method:  'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF_TOKEN },
            body:    JSON.stringify(payload),
        });
        const result = await resp.json();
        if (result.success) {
            if (!state.draftId) {
                state.draftId = result.draft_id;
            }
            setStatus('saved', '✓ Draft saved');
            setTimeout(() => {
                if (saveStatus.textContent === '✓ Draft saved') setStatus('', '');
            }, 2000);
        }
    } catch {
        // Silent — draft save failure shouldn't alarm the user mid-edit
    } finally {
        draftSaveInFlight = false;
        // If something changed while we were saving, flush it now
        if (draftSavePending) {
            draftSavePending = false;
            persistDraft();
        }
    }
}

// ── Render ────────────────────────────────────────────────────────────────────

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

// ── Reorder groups ───────────────────────────────────────────────────────────

function swapGroups(idxA, idxB) {
    // Swap the state content (category + books)
    const tmp = { ...state.groups[idxA] };
    state.groups[idxA] = { ...state.groups[idxB] };
    state.groups[idxB] = tmp;

    // Re-render both panels' slots and category inputs
    [idxA, idxB].forEach(g => {
        // Update category input value
        const input = document.querySelector(`.category-input[data-group="${g}"]`);
        if (input) input.value = state.groups[g].category;

        // Re-render all 4 slots
        for (let s = 0; s < 4; s++) {
            const el = getSlotEl(g, s);
            if (el) renderSlot(el, g, s);
        }
    });

    updateProgress();
    updateSaveButton();
    scheduleDraftSave();
}

function bindReorderButtons() {
    document.querySelectorAll('.reorder-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const g     = parseInt(btn.dataset.group);
            const isUp  = btn.classList.contains('reorder-up');
            const other = isUp ? g - 1 : g + 1;
            if (other < 0 || other > 3) return;
            swapGroups(g, other);
        });
    });
}

// ── Category inputs ───────────────────────────────────────────────────────────

function bindCategoryInputs() {
    document.querySelectorAll('.category-input').forEach(input => {
        const g = parseInt(input.dataset.group);
        input.addEventListener('input', () => {
            state.groups[g].category = input.value;
            scheduleDraftSave();
            updateSaveButton();
        });
    });
}

// ── Progress ──────────────────────────────────────────────────────────────────

function updateProgress() {
    state.groups.forEach((group, i) => {
        const filled = group.books.filter(Boolean).length;
        const el     = document.getElementById(`progress-${i}`);
        if (el) el.textContent = `${filled} / 4`;
    });
}

// ── Save button ───────────────────────────────────────────────────────────────

function updateSaveButton() {
    const allFilled  = state.groups.every(g => g.books.every(Boolean));
    const allNamed   = state.groups.every(g => g.category.trim().length > 0);
    saveBtn.disabled = !(allFilled && allNamed);
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
    scheduleDraftSave();
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
        const resp  = await fetch(`${BOOK_SEARCH_URL}?q=${encodeURIComponent(query)}`);
        if (!resp.ok) throw new Error();
        renderResults(await resp.json());
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
        if (!isUsed) item.addEventListener('click', () => selectBook(book));
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
    scheduleDraftSave();
    closeSearch();
}

// ── Publish ───────────────────────────────────────────────────────────────────

function bindSaveButton() {
    saveBtn.addEventListener('click', publishPuzzle);
}

async function publishPuzzle() {
    saveBtn.disabled = true;
    setStatus('saving', 'Publishing…');

    const payload = {
        draft_id: state.draftId,
        groups:   state.groups.map(g => ({
            category: g.category.trim(),
            books:    g.books.map(b => ({ id: b.id, title: b.title, author: b.author })),
        })),
    };

    try {
        const resp = await fetch(SAVE_URL, {
            method:  'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF_TOKEN },
            body:    JSON.stringify(payload),
        });
        const data = await resp.json();

        if (data.success) {
            setStatus('success', '✓ Published!');
            setTimeout(() => {
                window.location.href = `/connections/${data.puzzle_number}/`;
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
    saveStatus.textContent = message;
    saveStatus.className   = `save-status ${type}`;
}

function showError(message) {
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