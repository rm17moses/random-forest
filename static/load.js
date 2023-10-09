document.getElementById('upload-form').addEventListener('submit', function () {
    document.body.classList.add('loading'); // Add 'loading' class to body
    document.getElementById('loading-spinner').style.display = 'block';
});

function viewDatabase() {
    window.location.href = '/user_data';
};

function uploadFile(event) {
    event.preventDefault();
    const formData = new FormData();
    const fileInput = document.getElementById('fileInput');
    formData.append('file', fileInput.files[0]);

    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/upload', true);

    xhr.upload.onprogress = function (e) {
        if (e.lengthComputable) {
            const percentComplete = (e.loaded / e.total) * 100;
            document.getElementById('progress').innerText = `Progress: ${Math.round(percentComplete)}%`;
            // Update progress bar width
            document.getElementById('progress-bar').style.width = `${Math.round(percentComplete)}%`;
        }
    };

    xhr.onload = function () {
        if (xhr.status === 200) {
            const response = JSON.parse(xhr.responseText);
            if (response.result_filename) {
                // Ask user if they want to download the file
                var download = confirm("Do you want to download your results file?");
                if (download == true) {
                    window.location.href = `/download/${response.result_filename}`;
                    // Update progress bar text
                    document.getElementById('progress-bar').innerText = 'Analysis done and file has been downloaded';
                } else {
                    // User chose not to download the file
                    alert("You chose not to download the file.");
                }
            } else {
                alert('Invalid file type');
            }
        } else {
            alert('Error uploading file');
        }
        // Hide loading spinner
        document.getElementById('loading-spinner').style.display = 'none';
    };

    xhr.send(formData); // Send the form data
}