// Global state
let activeCell = null;
let guessesRemaining = 12; // Start with 12 guesses
let booksSolved = 0;       // Start with 0 solved
const totalBooks = 9;      // Total cells to solve
let isProcessing = false;
let isGameComplete = false;

$(document).ready(function() {
    // --- Selectors ---
    const $gridCells = $('.input-box');
    const $modalBackdrop = $('#modal-backdrop');
    const $bookInput = $('#book-input');
    const $closeButton = $('#modal-close-btn');
    const $modalCoords = $('#modal-coords');
    
    // UI Selectors for Stats
    const $guessesDisplay = $('.stat-value').first(); // Assumes Guesses is the first stat box
    const $solvedDisplay = $('.stat-value').last();   // Assumes Solved is the last stat box

    loadGameState();
    // Initialize UI
    updateStatsUI();

    // --- Helper: Update Stats on Screen ---
    function updateStatsUI() {
        $guessesDisplay.text(guessesRemaining);
        $solvedDisplay.text(`${booksSolved} / ${totalBooks}`);
    }

    const $helpModal = $('#help-modal-backdrop');
    const $helpBtn = $('#help-trigger-btn');
    const $startGameBtn = $('#start-game-btn');

    // 1. Check LocalStorage on Load
    if (!localStorage.getItem('litgrid_tutorial_seen')) {
        showHelpModal();
    }

    // 2. Open Modal via Button
    $helpBtn.on('click', function() {
        showHelpModal();
    });

    // 3. Close Modal ("Let's Play")
    $startGameBtn.on('click', function() {
        // Automatically save that they have seen it so it doesn't annoy them on refresh
        localStorage.setItem('litgrid_tutorial_seen', 'true');
        hideHelpModal();
    });

    function showHelpModal() {
        $helpModal.removeClass('hidden');
        setTimeout(() => {
            $helpModal.addClass('visible');
        }, 10);
    }

    function hideHelpModal() {
        $helpModal.removeClass('visible');
        setTimeout(() => {
            $helpModal.addClass('hidden');
        }, 300);
    }
    // --- Event Handlers ---

    // 1. Open Modal on Cell Click
    $gridCells.on('click', function() {
        if (guessesRemaining <= 0) return; // Prevent clicks if game is over
        if ($(this).hasClass('correct-guess') || $(this).hasClass('solved-correctly')) return;

        activeCell = $(this);
        const row = activeCell.data('row');
        const col = activeCell.data('col');
        
        $modalCoords.text(`Intersection: Row ${row}, Column ${col}`);
        $modalBackdrop.addClass('visible').removeClass('hidden');
        $bookInput.focus();
    });

    // 2. Close Modal
    function closeModal() {
        $modalBackdrop.removeClass('visible');
        setTimeout(() => {
            $modalBackdrop.addClass('hidden');
            $bookInput.val(''); 
            $('#search-results').empty(); 
        }, 300); 
        activeCell = null;
    }

    $closeButton.on('click', closeModal);
    $modalBackdrop.on('click', function(e) {
        if (e.target.id === 'modal-backdrop') {
            closeModal();
        }
    });

    // 3. Book Search (AJAX) - Unchanged
    $bookInput.on('input', function() {
        const query = $(this).val().trim();
        const $resultsContainer = $('#search-results');
        $resultsContainer.empty();

        if (query.length >= 4) {
            $resultsContainer.html('<p style="color:var(--primary-beige); text-align:center; padding: 15px;">Searching...</p>');
            clearTimeout(window.searchTimeout);
            window.searchTimeout = setTimeout(() => {
                $.ajax({
                    url: BOOK_SEARCH_URL,
                    data: { q: query },
                    success: function(data) { renderSearchResults(data); },
                    error: function() {
                        $resultsContainer.html('<p style="color:var(--error-red); text-align:center; padding: 15px;">Error connecting.</p>');
                    }
                });
            }, 300);
        }
    });

    function renderSearchResults(books) {
        const $resultsContainer = $('#search-results');
        $resultsContainer.empty();

        if (!books || books.length === 0) {
            $resultsContainer.html('<p style="color:var(--primary-beige); text-align:center; padding: 15px;">No results found. Try a different title.</p>');
            return;
        }

        // --- STEP 1: Gather all currently placed books ---
        const placedBooks = new Set();
        $('.solved-correctly').each(function() {
            // We can grab the title text we injected into the cell
            const title = $(this).find('.final-book-title').text().trim().toLowerCase();
            if (title) {
                placedBooks.add(title);
            }
        });

        books.forEach(book => {
            // --- STEP 2: Check if this book is already on the board ---
            // We check by Title (normalized to lowercase) because ID might vary slightly between editions
            const isAlreadyUsed = placedBooks.has(book.title.trim().toLowerCase());
            
            const disabledClass = isAlreadyUsed ? 'disabled' : '';
            const statusText = isAlreadyUsed ? '<span style="font-size:0.7em; color:var(--error-red); margin-left:10px;">(ALREADY USED)</span>' : '';

            const resultHtml = `
                <div class="book-result-item ${disabledClass}" 
                     data-book-id="${book.id}" 
                     data-book-title="${book.title}"
                     data-book-author="${book.author}"
                     data-book-cover="${book.cover}"> 
                    <img src="${book.cover}" class="book-cover-thumbnail" alt="Cover" onerror="this.onerror=null;this.src='https://placehold.co/55x80/4a4a4a/ffffff?text=N/A'">
                    <div class="book-info">
                        <p class="book-title-result">
                            ${book.title}
                            ${statusText}
                        </p>
                        <p class="book-author-result">${book.author}</p>
                    </div>
                </div>
            `;
            $resultsContainer.append(resultHtml);
        });

        // Attach click handler ONLY to items that are NOT disabled
        // The CSS 'pointer-events: none' usually handles this, but this is a double-safety.
        $('.book-result-item:not(.disabled)').off('click').on('click', handleBookSelection);
    }

    // 5. Handle Book Selection (Updated for Scoring)
    function handleBookSelection() {
        if (isProcessing) return;
        const $selectedBook = $(this);
        const bookId = $selectedBook.data('book-id');
        const bookTitle = $selectedBook.data('book-title');
        const bookAuthor = $selectedBook.data('book-author');
        const bookCover = $selectedBook.data('book-cover'); 
        
        const csrfToken = $('input[name="csrfmiddlewaretoken"]').val();

        if (activeCell) {
            isProcessing = true;
            $selectedBook.css('opacity', '0.5');
            const row = activeCell.data('row');
            const col = activeCell.data('col');
            
            // --- GAME STATE UPDATE: Deduct Guess ---
            guessesRemaining--;
            updateStatsUI();
            saveGameState();
            
            $.ajax({
                url: BOOK_VALIDATE_URL,
                type: 'POST',
                headers: { 'X-CSRFToken': csrfToken, 'Content-Type': 'application/json' },
                data: JSON.stringify({ book_id: bookId, row: row, col: col }),
                success: function(response) {
                    if (response.is_correct) {
                        markCellCorrect(activeCell, response.book_title || bookTitle, bookAuthor, bookCover);
                    } else {
                        markCellIncorrect(activeCell, response.book_title || bookTitle);
                    }
                    checkGameOver(); // Check if they ran out of guesses
                },
                error: function(xhr, status, error) {
                    console.error("Error:", error);
                    markCellIncorrect(activeCell, bookTitle + ' (Error)');
                    checkGameOver();
                },
                complete: function() {
                    closeModal();
                    isProcessing = false;
                }
            });
        }
    }

    // 6. UI Update Functions
    function markCellCorrect($cell, title, author, coverUrl, shouldSave= true) {
        // --- GAME STATE UPDATE: Increment Solved ---
        if ($cell.hasClass('solved-correctly')) return;
        if (shouldSave) {
            booksSolved++;
            updateStatsUI();
        }

        $cell.empty();
        $cell.removeClass('correct-guess').off('click'); 
        $cell.addClass('solved-correctly');

        const bookHtml = `
            <div class="book-result-final">
                <img src="${coverUrl}" class="final-book-cover" alt="Cover of ${title}" onerror="this.onerror=null;this.src='https://placehold.co/150x220/101010/C9A86A?text=No+Cover'">
                <p class="final-book-title">${title}</p>
                <p class="final-book-author">${author}</p>
            </div>
        `;
        $cell.append(bookHtml);

        if (shouldSave) {
            saveGameState();
        }
    }

    function markCellIncorrect($cell, title) {
        $cell.empty();
        $cell.append(`<div class="book-result"><p class="book-title">${title}</p></div>`);
        $cell.addClass('incorrect-guess').removeClass('correct-guess').removeClass('solved-correctly');
        
        setTimeout(() => {
            $cell.empty();
            $cell.removeClass('incorrect-guess');
        }, 2000); 
    }

    const $giveUpBtn = $('#give-up-btn');

    $giveUpBtn.on('click', function() {
        if (!confirm("Are you sure you want to give up? This will end the game.")) {
            return;
        }

        // 1. Set values to fail state
        guessesRemaining = 0;
        
        // 2. Update Stats Visuals
        updateStatsUI();

        // 3. Trigger the centralized Game Over logic
        checkGameOver(); // This sets isGameComplete = true and updates buttons

        // 4. Save
        saveGameState();
    });


    // --- End Screen Logic ---
    const $endModal = $('#end-modal-backdrop');
    const $endTitle = $('#end-title');
    const $summaryGrid = $('#end-grid-summary');
    const $backToPuzzleBtn = $('#back-to-puzzle-btn');
    const $closeEndBtn = $('#close-end-modal-btn');
    const $countdown = $('#countdown-timer');

    function showEndScreen(isVictory) {
        // 1. Set Title
        $endTitle.text(isVictory ? "Congratulations!" : "Thanks for playing!");

        // 2. Generate Visual Grid Summary
        $summaryGrid.empty();
        
        // Loop through rows 1-3 and cols 1-3
        for (let r = 1; r <= 3; r++) {
            for (let c = 1; c <= 3; c++) {
                // Find the cell in the actual game board
                const $cell = $(`.input-box[data-row="${r}"][data-col="${c}"]`);
                const isSolved = $cell.hasClass('solved-correctly');
                
                // Create the summary square
                const $square = $('<div>').addClass('summary-cell');
                if (isSolved) {
                    $square.addClass('summary-correct');
                } else {
                    $square.addClass('summary-incorrect');
                }
                $summaryGrid.append($square);
            }
        }

        // 3. Start Countdown
        startCountdown();

        // 4. Show Modal
        $endModal.removeClass('hidden').addClass('visible');
    }

    // --- Countdown Timer ---
    let timerInterval;
    function startCountdown() {
        function updateTimer() {
            const now = new Date();
            // Calculate next midnight
            const tomorrow = new Date(now);
            tomorrow.setHours(24, 0, 0, 0);
            
            const diff = tomorrow - now; // Difference in milliseconds
            
            // Convert to HH:MM:SS
            const hours = Math.floor((diff / (1000 * 60 * 60)) % 24);
            const minutes = Math.floor((diff / (1000 * 60)) % 60);
            const seconds = Math.floor((diff / 1000) % 60);

            // Format with leading zeros
            const hStr = hours.toString().padStart(2, '0');
            const mStr = minutes.toString().padStart(2, '0');
            const sStr = seconds.toString().padStart(2, '0');

            $countdown.text(`${hStr}:${hStr}:${sStr}`); // Bug fix: hStr, mStr, sStr
            $countdown.text(`${hStr}:${mStr}:${sStr}`);
        }

        updateTimer(); // Run once immediately
        clearInterval(timerInterval); // Clear any existing timer
        timerInterval = setInterval(updateTimer, 1000);
    }

    // --- End Modal Button Handlers ---
    
    // "Back to Puzzle" & "X" button both just hide the modal
    function hideEndModal() {
        $endModal.removeClass('visible');
        setTimeout(() => {
            $endModal.addClass('hidden');
        }, 300);
    }

    $backToPuzzleBtn.on('click', hideEndModal);
    $closeEndBtn.on('click', hideEndModal);
    
    // Optional: Share Button (Visual feedback only for MVP)
    $('#share-btn').on('click', function() {
        const originalText = $(this).text();
        $(this).text("COPIED!");
        setTimeout(() => {
            $(this).html('SHARE <span class="share-icon">➤</span>');
        }, 2000);
    });

    const $postGameControls = $('#post-game-controls');
    const $seeResultsBtn = $('#see-results-btn');
    const $archivesBtn = $('#archives-btn');

    // --- Helper: Check Game Over ---
    function checkGameOver() {
        const isVictory = (booksSolved >= totalBooks);
        const isDefeat = (guessesRemaining <= 0);

        if (isVictory || isDefeat) {
            // 1. Hide the "Give Up" button permanently
            $giveUpBtn.addClass('hidden'); // Ensure you have .hidden { display: none !important; } in CSS
            
            // 2. Show the Post-Game Controls
            $postGameControls.removeClass('hidden');

            // 3. Trigger the Modal
            showEndScreen(isVictory);
        }
    }

    // --- Post-Game Button Handlers ---
    
    // "See Results" simply re-opens the modal
    $seeResultsBtn.on('click', function() {
        const isVictory = (booksSolved === totalBooks);
        showEndScreen(isVictory);
    });

    // "Archives" (Placeholder for now)
    $archivesBtn.on('click', function() {
        alert("The Archives are coming soon! Stay tuned.");
    });

    // ==========================================
    // --- LOCAL STORAGE (SAVE/LOAD) LOGIC ---
    // ==========================================

    function saveGameState() {
        const gridState = [];

        // 1. Scrape the grid
        $('.input-box').each(function() {
            const $cell = $(this);
            const row = $cell.data('row');
            const col = $cell.data('col');
            let status = 'EMPTY';
            let bookData = null;

            if ($cell.hasClass('solved-correctly')) {
                status = 'SOLVED';
                // Grab data from the specific HTML structure we built
                bookData = {
                    title: $cell.find('.final-book-title').text(),
                    author: $cell.find('.final-book-author').text(),
                    cover: $cell.find('.final-book-cover').attr('src')
                };
            }

            gridState.push({
                row: row,
                col: col,
                status: status,
                bookData: bookData
            });
        });

        // 2. Create the Save Object
        const gameState = {
            date: new Date().toDateString(), // e.g., "Thu Dec 11 2025"
            guessesRemaining: guessesRemaining,
            booksSolved: booksSolved,
            isGameComplete: isGameComplete,
            grid: gridState
        };

        // 3. Write to Local Storage
        localStorage.setItem('litgrid_save_data', JSON.stringify(gameState));
        // console.log("Game Saved:", gameState); // Debug
    }

    function loadGameState() {
        const saveString = localStorage.getItem('litgrid_save_data');
        if (!saveString) return; 

        try {
            const save = JSON.parse(saveString);
            const today = new Date().toDateString();

            if (save.date !== today) {
                console.log("Old save found. Clearing.");
                localStorage.removeItem('litgrid_save_data');
                return;
            }

            console.log("Loading Save Game...");

            // 1. Restore Variables
            guessesRemaining = parseInt(save.guessesRemaining);
            booksSolved = parseInt(save.booksSolved);
            isGameComplete = save.isGameComplete; // <--- LOAD THE FLAG

            // 2. Restore Grid Cells
            if (save.grid) {
                save.grid.forEach(cellData => {
                    if (cellData.status === 'SOLVED') {
                        const $cell = $(`.input-box[data-row="${cellData.row}"][data-col="${cellData.col}"]`);
                        // Pass false to avoid triggering saveGameState during load
                        markCellCorrect($cell, cellData.bookData.title, cellData.bookData.author, cellData.bookData.cover, false);
                    }
                });
            }

            // 3. FORCE UI STATE BASED ON FLAG
            if (isGameComplete) {
                console.log("Game loaded in COMPLETED STATE.");
                
                // 1. Kill the Give Up Button
                $('#give-up-btn').addClass('hidden'); 
                
                // 2. Show the Results Button
                $('#post-game-controls').removeClass('hidden');
                
                // 3. Ensure input interactions are dead (optional extra safety)
                $('.input-box').off('click');
            }

            updateStatsUI();

        } catch (e) {
            console.error("Error loading save game:", e);
        }
    }

    $('body').append(`
        <div style="position: fixed; bottom: 10px; right: 10px; z-index: 10000; opacity: 0.8;">
            <button id="dev-reset-btn" style="background: red; color: white; border: 1px solid white; padding: 5px 10px; cursor: pointer; font-weight: bold;">
                ⚠️ RESET GAME
            </button>
        </div>
    `);
    $('#dev-reset-btn').on('click', function() {
        if(confirm("This will wipe your save and reload. Are you sure?")) {
            // Remove the ACTUAL key you are using in saveGameState()
            localStorage.removeItem('litgrid_save_data');
            
            // Reload the page
            window.location.reload();
        }
    });

    function checkGameOver() {
        const isVictory = (booksSolved >= totalBooks);
        const isDefeat = (guessesRemaining <= 0);

        if (isVictory || isDefeat) {
            // 1. Set the Flag
            isGameComplete = true; 

            // 2. UI: Hide Give Up, Show Post-Game
            $('#give-up-btn').addClass('hidden'); 
            $('#post-game-controls').removeClass('hidden');
            
            // 3. Disable further interaction
            $('.input-box').off('click');

            // 4. IMPORTANT: Save immediately so the "isGameComplete" flag persists on refresh
            saveGameState();

            // 5. Trigger Modal (only if it's not already visible)
            if (!$('#end-modal-backdrop').hasClass('visible')) {
                showEndScreen(isVictory);
            }
        }
    }

});