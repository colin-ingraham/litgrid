// Global state to track which cell was clicked
let activeCell = null;

$(document).ready(function() {
    // --- Selectors ---
    const $gridCells = $('.input-box');
    const $modalBackdrop = $('#modal-backdrop');
    const $bookInput = $('#book-input');
    const $closeButton = $('#modal-close-btn');
    const $modalCoords = $('#modal-coords');

    // --- Event Handlers ---

    // 1. Open Modal on Cell Click
    $gridCells.on('click', function() {
        // Prevent opening if cell is already correctly guessed
        if ($(this).hasClass('correct-guess')) return;

        activeCell = $(this);
        const row = activeCell.data('row');
        const col = activeCell.data('col');
        
        // Update modal header to show coordinates
        $modalCoords.text(`Intersection: Row ${row}, Column ${col}`);

        // Display modal with transition classes
        $modalBackdrop.addClass('visible').removeClass('hidden');
        $bookInput.focus();
    });

    // 2. Close Modal
    function closeModal() {
        $modalBackdrop.removeClass('visible');
        // Give time for fade-out animation before hiding completely
        setTimeout(() => {
            $modalBackdrop.addClass('hidden');
            $bookInput.val(''); // Clear search input
            $('#search-results').empty(); // Clear previous results
        }, 300); 
        activeCell = null;
    }

    $closeButton.on('click', closeModal);

    // Close modal if user clicks outside the container
    $modalBackdrop.on('click', function(e) {
        if (e.target.id === 'modal-backdrop') {
            closeModal();
        }
    });

    // 3. Book Search (AJAX Call to Django Backend)
    $bookInput.on('input', function() {
        const query = $(this).val().trim();
        const $resultsContainer = $('#search-results');
        $resultsContainer.empty();

        // Enforce minimum query length to 4 characters
        if (query.length >= 4) {
            $resultsContainer.html('<p style="color:var(--primary-beige); text-align:center; padding: 15px;">Searching...</p>');

            clearTimeout(window.searchTimeout);
            window.searchTimeout = setTimeout(() => {
                $.ajax({
                    url: BOOK_SEARCH_URL,
                    data: { q: query },
                    success: function(data) {
                        renderSearchResults(data);
                    },
                    error: function() {
                        $resultsContainer.html('<p style="color:var(--error-red); text-align:center; padding: 15px;">Error: Could not connect to search service.</p>');
                    }
                });
            }, 300); // Wait 300ms after typing stops
        } else if (query.length > 0) {
            $resultsContainer.html('<p style="color:var(--primary-beige); text-align:center; padding: 15px; opacity: 0.7;">Keep typing (min 4 characters for focused search).</p>');
        }
    });

    // 4. Render Search Results
    function renderSearchResults(books) {
        const $resultsContainer = $('#search-results');
        $resultsContainer.empty();

        if (!books || books.length === 0) {
            $resultsContainer.html('<p style="color:var(--primary-beige); text-align:center; padding: 15px;">No results found. Try a different title.</p>');
            return;
        }

        books.forEach(book => {
            // FIX: Store the book cover URL in the data attributes so we can retrieve it
            const resultHtml = `
                <div class="book-result-item" 
                     data-book-id="${book.id}" 
                     data-book-title="${book.title}"
                     data-book-cover="${book.cover}"> 
                    <img src="${book.cover}" class="book-cover-thumbnail" alt="Cover of ${book.title}" onerror="this.onerror=null;this.src='https://placehold.co/55x80/4a4a4a/ffffff?text=N/A'">
                    <div class="book-info">
                        <p class="book-title-result">${book.title}</p>
                        <p class="book-author-result">${book.author}</p>
                    </div>
                </div>
            `;
            $resultsContainer.append(resultHtml);
        });

        // Attach click handler to results
        $('.book-result-item').off('click').on('click', handleBookSelection);
    }

    // 5. Handle Book Selection (Trigger Validation and Saving)
    function handleBookSelection() {
        const $selectedBook = $(this);
        const bookId = $selectedBook.data('book-id');
        const bookTitle = $selectedBook.data('book-title');
        // FIX: Retrieve the cover URL from the selected book item
        const bookCover = $selectedBook.data('book-cover'); 
        
        const csrfToken = $('input[name="csrfmiddlewaretoken"]').val();

        if (activeCell) {
            const row = activeCell.data('row');
            const col = activeCell.data('col');
            
            // FIX: AJAX call to Django validation endpoint
            $.ajax({
                url: BOOK_VALIDATE_URL,
                type: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken,
                    'Content-Type': 'application/json'
                },
                data: JSON.stringify({
                    book_id: bookId,
                    row: row,
                    col: col
                }),
                success: function(response) {
                    if (response.is_correct) {
                        // Pass the cover image URL to markCellCorrect
                        markCellCorrect(activeCell, response.book_title || bookTitle, bookCover); 
                    } else {
                        markCellIncorrect(activeCell, response.book_title || bookTitle);
                    }
                    console.log("Validation/Save Success:", response.message);
                },
                error: function(xhr, status, error) {
                    // This often catches database errors or 500s from the backend
                    console.error("Validation/Save Error:", status, error, xhr.responseText);
                    // Provide generic failure feedback
                    markCellIncorrect(activeCell, bookTitle + ' (Verification Failed)');
                },
                complete: function() {
                    // Always close the modal after the process completes
                    closeModal();
                }
            });
        }
    }

    // 6. UI Update Functions
    // Updated to accept the cover URL
    function markCellCorrect($cell, title, coverUrl) {
        $cell.empty();
        
        // Remove the full green background by removing the 'correct-guess' class 
        // and relying on the default 'input-box' style, but we need some styling 
        // to indicate success, which is usually done by the content within.
        $cell.removeClass('correct-guess').off('click'); 
        
        // Use the default charcoal background (from input-box) but add the content
        
        // Construct the content with the cover image
        const bookHtml = `
            <div class="book-result-final">
                <img src="${coverUrl}" class="final-book-cover" alt="Cover of ${title}" onerror="this.onerror=null;this.src='https://placehold.co/55x80/4a4a4a/ffffff?text=N/A'">
                <p class="final-book-title">${title}</p>
            </div>
        `;
        $cell.append(bookHtml);
        
        // Add a class that can be styled for a visual 'solved' border/shadow effect
        $cell.addClass('solved-correctly');
    }

    function markCellIncorrect($cell, title) {
        $cell.empty();
        $cell.append(`<div class="book-result"><p class="book-title">${title}</p></div>`);
        $cell.addClass('incorrect-guess').removeClass('correct-guess').removeClass('solved-correctly');
        
        // Remove the guess content after a delay, allowing user to retry
        setTimeout(() => {
            $cell.empty().append('<span class="placeholder-text">Click to Guess</span>');
            $cell.removeClass('incorrect-guess');
        }, 2000); 
    }

});