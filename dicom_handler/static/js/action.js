
$(document).ready(function () {
    // Initialize DataTable with pagination, searching, and ordering
    $('#mapinfo-table').DataTable({
        responsive: true,
        paging: true,
        searching: true,
        ordering: true,
        pageLength: 10 // Adjust the number of rows per page
    });

    // CSRF token for form submission
    const csrftoken = $('[name=csrfmiddlewaretoken]').val();

    // Form submission handler
    $('.form').on('submit', function (e) {
        e.preventDefault();

        // Get form data
        const templateData = {
            templateName: $('#templatename').val(),
            description: $('#description').val(),
            selectedModels: []
        };

        // Get selected models
        $('#mapinfo-table tbody tr').each(function () {
            const checkbox = $(this).find('input[type="checkbox"]');
            if (checkbox.is(':checked')) {
                const rowData = {
                    model_id: $(this).find('td:eq(1)').text().trim(),
                    model_name: $(this).find('td:eq(2)').text().trim(),
                    mapid: $(this).find('td:eq(3)').text().trim(),
                    map_tg263_primary_name: $(this).find('td:eq(4)').text().trim(),
                    model_config: $(this).find('td:eq(5)').text().trim(),
                    model_trainer_name: $(this).find('td:eq(6)').text().trim(),
                    model_postprocess: $(this).find('td:eq(7)').text().trim()
                };
                templateData.selectedModels.push(rowData);
            }
        });

        // AJAX form submission
        $.ajax({
            url: '/create-yml/',  // Update the URL as necessary
            method: 'POST',
            headers: {
                'X-CSRFToken': csrftoken
            },
            contentType: 'application/json',
            data: JSON.stringify(templateData),
            success: function (response) {
                if (response.status === 'success') {
                    alert('Template created successfully!');
                    // Optionally, redirect or refresh
                    window.location.href = response.redirect_url;
                } else {
                    alert('Error: ' + response.message);
                }
            },
            error: function (xhr, status, error) {
                alert('Error creating template: ' + error);
            }
        });
    });
});