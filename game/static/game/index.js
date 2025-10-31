let activeBoxId = null;

$(".input-box").click(function() {
    if (!$(this).hasClass('filled')) {
        $("#modal-backdrop").removeClass("hidden");
        activeBoxId = $(this).attr('id');
        $("#book-input").focus();
    }
});

$("#modal-backdrop").click(function() {
    $("#modal-backdrop").addClass("hidden");
    $("#book-input").val("");
});

$("#modal-container").click(function(event) {
    event.stopPropagation();
});

$("input").keypress(function(event) { 
    event.stopPropagation();
    if( event.key === "Enter") {
        event.preventDefault();
        const inputValue = $('#book-input').val();
        const djangoUrl = BOOK_SEARCH_URL;
        $.ajax({
            type: 'POST',
            url: djangoUrl,
            data: {
                'user_text_input': inputValue,
                // You'll need to send the Django CSRF token for POST requests!
                'csrfmiddlewaretoken': $('input[name="csrfmiddlewaretoken"]').val() 
            },
            success: function(data) {
                
                if (data.success) {

                    $("#" + activeBoxId).html(`
                        <div class="book-result">
                            <img src="${data.url}" class="book-cover" alt="${data.title}">
                            <div class="book-info">
                                <h2 class="book-title">${data.title}</h2>
                                <h3 class="book-author">${data.author}</h3>
                            </div>
                        </div>
                    `);
                    
                    // Close modal and clear input
                    $("#modal-backdrop").addClass("hidden");
                    $("#" + activeBoxId).addClass("filled");
                    $("#book-input").val("");
                } else {
                    console.error("Search failed:", data.error);
                    $("#book-input").val("");
                    $("#book-input").attr("placeholder", "Book not found - try again");
                    $("#book-input").focus();
                    setTimeout(function() {
                        $("#book-input").attr("placeholder", "");
                    }, 2000);
                }
            },
            error: function(xhr, status, error) {
                console.error("AJAX Error:", status, error, xhr.responseText); 
                $("#book-input").val("");
                $("#book-input").attr("placeholder", "Book not found - try again");
                $("#book-input").focus();
                setTimeout(function() {
                        $("#book-input").attr("placeholder", "");
                }, 2000);
            }
        }) 
    }
})