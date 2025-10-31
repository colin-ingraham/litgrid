let activeBoxId = null;

$(".input-box").click(function() {
    $("#modal-backdrop").removeClass("hidden");
    activeBoxId = $(this).attr('id');
});

$("#modal-backdrop").click(function() {
    $("#modal-backdrop").addClass("hidden");
    $("#book-input").val("");
});

$("#modal-container").click(function(event) {
    event.stopPropagation();
});

$("input").keypress(function(event) { 
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

                    $("#" + activeBoxId).html(`<img src="${data.url}"><h2>${data.title}</h2><h3>${data.author}</h3>`);
                    
                    // Close modal and clear input
                    $("#modal-backdrop").addClass("hidden");
                    $("#book-input").val("");
                } else {
                    console.error("Search failed:", data.error);
                }
            },
            error: function(xhr, status, error) {
                console.error("AJAX Error:", status, error, xhr.responseText); 
                $("#modal-backdrop").addClass("hidden");
                $("#book-input").val("");
            }
        }) 
    }
})