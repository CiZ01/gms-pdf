async function uploadPDF() {
    let files = document.getElementById("pdfFiles").files;
    let placement = document.getElementById("placement").value;
    let style = document.getElementById("style").value;
    let spacing = document.getElementById("spacing").value;
    let status = document.getElementById("status");

    if (files.length === 0) {
        alert("Please select at least one PDF file.");
        return;
    }

    let formData = new FormData();
    for (let file of files) {
        formData.append("pdf", file);
    }
    formData.append("placement", placement);
    formData.append("style", style);
    formData.append("spacing", spacing);

    status.innerText = "Processing...";

    await fetch("/upload", { method: "POST", body: formData })
    .then(response => response.blob())
    .then(blob => {
        let url = window.URL.createObjectURL(blob);
        let a = document.createElement("a");
        a.href = url;
        if (files.length === 1) {
            a.download = files[0].name
        } else {
            a.download = "notebooks.pdf";
        }
        document.body.appendChild(a);
        a.click();
        a.remove();
        status.innerText = "Download completed!";
    })
    .catch(error => {
        console.error("Error:", error);
        status.innerText = "Error generating PDFs.";
    });
}

